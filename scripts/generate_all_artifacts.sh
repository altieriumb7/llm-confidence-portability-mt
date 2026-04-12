#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
CONFIG="${CONFIG:-configs/models.yaml}"
SNAPSHOT_DIR="${SNAPSHOT_DIR:-runs/snapshots/20260228_000439/raw}"
WITH_PDF="${WITH_PDF:-0}"

cat <<'MSG'
[generate_all_artifacts] Compatibility wrapper:
  - Regenerates manuscript-facing offline artifacts from the bundled snapshot
  - Optionally builds the manuscript PDF when WITH_PDF=1
MSG

SNAPSHOT_DIR="$SNAPSHOT_DIR" PYTHON_BIN="$PYTHON_BIN" CONFIG="$CONFIG" WITH_PDF="$WITH_PDF" \
  bash scripts/build_artifacts.sh
