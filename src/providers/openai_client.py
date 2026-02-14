import time
from typing import Any, Dict, Tuple

from openai import OpenAI

TRANSLATE_SYSTEM = "You are a precise machine translation engine."
CONF_SYSTEM = "You are a careful evaluator."


def _chat(client: OpenAI, model_id: str, system: str, user: str, cfg: Dict[str, Any]):
    return client.responses.create(
        model=model_id,
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=cfg["temperature"],
        max_output_tokens=cfg["max_output_tokens"],
        timeout=cfg["timeout_s"],
    )


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


def translate(text: str, model_id: str, global_cfg: Dict[str, Any], api_key: str) -> Tuple[str, Dict[str, Any], float]:
    client = OpenAI(api_key=api_key, timeout=global_cfg["timeout_s"])
    user = f"Translate the following sentence from English to German. Output ONLY the translation text.\n\n{text}"
    t0 = time.time()
    resp = _chat(client, model_id, TRANSLATE_SYSTEM, user, global_cfg)
    return _extract_text(resp), _usage(resp), time.time() - t0


def confidence(src: str, hyp: str, model_id: str, global_cfg: Dict[str, Any], api_key: str) -> Tuple[str, Dict[str, Any], float]:
    client = OpenAI(api_key=api_key, timeout=global_cfg["timeout_s"])
    user = (
        "Return ONLY valid JSON with exactly one key 'confidence' whose value is a number between 0 and 1.\n\n"
        f"SOURCE: {src}\nTRANSLATION: {hyp}"
    )
    t0 = time.time()
    resp = _chat(client, model_id, CONF_SYSTEM, user, global_cfg)
    return _extract_text(resp), _usage(resp), time.time() - t0
