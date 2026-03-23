import argparse
import csv
import importlib.util
import json
import statistics
from pathlib import Path

import sacrebleu

from utils.analysis_helpers import json_dump, load_dataframe_rows, quantile, write_csv, write_markdown_table, write_tex_table


SECONDARY_METRIC_FIELD = "secondary_metric_score"


def comet_available():
    return importlib.util.find_spec("comet") is not None


def run_comet(rows, model_name: str):
    from comet import download_model, load_from_checkpoint

    checkpoint = download_model(model_name)
    model = load_from_checkpoint(checkpoint)
    inputs = [{"src": r["src"], "mt": r["hyp"], "ref": r["ref"]} for r in rows]
    outputs = model.predict(inputs, batch_size=8, gpus=0)
    scores = outputs.scores if hasattr(outputs, "scores") else outputs[0]
    return [float(score) for score in scores], {
        "backend": "comet",
        "metric_label": f"COMET ({model_name})",
        "model": model_name,
        "is_fallback": False,
    }


def run_bleu_fallback(rows):
    scores = [float(r.get("bleu", 0.0)) for r in rows]
    return scores, {
        "backend": "bleu_fallback",
        "metric_label": "Sentence BLEU fallback",
        "reason": "COMET not installed; reused existing sentence BLEU scores as a conservative fallback secondary metric.",
        "is_fallback": True,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="runs/aggregated/dataframe.csv")
    ap.add_argument("--outdir", default="runs/aggregated/secondary_metric")
    ap.add_argument("--backend", choices=["auto", "comet", "fallback_bleu"], default="auto")
    ap.add_argument("--comet_model", default="Unbabel/wmt22-comet-da")
    ap.add_argument("--quantile", type=float, default=0.2)
    args = ap.parse_args()

    rows = load_dataframe_rows(args.input)
    if args.backend == "comet":
        if not comet_available():
            raise SystemExit("Requested --backend comet but the 'comet' package is not installed.")
        scores, meta = run_comet(rows, args.comet_model)
    elif args.backend == "auto":
        scores, meta = run_comet(rows, args.comet_model) if comet_available() else run_bleu_fallback(rows)
    else:
        scores, meta = run_bleu_fallback(rows)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    detail_rows = []
    by_model = {}
    for row, score in zip(rows, scores):
        label = row["model"]
        by_model.setdefault(label, []).append(score)
        detail_rows.append(
            {
                "id": row.get("id"),
                "provider": row.get("provider"),
                "model_id": row.get("model_id"),
                "secondary_metric_name": meta["backend"],
                "secondary_metric_label": meta["metric_label"],
                SECONDARY_METRIC_FIELD: score,
            }
        )

    summary_rows = []
    for label, vals in sorted(by_model.items()):
        threshold = quantile(vals, args.quantile)
        summary_rows.append(
            {
                "model": label,
                "secondary_metric_name": meta["backend"],
                "secondary_metric_label": meta["metric_label"],
                "secondary_metric_quantile": args.quantile,
                "secondary_error_threshold": threshold,
                "mean_secondary_metric": sum(vals) / len(vals),
                "median_secondary_metric": statistics.median(vals),
                "min_secondary_metric": min(vals),
                "max_secondary_metric": max(vals),
            }
        )

    write_csv(
        outdir / "secondary_metric_scores.csv",
        detail_rows,
        ["id", "provider", "model_id", "secondary_metric_name", "secondary_metric_label", SECONDARY_METRIC_FIELD],
    )
    write_csv(
        outdir / "secondary_metric_summary.csv",
        summary_rows,
        [
            "model",
            "secondary_metric_name",
            "secondary_metric_label",
            "secondary_metric_quantile",
            "secondary_error_threshold",
            "mean_secondary_metric",
            "median_secondary_metric",
            "min_secondary_metric",
            "max_secondary_metric",
        ],
    )
    json_dump(outdir / "secondary_metric_scores.json", {"meta": meta, "rows": detail_rows})
    json_dump(outdir / "secondary_metric_summary.json", {"meta": meta, "rows": summary_rows})
    write_markdown_table(
        outdir / "secondary_metric_summary.md",
        "Secondary metric summary",
        summary_rows,
        ["model", "secondary_metric_label", "secondary_error_threshold", "mean_secondary_metric", "median_secondary_metric"],
    )
    write_tex_table(
        outdir / "secondary_metric_summary.tex",
        summary_rows,
        ["model", "secondary_metric_label", "secondary_error_threshold", "mean_secondary_metric", "median_secondary_metric"],
    )

    meta["n_rows"] = len(rows)
    meta["secondary_metric_score_field"] = SECONDARY_METRIC_FIELD
    json_dump(outdir / "secondary_metric_meta.json", meta)
    print(f"Wrote secondary metric artifacts to {outdir} using backend={meta['backend']}")


if __name__ == "__main__":
    main()
