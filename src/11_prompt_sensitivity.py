import argparse
import csv
from pathlib import Path

from utils.analysis_helpers import json_dump, load_dataframe_rows, write_csv
from utils.common import load_config
from utils.prompt_variants import default_variant, list_variant_names


def _read_summary(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {row["model"]: row for row in rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/models.yaml")
    ap.add_argument("--baseline_summary", default="runs/aggregated/summary_table.csv")
    ap.add_argument("--variant_root", default="runs/prompt_variants")
    ap.add_argument("--outdir", default="runs/aggregated/prompt_sensitivity")
    args = ap.parse_args()

    cfg = load_config(args.config)
    variants = list_variant_names(cfg)
    baseline_variant = default_variant(cfg)

    baseline = _read_summary(Path(args.baseline_summary))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    status_rows = []
    comparison_rows = []

    for variant in variants:
        if variant == baseline_variant:
            status_rows.append({
                "prompt_variant": variant,
                "status": "available_baseline",
                "summary_path": args.baseline_summary,
                "n_models": len(baseline),
            })
            continue

        variant_summary = Path(args.variant_root) / variant / "aggregated" / "summary_table.csv"
        variant_rows = _read_summary(variant_summary)
        status_rows.append(
            {
                "prompt_variant": variant,
                "status": "available" if variant_rows else "missing_optional_live_run",
                "summary_path": str(variant_summary),
                "n_models": len(variant_rows),
            }
        )
        if not variant_rows:
            continue

        for model, base in baseline.items():
            other = variant_rows.get(model)
            if not other:
                continue
            comparison_rows.append(
                {
                    "prompt_variant": variant,
                    "model": model,
                    "delta_ece_within_model_q20": float(other["ece_within_model_q20"]) - float(base["ece_within_model_q20"]),
                    "delta_mismatch_rate_tau_0_9": float(other["mismatch_rate_overall_tau_0.9"]) - float(base["mismatch_rate_overall_tau_0.9"]),
                }
            )

    write_csv(outdir / "prompt_sensitivity_status.csv", status_rows, ["prompt_variant", "status", "summary_path", "n_models"])
    write_csv(
        outdir / "prompt_sensitivity_comparison.csv",
        comparison_rows,
        ["prompt_variant", "model", "delta_ece_within_model_q20", "delta_mismatch_rate_tau_0_9"],
    )

    json_dump(
        outdir / "prompt_sensitivity_status.json",
        {
            "default_prompt_variant": baseline_variant,
            "status_rows": status_rows,
            "comparison_rows": comparison_rows,
            "note": "Variants other than baseline require optional live reruns and are not fabricated in offline bundle.",
        },
    )

    manifest = {
        "default_prompt_variant": baseline_variant,
        "variants": variants,
        "expected_variant_output_pattern": "runs/prompt_variants/<variant>/aggregated/summary_table.csv",
    }
    json_dump(outdir / "prompt_sensitivity_manifest.json", manifest)
    print(f"Wrote prompt sensitivity status artifacts to {outdir}")


if __name__ == "__main__":
    main()
