# Multi-provider MT Confidence–Difficulty Mismatch Study

Code-only reproducible repository for the MT confidence–difficulty mismatch pipeline.

## Reproducible setup
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
# Optional exact environment lock (if present)
# pip install -r requirements.lock
```

## API keys
Create `.env` (or export shell vars):
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GEMINI_API_KEY` (fallback: `GOOGLE_API_KEY`)

Use `.env.example` as template. Do **not** commit `.env`.

## Quick reviewer run
```bash
bash run_repro.sh --clean
bash run_repro.sh
```

`run_repro.sh` will:
1. (optional) clean generated outputs,
2. create/use `.venv` and install dependencies,
3. load keys from `.env` if present,
4. execute steps 1→4 of the pipeline,
5. write logs to `runs/logs/`.

## Manual pipeline (steps 1→4)
1. Build dataset:
```bash
python src/01_make_dataset.py --config configs/models.yaml
```
2. Translate + confidence:
```bash
python src/02_translate_and_confidence.py --config configs/models.yaml --input data/wmt_sample.jsonl --outdir runs/raw
```
3. Features + metrics:
```bash
python src/03_features_and_metrics.py --config configs/models.yaml --input_dir runs/raw --output runs/aggregated/dataframe.csv
```
4. Analysis + plots:
```bash
python src/04_analysis_and_plots.py --config configs/models.yaml --input runs/aggregated/dataframe.csv --outdir figures --results runs/aggregated/results_by_model.json --summary runs/aggregated/summary_table.csv --examples paper/top_mismatch_examples.md
```

## Provider/model filters
```bash
python src/02_translate_and_confidence.py ... --providers openai,anthropic
python src/02_translate_and_confidence.py ... --models gpt-5.2,"Claude Sonnet 4.5"
```

## Dry-run mode
Use dry-run to test the pipeline without APIs:
```bash
python src/02_translate_and_confidence.py ... --dry_run
```
In dry-run, `hyp=ref` and `conf=0.5`.

## Artifact policy (code-only repository)
Generated artifacts are intentionally not versioned:
- `runs/`
- `figures/`
- `data/wmt_sample.jsonl`
- `paper/top_mismatch_examples.md`

## Where outputs are written
- Aggregated tables/metrics: `runs/aggregated/`
- Logs: `runs/logs/`
- Figures: `figures/`
- Paper snippets/examples: `paper/`

## Cost / rate-limit notes
Running step 2 triggers paid API calls and may be rate-limited.
For conservative reviewer runs, set `concurrency_per_provider: 1` in `configs/models.yaml`.

## Prompts
Prompt templates are defined in provider clients:
- `src/providers/openai_client.py`
- `src/providers/anthropic_client.py`
- `src/providers/gemini_client.py`

All providers use the same task structure for translation and confidence scoring.
