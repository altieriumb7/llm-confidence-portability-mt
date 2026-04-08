# Paper ↔ Repository Asset Audit

This file records the authoritative generation path for every manuscript-facing table/figure asset and notes what remains manual.

## Tables consumed by manuscript

| Manuscript input | Generated file | Upstream source data | Generator |
|---|---|---|---|
| `\input{tables/summary}` | `tables/summary.tex` | `runs/aggregated/summary_table.csv` | `tools/export_latex_tables.py` |
| `\input{tables/corr}` | `tables/corr.tex` | `runs/aggregated/results_by_model.json` (`correlations`) | `tools/export_latex_tables.py` |
| `\input{tables/calibration}` | `tables/calibration.tex` | `runs/aggregated/calibration/calibration_summary.json` | `tools/export_latex_tables.py` |
| `\input{tables/metric_robustness}` | `tables/metric_robustness.tex` | `runs/aggregated/metric_robustness/metric_robustness_summary.json` | `tools/export_latex_tables.py` |
| `\input{tables/robustness}` | `tables/robustness.tex` | `runs/aggregated/results_by_model.json` (mismatch@0.9 variants) | `tools/export_latex_tables.py` |

## Figures consumed by manuscript

| Manuscript include | Generated file | Upstream source data | Generator |
|---|---|---|---|
| `figures/fig1_scatter_difficulty_vs_conf.pdf` | same | `runs/aggregated/dataframe.csv` | `src/04_analysis_and_plots.py` via `scripts/regenerate_figures.sh` |
| `figures/fig2_reliability_diagram_overlay.pdf` | same | `runs/aggregated/dataframe.csv` | `src/04_analysis_and_plots.py` via `scripts/regenerate_figures.sh` |
| `figures/fig3_mismatch_by_difficulty_bucket.pdf` | same | `runs/aggregated/dataframe.csv` | `src/04_analysis_and_plots.py` via `scripts/regenerate_figures.sh` |
| `figures/fig4_efficiency_frontier.pdf` | same | `runs/aggregated/dataframe.csv` | `src/04_analysis_and_plots.py` via `scripts/regenerate_figures.sh` |

## Paper-facing examples markdown

- `paper/top_mismatch_examples.md` is generated from `runs/aggregated/dataframe.csv` by `src/04_analysis_and_plots.py`.

## Canonical generation + checks

- Regenerate all paper-facing assets:

```bash
bash scripts/generate_paper_assets.sh
```

- Check for drift only:

```bash
python3 tools/consistency_check.py
```

## Remaining manual values

- Narrative prose in `revised_submission_with_new_results.tex` remains hand-maintained text.
- Bibliography source `references.bib` is still external/missing from this repository snapshot.
