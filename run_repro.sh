#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

CONFIG="configs/models.yaml"
CLEAN=0
MAX_SAMPLES=""
PROVIDERS=""
MODELS=""
MODE="all"          # all | step1 | step2 | step3 | step4 | calibration | secondary_metric | robustness | selective_analysis | parse_audit
STEP2_BG=0
SKIP_STEP2=0
WITH_CALIBRATION=0
WITH_SELECTIVE_ANALYSIS=0
WITH_PARSE_AUDIT=0
WITH_STRONGER_METRIC=0
WITH_METRIC_ROBUSTNESS=0
SECONDARY_METRIC_BACKEND="auto"
DATASET=""
SRC_LANG=""
TGT_LANG=""
SAMPLE_SIZE=""

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
  --mode MODE             all | step1 | step2 | step3 | step4 | calibration | selective_analysis | parse_audit | secondary_metric | robustness
  --skip_step2            Skip Step 2 (useful for re-running Step 3/4)
  --step2-bg              Run Step 2 in background (nohup), logs to runs/logs/step2.log
  --dataset NAME          Dataset/testset for Step 1 (default: config global.testset)
  --src_lang LANG         Source language for Step 1 (default: from config langpair)
  --tgt_lang LANG         Target language for Step 1 (default: from config langpair)
  --sample_size N         Sample size for Step 1 (default: config global.n)
  --with_calibration      Run post-hoc isotonic calibration analysis after Step 4
  --with_selective_analysis Run coverage-aware selective prediction analysis after Step 4
  --with_parse_audit      Run parse-warning / repair audit after Step 4
  --with_stronger_metric  Run secondary metric analysis after Step 4
  --secondary_metric_backend MODE  auto | comet | fallback_bleu (default: auto)
  --with_metric_robustness Run robustness comparison after secondary metric analysis
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
    --dataset) DATASET="$2"; shift 2 ;;
    --src_lang) SRC_LANG="$2"; shift 2 ;;
    --tgt_lang) TGT_LANG="$2"; shift 2 ;;
    --sample_size) SAMPLE_SIZE="$2"; shift 2 ;;
    --with_calibration) WITH_CALIBRATION=1; shift ;;
    --with_selective_analysis) WITH_SELECTIVE_ANALYSIS=1; shift ;;
    --with_parse_audit) WITH_PARSE_AUDIT=1; shift ;;
    --with_stronger_metric) WITH_STRONGER_METRIC=1; shift ;;
    --secondary_metric_backend) SECONDARY_METRIC_BACKEND="$2"; shift 2 ;;
    --with_metric_robustness) WITH_METRIC_ROBUSTNESS=1; shift ;;
    --python) PYTHON="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2
      if [[ "$1" == "--with_selective_analysis" || "$1" == "--with_parse_audit" ]]; then
        echo "Hint: this flag requires the updated run_repro.sh. Verify with: bash run_repro.sh --help" >&2
      fi
      usage
      exit 1
      ;;
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

RUN_ID="${RUN_ID:-$(date +"%Y%m%d_%H%M%S")}"
SNAPDIR="runs/snapshots/${RUN_ID}"
mkdir -p "${SNAPDIR}/raw" "${SNAPDIR}/exports"
log "Run snapshot: ${SNAPDIR}"
cp -f "$CONFIG" "${SNAPDIR}/config.yaml" || true

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
  CMD=("$PYTHON" src/01_make_dataset.py --config "$CONFIG")
  if [[ -n "$DATASET" ]]; then CMD+=(--dataset "$DATASET"); fi
  if [[ -n "$SRC_LANG" ]]; then CMD+=(--src_lang "$SRC_LANG"); fi
  if [[ -n "$TGT_LANG" ]]; then CMD+=(--tgt_lang "$TGT_LANG"); fi
  if [[ -n "$SAMPLE_SIZE" ]]; then CMD+=(--sample_size "$SAMPLE_SIZE"); fi
  "${CMD[@]}" | tee runs/logs/step1.log
  wc -l data/wmt_sample.jsonl || true
  cp -f data/wmt_sample.jsonl "${SNAPDIR}/wmt_sample.jsonl" || true
}

