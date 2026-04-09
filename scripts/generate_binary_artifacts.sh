#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
CONFIG="${CONFIG:-configs/models.yaml}"
WITH_PDF="${WITH_PDF:-0}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: python binary not found: $PYTHON_BIN" >&2
  exit 1
fi

echo "[1/2] Regenerating binary figure assets (.png/.pdf)..."
PYTHON_BIN="$PYTHON_BIN" CONFIG="$CONFIG" bash scripts/regenerate_figures.sh

if [[ "$WITH_PDF" == "1" ]]; then
  echo "[2/2] Building manuscript PDF..."
  if command -v latexmk >/dev/null 2>&1; then
    latexmk -pdf -interaction=nonstopmode revised_submission_with_new_results.tex
  else
    echo "WARNING: latexmk not available; skipping manuscript PDF build." >&2
  fi
else
  echo "[2/2] Skipping manuscript PDF build (set WITH_PDF=1 to enable)."
fi

echo "Done. Binary assets regenerated." 
