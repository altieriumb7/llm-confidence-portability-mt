from __future__ import annotations

from typing import Any, Dict


DEFAULT_VARIANTS = {
    "canonical_v1": {
        "translation_user_template": (
            "Translate English to German. "
            "Return JSON with exactly one key: {\"translation\":\"...\"}.\n\n"
            "SOURCE: {src}"
        ),
        "confidence_user_template": (
            "Rate translation correctness confidence from 0 to 1. "
            "Return JSON with exactly one key: {\"confidence\":0.73}.\n\n"
            "SOURCE: {src}\nTRANSLATION: {hyp}"
        ),
    },
    "minimal_v2": {
        "translation_user_template": (
            "Task: English->German translation. "
            "Output must be one JSON object and only this key: {\"translation\":\"...\"}.\n\n"
            "English: {src}"
        ),
        "confidence_user_template": (
            "Task: estimate confidence that the German translation is correct. "
            "Respond with one JSON object and only this key: {\"confidence\":0.73}.\n\n"
            "English: {src}\nGerman translation: {hyp}"
        ),
    },
    "verifier_v3": {
        "translation_user_template": (
            "Produce a faithful German translation of the sentence below. "
            "Return strict JSON with exactly one field {\"translation\":\"...\"}; no extra keys.\n\n"
            "SOURCE_SENTENCE: {src}"
        ),
        "confidence_user_template": (
            "Judge how likely the German translation preserves the source meaning. "
            "Return strict JSON with exactly one field {\"confidence\":0.73} where 0 is very unlikely and 1 is very likely.\n\n"
            "SOURCE_SENTENCE: {src}\nTRANSLATION_TO_JUDGE: {hyp}"
        ),
    },
}


def _variant_block(cfg: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    block = (cfg.get("global") or {}).get("prompt_variants") or {}
    merged = {**DEFAULT_VARIANTS}
    for key, payload in block.items():
        if isinstance(payload, dict):
            merged[str(key)] = payload
    return merged


def default_variant(cfg: Dict[str, Any]) -> str:
    return str((cfg.get("global") or {}).get("default_prompt_variant", "canonical_v1"))


def resolve_variant(cfg: Dict[str, Any], requested: str | None = None) -> tuple[str, Dict[str, str]]:
    variants = _variant_block(cfg)
    name = requested or default_variant(cfg)
    if name not in variants:
        known = ", ".join(sorted(variants))
        raise ValueError(f"Unknown prompt variant '{name}'. Known variants: {known}")
    payload = variants[name]
    t = payload.get("translation_user_template")
    c = payload.get("confidence_user_template")
    if not t or not c:
        raise ValueError(f"Prompt variant '{name}' must define translation_user_template and confidence_user_template")
    return name, {"translation_user_template": t, "confidence_user_template": c}


def list_variant_names(cfg: Dict[str, Any]) -> list[str]:
    return sorted(_variant_block(cfg).keys())


def render_translation_prompt(cfg: Dict[str, Any], src: str, variant: str | None = None) -> tuple[str, str]:
    name, payload = resolve_variant(cfg, variant)
    return name, payload["translation_user_template"].format(src=src)


def render_confidence_prompt(cfg: Dict[str, Any], src: str, hyp: str, variant: str | None = None) -> tuple[str, str]:
    name, payload = resolve_variant(cfg, variant)
    return name, payload["confidence_user_template"].format(src=src, hyp=hyp)
