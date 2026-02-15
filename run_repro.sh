#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

CLEAN=0
if [[ "${1:-}" == "--clean" ]]; then
  CLEAN=1
elif [[ $# -gt 0 ]]; then
  echo "Usage: bash run_repro.sh [--clean]" >&2
  exit 1
fi

if [[ $CLEAN -eq 1 ]]; then
  echo "[repro] Cleaning generated outputs..."
  rm -rf runs figures
  rm -f data/wmt_sample.jsonl paper/top_mismatch_examples.md
fi

# Load environment variables from .env if present.
if [[ -f .env ]]; then
  echo "[repro] Loading environment from .env"
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

# Ensure API keys exist for configured providers.
missing=()
[[ -n "${OPENAI_API_KEY:-}" ]] || missing+=("OPENAI_API_KEY")
[[ -n "${ANTHROPIC_API_KEY:-}" ]] || missing+=("ANTHROPIC_API_KEY")
if [[ -z "${GEMINI_API_KEY:-}" && -z "${GOOGLE_API_KEY:-}" ]]; then
  missing+=("GEMINI_API_KEY (or GOOGLE_API_KEY)")
fi
if (( ${#missing[@]} > 0 )); then
  echo "[repro][error] Missing API credentials: ${missing[*]}" >&2
  echo "[repro][error] Set them in your shell or create .env from .env.example and retry." >&2
  exit 1
fi

# Create/use virtual environment.
if [[ ! -d .venv ]]; then
  echo "[repro] Creating virtualenv in .venv"
  python -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
if [[ -f requirements.lock ]]; then
  echo "[repro] Installing dependencies from requirements.lock"
  pip install -r requirements.lock
else
  echo "[repro] Installing dependencies from requirements.txt"
  pip install -r requirements.txt
fi

mkdir -p runs/logs

run_step() {
  local name="$1"
  shift
  echo "[repro] Running ${name}..."
  "$@" 2>&1 | tee "runs/logs/${name}.log"
}

run_step step1_dataset python src/01_make_dataset.py \
  --config configs/models.yaml

run_step step2_translate_confidence python src/02_translate_and_confidence.py \
  --config configs/models.yaml \
  --input data/wmt_sample.jsonl \
  --outdir runs/raw

run_step step3_features_metrics python src/03_features_and_metrics.py \
  --config configs/models.yaml \
  --input_dir runs/raw \
  --output runs/aggregated/dataframe.csv

run_step step4_analysis_plots python src/04_analysis_and_plots.py \
  --config configs/models.yaml \
  --input runs/aggregated/dataframe.csv \
  --outdir figures \
  --results runs/aggregated/results_by_model.json \
  --summary runs/aggregated/summary_table.csv \
  --examples paper/top_mismatch_examples.md

echo "[repro] Done. Outputs in runs/aggregated/, figures/, paper/."
