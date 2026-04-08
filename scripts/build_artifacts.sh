#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
CONFIG="${CONFIG:-configs/models.yaml}"
SNAPSHOT_DIR="${SNAPSHOT_DIR:-runs/snapshots/20260228_000439/raw}"
WITH_PDF="${WITH_PDF:-0}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: python binary not found: $PYTHON_BIN" >&2
  exit 1
fi

if [[ ! -d "$SNAPSHOT_DIR" ]]; then
  echo "ERROR: snapshot directory not found: $SNAPSHOT_DIR" >&2
  exit 1
fi

echo "[build_artifacts] regenerating offline paper artifacts from bundled snapshot..."
SNAPSHOT_DIR="$SNAPSHOT_DIR" PYTHON_BIN="$PYTHON_BIN" CONFIG="$CONFIG" bash scripts/generate_paper_assets.sh

if [[ "$WITH_PDF" == "1" ]]; then
  echo "[build_artifacts] WITH_PDF=1 -> building manuscript PDF"
  bash scripts/build_pdf.sh
else
  echo "[build_artifacts] skipping PDF build (set WITH_PDF=1 to enable)."
fi

echo "[build_artifacts] complete."
