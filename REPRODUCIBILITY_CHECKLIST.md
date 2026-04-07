# Reproducibility Checklist (Bundled Raw Snapshot)

This checklist defines the **minimal** reproducible paths in this repository and separates:

1. offline regeneration from bundled raw data,
2. live-API runs,
3. optional metric dependencies (COMET).

---

## A) Minimal environment

- OS: Linux/macOS with shell access.
- Python: `python3` available on PATH.
- Python deps: install from `requirements.txt`.

```bash
python3 -m pip install --root-user-action=ignore -U pip
python3 -m pip install --root-user-action=ignore -r requirements.txt
```

Notes:
- API keys are **not** required for the offline path in section B.
- `sacrebleu` command-line availability is required only when building datasets from Step 1 (section C).

---

## B) Offline path (no live APIs) — regenerate aggregated outputs from bundled raw snapshot

Authoritative bundled snapshot:

- `runs/snapshots/20260228_000439/raw/*.jsonl`

### B1. Stage bundled raw snapshot into `runs/raw`

```bash
python3 - <<'PY'
from pathlib import Path
import shutil, glob
raw = Path('runs/raw')
if raw.exists():
    shutil.rmtree(raw)
raw.mkdir(parents=True, exist_ok=True)
for fp in glob.glob('runs/snapshots/20260228_000439/raw/*.jsonl'):
    shutil.copy(fp, raw / Path(fp).name)
print('staged files:', len(list(raw.glob('*.jsonl'))))
PY
```

### B2. Regenerate core aggregates (offline)

```bash
python3 src/03_features_and_metrics.py \
  --config configs/models.yaml \
  --input_dir runs/raw \
  --output runs/aggregated/dataframe.csv

python3 src/04_analysis_and_plots.py \
  --config configs/models.yaml \
  --input runs/aggregated/dataframe.csv \
  --results runs/aggregated/results_by_model.json \
  --summary runs/aggregated/summary_table.csv \
  --meta runs/aggregated/meta.json \
  --examples runs/aggregated/top_mismatch_examples.md \
  --outdir figures \
  --skip_plots --skip_examples
```

### B3. Optional: regenerate plots offline from aggregated dataframe

> Only run this if you explicitly want figures.

```bash
python3 src/04_analysis_and_plots.py \
  --config configs/models.yaml \
  --input runs/aggregated/dataframe.csv \
  --outdir figures \
  --results runs/aggregated/results_by_model.json \
  --summary runs/aggregated/summary_table.csv \
  --meta runs/aggregated/meta.json \
  --examples paper/top_mismatch_examples.md
```

### B4. Quick consistency checks

```bash
python3 - <<'PY'
import csv, json
from pathlib import Path
meta=json.loads(Path('runs/aggregated/meta.json').read_text())
rows=list(csv.DictReader(open('runs/aggregated/dataframe.csv', encoding='utf-8')))
summary=list(csv.DictReader(open('runs/aggregated/summary_table.csv', encoding='utf-8')))
results=json.loads(Path('runs/aggregated/results_by_model.json').read_text())
print('dataframe_rows:', len(rows))
print('meta_n:', meta.get('n'))
print('summary_models:', len(summary))
print('results_models:', len(results))
PY
```

---

## C) Steps that require live APIs

These steps require provider credentials and network calls:

- Step 2 (`src/02_translate_and_confidence.py`) via OpenAI / Anthropic / Gemini.

Expected environment variables:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GEMINI_API_KEY` (or `GOOGLE_API_KEY`)

If these are missing, do not run API-backed reproduction; use section B for offline regeneration from bundled raw outputs.

---

## D) Optional dependencies and analyses

### D1. Secondary metric / COMET (optional)

- `src/05_secondary_metric.py` can use COMET when available.
- If COMET model/runtime is unavailable, use fallback backend behavior as configured.
- This stage is optional and not required for regenerating the primary aggregates.

### D2. Other optional post-hoc analyses

- Calibration: `src/05_calibration_analysis.py`
- Metric robustness: `src/06_metric_robustness.py`
- Selective analysis: `src/07_selective_analysis.py`
- Parse audit: `src/08_parse_warning_audit.py`

These are downstream analyses and not required for rebuilding the core aggregate artifacts.

---

## E) Reproduction intent guardrails

- Do not treat toy/demo dataset mode as real reproduction.
- Real dataset creation (`src/01_make_dataset.py`) now hard-fails if sacrebleu testsets are unavailable unless `--demo_toy_data` is explicitly set.
- For offline reproducibility claims, cite the bundled raw snapshot path and avoid re-running Step 2.
