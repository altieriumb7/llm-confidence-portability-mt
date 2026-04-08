#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: python binary not found: $PYTHON_BIN" >&2
  exit 1
fi

echo "[validate] parse regression checks"
"$PYTHON_BIN" tools/test_parse.py

echo "[validate] manuscript table drift check"
"$PYTHON_BIN" tools/export_latex_tables.py --check

echo "[validate] cross-artifact consistency check"
"$PYTHON_BIN" tools/consistency_check.py

echo "[validate] all checks passed"
