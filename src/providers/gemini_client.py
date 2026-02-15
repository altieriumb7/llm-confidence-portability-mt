import time
import logging
from typing import Any, Dict, Tuple

from google import genai
from google.genai import types

from utils.json_parse import extract_first_json_object, parse_json_field

TRANSLATE_SYSTEM = "You are a precise machine translation engine."
CONF_SYSTEM = "You are a careful evaluator."

# Runtime cache: clients keyed by api_key
_CLIENTS: dict[str, genai.Client] = {}
LOGGER = logging.getLogger(__name__)


def _get_client(api_key: str) -> genai.Client:
    client = _CLIENTS.get(api_key)
    if client is None:
        client = genai.Client(api_key=api_key)
        _CLIENTS[api_key] = client
    return client


def _usage(resp: Any) -> Dict[str, Any]:
    md = getattr(resp, "usage_metadata", None)
    if not md:
        return {}
    return {
        "input_tokens": getattr(md, "prompt_token_count", None),
        "output_tokens": getattr(md, "candidates_token_count", None),
    }


def _call(client: genai.Client, model_id: str, system: str, user: str, cfg: Dict[str, Any]):
    return client.models.generate_content(
        model=model_id,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=cfg["temperature"],
            max_output_tokens=cfg["max_output_tokens"],
        ),
    )


def _extract_text(resp: Any) -> str:
    return (getattr(resp, "text", "") or "").strip()


def translate(text: str, model_id: str, global_cfg: Dict[str, Any], api_key: str) -> Tuple[Any, Dict[str, Any], float]:
    client = _get_client(api_key)
    user = (
        "Translate the following sentence from English to German. "
        "Return ONLY valid JSON with exactly one key: {\"translation\": \"...\"}.\n\n"
        f"SOURCE: {text}"
    )
    t0 = time.time()
    resp = _call(client, model_id, TRANSLATE_SYSTEM, user, global_cfg)
    raw = _extract_text(resp)
    parsed = parse_json_field(raw, "translation")
    if parsed is not None:
        return str(parsed).strip(), _usage(resp), time.time() - t0
    fallback_obj = extract_first_json_object(raw)
    if fallback_obj:
        parsed = parse_json_field(fallback_obj, "translation")
        if parsed is not None:
            LOGGER.warning("Recovered translation JSON from embedded object for %s", model_id)
            return str(parsed).strip(), _usage(resp), time.time() - t0
    LOGGER.warning("Translation JSON parse failed for %s; falling back to raw text", model_id)
    return raw.strip(), _usage(resp), time.time() - t0


def confidence(src: str, hyp: str, model_id: str, global_cfg: Dict[str, Any], api_key: str) -> Tuple[Any, Dict[str, Any], float]:
    client = _get_client(api_key)
    user = (
        "Return ONLY valid JSON with exactly one key 'confidence' whose value is a number between 0 and 1.\n\n"
        f"SOURCE: {src}\nTRANSLATION: {hyp}"
    )
    t0 = time.time()
    resp = _call(client, model_id, CONF_SYSTEM, user, global_cfg)
    raw = _extract_text(resp)
    parsed = parse_json_field(raw, "confidence")
    if parsed is None:
        fallback_obj = extract_first_json_object(raw)
        if fallback_obj:
            parsed = parse_json_field(fallback_obj, "confidence")
            if parsed is not None:
                LOGGER.warning("Recovered confidence JSON from embedded object for %s", model_id)
        if parsed is None:
            LOGGER.warning("Confidence JSON parse failed for %s; returning raw text", model_id)
            return raw, _usage(resp), time.time() - t0
    try:
        parsed = max(0.0, min(1.0, float(parsed)))
    except Exception:
        LOGGER.warning("Confidence value invalid for %s; returning raw text", model_id)
        return raw, _usage(resp), time.time() - t0
    return parsed, _usage(resp), time.time() - t0
