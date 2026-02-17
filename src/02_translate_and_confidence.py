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
from utils.llm_parse import coerce_confidence, coerce_translation, find_first_json, normalize_json_obj

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


def _debug_dump_raw(
    base_outdir: str,
    provider: str,
    model_id: str,
    row_id: str,
    raw_translation: str,
    raw_confidence: str,
    raw_translation_preview: str = "",
    raw_confidence_preview: str = "",
):
    model_tag = model_id.replace("/", "_")
    debug_dir = Path(base_outdir) / "_debug" / f"{provider}_{model_tag}"
    debug_dir.mkdir(parents=True, exist_ok=True)
    debug_path = debug_dir / f"id_{row_id}_raw.txt"

    has_translation_json = find_first_json(raw_translation) is not None
    has_confidence_json = find_first_json(raw_confidence) is not None

    debug_path.write_text(
        "=== metadata ===\n"
        f"provider: {provider}\n"
        f"model_id: {model_id}\n"
        f"row_id: {row_id}\n"
        f"translation_json_detected: {has_translation_json}\n"
        f"confidence_json_detected: {has_confidence_json}\n\n"
        "=== translation_preview ===\n"
        f"{raw_translation_preview or ''}\n\n"
        "=== confidence_preview ===\n"
        f"{raw_confidence_preview or ''}\n\n"
        "=== translation_raw ===\n"
        f"{raw_translation or ''}\n\n"
        "=== confidence_raw ===\n"
        f"{raw_confidence or ''}\n",
        encoding="utf-8",
    )


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
                warnings: list[str] = []
                raw_translation = ""
                raw_confidence = ""
                repaired_conf = ""

                if args.dry_run:
                    translation = row["ref"]
                    confidence = 0.5
                    tr_usage = cf_usage = fx_tr_usage = fx_cf_usage = {}
                    tr_lat = cf_lat = fx_tr_lat = fx_cf_lat = 0.0
                else:
                    raw_translation, tr_usage, tr_lat, tr_warn = retry_with_backoff(
                        lambda: client.translate(row["src"], model_id, g, api_key), g["max_retries"], logger, "translate"
                    )
                    if tr_warn:
                        warnings.append(str(tr_warn))

                    translation = ""
                    parsed_tr = find_first_json(raw_translation)
                    if parsed_tr is not None:
                        normalized_tr, tr_norm_warnings = normalize_json_obj(parsed_tr[0], "translation")
                        warnings.extend(tr_norm_warnings)
                        if normalized_tr:
                            translation = normalized_tr["translation"]

                    fx_tr_usage, fx_tr_lat = {}, 0.0
                    if not translation:
                        parse_fail_translation += 1
                        warnings.append("translation_no_json")
                        translation = coerce_translation(raw_translation)

                    if not translation and hasattr(client, "format_fix"):
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
                        fixed_tr = find_first_json(fixed_translation)
                        if fixed_tr is not None:
                            normalized_tr, tr_norm_warnings = normalize_json_obj(fixed_tr[0], "translation")
                            warnings.extend(tr_norm_warnings)
                            if normalized_tr:
                                translation = normalized_tr["translation"]
                                warnings.append("translation_format_fix")

                    if not translation:
                        translation = _truncate(raw_translation, 1000) or _truncate(row["src"], 1000) or "[translation unavailable]"

                    raw_confidence, cf_usage, cf_lat, cf_warn = retry_with_backoff(
                        lambda: client.confidence(row["src"], translation, model_id, g, api_key),
                        g["max_retries"],
                        logger,
                        "confidence",
                    )
                    if cf_warn:
                        warnings.append(str(cf_warn))

                    fx_cf_usage, fx_cf_lat = {}, 0.0
                    confidence = None
                    parsed_cf = find_first_json(raw_confidence)
                    if parsed_cf is not None:
                        normalized_cf, cf_norm_warnings = normalize_json_obj(parsed_cf[0], "confidence")
                        warnings.extend(cf_norm_warnings)
                        if normalized_cf:
                            confidence = normalized_cf["confidence"]

                    if confidence is None:
                        parse_fail_confidence += 1
                        warnings.append("confidence_no_json")
                        confidence, cf_coerce_warn = coerce_confidence(raw_confidence)
                        if cf_coerce_warn:
                            warnings.append(cf_coerce_warn)

                    if confidence is None:
                        if hasattr(client, "repair_confidence"):
                            repaired_conf, fx_cf_usage, fx_cf_lat, _ = retry_with_backoff(
                                lambda: client.repair_confidence(
                                    src=row["src"],
                                    hyp=translation,
                                    previous_answer=raw_confidence,
                                    model_id=model_id,
                                    global_cfg=g,
                                    api_key=api_key,
                                ),
                                g["max_retries"],
                                logger,
                                "repair_confidence",
                            )
                        elif hasattr(client, "format_fix"):
                            repaired_conf, fx_cf_usage, fx_cf_lat, _ = retry_with_backoff(
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
                        else:
                            repaired_conf = ""

                        if repaired_conf:
                            fixed_cf = find_first_json(repaired_conf)
                            if fixed_cf is not None:
                                normalized_cf, cf_norm_warnings = normalize_json_obj(fixed_cf[0], "confidence")
                                warnings.extend(cf_norm_warnings)
                                if normalized_cf:
                                    confidence = normalized_cf["confidence"]
                            if confidence is None:
                                confidence, cf_coerce_warn = coerce_confidence(repaired_conf)
                                if cf_coerce_warn:
                                    warnings.append(cf_coerce_warn)
                            if confidence is not None:
                                warnings.append("confidence_repaired")

                if confidence is None:
                    missing_confidence += 1
                    _debug_dump_raw(
                        args.outdir,
                        provider,
                        model_id,
                        row_id,
                        raw_translation,
                        raw_confidence,
                        raw_translation_preview=_truncate(raw_translation),
                        raw_confidence_preview=_truncate(raw_confidence),
                    )

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
                    payload["parse_warnings"] = ";".join(dict.fromkeys(warnings))
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
