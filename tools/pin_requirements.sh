#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TMP_VENV=".venv.lock"
trap 'rm -rf "$TMP_VENV"' EXIT

python -m venv "$TMP_VENV"
source "$TMP_VENV/bin/activate"
python -m pip install --upgrade pip
pip install -r requirements.txt
pip freeze | sort > requirements.lock

echo "Wrote requirements.lock"
