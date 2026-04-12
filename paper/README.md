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
   The script auto-selects `latexmk` (preferred) or `tectonic` if available.
   You can force one with:
   ```bash
   PDF_ENGINE=latexmk bash scripts/build_pdf.sh
   # or
   PDF_ENGINE=tectonic bash scripts/build_pdf.sh
   ```

## Bibliography note

The manuscript uses:
```tex
\bibliography{references,added_refs}
```

`added_refs.bib` contains the curated bundled entries. `references.bib` is present as an empty compatibility file because canonical bibliography metadata was not included in the bundled snapshot. The manuscript was adjusted to cite only bundled bibliography keys so PDF builds do not emit unresolved citation placeholders, but restoring canonical `references.bib` metadata remains necessary for a fully referenced camera-ready version.

## Google Colab quickstart

Paste this into a Colab cell to build the manuscript PDF:

```bash
%%bash
set -euo pipefail

REPO_URL="https://github.com/<your-org-or-user>/confidence-difficulty-mismatch-on-MT-evaluation.git"
REPO_DIR="confidence-difficulty-mismatch-on-MT-evaluation"

apt-get -qq update
apt-get -qq install -y latexmk texlive-latex-extra texlive-fonts-recommended texlive-bibtex-extra

if [[ ! -d "$REPO_DIR" ]]; then
  git clone "$REPO_URL" "$REPO_DIR"
fi

cd "$REPO_DIR"
bash scripts/generate_paper_assets.sh
PDF_ENGINE=latexmk bash scripts/build_pdf.sh

echo "Built PDF:"
ls -lh revised_submission_with_new_results.pdf
```
