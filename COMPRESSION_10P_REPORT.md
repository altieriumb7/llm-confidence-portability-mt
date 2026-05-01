# COMPRESSION_10P_REPORT

## Status
Compression draft created, but environment lacks a TeX toolchain (`latexmk`, `pdflatex` not installed), so compilation/page verification could not be executed in-container.

## Page counts
- Original page count: **18 pages** (from prior compile log entry for `revised_submission_with_new_results.pdf`).
- New page count: **Not verifiable in this environment** (no PDF build toolchain available).

## Files created/changed
- `revised_submission_with_new_results_10p.tex` (new compressed manuscript variant)
- `COMPRESSION_10P_REPORT.md` (this report)

## Sections compressed
- Related Work reduced to 3 compact paragraphs (MT evaluation/QE; calibration; verbalized confidence).
- Methods reduced to minimal reproducibility logic (setup, protocol, operational target, ECE, mismatch@0.9, complexity proxy summary).
- Results focused on main summary and isotonic calibration only.
- Discussion and limitations merged into one compact section.
- Conclusion reduced to two short paragraphs.
- Appendices removed from main manuscript variant; replaced with repository-reference sentence.

## Tables/Figures retained or removed
### Retained
- `tables/summary` (main summary table)
- `tables/calibration` (single compact mitigation table)
- Reliability figure (`fig2_reliability_diagram_overlay`) as one central qualitative figure.

### Removed from 10p variant
- Correlation table
- Metric robustness table
- Semantic audit table
- External comparator table
- Prompt sensitivity table
- Complexity scatter figure
- Mismatch-by-complexity figure
- Latency/efficiency figure
- All appendices in main PDF

## Headline numerical claims unchanged
Confirmed preserved in abstract/body:
- 500 WMT17 sentences
- 4,000 outputs
- 8 models
- mean chrF range 54.0--60.1
- ECE range 0.076--0.180
- mismatch@0.9 range 0.2%--18.2%
- parse-warning burden 443/4000
- isotonic calibration is provider-specific and does not restore portability

## Remaining risks
- No in-container LaTeX toolchain to confirm clean compile.
- No generated `revised_submission_with_new_results_10p.pdf` yet.
- <=10-page target not certifiable until external compile/page-count check is run.


## Rebuild command
- Run `./scripts/rebuild_10p_paper.sh revised_submission_with_new_results_10p.tex` to compile and print page-count status when TeX tools are available.
