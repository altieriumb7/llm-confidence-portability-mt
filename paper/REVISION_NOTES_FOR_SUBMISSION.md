# Revision Notes for Submission Readiness

## 1) Central claim narrowed to protocol-bounded portability
- **Change made:** Reworded abstract and conclusion to explicitly state that the main finding is about portability of self-reported confidence **under this protocol and operational target**, not a general claim about uncertainty quality.
- **Why needed:** Reviewer-facing credibility requires avoiding overgeneralization beyond the released setup.
- **Artifact evidence:** Main table metrics show provider-dependent operating points at the same threshold despite similar mean chrF; this is a comparative operating-point result, not universal uncertainty calibration evidence.
  - `tables/summary.tex`
  - `runs/aggregated/summary_table.csv`

## 2) Operational overlap target limitation made explicit in core narrative
- **Change made:** Added explicit wording that low quality is operationally chrF-quantile-defined and that some high-confidence mismatches can be overlap-metric mismatches rather than clear semantic failures.
- **Why needed:** Prevents over-interpretation of mismatch events as semantic errors.
- **Artifact evidence:** Exported mismatch examples and manuscript appendix already include overlap-based caveats.
  - `paper/top_mismatch_examples.md`
  - `revised_submission_with_new_results.tex` (methods/results/discussion sections)

## 3) Parse-warning / repair burden quantified in Results and Limitations
- **Change made:** Added quantitative parse-audit reporting in the Results section and mirrored key figures in Limitations.
- **Why needed:** Parse burden is a potential confound and should be visible, not implicit.
- **Artifact evidence (exact values):**
  - Warning rows: 443/4000 (11.1%)
  - Strict raw-preview issues: 452/4000 (11.3%)
  - Unflagged malformed raw-preview rows: 9/4000 (0.23%)
  - High-burden model example: Gemini 2.5 Flash 287/500 warning rows (57.4%)
  - OpenAI warning-field rows: 0/500 for each model in this snapshot
  - Source: `runs/aggregated/parse_audit/parse_warning_audit_summary.csv`
  - Source: `runs/aggregated/parse_audit/parse_warning_audit_summary.json`

## 4) BLEU fallback robustness text de-amplified
- **Change made:** Rephrased robustness interpretation to emphasize that BLEU fallback only partially reduces metric-specific concern and does not substitute for learned metrics/human evaluation.
- **Why needed:** Avoids implying stronger validation than the artifact supports.
- **Artifact evidence:** Secondary metric export labels BLEU fallback in this run and does not include COMET outputs.
  - `runs/aggregated/secondary_metric/secondary_metric_meta.json`
  - `runs/aggregated/metric_robustness/metric_robustness_summary.json`
  - `tables/metric_robustness.tex`

## 5) Consistency with fixed threshold definition retained
- **Change made:** Manuscript wording remains aligned with strict mismatch definition `P(low_quality AND confidence > tau)` and keeps `tau=0.9` as the fixed operating point.
- **Why needed:** Ensures exact consistency with updated analysis code and regenerated artifacts.
- **Artifact evidence:**
  - `src/05_calibration_analysis.py`
  - `src/04_analysis_and_plots.py`
  - `runs/aggregated/meta.json`

## 6) Prompt wording claim aligned with released code paths
- **Change made:** Updated manuscript wording to state that released canonical runs use shared prompt-renderer templates across providers, with provider-specific API adapters only.
- **Why needed:** Removed paper↔repo contradiction claiming provider-specific shorter wording in baseline runs.
- **Artifact evidence:**
  - `src/utils/prompt_variants.py`
  - `src/providers/openai_client.py`
  - `src/providers/anthropic_client.py`
  - `src/providers/gemini_client.py`

## 7) Bibliography failure mode made explicit and placeholders removed
- **Change made:** Manuscript citation usage was constrained to keys present in bundled `added_refs.bib`; documentation now explicitly states that canonical `references.bib` metadata is missing in this release.
- **Why needed:** Prevents unresolved citation placeholders while avoiding fabricated bibliography entries.
- **Artifact evidence:**
  - `revised_submission_with_new_results.tex`
  - `paper/TODO_missing_bibliography.md`
  - `paper/README.md`
