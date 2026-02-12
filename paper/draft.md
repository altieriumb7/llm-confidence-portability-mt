# Multi-provider MT Confidence–Difficulty Mismatch Study

## Abstract
We present a reproducible benchmark of confidence–difficulty mismatch in EN→DE machine translation across OpenAI GPT-5, Anthropic Claude 4.x, and Gemini 3 model families. We standardize confidence collection via self-rated confidence JSON in [0,1], compare against reference-based quality metrics, and analyze calibration/mismatch patterns by source difficulty.

## Introduction
MT quality is increasingly strong on standard benchmarks, but reliability under difficult inputs remains under-studied. Confidence estimates can be miscalibrated, especially when models remain highly confident on low-quality outputs. This work evaluates how often such mismatches occur and whether they correlate with source difficulty.

## Experimental Setup
We sample WMT EN→DE sentences (default N=200, configurable to 500) using deterministic seeds. We evaluate: GPT-5.2 / mini / nano, Claude Opus/Sonnet/Haiku 4.5/4.6 variants, and Gemini 3 Pro/Flash preview models. Identical prompts are used for all providers with temperature 0.

## Methods
Difficulty features include source length, punctuation, NER count, syntactic depth, and lexical rarity. Quality is measured with sentence-level chrF (main) and BLEU (optional COMET). Errors are defined using global and model-specific bottom-20% quality thresholds. Calibration is measured with reliability diagrams and ECE; mismatch is defined as P(error & confidence>τ). Bootstrap confidence intervals are reported.

## Results
Outputs include: per-model summary table, comparative reliability and mismatch plots, and qualitative top examples where confidence is high but quality is poor.

## Discussion
Limitations include dependence on self-reported confidence and automatic metrics, plus provider-side variability in token accounting and latency behaviors.

## Future Work
Future extensions include token-level/logprob-based confidence where available, human evaluation, more language pairs, and adaptive difficulty-aware sampling.
