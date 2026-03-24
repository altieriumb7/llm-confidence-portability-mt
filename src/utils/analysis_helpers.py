import csv
import json
from pathlib import Path
from typing import Iterable, Optional

from utils.parse import coerce_confidence


DEFAULT_THRESHOLD_GRID = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95]


def as_float(value, default=0.0):
    try:
        if value in (None, "", "nan"):
            return default
        return float(value)
    except Exception:
        return default


def quantile(vals: list[float], q: float) -> float:
    ordered = sorted(vals)
    if not ordered:
        return 0.0
    idx = int((len(ordered) - 1) * q)
    return ordered[idx]


def ece(rows: list[dict], error_col: str, bins: int = 10) -> float:
    valid = [r for r in rows if r.get("conf") is not None]
    if not valid:
        return float("nan")
    total = 0.0
    for bucket in range(bins):
        lo, hi = bucket / bins, (bucket + 1) / bins
        if bucket == bins - 1:
            chunk = [r for r in valid if lo <= r["conf"] <= 1.0]
        else:
            chunk = [r for r in valid if lo <= r["conf"] < hi]
        if not chunk:
            continue
        mean_conf = sum(r["conf"] for r in chunk) / len(chunk)
        mean_acc = sum(1 - int(r.get(error_col, 0)) for r in chunk) / len(chunk)
        total += (len(chunk) / len(valid)) * abs(mean_acc - mean_conf)
    return total


def warning_tokens(value: str) -> list[str]:
    return [token.strip() for token in str(value or "").split(";") if token.strip()]


def warning_breakdown(tokens: list[str]) -> dict:
    translation = [t for t in tokens if t.startswith("translation") or t.startswith("mapped_") and "translation" in t]
    confidence = [t for t in tokens if t.startswith("confidence") or t.startswith("mapped_") and "confidence" in t or t.startswith("invalid_conf")]
    repaired = [t for t in tokens if "repaired" in t or "format_fix" in t]
    fallback = [t for t in tokens if t.endswith("_from_regex") or t.endswith("_from_word") or t.endswith("_from_partial_json") or t.endswith("_no_json")]
    return {
        "translation_tokens": translation,
        "confidence_tokens": confidence,
        "repair_tokens": repaired,
        "fallback_tokens": fallback,
    }


def load_dataframe_rows(path: str | Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        conf = coerce_confidence(row.get("conf"))
        if conf is None:
            conf = coerce_confidence(row.get("confidence"))
        row["conf"] = conf
        for key in [
            "chrf",
            "bleu",
            "quality",
            "difficulty_score",
            "latency_translate_s",
            "latency_conf_s",
            "input_tokens",
            "output_tokens",
        ]:
            row[key] = as_float(row.get(key), 0.0)
        for key in [k for k in row.keys() if k.startswith("error_")]:
            row[key] = int(as_float(row.get(key), 0))
        row["warning_tokens"] = warning_tokens(row.get("parse_warnings", ""))
        row.update(warning_breakdown(row["warning_tokens"]))
        row["model"] = f"{row.get('provider', 'unknown')}/{row.get('model_id', 'unknown')}"
    return rows


def group_by_model(rows: Iterable[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row["model"], []).append(row)
    return grouped


def json_dump(path: str | Path, payload: dict) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_csv(path: str | Path, rows: list[dict], fieldnames: list[str]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown_table(path: str | Path, title: str, rows: list[dict], columns: list[str]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title}", "", "| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        rendered = []
        for col in columns:
            value = row.get(col, "")
            if isinstance(value, float):
                rendered.append(f"{value:.4f}")
            else:
                rendered.append(str(value))
        lines.append("| " + " | ".join(rendered) + " |")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_tex_table(path: str | Path, rows: list[dict], columns: list[str]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    header = " & ".join(columns) + r" \\"
    body = []
    for row in rows:
        cells = []
        for col in columns:
            value = row.get(col, "")
            if isinstance(value, float):
                cells.append(f"{value:.4f}")
            else:
                cells.append(str(value).replace("_", r"\_"))
        body.append(" & ".join(cells) + r" \\")
    tex = "\n".join([
        r"\begin{tabular}{" + "l" * len(columns) + "}",
        r"\toprule",
        header,
        r"\midrule",
        *body,
        r"\bottomrule",
        r"\end{tabular}",
        "",
    ])
    target.write_text(tex, encoding="utf-8")
