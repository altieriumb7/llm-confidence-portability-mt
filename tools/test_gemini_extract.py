import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from providers.gemini_client import _extract_text


class Obj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_preface_with_hidden_json_leaf():
    # Simulates SDK objects where candidate.parts[0].text is just a preface,
    # while structured payload is stored under a less common attribute.
    part = Obj(text="Here is the JSON requested:", thought={"translation": "Hallo Welt"})
    resp = Obj(candidates=[Obj(content=Obj(parts=[part]))])
    out = _extract_text(resp)
    assert "translation" in out and "Hallo Welt" in out, out


def test_joined_structured_text_is_kept():
    part = Obj(text='{"confidence": 0.73}')
    resp = Obj(candidates=[Obj(content=Obj(parts=[part]))])
    out = _extract_text(resp)
    assert out == '{"confidence": 0.73}', out


if __name__ == "__main__":
    test_preface_with_hidden_json_leaf()
    test_joined_structured_text_is_kept()
    print("ok")
