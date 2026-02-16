import logging
import time
from typing import Any, Dict, Tuple

from openai import BadRequestError, OpenAI

from utils.parse import coerce_confidence, parse_json_field, sanitize_translation

LOGGER = logging.getLogger(__name__)

JSON_ONLY_INSTRUCTION = (
    "Return ONLY valid JSON. No prose. No markdown. No code fences. "
    "Output must be a single JSON object on one line."
)
TRANSLATE_SYSTEM = (
    "You are a precise machine translation engine. "
    + JSON_ONLY_INSTRUCTION
    + ' Example: {"translation":"Guten Morgen"}'
)
CONF_SYSTEM = (
    "You are a calibration evaluator. "
    + JSON_ONLY_INSTRUCTION
    + ' Example: {"confidence":0.73}'
)

_NO_TEMPERATURE_MODELS: set[str] = set()
_CLIENTS: dict[tuple[str, float], OpenAI] = {}


def _get_client(api_key: str, timeout_s: float) -> OpenAI:
    key = (api_key, float(timeout_s))
    client = _CLIENTS.get(key)
    if client is None:
        client = OpenAI(api_key=api_key, timeout=timeout_s)
        _CLIENTS[key] = client
    return client


def _chat(client: OpenAI, model_id: str, system: str, user: str, cfg: Dict[str, Any], max_tokens: int):
    payload: Dict[str, Any] = {
        "model": model_id,
        "input": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_output_tokens": max_tokens,
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


def _translation_tokens(cfg: Dict[str, Any]) -> int:
    return int(cfg.get("translation_max_tokens", min(256, int(cfg.get("max_output_tokens", 256)))))


def _confidence_tokens(cfg: Dict[str, Any]) -> int:
    return int(cfg.get("confidence_max_tokens", min(64, int(cfg.get("max_output_tokens", 64)))))


def translate(text: str, model_id: str, global_cfg: Dict[str, Any], api_key: str) -> Tuple[Dict[str, Any], Dict[str, Any], float]:
    client = _get_client(api_key, global_cfg["timeout_s"])
    user = (
        "Translate from English to German. "
        "Return exactly one JSON object with one key named translation.\n"
        '{"translation":"<German translation>"}\n'
        f"SOURCE: {text}"
    )
    t0 = time.time()
    resp = _chat(client, model_id, TRANSLATE_SYSTEM, user, global_cfg, _translation_tokens(global_cfg))
    raw = _extract_text(resp)
    parsed, err = parse_json_field(raw, "translation")

    warning = None
    translation = ""
    if parsed is not None:
        translation = sanitize_translation(str(parsed))
    else:
        translation = sanitize_translation(raw)
        warning = f"translation_parse_failed: {err}"
        LOGGER.warning("Translation parse failed for %s: %s", model_id, err)

    return {"translation": translation, "parse_warning": warning}, _usage(resp), time.time() - t0


def confidence(src: str, hyp: str, model_id: str, global_cfg: Dict[str, Any], api_key: str) -> Tuple[Dict[str, Any], Dict[str, Any], float]:
    client = _get_client(api_key, global_cfg["timeout_s"])
    user = (
        "Estimate confidence that TRANSLATION is correct for SOURCE. "
        "Return exactly one JSON object with one key named confidence in [0,1].\n"
        '{"confidence":0.73}\n'
        f"SOURCE: {src}\nTRANSLATION: {hyp}"
    )
    t0 = time.time()
    resp = _chat(client, model_id, CONF_SYSTEM, user, global_cfg, _confidence_tokens(global_cfg))
    raw = _extract_text(resp)
    parsed, err = parse_json_field(raw, "confidence")

    warning = None
    conf = coerce_confidence(parsed if parsed is not None else raw)
    if parsed is None or conf is None:
        warning = f"confidence_parse_failed: {err or 'coercion failed'}"
        LOGGER.warning("Confidence parse failed for %s: %s", model_id, warning)

    return {"confidence": conf, "parse_warning": warning}, _usage(resp), time.time() - t0
