# Artifact Status (Reviewer-Facing)

## Fully reproducible from this bundle
- Offline regeneration of `runs/aggregated/*` from `runs/snapshots/20260228_000439/raw/*.jsonl`
- Regeneration of `tables/*.tex` from aggregated outputs
- Regeneration of `figures/*` from aggregated outputs
- Regeneration of supplementary analyses:
  - calibration
  - selective analysis
  - parse-warning audit
  - metric robustness (BLEU fallback when COMET unavailable)
- Consistency validation via `tools/consistency_check.py`

## Partially reproducible from this bundle
- Manuscript PDF compilation is reproducible if local LaTeX toolchain is installed.
- Bibliography path resolves because `references.bib` is included as an empty compatibility file, but authoritative reference metadata is not fully packaged.

## Not reproducible from zip alone
- Fresh provider API outputs from Step 2 (`src/02_translate_and_confidence.py`) without credentials/network access.
- Exact bitwise reproduction of live API outputs due to provider/model drift over time.

## Recommended reviewer command
```bash
bash scripts/reproduce_offline_artifact.sh --skip-manuscript
```

## Optional full path (requires API credentials)
```bash
bash run_repro.sh --mode all
```
