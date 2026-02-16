import argparse
import csv
import hashlib
import json
import math
import random
import statistics
import subprocess
import warnings
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from utils.common import load_config
from utils.parse import coerce_confidence


def as_float(x, d=0.0):
    try:
        if x in (None, "", "nan"):
            return d
        return float(x)
    except Exception:
        return d


def corr(x, y):
    n = len(x)
    if n < 2:
        return float("nan")
    mx, my = sum(x) / n, sum(y) / n
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    dx = math.sqrt(sum((a - mx) ** 2 for a in x))
    dy = math.sqrt(sum((b - my) ** 2 for b in y))
    return num / (dx * dy + 1e-9)


def rank(vals):
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    r = [0] * len(vals)
    for k, i in enumerate(order):
        r[i] = k
    return r


def _bin_members(rows, bins):
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        if b == bins - 1:
            chunk = [r for r in rows if lo <= r["conf"] <= 1.0]
        else:
            chunk = [r for r in rows if lo <= r["conf"] < hi]
        yield b, lo, hi, chunk


def ece(rows, err_col, bins):
    if not rows:
        return float("nan")
    out = 0.0
    for _, _, _, chunk in _bin_members(rows, bins):
        if not chunk:
            continue
        acc = sum(1 - r[err_col] for r in chunk) / len(chunk)
        c = sum(r["conf"] for r in chunk) / len(chunk)
        out += (len(chunk) / len(rows)) * abs(acc - c)
    return out


def reliability_curve(rows, err_col, bins):
    xs, ys = [], []
    for _, lo, hi, chunk in _bin_members(rows, bins):
        if not chunk:
            continue
        center = (lo + hi) / 2
        acc = sum(1 - r[err_col] for r in chunk) / len(chunk)
        xs.append(center)
        ys.append(acc)
    return xs, ys


def bootstrap_ci(values, n=500):
    if not values:
        return [float("nan"), float("nan")]
    rng = random.Random(123)
    stats = []
    for _ in range(n):
        samp = [values[rng.randrange(len(values))] for _ in range(len(values))]
        stats.append(sum(samp) / len(samp))
    stats.sort()
    return [stats[int(0.025 * (n - 1))], stats[int(0.975 * (n - 1))]]


def _safe_slug(label: str) -> str:
    return "".join(c.lower() if c.isalnum() else "_" for c in label).strip("_")


