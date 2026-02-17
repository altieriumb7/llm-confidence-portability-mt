import json
import re
from typing import Any, Optional, Tuple

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)
_LABEL_RE = re.compile(r"^\s*(?:translation|output|answer)\s*[:=-]\s*", re.IGNORECASE)
_PARTIAL_TRANSLATION_RE = re.compile(r'"translation"\s*:\s*"((?:\\.|[^"\\])*)', re.IGNORECASE | re.DOTALL)
_PARTIAL_CONFIDENCE_RE = re.compile(
    r'"(?:confidence|conf|score|probability)"\s*:\s*(-?(?:\d+(?:[\.,]\d+)?|[\.,]\d+)(?:e[+-]?\d+)?)',
    re.IGNORECASE,
)
_NUMBER_RE = re.compile(
    r"(?ix)(?:confidence|conf|score|probability)?\s*[:=]?\s*"
    r"("
    r"-?(?:\d+(?:[\.,]\d+)?|[\.,]\d+)(?:e[+-]?\d+)?"
    r"|"
    r"-?(?:\d+(?:[\.,]\d+)?)\s*/\s*(?:\d+(?:[\.,]\d+)?)"
    r")\s*%?"
)


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
    partial = _PARTIAL_TRANSLATION_RE.search(cleaned)
    if partial:
        value = partial.group(1).encode("utf-8").decode("unicode_escape").strip()
        if value:
            return value

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

        normalized = txt.replace(",", ".")

        fraction_match = re.search(
            r"(-?(?:\d+(?:\.\d+)?|\.\d+))\s*/\s*(\d+(?:\.\d+)?)",
            normalized,
        )
        if fraction_match:
            den = float(fraction_match.group(2))
            if den == 0:
                return None
            out = float(fraction_match.group(1)) / den
        else:
            pct_match = re.search(
                r"(-?(?:\d+(?:\.\d+)?|\.\d+)(?:e[+-]?\d+)?)\s*%",
                normalized,
                re.IGNORECASE,
            )
            if pct_match:
                out = float(pct_match.group(1)) / 100.0
            else:
                num_match = re.search(
                    r"-?(?:\d+(?:\.\d+)?|\.\d+)(?:e[+-]?\d+)?",
                    normalized,
                    re.IGNORECASE,
                )
                if not num_match:
                    return None
                out = float(num_match.group(0))
    else:
        return None

    if 1 < out <= 100:
        out = out / 100.0
    return max(0.0, min(1.0, out))


def _coerce_confidence_word(text: str) -> Optional[float]:
    lowered = (text or "").lower()
    if not lowered.strip():
        return None
    if re.search(r"\b(?:very\s+high|high)\b", lowered):
        return 0.9
    if re.search(r"\b(?:medium|moderate)\b", lowered):
        return 0.6
    if re.search(r"\blow\b", lowered):
        return 0.3
    return None


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
                    word_value = _coerce_confidence_word(str(obj.get(key)))
                    if word_value is not None:
                        return word_value, "confidence_from_word"
                    return None, f"invalid_{key}_value"

    cleaned = strip_code_fences(resp_text)
    partial = _PARTIAL_CONFIDENCE_RE.search(cleaned)
    if partial:
        value = _coerce_numeric(partial.group(1))
        if value is not None:
            return value, "confidence_from_partial_json"

    for match in _NUMBER_RE.finditer(cleaned):
        token = match.group(1)
        if token is None:
            continue
        value = _coerce_numeric(token if "%" not in match.group(0) else f"{token}%")
        if value is not None:
            return value, "confidence_from_regex"

    word_value = _coerce_confidence_word(cleaned)
    if word_value is not None:
        return word_value, "confidence_from_word"

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
