#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
SNAPSHOT_DIR="${SNAPSHOT_DIR:-runs/snapshots/20260228_000439/raw}"
CONFIG="${CONFIG:-configs/models.yaml}"
RUN_SUPPLEMENTARY=1
BUILD_MANUSCRIPT=1
INSTALL_DEPS=1

usage() {
  cat <<'USAGE'
Usage: bash scripts/reproduce_offline_artifact.sh [options]

Canonical offline artifact pipeline:
  1) install Python dependencies
  2) regenerate aggregate outputs from bundled raw snapshot
  3) regenerate figures + paper-facing mismatch markdown
  4) regenerate supplementary analyses
  5) attempt manuscript build if LaTeX tools are present

Options:
  --skip-install          Skip pip install
  --skip-supplementary    Skip supplementary analyses (05/06/07/08)
  --skip-manuscript       Skip manuscript build attempt
  --snapshot-dir PATH     Raw snapshot directory (default: runs/snapshots/20260228_000439/raw)
  --python BIN            Python executable (default: python3)
  --config PATH           Config file (default: configs/models.yaml)
  -h, --help              Show this help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-install) INSTALL_DEPS=0; shift ;;
    --skip-supplementary) RUN_SUPPLEMENTARY=0; shift ;;
    --skip-manuscript) BUILD_MANUSCRIPT=0; shift ;;
    --snapshot-dir) SNAPSHOT_DIR="$2"; shift 2 ;;
    --python) PYTHON_BIN="$2"; shift 2 ;;
    --config) CONFIG="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 1 ;;
  esac
done

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: python binary not found: $PYTHON_BIN" >&2
  exit 1
fi

if [[ ! -d "$SNAPSHOT_DIR" ]]; then
  echo "ERROR: snapshot directory not found: $SNAPSHOT_DIR" >&2
  exit 1
fi

if [[ "$INSTALL_DEPS" -eq 1 ]]; then
  "$PYTHON_BIN" -m pip install --root-user-action=ignore -U pip
  "$PYTHON_BIN" -m pip install --root-user-action=ignore -r requirements.txt
fi

if [[ "$RUN_SUPPLEMENTARY" -eq 1 ]]; then
  SNAPSHOT_DIR="$SNAPSHOT_DIR" PYTHON_BIN="$PYTHON_BIN" CONFIG="$CONFIG" bash scripts/generate_paper_assets.sh
else
  SNAPSHOT_DIR="$SNAPSHOT_DIR" PYTHON_BIN="$PYTHON_BIN" CONFIG="$CONFIG" bash scripts/regenerate_tables.sh
  PYTHON_BIN="$PYTHON_BIN" CONFIG="$CONFIG" bash scripts/regenerate_figures.sh
  "$PYTHON_BIN" tools/export_latex_tables.py
fi

if [[ "$BUILD_MANUSCRIPT" -eq 1 ]]; then
  if command -v latexmk >/dev/null 2>&1; then
    latexmk -pdf -interaction=nonstopmode revised_submission_with_new_results.tex
  else
    echo "NOTE: manuscript build skipped because latexmk is not installed in this environment." >&2
    echo "NOTE: bibliography metadata is split across references.bib (compatibility placeholder) and added_refs.bib (bundled keys)." >&2
  fi
fi

echo "Offline artifact pipeline completed."