def _write_meta(path: Path, cfg_path: str, cfg: dict, rows: list):
    providers = sorted({r["provider"] for r in rows})
    models = sorted({f"{r['provider']}/{r['model_id']}" for r in rows})
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        commit = "unknown"
    cfg_text = Path(cfg_path).read_text(encoding="utf-8")
    meta = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "config_hash_sha256": hashlib.sha256(cfg_text.encode("utf-8")).hexdigest(),
        "git_commit": commit,
        "providers": providers,
        "models": models,
        "n": len(rows),
        "seed": (cfg.get("global") or {}).get("seed"),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def _mismatch_rate(rows, err_col, tau):
    if not rows:
        return float("nan")
    mism = [1 if (r[err_col] == 1 and r["conf"] > tau) else 0 for r in rows]
    return sum(mism) / len(mism)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/models.yaml")
    ap.add_argument("--input", default="runs/aggregated/dataframe.csv")
    ap.add_argument("--outdir", default="figures")
    ap.add_argument("--results", default="runs/aggregated/results_by_model.json")
    ap.add_argument("--summary", default="runs/aggregated/summary_table.csv")
    ap.add_argument("--examples", default="paper/top_mismatch_examples.md")
    ap.add_argument("--meta", default="runs/aggregated/meta.json")
    args = ap.parse_args()

    cfg = load_config(args.config)
    g = cfg["global"]
    mismatch_error_col = g.get("mismatch_error_col", "error_within_model_q20")
    if mismatch_error_col not in {"error_within_model_q20", "error_global_q20"}:
        raise ValueError("global.mismatch_error_col must be error_within_model_q20 or error_global_q20")

    with open(args.input, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        Path(args.results).parent.mkdir(parents=True, exist_ok=True)
        Path(args.summary).parent.mkdir(parents=True, exist_ok=True)
        Path(args.examples).parent.mkdir(parents=True, exist_ok=True)
        Path(args.results).write_text("{}", encoding="utf-8")
        Path(args.summary).write_text(
            "model,mean_quality,ece_global_q20,ece_within_model_q20,mismatch_rate_overall,avg_total_latency_s\n",
            encoding="utf-8",
        )
        Path(args.examples).write_text("# Top confident-but-wrong examples\n\n_No data available._\n", encoding="utf-8")
        Path(args.outdir).mkdir(parents=True, exist_ok=True)
        _write_meta(Path(args.meta), args.config, cfg, rows)
        return

    for r in rows:
        r["conf"] = coerce_confidence(r.get("confidence", r.get("conf")))
        for k in ["difficulty_score", "quality", "latency_translate_s", "latency_conf_s", "input_tokens", "output_tokens"]:
            r[k] = as_float(r.get(k), 0.0)
        for k in ["error_global_q20", "error_within_model_q20"]:
            r[k] = int(as_float(r.get(k), 0))

    grouped = defaultdict(list)
    for r in rows:
        grouped[f"{r['provider']}/{r['model_id']}"] .append(r)

    results = {}
    summary = []
    lines = ["# Top confident-but-wrong examples\n"]

    mismatch_all = []
    ece_bucket_values = []

    for label, d_all in grouped.items():
        d_valid = [r for r in d_all if r["conf"] is not None and 0.0 <= r["conf"] <= 1.0]
        x_all = [r["difficulty_score"] for r in d_all]
        conf_all = [r["conf"] if r["conf"] is not None else 0.5 for r in d_all]
        qual_all = [r["quality"] for r in d_all]

        conf_stats = {
            "num_rows_total": len(d_all),
            "num_rows_with_valid_conf": len(d_valid),
            "min_conf": min((r["conf"] for r in d_valid), default=float("nan")),
            "median_conf": statistics.median([r["conf"] for r in d_valid]) if d_valid else float("nan"),
            "max_conf": max((r["conf"] for r in d_valid), default=float("nan")),
        }

        if not d_valid:
            warnings.warn(f"{label}: no valid confidence values; skipping mismatch/ECE")
            ece_g = float("nan")
            ece_w = float("nan")
            mism_main = float("nan")
            mism_within = float("nan")
            mism_global = float("nan")
            mismatch_by_bucket = {b: float("nan") for b in ["Q1", "Q2", "Q3", "Q4"]}
            ece_by_bucket = {b: float("nan") for b in ["Q1", "Q2", "Q3", "Q4"]}
            tau_map = {f"mismatch_rate_overall_tau_{tau:.1f}": float("nan") for tau in [0.6, 0.7, 0.8, 0.9]}
        else:
            ece_g = ece(d_valid, "error_global_q20", g["conf_bins"])
            ece_w = ece(d_valid, "error_within_model_q20", g["conf_bins"])
            mism_main = _mismatch_rate(d_valid, mismatch_error_col, g["tau"])
            mism_within = _mismatch_rate(d_valid, "error_within_model_q20", g["tau"])
            mism_global = _mismatch_rate(d_valid, "error_global_q20", g["tau"])

            mismatch_by_bucket = {}
            ece_by_bucket = {}
            for b in ["Q1", "Q2", "Q3", "Q4"]:
                subset = [r for r in d_valid if r["difficulty_bucket"] == b]
                mismatch_by_bucket[b] = _mismatch_rate(subset, mismatch_error_col, g["tau"]) if subset else float("nan")
                ece_by_bucket[b] = ece(subset, mismatch_error_col, g["conf_bins"]) if subset else float("nan")

            tau_map = {
                f"mismatch_rate_overall_tau_{tau:.1f}": _mismatch_rate(d_valid, mismatch_error_col, tau)
                for tau in [0.6, 0.7, 0.8, 0.9]
            }

            ece_bucket_values.extend([v for v in ece_by_bucket.values() if not math.isnan(v)])
            mismatch_all.append(mism_main)

        results[label] = {
            "confidence_stats": conf_stats,
            "correlations": {
                "pearson_difficulty_conf": corr(x_all, conf_all),
                "spearman_difficulty_conf": corr(rank(x_all), rank(conf_all)),
                "pearson_difficulty_quality": corr(x_all, qual_all),
                "spearman_difficulty_quality": corr(rank(x_all), rank(qual_all)),
                "pearson_conf_quality": corr(conf_all, qual_all),
                "spearman_conf_quality": corr(rank(conf_all), rank(qual_all)),
            },
            "ece_global_q20": ece_g,
            "ece_within_model_q20": ece_w,
            "ece_by_difficulty_bucket": ece_by_bucket,
            "mismatch_rate_overall": mism_main,
            "mismatch_rate_overall_within_model_q20": mism_within,
            "mismatch_rate_overall_global_q20": mism_global,
            "mismatch_rate_by_bucket": mismatch_by_bucket,
            **tau_map,
            "efficiency": {
                "avg_latency_translate_s": sum(r["latency_translate_s"] for r in d_all) / len(d_all),
                "avg_latency_conf_s": sum(r["latency_conf_s"] for r in d_all) / len(d_all),
                "avg_total_latency_s": sum(r["latency_translate_s"] + r["latency_conf_s"] for r in d_all) / len(d_all),
                "avg_input_tokens": sum(r["input_tokens"] for r in d_all) / len(d_all),
                "avg_output_tokens": sum(r["output_tokens"] for r in d_all) / len(d_all),
                "median_output_tokens": sorted(r["output_tokens"] for r in d_all)[len(d_all) // 2],
            },
            "bootstrap_ci": {
                "mean_quality": bootstrap_ci(qual_all, g["bootstrap_samples"]),
                "ece": bootstrap_ci(
                    [abs((1 - r[mismatch_error_col]) - r["conf"]) for r in d_valid],
                    g["bootstrap_samples"],
                )
                if d_valid
                else [float("nan"), float("nan")],
                "mismatch_rate_overall": bootstrap_ci(
                    [1 if (r[mismatch_error_col] == 1 and r["conf"] > g["tau"]) else 0 for r in d_valid],
                    g["bootstrap_samples"],
                )
                if d_valid
                else [float("nan"), float("nan")],
            },
        }

        summary.append(
            {
                "model": label,
                "mean_quality": sum(qual_all) / len(qual_all),
                "ece_global_q20": ece_g,
                "ece_within_model_q20": ece_w,
                "mismatch_rate_overall": mism_main,
                "avg_total_latency_s": results[label]["efficiency"]["avg_total_latency_s"],
            }
        )

        bad = [r for r in d_valid if r[mismatch_error_col] == 1]
        bad.sort(key=lambda r: (-r["conf"], r["quality"]))
        lines.append(f"\n## {label}\n")
        lines.append("| id | bucket | conf | quality | src | hyp | ref |\n|---|---|---:|---:|---|---|---|\n")
        for r in bad[:10]:
            lines.append(
                f"| {r['id']} | {r['difficulty_bucket']} | {r['conf']:.3f} | {r['quality']:.2f} | {r['src'].replace('|','/')} | {r['hyp'].replace('|','/')} | {r['ref'].replace('|','/')} |\n"
            )

    Path(args.results).parent.mkdir(parents=True, exist_ok=True)
    with open(args.results, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    Path(args.summary).parent.mkdir(parents=True, exist_ok=True)
    with open(args.summary, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["model", "mean_quality", "ece_global_q20", "ece_within_model_q20", "mismatch_rate_overall", "avg_total_latency_s"],
        )
        w.writeheader()
        w.writerows(summary)

    Path(args.examples).parent.mkdir(parents=True, exist_ok=True)
    with open(args.examples, "w", encoding="utf-8") as f:
        f.writelines(lines)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    plt.style.use("seaborn-v0_8-whitegrid")

    plt.figure(figsize=(8, 5))
    for label, d_all in grouped.items():
        valid = [r for r in d_all if r["conf"] is not None]
        if not valid:
            continue
        plt.scatter([r["difficulty_score"] for r in valid], [r["conf"] for r in valid], s=10, alpha=0.5, label=label)
    plt.xlabel("Difficulty score")
    plt.ylabel("Confidence")
    plt.title("Confidence vs difficulty")
    plt.legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(outdir / "fig1_scatter_difficulty_vs_conf.png", dpi=200)
    plt.close()

    plt.figure(figsize=(8, 5))
    for label, d_all in grouped.items():
        d_valid = [r for r in d_all if r["conf"] is not None]
        xs, ys = reliability_curve(d_valid, mismatch_error_col, g["conf_bins"])
        if xs:
            plt.plot(xs, ys, marker="o", linewidth=1, label=label)
            slug = _safe_slug(label)
            plt_m = plt.figure(figsize=(6, 4))
            plt.plot(xs, ys, marker="o", linewidth=1)
            plt.plot([0, 1], [0, 1], "k--", linewidth=1)
            plt.xlabel("Confidence")
            plt.ylabel("Accuracy")
            plt.title(f"Reliability diagram: {label}")
            plt.ylim(0, 1)
            plt.xlim(0, 1)
            plt.tight_layout()
            plt.savefig(outdir / f"reliability_{slug}.png", dpi=200)
            plt.close(plt_m)
    plt.plot([0, 1], [0, 1], "k--", linewidth=1)
    plt.xlabel("Confidence")
    plt.ylabel("Accuracy")
    plt.title("Reliability diagram")
    plt.ylim(0, 1)
    plt.xlim(0, 1)
    plt.legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(outdir / "fig2_reliability_diagram_overlay.png", dpi=200)
    plt.close()

    buckets = ["Q1", "Q2", "Q3", "Q4"]
    labels = list(grouped.keys())
    x = list(range(len(buckets)))
    width = 0.8 / max(1, len(labels))
    plt.figure(figsize=(9, 5))
    for i, label in enumerate(labels):
        vals = [results[label]["mismatch_rate_by_bucket"].get(b, float("nan")) for b in buckets]
        xs = [v + (i - (len(labels) - 1) / 2) * width for v in x]
        plt.bar(xs, vals, width=width, label=label)
    plt.xticks(x, buckets)
    plt.ylabel("Mismatch rate")
    plt.xlabel("Difficulty bucket")
    plt.title("Mismatch rate by difficulty bucket")
    plt.legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(outdir / "fig3_mismatch_by_difficulty_bucket.png", dpi=200)
    plt.close()

    plt.figure(figsize=(7, 5))
    for label in labels:
        qv = next(s["mean_quality"] for s in summary if s["model"] == label)
        tv = results[label]["efficiency"]["avg_total_latency_s"]
        plt.scatter(tv, qv, s=60)
        plt.annotate(label, (tv, qv), fontsize=7, xytext=(3, 3), textcoords="offset points")
    plt.xlabel("Average total latency (s)")
    plt.ylabel("Mean quality (chrF++)")
    plt.title("Efficiency frontier")
    plt.tight_layout()
    plt.savefig(outdir / "fig4_efficiency_frontier.png", dpi=200)
    plt.close()

    if mismatch_all and all((v == 0.0) for v in mismatch_all if not math.isnan(v)):
        warnings.warn("mismatch_rate_overall is 0.0 for all models; mismatch definition or tau may be too strict")
    if not ece_bucket_values or all((v == 0.0 or math.isnan(v)) for v in ece_bucket_values):
        warnings.warn("ECE-by-difficulty buckets are all 0 or NaN; check confidence and error labels")
    for label, metrics in results.items():
        if metrics["efficiency"]["median_output_tokens"] > 300:
            warnings.warn(f"{label} median output_tokens > 300; output may be too verbose")

    _write_meta(Path(args.meta), args.config, cfg, rows)


if __name__ == "__main__":
    main()
