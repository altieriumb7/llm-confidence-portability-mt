import logging
import time
from typing import Any, Dict, Tuple

from google import genai
from google.genai import types

from utils.parse import build_strict_json_system

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
        "temperature": cfg.get("temperature", 0.0),
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
    system = build_strict_json_system("translation")
    user = (
        "Translate English to German. "
        "Return JSON with exactly one key: {\"translation\":\"...\"}.\n\n"
        f"SOURCE: {text}"
    )
    t0 = time.time()
    resp = _call(client, model_id, system, user, global_cfg, "translation")
    return _extract_text(resp), _usage(resp), time.time() - t0, None


def confidence(src: str, hyp: str, model_id: str, global_cfg: Dict[str, Any], api_key: str) -> Tuple[str, Dict[str, Any], float, str | None]:
    client = _get_client(api_key)
    system = build_strict_json_system("confidence")
    user = (
        "Rate translation correctness confidence from 0 to 1. "
        "Return JSON with exactly one key: {\"confidence\":0.73}.\n\n"
        f"SOURCE: {src}\nTRANSLATION: {hyp}"
    )
    t0 = time.time()
    resp = _call(client, model_id, system, user, global_cfg, "confidence")
    return _extract_text(resp), _usage(resp), time.time() - t0, None


def format_fix(
    task: str,
    previous_answer: str,
    original_input: str,
    model_id: str,
    global_cfg: Dict[str, Any],
    api_key: str,
    translation: str | None = None,
) -> Tuple[str, Dict[str, Any], float, str | None]:
    client = _get_client(api_key)
    task = (task or "").lower()
    if task == "confidence":
        system = build_strict_json_system("confidence")
        user = (
            "Convert your previous answer into EXACT JSON: {\"confidence\": <number 0..1>}. Return ONLY JSON.\n\n"
            f"SOURCE: {original_input}\nTRANSLATION: {translation or ''}\nPREVIOUS_ANSWER: {previous_answer}"
        )
        kind = "confidence"
    else:
        system = build_strict_json_system("translation")
        user = (
            "Convert your previous answer into EXACT JSON: {\"translation\": \"...\"}; output JSON only.\n\n"
            f"SOURCE: {original_input}\nPREVIOUS_ANSWER: {previous_answer}"
        )
        kind = "translation"
    cfg = {**global_cfg, "translation_max_output_tokens": 64, "confidence_max_output_tokens": 64}
    t0 = time.time()
    resp = _call(client, model_id, system, user, cfg, kind)
    return _extract_text(resp), _usage(resp), time.time() - t0, None
