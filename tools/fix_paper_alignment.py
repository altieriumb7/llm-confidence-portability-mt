from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(".")
CFG = ROOT / "configs" / "models.yaml"
F03 = ROOT / "src" / "03_features_and_metrics.py"
F04 = ROOT / "src" / "04_analysis_and_plots.py"

def backup(p: Path):
    bak = p.with_suffix(p.suffix + ".bak")
    if not bak.exists():
        bak.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")

def ensure_yaml_scalar(text: str, key: str, value: str) -> str:
    pat = rf"(?m)^(\s*{re.escape(key)}\s*:\s*).*$"
    if re.search(pat, text) is None:
        raise SystemExit(f"[ERROR] YAML key not found: {key}")
    return re.sub(pat, rf"\g<1>{value}", text, count=1)

def insert_after_yaml_key(text: str, after_key: str, block: str) -> str:
    if block.strip() in text:
        return text
    lines = text.splitlines(True)
    for i, line in enumerate(lines):
        if re.match(rf"^\s*{re.escape(after_key)}\s*:\s*.*$", line):
            ins = "\n" + block.rstrip() + "\n"
            lines.insert(i + 1, ins)
            return "".join(lines)
    raise SystemExit(f"[ERROR] Could not insert YAML block after: {after_key}")

def patch_models_yaml():
    backup(CFG)
    t = CFG.read_text(encoding="utf-8")
    t = ensure_yaml_scalar(t, "mismatch_tau", "0.9")
    t = ensure_yaml_scalar(t, "tau", "0.9")
    t = ensure_yaml_scalar(t, "bootstrap_samples", "2000")
    if "error_quantile_within_model_chrf_q10" not in t:
        t = insert_after_yaml_key(
            t,
            "mismatch_error_col",
            "  # Appendix C robustness variant: within-model bottom 10% chrF\n"
            "  error_quantile_within_model_chrf_q10: 0.1",
        )
    CFG.write_text(t, encoding="utf-8")
    print("[OK] configs/models.yaml")

def patch_03():
    backup(F03)
    t = F03.read_text(encoding="utf-8")

    anchor = (
        '    q = cfg["global"]["error_quantile_within_model"]\n'
        "    for _, idxs in by_model.items():\n"
        '        thr = quantile([rows[i]["quality"] for i in idxs], q)\n'
        "        for i in idxs:\n"
        '            rows[i]["error_within_model_q20"] = int(rows[i]["quality"] < thr)\n'
    )
    if anchor not in t:
        raise SystemExit("[ERROR] 03_features_and_metrics.py anchor not found (file layout changed).")

    if "error_within_model_bleu_q20" not in t:
        insert = (
            "\n"
            "    # Appendix C / Table 4 robustness variants\n"
            "    # (ii) within-model bottom 20% BLEU\n"
            "    for _, idxs in by_model.items():\n"
            "        thr_bleu = quantile([rows[i]['bleu'] for i in idxs], q)\n"
            "        for i in idxs:\n"
            "            rows[i]['error_within_model_bleu_q20'] = int(rows[i]['bleu'] < thr_bleu)\n"
            "\n"
            "    # (iii) within-model bottom 10% chrF\n"
            "    q10 = float((cfg.get('global') or {}).get('error_quantile_within_model_chrf_q10', 0.1))\n"
            "    for _, idxs in by_model.items():\n"
            "        thr10 = quantile([rows[i]['quality'] for i in idxs], q10)\n"
            "        for i in idxs:\n"
            "            rows[i]['error_within_model_chrf_q10'] = int(rows[i]['quality'] < thr10)\n"
        )
        t = t.replace(anchor, anchor + insert)
        print("[OK] src/03_features_and_metrics.py (robustness error cols)")

    F03.write_text(t, encoding="utf-8")

def insert_before(text: str, marker: str, block: str) -> str:
    if block.strip() in text:
        return text
    i = text.find(marker)
    if i == -1:
        raise SystemExit(f"[ERROR] Marker not found: {marker}")
    return text[:i] + block + text[i:]

