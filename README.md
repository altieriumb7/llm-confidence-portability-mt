# Confidence–Difficulty Mismatch in MT Evaluation

This repository is packaged as a **reviewer artifact** for the full manuscript `revised_submission_with_new_results.tex` and an ATC-compressed draft `revised_submission_atc2026_compressed.tex`.

## Quick start (offline, recommended)

```bash
bash scripts/reproduce_offline_artifact.sh --skip-manuscript
```

This pipeline regenerates manuscript-facing assets from the bundled snapshot and runs consistency checks. It validates artifact drift and key wiring/metadata checks, but it does **not** validate narrative claims, bibliography completeness, or figure semantics.

## Reviewer Quickstart: deterministic offline reproduction

This section is the intended **reviewer-safe path** for FLLM-style artifact checks.

- **Reproducible without API keys (deterministic, snapshot-based):**
  - Regenerate manuscript-facing tables/figures/examples from bundled raw snapshot.
  - Re-run consistency checks for paper/repo wiring and drift.
- **Requires live provider API keys (non-deterministic over time):**
  - Step 2 (`run_repro.sh --mode step2` or `--mode all`) model calls.
  - Non-baseline prompt-variant reruns (`minimal_v2`, `verifier_v3`).
- **Snapshot/artifact-level only in this bundle:**
  - Baseline prompt variant (`canonical_v1`) outputs.
  - Semantic-audit scaffold artifacts (no completed human labels).
- **Intentionally not claimed by this artifact alone:**
  - Cross-prompt robustness invariance.
  - Semantic correctness calibration against human annotation labels.

Deterministic reviewer commands:

```bash
# regenerate manuscript-facing tables/figures/examples from bundled snapshot
bash scripts/generate_paper_assets.sh

# run consistency checks
python3 tools/consistency_check.py --config configs/models.yaml

# run one-pass reviewer readiness checks (files + consistency + bib keys + optional TeX)
make reviewer-check
```

Expected outputs after deterministic regeneration:
- tables: `tables/summary.tex`, `tables/corr.tex`, `tables/robustness.tex`, `tables/calibration.tex`, `tables/metric_robustness.tex`, `tables/semantic_audit.tex`, `tables/prompt_sensitivity_status.tex`
- figures: `figures/fig1_scatter_difficulty_vs_conf.pdf`, `figures/fig2_reliability_diagram_overlay.pdf`, `figures/fig3_mismatch_by_difficulty_bucket.pdf`, `figures/fig4_efficiency_frontier.pdf`
- examples: `paper/top_mismatch_examples.md`

## Quick repository orientation


- **Manuscript variants**
  - Full manuscript: `revised_submission_with_new_results.tex`
  - ATC-compressed draft: `revised_submission_atc2026_compressed.tex` (submission-oriented condensation using only bundled evidence)
- **Active analysis + paper-facing outputs**
  - `src/` (analysis pipeline)
  - `scripts/` (root-runnable orchestration)
  - `tools/` (table export + consistency checks)
  - `runs/aggregated/`, `tables/`, `figures/`, `paper/top_mismatch_examples.md`
- **Bundled offline source snapshot**
  - `runs/snapshots/20260228_000439/raw/*.jsonl`
- **Paper source + paper docs**
  - `revised_submission_with_new_results.tex`
  - `paper/`
- **Live/API path (credentials required)**
  - `run_repro.sh` (Step 2 calls providers)
- **Archival/context docs**
  - `REPAIR_REPORT.md`, `CHANGELOG_ARTIFACT_FIXES.md`

## Local artifact build scripts (text-only workflow)

To regenerate generated artifacts locally (without committing binaries from Codex), use:

```bash
bash scripts/build_artifacts.sh
```

Optional manuscript PDF build:

```bash
WITH_PDF=1 bash scripts/build_artifacts.sh
```

If you only need figures:

```bash
bash scripts/build_figures.sh
```

If you want a binary-only regeneration entrypoint for figures (and optional manuscript PDF):

