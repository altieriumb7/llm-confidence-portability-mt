#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TEX_MAIN="${TEX_MAIN:-revised_submission_with_new_results.tex}"
BUILD_DIR="${BUILD_DIR:-.}"

if [[ ! -f "$TEX_MAIN" ]]; then
  echo "ERROR: TeX entrypoint not found: $TEX_MAIN" >&2
  exit 1
fi

if ! command -v latexmk >/dev/null 2>&1; then
  echo "ERROR: latexmk is required to build PDF. Install TeX Live/MacTeX (with latexmk)." >&2
  exit 1
fi

# NOTE: This repository snapshot does not include the full bibliography inputs
# needed for guaranteed final-reference resolution in every environment.
# See paper/TODO_missing_bibliography.md for current limitations.

echo "[build_pdf] building manuscript PDF from $TEX_MAIN ..."
latexmk -pdf -interaction=nonstopmode -output-directory="$BUILD_DIR" "$TEX_MAIN"

echo "[build_pdf] done (expected output: $BUILD_DIR/$(basename "${TEX_MAIN%.tex}.pdf"))."
