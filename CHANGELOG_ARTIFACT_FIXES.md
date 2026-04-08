# CHANGELOG: Artifact Pipeline Technical Fixes

## What changed
- Standardized mismatch threshold semantics across analysis paths to strict `confidence > tau` (not `>=`).
- Updated calibration threshold scan coverage to use the same strict acceptance rule (`conf_after > threshold`).
- Expanded parse-warning audit with strict raw-preview validation against the bundled snapshot:
  - detects invalid/truncated JSON snippets,
  - detects trailing text after parsed JSON,
  - detects schema/key/value mismatches for expected translation/confidence keys,
  - reports malformed raw rows that previously had no parse warnings.
- Added deterministic regression assertions for malformed preview cases in `tools/test_parse.py`.
- Hardened `tools/consistency_check.py` from wiring-only checks to cross-artifact metric checks across:
  - generated CSV/JSON summaries,
  - manuscript-facing LaTeX tables in `tables/`,
  - selective-analysis exported mismatch@0.9 values.
- Added cleanup steps before regenerating aggregate/supplementary artifacts to reduce stale-file risk.
- Regenerated offline artifacts from `runs/snapshots/20260228_000439/raw`.

## Why it changed
- Mixed `>`/`>=` thresholding produced technically inconsistent operating-point definitions.
- Previous parse-warning audit relied too much on existing warning tokens and missed malformed-but-unflagged outputs.
- Consistency checks needed to validate numeric agreement (not just file existence/wiring) for manuscript-facing outputs.
- Stale generated files can silently conflict with current source and weaken reproducibility claims.

## Outputs that changed
- Code:
  - `src/05_calibration_analysis.py`
  - `src/08_parse_warning_audit.py`
  - `src/utils/analysis_helpers.py`
  - `tools/consistency_check.py`
  - `tools/test_parse.py`
  - `scripts/regenerate_tables.sh`
  - `scripts/generate_paper_assets.sh`
- Regenerated artifacts (from bundled snapshot):
  - `runs/aggregated/dataframe.csv`
  - `runs/aggregated/results_by_model.json`
  - `runs/aggregated/summary_table.csv`
  - `runs/aggregated/meta.json`
  - `runs/aggregated/calibration/*`
  - `runs/aggregated/selective_analysis/*`
  - `runs/aggregated/parse_audit/*`
  - `runs/aggregated/secondary_metric/*`
  - `runs/aggregated/metric_robustness/*`
  - `tables/*.tex`
  - figures in `figures/`

## Headline conclusions
- The central paper conclusion remains stable: confidence operating points are not portable across providers under a shared threshold.
- Numerical values in threshold-sensitive supplementary outputs are now definition-consistent (`>` only), and parse-audit reporting is stricter/more complete.
