# Parse-warning audit summary

| model | n_warning_rows | warning_rate | n_repaired_rows | n_fallback_rows | n_translation_warning_rows | n_confidence_warning_rows | n_both_warning_rows | mean_conf_clean | mean_conf_warning | ece_all | ece_clean | mismatch_all | mismatch_clean | top_warning_token |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| anthropic/claude-haiku-4-5-20251001 | 29 | 0.0580 | 0 | 29 | 29 | 0 | 0 | 0.8991 | 0.5641 | 0.0943 | 0.0835 | 0.1340 | 0.1316 | translation_no_json |
| anthropic/claude-opus-4-6 | 58 | 0.1160 | 0 | 58 | 58 | 0 | 0 | 0.9222 | 0.4386 | 0.0869 | 0.0723 | 0.0760 | 0.0860 | translation_no_json |
| anthropic/claude-sonnet-4-5-20250929 | 68 | 0.1360 | 0 | 68 | 68 | 0 | 0 | 0.9388 | 0.5869 | 0.0948 | 0.0933 | 0.1280 | 0.1250 | translation_no_json |
| gemini/gemini-2.5-flash | 287 | 0.5740 | 164 | 287 | 77 | 240 | 30 | 0.7736 | 0.6789 | 0.1479 | 0.1729 | 0.0420 | 0.0282 | confidence_no_json |
| gemini/gemini-2.5-pro | 1 | 0.0020 | 0 | 1 | 1 | 0 | 0 | 0.9842 | 0.0000 | 0.1802 | 0.1806 | 0.1820 | 0.1824 | translation_no_json |
| openai/gpt-5-mini | 0 | 0.0000 | 0 | 0 | 0 | 0 | 0 | 0.8819 | nan | 0.1522 | 0.1522 | 0.1280 | 0.1280 | none |
| openai/gpt-5-nano | 0 | 0.0000 | 0 | 0 | 0 | 0 | 0 | 0.7263 | nan | 0.0757 | 0.0757 | 0.0020 | 0.0020 | none |
| openai/gpt-5.2 | 0 | 0.0000 | 0 | 0 | 0 | 0 | 0 | 0.9239 | nan | 0.1339 | 0.1339 | 0.1520 | 0.1520 | none |
