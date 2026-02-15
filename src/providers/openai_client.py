import time
import logging
from typing import Any, Dict, Tuple

from openai import BadRequestError
from openai import OpenAI

from utils.json_parse import extract_first_json_object, parse_json_field

TRANSLATE_SYSTEM = "You are a precise machine translation engine."
CONF_SYSTEM = "You are a careful evaluator."

# Runtime cache: models that reject the `temperature` parameter
_NO_TEMPERATURE_MODELS: set[str] = set()
# Runtime cache: clients keyed by (api_key, timeout_s)
_CLIENTS: dict[tuple[str, float], OpenAI] = {}
LOGGER = logging.getLogger(__name__)


def _get_client(api_key: str, timeout_s: float) -> OpenAI:
    key = (api_key, float(timeout_s))
    client = _CLIENTS.get(key)
    if client is None:
        client = OpenAI(api_key=api_key, timeout=timeout_s)
        _CLIENTS[key] = client
    return client


def _chat(client: OpenAI, model_id: str, system: str, user: str, cfg: Dict[str, Any]):
    payload: Dict[str, Any] = {
        "model": model_id,
        "input": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_output_tokens": cfg["max_output_tokens"],
        # NOTE: OpenAI python SDK uses client-level timeout; keep here only if supported.
        "timeout": cfg["timeout_s"],
    }

    temp = cfg.get("temperature", None)
    if temp is not None and model_id not in _NO_TEMPERATURE_MODELS:
        payload["temperature"] = temp

    try:
        return client.responses.create(**payload)
    except BadRequestError as e:
        msg = str(e)
        if ("Unsupported parameter" in msg and "temperature" in msg) or ("param': 'temperature'" in msg):
            _NO_TEMPERATURE_MODELS.add(model_id)
            payload.pop("temperature", None)
            return client.responses.create(**payload)
        raise


def _extract_text(resp: Any) -> str:
    if hasattr(resp, "output_text") and resp.output_text:
        return resp.output_text.strip()
    text_chunks = []
    for item in getattr(resp, "output", []) or []:
        for c in getattr(item, "content", []) or []:
            t = getattr(c, "text", None)
            if t:
                text_chunks.append(t)
    return "\n".join(text_chunks).strip()


def _usage(resp: Any) -> Dict[str, Any]:
    u = getattr(resp, "usage", None)
    if not u:
        return {}
    return {
        "input_tokens": getattr(u, "input_tokens", None),
        "output_tokens": getattr(u, "output_tokens", None),
    }


def translate(text: str, model_id: str, global_cfg: Dict[str, Any], api_key: str) -> Tuple[Any, Dict[str, Any], float]:
    client = _get_client(api_key, global_cfg["timeout_s"])
    user = (
        "Translate the following sentence from English to German. "
        "Return ONLY valid JSON with exactly one key: {\"translation\": \"...\"}.\n\n"
        f"SOURCE: {text}"
    )
    t0 = time.time()
    resp = _chat(client, model_id, TRANSLATE_SYSTEM, user, global_cfg)
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


def confidence(
    src: str, hyp: str, model_id: str, global_cfg: Dict[str, Any], api_key: str
) -> Tuple[Any, Dict[str, Any], float]:
    client = _get_client(api_key, global_cfg["timeout_s"])
    user = (
        "Return ONLY valid JSON with exactly one key 'confidence' whose value is a number between 0 and 1.\n\n"
        f"SOURCE: {src}\nTRANSLATION: {hyp}"
    )
    t0 = time.time()
    resp = _chat(client, model_id, CONF_SYSTEM, user, global_cfg)
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
