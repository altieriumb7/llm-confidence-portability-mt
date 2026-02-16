import logging
import time
from typing import Any, Dict, Tuple

from google import genai
from google.genai import types

from utils.parse import coerce_confidence, ensure_translation, parse_json_field

STRICT_JSON_SYSTEM = (
    "You are a strict JSON generator. Return ONLY valid JSON. "
    "No prose. No markdown. No code fences. Output must be a single JSON object on one line."
)
TRANSLATION_SCHEMA_HINT = '{"translation": "<German translation string>"}'
CONFIDENCE_SCHEMA_HINT = '{"confidence": 0.73}'

_CLIENTS: dict[str, genai.Client] = {}
_MIME_JSON_UNSUPPORTED_MODELS: set[str] = set()
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


def _max_tokens(cfg: Dict[str, Any], kind: str) -> int:
    key = f"{kind}_max_output_tokens"
    default = 256 if kind == "translation" else 64
    return int(cfg.get(key, default))


def _call(client: genai.Client, model_id: str, system: str, user: str, cfg: Dict[str, Any], kind: str):
    config_kwargs = {
        "system_instruction": system,
        "temperature": cfg["temperature"],
        "max_output_tokens": _max_tokens(cfg, kind),
    }
    if model_id not in _MIME_JSON_UNSUPPORTED_MODELS:
        config_kwargs["response_mime_type"] = "application/json"

    try:
        return client.models.generate_content(
            model=model_id,
            contents=user,
            config=types.GenerateContentConfig(**config_kwargs),
        )
    except Exception as exc:
        if "response_mime_type" in config_kwargs and "mime" in str(exc).lower():
            _MIME_JSON_UNSUPPORTED_MODELS.add(model_id)
            config_kwargs.pop("response_mime_type", None)
            return client.models.generate_content(
                model=model_id,
                contents=user,
                config=types.GenerateContentConfig(**config_kwargs),
            )
        raise


def _extract_text(resp: Any) -> str:
    return (getattr(resp, "text", "") or "").strip()


def translate(text: str, model_id: str, global_cfg: Dict[str, Any], api_key: str) -> Tuple[str, Dict[str, Any], float, str | None]:
    client = _get_client(api_key)
    user = (
        "Translate from English to German. "
        f"Schema: {TRANSLATION_SCHEMA_HINT}. "
        "Return ONLY valid JSON object with exactly one key: translation. "
        "No markdown, no code fences, no explanation, one line only.\n\n"
        f"SOURCE: {text}"
    )
    t0 = time.time()
    resp = _call(client, model_id, STRICT_JSON_SYSTEM, user, global_cfg, "translation")
    raw = _extract_text(resp)
    parsed, err = parse_json_field(raw, "translation")
    if parsed is not None:
        return str(parsed).strip(), _usage(resp), time.time() - t0, None
    warning = f"translation parse fallback: {err or 'unknown error'}"
    LOGGER.warning("Translation JSON parse failed for %s: %s", model_id, err)
    return ensure_translation(raw, fallback=text), _usage(resp), time.time() - t0, warning


def confidence(src: str, hyp: str, model_id: str, global_cfg: Dict[str, Any], api_key: str) -> Tuple[float | None, Dict[str, Any], float, str | None]:
    client = _get_client(api_key)
    user = (
        "Evaluate how likely this translation is correct. "
        f"Schema: {CONFIDENCE_SCHEMA_HINT}. "
        "Confidence must be a number in [0,1]. "
        "Return ONLY valid JSON object with exactly one key: confidence. "
        "No markdown, no code fences, no explanation, one line only.\n\n"
        f"SOURCE: {src}\nTRANSLATION: {hyp}"
    )
    t0 = time.time()
    resp = _call(client, model_id, STRICT_JSON_SYSTEM, user, global_cfg, "confidence")
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
