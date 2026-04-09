# Semantic audit annotation guide

This file accompanies `semantic_audit_sample.csv` and `semantic_audit_annotation_template.csv`.

## Scope
- This audit is a deterministic review scaffold for high-confidence mismatch cases.
- It is **not** a replacement for the paper's main chrF-based operational label.
- In this bundle, examples are selected with:
  - `confidence >= 0.9`
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
