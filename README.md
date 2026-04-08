# Confidence–Difficulty Mismatch in MT Evaluation

This repository is the **reviewer-facing reproducibility artifact** for the MT confidence portability study.

## Canonical offline reproduction entrypoint

Use exactly one command:

```bash
bash scripts/reproduce_offline_artifact.sh
```

This authoritative pipeline now guarantees paper/repo synchronization by regenerating all manuscript-facing assets and running a hard consistency check.

## Local artifact build scripts (text-only workflow)

To regenerate generated artifacts locally (without committing binaries from Codex), use:

```bash
bash scripts/build_artifacts.sh
```

Optional manuscript PDF build:

```bash
WITH_PDF=1 bash scripts/build_artifacts.sh
```

If you only need figures:

```bash
bash scripts/build_figures.sh
```

If you only need the manuscript PDF:

```bash
bash scripts/build_pdf.sh
```

### Prerequisites
- Python 3 + dependencies from `requirements.txt`
- Bundled snapshot data at `runs/snapshots/20260228_000439/raw/*.jsonl`
- `latexmk` (only for PDF build)

### Generated artifact types and output locations
- Figures (`.png`, `.pdf`): `figures/` via `src/04_analysis_and_plots.py` (called by `scripts/regenerate_figures.sh` / `scripts/build_figures.sh`)
- Aggregated analysis artifacts (`.csv`, `.json`, `.md`, `.tex`): `runs/aggregated/` and `tables/` via `scripts/generate_paper_assets.sh`
- Manuscript PDF (`.pdf`): project root (or `BUILD_DIR`) via `scripts/build_pdf.sh`

### Known limitation
The snapshot does not include the full bibliography inputs needed to guarantee fully resolved references in every environment; see `paper/TODO_missing_bibliography.md`.

## Authoritative locations

- Environment setup: `requirements.txt`, `requirements.lock`
- Raw snapshot input (bundled): `runs/snapshots/20260228_000439/raw/*.jsonl`
- Aggregate outputs: `runs/aggregated/`
- Paper tables consumed by LaTeX (generated): `tables/*.tex`
- Paper figures (generated): `figures/*.pdf`, `figures/*.png`
- Paper-facing generated markdown examples: `paper/top_mismatch_examples.md`
- Manuscript entrypoint: `revised_submission_with_new_results.tex`

## Generated manuscript asset pipeline

- `scripts/generate_paper_assets.sh` regenerates:
  1. aggregate outputs from bundled snapshot
  2. figures and paper examples markdown
  3. supplementary analyses
  4. manuscript-facing LaTeX tables via `tools/export_latex_tables.py`
  5. alignment checks via `tools/consistency_check.py`

- `tools/export_latex_tables.py` is the only source of truth for:
  - `tables/summary.tex`
  - `tables/corr.tex`
  - `tables/robustness.tex`
  - `tables/calibration.tex`
  - `tables/metric_robustness.tex`

## Drift prevention

`tools/consistency_check.py` fails if regenerated manuscript-facing tables differ from committed `tables/*.tex`, or if manuscript-referenced generated assets are missing.

## Scope boundaries (offline vs API-required)

- Offline regeneration (fully supported from bundled snapshot):
  - `src/03_features_and_metrics.py`
  - `src/04_analysis_and_plots.py`
  - `src/05_calibration_analysis.py`
  - `src/07_selective_analysis.py`
  - `src/08_parse_warning_audit.py`
  - `src/05_secondary_metric.py`
  - `src/06_metric_robustness.py`

- API-required (not part of canonical offline reviewer path):
  - `src/02_translate_and_confidence.py`
  - orchestrated by `run_repro.sh --mode step2` or `--mode all`

## Bibliography/manuscript caveat

The manuscript cites `references.bib` and `added_refs.bib`, but only `added_refs.bib` is bundled in this repository. Therefore full bibliography resolution cannot be guaranteed from this snapshot alone.

See `paper/README.md` and `paper/TODO_missing_bibliography.md` for exact blocker details.
