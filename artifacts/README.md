# Committed artifacts (artifact companion)

This repository is an artifact-only companion repository. It keeps release-relevant evidence under version control for transparency and easy review, but it does **not** include the final LaTeX paper source.

## What is committed

- `runs/aggregated/*`  
  Final aggregated dataset and metrics/features tables used for analysis.
- `paper/*` (selected markdown outputs)  
  Paper-facing markdown notes and generated examples used to accompany the artifact.

## What is not committed by default

- `figures/*` binary plots are regenerated locally and are not versioned.
- `runs/raw/*` full model API caches are ignored by default to reduce repository size and avoid redistributing potentially license-sensitive/raw text content.
- A compact debugging sample is kept in `runs/raw_sample/*`.
- Historical backup/debug files are archived under `archive/dev_old/` rather than left in the main release tree.

## Reproducibility

Running `bash run_repro.sh --clean` regenerates all generated outputs from source scripts and config.
