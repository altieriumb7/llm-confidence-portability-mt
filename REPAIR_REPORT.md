# Repair Report — PASS 1 (Audit and Source-of-Truth Lock)

Date: 2026-04-07 (UTC)

## 1) True paper entrypoint (locked)

- **Locked manuscript entrypoint:** `revised_submission_with_new_results.tex`.
- Rationale: it is the only manuscript `.tex` file present in the repository root, and it contains the full paper structure (abstract, methods, results, figures, discussion, appendix references).
- Audit note: repository `README.md` currently claims a `main.tex` entrypoint, but `main.tex` is not present in this repository.

## 2) Authoritative bundled raw snapshot (locked)

- **Locked authoritative snapshot:** `runs/snapshots/20260228_000439/raw/*.jsonl`.
- Selection rule used in this audit:
  1. prefer bundled in-repo raw snapshot over derived outputs;
  2. require complete multi-model coverage;
  3. require non-empty per-model files;
  4. choose the latest timestamp among complete snapshots.
- Completeness check summary:
  - `runs/snapshots/20260228_000439/raw/` contains 8 model files, each with 500 lines.
  - Earlier snapshots include incomplete or inconsistent cases (e.g., `20260226_200056` has Gemini Pro at 488 lines; `20260227_235509` has Gemini Flash at 511 lines).
- Lock decision: all paper/code synchronization in later passes must be grounded in this raw snapshot (or explicitly justified if a different bundled raw source is required).


## 2.1) Snapshot selection tie-break note

- Another bundled snapshot (`runs/snapshots/20260228_000109/raw/*.jsonl`) is also complete at 8x500.
- Tie-break policy used for PASS 1 lock: choose the latest complete bundled snapshot by timestamp.
- Therefore the lock remains `20260228_000439`.

## 3) Stale / empty derived artifacts identified

The following currently committed derived outputs are stale/empty relative to the authoritative raw snapshot and must not be treated as evidence:

- `runs/aggregated/dataframe.csv` (header-only, 0 rows)
- `runs/aggregated/summary_table.csv` (header-only, 0 rows)
- `runs/aggregated/meta.json` (`n: 0`, empty providers/models)
- `runs/aggregated/results_by_model.json` (empty object)
- `runs/aggregated/calibration/calibration_summary.csv` (header-only, 0 rows)
- `runs/aggregated/calibration/calibration_summary.json` (`models: {}`)
- `runs/aggregated/metric_robustness/metric_robustness_summary.csv` (header-only, 0 rows)
- `runs/aggregated/metric_robustness/metric_robustness_summary.json` (`models: {}`)
- `runs/aggregated/selective_analysis/selective_model_summary.csv` (header-only, 0 rows)
- `runs/aggregated/selective_analysis/selective_threshold_summary.csv` (header-only, 0 rows)
- `runs/aggregated/selective_analysis/selective_threshold_summary.json` (`models: {}`)
- `runs/aggregated/parse_audit/parse_warning_audit_summary.csv` (header-only, 0 rows)
- `runs/aggregated/parse_audit/parse_warning_audit_summary.json` (`models: {}`)
- `runs/aggregated/secondary_metric/secondary_metric_summary.csv` (header-only, 0 rows)
- `runs/aggregated/secondary_metric/secondary_metric_scores.csv` (header-only, 0 rows)
- `runs/aggregated/secondary_metric/secondary_metric_summary.json` (`rows: []`)
- `runs/aggregated/secondary_metric/secondary_metric_scores.json` (`rows: []`)
- `runs/aggregated/secondary_metric/secondary_metric_meta.json` (`n_rows: 0`)

Additional manuscript-side mismatch discovered in this audit (to be fixed in later passes, not now):

- `revised_submission_with_new_results.tex` inputs missing table files:
  - `tables/summary`
  - `tables/corr`
  - `tables/calibration`
  - `tables/metric_robustness`
  - `tables/robustness`

## 4) Files that must be regenerated in PASS 2 (code-side only)

Regenerate from `runs/snapshots/20260228_000439/raw/`:

- Core aggregates:
  - `runs/aggregated/dataframe.csv`
  - `runs/aggregated/results_by_model.json`
  - `runs/aggregated/summary_table.csv`
  - `runs/aggregated/meta.json`
- Calibration outputs:
  - `runs/aggregated/calibration/calibration_summary.csv`
  - `runs/aggregated/calibration/calibration_summary.json`
