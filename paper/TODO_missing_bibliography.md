# Bibliography packaging note

For reviewer artifact compatibility, this repository includes:
- `added_refs.bib` (curated entries that are actually bundled)
- `references.bib` (empty compatibility file so `\bibliography{references,added_refs}` resolves)

Canonical metadata for the historical `references.bib` was not bundled in this snapshot.

Current submission-safe status:
- Active manuscript citations are restricted to keys present in `added_refs.bib`.
- `references.bib` remains a compatibility include path placeholder and should not be treated as canonical metadata.

Open TODO for post-submission archival completeness:
- restore full historical bibliography metadata in `references.bib` with verifiable sources.
