#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from difflib import unified_diff
from pathlib import Path


def _f(x: str | float, nd=3) -> float:
    return float(x)


def _pct(x: str | float, nd=1) -> str:
    return f"{100.0 * float(x):.{nd}f}\\%"


def _render_table(label: str, caption: str, headers: list[str], rows: list[list[str]], align: str) -> str:
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\small",
        rf"\begin{{tabular}}{{{align}}}",
        r"\toprule",
        " & ".join(headers) + r" \\",
        r"\midrule",
    ]
    for r in rows:
        lines.append(" & ".join(r) + r" \\")
    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        rf"\caption{{{caption}}}",
        rf"\label{{{label}}}",
        r"\end{table}",
        "",
    ])
    return "\n".join(lines)


def build_summary_table(summary_csv: Path) -> str:
    rows = sorted(csv.DictReader(summary_csv.open(encoding="utf-8")), key=lambda r: r["model"])
    out = []
    for r in rows:
        out.append([
            r["model"],
            f"{_f(r['mean_quality']):.2f}",
            f"{_f(r['ece_within_model_q20']):.3f}",
            _pct(r["mismatch_rate_overall_tau_0.9"]),
            f"{_f(r['median_conf']):.2f}",
        ])
    return _render_table(
        label="tab:main",
        caption="Main summary table from regenerated code-side outputs (within-model chrF-q20 target).",
        headers=["Model", "Mean chrF", "ECE (within-q20)", "Mismatch@0.9", "Median conf."],
        rows=out,
        align="lcccc",
    )


def build_corr_table(results_json: Path) -> str:
    results = json.loads(results_json.read_text(encoding="utf-8"))
    out = []
    for model in sorted(results):
        corr = results[model]["correlations"]
        out.append([
            model,
            f"{float(corr['pearson_difficulty_conf']):.3f}",
            f"{float(corr['pearson_difficulty_quality']):.3f}",
            f"{float(corr['pearson_conf_quality']):.3f}",
        ])
    return _render_table(
        label="tab:corr",
        caption="Pearson correlations from regenerated analysis outputs.",
        headers=["Model", "$r$(difficulty, conf)", "$r$(difficulty, chrF)", "$r$(conf, chrF)"],
        rows=out,
        align="lccc",
    )


def build_robustness_table(results_json: Path) -> str:
    results = json.loads(results_json.read_text(encoding="utf-8"))
    out = []
    for model in sorted(results):
        out.append([
            model,
            _pct(results[model]["mismatch_rate_overall_within_model_q20_tau_0.9"]),
            _pct(results[model]["mismatch_rate_overall_global_q20_tau_0.9"]),
        ])
    return _render_table(
        label="tab:robustness",
        caption=r"Appendix robustness comparison across chrF-based low-quality definitions at $\tau=0.9$.",
        headers=["Model", "Mismatch@0.9 (within-model chrF-q20)", "Mismatch@0.9 (global chrF-q20)"],
        rows=out,
        align="lcc",
    )


def build_calibration_table(calibration_json: Path) -> str:
    payload = json.loads(calibration_json.read_text(encoding="utf-8"))
    models = payload["models"]
    out = []
    for model in sorted(models):
        m = models[model]["metrics"]
        out.append([
            model,
            f"{float(m['ece_before']):.3f}",
            f"{float(m['ece_after']):.3f}",
            _pct(m["mismatch_at_0_9_before"]),
            _pct(m["mismatch_at_0_9_after"]),
        ])
    return _render_table(
        label="tab:calibration",
        caption="Held-out isotonic calibration summary from regenerated calibration artifacts.",
        headers=["Model", "ECE before", "ECE after", "Mismatch@0.9 before", "Mismatch@0.9 after"],
        rows=out,
        align="lcccc",
    )


def build_metric_robustness_table(metric_json: Path) -> str:
    payload = json.loads(metric_json.read_text(encoding="utf-8"))
    models = payload["models"]
    out = []
    for model in sorted(models):
        s = models[model]["summary"]
        out.append([
            model,
            s["secondary_metric_label"],
            f"{float(s['ece_chrf_q20']):.3f}",
            f"{float(s['ece_secondary_q20']):.3f}",
            _pct(s["mismatch_chrf_tau_0_9"]),
            _pct(s["mismatch_secondary_tau_0_9"]),
        ])
    return _render_table(
        label="tab:metric_robustness",
        caption="Robustness comparison between the main chrF-based target and the strongest available secondary metric target (current run: sentence BLEU fallback).",
        headers=["Model", "Secondary metric", "ECE (chrF-q20)", "ECE (secondary-q20)", "Mismatch@0.9 (chrF)", "Mismatch@0.9 (secondary)"],
        rows=out,
        align="lccccc",
    )


