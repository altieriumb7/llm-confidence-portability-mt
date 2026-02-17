import logging
import json
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
    cap = 2048 if kind == "translation" else 256
    return min(int(cfg.get(key, default)), cap)


def _obj_get(obj: Any, key: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _call(client: genai.Client, model_id: str, system: str, user: str, cfg: Dict[str, Any], kind: str):
    config_kwargs = {
        "system_instruction": system,
        "temperature": 0,
        "max_output_tokens": _max_tokens(cfg, kind),
    }
    if model_id not in _MIME_JSON_UNSUPPORTED_MODELS:
        config_kwargs["response_mime_type"] = "application/json"

    try:
        resp = client.models.generate_content(
            model=model_id,
            contents=user,
            config=types.GenerateContentConfig(**config_kwargs),
        )
        if config_kwargs.get("response_mime_type") == "application/json" and not _extract_text(resp):
            _MIME_JSON_UNSUPPORTED_MODELS.add(model_id)
            config_kwargs.pop("response_mime_type", None)
            return client.models.generate_content(
                model=model_id,
                contents=user,
                config=types.GenerateContentConfig(**config_kwargs),
            )
        return resp
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
        if isinstance(v, str) and v.strip():
            return v.strip()
        t = getattr(x, "text", None)
        tv = getattr(t, "value", None) if t is not None else None
        if isinstance(tv, str) and tv.strip():
            return tv.strip()
        try:
            s = str(x).strip()
            return s or None
        except Exception:
            return None

    parsed_top = _obj_get(resp, "parsed")
    pt = _as_text(parsed_top)
    if pt:
        return pt

    text = _as_text(_obj_get(resp, "text"))
    if text:
        return text

    chunks: list[str] = []
    candidates = _obj_get(resp, "candidates") or []
    for candidate in candidates:
        content = _obj_get(candidate, "content")
        for part in (_obj_get(content, "parts") or []):
            part_text = _as_text(_obj_get(part, "text"))
            if part_text:
                chunks.append(part_text)
                continue
            for key in ("parsed", "json", "data"):
                parsed = _as_text(_obj_get(part, key))
                if parsed:
                    chunks.append(parsed)
                    break
            fc = _obj_get(part, "function_call")
            if fc is not None:
                args = _obj_get(fc, "args")
                if args is None:
                    args = _obj_get(fc, "arguments")
                at = _as_text(args)
                if at:
                    chunks.append(at)
            fr = _obj_get(part, "function_response")
            if fr is not None:
                rt = _as_text(_obj_get(fr, "response"))
                if rt:
                    chunks.append(rt)

    joined = "\n".join(chunks).strip()
    if joined:
        return joined

    def _iter_leaf_strings(obj: Any, *, max_items: int = 4000, max_total_chars: int = 200_000):
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
                for k in ("confidence", "translation"):
                    if k in keys:
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
            try:
                yield from walk(vars(x))
            except Exception:
                for attr in (
                    "candidates",
                    "content",
                    "parts",
                    "text",
                    "parsed",
                    "function_call",
                    "function_response",
                    "args",
                    "arguments",
                    "response",
                    "value",
                ):
                    xv = getattr(x, attr, None)
                    if xv is not None:
                        yield from walk(xv)

        yield from walk(obj)

    leaves = [_as_text(x) for x in _iter_leaf_strings(resp)]
    leaves = [s for s in leaves if s]
    best = ""
    best_score = (-1, -1)
    for s in leaves:
        ss = s.strip()
        score = 0
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


def translate(text: str, model_id: str, global_cfg: Dict[str, Any], api_key: str) -> Tuple[str, Dict[str, Any], float, str | None]:
    client = _get_client(api_key)
    system = build_strict_json_system("translation")
    user = (
        "Translate English to German. Return ONLY one JSON object with exactly this key: "
        '{"translation":"..."}. No explanations, no markdown, no code fences.\n\n'
        f"SOURCE: {text}"
    )
    t0 = time.time()
    resp = _call(client, model_id, system, user, global_cfg, "translation")
    return _extract_text(resp), _usage(resp), time.time() - t0, None


def confidence(src: str, hyp: str, model_id: str, global_cfg: Dict[str, Any], api_key: str) -> Tuple[str, Dict[str, Any], float, str | None]:
    client = _get_client(api_key)
    system = build_strict_json_system("confidence")
    user = (
        "Rate translation correctness confidence from 0 to 1. Return ONLY one JSON object "
        'with exactly this key: {"confidence":0.73}. No explanations, no markdown, no code fences.\n\n'
        f"SOURCE: {src}\nTRANSLATION: {hyp}"
    )
    t0 = time.time()
    resp = _call(client, model_id, system, user, global_cfg, "confidence")
    return _extract_text(resp), _usage(resp), time.time() - t0, None


def repair_confidence(
    src: str,
    hyp: str,
    previous_answer: str,
    model_id: str,
    global_cfg: Dict[str, Any],
    api_key: str,
) -> Tuple[str, Dict[str, Any], float, str | None]:
    client = _get_client(api_key)
    system = build_strict_json_system("confidence")
    user = (
        'Return ONLY a JSON object: {"confidence": <number between 0 and 1>} with no extra text.\n\n'
        f"SOURCE: {src}\nTRANSLATION: {hyp}\nPREVIOUS_ANSWER: {previous_answer}"
    )
    cfg = {**global_cfg, "confidence_max_output_tokens": max(64, int(global_cfg.get("confidence_max_output_tokens", 64)))}
    t0 = time.time()
    resp = _call(client, model_id, system, user, cfg, "confidence")
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

    client = _get_client(api_key)
    system = build_strict_json_system("translation")
    user = (
        "Convert your previous answer into EXACT JSON: {\"translation\": \"...\"}; output JSON only.\n\n"
        f"SOURCE: {original_input}\nPREVIOUS_ANSWER: {previous_answer}"
    )
    cfg = {**global_cfg, "translation_max_output_tokens": max(256, int(global_cfg.get("translation_max_output_tokens", 256)))}
    t0 = time.time()
    resp = _call(client, model_id, system, user, cfg, "translation")
    return _extract_text(resp), _usage(resp), time.time() - t0, None
