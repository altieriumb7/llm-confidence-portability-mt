import argparse
import csv
import json
from pathlib import Path


def as_float(x, default=0.0):
    try:
        if x in (None, "", "nan"):
            return default
        return float(x)
    except Exception:
        return default


def quantile(vals, q):
    s = sorted(vals)
    if not s:
        return 0.0
    idx = int((len(s) - 1) * q)
    return s[idx]


def mismatch_rate(rows, error_col, tau=0.9):
    if not rows:
        return float("nan")
    return sum(1 for r in rows if r[error_col] == 1 and r["conf"] >= tau) / len(rows)


def ece(rows, error_col, bins=10):
    if not rows:
        return float("nan")
    total = 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        if b == bins - 1:
            chunk = [r for r in rows if lo <= r["conf"] <= 1.0]
        else:
            chunk = [r for r in rows if lo <= r["conf"] < hi]
        if not chunk:
            continue
        acc = sum(1 - r[error_col] for r in chunk) / len(chunk)
        mean_conf = sum(r["conf"] for r in chunk) / len(chunk)
        total += (len(chunk) / len(rows)) * abs(acc - mean_conf)
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="runs/aggregated/dataframe.csv")
    ap.add_argument("--secondary_scores", default="runs/aggregated/secondary_metric/secondary_metric_scores.csv")
    ap.add_argument("--outdir", default="runs/aggregated/metric_robustness")
    ap.add_argument("--tau", type=float, default=0.9)
    ap.add_argument("--bins", type=int, default=10)
    ap.add_argument("--secondary_quantile", type=float, default=0.2)
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    secondary_by_key = {}
    secondary_name = "unavailable"
    p = Path(args.secondary_scores)
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                key = (row.get("provider"), row.get("model_id"), str(row.get("id")))
                secondary_by_key[key] = as_float(row.get("secondary_metric_score"), 0.0)
                secondary_name = row.get("secondary_metric_name") or secondary_name

    grouped = {}
    for row in rows:
        row["conf"] = as_float(row.get("conf"), None)
        if row["conf"] is None:
            continue
        row["chrf"] = as_float(row.get("chrf"), 0.0)
        row["secondary_metric_score"] = secondary_by_key.get((row.get("provider"), row.get("model_id"), str(row.get("id"))), as_float(row.get("bleu"), 0.0))
        label = f"{row.get('provider','unknown')}/{row.get('model_id','unknown')}"
        grouped.setdefault(label, []).append(row)

    table = []
    for label, model_rows in sorted(grouped.items()):
        chrf_thr = quantile([r["chrf"] for r in model_rows], args.secondary_quantile)
        sec_thr = quantile([r["secondary_metric_score"] for r in model_rows], args.secondary_quantile)
        for r in model_rows:
            r["error_chrf_q20"] = int(r["chrf"] < chrf_thr)
            r["error_secondary_q20"] = int(r["secondary_metric_score"] < sec_thr)
        table.append(
            {
                "model": label,
                "secondary_metric_name": secondary_name,
                "mean_chrf": sum(r["chrf"] for r in model_rows) / len(model_rows),
                "mean_secondary_metric": sum(r["secondary_metric_score"] for r in model_rows) / len(model_rows),
                "ece_chrf_q20": ece(model_rows, "error_chrf_q20", bins=args.bins),
                "ece_secondary_q20": ece(model_rows, "error_secondary_q20", bins=args.bins),
                "mismatch_chrf_q20_tau_0_9": mismatch_rate(model_rows, "error_chrf_q20", tau=args.tau),
                "mismatch_secondary_q20_tau_0_9": mismatch_rate(model_rows, "error_secondary_q20", tau=args.tau),
            }
        )

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    with open(outdir / "metric_robustness_summary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "model",
                "secondary_metric_name",
                "mean_chrf",
                "mean_secondary_metric",
                "ece_chrf_q20",
                "ece_secondary_q20",
                "mismatch_chrf_q20_tau_0_9",
                "mismatch_secondary_q20_tau_0_9",
            ],
        )
        writer.writeheader()
        writer.writerows(table)

    (outdir / "metric_robustness_summary.json").write_text(
        json.dumps({"secondary_metric_name": secondary_name, "rows": table}, indent=2), encoding="utf-8"
    )
    print(f"Wrote metric robustness artifacts to {outdir}")

if __name__ == "__main__":
    main()
