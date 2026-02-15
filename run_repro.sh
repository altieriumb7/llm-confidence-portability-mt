#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

CONFIG="configs/models.yaml"
CLEAN=0
MAX_SAMPLES=""
PROVIDERS=""
MODE="all"          # all | step1 | step2 | step3 | step4
STEP2_BG=0
VENV_DIR=".venv"

log() {
  printf '\n[%s] %s\n' "$(date +"%Y-%m-%d %H:%M:%S")" "$*"
}

usage() {
  cat <<'USAGE'
Usage: bash run_repro.sh [options]

Options:
  --config PATH           Path to config YAML (default: configs/models.yaml)
  --clean                 Remove generated outputs before running
  --max-samples N         Limit Step 2 to N samples (smoke test)
  --providers LIST        Comma-separated providers for Step 2 (e.g. openai,anthropic)
  --mode MODE             all | step1 | step2 | step3 | step4 (default: all)
  --step2-bg              Run Step 2 in background (nohup), logs to runs/logs/step2.log
  -h, --help              Show help
USAGE
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

if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

if [[ ! -d "$VENV_DIR" ]]; then
  log "Creating virtual environment at $VENV_DIR"
  python -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

log "Installing dependencies"
python -m pip install -U pip >/dev/null
pip install -r requirements.txt >/dev/null

mkdir -p runs/logs

log "Environment"
python --version
pip --version

log "Config sanity check"
python - "$CONFIG" <<'PY' || true
import sys
cfg_path = sys.argv[1]
try:
    import yaml
except Exception:
    print("WARN: PyYAML unavailable; skipping config parse check")
    raise SystemExit(0)

with open(cfg_path, "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f) or {}
print(f"global.n = {(cfg.get('global') or {}).get('n')!r}")
PY

if [[ "$CLEAN" -eq 1 ]]; then
  log "CLEAN: removing generated outputs only"
  rm -f data/wmt_sample.jsonl
  rm -rf runs/raw
  rm -rf runs/logs
  rm -rf runs/aggregated
  rm -rf figures
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
  python src/01_make_dataset.py --config "$CONFIG" | tee runs/logs/step1.log
  wc -l data/wmt_sample.jsonl || true
}

run_step2() {
  log "Step 2/4: Translate + confidence (API calls)"
  require_step2_keys
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
  python src/03_features_and_metrics.py \
    --config "$CONFIG" \
    --input_dir runs/raw \
    --output runs/aggregated/dataframe.csv \
    | tee runs/logs/step3.log
}

run_step4() {
  log "Step 4/4: Analysis + paper outputs"
  mkdir -p figures
  python src/04_analysis_and_plots.py \
    --config "$CONFIG" \
    --input runs/aggregated/dataframe.csv \
    --outdir figures \
    --results runs/aggregated/results_by_model.json \
    --summary runs/aggregated/summary_table.csv \
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
    run_step2
    if [[ "$STEP2_BG" -eq 1 ]]; then
      log "Step 2 is running in background. Continue later with:"
      log "  bash run_repro.sh --mode step3"
      log "  bash run_repro.sh --mode step4"
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

log "All requested steps completed."
