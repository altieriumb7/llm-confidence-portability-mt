import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

from utils.common import load_config
from utils.parse import coerce_confidence


def as_float(x, default=0.0):
    try:
        if x in (None, "", "nan"):
            return default
        return float(x)
    except Exception:
        return default


def deterministic_split(row_id: str, label: str, modulus: int = 5) -> bool:
    digest = hashlib.sha256(f"{label}::{row_id}".encode("utf-8")).hexdigest()
    return (int(digest[:8], 16) % modulus) < 2


def ece(rows, conf_key: str, label_key: str, bins: int = 10) -> float:
    valid = [r for r in rows if r.get(conf_key) is not None]
    if not valid:
        return float("nan")
    total = 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        if b == bins - 1:
            chunk = [r for r in valid if lo <= r[conf_key] <= 1.0]
        else:
            chunk = [r for r in valid if lo <= r[conf_key] < hi]
        if not chunk:
            continue
        mean_conf = sum(r[conf_key] for r in chunk) / len(chunk)
        mean_acc = sum(r[label_key] for r in chunk) / len(chunk)
        total += (len(chunk) / len(valid)) * abs(mean_acc - mean_conf)
    return total


def mismatch_at(rows, conf_key: str, label_key: str, tau: float = 0.9) -> float:
    valid = [r for r in rows if r.get(conf_key) is not None]
    if not valid:
        return float("nan")
    return sum(1 for r in valid if r[conf_key] > tau and r[label_key] == 0) / len(valid)


def pav_isotonic(xs, ys):
    pairs = sorted(zip(xs, ys), key=lambda t: t[0])
    blocks = []
    for x, y in pairs:
        blocks.append({"sum_y": y, "count": 1, "x_min": x, "x_max": x})
        while len(blocks) >= 2:
            left = blocks[-2]
            right = blocks[-1]
            if (left["sum_y"] / left["count"]) <= (right["sum_y"] / right["count"]):
                break
            merged = {
                "sum_y": left["sum_y"] + right["sum_y"],
                "count": left["count"] + right["count"],
                "x_min": left["x_min"],
                "x_max": right["x_max"],
            }
            blocks = blocks[:-2] + [merged]
    model = []
    for block in blocks:
        model.append(
            {
                "x_min": block["x_min"],
                "x_max": block["x_max"],
                "value": block["sum_y"] / block["count"],
                "count": block["count"],
            }
        )
    return model


def apply_isotonic(x, model):
    if not model:
        return x
    if x <= model[0]["x_max"]:
        return model[0]["value"]
    for block in model:
        if block["x_min"] <= x <= block["x_max"]:
            return block["value"]
    return model[-1]["value"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/models.yaml")
    ap.add_argument("--input", default="runs/aggregated/dataframe.csv")
    ap.add_argument("--outdir", default="runs/aggregated/calibration")
    ap.add_argument("--label_col", default="error_within_model_q20")
    ap.add_argument("--bins", type=int, default=10)
    ap.add_argument("--tau", type=float, default=0.9)
    args = ap.parse_args()

    cfg = load_config(args.config)
    tau = float(args.tau if args.tau is not None else cfg.get("global", {}).get("mismatch_tau", 0.9))

    with open(args.input, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    grouped = {}
    for row in rows:
        conf = coerce_confidence(row.get("conf"))
        if conf is None:
            conf = coerce_confidence(row.get("confidence"))
        if conf is None:
            continue
        row["conf_before"] = min(1.0, max(0.0, float(conf)))
        row["correct_label"] = 1 - int(as_float(row.get(args.label_col), 0))
        label = f"{row.get('provider','unknown')}/{row.get('model_id','unknown')}"
        grouped.setdefault(label, []).append(row)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    artifact = {
        "config": {
            "input": args.input,
            "label_col": args.label_col,
            "bins": args.bins,
            "tau": tau,
            "split": "deterministic hash split; 40% calibration / 60% evaluation",
        },
        "models": {},
    }

    for label, model_rows in sorted(grouped.items()):
        calib = [r for r in model_rows if deterministic_split(str(r.get("id")), label)]
        eval_rows = [r for r in model_rows if not deterministic_split(str(r.get("id")), label)]
        if not calib or not eval_rows:
            calib = model_rows[::2]
            eval_rows = model_rows[1::2] or model_rows

        iso_model = pav_isotonic([r["conf_before"] for r in calib], [r["correct_label"] for r in calib])
        for r in eval_rows:
            r["conf_after"] = apply_isotonic(r["conf_before"], iso_model)

        before_ece = ece(eval_rows, "conf_before", "correct_label", bins=args.bins)
        after_ece = ece(eval_rows, "conf_after", "correct_label", bins=args.bins)
        before_mismatch = mismatch_at(eval_rows, "conf_before", "correct_label", tau=tau)
        after_mismatch = mismatch_at(eval_rows, "conf_after", "correct_label", tau=tau)

        thresholds = []
        for threshold in [round(i / 20, 2) for i in range(10, 20)]:
            subset = [r for r in eval_rows if r["conf_after"] > threshold]
            coverage = len(subset) / len(eval_rows) if eval_rows else 0.0
            mismatch = mismatch_at(subset, "conf_after", "correct_label", tau=threshold) if subset else float("nan")
            thresholds.append({"threshold": threshold, "coverage": coverage, "mismatch_rate": mismatch})

        summary_rows.append(
            {
                "model": label,
                "n_calibration": len(calib),
                "n_eval": len(eval_rows),
                "ece_before": before_ece,
                "ece_after": after_ece,
                "ece_delta": after_ece - before_ece,
                "mismatch_at_0_9_before": before_mismatch,
                "mismatch_at_0_9_after": after_mismatch,
                "mismatch_delta": after_mismatch - before_mismatch,
            }
        )
        artifact["models"][label] = {
            "n_calibration": len(calib),
            "n_eval": len(eval_rows),
            "isotonic_blocks": iso_model,
            "metrics": summary_rows[-1],
            "threshold_scan": thresholds,
        }

    csv_path = outdir / "calibration_summary.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "model",
                "n_calibration",
                "n_eval",
                "ece_before",
                "ece_after",
                "ece_delta",
                "mismatch_at_0_9_before",
                "mismatch_at_0_9_after",
                "mismatch_delta",
            ],
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    (outdir / "calibration_summary.json").write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"Wrote calibration artifacts to {outdir}")


if __name__ == "__main__":
    main()
