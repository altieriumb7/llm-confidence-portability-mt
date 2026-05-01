#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

VARIANT="10page"
SKIP_ASSETS=0
CONFIG="configs/paper.yaml"

usage() {
  cat <<'USAGE'
Usage: bash run_paper.sh [--variant 10page|long] [--skip-assets]

Builds canonical paper variants with explicit outputs:
  - 10page -> build/paper_10page.pdf (fails if pages > 10)
  - long   -> build/paper_long.pdf
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --variant) VARIANT="$2"; shift 2 ;;
    --skip-assets) SKIP_ASSETS=1; shift ;;
    --config) CONFIG="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ ! -f "$CONFIG" ]]; then
  echo "[error] Missing paper config: $CONFIG" >&2
  exit 1
fi

read_cfg() {
  python3 - "$CONFIG" "$VARIANT" <<'PY'
import sys, yaml
cfg=yaml.safe_load(open(sys.argv[1],encoding='utf-8'))
var=sys.argv[2]
if var not in cfg.get('variants',{}):
    raise SystemExit(f"Unknown variant '{var}'")
v=cfg['variants'][var]
print(v['tex'])
print(v['output_pdf'])
print(v.get('max_pages'))
PY
}

mapfile -t CFG < <(read_cfg)
TEX_FILE="${CFG[0]}"
OUT_PDF="${CFG[1]}"
MAX_PAGES="${CFG[2]}"

if [[ ! -f "$TEX_FILE" ]]; then
  echo "[error] Variant '$VARIANT' points to missing TeX entrypoint: $TEX_FILE" >&2
  exit 2
fi

if [[ "$SKIP_ASSETS" -ne 1 ]]; then
  bash scripts/generate_paper_assets.sh
fi

mkdir -p build

if ! command -v latexmk >/dev/null 2>&1; then
  echo "[error] latexmk is required to build paper variants." >&2
  exit 3
fi

BASE_NAME="$(basename "${TEX_FILE%.tex}")"
latexmk -pdf -interaction=nonstopmode -halt-on-error -output-directory=build "$TEX_FILE"

BUILT_PDF="build/${BASE_NAME}.pdf"
if [[ ! -f "$BUILT_PDF" ]]; then
  echo "[error] Expected built PDF not found: $BUILT_PDF" >&2
  exit 4
fi

cp "$BUILT_PDF" "$OUT_PDF"
echo "[info] Compiled source: $TEX_FILE"
echo "[info] Wrote PDF: $OUT_PDF"

PAGE_COUNT="$(pdfinfo "$OUT_PDF" | awk '/^Pages:/ {print $2}')"
echo "[info] Page count: ${PAGE_COUNT}"

if [[ "$MAX_PAGES" != "None" && "$MAX_PAGES" != "null" ]]; then
  if [[ "$PAGE_COUNT" -gt "$MAX_PAGES" ]]; then
    echo "[error] Page-limit violation: variant '$VARIANT' compiled from '$TEX_FILE' to '$OUT_PDF' with ${PAGE_COUNT} pages (max ${MAX_PAGES})." >&2
    exit 5
  fi
fi

echo "[ok] Build succeeded for variant '$VARIANT'."
