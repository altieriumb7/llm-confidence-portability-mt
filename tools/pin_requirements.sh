#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VENV_DIR=".venv-lock"

rm -rf "$VENV_DIR"
python -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install -U pip
pip install -r requirements.txt
pip freeze > requirements.lock

deactivate
rm -rf "$VENV_DIR"

echo "Wrote requirements.lock"
