import json
import re
from typing import Any, Optional

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)
_LEADING_LABEL_RE = re.compile(r"^\s*(?:translation|output|answer)\s*[:=-]\s*", re.IGNORECASE)
_CONF_LABEL_RE = re.compile(r"(?i)confidence\s*[:= ]+(-?\d+(?:\.\d+)?)")
_PERCENT_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*%")
_DECIMAL_RE = re.compile(r"(?<!\d)(0(?:\.\d+)?|1(?:\.0+)?)(?!\d)")
_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


def strip_code_fences(text: str) -> str:
    cleaned = str(text or "").strip()
    if "```" not in cleaned:
        return cleaned

    def _unwrap(match: re.Match[str]) -> str:
        return match.group(1).strip()

    cleaned = _FENCE_RE.sub(_unwrap, cleaned)
    if cleaned.startswith("```") and cleaned.endswith("```"):
        cleaned = cleaned[3:-3].strip()
    return cleaned.strip()


def extract_first_json(text: str) -> dict | list | None:
    cleaned = strip_code_fences(text)
    if not cleaned:
        return None

    decoder = json.JSONDecoder()
    for idx, ch in enumerate(cleaned):
        if ch not in "[{":
            continue
        try:
            obj, _ = decoder.raw_decode(cleaned[idx:])
            if isinstance(obj, (dict, list)):
                return obj
        except Exception:
            continue
    return None


def ensure_confidence(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None

    out: Optional[float]
    if isinstance(value, (int, float)):
        out = float(value)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        pct = _PERCENT_RE.search(text)
        if pct:
            out = float(pct.group(1)) / 100.0
        else:
            m = _NUMBER_RE.search(text)
            if not m:
                return None
            out = float(m.group(0))
    else:
        return None

    if 1 < out <= 100:
        out /= 100.0
    if out < 0:
        out = 0.0
    if out > 1:
        out = 1.0
    return out


def coerce_translation(text: str) -> str:
    obj = extract_first_json(text)
    if isinstance(obj, dict):
        for key in ("translation", "output", "text", "translated_text"):
            val = obj.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()

    cleaned = strip_code_fences(text)
    cleaned = _LEADING_LABEL_RE.sub("", cleaned).strip()
    return cleaned.strip('"\'“”').strip()


def coerce_confidence(text: str) -> tuple[Optional[float], Optional[str]]:
    obj = extract_first_json(text)
    if isinstance(obj, dict):
        for key in ("confidence", "conf", "score", "probability"):
            if key in obj:
                val = ensure_confidence(obj.get(key))
                if val is not None:
                    return val, None

    cleaned = strip_code_fences(text)
    label_match = _CONF_LABEL_RE.search(cleaned)
    if label_match:
        val = ensure_confidence(label_match.group(1))
        if val is not None:
            return val, "confidence_coerced_regex"

    percent_match = _PERCENT_RE.search(cleaned)
    if percent_match:
        val = ensure_confidence(f"{percent_match.group(1)}%")
        if val is not None:
            return val, "confidence_coerced_regex"

    decimal_match = _DECIMAL_RE.search(cleaned)
    if decimal_match:
        val = ensure_confidence(decimal_match.group(1))
        if val is not None:
            return val, "confidence_coerced_regex"

    return None, "confidence_unparsed"
