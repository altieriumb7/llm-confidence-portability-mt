# TODO: missing bibliography source for full manuscript build

## Blocker

- `revised_submission_with_new_results.tex` calls `\bibliography{references,added_refs}`.
- `added_refs.bib` exists.
- `references.bib` is not present in this repository snapshot.

## What can be reproduced now

- All code-side aggregate outputs, figures, and supplementary analysis exports can be regenerated offline from the bundled snapshot.
- Manuscript compilation can proceed only after a LaTeX toolchain is installed and `references.bib` is supplied.

## Required external input

- `references.bib` from the paper-authoring repository or submission bundle.
