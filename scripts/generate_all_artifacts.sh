#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "[1/2] Regenerating aggregate/table artifacts from bundled snapshot..."
bash scripts/regenerate_tables.sh

echo "[2/2] Regenerating figures and paper-facing examples..."
bash scripts/regenerate_figures.sh

echo "Done. Artifacts refreshed under runs/aggregated/, figures/, and paper/."
