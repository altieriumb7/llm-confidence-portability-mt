import argparse
from collections import Counter
from pathlib import Path

from utils.analysis_helpers import ece, group_by_model, json_dump, load_dataframe_rows, write_csv, write_markdown_table, write_tex_table
from utils.common import load_config


def rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else float("nan")


def mean_conf(rows: list[dict]) -> float:
    vals = [r["conf"] for r in rows if r.get("conf") is not None]
    return sum(vals) / len(vals) if vals else float("nan")


def metric_summary(rows: list[dict], error_col: str) -> dict:
    valid = [r for r in rows if r.get("conf") is not None]
    return {
        "n": len(valid),
        "mean_conf": mean_conf(valid),
        "ece": ece(valid, error_col),
        "mismatch_at_0_9": sum(1 for r in valid if r["conf"] > 0.9 and int(r.get(error_col, 0)) == 1) / len(valid) if valid else float("nan"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/models.yaml")
    ap.add_argument("--input", default="runs/aggregated/dataframe.csv")
    ap.add_argument("--outdir", default="runs/aggregated/parse_audit")
    ap.add_argument("--error_col", default=None)
    ap.add_argument("--min_clean_subset", type=int, default=30)
    args = ap.parse_args()

    cfg = load_config(args.config)
    error_col = args.error_col or cfg.get("global", {}).get("mismatch_error_col", "error_within_model_q20")
    rows = load_dataframe_rows(args.input)
    grouped = group_by_model(rows)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    payload = {"config": {"input": args.input, "error_col": error_col, "min_clean_subset": args.min_clean_subset}, "models": {}}

    for model, model_rows in sorted(grouped.items()):
        warning_rows = [r for r in model_rows if r["warning_tokens"]]
        clean_rows = [r for r in model_rows if not r["warning_tokens"]]
        repaired_rows = [r for r in model_rows if r["repair_tokens"]]
        fallback_rows = [r for r in model_rows if r["fallback_tokens"]]
        translation_warning_rows = [r for r in model_rows if r["translation_tokens"]]
        confidence_warning_rows = [r for r in model_rows if r["confidence_tokens"]]
        both_warning_rows = [r for r in model_rows if r["translation_tokens"] and r["confidence_tokens"]]

        token_counter = Counter(token for r in warning_rows for token in r["warning_tokens"])
        clean_summary = metric_summary(clean_rows, error_col) if len(clean_rows) >= args.min_clean_subset else None
        all_summary = metric_summary(model_rows, error_col)

        summary_row = {
            "model": model,
            "n_total": len(model_rows),
            "n_warning_rows": len(warning_rows),
            "warning_rate": rate(len(warning_rows), len(model_rows)),
            "n_repaired_rows": len(repaired_rows),
            "n_fallback_rows": len(fallback_rows),
            "n_translation_warning_rows": len(translation_warning_rows),
            "n_confidence_warning_rows": len(confidence_warning_rows),
            "n_both_warning_rows": len(both_warning_rows),
            "mean_conf_clean": mean_conf(clean_rows),
            "mean_conf_warning": mean_conf(warning_rows),
            "clean_subset_stable": int(clean_summary is not None),
            "ece_all": all_summary["ece"],
            "ece_clean": clean_summary["ece"] if clean_summary else float("nan"),
            "mismatch_all": all_summary["mismatch_at_0_9"],
            "mismatch_clean": clean_summary["mismatch_at_0_9"] if clean_summary else float("nan"),
            "top_warning_token": token_counter.most_common(1)[0][0] if token_counter else "none",
        }
        summary_rows.append(summary_row)
        payload["models"][model] = {
            "summary": summary_row,
            "warning_token_counts": dict(token_counter),
            "all_rows_metrics": all_summary,
            "clean_rows_metrics": clean_summary,
            "warning_rows_metrics": metric_summary(warning_rows, error_col) if warning_rows else None,
            "notes": "Clean-subset metrics are omitted when the clean subset is smaller than min_clean_subset.",
        }

    compact_cols = [
        "model", "n_warning_rows", "warning_rate", "n_repaired_rows", "n_fallback_rows",
        "n_translation_warning_rows", "n_confidence_warning_rows", "n_both_warning_rows",
        "mean_conf_clean", "mean_conf_warning", "ece_all", "ece_clean", "mismatch_all", "mismatch_clean", "top_warning_token"
    ]
    write_csv(outdir / "parse_warning_audit_summary.csv", summary_rows, compact_cols + ["n_total", "clean_subset_stable"])
    json_dump(outdir / "parse_warning_audit_summary.json", payload)
    write_markdown_table(outdir / "parse_warning_audit_summary.md", "Parse-warning audit summary", summary_rows, compact_cols)
    write_tex_table(outdir / "parse_warning_audit_summary.tex", summary_rows, compact_cols)
    print(f"Wrote parse-warning audit artifacts to {outdir}")


if __name__ == "__main__":
    main()
