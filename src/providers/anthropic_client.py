import time
from typing import Any, Dict, Tuple

import anthropic

TRANSLATE_SYSTEM = "You are a precise machine translation engine."
CONF_SYSTEM = "You are a careful evaluator."

# Runtime cache: clients keyed by api_key
_CLIENTS: dict[str, anthropic.Anthropic] = {}


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


def translate(text: str, model_id: str, global_cfg: Dict[str, Any], api_key: str) -> Tuple[str, Dict[str, Any], float]:
    client = _get_client(api_key)
    user = f"Translate the following sentence from English to German. Output ONLY the translation text.\n\n{text}"
    t0 = time.time()
    resp = _message(client, model_id, TRANSLATE_SYSTEM, user, global_cfg)
    return _extract_text(resp), _usage(resp), time.time() - t0


def confidence(src: str, hyp: str, model_id: str, global_cfg: Dict[str, Any], api_key: str) -> Tuple[str, Dict[str, Any], float]:
    client = _get_client(api_key)
    user = (
        "Return ONLY valid JSON with exactly one key 'confidence' whose value is a number between 0 and 1.\n\n"
        f"SOURCE: {src}\nTRANSLATION: {hyp}"
    )
    t0 = time.time()
    resp = _message(client, model_id, CONF_SYSTEM, user, global_cfg)
    return _extract_text(resp), _usage(resp), time.time() - t0