- Selective analysis outputs:
  - `runs/aggregated/selective_analysis/selective_model_summary.csv`
  - `runs/aggregated/selective_analysis/selective_threshold_summary.csv`
  - `runs/aggregated/selective_analysis/selective_threshold_summary.json`
- Parse-audit outputs:
  - `runs/aggregated/parse_audit/parse_warning_audit_summary.csv`
  - `runs/aggregated/parse_audit/parse_warning_audit_summary.json`
- Secondary metric + robustness outputs:
  - `runs/aggregated/secondary_metric/secondary_metric_scores.csv`
  - `runs/aggregated/secondary_metric/secondary_metric_scores.json`
  - `runs/aggregated/secondary_metric/secondary_metric_summary.csv`
  - `runs/aggregated/secondary_metric/secondary_metric_summary.json`
  - `runs/aggregated/secondary_metric/secondary_metric_meta.json`
  - `runs/aggregated/metric_robustness/metric_robustness_summary.csv`
  - `runs/aggregated/metric_robustness/metric_robustness_summary.json`

## 5) Guardrails locked for remaining passes

- Do not treat any empty/header-only aggregated files as valid evidence.
- Prefer authoritative bundled raw snapshot over stale aggregated artifacts.
- If a manuscript claim cannot be supported by regenerated outputs from bundled raw materials, downgrade or remove that claim.
- PASS 2 must also remove silent toy-data fallback behavior and fail loudly when expected raw inputs are absent.

## 6) PASS 2 — STEP 2.1 mapping (raw snapshot → aggregated artifacts)

Goal of this step: identify the exact pipeline entry points (scripts/functions/inputs) that generate the core aggregated artifacts, without regenerating outputs yet.

### 6.1 Authoritative raw input snapshot (for regeneration)

- Locked raw snapshot directory: `runs/snapshots/20260228_000439/raw/`
- Expected input files to Step 3 (8 model files):
  - `runs/snapshots/20260228_000439/raw/openai__gpt-5.2.jsonl`
  - `runs/snapshots/20260228_000439/raw/openai__gpt-5-mini.jsonl`
  - `runs/snapshots/20260228_000439/raw/openai__gpt-5-nano.jsonl`
  - `runs/snapshots/20260228_000439/raw/anthropic__claude-opus-4-6.jsonl`
  - `runs/snapshots/20260228_000439/raw/anthropic__claude-sonnet-4-5-20250929.jsonl`
  - `runs/snapshots/20260228_000439/raw/anthropic__claude-haiku-4-5-20251001.jsonl`
  - `runs/snapshots/20260228_000439/raw/gemini__gemini-2.5-pro.jsonl`
  - `runs/snapshots/20260228_000439/raw/gemini__gemini-2.5-flash.jsonl`

### 6.2 Authoritative generation mapping for each aggregated output

1. `runs/aggregated/dataframe.csv`
   - Script: `src/03_features_and_metrics.py`
   - Function path: `main()` (loads all `*.jsonl` in `--input_dir`, dedupes, computes features/metrics, writes CSV)
   - Input requirement: JSONL raw files in `--input_dir` (default `runs/raw`)
   - Output arg: `--output runs/aggregated/dataframe.csv`

2. `runs/aggregated/results_by_model.json`
   - Script: `src/04_analysis_and_plots.py`
   - Function path: `main()` builds per-model `results` dict and writes JSON
   - Upstream input requirement: `--input runs/aggregated/dataframe.csv`
   - Output arg: `--results runs/aggregated/results_by_model.json`

3. `runs/aggregated/summary_table.csv`
   - Script: `src/04_analysis_and_plots.py`
   - Function path: `main()` builds `summary` rows and writes CSV via `csv.DictWriter`
   - Upstream input requirement: `--input runs/aggregated/dataframe.csv`
   - Output arg: `--summary runs/aggregated/summary_table.csv`

4. `runs/aggregated/meta.json`
   - Script: `src/04_analysis_and_plots.py`
   - Function path: `main()` calls `_write_meta(Path(args.meta), args.config, cfg, rows)` at end
   - Meta writer: `_write_meta(...)` computes timestamp/config hash/git commit/providers/models/n/seed/tau and writes JSON
   - Upstream input requirement: same dataframe rows read from `--input runs/aggregated/dataframe.csv`
   - Output arg: `--meta runs/aggregated/meta.json`

