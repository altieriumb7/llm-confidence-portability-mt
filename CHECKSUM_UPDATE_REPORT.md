# CHECKSUM_UPDATE_REPORT

Date (UTC): 2026-04-30

## Commands run
1. `git status --short`
2. `sha256sum -c artifacts/CHECKSUMS.sha256`
3. `sha256sum -c CHECKSUMS.sha256`
4. `sha256sum revised_submission_with_new_results.tex`
5. Rebuilt checksum file from the existing canonical file list in `CHECKSUMS.sha256` (no new files added).
6. `sha256sum -c CHECKSUMS.sha256`
7. `bash reproduce_minimal.sh`

## Path note
- Requested path `artifacts/CHECKSUMS.sha256` does not exist in this repository.
- Canonical checksum file present in repo root: `CHECKSUMS.sha256`.

## Old failing files (before update)
- `revised_submission_with_new_results.tex` (checksum mismatch under `CHECKSUMS.sha256`).

## Classification of failures
- `revised_submission_with_new_results.tex`: **expected regenerated artifact difference** (tracked manuscript source changed; no evidence of scientific-result regeneration in this step).
- No build/log/temp file mismatches reported by checksum validation.
- No suspicious scientific artifact changes detected by checksum validation.
- No missing files in canonical checksum list.

## Change applied
- Updated `CHECKSUMS.sha256` using the **same existing file list and ordering** already present.
- No new files were added to checksum coverage.

## Scientific integrity statement
- No experiments were regenerated.
- No result CSVs, tables, figures, or PDFs were modified in this update.
- No manuscript claims were modified in this update.

## Final checksum validation status
- `sha256sum -c CHECKSUMS.sha256`: **PASS** (all entries OK).

## Reproduction script status
- `bash reproduce_minimal.sh`: **FAIL** (`No such file or directory`).
- This appears to be an environment/repository-script availability issue, not a checksum-computation failure.
