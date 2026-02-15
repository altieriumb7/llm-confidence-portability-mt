# Committed artifacts (paper evidence)

This repository intentionally keeps final paper-facing outputs under version control for transparency and easy review.

## What is committed

- `runs/aggregated/*`  
  Final aggregated dataset and metrics/features tables used for analysis.
- `figures/*`  
  Plots used in the paper (generated locally; binary outputs are not versioned).
- `paper/*` (selected generated outputs)  
  Paper-facing markdown artifacts, including top mismatch examples.

## What is not committed by default

- `runs/raw/*` full model API caches are ignored by default to reduce repository size and avoid redistributing potentially license-sensitive/raw text content.
- A compact debugging sample is kept in `runs/raw_sample/*`.

## Reproducibility

Running `bash run_repro.sh --clean` regenerates all generated outputs from source scripts and config.
