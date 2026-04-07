#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
CONFIG="${CONFIG:-configs/models.yaml}"
AGG_DF="${AGG_DF:-runs/aggregated/dataframe.csv}"
FIG_DIR="${FIG_DIR:-figures}"
EXAMPLES_OUT="${EXAMPLES_OUT:-paper/top_mismatch_examples.md}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: python binary not found: $PYTHON_BIN" >&2
  exit 1
fi

if [[ ! -f "$AGG_DF" ]]; then
  echo "ERROR: aggregated dataframe missing: $AGG_DF" >&2
  echo "Run scripts/regenerate_tables.sh first." >&2
  exit 1
fi

mkdir -p "$FIG_DIR" "$(dirname "$EXAMPLES_OUT")"

"$PYTHON_BIN" src/04_analysis_and_plots.py \
  --config "$CONFIG" \
  --input "$AGG_DF" \
  --outdir "$FIG_DIR" \
  --results runs/aggregated/results_by_model.json \
  --summary runs/aggregated/summary_table.csv \
  --meta runs/aggregated/meta.json \
  --examples "$EXAMPLES_OUT"

echo "Regenerated figures into $FIG_DIR from $AGG_DF."
