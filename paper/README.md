# Confidence–Difficulty Mismatch in MT Evaluation (Paper Repository Notes)

This directory documents the manuscript compile entrypoint and its dependency on generated artifacts from the code pipeline.

## True manuscript entrypoint

The manuscript entrypoint in this repository is:

- `revised_submission_with_new_results.tex`

Bibliography file:

- `added_refs.bib`

> Stale references to `main.tex` / `main_v2.tex` are obsolete for this repository and should not be used.

## Correct compile instructions

From repository root:

```bash
latexmk -pdf -interaction=nonstopmode revised_submission_with_new_results.tex
```

If your LaTeX toolchain does not auto-run bibliography resolution, run:

```bash
pdflatex revised_submission_with_new_results.tex
bibtex revised_submission_with_new_results
pdflatex revised_submission_with_new_results.tex
pdflatex revised_submission_with_new_results.tex
```

## Pre-compilation artifact generation workflow (required)

Before compiling the manuscript, regenerate artifacts via shell scripts so figure/table inputs are up to date:

```bash
bash scripts/generate_all_artifacts.sh
```

Equivalent two-step form:

```bash
bash scripts/regenerate_tables.sh
bash scripts/regenerate_figures.sh
```

This ensures the manuscript has current generated dependencies under:

- `figures/`
- `runs/aggregated/`
- `paper/top_mismatch_examples.md`
