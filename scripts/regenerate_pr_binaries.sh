#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
CONFIG="${CONFIG:-configs/models.yaml}"
WITH_PDF="${WITH_PDF:-0}"

echo "[regenerate_pr_binaries] Regenerating figure binaries tracked by the paper..."
PYTHON_BIN="$PYTHON_BIN" CONFIG="$CONFIG" bash scripts/regenerate_figures.sh

if [[ "$WITH_PDF" == "1" ]]; then
  echo "[regenerate_pr_binaries] WITH_PDF=1 -> trying PDF build"
  bash scripts/build_pdf.sh
else
  echo "[regenerate_pr_binaries] Skipping manuscript PDF (set WITH_PDF=1 to enable)."
fi

echo "[regenerate_pr_binaries] Done."
