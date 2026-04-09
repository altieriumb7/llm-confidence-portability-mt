import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from utils.analysis_helpers import load_dataframe_rows, write_csv


LABELS = {
    "semantic_error": "clear semantic error",
    "acceptable_paraphrase": "acceptable paraphrase",
    "metric_artifact_or_unclear": "metric artifact / unclear",
}


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _load_annotations(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for fp in sorted(path.glob("*.csv")):
        with open(fp, "r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                row["__file"] = fp.name
                rows.append(row)
    return rows


def _annotation_key(row: dict) -> str:
    return f"{row.get('provider','')}::{row.get('model_id','')}::{row.get('id','')}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="runs/aggregated/dataframe.csv")
    ap.add_argument("--outdir", default="runs/aggregated/semantic_audit")
    ap.add_argument("--annotations_dir", default="runs/annotations/semantic_audit")
    ap.add_argument("--tau", type=float, default=0.9)
    ap.add_argument("--sample_size", type=int, default=48)
    ap.add_argument("--min_per_provider", type=int, default=12)
    ap.add_argument("--max_per_bucket", type=int, default=12)
    args = ap.parse_args()

    rows = load_dataframe_rows(args.input)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # High-confidence mismatch cases under the paper's primary operational definition.
    candidates = [
        row
        for row in rows
        if row.get("conf") is not None and row.get("conf") >= args.tau and int(row.get("error_within_model_q20", 0)) == 1
    ]

    # Deterministic ranking by mismatch severity: prioritize higher confidence and lower chrF.
    candidates = sorted(
        candidates,
        key=lambda row: (
            -_safe_float(row.get("conf"), 0.0),
            _safe_float(row.get("chrf"), 0.0),
            row.get("provider", ""),
            row.get("model_id", ""),
            int(_safe_float(row.get("id"), 0)),
        ),
    )

    providers = sorted({row.get("provider", "unknown") for row in candidates})
    buckets = ["Q1", "Q2", "Q3", "Q4"]

    by_provider = defaultdict(list)
    for row in candidates:
        by_provider[row.get("provider", "unknown")].append(row)

    sample_keys = set()
    sample_rows = []

    # First pass: guarantee multi-provider coverage.
    for provider in providers:
        provider_rows = by_provider[provider]
        for row in provider_rows[: args.min_per_provider]:
            key = _annotation_key(row)
            if key not in sample_keys:
                sample_keys.add(key)
                sample_rows.append(row)

    # Second pass: fill while balancing complexity quartiles.
    by_bucket = defaultdict(list)
    for row in candidates:
        by_bucket[row.get("difficulty_bucket", "")].append(row)

    bucket_counts = Counter(row.get("difficulty_bucket", "") for row in sample_rows)
    provider_counts = Counter(row.get("provider", "") for row in sample_rows)

    target_size = min(args.sample_size, len(candidates))
    for bucket in buckets:
        for row in by_bucket.get(bucket, []):
            if len(sample_rows) >= target_size:
                break
            key = _annotation_key(row)
            if key in sample_keys:
                continue
            provider = row.get("provider", "")
            if bucket_counts[bucket] >= args.max_per_bucket:
                continue
            # Keep provider mix from collapsing to one provider in fill stage.
            if provider_counts[provider] > max(1, target_size // max(1, len(providers))) + 4:
                continue
            sample_keys.add(key)
            sample_rows.append(row)
            bucket_counts[bucket] += 1
            provider_counts[provider] += 1

    # Final fill if still short.
    for row in candidates:
        if len(sample_rows) >= target_size:
            break
        key = _annotation_key(row)
        if key in sample_keys:
            continue
        sample_keys.add(key)
        sample_rows.append(row)

    export_cols = [
        "id",
        "provider",
        "model_id",
        "difficulty_bucket",
        "src",
        "ref",
        "hyp",
        "conf",
        "chrf",
        "bleu",
        "error_within_model_q20",
        "parse_warnings",
    ]

    all_candidate_rows = [{k: row.get(k, "") for k in export_cols} for row in candidates]
    sampled_export_rows = [{k: row.get(k, "") for k in export_cols} for row in sample_rows]
    template_rows = []
    for row in sampled_export_rows:
        enriched = dict(row)
        enriched["audit_label"] = ""
        enriched["annotator_id"] = ""
        enriched["notes"] = ""
        template_rows.append(enriched)

    write_csv(outdir / "semantic_audit_candidates_all.csv", all_candidate_rows, export_cols)
    write_csv(outdir / "semantic_audit_sample.csv", sampled_export_rows, export_cols)
    write_csv(
        outdir / "semantic_audit_annotation_template.csv",
        template_rows,
        export_cols + ["audit_label", "annotator_id", "notes"],
    )

    guide = f"""# Semantic audit annotation guide

This file accompanies `semantic_audit_sample.csv` and `semantic_audit_annotation_template.csv`.

## Scope
- This audit is a deterministic review scaffold for high-confidence mismatch cases.
- It is **not** a replacement for the paper's main chrF-based operational label.
- In this bundle, examples are selected with:
  - `confidence >= {args.tau}`
  - `error_within_model_q20 == 1` (bottom-20% chrF within each model)

## Labels
Use exactly one `audit_label` per row:
1. `semantic_error`: clear meaning error (wrong fact/entity/polarity, omitted crucial content, hallucinated content).
2. `acceptable_paraphrase`: translation is semantically acceptable despite lower overlap.
3. `metric_artifact_or_unclear`: cannot confidently assign semantic error/paraphrase, or metric disagreement due to ambiguity/style.

## Process
1. Read source (`src`), reference (`ref`), and hypothesis (`hyp`).
2. Ignore the model confidence value while deciding the semantic label.
3. Enter `audit_label`, optional `notes`, and your `annotator_id`.

## Aggregation
- Place completed CSV files in `runs/annotations/semantic_audit/`.
- Re-run:
  - `python3 src/09_semantic_audit.py`
- The script will aggregate provided labels into summary outputs.
"""
    (outdir / "annotation_guide.md").write_text(guide, encoding="utf-8")

    annotation_rows = _load_annotations(Path(args.annotations_dir))
    sample_key_set = {_annotation_key(r) for r in sample_rows}

    valid_annotations = []
    for row in annotation_rows:
        key = _annotation_key(row)
        label = str(row.get("audit_label", "")).strip()
        if key in sample_key_set and label in LABELS:
            valid_annotations.append({**row, "_key": key})

    by_label = Counter(row["audit_label"] for row in valid_annotations)
    by_provider_labels = defaultdict(Counter)
    for row in valid_annotations:
        by_provider_labels[row.get("provider", "unknown")][row["audit_label"]] += 1

    summary = {
        "config": {
            "tau": args.tau,
            "sample_size": args.sample_size,
            "min_per_provider": args.min_per_provider,
            "max_per_bucket": args.max_per_bucket,
        },
        "counts": {
            "n_total_rows": len(rows),
            "n_candidate_rows": len(candidates),
            "n_sample_rows": len(sample_rows),
            "n_annotation_files": len(list(Path(args.annotations_dir).glob("*.csv"))) if Path(args.annotations_dir).exists() else 0,
            "n_valid_annotations": len(valid_annotations),
        },
        "sample_distribution": {
            "providers": dict(Counter(row.get("provider", "unknown") for row in sample_rows)),
            "difficulty_buckets": dict(Counter(row.get("difficulty_bucket", "") for row in sample_rows)),
        },
        "labels": {
            "label_definitions": LABELS,
            "overall_counts": dict(by_label),
            "provider_counts": {p: dict(c) for p, c in by_provider_labels.items()},
        },
    }

    (outdir / "semantic_audit_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    summary_rows = []
    for provider in sorted(summary["sample_distribution"]["providers"]):
        base = {
            "provider": provider,
            "sample_rows": summary["sample_distribution"]["providers"][provider],
            "valid_annotations": 0,
        }
        provider_label_counts = summary["labels"]["provider_counts"].get(provider, {})
        base["valid_annotations"] = int(sum(provider_label_counts.values()))
        for label in LABELS:
            base[label] = int(provider_label_counts.get(label, 0))
        summary_rows.append(base)

    write_csv(
        outdir / "semantic_audit_provider_summary.csv",
        summary_rows,
        ["provider", "sample_rows", "valid_annotations", *LABELS.keys()],
    )

    print(f"Wrote semantic audit artifacts to {outdir} (candidates={len(candidates)}, sample={len(sample_rows)}, annotations={len(valid_annotations)})")


if __name__ == "__main__":
    main()
