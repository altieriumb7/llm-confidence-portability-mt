#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TEX_MAIN="${TEX_MAIN:-revised_submission_with_new_results.tex}"
BUILD_DIR="${BUILD_DIR:-.}"
PDF_ENGINE="${PDF_ENGINE:-auto}"

if [[ ! -f "$TEX_MAIN" ]]; then
  echo "ERROR: TeX entrypoint not found: $TEX_MAIN" >&2
  exit 1
fi

choose_engine() {
  case "$PDF_ENGINE" in
    auto)
      if command -v latexmk >/dev/null 2>&1; then
        echo "latexmk"
      elif command -v tectonic >/dev/null 2>&1; then
        echo "tectonic"
      else
        return 1
      fi
      ;;
    latexmk|tectonic)
      if command -v "$PDF_ENGINE" >/dev/null 2>&1; then
        echo "$PDF_ENGINE"
      else
        return 1
      fi
      ;;
    *)
      echo "ERROR: unsupported PDF_ENGINE=$PDF_ENGINE (expected: auto, latexmk, tectonic)." >&2
      exit 1
      ;;
  esac
}

ENGINE="$(choose_engine)" || {
  cat >&2 <<'EOF'
ERROR: no supported TeX PDF engine found.
Install one of:
  - latexmk (typically from TeX Live/MacTeX)
  - tectonic
You can also choose explicitly with: PDF_ENGINE=latexmk|tectonic bash scripts/build_pdf.sh
EOF
  exit 1
}

# NOTE: This repository snapshot does not include the full bibliography inputs
# needed for guaranteed final-reference resolution in every environment.
# See paper/TODO_missing_bibliography.md for current limitations.

echo "[build_pdf] building manuscript PDF from $TEX_MAIN using $ENGINE ..."
if [[ "$ENGINE" == "latexmk" ]]; then
  latexmk -pdf -interaction=nonstopmode -output-directory="$BUILD_DIR" "$TEX_MAIN"
else
  mkdir -p "$BUILD_DIR"
  tectonic --keep-logs --outdir "$BUILD_DIR" "$TEX_MAIN"
fi

echo "[build_pdf] done (expected output: $BUILD_DIR/$(basename "${TEX_MAIN%.tex}.pdf"))."
