# Claims to Artifacts Map (FLLM 2026 submission prep)

Scope: headline numeric claims in `revised_submission_with_new_results.tex`, mapped to bundled artifacts only.

## Legend
- **Supported**: claim directly matches available artifact values.
- **Partially supported**: artifacts exist but claim needs caveat or computation provenance is indirect.
- **Unsupported**: no direct artifact support found in bundle.

## Headline claim map

| Claim | Manuscript section | Supporting artifact path(s) | Row/column anchor | Regeneration command | Status |
|---|---|---|---|---|---|
| 500 WMT17 en-de samples | Abstract, Dataset, Reproducibility | `configs/models.yaml`, `runs/snapshots/20260228_000439/raw/*.jsonl` | `global.n=500`, `testset=wmt17`, `langpair=en-de` | `bash scripts/reproduce_offline_artifact.sh --skip-manuscript` | Supported |
| 4,000 outputs total | Abstract, Reproducibility | `runs/aggregated/dataframe.csv`, `tables/summary.tex` | 8 models x 500 each implied by summary rows and snapshot exports | `bash scripts/generate_paper_assets.sh` | Supported |
| 8 models across providers | Experimental setup | `configs/models.yaml`, `tables/summary.tex` | 8 `models:` entries; 8 table rows | `bash scripts/generate_paper_assets.sh` | Supported |
| Mean chrF range 54.0–60.1 | Abstract/main results | `tables/summary.tex` | `Mean chrF` min=54.01 (gemini flash), max=60.07 (gemini pro) | `bash scripts/generate_paper_assets.sh` | Supported |
| ECE range 0.076–0.180 | Abstract/main results | `tables/summary.tex` | `ECE (within-q20)` min=0.076, max=0.180 | `bash scripts/generate_paper_assets.sh` | Supported |
| Mismatch@0.9 range 0.2%–18.2% | Abstract/main results | `tables/summary.tex` | `Mismatch@0.9` min=0.2%, max=18.2% | `bash scripts/generate_paper_assets.sh` | Supported |
| Parse-warning burden 443/4000 (11.1%) | Abstract, Limitations | `runs/aggregated/parse_audit/parse_warning_audit_summary.csv`, `tables/semantic_audit.tex` | Sum of `n_warning_rows` across models = 443; denominator 4000 | `python3 src/08_parse_warning_audit.py --config configs/models.yaml --input runs/aggregated/dataframe.csv --outdir runs/aggregated/parse_audit` | Partially supported (requires explicit sum step) |
| Raw-preview strict schema issues 452/4000 (11.3%), incl. 9 unflagged | Limitations | `runs/aggregated/parse_audit/parse_warning_audit_summary.csv` | Sum of `n_strict_schema_issue_rows`=452 and `n_unflagged_schema_issue_rows`=9 | Same as above | Partially supported (derived aggregate, not precomputed headline row) |
| Isotonic calibration mixed outcome; Opus ECE worsens | Calibration subsection, Discussion | `tables/calibration.tex`, `runs/aggregated/calibration/calibration_summary.csv` | Opus: `ECE before 0.084`, `ECE after 0.114` | `python3 src/05_calibration_analysis.py --config configs/models.yaml --input runs/aggregated/dataframe.csv --outdir runs/aggregated/calibration` | Supported |
| Prompt variants availability: only canonical bundled; others missing optional live runs | Prompt-sensitivity subsection | `tables/prompt_sensitivity_status.tex`, `configs/models.yaml` | canonical models=8; minimal/verifier models=0 | `python3 src/11_prompt_sensitivity.py --config configs/models.yaml --input runs/aggregated/dataframe.csv --outdir runs/aggregated/prompt_sensitivity` | Supported |
| Semantic-audit scaffold exists but labels unavailable (0) | Semantic-audit subsection, Limitations | `tables/semantic_audit.tex`, `runs/aggregated/semantic_audit/*` | `Valid human labels available = 0`; annotation categories all zero | `python3 src/09_semantic_audit.py --config configs/models.yaml --input runs/aggregated/dataframe.csv --outdir runs/aggregated/semantic_audit` | Supported |

## Notes for reviewers
- All claims above are tied to an **operational chrF-based target**, not human semantic correctness labels.
- Prompt robustness across non-baseline variants is intentionally not claimed from offline bundle alone.
