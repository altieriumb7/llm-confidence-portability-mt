# Overleaf project: Confidence--Difficulty Mismatch in MT

Upload the whole zip to Overleaf (New Project → Upload Project).

## Compile
- Main file: `main.tex`
- Bibliography: `references.bib`

## Current submission-ready source
`main.tex` is the cleaned, submission-ready source. The project now includes the patched section files, synchronized tables, corrected figure paths, and a compiled `main.pdf` for reference.

## Assets included
- Figures: `figures/*.pdf`
- Tables: `tables/*.tex`
- Sections: `sections/*.tex`
- References: `references.bib`

## Notes
- `main_v2.tex` has been synchronized with `main.tex` for convenience.
- Older historical files are kept only as repository leftovers and should not be used for submission.


## Deterministic regeneration scripts (no binary artifacts in commits)

Use bundled raw snapshot data as the authority and regenerate outputs locally instead of committing regenerated binary files (`.png`, `.pdf`, `.jpg`, etc.).

- Regenerate core table/source outputs (no plots):

```bash
bash scripts/regenerate_tables.sh
```

- Regenerate figures from `runs/aggregated/dataframe.csv`:

```bash
bash scripts/regenerate_figures.sh
```

Both scripts are deterministic wrappers around the existing Python pipeline stages and keep manuscript-facing paths (`figures/*`, `runs/aggregated/*`, `paper/top_mismatch_examples.md`) consistent.

---

## Reproduction paths (code)

For code-side reproduction, use `REPRODUCIBILITY_CHECKLIST.md`.

- **Offline (recommended for deterministic regeneration from bundled data):**
  regenerate `runs/aggregated/{dataframe.csv,results_by_model.json,summary_table.csv,meta.json}` from
  `runs/snapshots/20260228_000439/raw/*.jsonl` with no API keys.
- **Live API path:** Step 2 translation/confidence generation requires provider keys and network calls.
- **Optional dependencies:** COMET-backed secondary metric analysis is optional and not required for core aggregates.

If you only need core aggregates, follow the checklist’s offline section and skip API-backed steps.
