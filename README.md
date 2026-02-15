# Multi-provider MT Confidence–Difficulty Mismatch Study

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment variables
Create `.env` (or export shell vars):
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GEMINI_API_KEY` (fallback: `GOOGLE_API_KEY`)

See `.env.example`.

## Run end-to-end whole pipeline

run run_repro.sh


## Run end-to-end
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
Use dry-run to test pipeline without APIs:
```bash
python src/02_translate_and_confidence.py ... --dry_run
```
In dry-run, `hyp=ref` and `conf=0.5`.

## Caching/resume
Per-model cache files are stored at `runs/raw/{provider}__{model_id}.jsonl`.
Already translated IDs are skipped on rerun.

## Fairness notes
- Identical translation/confidence prompts across providers.
- Default `temperature=0.0`.
- Shared config in `configs/models.yaml`.

## Expected outputs

Note: generated artifacts (figures and run outputs) are not meant to be versioned; they are produced locally when you run the pipeline.
- `data/wmt_sample.jsonl`
- `runs/raw/{provider}__{model_id}.jsonl`
- `runs/aggregated/dataframe.csv`
- `runs/aggregated/results_by_model.json`
- `runs/aggregated/summary_table.csv`
- `figures/fig1_scatter_difficulty_vs_conf.png`
- `figures/fig2_reliability_diagram_overlay.png`
- `figures/fig3_mismatch_by_difficulty_bucket.png`
- `figures/fig4_efficiency_frontier.png`
- `paper/draft.md`
- `paper/top_mismatch_examples.md`
