# Confidence–Difficulty Mismatch in MT Evaluation

This repository is packaged as a **reviewer artifact** for the paper manuscript in `revised_submission_with_new_results.tex`.

## Quick start (offline, recommended)

```bash
bash scripts/reproduce_offline_artifact.sh --skip-manuscript
```

This command regenerates aggregated outputs, figures, supplementary artifacts, manuscript-facing LaTeX tables, and runs consistency checks using only bundled snapshot data.

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
