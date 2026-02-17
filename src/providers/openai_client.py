import logging
import time
from typing import Any, Dict, Tuple

from openai import BadRequestError
from openai import OpenAI

from utils.parse import coerce_confidence, parse_json_field, sanitize_translation

STRICT_JSON_SYSTEM = (
    "Return ONLY a single JSON object on ONE line. "
    "No markdown, no code fences, no extra keys."
)
TRANSLATION_SCHEMA_HINT = '{"translation": "<German translation string>"}'
CONFIDENCE_SCHEMA_HINT = '{"confidence": 0.73}'

_NO_TEMPERATURE_MODELS: set[str] = set()
_CLIENTS: dict[tuple[str, float], OpenAI] = {}
LOGGER = logging.getLogger(__name__)


def _get_client(api_key: str, timeout_s: float) -> OpenAI:
    key = (api_key, float(timeout_s))
    client = _CLIENTS.get(key)
    if client is None:
        client = OpenAI(api_key=api_key, timeout=timeout_s)
        _CLIENTS[key] = client
    return client


def _max_tokens(cfg: Dict[str, Any], kind: str) -> int:
    key = f"{kind}_max_output_tokens"
    default = 256 if kind == "translation" else 64
    return int(cfg.get(key, default))


def _chat(client: OpenAI, model_id: str, system: str, user: str, cfg: Dict[str, Any], kind: str):
    payload: Dict[str, Any] = {
        "model": model_id,
        "input": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_output_tokens": _max_tokens(cfg, kind),
        "timeout": cfg["timeout_s"],
    }

    temp = cfg.get("temperature", None)
    if temp is not None and model_id not in _NO_TEMPERATURE_MODELS:
        payload["temperature"] = temp

    try:
        return client.responses.create(**payload)
    except BadRequestError as e:
        msg = str(e)
        if (("Unsupported parameter" in msg and "temperature" in msg) or ("param': 'temperature'" in msg)) and "temperature" in payload:
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


def translate(text: str, model_id: str, global_cfg: Dict[str, Any], api_key: str) -> Tuple[str, Dict[str, Any], float, str | None]:
    client = _get_client(api_key, global_cfg["timeout_s"])
    user = (
        "Translate from English to German. "
        f"Schema: {TRANSLATION_SCHEMA_HINT}. "
        "Return ONLY valid JSON object with exactly one key: translation. "
        "No markdown, no code fences, no explanation, one line only.\n\n"
        f"SOURCE: {text}"
    )
    t0 = time.time()
    resp = _chat(client, model_id, STRICT_JSON_SYSTEM, user, global_cfg, "translation")
    raw = _extract_text(resp)
    parsed, err = parse_json_field(raw, "translation")
    if parsed is not None:
        return str(parsed).strip(), _usage(resp), time.time() - t0, None
    warning = f"translation parse fallback: {err or 'unknown error'}"
    LOGGER.warning("Translation JSON parse failed for %s: %s", model_id, err)
    sanitized = sanitize_translation(raw)
    if sanitized:
        return sanitized, _usage(resp), time.time() - t0, warning

    raw_fallback = str(raw or "").strip()[:1000]
    source_fallback = str(text or "").strip()[:1000]
    return (raw_fallback or source_fallback or "[translation unavailable]"), _usage(resp), time.time() - t0, warning


def confidence(
    src: str, hyp: str, model_id: str, global_cfg: Dict[str, Any], api_key: str
) -> Tuple[float | None, Dict[str, Any], float, str | None]:
    client = _get_client(api_key, global_cfg["timeout_s"])
    user = (
        "Evaluate how likely this translation is correct. "
        f"Schema: {CONFIDENCE_SCHEMA_HINT}. "
        "Confidence must be a number in [0,1]. "
        "Return ONLY valid JSON object with exactly one key: confidence. "
        "No markdown, no code fences, no explanation, one line only.\n\n"
        f"SOURCE: {src}\nTRANSLATION: {hyp}"
    )
    t0 = time.time()
    resp = _chat(client, model_id, STRICT_JSON_SYSTEM, user, global_cfg, "confidence")
    raw = _extract_text(resp)
    parsed, err = parse_json_field(raw, "confidence")
    conf = coerce_confidence(parsed if parsed is not None else raw)
    if conf is None:
        warning = f"confidence parse failed: {err or 'could not coerce value'}"
        LOGGER.warning("Confidence JSON parse failed for %s: %s", model_id, err)
        return None, _usage(resp), time.time() - t0, warning
    warning = None if parsed is not None else f"confidence coerced from fallback text: {err or 'json parse failed'}"
    if warning:
        LOGGER.warning("Confidence JSON parse fallback used for %s: %s", model_id, err)
    return conf, _usage(resp), time.time() - t0, warning
