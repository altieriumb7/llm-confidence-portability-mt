import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from utils.parse import coerce_confidence, parse_json_field, sanitize_translation
from utils.analysis_helpers import parse_preview_issues


def run():
    # Regression guard: malformed-but-parseable response fragments should be flagged.
    assert "confidence_trailing_text_after_json" in parse_preview_issues(
        "{\"confidence\": 0.92} trailing",
        "confidence",
    )
    assert "confidence_invalid_or_truncated_json" in parse_preview_issues(
        "{\"confidence\": 0.92",
        "confidence",
    )
    assert "translation_missing_expected_key" in parse_preview_issues(
        "{\"text\":\"Hallo\"}",
        "translation",
    )

    cases = [
        ("```json\n{\"translation\":\"Hallo Welt\"}\n```", "translation"),
        ("Sure: {\"confidence\":\"83%\"}", "confidence"),
        ("Translation: Guten Morgen", "translation"),
        ("not json", "confidence"),
    ]
    for text, field in cases:
        value, err = parse_json_field(text, field)
        print(f"field={field} value={value!r} err={err!r}")

    conf_samples = [0.91, "0.77", "83%", "Confidence: 0.64", "none"]
    for sample in conf_samples:
        print(f"coerce_confidence({sample!r}) -> {coerce_confidence(sample)!r}")

    translations = [
        "```json\n{\"translation\":\"Wie geht's?\"}\n```",
        "Translation: Das ist gut.",
        "\n\nDies ist direkt.",
    ]
    for sample in translations:
        print(f"sanitize_translation -> {sanitize_translation(sample)!r}")


if __name__ == "__main__":
    run()
