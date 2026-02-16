import logging
import time
from typing import Any, Dict, Tuple

from google import genai
from google.genai import types

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

_CLIENTS: dict[str, genai.Client] = {}


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


def _call(client: genai.Client, model_id: str, system: str, user: str, cfg: Dict[str, Any], max_tokens: int):
    return client.models.generate_content(
        model=model_id,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=cfg.get("temperature", 0.0),
            max_output_tokens=max_tokens,
            candidate_count=1,
        ),
    )


def _extract_text(resp: Any) -> str:
    return (getattr(resp, "text", "") or "").strip()


def _translation_tokens(cfg: Dict[str, Any]) -> int:
    return int(cfg.get("translation_max_tokens", min(256, int(cfg.get("max_output_tokens", 256)))))


def _confidence_tokens(cfg: Dict[str, Any]) -> int:
    return int(cfg.get("confidence_max_tokens", min(64, int(cfg.get("max_output_tokens", 64)))))


def translate(text: str, model_id: str, global_cfg: Dict[str, Any], api_key: str) -> Tuple[Dict[str, Any], Dict[str, Any], float]:
    client = _get_client(api_key)
    user = (
        "Translate from English to German. "
        "Return exactly one JSON object with one key named translation.\n"
        '{"translation":"<German translation>"}\n'
        f"SOURCE: {text}"
    )
    t0 = time.time()
    resp = _call(client, model_id, TRANSLATE_SYSTEM, user, global_cfg, _translation_tokens(global_cfg))
    raw = _extract_text(resp)
    parsed, err = parse_json_field(raw, "translation")

    warning = None
    if parsed is not None:
        translation = sanitize_translation(str(parsed))
    else:
        translation = sanitize_translation(raw)
        warning = f"translation_parse_failed: {err}"
        LOGGER.warning("Translation parse failed for %s: %s", model_id, err)

    return {"translation": translation, "parse_warning": warning}, _usage(resp), time.time() - t0


def confidence(src: str, hyp: str, model_id: str, global_cfg: Dict[str, Any], api_key: str) -> Tuple[Dict[str, Any], Dict[str, Any], float]:
    client = _get_client(api_key)
    user = (
        "Estimate confidence that TRANSLATION is correct for SOURCE. "
        "Return exactly one JSON object with one key named confidence in [0,1].\n"
        '{"confidence":0.73}\n'
        f"SOURCE: {src}\nTRANSLATION: {hyp}"
    )
    t0 = time.time()
    resp = _call(client, model_id, CONF_SYSTEM, user, global_cfg, _confidence_tokens(global_cfg))
    raw = _extract_text(resp)
    parsed, err = parse_json_field(raw, "confidence")

    warning = None
    conf = coerce_confidence(parsed if parsed is not None else raw)
    if parsed is None or conf is None:
        warning = f"confidence_parse_failed: {err or 'coercion failed'}"
        LOGGER.warning("Confidence parse failed for %s: %s", model_id, warning)

    return {"confidence": conf, "parse_warning": warning}, _usage(resp), time.time() - t0
