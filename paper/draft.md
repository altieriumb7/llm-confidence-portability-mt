# Multi-provider MT Confidence–Surface-Complexity Mismatch Study

## Abstract
We present a reproducible benchmark of confidence–difficulty mismatch in EN→DE machine translation across OpenAI GPT-5, Anthropic Claude 4.x, and Gemini 2.5 model families. We standardize confidence collection via self-rated confidence JSON in [0,1], compare against reference-based quality metrics, and analyze calibration/mismatch patterns against a source-side surface-complexity proxy.

## Introduction
MT quality is increasingly strong on standard benchmarks, but reliability under difficult inputs remains under-studied. Confidence estimates can be miscalibrated, especially when models remain highly confident on low-quality outputs. This work evaluates how often such mismatches occur and whether they correlate with a source-side surface-complexity proxy.

## Experimental Setup
For the current committed snapshot, we sample 500 WMT17 EN→DE sentences using a deterministic seed. We evaluate eight models: GPT-5.2 / mini / nano, Claude Opus / Sonnet / Haiku 4.5/4.6 variants, and Gemini 2.5 Pro / Flash. Identical prompts are used for all providers with temperature 0.

## Methods
The surface-complexity score is a source-side surface-complexity proxy built from source length, NER count, syntactic depth, and lexical rarity; punctuation is tracked separately but is not included in the summed score. Quality is measured with sentence-level chrF as the main metric, with sentence-level BLEU retained as an auxiliary metric in the code snapshot. Errors are defined using global and model-specific bottom-20% quality thresholds, with an additional within-model bottom-10% chrF robustness label. Calibration is measured with reliability diagrams and ECE; mismatch is defined as P(error & confidence>τ). Analyses are also stratified by surface-complexity quartile. Bootstrap confidence intervals are reported.

## Results
Outputs include: per-model summary table, comparative reliability and mismatch plots, and qualitative top examples where confidence is high but quality is poor.

## Discussion
Limitations include dependence on self-reported confidence and automatic metrics, plus provider-side variability in token accounting and latency behaviors.

## Future Work
Future extensions include token-level/logprob-based confidence where available, human evaluation, more language pairs, and adaptive surface-complexity-aware sampling.
