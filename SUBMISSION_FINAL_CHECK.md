# SUBMISSION_FINAL_CHECK

Date (UTC): 2026-04-30
Target venue assessed: **FLLM 2026** (confidence/MT repository)
Auditor mode: freeze-stage pre-submission check (no scientific-result changes)

## 1) Repository cleanliness and release markers

### Commands run
- `git status --short --branch`
- `git log --oneline -5`
- `git tag --list`

### Result
- Branch status: clean working tree on branch `work`.
- Last 5 commits inspected.
- **Blocking:** required submission tag `submission-fllm-2026` is **missing** (no tags returned).

Status: **FAIL (blocking)**

## 2) PDF readiness

### Checks performed
- Verified expected final PDF path exists: `revised_submission_with_new_results.pdf`.
- Attempted structural checks with local tooling:
  - `pdfinfo revised_submission_with_new_results.pdf` (tool unavailable)
  - Python byte-level sanity checks (header, EOF marker, file size)

### Result
- PDF file exists and is non-empty.
- Header is `%PDF-1.5` and EOF marker is present.
- Could not run standard page-count/openability tooling in this environment (missing `pdfinfo` and PDF Python libs).
- Could not visually inspect figures/tables for readability in this CLI-only environment.

Status: **WARN (environment-limited; non-blocking pending manual visual check)**

## 3) LaTeX build health

### Commands run
- `bash scripts/build_pdf.sh`
- `rg -n "undefined|Citation|Reference|LaTeX Warning|Overfull|Missing|not found|Rerun" revised_submission_with_new_results.log`

### Result
- Build command failed because TeX engine is unavailable (`latexmk`/`tectonic` not installed).
- Existing log scan did **not** reveal undefined citations/references from searched patterns.
- Existing log shows multiple overfull boxes, including severe values (up to ~267pt).

Status: **WARN**
- Build inability is environment/tooling limitation.
- Severe overfull boxes should be reviewed in PDF output before submission.

## 4) Reviewer-visible unfinished markers

### Command run
- `rg -n -i "TODO|FIXME|WIP|placeholder|temporary|unfinished" revised_submission_with_new_results.tex paper/*.md README.md REPRODUCIBILITY*.md ARTIFACT*.md CLAIMS_TO_ARTIFACTS.md`

### Result
- Matches found mostly in documentation discussing known limitations and bibliography status (intentional status notes).
- No obvious accidental `TODO/FIXME/WIP` placeholders found in manuscript narrative requiring freeze-stage edits.

Status: **PASS**

## 5) Claims and limitations audit (overclaim risk)

### Files inspected
- `revised_submission_with_new_results.tex` (abstract/introduction/results/discussion/limitations)

### Result
- Framing is generally cautious and scoped (operational target vs semantic correctness clearly stated).
- No strong overclaim found about full semantic calibration or broad generalization.
- Prompt-robustness limitations and incomplete semantic annotations are explicitly stated.

Status: **PASS**

## 6) Repository links in paper

### Checks performed
- Located repository URL mention in manuscript.
- Attempted connectivity check:
  - `git ls-remote --heads https://github.com/altieriumb7/llm-confidence-portability-mt.git`

### Result
- URL string exists in manuscript.
- Remote connectivity check failed in this environment (`CONNECT tunnel failed, response 403`), so reachability could not be validated here.
- Required submission tag is not present locally (`submission-fllm-2026`), which also affects discoverability expectations.

Status: **FAIL (blocking due to missing submission tag)**

## 7) Submission-policy risk scan

### Files inspected
- `revised_submission_with_new_results.tex`

### Result
- Manuscript currently contains explicit author identity (`\author{Umberto Altieri}`).
- Manuscript includes a direct repository URL.
- These are potential double-blind conflicts **if** FLLM 2026 submission track is anonymized.
- Could not verify venue policy text from this environment; treat as policy risk requiring organizer-policy confirmation.

Status: **WARN (potentially blocking depending on track policy)**

## Blocking issues
1. Missing required release tag: **`submission-fllm-2026`**.

## Non-blocking issues / warnings
1. Could not run full PDF/page-count and visual checks due to missing PDF tooling.
2. Could not rebuild TeX locally due to missing TeX engines.
3. Existing log reports several overfull boxes, including severe ones.
4. Potential anonymization risk (author name + repo link) depending on venue policy.

## Exact files inspected
- `revised_submission_with_new_results.tex`
- `revised_submission_with_new_results.log`
- `revised_submission_with_new_results.pdf` (byte-level check only)
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

## Final recommendation
**READY WITH MINOR WARNINGS** if and only if the required submission tag is created before upload and policy checks are confirmed.

Given the currently missing required tag, operational recommendation at this instant is: **NOT READY**.