### 6.3 Regeneration chain (commands to run in PASS 2.2, not executed in STEP 2.1)

Important: Step 3 reads `runs/raw/*.jsonl`, so authoritative snapshot files must first be staged into `runs/raw/` (or Step 3 must be pointed to the snapshot dir directly).

Recommended exact commands:

```bash
# 0) Stage authoritative raw snapshot into active raw dir
rm -rf runs/raw
mkdir -p runs/raw
cp runs/snapshots/20260228_000439/raw/*.jsonl runs/raw/

# 1) Regenerate aggregated dataframe from raw snapshot
python3 src/03_features_and_metrics.py \
  --config configs/models.yaml \
  --input_dir runs/raw \
  --output runs/aggregated/dataframe.csv

# 2) Regenerate analysis aggregates (results/summary/meta)
python3 src/04_analysis_and_plots.py \
  --config configs/models.yaml \
  --input runs/aggregated/dataframe.csv \
  --outdir figures \
  --results runs/aggregated/results_by_model.json \
  --summary runs/aggregated/summary_table.csv \
  --meta runs/aggregated/meta.json \
  --examples paper/top_mismatch_examples.md
```

Equivalent orchestrated path (same script entry points) is also defined in `run_repro.sh` as `run_step3()` then `run_step4()`.

## 7) PASS 3 — STEP 3.1 table-to-source mapping

Goal of this step: map every paper table reference in `revised_submission_with_new_results.tex` to its concrete source artifact(s) and generating code path.

### 7.1 Mapping inventory

1. `tables/summary` (Table `tab:main`)
   - Manuscript input: `\input{tables/summary}`
   - Paper table file: `tables/summary.tex`
   - Status: **generated-derived table file** (materialized from regenerated aggregates)
   - Upstream data source: `runs/aggregated/summary_table.csv`
   - Generating script/function: `src/04_analysis_and_plots.py` (`main()`, `--summary` output)

2. `tables/corr` (Table `tab:corr`)
   - Manuscript input: `\input{tables/corr}`
   - Paper table file: `tables/corr.tex`
   - Status: **generated-derived table file** (materialized from regenerated aggregates)
   - Upstream data source: `runs/aggregated/results_by_model.json` (`correlations` block per model)
   - Generating script/function: `src/04_analysis_and_plots.py` (`main()`, `results` object written via `--results`)

3. `tables/calibration` (Table `tab:calibration`)
   - Manuscript input: `\input{tables/calibration}`
   - Paper table file: `tables/calibration.tex`
   - Status: **generated-derived table file** (materialized from regenerated calibration exports)
   - Upstream data source: `runs/aggregated/calibration/calibration_summary.csv`
   - Generating script/function: `src/05_calibration_analysis.py` (`main()`, `calibration_summary.csv`)

4. `tables/metric_robustness` (Table `tab:metric_robustness`)
   - Manuscript input: `\input{tables/metric_robustness}`
   - Paper table file: **currently unresolved in paper tree** (no `tables/metric_robustness.tex` committed in this pass)
   - Status: **expected generated table**
   - Upstream data source: `runs/aggregated/metric_robustness/metric_robustness_summary.csv`
   - Closest generated TeX artifact: `runs/aggregated/metric_robustness/metric_robustness_summary.tex`
   - Generating script/function: `src/06_metric_robustness.py` (`main()`, writes csv/json/md/tex summary files)

5. Inline illustrative examples table (Table `tab:examples` in manuscript body)
   - Manuscript location: explicit `\begin{table}...\end{table}` block in `revised_submission_with_new_results.tex`
   - Status: **handwritten table in manuscript**
   - Upstream source: `paper/top_mismatch_examples.md` (exported examples list)
   - Generating script/function for source list: `src/04_analysis_and_plots.py` (`--examples` output)
   - Note: final 3-row selection and wording are manually curated in manuscript.

6. `tables/robustness` (Appendix Table `tab:robustness`)
   - Manuscript input: `\input{tables/robustness}`
   - Paper table file: **currently unresolved in paper tree** (no `tables/robustness.tex` committed in this pass)
   - Status: **expected generated-or-curated table (not yet materialized)**
   - Candidate upstream data source: `runs/aggregated/results_by_model.json` (contains `mismatch_rate_overall` and `mismatch_rate_overall_global_q20_tau_0.9`)
   - Candidate generator: `src/04_analysis_and_plots.py` (`main()`, `results` payload)

