#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
CONFIG="${CONFIG:-configs/models.yaml}"
SNAPSHOT_DIR="${SNAPSHOT_DIR:-runs/snapshots/20260228_000439/raw}"
AGG_DF="runs/aggregated/dataframe.csv"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: python binary not found: $PYTHON_BIN" >&2
  exit 1
fi

if [[ ! -d "$SNAPSHOT_DIR" ]]; then
  echo "ERROR: snapshot directory not found: $SNAPSHOT_DIR" >&2
  exit 1
fi

mkdir -p figures paper

if [[ ! -f "$AGG_DF" ]]; then
  echo "[build_figures] aggregated dataframe missing; regenerating tables/data first..."
  SNAPSHOT_DIR="$SNAPSHOT_DIR" PYTHON_BIN="$PYTHON_BIN" CONFIG="$CONFIG" bash scripts/regenerate_tables.sh
fi

echo "[build_figures] regenerating figure binaries and mismatch examples..."
PYTHON_BIN="$PYTHON_BIN" CONFIG="$CONFIG" bash scripts/regenerate_figures.sh

echo "[build_figures] done (outputs in figures/ and paper/top_mismatch_examples.md)."
