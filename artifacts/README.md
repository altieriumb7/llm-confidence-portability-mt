# Artifact notes

## Canonical paper-facing generation

```bash
bash scripts/generate_paper_assets.sh
```

This is the authoritative manuscript-asset pipeline.

## Generated (do not hand-edit)

- `tables/*.tex` (from `tools/export_latex_tables.py`)
- `figures/*`
- `paper/top_mismatch_examples.md`
- `runs/aggregated/*` outputs and supplementary analyses

## Drift guard

- `python3 tools/consistency_check.py` fails on stale manuscript-facing table files or missing manuscript-referenced figures.

## Hand-maintained

- `revised_submission_with_new_results.tex`
- `added_refs.bib`
- docs (`README.md`, `paper/README.md`, `REPRODUCIBILITY_CHECKLIST.md`)
