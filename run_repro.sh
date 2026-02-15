#!/usr/bin/env bash
set -euo pipefail

# ----------------------------
# Reproducible end-to-end runner
# ----------------------------
# Usage examples:
#   bash run_repro.sh --clean
#   bash run_repro.sh --clean --max-samples 10
#   bash run_repro.sh --providers openai --max-samples 50
#   bash run_repro.sh --clean --step2-bg
#
# Notes for reviewers:
# - Put API keys in environment variables, or create a local .env (NOT committed):
#     OPENAI_API_KEY=...
#     ANTHROPIC_API_KEY=...
#     GEMINI_API_KEY=...
# - If a provider key is missing, the pipeline may skip that provider depending on implementation.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

CONFIG="configs/models.yaml"
CLEAN=0
MAX_SAMPLES=""
PROVIDERS=""
MODE="all"           # all | step1 | step2 | step3 | step4
STEP2_BG=0           # run step2 via nohup in background
VENV_DIR=".venv"

usage() {
  cat <<EOF
Usage: bash run_repro.sh [options]

Options:
  --config PATH           Path to config YAML (default: ${CONFIG})
  --clean                 Remove generated outputs and cached runs (start from 0)
  --max-samples N         Limit Step 2 to N samples (useful for smoke tests)
  --providers LIST        Comma-separated providers for Step 2 (e.g. openai,anthropic,gemini)
  --mode MODE             all | step1 | step2 | step3 | step4  (default: all)
  --step2-bg              Run Step 2 in background (nohup), logs to runs/logs/step2.log
  -h, --help              Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config) CONFIG="$2"; shift 2 ;;
    --clean) CLEAN=1; shift ;;
    --max-samples) MAX_SAMPLES="$2"; shift 2 ;;
    --providers) PROVIDERS="$2"; shift 2 ;;
    --mode) MODE="$2"; shift 2 ;;
    --step2-bg) STEP2_BG=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1"; usage; exit 1 ;;
  esac
done

mkdir -p runs/logs

# Load local .env if present (do NOT commit it)
if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

# Create venv if missing, then activate (Linux/macOS bash)
if [[ ! -d "${VENV_DIR}" ]]; then
  python -m venv "${VENV_DIR}"
fi
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

python -m pip install -U pip >/dev/null
pip install -r requirements.txt >/dev/null

echo "== Environment =="
python --version
pip --version

# Optional: check n in YAML (warn if not 500)
python - <<'PY' || true
import sys
try:
    import yaml
except Exception:
    print("WARN: PyYAML not available; skipping config check.")
    sys.exit(0)
cfg_path = sys.argv[1] if len(sys.argv) > 1 else "configs/models.yaml"
with open(cfg_path, "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f) or {}
g = cfg.get("global", {}) or {}
n = g.get("n", None)
print(f"== Config check == global.n = {n!r} (set to 500 for the full run)")
PY "$CONFIG"

if [[ "$CLEAN" -eq 1 ]]; then
  echo "== CLEAN: removing generated artifacts =="
  rm -f data/wmt_sample.jsonl || true
  rm -rf runs/raw runs/aggregated figures || true
  rm -f paper/top_mismatch_examples.md || true
  # keep runs/logs but clear its contents
  rm -f runs/logs/*.log || true
fi

run_step1() {
  echo "== Step 1: build dataset =="
  python src/01_make_dataset.py --config "$CONFIG" | tee runs/logs/step1.log
  echo "Dataset lines:"
  wc -l data/wmt_sample.jsonl || true
}

run_step2() {
  echo "== Step 2: translate + confidence (APIs) =="
  mkdir -p runs/raw

  CMD=(python src/02_translate_and_confidence.py
        --config "$CONFIG"
        --input data/wmt_sample.jsonl
        --outdir runs/raw)

  if [[ -n "$MAX_SAMPLES" ]]; then
    CMD+=(--max_samples "$MAX_SAMPLES")
  fi
  if [[ -n "$PROVIDERS" ]]; then
    CMD+=(--providers "$PROVIDERS")
  fi

  echo "Command: ${CMD[*]}"

  if [[ "$STEP2_BG" -eq 1 ]]; then
    echo "Running Step 2 in background. Log: runs/logs/step2.log"
    nohup "${CMD[@]}" > runs/logs/step2.log 2>&1 &
    disown || true
    echo "Tail with: tail -f runs/logs/step2.log"
  else
    "${CMD[@]}" 2>&1 | tee runs/logs/step2.log
  fi
}

run_step3() {
  echo "== Step 3: features + metrics =="
  mkdir -p runs/aggregated
  python src/03_features_and_metrics.py \
    --config "$CONFIG" \
    --input_dir runs/raw \
    --output runs/aggregated/dataframe.csv \
    | tee runs/logs/step3.log
}

run_step4() {
  echo "== Step 4: analysis + outputs =="
  mkdir -p figures
  python src/04_analysis_and_plots.py \
    --config "$CONFIG" \
    --input runs/aggregated/dataframe.csv \
    --outdir figures \
    --results runs/aggregated/results_by_model.json \
    --summary runs/aggregated/summary_table.csv \
    --examples paper/top_mismatch_examples.md \
    | tee runs/logs/step4.log

  echo "== Outputs =="
  ls -lah runs/aggregated || true
  ls -lah figures || true
  ls -lah paper/top_mismatch_examples.md || true
}

case "$MODE" in
  all)
    run_step1
    run_step2
    # If step2-bg was used, stop here (reviewers can run step3/4 after step2 finishes)
    if [[ "$STEP2_BG" -eq 1 ]]; then
      echo "Step 2 is running in background. When finished, run:"
      echo "  bash run_repro.sh --mode step3"
      echo "  bash run_repro.sh --mode step4"
      exit 0
    fi
    run_step3
    run_step4
    ;;
  step1) run_step1 ;;
  step2) run_step2 ;;
  step3) run_step3 ;;
  step4) run_step4 ;;
  *) echo "Unknown --mode: $MODE"; usage; exit 1 ;;
esac

echo "✅ Done."