run_step2() {
  log "Step 2/4: Translate + confidence (API calls)"
  require_step2_keys
  mkdir -p runs/raw
  if [[ ! -s data/wmt_sample.jsonl ]]; then
    echo "ERROR: data/wmt_sample.jsonl missing or empty. Run: bash run_repro.sh --mode step1" >&2
    exit 1
  fi

  CMD=("$PYTHON" src/02_translate_and_confidence.py
    --config "$CONFIG"
    --input data/wmt_sample.jsonl
    --outdir runs/raw)

  if [[ -n "$MAX_SAMPLES" ]]; then CMD+=(--max_samples "$MAX_SAMPLES"); fi
  if [[ -n "$PROVIDERS" ]]; then CMD+=(--providers "$PROVIDERS"); fi
  if [[ -n "$MODELS" ]]; then CMD+=(--models "$MODELS"); fi

  log "Command: ${CMD[*]}"

  if [[ "$STEP2_BG" -eq 1 ]]; then
    nohup "${CMD[@]}" > runs/logs/step2.log 2>&1 &
    disown || true
    log "Step 2 running in background. Tail logs: tail -f runs/logs/step2.log"
  else
    "${CMD[@]}" 2>&1 | tee runs/logs/step2.log
    log "Snapshotting raw outputs to ${SNAPDIR}/raw"
    mkdir -p "${SNAPDIR}/raw" "${SNAPDIR}/exports"
    (command -v rsync >/dev/null 2>&1 && rsync -a runs/raw/ "${SNAPDIR}/raw/") || cp -a runs/raw/. "${SNAPDIR}/raw/"
    log "Exporting per-model inputs/translations to ${SNAPDIR}/exports"
    "$PYTHON" tools/export_translations.py --raw_dir runs/raw --out_dir "${SNAPDIR}/exports" --dedupe_last || true
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

run_calibration() {
  log "Step 5/6: Post-hoc calibration analysis"
  mkdir -p runs/aggregated/calibration
  "$PYTHON" src/05_calibration_analysis.py \
    --config "$CONFIG" \
    --input runs/aggregated/dataframe.csv \
    --outdir runs/aggregated/calibration \
    | tee runs/logs/step5_calibration.log
}


run_selective_analysis() {
  log "Step 5/8: Coverage-aware selective analysis"
  mkdir -p runs/aggregated/selective_analysis
  "$PYTHON" src/07_selective_analysis.py \
    --config "$CONFIG" \
    --input runs/aggregated/dataframe.csv \
    --outdir runs/aggregated/selective_analysis \
    | tee runs/logs/step5_selective_analysis.log
}

run_parse_audit() {
  log "Step 6/8: Parse-warning audit"
  mkdir -p runs/aggregated/parse_audit
  "$PYTHON" src/08_parse_warning_audit.py \
    --config "$CONFIG" \
    --input runs/aggregated/dataframe.csv \
    --outdir runs/aggregated/parse_audit \
    | tee runs/logs/step6_parse_audit.log
}

run_secondary_metric() {
  log "Step 7/8: Secondary metric analysis"
  mkdir -p runs/aggregated/secondary_metric
  "$PYTHON" src/05_secondary_metric.py \
    --input runs/aggregated/dataframe.csv \
    --outdir runs/aggregated/secondary_metric \
    --backend "$SECONDARY_METRIC_BACKEND" \
    | tee runs/logs/step5_secondary_metric.log
}

run_metric_robustness() {
  log "Step 8/8: Metric robustness analysis"
  if [[ ! -f runs/aggregated/secondary_metric/secondary_metric_scores.csv ]]; then
    echo "ERROR: metric robustness requires runs/aggregated/secondary_metric/secondary_metric_scores.csv. Run with --with_stronger_metric first." >&2
    exit 1
  fi
  mkdir -p runs/aggregated/metric_robustness
  "$PYTHON" src/06_metric_robustness.py \
    --input runs/aggregated/dataframe.csv \
    --secondary_scores runs/aggregated/secondary_metric/secondary_metric_scores.csv \
    --outdir runs/aggregated/metric_robustness \
    | tee runs/logs/step6_metric_robustness.log
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
    if [[ "$WITH_CALIBRATION" -eq 1 ]]; then run_calibration; fi
    if [[ "$WITH_SELECTIVE_ANALYSIS" -eq 1 ]]; then run_selective_analysis; fi
    if [[ "$WITH_PARSE_AUDIT" -eq 1 ]]; then run_parse_audit; fi
    if [[ "$WITH_STRONGER_METRIC" -eq 1 ]]; then run_secondary_metric; fi
    if [[ "$WITH_METRIC_ROBUSTNESS" -eq 1 ]]; then
      if [[ "$WITH_STRONGER_METRIC" -eq 0 ]]; then
        log "Robustness requested without explicit stronger-metric stage; running secondary metric first"
        run_secondary_metric
      fi
      run_metric_robustness
    fi
    ;;
  step1) run_step1 ;;
  step2) run_step2 ;;
  step3) run_step3 ;;
  step4) run_step4 ;;
  calibration) run_calibration ;;
  selective_analysis) run_selective_analysis ;;
  parse_audit) run_parse_audit ;;
  secondary_metric) run_secondary_metric ;;
  robustness) run_metric_robustness ;;
  *) echo "Unknown --mode: $MODE"; usage; exit 1 ;;
esac

log "All requested steps completed."
