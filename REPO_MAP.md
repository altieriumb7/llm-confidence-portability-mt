# Repository map (reviewer quick scan)

## Active paths (used by current offline artifact workflow)
- `scripts/` — root-runnable orchestration for regeneration/validation.
- `src/` — analysis pipeline stages.
- `tools/` — table export and consistency checks.
- `runs/snapshots/20260228_000439/raw/` — bundled raw snapshot used for offline regeneration.
- `runs/aggregated/` — regenerated aggregate outputs.
- `tables/`, `figures/`, `paper/top_mismatch_examples.md` — manuscript-facing generated artifacts.
- `revised_submission_with_new_results.tex` — manuscript source entrypoint.

## Root commands from this repository
- Offline regeneration (recommended):
  - `bash scripts/reproduce_offline_artifact.sh --skip-manuscript`
- Paper-facing assets only:
  - `bash scripts/generate_paper_assets.sh`
- Validation only:
  - `bash scripts/validate_artifact.sh`
- Legacy-compatible wrapper:
  - `bash scripts/generate_all_artifacts.sh`
- Live/API path (credentials required):
  - `bash run_repro.sh --mode all`

## Requires live provider credentials/network
- `src/02_translate_and_confidence.py`
- `run_repro.sh` when running Step 2 / full `--mode all`.

## Archival/context paths
- `REPAIR_REPORT.md`
- `CHANGELOG_ARTIFACT_FIXES.md`

These are historical context documents; they are not the authoritative command source.