def patch_04():
    backup(F04)
    t = F04.read_text(encoding="utf-8")

    # add bootstrap_ci_metric before _safe_slug
    if "def bootstrap_ci_metric(" not in t:
        marker = "\n\ndef _safe_slug(label: str) -> str:"
        block = (
            "\n\n"
            "def bootstrap_ci_metric(rows, metric_fn, n=500, seed=123):\n"
            "    \"\"\"Bootstrap CI for metrics that must be recomputed on resampled rows (e.g., ECE).\"\"\"\n"
            "    if not rows:\n"
            "        return [float('nan'), float('nan')]\n"
            "    rng = random.Random(seed)\n"
            "    stats = []\n"
            "    for _ in range(n):\n"
            "        samp = [rows[rng.randrange(len(rows))] for _ in range(len(rows))]\n"
            "        stats.append(float(metric_fn(samp)))\n"
            "    stats.sort()\n"
            "    return [stats[int(0.025 * (n - 1))], stats[int(0.975 * (n - 1))]]\n"
        )
        t = insert_before(t, marker, block)
        print("[OK] src/04_analysis_and_plots.py (bootstrap_ci_metric)")

    # allowed mismatch_error_col
    if 'allowed_error_cols' not in t:
        old = (
            '    mismatch_error_col = g.get("mismatch_error_col", "error_within_model_q20")\n'
            '    if mismatch_error_col not in {"error_within_model_q20", "error_global_q20"}:\n'
            '        raise ValueError("global.mismatch_error_col must be error_within_model_q20 or error_global_q20")\n'
        )
        new = (
            '    mismatch_error_col = g.get("mismatch_error_col", "error_within_model_q20")\n'
            '    allowed_error_cols = {\n'
            '        "error_within_model_q20",\n'
            '        "error_global_q20",\n'
            '        "error_within_model_bleu_q20",\n'
            '        "error_within_model_chrf_q10",\n'
            '    }\n'
            '    if mismatch_error_col not in allowed_error_cols:\n'
            '        raise ValueError(f"global.mismatch_error_col must be one of: {sorted(allowed_error_cols)}")\n'
        )
        if old in t:
            t = t.replace(old, new)
            print("[OK] src/04_analysis_and_plots.py (allowed_error_cols)")

    # parse additional error cols
    t = t.replace(
        '        for k in ["error_global_q20", "error_within_model_q20"]:',
        '        for k in ["error_global_q20", "error_within_model_q20", "error_within_model_bleu_q20", "error_within_model_chrf_q10"]:',
    )

    # tau default fallback
    t = t.replace(
        '    configured_tau = float(g.get("mismatch_tau", g.get("tau", 0.1)))',
        '    configured_tau = float(g.get("mismatch_tau", g.get("tau", 0.9)))',
    )

    # add multi_tau metrics for robustness error defs (Table 4)
    needle = '            multi_tau[f"mismatch_rate_overall_global_q20_tau_{tau:.1f}"] = _mismatch_rate(valid_conf, "error_global_q20", tau)\n'
    add_lines = (
        '            multi_tau[f"mismatch_rate_overall_within_model_bleu_q20_tau_{tau:.1f}"] = _mismatch_rate(valid_conf, "error_within_model_bleu_q20", tau)\n'
        '            multi_tau[f"mismatch_rate_overall_within_model_chrf_q10_tau_{tau:.1f}"] = _mismatch_rate(valid_conf, "error_within_model_chrf_q10", tau)\n'
    )
    if needle in t and "mismatch_rate_overall_within_model_bleu_q20_tau_" not in t:
        t = t.replace(needle, needle + add_lines)
        print("[OK] src/04_analysis_and_plots.py (multi_tau robustness metrics)")

    # bootstrap ECE CI: recompute binned ECE
    old_ece = (
        '                "ece": bootstrap_ci(\n'
        '                    [abs((1 - r[mismatch_error_col]) - r["conf"]) for r in valid_conf],\n'
        '                    g["bootstrap_samples"],\n'
        '                ),\n'
    )
    if old_ece in t:
        new_ece = (
            '                # Recompute binned ECE on each bootstrap resample (paper method)\n'
            '                "ece": bootstrap_ci_metric(\n'
            '                    valid_conf,\n'
            '                    lambda samp: ece(samp, mismatch_error_col, g["conf_bins"]),\n'
            '                    g["bootstrap_samples"],\n'
            '                ),\n'
        )
        t = t.replace(old_ece, new_ece)
        print("[OK] src/04_analysis_and_plots.py (ECE bootstrap)")

    # add mismatch@0.9 CI (paper headline)
    if '"mismatch_rate_overall_tau_0.9"' not in t:
        after = '                "mismatch_rate_overall": bootstrap_ci(mism, g["bootstrap_samples"]),\n'
        if after in t:
            t = t.replace(
                after,
                after +
                '                # Table 1 headline CI: mismatch@0.9\n'
                '                "mismatch_rate_overall_tau_0.9": bootstrap_ci(\n'
                '                    [1 if (r[mismatch_error_col] == 1 and r["conf"] > 0.9) else 0 for r in valid_conf],\n'
                '                    g["bootstrap_samples"],\n'
                '                ),\n'
            )
            print("[OK] src/04_analysis_and_plots.py (mismatch@0.9 bootstrap CI)")

    # extend summary row + CSV columns
    if '"median_conf"' not in t:
        anchor = '                "mismatch_rate_overall": (sum(mism) / len(mism)) if mism else float("nan"),\n'
        if anchor in t:
            t = t.replace(
                anchor,
                anchor +
                '                "median_conf": conf_stats["median_conf"],\n'
                '                "mismatch_rate_overall_tau_0.9": multi_tau.get("mismatch_rate_overall_tau_0.9", float("nan")),\n'
                '                "valid_conf_count": len(valid_conf),\n'
                '                "total_count": len(d),\n'
            )
            print("[OK] src/04_analysis_and_plots.py (summary row extended)")

    old_fields = 'fieldnames=["model", "mean_quality", "ece_global_q20", "ece_within_model_q20", "mismatch_rate_overall", "avg_total_latency_s"],'
    if old_fields in t:
        t = t.replace(
            old_fields,
            'fieldnames=["model", "mean_quality", "ece_global_q20", "ece_within_model_q20", "mismatch_rate_overall", "median_conf", "mismatch_rate_overall_tau_0.9", "valid_conf_count", "total_count", "avg_total_latency_s"],'
        )
        print("[OK] src/04_analysis_and_plots.py (summary fieldnames)")

    # empty-case header
    t = t.replace(
        "model,mean_quality,ece_global_q20,ece_within_model_q20,mismatch_rate_overall,avg_total_latency_s\n",
        "model,mean_quality,ece_global_q20,ece_within_model_q20,mismatch_rate_overall,median_conf,mismatch_rate_overall_tau_0.9,valid_conf_count,total_count,avg_total_latency_s\n",
    )

    F04.write_text(t, encoding="utf-8")
    print("[OK] src/04_analysis_and_plots.py")

def main():
    for p in (CFG, F03, F04):
        if not p.exists():
            raise SystemExit(f"[ERROR] Missing: {p}")
    patch_models_yaml()
    patch_03()
    patch_04()
    print("\n✅ Done. Backups are .bak files next to each patched file.")

if __name__ == "__main__":
    main()
