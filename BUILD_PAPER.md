# Paper Build Workflow

## Canonical command for submission PDF (10 pages)

```bash
bash run_paper.sh --variant 10page
```

This is the **only recommended submission build path**.

It will:
1. regenerate metadata-driven tables and figures (`bash scripts/generate_paper_assets.sh`),
2. compile `revised_submission_with_new_results_10p.tex`,
3. write the PDF to `build/paper_10page.pdf`,
4. print page count via `pdfinfo`,
5. fail with non-zero exit if page count is greater than 10.

## Long draft build (non-submission)

```bash
bash run_paper.sh --variant long
```

Outputs: `build/paper_long.pdf`.

## Entrypoints

- 10-page submission source: `revised_submission_with_new_results_10p.tex`
- long draft source: `revised_submission_with_new_results.tex`
- variant mapping: `configs/paper.yaml`

## Notebook workflow guidance

No tracked `.ipynb` notebook currently exists in this repository for paper compilation. If you use a local notebook, call the canonical shell command directly:

```bash
!bash run_paper.sh --variant 10page
```

Do **not** call LaTeX directly from notebook cells, to avoid accidentally compiling the long draft.
