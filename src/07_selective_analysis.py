import argparse
from pathlib import Path

from utils.analysis_helpers import (
    DEFAULT_THRESHOLD_GRID,
    ece,
    group_by_model,
    json_dump,
    load_dataframe_rows,
    write_csv,
    write_markdown_table,
    write_tex_table,
)
from utils.common import load_config


def selective_stats(rows: list[dict], error_col: str, tau: float) -> dict:
    valid = [r for r in rows if r.get("conf") is not None]
    accepted = [r for r in valid if r["conf"] > tau]
    rejected = [r for r in valid if r["conf"] <= tau]
    accepted_errors = sum(int(r.get(error_col, 0)) for r in accepted)
    accepted_non_errors = len(accepted) - accepted_errors
    return {
        "threshold": tau,
        "n_total": len(valid),
        "n_accepted": len(accepted),
        "n_rejected": len(rejected),
        "coverage": (len(accepted) / len(valid)) if valid else float("nan"),
        "mismatch_rate": (accepted_errors / len(valid)) if valid else float("nan"),
        "accepted_error_rate": (accepted_errors / len(accepted)) if accepted else float("nan"),
        "accepted_non_low_quality_rate": (accepted_non_errors / len(accepted)) if accepted else float("nan"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/models.yaml")
    ap.add_argument("--input", default="runs/aggregated/dataframe.csv")
    ap.add_argument("--outdir", default="runs/aggregated/selective_analysis")
    ap.add_argument("--error_col", default=None)
    ap.add_argument("--thresholds", default=",".join(str(x) for x in DEFAULT_THRESHOLD_GRID))
    ap.add_argument("--bins", type=int, default=10)
    args = ap.parse_args()

    cfg = load_config(args.config)
    error_col = args.error_col or cfg.get("global", {}).get("mismatch_error_col", "error_within_model_q20")
    thresholds = [float(part) for part in args.thresholds.split(",") if part.strip()]

    rows = load_dataframe_rows(args.input)
    grouped = group_by_model(rows)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    threshold_rows = []
    model_summary = []
    payload = {
        "config": {
            "input": args.input,
            "error_col": error_col,
            "thresholds": thresholds,
            "bins": args.bins,
        },
        "models": {},
    }

    for model, model_rows in sorted(grouped.items()):
        valid = [r for r in model_rows if r.get("conf") is not None]
        if not valid:
            continue
        threshold_stats = []
        for tau in thresholds:
            stats = selective_stats(valid, error_col, tau)
            stats["model"] = model
            stats["ece"] = ece(valid, error_col, bins=args.bins)
            threshold_rows.append(stats)
            threshold_stats.append(stats)

        tau09 = next((row for row in threshold_stats if abs(row["threshold"] - 0.9) < 1e-9), threshold_stats[-1])
        summary_row = {
            "model": model,
            "error_col": error_col,
            "n_total": tau09["n_total"],
            "coverage_at_0_9": tau09["coverage"],
            "mismatch_at_0_9": tau09["mismatch_rate"],
            "accepted_error_rate_at_0_9": tau09["accepted_error_rate"],
            "accepted_non_low_quality_rate_at_0_9": tau09["accepted_non_low_quality_rate"],
            "ece": ece(valid, error_col, bins=args.bins),
        }
        model_summary.append(summary_row)
        payload["models"][model] = {
            "summary": summary_row,
            "thresholds": threshold_stats,
            "risk_coverage_curve": [
                {
                    "threshold": row["threshold"],
                    "coverage": row["coverage"],
                    "accepted_error_rate": row["accepted_error_rate"],
                }
                for row in threshold_stats
            ],
        }

    compact_cols = [
        "model",
        "coverage_at_0_9",
        "mismatch_at_0_9",
        "accepted_error_rate_at_0_9",
        "accepted_non_low_quality_rate_at_0_9",
        "ece",
    ]
    write_csv(outdir / "selective_threshold_summary.csv", threshold_rows, [
        "model", "threshold", "n_total", "n_accepted", "n_rejected", "coverage", "mismatch_rate",
        "accepted_error_rate", "accepted_non_low_quality_rate", "ece"
    ])
    write_csv(outdir / "selective_model_summary.csv", model_summary, list(model_summary[0].keys()) if model_summary else compact_cols)
    json_dump(outdir / "selective_threshold_summary.json", payload)
    write_markdown_table(outdir / "selective_threshold_summary.md", "Selective threshold summary", model_summary, compact_cols)
    write_tex_table(outdir / "selective_threshold_summary.tex", model_summary, compact_cols)
    print(f"Wrote selective analysis artifacts to {outdir}")


if __name__ == "__main__":
    main()
