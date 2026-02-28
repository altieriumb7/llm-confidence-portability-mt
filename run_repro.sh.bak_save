#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

CONFIG="configs/models.yaml"
CLEAN=0
MAX_SAMPLES=""
PROVIDERS=""
MODELS=""
MODE="all"          # all | step1 | step2 | step3 | step4
STEP2_BG=0
SKIP_STEP2=0

# Use system python (Vast.ai containers usually have python3)
PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  PYTHON="python"
fi
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "ERROR: python3/python not found in PATH." >&2
  exit 1
fi

log() {
  printf '\n[%s] %s\n' "$(date +"%Y-%m-%d %H:%M:%S")" "$*"
}

usage() {
  cat <<'USAGE'
Usage: bash run_repro.sh [options]

Options:
  --config PATH           Path to config YAML (default: configs/models.yaml)
  --clean                 Remove generated outputs before running
  --max_samples N         Limit Step 2 to N samples (smoke test)
  --providers LIST        Comma-separated providers for Step 2 (e.g. openai,anthropic)
  --models LIST           Comma-separated model IDs/labels for Step 2
  --mode MODE             all | step1 | step2 | step3 | step4 (default: all)
  --skip_step2            Skip Step 2 (useful for re-running Step 3/4)
  --step2-bg              Run Step 2 in background (nohup), logs to runs/logs/step2.log
  --python BIN            Python executable to use (default: python3; fallback: python)
  -h, --help              Show help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config) CONFIG="$2"; shift 2 ;;
    --clean) CLEAN=1; shift ;;
    --max-samples|--max_samples) MAX_SAMPLES="$2"; shift 2 ;;
    --providers) PROVIDERS="$2"; shift 2 ;;
    --models) MODELS="$2"; shift 2 ;;
    --mode) MODE="$2"; shift 2 ;;
    --skip_step2) SKIP_STEP2=1; shift ;;
    --step2-bg) STEP2_BG=1; shift ;;
    --python) PYTHON="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1"; usage; exit 1 ;;
  esac
done

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "ERROR: requested python '$PYTHON' not found in PATH." >&2
  exit 1
fi

if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

mkdir -p runs/logs
LOGFILE="runs/logs/repro_$(date +"%Y%m%d_%H%M%S").log"
exec > >(tee -a "$LOGFILE") 2>&1

log "Environment"
echo "Using: $PYTHON"
"$PYTHON" --version
"$PYTHON" -m pip -V || true

log "Installing dependencies (no venv)"
"$PYTHON" -m pip install --root-user-action=ignore -U pip
"$PYTHON" -m pip install --root-user-action=ignore -r requirements.txt

log "Config sanity check"
"$PYTHON" - "$CONFIG" <<'PY'
import sys
import yaml
cfg_path = sys.argv[1]
with open(cfg_path, "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f) or {}
print(f"global.n = {(cfg.get('global') or {}).get('n')!r}")
PY

if [[ "$CLEAN" -eq 1 ]]; then
  log "CLEAN: removing generated outputs"
  rm -f data/wmt_sample.jsonl
  rm -rf runs/raw runs/aggregated runs/logs figures
  rm -f paper/top_mismatch_examples.md
  rm -f paper/results_table.md paper/summary_table.md
fi

mkdir -p runs/logs

require_step2_keys() {
  local missing=()
  if [[ -z "${OPENAI_API_KEY:-}" ]]; then
    missing+=("OPENAI_API_KEY")
  fi
  if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
    missing+=("ANTHROPIC_API_KEY")
  fi
  if [[ -z "${GEMINI_API_KEY:-}" && -z "${GOOGLE_API_KEY:-}" ]]; then
    missing+=("GEMINI_API_KEY or GOOGLE_API_KEY")
  fi

  if (( ${#missing[@]} > 0 )); then
    echo "ERROR: Step 2 requires API keys. Missing: ${missing[*]}" >&2
    echo "Hint: set env vars or create a local .env file." >&2
    exit 1
  fi
}

run_step1() {
  log "Step 1/4: Build dataset"
  "$PYTHON" src/01_make_dataset.py --config "$CONFIG" | tee runs/logs/step1.log
  wc -l data/wmt_sample.jsonl || true
}

run_step2() {
  log "Step 2/4: Translate + confidence (API calls)"
  require_step2_keys
  mkdir -p runs/raw

  CMD=("$PYTHON" src/02_translate_and_confidence.py
    --config "$CONFIG"
    --input data/wmt_sample.jsonl
    --outdir runs/raw)

  if [[ -n "$MAX_SAMPLES" ]]; then
    CMD+=(--max_samples "$MAX_SAMPLES")
  fi
  if [[ -n "$PROVIDERS" ]]; then
    CMD+=(--providers "$PROVIDERS")
  fi
  if [[ -n "$MODELS" ]]; then
    CMD+=(--models "$MODELS")
  fi

  log "Command: ${CMD[*]}"

  if [[ "$STEP2_BG" -eq 1 ]]; then
    nohup "${CMD[@]}" > runs/logs/step2.log 2>&1 &
    disown || true
    log "Step 2 running in background. Tail logs: tail -f runs/logs/step2.log"
  else
    "${CMD[@]}" 2>&1 | tee runs/logs/step2.log
  fi
}

run_step3() {
  log "Step 3/4: Features + metrics"
  mkdir -p runs/aggregated
  "$PYTHON" src/03_features_and_metrics.py \
    --config "$CONFIG" \
    --input_dir runs/raw \
    --output runs/aggregated/dataframe.csv \
    | tee runs/logs/step3.log
}

run_step4() {
  log "Step 4/4: Analysis + paper outputs"
  mkdir -p figures
  "$PYTHON" src/04_analysis_and_plots.py \
    --config "$CONFIG" \
    --input runs/aggregated/dataframe.csv \
    --outdir figures \
    --results runs/aggregated/results_by_model.json \
    --summary runs/aggregated/summary_table.csv \
    --meta runs/aggregated/meta.json \
    --examples paper/top_mismatch_examples.md \
    | tee runs/logs/step4.log

  log "Done writing outputs"
  ls -lah runs/aggregated || true
  ls -lah figures || true
  ls -lah paper/top_mismatch_examples.md || true
}

case "$MODE" in
  all)
    run_step1
    if [[ "$SKIP_STEP2" -eq 0 ]]; then
      run_step2
      if [[ "$STEP2_BG" -eq 1 ]]; then
        log "Step 2 is running in background. Continue later with:"
        log "  bash run_repro.sh --mode step3"
        log "  bash run_repro.sh --mode step4"
        exit 0
      fi
    else
      log "Skipping Step 2 as requested (--skip_step2)."
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

log "All requested steps completed."
