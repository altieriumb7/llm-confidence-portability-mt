import time
import logging
from typing import Any, Dict, Tuple

import anthropic

from utils.json_parse import extract_first_json_object, parse_json_field

TRANSLATE_SYSTEM = "You are a precise machine translation engine."
CONF_SYSTEM = "You are a careful evaluator."

# Runtime cache: clients keyed by api_key
_CLIENTS: dict[str, anthropic.Anthropic] = {}
LOGGER = logging.getLogger(__name__)


def _get_client(api_key: str) -> anthropic.Anthropic:
    client = _CLIENTS.get(api_key)
    if client is None:
        client = anthropic.Anthropic(api_key=api_key)
        _CLIENTS[api_key] = client
    return client


def _message(client: anthropic.Anthropic, model_id: str, system: str, user: str, cfg: Dict[str, Any]):
    return client.messages.create(
        model=model_id,
        max_tokens=cfg["max_output_tokens"],
        temperature=cfg["temperature"],
        system=system,
        messages=[{"role": "user", "content": user}],
        timeout=cfg["timeout_s"],
    )


def _extract_text(resp: Any) -> str:
    chunks = []
    for c in getattr(resp, "content", []) or []:
        txt = getattr(c, "text", None)
        if txt:
            chunks.append(txt)
    return "\n".join(chunks).strip()


def _usage(resp: Any) -> Dict[str, Any]:
    u = getattr(resp, "usage", None)
    if not u:
        return {}
    return {
        "input_tokens": getattr(u, "input_tokens", None),
        "output_tokens": getattr(u, "output_tokens", None),
    }


def translate(text: str, model_id: str, global_cfg: Dict[str, Any], api_key: str) -> Tuple[Any, Dict[str, Any], float]:
    client = _get_client(api_key)
    user = (
        "Translate the following sentence from English to German. "
        "Return ONLY valid JSON with exactly one key: {\"translation\": \"...\"}.\n\n"
        f"SOURCE: {text}"
    )
    t0 = time.time()
    resp = _message(client, model_id, TRANSLATE_SYSTEM, user, global_cfg)
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
    resp = _message(client, model_id, CONF_SYSTEM, user, global_cfg)
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
