# Submission Freeze Report (ATC 2026 final polish)

Date: 2026-04-30 (UTC)

## Scope
Final reviewer-safe freeze pass focused on wording conservatism, artifact reproducibility messaging, and offline validation. No scientific results, datasets, or conclusions were changed.

## Files changed
- `scripts/reproduce_offline_artifact.sh`
- `README.md`
- `REPRODUCIBILITY_CHECKLIST.md`
- `REPRODUCIBILITY.md` (added)
- `CHECKSUMS.sha256` (generated/updated)

## Reviewer-visible cleanup
- Scanned for reviewer-visible `TODO` / `FIXME` / `WIP` / `placeholder` / temporary wording markers.
- Kept intentional limitation documentation (e.g., bibliography boundary notes) and avoided removing explicit reproducibility caveats.

## Repro script messaging improvements
- Clarified that pip/install failures are usually environment/network/package-index issues.
- Added explicit manual installation instructions and offline wheelhouse fallback.
- Added rerun guidance (`--skip-install`) once dependencies are preinstalled.
- Experimental and analysis execution logic remains unchanged.

## Reproducibility docs polish
- Standardized explicit Level A/B/C definitions in reviewer-facing docs.
- Added one-command reviewer run guidance (`--skip-manuscript`) for deterministic A+B checks.
- Added checksum verification commands and interpretation notes.
- Kept boundary language conservative: offline bundle does not claim full live end-to-end reproducibility.

## Manuscript/claims synchronization audit
- Audited manuscript wording and artifact-claim framing for conservative systems-oriented language.
- Verified central claim remains scoped to operational portability under shared protocol.
- Confirmed no new experiments and no broadened claim scope.

## Checks run
1. `bash scripts/reproduce_offline_artifact.sh --skip-manuscript`
   - Pass; regenerated tables/figures/aggregates and passed consistency checks.
2. `make reviewer-check`
   - Pass with expected warning: TeX compile check skipped because `latexmk` unavailable in environment.
3. `sha256sum -c CHECKSUMS.sha256`
   - Pass after generating `CHECKSUMS.sha256` in repo root.
4. TeX compile attempt:
   - `latexmk` not installed in this environment.

## Remaining limitations (intentionally disclosed)
- Live provider/API reruns remain external-dependency paths (Level C, not artifact-only claim).
- Canonical legacy bibliography metadata remains partial in this snapshot; compatibility/bundled split is documented.
- No completed semantic-audit human labels in bundled snapshot.
- Experimental breadth remains bounded to current bundled protocol/snapshot.

## Final readiness judgment
**Ready for reviewer-facing ATC 2026 submission freeze** with conservative, artifact-faithful claims and explicit reproducibility boundaries.


## Binary artifact policy note
- Figure/image binaries were not retained in this follow-up change to keep the patch text-centric and push-safe; reviewer regeneration remains available via `bash scripts/reproduce_offline_artifact.sh --skip-manuscript`.