### 7.2 Regeneration commands used for source verification

```bash
mkdir -p runs/raw && cp runs/snapshots/20260228_000439/raw/*.jsonl runs/raw/
python3 src/03_features_and_metrics.py --config configs/models.yaml --input_dir runs/raw --output runs/aggregated/dataframe.csv
python3 src/04_analysis_and_plots.py --config configs/models.yaml --input runs/aggregated/dataframe.csv --outdir figures --results runs/aggregated/results_by_model.json --summary runs/aggregated/summary_table.csv --meta runs/aggregated/meta.json --examples paper/top_mismatch_examples.md
python3 src/05_calibration_analysis.py --config configs/models.yaml --input runs/aggregated/dataframe.csv --outdir runs/aggregated/calibration
python3 src/05_secondary_metric.py --input runs/aggregated/dataframe.csv --outdir runs/aggregated/secondary_metric --backend auto
python3 src/06_metric_robustness.py --input runs/aggregated/dataframe.csv --secondary_scores runs/aggregated/secondary_metric/secondary_metric_scores.csv --outdir runs/aggregated/metric_robustness
```

## 8) PASS 4A — figure file/linkage audit and repair

Goal of this step: audit all LaTeX figure environments in the manuscript and fix only figure linkage issues (paths, filenames, local labels/refs, obvious caption mismatches).

### 8.1 Figure-to-file mapping audit

Manuscript audited: `revised_submission_with_new_results.tex`

| Figure label | Caption (short) | Included file path in manuscript | Exists on disk | Likely generating code path |
|---|---|---|---|---|
| `fig:conf_vs_complexity` | Source-side surface-complexity proxy vs self-reported confidence | `figures/fig1_scatter_difficulty_vs_conf.pdf` | Yes | `src/04_analysis_and_plots.py` (`savefig` for `fig1_scatter_difficulty_vs_conf`) |
| `fig:reliability` | Overlaid reliability diagram with 10 bins | `figures/fig2_reliability_diagram_overlay.pdf` | Yes | `src/04_analysis_and_plots.py` (`savefig` for `fig2_reliability_diagram_overlay`) |
| `fig:mismatch_by_complexity` | Mismatch@0.9 by surface-complexity quartile | `figures/fig3_mismatch_by_difficulty_bucket.pdf` | Yes | `src/04_analysis_and_plots.py` (`savefig` for `fig3_mismatch_by_difficulty_bucket`) |
| `fig:frontier` | Secondary quality--latency view across models | `figures/fig4_efficiency_frontier.pdf` | Yes | `src/04_analysis_and_plots.py` (`savefig` for `fig4_efficiency_frontier`) |

### 8.2 Linkage/label fixes applied in PASS 4A

- No `\includegraphics` path or filename repairs were needed.
- No figure-label/reference repairs were needed (all `fig:*` labels are referenced in text).
- No obvious caption/file mismatch required correction.

### 8.3 Deterministic figure generation scripts (added in PASS 4A)

- `scripts/generate_figures.sh`
  - Authoritative input lock: `runs/snapshots/20260228_000439/raw/*.jsonl`
  - Deterministic flow:
    1. stage snapshot JSONL files into `runs/raw/`;
    2. regenerate `runs/aggregated/dataframe.csv` via `src/03_features_and_metrics.py`;
    3. regenerate manuscript figure binaries via `src/04_analysis_and_plots.py` into `figures/`.
  - Script intentionally regenerates binaries locally but those binaries are not committed as part of this pass.

### 8.4 Figure-to-generator-script mapping

| Manuscript figure file | Local regeneration script |
|---|---|
| `figures/fig1_scatter_difficulty_vs_conf.pdf` | `bash scripts/generate_figures.sh` |
| `figures/fig2_reliability_diagram_overlay.pdf` | `bash scripts/generate_figures.sh` |
| `figures/fig3_mismatch_by_difficulty_bucket.pdf` | `bash scripts/generate_figures.sh` |
| `figures/fig4_efficiency_frontier.pdf` | `bash scripts/generate_figures.sh` |

### 8.5 Figures still requiring logical verification/regeneration

- Logical verification still recommended after regeneration (visual QA + manuscript compile check), but no broken file links were found in this audit.
