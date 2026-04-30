# FLLM 2026 Positioning Notes

This repository supports a **black-box LLM reliability** contribution, using MT as a controlled testbed.

## Emphasis for FLLM framing
- Core question: whether self-reported confidence is portable across provider APIs under a shared protocol.
- Main finding: confidence scales are provider-dependent; fixed thresholds are non-portable.
- Reliability implications: threshold-based routing/abstention can induce materially different failure modes across providers.
- Calibration implication: post-hoc isotonic remapping can improve provider-local alignment but does not restore global portability.
- Scope guardrail: operational chrF-based targets are reproducible proxies, not semantic correctness labels.

## Keep conservative wording
- Do not claim cross-prompt invariance from offline bundle (non-baseline variants absent).
- Do not claim semantic correctness calibration (no bundled human semantic labels).
- Treat MT as a controlled benchmarked environment for LLM confidence reliability rather than the only intended application domain.
