import json
import re
from typing import Any, Optional, Tuple

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)
_LABEL_RE = re.compile(r"^\s*(?:translation|output|answer)\s*[:=-]\s*", re.IGNORECASE)
_NUMBER_RE = re.compile(r"(?i)(?:confidence|conf|score|probability)?\s*[:=]?\s*(-?\d+(?:\.\d+)?)\s*%?")


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


def find_first_json(text: str) -> Optional[Tuple[Any, str]]:
    cleaned = strip_code_fences(text)
    if not cleaned:
        return None

    decoder = json.JSONDecoder()
    starts = [idx for idx, ch in enumerate(cleaned) if ch in "[{"]
    for start in starts:
        try:
            obj, end = decoder.raw_decode(cleaned[start:])
        except Exception:
            continue
        return obj, cleaned[start : start + end]
    return None


def coerce_translation(resp_text: str) -> str:
    parsed = find_first_json(resp_text)
    if parsed is not None:
        obj, _ = parsed
        if isinstance(obj, dict):
            for key in ("translation", "translated_text", "output", "text"):
                val = obj.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()

    cleaned = strip_code_fences(resp_text)
    cleaned = _LABEL_RE.sub("", cleaned).strip()
    cleaned = cleaned.strip('"\'“”')
    return re.sub(r"\s+", " ", cleaned).strip()


def _coerce_numeric(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        out = float(value)
    elif isinstance(value, str):
        txt = value.strip()
        if not txt:
            return None
        pct_match = re.search(r"(-?\d+(?:\.\d+)?)\s*%", txt)
        if pct_match:
            out = float(pct_match.group(1)) / 100.0
        else:
            num_match = re.search(r"-?\d+(?:\.\d+)?", txt)
            if not num_match:
                return None
            out = float(num_match.group(0))
    else:
        return None

    if 1 < out <= 100:
        out = out / 100.0
    return max(0.0, min(1.0, out))


def coerce_confidence(resp_text: str) -> Tuple[Optional[float], Optional[str]]:
    parsed = find_first_json(resp_text)
    if parsed is not None:
        obj, _ = parsed
        if isinstance(obj, dict):
            for key in ("confidence", "conf", "score", "probability"):
                if key in obj:
                    value = _coerce_numeric(obj.get(key))
                    if value is not None:
                        return value, None
                    return None, f"invalid_{key}_value"

    cleaned = strip_code_fences(resp_text)
    for match in _NUMBER_RE.finditer(cleaned):
        token = match.group(1)
        if token is None:
            continue
        value = _coerce_numeric(token if "%" not in match.group(0) else f"{token}%")
        if value is not None:
            return value, "confidence_from_regex"
    return None, "no_confidence_found"


def normalize_json_obj(obj: Any, kind: str) -> Tuple[Optional[dict], list[str]]:
    warnings: list[str] = []
    kind = (kind or "").strip().lower()
    if kind not in {"translation", "confidence"}:
        return None, ["unsupported_kind"]

    if kind == "translation":
        if isinstance(obj, dict):
            for key in ("translation", "translated_text", "output", "text"):
                if key in obj:
                    text = str(obj.get(key) or "").strip()
                    if text:
                        if key != "translation":
                            warnings.append(f"mapped_{key}_to_translation")
                        return {"translation": text}, warnings
        warnings.append("translation_not_found")
        return None, warnings

    if isinstance(obj, dict):
        for key in ("confidence", "conf", "score", "probability"):
            if key in obj:
                value = _coerce_numeric(obj.get(key))
                if value is not None:
                    if key != "confidence":
                        warnings.append(f"mapped_{key}_to_confidence")
                    return {"confidence": value}, warnings
                warnings.append(f"invalid_{key}_value")
                return None, warnings

    warnings.append("confidence_not_found")
    return None, warnings
