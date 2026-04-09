import argparse
import math
from pathlib import Path

from utils.analysis_helpers import ece, group_by_model, json_dump, load_dataframe_rows, write_csv, write_markdown_table, write_tex_table


def _tokens(text: str) -> list[str]:
    return [tok for tok in str(text or "").strip().split() if tok]


def _digit_count(text: str) -> int:
    return sum(ch.isdigit() for ch in str(text or ""))


def _punct_count(text: str) -> int:
    return sum((not ch.isalnum()) and (not ch.isspace()) for ch in str(text or ""))


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2 or len(ys) < 2 or len(xs) != len(ys):
        return float("nan")
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mx) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - my) ** 2 for y in ys))
    if den_x == 0 or den_y == 0:
        return float("nan")
    return num / (den_x * den_y)


def _accepted_error_rate(rows: list[dict], score_key: str, top_fraction: float) -> float:
    ordered = sorted(rows, key=lambda r: float(r.get(score_key, 0.0)), reverse=True)
    k = max(1, int(len(ordered) * top_fraction))
    accepted = ordered[:k]
    return sum(int(r.get("error_within_model_q20", 0)) for r in accepted) / len(accepted)


def _comparator_score(row: dict, median_len_ratio: float) -> float:
    src = row.get("src", "")
    hyp = row.get("hyp", "")
    src_len = max(1, len(_tokens(src)))
    hyp_len = max(1, len(_tokens(hyp)))

    ratio = hyp_len / src_len
    len_term = _clamp01(1.0 - abs(ratio - median_len_ratio) / 0.75)

    src_digits = _digit_count(src)
    hyp_digits = _digit_count(hyp)
    digit_term = 1.0 - min(1.0, abs(src_digits - hyp_digits) / max(1, src_digits + 1))

    src_punct = _punct_count(src)
    hyp_punct = _punct_count(hyp)
    punct_term = 1.0 - min(1.0, abs(src_punct - hyp_punct) / max(1, src_punct + 1))

    warn_term = 0.0 if str(row.get("parse_warnings", "")).strip() else 1.0

    return _clamp01(0.55 * len_term + 0.2 * digit_term + 0.2 * punct_term + 0.05 * warn_term)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="runs/aggregated/dataframe.csv")
    ap.add_argument("--outdir", default="runs/aggregated/external_comparator")
    ap.add_argument("--coverage", type=float, default=0.2)
    args = ap.parse_args()

    rows = load_dataframe_rows(args.input)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    ratios = []
    for row in rows:
        src_len = max(1, len(_tokens(row.get("src", ""))))
        hyp_len = max(1, len(_tokens(row.get("hyp", ""))))
        ratios.append(hyp_len / src_len)
    median_len_ratio = sorted(ratios)[len(ratios) // 2] if ratios else 1.0

    detailed = []
    for row in rows:
        proxy = _comparator_score(row, median_len_ratio)
        row["external_proxy_conf"] = proxy
        detailed.append(
            {
                "id": row.get("id"),
                "provider": row.get("provider"),
                "model_id": row.get("model_id"),
                "external_proxy_conf": proxy,
                "conf": row.get("conf"),
                "chrf": row.get("chrf"),
                "error_within_model_q20": row.get("error_within_model_q20"),
            }
        )

    grouped = group_by_model(rows)
    summary_rows = []
    payload = {
        "meta": {
            "comparator": "surface_proxy_v1",
            "description": "Length/number/punctuation consistency heuristic plus parse-warning penalty.",
            "median_len_ratio": median_len_ratio,
            "coverage_top_fraction": args.coverage,
        },
        "models": {},
    }

    for model, model_rows in sorted(grouped.items()):
        valid_self = [r for r in model_rows if r.get("conf") is not None]
        self_conf = [float(r.get("conf", 0.0)) for r in valid_self]
        proxy_conf = [float(r.get("external_proxy_conf", 0.0)) for r in valid_self]
        chrf = [float(r.get("chrf", 0.0)) for r in valid_self]

        row = {
            "model": model,
            "corr_self_conf_vs_chrf": _pearson(self_conf, chrf),
            "corr_proxy_vs_chrf": _pearson(proxy_conf, chrf),
            "ece_self_conf": ece(valid_self, "error_within_model_q20", bins=10),
            "ece_proxy": ece([
                {**r, "conf": float(r.get("external_proxy_conf", 0.0))} for r in valid_self
            ], "error_within_model_q20", bins=10),
            "accepted_error_self_top_frac": _accepted_error_rate(valid_self, "conf", args.coverage),
            "accepted_error_proxy_top_frac": _accepted_error_rate(valid_self, "external_proxy_conf", args.coverage),
        }
        summary_rows.append(row)
        payload["models"][model] = row

    write_csv(
        outdir / "external_comparator_scores.csv",
        detailed,
        ["id", "provider", "model_id", "external_proxy_conf", "conf", "chrf", "error_within_model_q20"],
    )
    write_csv(
        outdir / "external_comparator_summary.csv",
        summary_rows,
        [
            "model",
            "corr_self_conf_vs_chrf",
            "corr_proxy_vs_chrf",
            "ece_self_conf",
            "ece_proxy",
            "accepted_error_self_top_frac",
            "accepted_error_proxy_top_frac",
        ],
    )
    write_markdown_table(
        outdir / "external_comparator_summary.md",
        "External comparator summary",
        summary_rows,
        [
            "model",
            "corr_self_conf_vs_chrf",
            "corr_proxy_vs_chrf",
            "ece_self_conf",
            "ece_proxy",
            "accepted_error_self_top_frac",
            "accepted_error_proxy_top_frac",
        ],
    )
    write_tex_table(
        outdir / "external_comparator_summary.tex",
        summary_rows,
        [
            "model",
            "corr_self_conf_vs_chrf",
            "corr_proxy_vs_chrf",
            "ece_self_conf",
            "ece_proxy",
            "accepted_error_self_top_frac",
            "accepted_error_proxy_top_frac",
        ],
    )
    json_dump(outdir / "external_comparator_summary.json", payload)
    print(f"Wrote external comparator artifacts to {outdir}")


if __name__ == "__main__":
    main()
