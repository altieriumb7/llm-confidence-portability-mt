import logging
import time
from typing import Any, Dict, Tuple

import anthropic

from utils.parse import build_strict_json_system
from utils.prompt_variants import render_confidence_prompt, render_translation_prompt

_CLIENTS: dict[str, anthropic.Anthropic] = {}
LOGGER = logging.getLogger(__name__)


def _get_client(api_key: str) -> anthropic.Anthropic:
    client = _CLIENTS.get(api_key)
    if client is None:
        client = anthropic.Anthropic(api_key=api_key)
        _CLIENTS[api_key] = client
    return client


def _max_tokens(cfg: Dict[str, Any], kind: str) -> int:
    key = f"{kind}_max_output_tokens"
    default = 256 if kind == "translation" else 64
    return int(cfg.get(key, default))


def _message(client: anthropic.Anthropic, model_id: str, system: str, user: str, cfg: Dict[str, Any], kind: str):
    return client.messages.create(
        model=model_id,
        max_tokens=_max_tokens(cfg, kind),
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


def translate(text: str, model_id: str, global_cfg: Dict[str, Any], api_key: str) -> Tuple[str, Dict[str, Any], float, str | None]:
    client = _get_client(api_key)
    system = build_strict_json_system("translation")
    _, user = render_translation_prompt(global_cfg, src=text, variant=global_cfg.get("prompt_variant"))
    t0 = time.time()
    resp = _message(client, model_id, system, user, global_cfg, "translation")
    return _extract_text(resp), _usage(resp), time.time() - t0, None


def confidence(src: str, hyp: str, model_id: str, global_cfg: Dict[str, Any], api_key: str) -> Tuple[str, Dict[str, Any], float, str | None]:
    client = _get_client(api_key)
    system = build_strict_json_system("confidence")
    _, user = render_confidence_prompt(global_cfg, src=src, hyp=hyp, variant=global_cfg.get("prompt_variant"))
    t0 = time.time()
    resp = _message(client, model_id, system, user, global_cfg, "confidence")
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
    resp = _message(client, model_id, system, user, cfg, kind)
    return _extract_text(resp), _usage(resp), time.time() - t0, None
