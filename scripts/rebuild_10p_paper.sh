#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEX_FILE="${1:-revised_submission_with_new_results_10p.tex}"
cd "$ROOT_DIR"

if [[ ! -f "$TEX_FILE" ]]; then
  echo "[error] TeX file not found: $TEX_FILE" >&2
  exit 1
fi

base="${TEX_FILE%.tex}"

build_with_latexmk() {
  latexmk -pdf -interaction=nonstopmode -halt-on-error "$TEX_FILE"
}

build_with_pdflatex() {
  pdflatex -interaction=nonstopmode -halt-on-error "$TEX_FILE"
  bibtex "$base" || true
  pdflatex -interaction=nonstopmode -halt-on-error "$TEX_FILE"
  pdflatex -interaction=nonstopmode -halt-on-error "$TEX_FILE"
}

if command -v latexmk >/dev/null 2>&1; then
  echo "[info] Building with latexmk"
  build_with_latexmk
elif command -v pdflatex >/dev/null 2>&1; then
  echo "[info] Building with pdflatex fallback"
  build_with_pdflatex
else
  echo "[error] No TeX build tool found. Install latexmk or pdflatex." >&2
  exit 2
fi

PDF_FILE="${base}.pdf"
if [[ ! -f "$PDF_FILE" ]]; then
  echo "[error] Build finished but PDF not found: $PDF_FILE" >&2
  exit 3
fi

page_count=""
if command -v pdfinfo >/dev/null 2>&1; then
  page_count="$(pdfinfo "$PDF_FILE" | awk '/^Pages:/ {print $2}')"
else
  page_count="$(python - "$PDF_FILE" <<'PY'
import re,sys,zlib
pdf=open(sys.argv[1],'rb').read()
# Try to parse page count from trailer/catalog first
m=re.search(rb'/Count\s+(\d+)', pdf)
print(m.group(1).decode() if m else '')
PY
)"
fi

if [[ -n "$page_count" ]]; then
  echo "[info] Built $PDF_FILE ($page_count pages)"
  if [[ "$page_count" -le 10 ]]; then
    echo "[ok] Page limit satisfied (<=10)."
  else
    echo "[warn] Page limit exceeded (>10)."
  fi
else
  echo "[warn] Could not determine page count automatically."
fi
