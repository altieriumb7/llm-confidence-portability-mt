#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from utils.parse import coerce_confidence, parse_json_field, sanitize_translation


CASES = [
    ("```json\n{\"translation\":\"Hallo Welt\"}\n```", "translation", "Hallo Welt"),
    ("Some text\n{\"confidence\": 0.81}\nmore", "confidence", 0.81),
    ("{\"confidence\":\"83%\"}", "confidence", "83%"),
    ("Translation: Guten Morgen", "translation", None),
]


def main():
    ok = True
    for i, (text, field, expected) in enumerate(CASES, 1):
        value, err = parse_json_field(text, field)
        print(f"Case {i}: field={field} value={value!r} err={err}")
        if expected is not None and value != expected:
            ok = False

    print("coerce_confidence('83%') ->", coerce_confidence("83%"))
    print("coerce_confidence('Confidence: 0.67') ->", coerce_confidence("Confidence: 0.67"))
    print("sanitize_translation('Translation: Guten Tag') ->", sanitize_translation("Translation: Guten Tag"))

    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
