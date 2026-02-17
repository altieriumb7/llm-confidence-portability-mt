import json
import re
from typing import Any, Optional, Tuple

_FENCE_BLOCK_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)
_LEADING_LABEL_RE = re.compile(r"^\s*translation\s*:\s*", re.IGNORECASE)


def build_strict_json_system(task_name: str) -> str:
    task = (task_name or "").strip().lower()
    if task == "confidence":
        schema = '{"confidence": <number between 0 and 1>}'
        example = 'Example: {"confidence": 0.83}'
    else:
        schema = '{"translation": "<string>"}'
        example = 'Example: {"translation": "Hallo Welt."}'
    return (
        "Return ONLY valid JSON (single object) on ONE line. "
        "No markdown, no code fences, no extra text. Use double quotes. "
        f"Schema: {schema}. {example}"
    )


def _strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    if "```" not in cleaned:
        return cleaned

    def _unwrap(match: re.Match[str]) -> str:
        return match.group(1).strip()

    cleaned = _FENCE_BLOCK_RE.sub(_unwrap, cleaned)
    if cleaned.startswith("```") and cleaned.endswith("```"):
        cleaned = cleaned[3:-3].strip()
    return cleaned.strip()


def extract_first_json_object(text: str) -> Optional[dict]:
    if text is None:
        return None

    cleaned = _strip_code_fences(str(text))
    start = cleaned.find("{")
    if start < 0:
        return None

    depth = 0
    in_string = False
    escaped = False

    for idx in range(start, len(cleaned)):
        ch = cleaned[idx]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = cleaned[start : idx + 1]
                try:
                    obj = json.loads(candidate)
                except Exception:
                    return None
                return obj if isinstance(obj, dict) else None
    return None


def parse_json_field(text: str, field: str) -> Tuple[Optional[Any], Optional[str]]:
    if text is None:
        return None, "empty response"

    obj = extract_first_json_object(str(text))
    if obj is None:
        return None, "no JSON object found"
    if field not in obj:
        return None, f"missing field '{field}'"
    return obj[field], None


def coerce_confidence(x: Any) -> Optional[float]:
    if x is None:
        return None

    value: Optional[float] = None
    if isinstance(x, (int, float)):
        value = float(x)
    elif isinstance(x, str):
        text = x.strip()
        if not text:
            return None
        pct = re.search(r"(-?\d+(?:\.\d+)?)\s*%", text)
        if pct:
            try:
                value = float(pct.group(1)) / 100.0
            except Exception:
                return None
        else:
            m = re.search(r"-?\d+(?:\.\d+)?", text)
            if m:
                try:
                    value = float(m.group(0))
                except Exception:
                    return None
            else:
                lowered = text.lower()
                if re.search(r"\bhigh\b", lowered):
                    value = 0.9
                elif re.search(r"\bmedium\b", lowered):
                    value = 0.6
                elif re.search(r"\blow\b", lowered):
                    value = 0.3
                else:
                    return None
    else:
        return None

    if value > 1.0 and value <= 100.0:
        value = value / 100.0
    return max(0.0, min(1.0, value))


def sanitize_translation(text: str) -> str:
    cleaned = _strip_code_fences(str(text or ""))
    parsed, _ = parse_json_field(cleaned, "translation")
    if parsed is not None:
        return str(parsed).strip()

    lines = [ln.strip() for ln in cleaned.splitlines() if ln.strip()]
    if not lines:
        return ""

    first = _LEADING_LABEL_RE.sub("", lines[0]).strip().strip('"\'“”')
    if first:
        return re.sub(r"\s+", " ", first).strip()

    for ln in lines[1:]:
        ln = _LEADING_LABEL_RE.sub("", ln).strip()
        if ln:
            return re.sub(r"\s+", " ", ln.strip('"\'“”')).strip()
    return ""


def ensure_translation(text: str, fallback: str = "") -> str:
    sanitized = sanitize_translation(text)
    if sanitized:
        return sanitized

    raw = str(text or "").strip()
    if raw:
        return raw

    return str(fallback or "").strip() or "[translation unavailable]"
