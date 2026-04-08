#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
CONFIG="${CONFIG:-configs/models.yaml}"
SNAPSHOT_DIR="${SNAPSHOT_DIR:-runs/snapshots/20260228_000439/raw}"

echo "[1/3] Regenerating aggregate/table artifacts from bundled snapshot..."
SNAPSHOT_DIR="$SNAPSHOT_DIR" PYTHON_BIN="$PYTHON_BIN" CONFIG="$CONFIG" bash scripts/regenerate_tables.sh

echo "[2/3] Regenerating figures and paper-facing examples..."
PYTHON_BIN="$PYTHON_BIN" CONFIG="$CONFIG" bash scripts/regenerate_figures.sh

echo "[3/3] Regenerating manuscript-facing LaTeX tables..."
"$PYTHON_BIN" tools/export_latex_tables.py

echo "Done. Artifacts refreshed under runs/aggregated/, figures/, paper/, and tables/."
