import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent
sys.path.append(str(ROOT))

from utils.common import (
    append_jsonl,
    load_config,
    load_env,
    now_utc_iso,
    read_jsonl,
    retry_with_backoff,
    setup_logging,
    usage_to_tokens,
)
from utils.parse import coerce_confidence, parse_json_field, sanitize_translation

ENV_KEYS = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY", "gemini": "GEMINI_API_KEY"}


def get_client(provider: str):
    try:
        if provider == "openai":
            from providers import openai_client as c
        elif provider == "anthropic":
            from providers import anthropic_client as c
        elif provider == "gemini":
            from providers import gemini_client as c
        else:
            return None
        return c
    except Exception:
        return None


def filter_models(models: List[Dict], providers: str, names: str):
    provider_set = set(x.strip() for x in providers.split(",")) if providers else None
    name_set = set(x.strip() for x in names.split(",")) if names else None
    out = []
    for m in models:
        if provider_set and m["provider"] not in provider_set:
            continue
        if name_set and m["model_id"] not in name_set and m["label"] not in name_set:
            continue
        out.append(m)
    return out


def _rate(numerator: int, denominator: int) -> float:
    return 0.0 if denominator <= 0 else numerator / denominator


def _truncate(text: str, limit: int = 500) -> str:
    return str(text or "").strip()[:limit]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/models.yaml")
    ap.add_argument("--input", default="data/wmt_sample.jsonl")
    ap.add_argument("--outdir", default="runs/raw")
    ap.add_argument("--providers", default=None)
    ap.add_argument("--models", default=None)
    ap.add_argument("--max_samples", type=int, default=None)
    ap.add_argument("--dry_run", action="store_true")
    ap.add_argument("--progress_every", type=int, default=25)
    ap.add_argument("--fail_on_parse_rate", type=float, default=None)
    args = ap.parse_args()

    load_env()
    cfg = load_config(args.config)
    g = cfg["global"]
    logger = setup_logging(Path("runs/logs/translate.log"), name="translate")

    data = list(read_jsonl(Path(args.input)))
    if args.max_samples:
        data = data[: args.max_samples]

    selected_models = filter_models(cfg["models"], args.providers, args.models)
    if not args.models and not args.providers and len(selected_models) > 1:
        logger.info("No --models/--providers filter set: processing %d configured models.", len(selected_models))

    for m in selected_models:
        provider, model_id = m["provider"], m["model_id"]
        out_path = Path(args.outdir) / f"{provider}__{model_id}.jsonl"
        done_ids = {str(r["id"]) for r in read_jsonl(out_path) if "id" in r}

        key_name = ENV_KEYS[provider]
        api_key = os.getenv(key_name) or (os.getenv("GOOGLE_API_KEY") if provider == "gemini" else None)
        client = get_client(provider)

        if not args.dry_run and not api_key:
            logger.warning("Skipping %s/%s due to missing API key (%s)", provider, model_id, key_name)
            continue
        if not args.dry_run and client is None:
            logger.warning("Skipping %s/%s due to missing provider SDK", provider, model_id)
            continue

        logger.info("Running %s/%s existing=%d", provider, model_id, len(done_ids))
        total_pending = sum(1 for row in data if str(row["id"]) not in done_ids)
        logger.info("Input samples: %d | Existing cached: %d | Pending: %d", len(data), len(done_ids), total_pending)
        processed = 0
        parse_fail_translation = 0
        parse_fail_confidence = 0
        missing_confidence = 0

        for row in data:
            row_id = str(row["id"])
            if row_id in done_ids:
                continue
            try:
                warnings = []
                raw_translation = ""
                raw_confidence = ""

                if args.dry_run:
                    translation = row["ref"]
                    confidence = 0.5
                    tr_usage = cf_usage = fx_tr_usage = fx_cf_usage = {}
                    tr_lat = cf_lat = fx_tr_lat = fx_cf_lat = 0.0
                else:
                    raw_translation, tr_usage, tr_lat, _ = retry_with_backoff(
                        lambda: client.translate(row["src"], model_id, g, api_key), g["max_retries"], logger, "translate"
                    )
                    parsed_translation, tr_err = parse_json_field(raw_translation, "translation")
                    if parsed_translation is not None and str(parsed_translation).strip():
                        translation = str(parsed_translation).strip()
                        fx_tr_usage, fx_tr_lat = {}, 0.0
                    else:
                        parse_fail_translation += 1
                        warnings.append("translation_no_json")
                        translation = sanitize_translation(raw_translation)
                        fx_tr_usage, fx_tr_lat = {}, 0.0
                        if hasattr(client, "format_fix"):
                            fixed_translation, fx_tr_usage, fx_tr_lat, _ = retry_with_backoff(
                                lambda: client.format_fix(
                                    task="translation",
                                    previous_answer=raw_translation,
                                    original_input=row["src"],
                                    model_id=model_id,
                                    global_cfg=g,
                                    api_key=api_key,
                                ),
                                g["max_retries"],
                                logger,
                                "format_fix_translation",
                            )
                            fixed_parsed, _ = parse_json_field(fixed_translation, "translation")
                            if fixed_parsed is not None and str(fixed_parsed).strip():
                                translation = str(fixed_parsed).strip()
                                warnings.append("translation_format_fix")

                    if not translation:
                        translation = _truncate(raw_translation, 1000) or _truncate(row["src"], 1000) or "[translation unavailable]"

                    raw_confidence, cf_usage, cf_lat, _ = retry_with_backoff(
                        lambda: client.confidence(row["src"], translation, model_id, g, api_key),
                        g["max_retries"],
                        logger,
                        "confidence",
                    )
                    parsed_confidence, cf_err = parse_json_field(raw_confidence, "confidence")
                    confidence = coerce_confidence(parsed_confidence)
                    fx_cf_usage, fx_cf_lat = {}, 0.0
                    if confidence is None:
                        confidence = coerce_confidence(raw_confidence)
                    if confidence is None:
                        parse_fail_confidence += 1
                        warnings.append("confidence_no_json")
                        if hasattr(client, "format_fix"):
                            fixed_conf, fx_cf_usage, fx_cf_lat, _ = retry_with_backoff(
                                lambda: client.format_fix(
                                    task="confidence",
                                    previous_answer=raw_confidence,
                                    original_input=row["src"],
                                    translation=translation,
                                    model_id=model_id,
                                    global_cfg=g,
                                    api_key=api_key,
                                ),
                                g["max_retries"],
                                logger,
                                "format_fix_confidence",
                            )
                            fixed_parsed_conf, _ = parse_json_field(fixed_conf, "confidence")
                            confidence = coerce_confidence(fixed_parsed_conf)
                            if confidence is None:
                                confidence = coerce_confidence(fixed_conf)
                            if confidence is not None:
                                warnings.append("confidence_format_fix")

                if confidence is None:
                    missing_confidence += 1

                u1, u2 = usage_to_tokens(tr_usage), usage_to_tokens(cf_usage)
                uf1, uf2 = usage_to_tokens(fx_tr_usage), usage_to_tokens(fx_cf_usage)
                input_total = sum(v for v in [u1["input_tokens"], u2["input_tokens"], uf1["input_tokens"], uf2["input_tokens"]] if v is not None)
                output_total = sum(v for v in [u1["output_tokens"], u2["output_tokens"], uf1["output_tokens"], uf2["output_tokens"]] if v is not None)
                payload = {
                    "id": row["id"],
                    "src": row["src"],
                    "ref": row["ref"],
                    "hyp": translation,
                    "translation": translation,
                    "conf": confidence,
                    "confidence": confidence,
                    "provider": provider,
                    "model_id": model_id,
                    "latency_translate_s": tr_lat + fx_tr_lat,
                    "latency_conf_s": cf_lat + fx_cf_lat,
                    "input_tokens": input_total if any(v is not None for v in [u1["input_tokens"], u2["input_tokens"], uf1["input_tokens"], uf2["input_tokens"]]) else None,
                    "output_tokens": output_total if any(v is not None for v in [u1["output_tokens"], u2["output_tokens"], uf1["output_tokens"], uf2["output_tokens"]]) else None,
                    "timestamp_utc": now_utc_iso(),
                }
                if warnings:
                    payload["parse_warnings"] = ";".join(warnings)
                if raw_translation:
                    payload["raw_translation_preview"] = _truncate(raw_translation)
                if raw_confidence:
                    payload["raw_confidence_preview"] = _truncate(raw_confidence)
                append_jsonl(out_path, payload)

                done_ids.add(row_id)
                processed += 1
                if processed % max(1, args.progress_every) == 0 or processed == total_pending:
                    logger.info("Progress %s/%s: %d/%d completed", provider, model_id, processed, total_pending)
            except Exception as exc:
                logger.exception("Failed %s/%s id=%s: %s", provider, model_id, row["id"], exc)

        logger.info(
            "Summary %s/%s: processed=%d parse_fail_translation=%d parse_fail_confidence=%d missing_confidence=%d",
            provider,
            model_id,
            processed,
            parse_fail_translation,
            parse_fail_confidence,
            missing_confidence,
        )
        if args.fail_on_parse_rate is not None and processed > 0:
            combined_parse_fail = parse_fail_translation + parse_fail_confidence
            rate = _rate(combined_parse_fail, 2 * processed)
            logger.info("Combined parse fail rate for %s/%s: %.2f%%", provider, model_id, rate * 100)
            if rate > args.fail_on_parse_rate:
                raise RuntimeError(
                    f"Parse failure rate {rate:.3f} exceeded --fail_on_parse_rate {args.fail_on_parse_rate:.3f} "
                    f"for {provider}/{model_id}"
                )


if __name__ == "__main__":
    main()
