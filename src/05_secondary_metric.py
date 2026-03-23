import argparse
import csv
import importlib.util
import json
import statistics
from pathlib import Path

import sacrebleu


def as_float(x, default=0.0):
    try:
        if x in (None, "", "nan"):
            return default
        return float(x)
    except Exception:
        return default


def comet_available():
    return importlib.util.find_spec("comet") is not None


def run_comet(rows, model_name: str):
    from comet import download_model, load_from_checkpoint

    checkpoint = download_model(model_name)
    model = load_from_checkpoint(checkpoint)
    inputs = [{"src": r["src"], "mt": r["hyp"], "ref": r["ref"]} for r in rows]
    outputs = model.predict(inputs, batch_size=8, gpus=0)
    scores = outputs.scores if hasattr(outputs, "scores") else outputs[0]
    return [float(s) for s in scores], {"backend": "comet", "model": model_name}


def run_bleu_fallback(rows):
    return [as_float(r.get("bleu"), 0.0) for r in rows], {
        "backend": "bleu_fallback",
        "reason": "COMET not installed; reused existing sentence BLEU scores as a conservative fallback secondary metric.",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="runs/aggregated/dataframe.csv")
    ap.add_argument("--outdir", default="runs/aggregated/secondary_metric")
    ap.add_argument("--backend", choices=["auto", "comet", "fallback_bleu"], default="auto")
    ap.add_argument("--comet_model", default="Unbabel/wmt22-comet-da")
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if args.backend == "comet":
        if not comet_available():
            raise SystemExit("Requested --backend comet but the 'comet' package is not installed.")
        scores, meta = run_comet(rows, args.comet_model)
    elif args.backend == "auto":
        if comet_available():
            scores, meta = run_comet(rows, args.comet_model)
        else:
            scores, meta = run_bleu_fallback(rows)
    else:
        scores, meta = run_bleu_fallback(rows)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    detail_rows = []
    by_model = {}
    for row, score in zip(rows, scores):
        label = f"{row.get('provider','unknown')}/{row.get('model_id','unknown')}"
        by_model.setdefault(label, []).append(score)
        detail_rows.append(
            {
                "id": row.get("id"),
                "provider": row.get("provider"),
                "model_id": row.get("model_id"),
                "secondary_metric_name": meta["backend"],
                "secondary_metric_score": score,
            }
        )

    with open(outdir / "secondary_metric_scores.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["id", "provider", "model_id", "secondary_metric_name", "secondary_metric_score"],
        )
        writer.writeheader()
        writer.writerows(detail_rows)

    summary = []
    for label, vals in sorted(by_model.items()):
        summary.append(
            {
                "model": label,
                "secondary_metric_name": meta["backend"],
                "mean_secondary_metric": sum(vals) / len(vals),
                "median_secondary_metric": statistics.median(vals),
                "min_secondary_metric": min(vals),
                "max_secondary_metric": max(vals),
            }
        )
    with open(outdir / "secondary_metric_summary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["model", "secondary_metric_name", "mean_secondary_metric", "median_secondary_metric", "min_secondary_metric", "max_secondary_metric"],
        )
        writer.writeheader()
        writer.writerows(summary)

    meta["n_rows"] = len(rows)
    (outdir / "secondary_metric_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Wrote secondary metric artifacts to {outdir} using backend={meta['backend']}")

if __name__ == "__main__":
    main()
