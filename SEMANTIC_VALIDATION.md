# Semantic validation layer (offline-compatible)

## What was added

This repository now includes a deterministic semantic-audit scaffold in `src/09_semantic_audit.py`.

The stage exports:
- `runs/aggregated/semantic_audit/semantic_audit_candidates_all.csv`
- `runs/aggregated/semantic_audit/semantic_audit_sample.csv`
- `runs/aggregated/semantic_audit/semantic_audit_annotation_template.csv`
- `runs/aggregated/semantic_audit/annotation_guide.md`
- `runs/aggregated/semantic_audit/semantic_audit_summary.json`
- `runs/aggregated/semantic_audit/semantic_audit_provider_summary.csv`

## Why this fallback was chosen

Priority-A learned metrics (COMET/xCOMET) are not fully offline-reproducible in the bundled artifact:
- `requirements.txt` does not include COMET packages.
- COMET/xCOMET checkpoints are not bundled in `runs/`.
- Standard COMET execution requires external checkpoint download.

Therefore, this artifact adds an explicit human-evaluation-style robustness layer instead of claiming unavailable learned-metric evidence.

## Selection protocol (deterministic)

The scaffold selects high-confidence operational mismatches using:
- `conf >= 0.9`
- `error_within_model_q20 == 1`

Selection is deterministic and prioritizes:
1. higher confidence,
2. lower chrF,
3. multi-provider coverage,
4. spread across source complexity quartiles (`Q1..Q4`).

Default sample target: 48 rows.

## Annotation schema

Three labels are defined:
- `semantic_error`
- `acceptable_paraphrase`
- `metric_artifact_or_unclear`

The annotation template includes model/provider metadata plus optional notes and annotator ID.

## How to add real labels

1. Copy `semantic_audit_annotation_template.csv` into `runs/annotations/semantic_audit/`.
2. Fill `audit_label` with one of the three labels above.
3. Re-run:
   ```bash
   python3 src/09_semantic_audit.py
   ```
4. Updated label counts appear in `semantic_audit_summary.json` and manuscript-facing `tables/semantic_audit.tex`.

## Scope and limitations

- The scaffold **does not invent labels**.
- The paper's main target remains chrF-based and unchanged.
- The semantic-audit layer improves validity by making targeted human validation reproducible, but semantic conclusions require actual annotations.
