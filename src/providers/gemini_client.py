import time
from typing import Any, Dict, Tuple

from google import genai
from google.genai import types

TRANSLATE_SYSTEM = "You are a precise machine translation engine."
CONF_SYSTEM = "You are a careful evaluator."

# Runtime cache: clients keyed by api_key
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


def translate(text: str, model_id: str, global_cfg: Dict[str, Any], api_key: str) -> Tuple[str, Dict[str, Any], float]:
    client = _get_client(api_key)
    user = f"Translate the following sentence from English to German. Output ONLY the translation text.\n\n{text}"
    t0 = time.time()
    resp = _call(client, model_id, TRANSLATE_SYSTEM, user, global_cfg)
    return _extract_text(resp), _usage(resp), time.time() - t0


def confidence(src: str, hyp: str, model_id: str, global_cfg: Dict[str, Any], api_key: str) -> Tuple[str, Dict[str, Any], float]:
    client = _get_client(api_key)
    user = (
        "Return ONLY valid JSON with exactly one key 'confidence' whose value is a number between 0 and 1.\n\n"
        f"SOURCE: {src}\nTRANSLATION: {hyp}"
    )
    t0 = time.time()
    resp = _call(client, model_id, CONF_SYSTEM, user, global_cfg)
    return _extract_text(resp), _usage(resp), time.time() - t0
