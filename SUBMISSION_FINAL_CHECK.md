# SUBMISSION_FINAL_CHECK

Date (UTC): 2026-04-30  
Target venue assessed: **FLLM 2026** (confidence/MT repository)

## Freeze checksum (quick copy)

- Commit: `0a72c2736d3276b7927af831875c71819ffe61c2`
- Tree: `3339720451ef55cc3bf624d9f06f83338892abce`
- PDF SHA256: `ae74788476b96fb44599e3c9a4c65b4b3d952464b254d0f98b97ba0f3f6cf580`
- TeX SHA256: `7424b126a38f40f951661fb2cd09dd17ea692404b790158cec63d50e1533dd9f`
- CHECKSUMS.sha256 SHA256: `12a66d504487756e00dabcc6b21815f828c064aa472e1127c380ce219cd1275f`

## 1) Repository cleanliness

### Checks run
- `git status --short --branch`
- `git log --oneline -5`
- `git tag --list`

### Status: **PASS**
- Working tree is clean on branch `work`.
- Recent commit history is present and consistent with freeze-stage updates.
- Required submission tag **`submission-fllm-2026` exists**.

## 2) PDF readiness

### Checks run
- Verified final PDF file exists: `revised_submission_with_new_results.pdf`.
- Byte-level sanity check via Python (`%PDF` header and `%%EOF` trailer).
- Page count recovered from LaTeX build log line: `Output written on ... (18 pages, ...)`.
- Figure/table include-path existence check by parsing TeX (`\IfFileExists{...}` and `\input{...}` targets).

### Status: **PASS WITH WARNINGS**
- PDF file exists, is non-empty, has valid header/trailer markers.
- Log indicates a successfully produced PDF with **18 pages**.
- No missing included figures/tables detected from TeX include paths.
- CLI environment could not support manual visual inspection of rendered table readability/figure quality.

## 3) LaTeX build health

### Checks run
- `bash scripts/build_pdf.sh`
- `rg -n "undefined|Citation|Reference|LaTeX Warning|Overfull|Missing|not found|Rerun" revised_submission_with_new_results.log`

### Status: **WARN (environment-limited)**
- Local rebuild could not be run because TeX engine (`latexmk` or `tectonic`) is not installed in this environment.
- Existing log scan shows no unresolved-reference/citation errors in searched patterns.
- Overfull boxes are present; several are severe and should be visually reviewed before upload.

## 4) Reviewer-visible unfinished text

### Checks run
- `rg -n -i "TODO|FIXME|WIP|placeholder|temporary|unfinished" revised_submission_with_new_results.tex paper/*.md README.md REPRODUCIBILITY*.md ARTIFACT*.md CLAIMS_TO_ARTIFACTS.md`

### Status: **PASS**
- Matches are in limitation/status documentation and not accidental reviewer-facing unfinished manuscript text.

## 5) Claims and limitations scope audit

### Files inspected
- `revised_submission_with_new_results.tex` (abstract, introduction, results, discussion, limitations)

### Status: **PASS**
- Wording is generally scoped and avoids broad claims of semantic correctness calibration.
- Limitations about operational labels, missing bundled learned-metric checkpoints, and prompt-robustness scope are explicitly stated.
- No claim found implying full raw-to-paper reproducibility under all environments.

## 6) Repository link checks

### Checks run
- Located repository URL mention in manuscript.
- Attempted remote probe:
  - `git ls-remote --heads https://github.com/altieriumb7/llm-confidence-portability-mt.git`

### Status: **WARN (network-limited)**
- Repository URL is present in the manuscript text.
- Live reachability check could not be confirmed in this environment (`CONNECT tunnel failed, response 403`).
- Submission tag naming is now aligned locally (`submission-fllm-2026`).

## 7) Submission-policy risk scan

### Files inspected
- `revised_submission_with_new_results.tex`

### Status: **WARN (policy-dependent)**
- Manuscript includes explicit author name and direct repository URL.
- This is acceptable only if the submission track is not double-blind, or if disclosed by policy.

## Blocking issues
- **None currently identified inside repository state.**

## Non-blocking issues
1. Could not rerun full TeX build due to missing local TeX engine.
2. Could not perform human visual QA of PDF rendering in this CLI-only environment.
3. Potential anonymization conflict remains policy-dependent.

## Exact files inspected
- `SUBMISSION_FINAL_CHECK.md`
- `revised_submission_with_new_results.tex`
- `revised_submission_with_new_results.log`
- `revised_submission_with_new_results.pdf`
- `paper/README.md`
- `scripts/build_pdf.sh`
- `README.md`
- `REPRODUCIBILITY.md`
- `REPRODUCIBILITY_CHECKLIST.md`
- `ARTIFACT_GUIDE.md`
- `ARTIFACT_STATUS.md`
- `CLAIMS_TO_ARTIFACTS.md`
- `paper/REVISION_NOTES_FOR_SUBMISSION.md`
- `paper/TODO_missing_bibliography.md`

## 8) Freeze checksum / immutable snapshot identifiers

### Status: **PASS**
- Git commit (full): `53287472508c1386294a8e35b88f1c114e99e65c`
- Git commit (short): `53287472`
- Git tree object: `9c68e6c67884bb0da61c50ef28110048e9528ee7`
- `CHECKSUMS.sha256`: `12a66d504487756e00dabcc6b21815f828c064aa472e1127c380ce219cd1275f`
- `revised_submission_with_new_results.pdf`: `ae74788476b96fb44599e3c9a4c65b4b3d952464b254d0f98b97ba0f3f6cf580`
- `revised_submission_with_new_results.tex`: `7424b126a38f40f951661fb2cd09dd17ea692404b790158cec63d50e1533dd9f`

These identifiers freeze the audited repository state and key submission artifacts for traceability.

## Final recommendation
**READY WITH MINOR WARNINGS**.
