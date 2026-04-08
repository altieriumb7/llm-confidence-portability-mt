# Confidence–Difficulty Mismatch in MT Evaluation

This repository is packaged as a **reviewer artifact** for the paper manuscript in `revised_submission_with_new_results.tex`.

## Quick start (offline, recommended)

```bash
bash scripts/reproduce_offline_artifact.sh --skip-manuscript
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

## Optional commands

- Build manuscript PDF as well (requires LaTeX):
  ```bash
  bash scripts/reproduce_offline_artifact.sh
  ```
- Run all validation checks only:
  ```bash
  bash scripts/validate_artifact.sh
  ```
- Attempt full live/API pipeline (credentials required):
  ```bash
  bash run_repro.sh --mode all
  ```

## Core documentation

- Reviewer workflow and provenance map: `ARTIFACT_GUIDE.md`
- Reproducibility scope/status statement: `ARTIFACT_STATUS.md`
- Paper-specific build notes: `paper/README.md`

## What is bundled

- Raw offline snapshot: `runs/snapshots/20260228_000439/raw/*.jsonl`
- Regenerated aggregated outputs: `runs/aggregated/`
- Manuscript tables: `tables/*.tex`
- Manuscript figures: `figures/*`

## Environment

- Python dependencies: `requirements.txt`
- Optional containerized path: `Dockerfile`

## Important scope boundary

Live provider API calls (Step 2) are **not** reproducible from the zip alone and are expected to vary over time.
