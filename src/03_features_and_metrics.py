import argparse
import csv
import glob
import math
import statistics
from pathlib import Path

from utils.common import load_config, read_jsonl


def tokenize(s):
    return [t for t in s.strip().split() if t]


def chrf_simple(h, r):
    hs, rs = set(h), set(r)
    if not hs and not rs:
        return 100.0
    p = len(hs & rs) / (len(hs) or 1)
    q = len(hs & rs) / (len(rs) or 1)
    return 100 * (2 * p * q / (p + q + 1e-9))


def bleu_simple(h, r):
    ht, rt = tokenize(h.lower()), tokenize(r.lower())
    if not ht:
        return 0.0
    overlap = sum(1 for t in ht if t in set(rt))
    prec = overlap / len(ht)
    bp = min(1.0, math.exp(1 - len(rt) / max(1, len(ht))))
    return 100 * bp * prec


def zscores(vals):
    if not vals:
        return []
    m = statistics.mean(vals)
    s = statistics.pstdev(vals)
    if s == 0:
        return [0.0] * len(vals)
    return [(v - m) / s for v in vals]


def quantile(vals, q):
    s = sorted(vals)
    if not s:
        return 0.0
    idx = int((len(s) - 1) * q)
    return s[idx]


def quartile_bucket(v, cuts):
    if v <= cuts[0]:
        return "Q1"
    if v <= cuts[1]:
        return "Q2"
    if v <= cuts[2]:
        return "Q3"
    return "Q4"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/models.yaml")
    ap.add_argument("--input_dir", default="runs/raw")
    ap.add_argument("--output", default="runs/aggregated/dataframe.csv")
    args = ap.parse_args()

    cfg = load_config(args.config)
    rows = []
    for fp in glob.glob(f"{args.input_dir}/*.jsonl"):
        rows.extend(read_jsonl(Path(fp)))
    if not rows:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["id","src","ref","hyp","conf","provider","model_id","latency_translate_s","latency_conf_s","input_tokens","output_tokens","timestamp_utc","quality","difficulty_score","difficulty_bucket","error_global_q20","error_within_model_q20"])
        print(f"Wrote empty {out}")
        return

    for r in rows:
        toks = tokenize(r["src"])
        r["src_len_tokens"] = len(toks)
        r["src_len_chars"] = len(r["src"])
        r["punct_count"] = sum(1 for c in r["src"] if not c.isalnum() and not c.isspace())
        r["ner_count"] = sum(1 for t in toks if t[:1].isupper())
        r["syntactic_depth"] = max(1, min(10, len(toks) // 4 + 1))
        r["rare_ratio"] = sum(1 for t in toks if len(t) >= 8) / (len(toks) or 1)
        r["chrf"] = chrf_simple(r["hyp"], r["ref"])
        r["bleu"] = bleu_simple(r["hyp"], r["ref"])
        r["quality"] = r["chrf"]

    for feat in ["src_len_tokens", "syntactic_depth", "rare_ratio", "ner_count"]:
        z = zscores([float(r[feat]) for r in rows])
        for i, r in enumerate(rows):
            r[f"z_{feat}"] = z[i]

    for r in rows:
        r["difficulty_score"] = r["z_src_len_tokens"] + r["z_syntactic_depth"] + r["z_rare_ratio"] + r["z_ner_count"]

    dvals = [r["difficulty_score"] for r in rows]
    cuts = [quantile(dvals, 0.25), quantile(dvals, 0.5), quantile(dvals, 0.75)]
    for r in rows:
        r["difficulty_bucket"] = quartile_bucket(r["difficulty_score"], cuts)

    global_thr = quantile([r["quality"] for r in rows], cfg["global"]["error_quantile_global"])
    for r in rows:
        r["error_global_q20"] = int(r["quality"] < global_thr)

    by_model = {}
    for i, r in enumerate(rows):
        key = (r["provider"], r["model_id"])
        by_model.setdefault(key, []).append(i)
    q = cfg["global"]["error_quantile_within_model"]
    for key, idxs in by_model.items():
        thr = quantile([rows[i]["quality"] for i in idxs], q)
        for i in idxs:
            rows[i]["error_within_model_q20"] = int(rows[i]["quality"] < thr)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    cols = list(rows[0].keys())
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
