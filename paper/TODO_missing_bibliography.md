# Bibliography packaging note

For reviewer artifact compatibility, this repository includes:
- `added_refs.bib` (curated entries that are actually bundled)
- `references.bib` (empty compatibility file so `\bibliography{references,added_refs}` resolves)

Canonical metadata for the historical `references.bib` was not bundled in this snapshot.

To avoid unresolved citation placeholders in the manuscript build, the current TeX source cites only keys that are present in `added_refs.bib`. Restoring the full historical bibliography remains a release blocker for a fully referenced final submission.
