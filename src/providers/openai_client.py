import logging
import json
import re
import time
from typing import Any, Dict, Tuple

from openai import BadRequestError
from openai import OpenAI

from utils.parse import build_strict_json_system

_NO_TEMPERATURE_MODELS: set[str] = set()
_NO_TEXT_FORMAT_MODELS: set[str] = set()
_SIMPLE_INPUT_MODELS: set[str] = set()
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
    cap = 2048 if kind == "translation" else 256
    return min(int(cfg.get(key, default)), cap)


def _obj_get(obj: Any, key: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _chat(client: OpenAI, model_id: str, system: str, user: str, cfg: Dict[str, Any], kind: str):
    use_simple_input = model_id in _SIMPLE_INPUT_MODELS

    def _make_payload() -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": model_id,
            "max_output_tokens": _max_tokens(cfg, kind),
            "timeout": cfg["timeout_s"],
        }
        if model_id not in _NO_TEMPERATURE_MODELS:
            payload["temperature"] = 0
        if use_simple_input:
            payload["instructions"] = system
            payload["input"] = user
        else:
            payload["input"] = [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ]
        if model_id not in _NO_TEXT_FORMAT_MODELS:
            payload["text"] = {"format": {"type": "json_object"}}
        return payload

    payload = _make_payload()
    try:
        resp = client.responses.create(**payload)
    except BadRequestError as e:
        msg = str(e)
        if ("temperature" in msg and "temperature" in payload) or ("param': 'temperature'" in msg):
            _NO_TEMPERATURE_MODELS.add(model_id)
            payload.pop("temperature", None)
            resp = client.responses.create(**payload)
        elif (("text.format" in msg) or ("json_object" in msg) or ("format" in msg and "Unsupported" in msg)) and "text" in payload:
            _NO_TEXT_FORMAT_MODELS.add(model_id)
            payload.pop("text", None)
            resp = client.responses.create(**payload)
        else:
            raise

    extracted = _extract_text(resp, prefer_key=kind)
    if not extracted:
        if model_id not in _NO_TEXT_FORMAT_MODELS:
            _NO_TEXT_FORMAT_MODELS.add(model_id)
            retry_payload = _make_payload()
            retry_payload.pop("text", None)
            resp = client.responses.create(**retry_payload)
            extracted = _extract_text(resp, prefer_key=kind)
        if not extracted and not use_simple_input:
            _SIMPLE_INPUT_MODELS.add(model_id)
            use_simple_input = True
            retry_payload = _make_payload()
            retry_payload.pop("text", None)
            resp = client.responses.create(**retry_payload)
            extracted = _extract_text(resp, prefer_key=kind)

    if kind == "confidence" and extracted and "{" not in extracted and not re.search(r"\d", extracted):
        if model_id not in _NO_TEXT_FORMAT_MODELS:
            _NO_TEXT_FORMAT_MODELS.add(model_id)
        if not use_simple_input:
            _SIMPLE_INPUT_MODELS.add(model_id)
            use_simple_input = True
        retry_payload = _make_payload()
        retry_payload.pop("text", None)
        resp = client.responses.create(**retry_payload)

    return resp


def _iter_leaf_strings(obj: Any, *, prefer_key: str | None = None, max_items: int = 4000, max_total_chars: int = 200_000):
    yielded = 0
    total = 0

    def walk(x: Any):
        nonlocal yielded, total
        if x is None or yielded >= max_items or total >= max_total_chars:
            return
        if isinstance(x, str):
            yielded += 1
            total += len(x)
            if yielded <= max_items and total <= max_total_chars:
                yield x
            return
        if isinstance(x, (int, float, bool)):
            s = str(x)
            yielded += 1
            total += len(s)
            if yielded <= max_items and total <= max_total_chars:
                yield s
            return
        if isinstance(x, dict):
            keys = set(x.keys())
            for k in ([prefer_key] if prefer_key else []) + ["confidence", "translation"]:
                if k and k in keys:
                    v = x.get(k)
                    if isinstance(v, (str, int, float, bool)) or v is None:
                        s = json.dumps({k: v}, ensure_ascii=False)
                        yielded += 1
                        total += len(s)
                        if yielded <= max_items and total <= max_total_chars:
                            yield s
            for v in x.values():
                if yielded >= max_items or total >= max_total_chars:
                    return
                yield from walk(v)
            return
        if isinstance(x, (list, tuple, set)):
            for v in x:
                if yielded >= max_items or total >= max_total_chars:
                    return
                yield from walk(v)
            return
        for attr in ("value", "text", "parsed", "json", "data", "arguments", "args", "content", "output", "choices", "message"):
            xv = getattr(x, attr, None)
            if xv is not None:
                yield from walk(xv)
        try:
            d = vars(x)
        except Exception:
            d = None
        if isinstance(d, dict):
            yield from walk(d)

    yield from walk(obj)


