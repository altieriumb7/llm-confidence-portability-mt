# Robustness and baselines

This note documents two additions:
1. prompt-sensitivity robustness scaffolding (config-driven prompt variants), and
2. an external comparator baseline that is fully offline-computable.

## 1) Prompt variants (same task/schema)

Prompt variants are defined in `configs/models.yaml` under `global.prompt_variants`.
The shipped variants are:
- `canonical_v1` (baseline)
- `minimal_v2`
- `verifier_v3`

All variants preserve:
- English-to-German translation task
- strict JSON output schema (`{"translation": ...}` and `{"confidence": ...}`)
- same dataset and model list
- same decoding settings from config unless changed explicitly

Implementation paths:
- `src/utils/prompt_variants.py`
- provider clients call the shared renderer (`src/providers/*.py`)
- runner accepts `--prompt_variant` (`src/02_translate_and_confidence.py`)

### Optional live reruns (not bundled)

Variant reruns require provider credentials and network:

```bash
python3 src/02_translate_and_confidence.py \
  --config configs/models.yaml \
  --input data/wmt_sample.jsonl \
  --outdir runs/prompt_variants/minimal_v2/raw \
  --prompt_variant minimal_v2
```

Then aggregate/analyze into `runs/prompt_variants/<variant>/aggregated/summary_table.csv`.

The offline bundle does **not** fabricate these outputs. Availability status is tracked in:
- `runs/aggregated/prompt_sensitivity/prompt_sensitivity_status.json`

## 2) External comparator baseline (offline)

Implemented in `src/10_external_comparator.py`.

Comparator name: `surface_proxy_v1`.

Definition (model-independent heuristic):
- length-ratio consistency between source and hypothesis
- digit-count consistency
- punctuation-count consistency
- small penalty for parse-warning rows

No provider internals, no hidden logits, no extra API calls.

Outputs:
- `runs/aggregated/external_comparator/external_comparator_scores.csv`
- `runs/aggregated/external_comparator/external_comparator_summary.csv`
- `runs/aggregated/external_comparator/external_comparator_summary.json`

Comparison metrics reported per model:
- correlation with chrF: self-confidence vs proxy
- ECE-style alignment to chrF-q20 operational label
- accepted-error rate among top-20% highest-score outputs (self vs proxy)

## Reproduction path

Canonical artifact command (offline):

```bash
bash scripts/generate_paper_assets.sh
```

This now regenerates:
- semantic audit artifacts
- external comparator artifacts
- prompt-sensitivity status artifacts
- manuscript-facing tables