def build_semantic_audit_table(semantic_json: Path) -> str:
    payload = json.loads(semantic_json.read_text(encoding="utf-8"))
    counts = payload.get("counts", {})
    dist = payload.get("sample_distribution", {})
    by_provider = dist.get("providers", {})
    by_bucket = dist.get("difficulty_buckets", {})
    label_counts = payload.get("labels", {}).get("overall_counts", {})
    rows = [
        ["Candidate pool (conf>=0.9 and chrF-q20 mismatch)", str(int(counts.get("n_candidate_rows", 0)))],
        ["Audit sample rows", str(int(counts.get("n_sample_rows", 0)))],
        ["Valid human labels available", str(int(counts.get("n_valid_annotations", 0)))],
        ["Sample provider mix (anthropic/openai/gemini)", f"{int(by_provider.get('anthropic', 0))}/{int(by_provider.get('openai', 0))}/{int(by_provider.get('gemini', 0))}"],
        ["Sample bucket mix (Q1/Q2/Q3/Q4)", f"{int(by_bucket.get('Q1', 0))}/{int(by_bucket.get('Q2', 0))}/{int(by_bucket.get('Q3', 0))}/{int(by_bucket.get('Q4', 0))}"],
        ["Annotated: semantic error", str(int(label_counts.get("semantic_error", 0)))],
        ["Annotated: acceptable paraphrase", str(int(label_counts.get("acceptable_paraphrase", 0)))],
        ["Annotated: metric artifact/unclear", str(int(label_counts.get("metric_artifact_or_unclear", 0)))],
    ]
    return _render_table(
        label="tab:semantic_audit",
        caption="Deterministic semantic-audit scaffold for high-confidence chrF mismatches. Label rows remain zero until annotation CSV files are added under runs/annotations/semantic_audit/.",
        headers=["Audit item", "Count"],
        rows=rows,
        align="lc",
    )


def build_external_comparator_table(comparator_json: Path) -> str:
    payload = json.loads(comparator_json.read_text(encoding="utf-8"))
    models = payload.get("models", {})
    out = []
    for model in sorted(models):
        s = models[model]
        out.append([
            model,
            f"{float(s['corr_self_conf_vs_chrf']):.3f}",
            f"{float(s['corr_proxy_vs_chrf']):.3f}",
            f"{float(s['accepted_error_self_top_frac']):.3f}",
            f"{float(s['accepted_error_proxy_top_frac']):.3f}",
        ])
    return _render_table(
        label="tab:external_comparator",
        caption="External comparator against self-reported confidence using a model-independent surface proxy (higher correlation and lower accepted-error are better).",
        headers=["Model", "Corr(self,chrF)", "Corr(proxy,chrF)", "Accepted err@top20\\% self", "Accepted err@top20\\% proxy"],
        rows=out,
        align="lcccc",
    )


def build_prompt_sensitivity_status_table(status_json: Path) -> str:
    payload = json.loads(status_json.read_text(encoding="utf-8"))
    rows = []
    default_variant = payload.get("default_prompt_variant", "unknown")
    for row in payload.get("status_rows", []):
        variant = row.get("prompt_variant", "")
        tag = "baseline" if variant == default_variant else "variant"
        rows.append([
            variant,
            tag,
            str(row.get("status", "")),
            str(int(row.get("n_models", 0))),
        ])
    return _render_table(
        label="tab:prompt_sensitivity_status",
        caption="Prompt-sensitivity availability in the released artifact bundle. Non-baseline variants require optional live reruns and are not fabricated offline.",
        headers=["Prompt variant", "Role", "Status", "Models with data"],
        rows=rows,
        align="lllc",
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary-csv", default="runs/aggregated/summary_table.csv")
    ap.add_argument("--results-json", default="runs/aggregated/results_by_model.json")
    ap.add_argument("--calibration-json", default="runs/aggregated/calibration/calibration_summary.json")
    ap.add_argument("--metric-robustness-json", default="runs/aggregated/metric_robustness/metric_robustness_summary.json")
    ap.add_argument("--semantic-audit-json", default="runs/aggregated/semantic_audit/semantic_audit_summary.json")
    ap.add_argument("--external-comparator-json", default="runs/aggregated/external_comparator/external_comparator_summary.json")
    ap.add_argument("--prompt-sensitivity-json", default="runs/aggregated/prompt_sensitivity/prompt_sensitivity_status.json")
    ap.add_argument("--outdir", default="tables")
    ap.add_argument("--check", action="store_true", help="Fail if committed tables differ from regenerated content.")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    rendered = {
        "summary.tex": build_summary_table(Path(args.summary_csv)),
        "corr.tex": build_corr_table(Path(args.results_json)),
        "robustness.tex": build_robustness_table(Path(args.results_json)),
        "calibration.tex": build_calibration_table(Path(args.calibration_json)),
        "metric_robustness.tex": build_metric_robustness_table(Path(args.metric_robustness_json)),
        "semantic_audit.tex": build_semantic_audit_table(Path(args.semantic_audit_json)),
        "external_comparator.tex": build_external_comparator_table(Path(args.external_comparator_json)),
        "prompt_sensitivity_status.tex": build_prompt_sensitivity_status_table(Path(args.prompt_sensitivity_json)),
    }

    failed = False
    for name, text in rendered.items():
        target = outdir / name
        if args.check:
            current = target.read_text(encoding="utf-8") if target.exists() else ""
            if current != text:
                failed = True
                diff = "\n".join(unified_diff(current.splitlines(), text.splitlines(), fromfile=str(target), tofile=f"{target} (regenerated)", lineterm=""))
                print(diff)
        else:
            target.write_text(text, encoding="utf-8")
            print(f"Wrote {target}")

    if failed:
        print("ERROR: manuscript-facing LaTeX tables are stale. Run tools/export_latex_tables.py")
        return 1
    if args.check:
        print("OK: manuscript-facing LaTeX tables are in sync.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