def _extract_text(resp: Any, *, prefer_key: str | None = None) -> str:
    def _as_text(x: Any) -> str | None:
        if x is None:
            return None
        if isinstance(x, dict):
            if "value" in x and isinstance(x["value"], str):
                s = x["value"].strip()
                return s or None
            if "text" in x:
                tv = x["text"]
                if isinstance(tv, str):
                    s = tv.strip()
                    return s or None
                if isinstance(tv, dict) and "value" in tv and isinstance(tv["value"], str):
                    s = tv["value"].strip()
                    return s or None
        if isinstance(x, str):
            s = x.strip()
            return s or None
        if isinstance(x, (dict, list)):
            return json.dumps(x, ensure_ascii=False)
        v = getattr(x, "value", None)
        if isinstance(v, str):
            s = v.strip()
            if s:
                return s
        t = getattr(x, "text", None)
        tv = getattr(t, "value", None) if t is not None else None
        if isinstance(tv, str):
            s = tv.strip()
            if s:
                return s
        try:
            s = str(x).strip()
            return s or None
        except Exception:
            return None

    out_text = _as_text(_obj_get(resp, "output_text"))
    if out_text:
        return out_text

    choices = _obj_get(resp, "choices")
    if choices:
        c0 = choices[0] if isinstance(choices, (list, tuple)) else choices
        msg = _obj_get(c0, "message")
        ctxt = _as_text(_obj_get(msg, "content") if msg is not None else None)
        if ctxt:
            return ctxt

    text_chunks: list[str] = []
    for item in (_obj_get(resp, "output") or []):
        for block in (_obj_get(item, "content") or []):
            t = _as_text(_obj_get(block, "text"))
            if t:
                text_chunks.append(t)
                continue
            t = _as_text(_obj_get(block, "value"))
            if t:
                text_chunks.append(t)
                continue
            for json_key in ("json", "parsed", "data"):
                parsed = _obj_get(block, json_key)
                p = _as_text(parsed)
                if p:
                    text_chunks.append(p)
                    break

    joined = "\n".join(text_chunks).strip()
    if joined:
        return joined

    leaves = list(_iter_leaf_strings(resp, prefer_key=prefer_key))
    best = ""
    best_score = (-1, -1)
    for s in leaves:
        ss = (s or "").strip()
        if not ss:
            continue
        score = 0
        if prefer_key and prefer_key in ss:
            score += 12
        if "confidence" in ss or "translation" in ss:
            score += 10
        if "{" in ss and "}" in ss:
            score += 6
        if any(ch.isdigit() for ch in ss):
            score += 1
        score2 = min(len(ss), 5000)
        if (score, score2) > best_score:
            best_score = (score, score2)
            best = ss
    return best


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
        "Translate English to German. Return ONLY one JSON object with exactly this key: "
        '{"translation":"..."}. No explanations, no markdown, no code fences.\n\n'
        f"SOURCE: {text}"
    )
    t0 = time.time()
    resp = _chat(client, model_id, system, user, global_cfg, "translation")
    raw = _extract_text(resp, prefer_key="translation")
    return raw, _usage(resp), time.time() - t0, None


def confidence(
    src: str, hyp: str, model_id: str, global_cfg: Dict[str, Any], api_key: str
) -> Tuple[str, Dict[str, Any], float, str | None]:
    client = _get_client(api_key, global_cfg["timeout_s"])
    system = build_strict_json_system("confidence")
    user = (
        "Rate translation correctness confidence from 0 to 1. Return ONLY one JSON object "
        'with exactly this key: {"confidence":0.73}. No explanations, no markdown, no code fences.\n\n'
        f"SOURCE: {src}\nTRANSLATION: {hyp}"
    )
    t0 = time.time()
    resp = _chat(client, model_id, system, user, global_cfg, "confidence")
    return _extract_text(resp, prefer_key="confidence"), _usage(resp), time.time() - t0, None


def repair_confidence(
    src: str,
    hyp: str,
    previous_answer: str,
    model_id: str,
    global_cfg: Dict[str, Any],
    api_key: str,
) -> Tuple[str, Dict[str, Any], float, str | None]:
    client = _get_client(api_key, global_cfg["timeout_s"])
    system = build_strict_json_system("confidence")
    user = (
        'Return ONLY a JSON object: {"confidence": <number between 0 and 1>} with no extra text.\n\n'
        f"SOURCE: {src}\nTRANSLATION: {hyp}\nPREVIOUS_ANSWER: {previous_answer}"
    )
    t0 = time.time()
    cfg = {**global_cfg, "confidence_max_output_tokens": max(64, int(global_cfg.get("confidence_max_output_tokens", 64)))}
    resp = _chat(client, model_id, system, user, cfg, "confidence")
    return _extract_text(resp, prefer_key="confidence"), _usage(resp), time.time() - t0, None


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
        return repair_confidence(
            src=original_input,
            hyp=translation or "",
            previous_answer=previous_answer,
            model_id=model_id,
            global_cfg=global_cfg,
            api_key=api_key,
        )

    system = build_strict_json_system("translation")
    user = (
        'Convert your previous answer into EXACT JSON: {"translation": "..."}; output JSON only.\n\n'
        f"SOURCE: {original_input}\nPREVIOUS_ANSWER: {previous_answer}"
    )
    t0 = time.time()
    resp = _chat(client, model_id, system, user, {**global_cfg, "translation_max_output_tokens": 64}, "translation")
    return _extract_text(resp, prefer_key="translation"), _usage(resp), time.time() - t0, None
