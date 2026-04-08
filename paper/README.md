# Paper Build Notes

This file contains only paper-specific build details.
For full artifact reproduction instructions, see `../ARTIFACT_GUIDE.md`.

## Manuscript source

- Main TeX file: `../revised_submission_with_new_results.tex`
- Tables consumed by TeX: `../tables/*.tex`
- Figures consumed by TeX: `../figures/*`

## Build sequence

From repository root:

1. Regenerate paper-facing assets:
   ```bash
   bash scripts/generate_paper_assets.sh
   ```
2. Build PDF (optional, requires LaTeX):
   ```bash
   bash scripts/build_pdf.sh
   ```

## Bibliography note

The manuscript uses:
```tex
\bibliography{references,added_refs}
```

`added_refs.bib` contains the curated added entries. `references.bib` is present as an empty compatibility file because canonical bibliography metadata was not included in the bundled snapshot. The manuscript can still be built for structure/layout checks, but unresolved citations will remain until canonical `references.bib` metadata is restored.
