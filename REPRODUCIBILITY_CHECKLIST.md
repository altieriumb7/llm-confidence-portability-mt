# Reproducibility Checklist

## Canonical offline command

```bash
bash scripts/reproduce_offline_artifact.sh
```

## Reviewer Quickstart: deterministic offline reproduction

### What works without API keys
- Regenerate manuscript-facing tables/figures/examples from bundled snapshot.
- Re-run consistency checks and reviewer readiness checks.

### What requires live API calls
- `run_repro.sh --mode step2` and `run_repro.sh --mode all` (provider calls).
- Non-baseline prompt variant outputs (`minimal_v2`, `verifier_v3`), which are optional and not bundled offline.

### What is snapshot/artifact-level only
- Baseline `canonical_v1` prompt outputs.
- Semantic-audit scaffold and candidate/sample exports; completed semantic labels are not bundled.

### What is intentionally not claimed in offline-only mode
- Cross-prompt robustness invariance.
- Semantic correctness calibration against human labels.

### Deterministic reviewer commands

```bash
bash scripts/generate_paper_assets.sh
python3 tools/consistency_check.py --config configs/models.yaml
make reviewer-check
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
  - canonical bibliography metadata is incomplete in this snapshot (`references.bib` is compatibility-only; bundled keys are in `added_refs.bib`)


## Submission-oriented manuscript files

- Full manuscript source: `revised_submission_with_new_results.tex`
- ATC-compressed source: `revised_submission_atc2026_compressed.tex`
