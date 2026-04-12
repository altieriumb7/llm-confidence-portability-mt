# Reproducibility Checklist

## Canonical offline command

```bash
bash scripts/reproduce_offline_artifact.sh
```

## Paper-asset-only command

```bash
bash scripts/generate_paper_assets.sh
```

This regenerates manuscript-facing tables/figures/examples and runs `tools/consistency_check.py`.

## Bundled snapshot

- `runs/snapshots/20260228_000439/raw/*.jsonl`

## Generated manuscript-facing assets

- `tables/summary.tex`
- `tables/corr.tex`
- `tables/robustness.tex`
- `tables/calibration.tex`
- `tables/metric_robustness.tex`
- `figures/fig1_scatter_difficulty_vs_conf.pdf`
- `figures/fig2_reliability_diagram_overlay.pdf`
- `figures/fig3_mismatch_by_difficulty_bucket.pdf`
- `figures/fig4_efficiency_frontier.pdf`
- `paper/top_mismatch_examples.md`

## Drift check

```bash
python3 tools/consistency_check.py
```

Fails on table drift, manuscript wiring gaps, key metric inconsistencies, or metadata/config integrity mismatches.

## Legacy-compatible wrapper

```bash
bash scripts/generate_all_artifacts.sh
```

This wrapper is kept for command compatibility and forwards to the active offline build workflow.

## Remaining blocker

- Full manuscript PDF build still needs:
  - TeX toolchain (`latexmk` or `pdflatex` + `bibtex`)
  - missing external file `references.bib`
