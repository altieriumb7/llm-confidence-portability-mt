import json
import re
from typing import Any, Optional, Tuple

_FENCE_BLOCK_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.IGNORECASE | re.DOTALL)
_LABEL_RE = re.compile(r"^\s*(translation|output|answer)\s*:\s*", re.IGNORECASE)


def strip_code_fences(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```") and text.endswith("```"):
        m = _FENCE_BLOCK_RE.match(text)
        if m:
            return m.group(1).strip()
        return text[3:-3].strip()
    return _FENCE_BLOCK_RE.sub(lambda m: m.group(1).strip(), text).strip()


def extract_first_json_object(text: str) -> Optional[str]:
    cleaned = strip_code_fences(text or "")
    start = cleaned.find("{")
    if start < 0:
        return None

    depth = 0
    in_string = False
    escape = False
    for idx in range(start, len(cleaned)):
        ch = cleaned[idx]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = cleaned[start : idx + 1]
                try:
                    json.loads(candidate)
                    return candidate
                except Exception:
                    return None
    return None


def parse_json_field(text: str, field: str) -> Tuple[Any, Optional[str]]:
    if text is None:
        return None, "empty response"
    if isinstance(text, dict):
        if field in text:
            return text[field], None
        return None, f"missing field '{field}' in dict"

    obj_text = extract_first_json_object(str(text))
    if obj_text is None:
        return None, "no JSON object found"

    try:
        obj = json.loads(obj_text)
    except Exception as exc:
        return None, f"json decode error: {exc}"

    if not isinstance(obj, dict):
        return None, "JSON root is not object"
    if field not in obj:
        return None, f"missing field '{field}'"
    return obj[field], None


def coerce_confidence(x: Any) -> Optional[float]:
    if x is None:
        return None

    value = None
    if isinstance(x, (int, float)):
        value = float(x)
    else:
        text = str(x).strip()
        if not text:
            return None
        try:
            value = float(text)
        except Exception:
            m = re.search(r"-?\d+(?:\.\d+)?\s*%?", text)
            if not m:
                return None
            token = m.group(0).strip()
            is_percent = token.endswith("%")
            token = token.rstrip("%")
            try:
                value = float(token)
            except Exception:
                return None
            if is_percent and value <= 100:
                value = value / 100.0

    if value is None:
        return None
    if value > 1.0 and value <= 100.0:
        value = value / 100.0
    value = max(0.0, min(1.0, value))
    return value


def sanitize_translation(text: str) -> str:
    raw = strip_code_fences(text or "")

    extracted, _ = parse_json_field(raw, "translation")
    if extracted is not None:
        return str(extracted).strip()

    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    if not lines:
        return ""

    first = _LABEL_RE.sub("", lines[0]).strip()
    if first:
        return first

    for ln in lines[1:]:
        if ln.strip():
            return ln.strip()
    return ""
