import argparse
import csv
from pathlib import Path

from utils.analysis_helpers import (
    ece,
    group_by_model,
    json_dump,
    load_dataframe_rows,
    quantile,
    write_csv,
    write_markdown_table,
    write_tex_table,
)


def selective_rows(rows: list[dict], error_col: str, tau: float) -> dict:
    valid = [r for r in rows if r.get("conf") is not None]
    accepted = [r for r in valid if r["conf"] > tau]
    accepted_errors = sum(int(r.get(error_col, 0)) for r in accepted)
    return {
        "coverage": len(accepted) / len(valid) if valid else float("nan"),
        "mismatch": accepted_errors / len(valid) if valid else float("nan"),
        "accepted_error_rate": accepted_errors / len(accepted) if accepted else float("nan"),
    }


def load_secondary_scores(path: str | Path) -> tuple[dict, str, str]:
    scores = {}
    backend = "unavailable"
    label = "Unavailable"
    source = Path(path)
    if not source.exists():
        return scores, backend, label
    with open(source, "r", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            scores[(row.get("provider"), row.get("model_id"), str(row.get("id")))] = float(row.get("secondary_metric_score", 0.0))
            backend = row.get("secondary_metric_name") or backend
            label = row.get("secondary_metric_label") or label
    return scores, backend, label


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="runs/aggregated/dataframe.csv")
    ap.add_argument("--secondary_scores", default="runs/aggregated/secondary_metric/secondary_metric_scores.csv")
    ap.add_argument("--outdir", default="runs/aggregated/metric_robustness")
    ap.add_argument("--tau", type=float, default=0.9)
    ap.add_argument("--bins", type=int, default=10)
    ap.add_argument("--secondary_quantile", type=float, default=0.2)
    args = ap.parse_args()

    rows = load_dataframe_rows(args.input)
    secondary_scores, secondary_backend, secondary_label = load_secondary_scores(args.secondary_scores)

    grouped = group_by_model(rows)
    summary_rows = []
    payload = {
        "config": {
            "input": args.input,
            "secondary_scores": args.secondary_scores,
            "tau": args.tau,
            "bins": args.bins,
            "secondary_quantile": args.secondary_quantile,
        },
        "secondary_metric": {
            "backend": secondary_backend,
            "label": secondary_label,
        },
        "models": {},
    }

    for model, model_rows in sorted(grouped.items()):
        chrf_rows = [dict(row) for row in model_rows if row.get("conf") is not None]
        if not chrf_rows:
            continue
        sec_vals = []
        for row in chrf_rows:
            key = (row.get("provider"), row.get("model_id"), str(row.get("id")))
            row["secondary_metric_score"] = secondary_scores.get(key, float(row.get("bleu", 0.0)))
            sec_vals.append(row["secondary_metric_score"])
        secondary_source = secondary_backend if secondary_scores else "bleu_fallback_from_dataframe"

        chrf_threshold = quantile([r["chrf"] for r in chrf_rows], args.secondary_quantile)
        secondary_threshold = quantile(sec_vals, args.secondary_quantile)
        for row in chrf_rows:
            row["error_chrf_q20"] = int(row["chrf"] < chrf_threshold)
            row["error_secondary_q20"] = int(row["secondary_metric_score"] < secondary_threshold)

        chrf_sel = selective_rows(chrf_rows, "error_chrf_q20", args.tau)
        sec_sel = selective_rows(chrf_rows, "error_secondary_q20", args.tau)
        summary_row = {
            "model": model,
            "secondary_metric_name": secondary_source,
            "secondary_metric_label": secondary_label,
            "ece_chrf_q20": ece(chrf_rows, "error_chrf_q20", bins=args.bins),
            "ece_secondary_q20": ece(chrf_rows, "error_secondary_q20", bins=args.bins),
            "coverage_chrf_tau_0_9": chrf_sel["coverage"],
            "coverage_secondary_tau_0_9": sec_sel["coverage"],
            "mismatch_chrf_tau_0_9": chrf_sel["mismatch"],
            "mismatch_secondary_tau_0_9": sec_sel["mismatch"],
            "accepted_error_chrf_tau_0_9": chrf_sel["accepted_error_rate"],
            "accepted_error_secondary_tau_0_9": sec_sel["accepted_error_rate"],
        }
        summary_rows.append(summary_row)
        payload["models"][model] = {
            "summary": summary_row,
            "thresholds": {
                "chrf": chrf_threshold,
                "secondary": secondary_threshold,
            },
        }

    cols = [
        "model",
        "secondary_metric_name",
        "secondary_metric_label",
        "ece_chrf_q20",
        "ece_secondary_q20",
        "coverage_chrf_tau_0_9",
        "coverage_secondary_tau_0_9",
        "mismatch_chrf_tau_0_9",
        "mismatch_secondary_tau_0_9",
        "accepted_error_chrf_tau_0_9",
        "accepted_error_secondary_tau_0_9",
    ]
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    write_csv(outdir / "metric_robustness_summary.csv", summary_rows, cols)
    json_dump(outdir / "metric_robustness_summary.json", payload)
    write_markdown_table(outdir / "metric_robustness_summary.md", "Metric robustness summary", summary_rows, cols)
    write_tex_table(outdir / "metric_robustness_summary.tex", summary_rows, [
        "model", "secondary_metric_label", "ece_chrf_q20", "ece_secondary_q20", "mismatch_chrf_tau_0_9", "mismatch_secondary_tau_0_9"
    ])
    print(f"Wrote metric robustness artifacts to {outdir}")


if __name__ == "__main__":
    main()
