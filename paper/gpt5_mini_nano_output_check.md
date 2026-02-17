# GPT-5 mini / nano + Gemini 2.5 output format check

This note checks whether `gpt-5-mini`, `gpt-5-nano`, `gemini-2.5-pro`, and `gemini-2.5-flash` return outputs in the same strict JSON style as stable runs in this repository's translation+confidence pipeline.

## What we observed in the current aggregated sample

From `runs/aggregated/dataframe.csv` (1 sentence per model in this sample):

- `gpt-5.2` returned strict JSON-like outputs that were parsed cleanly (`parse_warnings` empty, confidence present).
- `gpt-5-mini` produced a truncated JSON-looking translation string and missing confidence parse (`translation_no_json;confidence_no_json;no_confidence_found`).
- `gpt-5-nano` returned unstructured translation output (the English source copied back) and missing confidence parse (`translation_no_json;confidence_no_json;no_confidence_found`).
- `gemini-2.5-pro` and `gemini-2.5-flash` showed the same formatting drift in the affected run (non-JSON text / prefixed text leading to parse warnings).

## Interpretation

Yes — in this run, `gpt-5-mini`, `gpt-5-nano`, `gemini-2.5-pro`, and `gemini-2.5-flash` did not consistently follow the strict one-object JSON schema.

## Mitigations implemented

1. Increased OpenAI response token budget caps in the client wrapper so strict JSON responses are less likely to be cut off when smaller models elaborate unexpectedly.
2. Improved parser coercion to recover useful values from *partial JSON fragments* (e.g., `{"translation":"...` or `{"confidence":0.93` without closing braces).
3. For non-JSON translation outputs, trigger `format_fix` first (instead of trusting loose text fallback), then only fall back to coercion if repair does not return valid JSON.
4. Increased Gemini response token caps and translation-format-fix token budget to reduce JSON truncation risk for `gemini-2.5-pro` and `gemini-2.5-flash`.

These changes make the pipeline more robust for mini/nano style drift while preserving existing strict parsing behavior when valid JSON is present.