```bash
bash scripts/generate_binary_artifacts.sh
# optional PDF build:
WITH_PDF=1 bash scripts/generate_binary_artifacts.sh
```

PR-friendly binary regeneration helper (same intent, explicit for figure rebuilds):
```bash
bash scripts/regenerate_pr_binaries.sh
# optional manuscript PDF attempt:
WITH_PDF=1 bash scripts/regenerate_pr_binaries.sh
```

Compatibility wrapper used in older docs:
```bash
bash scripts/generate_all_artifacts.sh
```

If you only need the manuscript PDF:

```bash
bash scripts/build_pdf.sh
```

### Prerequisites
- Python 3 + dependencies from `requirements.txt`
- Bundled snapshot data at `runs/snapshots/20260228_000439/raw/*.jsonl`
- `latexmk` (only for PDF build)

### Generated artifact types and output locations
- Figures (`.png`, `.pdf`): `figures/` via `src/04_analysis_and_plots.py` (called by `scripts/regenerate_figures.sh` / `scripts/build_figures.sh`)
- Aggregated analysis artifacts (`.csv`, `.json`, `.md`, `.tex`): `runs/aggregated/` and `tables/` via `scripts/generate_paper_assets.sh`
- Manuscript PDF (`.pdf`): project root (or `BUILD_DIR`) via `scripts/build_pdf.sh`

### Known limitation
The snapshot does not include the canonical legacy bibliography metadata. `references.bib` is an empty compatibility file and bundled entries currently live in `added_refs.bib`; see `paper/TODO_missing_bibliography.md`.

## Authoritative locations

- Environment setup: `requirements.txt`, `requirements.lock`
- Raw snapshot input (bundled): `runs/snapshots/20260228_000439/raw/*.jsonl`
- Aggregate outputs: `runs/aggregated/`
- Paper tables consumed by LaTeX (generated): `tables/*.tex`
- Paper figures (generated): `figures/*.pdf`, `figures/*.png`
- Paper-facing generated markdown examples: `paper/top_mismatch_examples.md`
- Manuscript entrypoint: `revised_submission_with_new_results.tex`

## Generated manuscript asset pipeline

- Full offline paper-asset regeneration:
  ```bash
  bash scripts/generate_paper_assets.sh
  ```
- Validation-only pass:
  ```bash
  bash scripts/validate_artifact.sh
  ```
  This currently checks parse regression, LaTeX table drift, manuscript wiring, key metric/table cross-consistency, and metadata/config integrity.

## Optional commands

- Build manuscript PDF as well (requires LaTeX):
  ```bash
  bash scripts/reproduce_offline_artifact.sh
  ```
- Run all validation checks only:
  ```bash
  bash scripts/validate_artifact.sh
  ```
- Attempt full live/API pipeline (credentials required):
  ```bash
  bash run_repro.sh --mode all
  ```

## Core documentation

- Reviewer workflow and provenance map: `ARTIFACT_GUIDE.md`
- Quick repository orientation map: `REPO_MAP.md`
- Reproducibility scope/status statement: `ARTIFACT_STATUS.md`
- Prompt robustness and baseline details: `ROBUSTNESS_AND_BASELINES.md`
- Paper-specific build notes: `paper/README.md`

## What is bundled

- Raw offline snapshot: `runs/snapshots/20260228_000439/raw/*.jsonl`
- Regenerated aggregated outputs: `runs/aggregated/`
- Semantic-audit exports for high-confidence mismatch review: `runs/aggregated/semantic_audit/`
- External comparator baseline exports: `runs/aggregated/external_comparator/`
- Prompt-sensitivity status exports: `runs/aggregated/prompt_sensitivity/`
- Manuscript tables: `tables/*.tex`
- Manuscript figures: `figures/*`

## Environment

- Python dependencies: `requirements.txt`
- Optional containerized path: `Dockerfile`

## Important scope boundary

Live provider API calls (Step 2) are **not** reproducible from the zip alone and are expected to vary over time.
