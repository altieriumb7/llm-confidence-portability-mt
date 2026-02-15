import json
import re
from typing import Any, Optional


_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def _strip_fences(text: str) -> str:
    cleaned = text.strip()
    cleaned = _FENCE_RE.sub("", cleaned).strip()
    if cleaned.startswith("```") and cleaned.endswith("```"):
        cleaned = cleaned[3:-3].strip()
    return cleaned


def extract_first_json_object(text: Any) -> Optional[str]:
    if text is None:
        return None
    cleaned = _strip_fences(str(text))
    start = cleaned.find("{")
    if start < 0:
        return None

    depth = 0
    in_str = False
    escape = False
    for idx in range(start, len(cleaned)):
        ch = cleaned[idx]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue

        if ch == '"':
            in_str = True
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


def parse_json_field(text: Any, field: str):
    if text is None:
        return None
    if isinstance(text, dict):
        return text.get(field)

    cleaned = _strip_fences(str(text))
    for payload in (cleaned, extract_first_json_object(cleaned)):
        if not payload:
            continue
        try:
            obj = json.loads(payload)
            if isinstance(obj, dict):
                return obj.get(field)
        except Exception:
            continue
    return None
