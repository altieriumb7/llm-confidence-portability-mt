# GPT-5 mini / nano output format check

This note checks whether `gpt-5-mini` and `gpt-5-nano` return outputs in the same strict JSON style as `gpt-5.2` in this repository's translation+confidence pipeline.

## What we observed in the current aggregated sample

From `runs/aggregated/dataframe.csv` (1 sentence per model in this sample):

- `gpt-5.2` returned strict JSON-like outputs that were parsed cleanly (`parse_warnings` empty, confidence present).
- `gpt-5-mini` produced a truncated JSON-looking translation string and missing confidence parse (`translation_no_json;confidence_no_json;no_confidence_found`).
- `gpt-5-nano` returned unstructured translation output (the English source copied back) and missing confidence parse (`translation_no_json;confidence_no_json;no_confidence_found`).

## Interpretation

Yes — in this run, `gpt-5-mini` and `gpt-5-nano` behaved differently from `gpt-5.2` for formatting/compliance, and did not consistently follow the strict one-object JSON schema.

## Mitigations implemented

1. Increased OpenAI response token budget caps in the client wrapper so strict JSON responses are less likely to be cut off when smaller models elaborate unexpectedly.
2. Improved parser coercion to recover useful values from *partial JSON fragments* (e.g., `{"translation":"...` or `{"confidence":0.93` without closing braces).

These changes make the pipeline more robust for mini/nano style drift while preserving existing strict parsing behavior when valid JSON is present.
