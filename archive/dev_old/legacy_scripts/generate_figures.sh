#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
SNAPSHOT_DIR="${SNAPSHOT_DIR:-runs/snapshots/20260228_000439/raw}"
RAW_DIR="${RAW_DIR:-runs/raw}"
CONFIG="${CONFIG:-configs/models.yaml}"
AGG_DF="${AGG_DF:-runs/aggregated/dataframe.csv}"
FIG_DIR="${FIG_DIR:-figures}"
EXAMPLES_OUT="${EXAMPLES_OUT:-paper/top_mismatch_examples.md}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: python binary not found: $PYTHON_BIN" >&2
  exit 1
fi

if [[ ! -d "$SNAPSHOT_DIR" ]]; then
  echo "ERROR: snapshot directory not found: $SNAPSHOT_DIR" >&2
  exit 1
fi

mkdir -p "$RAW_DIR" "$(dirname "$AGG_DF")" "$FIG_DIR" "$(dirname "$EXAMPLES_OUT")"
find "$RAW_DIR" -maxdepth 1 -type f -name '*.jsonl' -delete

shopt -s nullglob
snapshot_files=("$SNAPSHOT_DIR"/*.jsonl)
shopt -u nullglob
if [[ ${#snapshot_files[@]} -eq 0 ]]; then
  echo "ERROR: no jsonl files found in $SNAPSHOT_DIR" >&2
  exit 1
fi

for fp in "${snapshot_files[@]}"; do
  cp -f "$fp" "$RAW_DIR/"
done

echo "Staged ${#snapshot_files[@]} raw files into $RAW_DIR"

"$PYTHON_BIN" src/03_features_and_metrics.py \
  --config "$CONFIG" \
  --input_dir "$RAW_DIR" \
  --output "$AGG_DF"

"$PYTHON_BIN" src/04_analysis_and_plots.py \
  --config "$CONFIG" \
  --input "$AGG_DF" \
  --outdir "$FIG_DIR" \
  --results runs/aggregated/results_by_model.json \
  --summary runs/aggregated/summary_table.csv \
  --meta runs/aggregated/meta.json \
  --examples "$EXAMPLES_OUT"

echo "Regenerated manuscript figures in $FIG_DIR from authoritative snapshot data."
