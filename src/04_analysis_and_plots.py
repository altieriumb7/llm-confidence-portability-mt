import argparse
import base64
import csv
import json
import math
import random
from collections import defaultdict
from pathlib import Path

from utils.common import load_config

PNG_1X1 = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+tmHsAAAAASUVORK5CYII=")


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


def ece(rows, err_col, bins):
    valid = [r for r in rows if r["conf"] is not None]
    if not valid:
        return float("nan")
    out = 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        chunk = [r for r in valid if lo <= r["conf"] <= hi]
        if not chunk:
            continue
        acc = sum(1 - r[err_col] for r in chunk) / len(chunk)
        c = sum(r["conf"] for r in chunk) / len(chunk)
        out += (len(chunk) / len(valid)) * abs(acc - c)
    return out


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


def write_placeholder_png(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(PNG_1X1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/models.yaml")
    ap.add_argument("--input", default="runs/aggregated/dataframe.csv")
    ap.add_argument("--outdir", default="figures")
    ap.add_argument("--results", default="runs/aggregated/results_by_model.json")
    ap.add_argument("--summary", default="runs/aggregated/summary_table.csv")
    ap.add_argument("--examples", default="paper/top_mismatch_examples.md")
    args = ap.parse_args()

    cfg = load_config(args.config)
    g = cfg["global"]

    with open(args.input, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        Path(args.results).parent.mkdir(parents=True, exist_ok=True)
        Path(args.summary).parent.mkdir(parents=True, exist_ok=True)
        Path(args.examples).parent.mkdir(parents=True, exist_ok=True)
        Path(args.results).write_text("{}", encoding="utf-8")
        Path(args.summary).write_text("model,mean_quality,ece_global_q20,mismatch_rate_overall,avg_total_latency_s\n", encoding="utf-8")
        Path(args.examples).write_text("# Top confident-but-wrong examples\n\n_No data available._\n", encoding="utf-8")
        for p in ["fig1_scatter_difficulty_vs_conf.png","fig2_reliability_diagram_overlay.png","fig3_mismatch_by_difficulty_bucket.png","fig4_efficiency_frontier.png"]:
            write_placeholder_png(Path(args.outdir)/p)
        return
    for r in rows:
        r["conf"] = None if r["conf"] in ("", "None") else as_float(r["conf"], 0.5)
        for k in ["difficulty_score", "quality", "latency_translate_s", "latency_conf_s", "input_tokens", "output_tokens"]:
            r[k] = as_float(r.get(k), 0.0)
        for k in ["error_global_q20", "error_within_model_q20"]:
            r[k] = int(as_float(r[k], 0))

    grouped = defaultdict(list)
    for r in rows:
        grouped[f"{r['provider']}/{r['model_id']}"] .append(r)

    results = {}
    summary = []
    lines = ["# Top confident-but-wrong examples\n"]

    for label, d in grouped.items():
        x = [r["difficulty_score"] for r in d]
        conf = [0.5 if r["conf"] is None else r["conf"] for r in d]
        qual = [r["quality"] for r in d]
        ece_g = ece(d, "error_global_q20", g["conf_bins"])
        ece_w = ece(d, "error_within_model_q20", g["conf_bins"])

        mism = [1 if (r["error_global_q20"] == 1 and (r["conf"] or 0) > g["tau"]) else 0 for r in d]
        by_bucket = {}
        for b in ["Q1", "Q2", "Q3", "Q4"]:
            m = [mism[i] for i, r in enumerate(d) if r["difficulty_bucket"] == b]
            by_bucket[b] = (sum(m) / len(m)) if m else float("nan")

        results[label] = {
            "correlations": {
                "pearson_difficulty_conf": corr(x, conf),
                "spearman_difficulty_conf": corr(rank(x), rank(conf)),
                "pearson_difficulty_quality": corr(x, qual),
                "spearman_difficulty_quality": corr(rank(x), rank(qual)),
                "pearson_conf_quality": corr(conf, qual),
                "spearman_conf_quality": corr(rank(conf), rank(qual)),
            },
            "ece_global_q20": ece_g,
            "ece_within_model_q20": ece_w,
            "ece_by_difficulty_bucket": by_bucket,
            "mismatch_rate_overall": sum(mism) / len(mism),
            "mismatch_rate_by_bucket": by_bucket,
            "efficiency": {
                "avg_latency_translate_s": sum(r["latency_translate_s"] for r in d) / len(d),
                "avg_latency_conf_s": sum(r["latency_conf_s"] for r in d) / len(d),
                "avg_total_latency_s": sum(r["latency_translate_s"] + r["latency_conf_s"] for r in d) / len(d),
                "avg_input_tokens": sum(r["input_tokens"] for r in d) / len(d),
                "avg_output_tokens": sum(r["output_tokens"] for r in d) / len(d),
            },
            "bootstrap_ci": {
                "mean_quality": bootstrap_ci(qual, g["bootstrap_samples"]),
                "ece": bootstrap_ci([abs((1-r["error_global_q20"]) - (r["conf"] or 0.5)) for r in d], g["bootstrap_samples"]),
                "mismatch_rate_overall": bootstrap_ci(mism, g["bootstrap_samples"]),
            },
        }

        summary.append({
            "model": label,
            "mean_quality": sum(qual) / len(qual),
            "ece_global_q20": ece_g,
            "mismatch_rate_overall": sum(mism) / len(mism),
            "avg_total_latency_s": results[label]["efficiency"]["avg_total_latency_s"],
        })

        bad = [r for r in d if r["error_global_q20"] == 1 and r["conf"] is not None]
        bad.sort(key=lambda r: (-r["conf"], r["quality"]))
        lines.append(f"\n## {label}\n")
        lines.append("| id | bucket | conf | quality | src | hyp | ref |\n|---|---|---:|---:|---|---|---|\n")
        for r in bad[:10]:
            lines.append(f"| {r['id']} | {r['difficulty_bucket']} | {r['conf']:.3f} | {r['quality']:.2f} | {r['src'].replace('|','/')} | {r['hyp'].replace('|','/')} | {r['ref'].replace('|','/')} |\n")

    Path(args.results).parent.mkdir(parents=True, exist_ok=True)
    with open(args.results, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    Path(args.summary).parent.mkdir(parents=True, exist_ok=True)
    with open(args.summary, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["model", "mean_quality", "ece_global_q20", "mismatch_rate_overall", "avg_total_latency_s"])
        w.writeheader()
        w.writerows(summary)

    Path(args.examples).parent.mkdir(parents=True, exist_ok=True)
    with open(args.examples, "w", encoding="utf-8") as f:
        f.writelines(lines)

    for p in [
        "fig1_scatter_difficulty_vs_conf.png",
        "fig2_reliability_diagram_overlay.png",
        "fig3_mismatch_by_difficulty_bucket.png",
        "fig4_efficiency_frontier.png",
    ]:
        write_placeholder_png(Path(args.outdir) / p)


if __name__ == "__main__":
    main()
