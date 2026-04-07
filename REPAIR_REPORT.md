# Repair Report — PASS 1 (Audit and Source-of-Truth Lock)

Date: 2026-04-07 (UTC)

## 1) True paper entrypoint (locked)

- **Locked manuscript entrypoint:** `revised_submission_with_new_results.tex`.
- Rationale: it is the only manuscript `.tex` file present in the repository root, and it contains the full paper structure (abstract, methods, results, figures, discussion, appendix references).
- Audit note: repository `README.md` currently claims a `main.tex` entrypoint, but `main.tex` is not present in this repository.

## 2) Authoritative bundled raw snapshot (locked)

- **Locked authoritative snapshot:** `runs/snapshots/20260228_000439/raw/*.jsonl`.
- Selection rule used in this audit:
  1. prefer bundled in-repo raw snapshot over derived outputs;
  2. require complete multi-model coverage;
  3. require non-empty per-model files;
  4. choose the latest timestamp among complete snapshots.
- Completeness check summary:
  - `runs/snapshots/20260228_000439/raw/` contains 8 model files, each with 500 lines.
  - Earlier snapshots include incomplete or inconsistent cases (e.g., `20260226_200056` has Gemini Pro at 488 lines; `20260227_235509` has Gemini Flash at 511 lines).
- Lock decision: all paper/code synchronization in later passes must be grounded in this raw snapshot (or explicitly justified if a different bundled raw source is required).


## 2.1) Snapshot selection tie-break note

- Another bundled snapshot (`runs/snapshots/20260228_000109/raw/*.jsonl`) is also complete at 8x500.
- Tie-break policy used for PASS 1 lock: choose the latest complete bundled snapshot by timestamp.
- Therefore the lock remains `20260228_000439`.

## 3) Stale / empty derived artifacts identified

The following currently committed derived outputs are stale/empty relative to the authoritative raw snapshot and must not be treated as evidence:

- `runs/aggregated/dataframe.csv` (header-only, 0 rows)
- `runs/aggregated/summary_table.csv` (header-only, 0 rows)
- `runs/aggregated/meta.json` (`n: 0`, empty providers/models)
- `runs/aggregated/results_by_model.json` (empty object)
- `runs/aggregated/calibration/calibration_summary.csv` (header-only, 0 rows)
- `runs/aggregated/calibration/calibration_summary.json` (`models: {}`)
- `runs/aggregated/metric_robustness/metric_robustness_summary.csv` (header-only, 0 rows)
- `runs/aggregated/metric_robustness/metric_robustness_summary.json` (`models: {}`)
- `runs/aggregated/selective_analysis/selective_model_summary.csv` (header-only, 0 rows)
- `runs/aggregated/selective_analysis/selective_threshold_summary.csv` (header-only, 0 rows)
- `runs/aggregated/selective_analysis/selective_threshold_summary.json` (`models: {}`)
- `runs/aggregated/parse_audit/parse_warning_audit_summary.csv` (header-only, 0 rows)
- `runs/aggregated/parse_audit/parse_warning_audit_summary.json` (`models: {}`)
- `runs/aggregated/secondary_metric/secondary_metric_summary.csv` (header-only, 0 rows)
- `runs/aggregated/secondary_metric/secondary_metric_scores.csv` (header-only, 0 rows)
- `runs/aggregated/secondary_metric/secondary_metric_summary.json` (`rows: []`)
- `runs/aggregated/secondary_metric/secondary_metric_scores.json` (`rows: []`)
- `runs/aggregated/secondary_metric/secondary_metric_meta.json` (`n_rows: 0`)

Additional manuscript-side mismatch discovered in this audit (to be fixed in later passes, not now):

- `revised_submission_with_new_results.tex` inputs missing table files:
  - `tables/summary`
  - `tables/corr`
  - `tables/calibration`
  - `tables/metric_robustness`
  - `tables/robustness`

## 4) Files that must be regenerated in PASS 2 (code-side only)

Regenerate from `runs/snapshots/20260228_000439/raw/`:

- Core aggregates:
  - `runs/aggregated/dataframe.csv`
  - `runs/aggregated/results_by_model.json`
  - `runs/aggregated/summary_table.csv`
  - `runs/aggregated/meta.json`
- Calibration outputs:
  - `runs/aggregated/calibration/calibration_summary.csv`
  - `runs/aggregated/calibration/calibration_summary.json`
- Selective analysis outputs:
  - `runs/aggregated/selective_analysis/selective_model_summary.csv`
  - `runs/aggregated/selective_analysis/selective_threshold_summary.csv`
  - `runs/aggregated/selective_analysis/selective_threshold_summary.json`
- Parse-audit outputs:
  - `runs/aggregated/parse_audit/parse_warning_audit_summary.csv`
  - `runs/aggregated/parse_audit/parse_warning_audit_summary.json`
- Secondary metric + robustness outputs:
  - `runs/aggregated/secondary_metric/secondary_metric_scores.csv`
  - `runs/aggregated/secondary_metric/secondary_metric_scores.json`
  - `runs/aggregated/secondary_metric/secondary_metric_summary.csv`
  - `runs/aggregated/secondary_metric/secondary_metric_summary.json`
  - `runs/aggregated/secondary_metric/secondary_metric_meta.json`
  - `runs/aggregated/metric_robustness/metric_robustness_summary.csv`
  - `runs/aggregated/metric_robustness/metric_robustness_summary.json`

## 5) Guardrails locked for remaining passes

- Do not treat any empty/header-only aggregated files as valid evidence.
- Prefer authoritative bundled raw snapshot over stale aggregated artifacts.
- If a manuscript claim cannot be supported by regenerated outputs from bundled raw materials, downgrade or remove that claim.
- PASS 2 must also remove silent toy-data fallback behavior and fail loudly when expected raw inputs are absent.
