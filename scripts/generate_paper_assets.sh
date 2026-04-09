#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
CONFIG="${CONFIG:-configs/models.yaml}"
SNAPSHOT_DIR="${SNAPSHOT_DIR:-runs/snapshots/20260228_000439/raw}"

SNAPSHOT_DIR="$SNAPSHOT_DIR" PYTHON_BIN="$PYTHON_BIN" CONFIG="$CONFIG" bash scripts/regenerate_tables.sh
PYTHON_BIN="$PYTHON_BIN" CONFIG="$CONFIG" bash scripts/regenerate_figures.sh

rm -f runs/aggregated/calibration/* runs/aggregated/selective_analysis/* runs/aggregated/parse_audit/*
rm -f runs/aggregated/secondary_metric/* runs/aggregated/metric_robustness/* runs/aggregated/semantic_audit/*
rm -f runs/aggregated/external_comparator/* runs/aggregated/prompt_sensitivity/*

"$PYTHON_BIN" src/05_calibration_analysis.py --config "$CONFIG" --input runs/aggregated/dataframe.csv --outdir runs/aggregated/calibration
"$PYTHON_BIN" src/07_selective_analysis.py --config "$CONFIG" --input runs/aggregated/dataframe.csv --outdir runs/aggregated/selective_analysis
"$PYTHON_BIN" src/08_parse_warning_audit.py --config "$CONFIG" --input runs/aggregated/dataframe.csv --snapshot_dir "$SNAPSHOT_DIR" --outdir runs/aggregated/parse_audit
"$PYTHON_BIN" src/05_secondary_metric.py --input runs/aggregated/dataframe.csv --outdir runs/aggregated/secondary_metric --backend auto
"$PYTHON_BIN" src/06_metric_robustness.py --input runs/aggregated/dataframe.csv --secondary_scores runs/aggregated/secondary_metric/secondary_metric_scores.csv --outdir runs/aggregated/metric_robustness
"$PYTHON_BIN" src/09_semantic_audit.py --input runs/aggregated/dataframe.csv --outdir runs/aggregated/semantic_audit
"$PYTHON_BIN" src/10_external_comparator.py --input runs/aggregated/dataframe.csv --outdir runs/aggregated/external_comparator
"$PYTHON_BIN" src/11_prompt_sensitivity.py --config "$CONFIG" --baseline_summary runs/aggregated/summary_table.csv --variant_root runs/prompt_variants --outdir runs/aggregated/prompt_sensitivity

"$PYTHON_BIN" tools/export_latex_tables.py
"$PYTHON_BIN" tools/consistency_check.py

echo "Paper-facing assets regenerated and checked."
