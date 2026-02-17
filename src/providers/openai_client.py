import logging
import time
from typing import Any, Dict, Tuple

from openai import BadRequestError
from openai import OpenAI

from utils.parse import build_strict_json_system

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
    system = build_strict_json_system("translation")
    user = (
        "Translate English to German. "
        'Return JSON with exactly one key: {"translation":"..."}.\n\n'
        f"SOURCE: {text}"
    )
    t0 = time.time()
    resp = _chat(client, model_id, system, user, global_cfg, "translation")
    raw = _extract_text(resp)
    return raw, _usage(resp), time.time() - t0, None


def confidence(
    src: str, hyp: str, model_id: str, global_cfg: Dict[str, Any], api_key: str
) -> Tuple[str, Dict[str, Any], float, str | None]:
    client = _get_client(api_key, global_cfg["timeout_s"])
    system = build_strict_json_system("confidence")
    user = (
        "Rate translation correctness confidence from 0 to 1. "
        'Return JSON with exactly one key: {"confidence":0.73}.\n\n'
        f"SOURCE: {src}\nTRANSLATION: {hyp}"
    )
    t0 = time.time()
    resp = _chat(client, model_id, system, user, global_cfg, "confidence")
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
    client = _get_client(api_key, global_cfg["timeout_s"])
    task = (task or "").lower()
    if task == "confidence":
        system = build_strict_json_system("confidence")
        user = (
            'Convert your previous answer into EXACT JSON: {"confidence": <number 0..1>}. '
            "Return ONLY JSON.\n\n"
            f"SOURCE: {original_input}\nTRANSLATION: {translation or ''}\nPREVIOUS_ANSWER: {previous_answer}"
        )
        kind = "confidence"
    else:
        system = build_strict_json_system("translation")
        user = (
            'Convert your previous answer into EXACT JSON: {"translation": "..."}; output JSON only.\n\n'
            f"SOURCE: {original_input}\nPREVIOUS_ANSWER: {previous_answer}"
        )
        kind = "translation"
    t0 = time.time()
    resp = _chat(client, model_id, system, user, {**global_cfg, "translation_max_output_tokens": 64, "confidence_max_output_tokens": 64}, kind)
    return _extract_text(resp), _usage(resp), time.time() - t0, None
