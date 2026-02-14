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
    parse_confidence,
    read_jsonl,
    retry_with_backoff,
    setup_logging,
    usage_to_tokens,
)

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/models.yaml")
    ap.add_argument("--input", default="data/wmt_sample.jsonl")
    ap.add_argument("--outdir", default="runs/raw")
    ap.add_argument("--providers", default=None)
    ap.add_argument("--models", default=None)
    ap.add_argument("--max_samples", type=int, default=None)
    ap.add_argument("--dry_run", action="store_true")
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
        logger.info(
            "No --models/--providers filter set: processing %d configured models.",
            len(selected_models),
        )

    for m in selected_models:
        provider, model_id = m["provider"], m["model_id"]
        out_path = Path(args.outdir) / f"{provider}__{model_id}.jsonl"
        # Normalize IDs to string so resume works even if previous runs used a
        # different JSON type (e.g. "1" vs 1).
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
        logger.info("Pending %s/%s samples=%d", provider, model_id, total_pending)
        for row in data:
            row_id = str(row["id"])
            if row_id in done_ids:
                continue
            try:
                if args.dry_run:
                    hyp, conf = row["ref"], 0.5
                    tr_usage = cf_usage = {}
                    tr_lat = cf_lat = 0.0
                else:
                    hyp, tr_usage, tr_lat = retry_with_backoff(
                        lambda: client.translate(row["src"], model_id, g, api_key), g["max_retries"], logger, "translate"
                    )
                    conf_raw, cf_usage, cf_lat = retry_with_backoff(
                        lambda: client.confidence(row["src"], hyp, model_id, g, api_key), g["max_retries"], logger, "confidence"
                    )
                    conf = parse_confidence(conf_raw)

                u1, u2 = usage_to_tokens(tr_usage), usage_to_tokens(cf_usage)
                append_jsonl(
                    out_path,
                    {
                        "id": row["id"], "src": row["src"], "ref": row["ref"], "hyp": hyp, "conf": conf,
                        "provider": provider, "model_id": model_id,
                        "latency_translate_s": tr_lat, "latency_conf_s": cf_lat,
                        "input_tokens": (u1["input_tokens"] or 0) + (u2["input_tokens"] or 0) if (u1["input_tokens"] is not None or u2["input_tokens"] is not None) else None,
                        "output_tokens": (u1["output_tokens"] or 0) + (u2["output_tokens"] or 0) if (u1["output_tokens"] is not None or u2["output_tokens"] is not None) else None,
                        "timestamp_utc": now_utc_iso(),
                    },
                )
                done_ids.add(row_id)
            except Exception as exc:
                logger.exception("Failed %s/%s id=%s: %s", provider, model_id, row["id"], exc)


if __name__ == "__main__":
    main()
