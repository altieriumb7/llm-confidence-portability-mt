# Repair Report — Final (STEP 6B)

Date: 2026-04-07 (UTC)

## 1) Authoritative source of truth used

The authoritative bundled raw source for deterministic reproduction is:

- `runs/snapshots/20260228_000439/raw/*.jsonl`

This snapshot is the documented baseline for offline regeneration of derived aggregates and manuscript-facing artifacts.

## 2) Artifacts regenerated or made reproducible via shell scripts

The following artifact classes are reproducible via documented shell entrypoints:

- `scripts/regenerate_tables.sh`
  - stages authoritative raw JSONL files into `runs/raw/`
  - regenerates non-binary aggregate artifacts under `runs/aggregated/`:
    - `dataframe.csv`
    - `results_by_model.json`
    - `summary_table.csv`
    - `meta.json`
- `scripts/regenerate_figures.sh`
  - regenerates binary plots under `figures/` (`.png`, `.pdf`)
  - regenerates manuscript-facing examples markdown:
    - `paper/top_mismatch_examples.md`
- `scripts/generate_all_artifacts.sh`
  - compatibility wrapper that forwards to `scripts/build_artifacts.sh`
  - preserves older documentation command paths while using current workflow internally

No binary artifacts were committed as part of this documentation repair step.

## 3) Stale artifacts replaced or deprecated

- Stale documentation references to `main.tex` / `main_v2.tex` were deprecated in paper documentation.
- Documentation now points to the true manuscript entrypoint: `revised_submission_with_new_results.tex`.
- README entrypoints were repaired to prefer script-based regeneration over manual binary artifact handling.

## 4) Manuscript claims corrected

Documentation claims were corrected to match repository reality:

- manuscript entrypoint corrected to `revised_submission_with_new_results.tex`
- bibliography file documented as `added_refs.bib`
- pre-compilation artifact workflow explicitly documented (current scripts plus `generate_all_artifacts.sh` compatibility wrapper)
- live-API dependency scope clarified: Step 2 (`src/02_translate_and_confidence.py`) only

## 5) Remaining unreproducible elements and limitations

The following limitations remain and are explicitly acknowledged:

1. **Live API dependence for raw generation**
   - Re-running Step 2 from scratch requires provider credentials/network and may not be byte-identical over time due to external model/service drift.
2. **Binary outputs are derived and environment-sensitive**
   - Figure binaries (`figures/*.png`, `figures/*.pdf`) are reproducible from local artifacts/scripts but may differ at byte level across environments/toolchain versions.
3. **Optional metric stack variability**
   - Optional COMET-backed secondary metric stages depend on local runtime/model availability.
4. **Toolchain dependency for manuscript build**
   - LaTeX compilation requires a local TeX toolchain (`latexmk`/`pdflatex` + `bibtex`) that is outside this repository.

## 6) Final light consistency sweep (STEP 6B)

A final light sweep was performed for broken references, stale filenames, obvious paper-code mismatches, and missing binary-artifact documentation.

### Sweep outcome

- No remaining stale `main.tex`/`main_v2.tex` references in current primary README entrypoints.
- Script entrypoints and manuscript entrypoint are now consistent across `README.md`, `paper/README.md`, and checklist docs.
- Binary artifact generation ownership is documented (`regenerate_figures.sh`, `build_artifacts.sh`, `generate_all_artifacts.sh` compatibility wrapper).

### Tiny residual fixes made

- Aligned `scripts/regenerate_tables.sh` `--examples` output target to `paper/top_mismatch_examples.md` for documentation/path consistency with the rest of the repo flow.
