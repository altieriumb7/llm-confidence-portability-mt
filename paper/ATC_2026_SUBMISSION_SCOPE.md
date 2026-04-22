# IEEE ATC 2026 Submission Scope (Conservative)

This note documents what is and is not currently supported for a possible IEEE ATC 2026 submission.

## Intended framing

- Trustworthy AI / reliability of black-box confidence signals.
- Provider-dependent uncertainty behavior under a shared protocol.
- Risk of reusing one confidence threshold across providers for routing/abstention.

The manuscript does **not** claim a general autonomous-systems contribution beyond these reliability implications.

## Manuscript variants

- Full manuscript: `revised_submission_with_new_results.tex`
- ATC-compressed draft: `revised_submission_atc2026_compressed.tex`

The compressed draft is a conservative condensation of already bundled evidence.

## Evidence actually bundled offline

- Raw snapshot for offline regeneration: `runs/snapshots/20260228_000439/raw/*.jsonl`
- Aggregated outputs: `runs/aggregated/*`
- Generated tables and figures consumed by TeX: `tables/*.tex`, `figures/*`

## Explicit non-claims / unresolved risks

- Page-limit pressure remains (ATC full paper target: 6 pages + up to 2 overlength pages).
- Venue fit is plausible but partial (trustworthy reliability angle stronger than MT-centric framing).
- Semantic validation is incomplete (semantic-audit scaffold exists; bundled labels are zero).
- Prompt-variant robustness is incomplete (non-baseline outputs not bundled).
- Fresh raw generation is not self-contained (requires live provider APIs and credentials).
- COMET/xCOMET learned-metric checkpoints are not bundled offline.
- Bibliography packaging remains partial (`references.bib` compatibility-only; bundled entries in `added_refs.bib`).
