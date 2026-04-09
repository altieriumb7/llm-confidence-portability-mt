#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, cwd=ROOT)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def _check_tex_inputs(manuscript: Path) -> None:
    text = manuscript.read_text(encoding="utf-8")
    expected_tables = [
        "summary",
        "corr",
        "calibration",
        "metric_robustness",
        "semantic_audit",
        "external_comparator",
        "prompt_sensitivity_status",
        "robustness",
    ]
    for t in expected_tables:
        token = f"\\input{{tables/{t}}}"
        if token not in text:
            raise SystemExit(f"Missing manuscript table input: {token}")

    figure_paths = re.findall(r"\\includegraphics\[[^\]]*\]\{([^}]+)\}", text)
    for rel in figure_paths:
        p = ROOT / rel
        if not p.exists():
            raise SystemExit(f"Missing figure referenced by manuscript: {rel}")


def _check_core_values(manuscript: Path, meta: Path) -> None:
    m = json.loads(meta.read_text(encoding="utf-8"))
    text = manuscript.read_text(encoding="utf-8")

    expected_seed = str(m.get("seed"))
    expected_n = int(m.get("n", 0))
    expected_tau = str(m.get("mismatch_tau"))

    if expected_seed and expected_seed not in text:
        raise SystemExit(f"Seed mismatch: seed {expected_seed} from meta.json not found in manuscript")
    if expected_n and "4{,}000" not in text and str(expected_n) not in text:
        raise SystemExit(f"Sample-size mismatch: n={expected_n} from meta.json not found in manuscript")
    if expected_tau and f"{expected_tau}" not in text:
        raise SystemExit(f"Threshold mismatch: tau={expected_tau} from meta.json not found in manuscript")


def _check_examples_file(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "_No data available._" in text:
        raise SystemExit("paper/top_mismatch_examples.md is placeholder/stale")


def _parse_percent_cell(cell: str) -> float:
    return float(cell.replace("\\%", "").strip()) / 100.0


def _extract_tabular_rows(tex_path: Path) -> list[list[str]]:
    rows = []
    for line in tex_path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or "&" not in s or s.startswith("\\"):
            continue
        if s in {"\\toprule", "\\midrule", "\\bottomrule"}:
            continue
        if s.endswith("\\\\"):
            s = s[:-2].strip()
        rows.append([part.strip() for part in s.split("&")])
    return rows


def _assert_close(label: str, a: float, b: float, tol: float = 5e-4) -> None:
    if abs(a - b) > tol:
        raise SystemExit(f"{label} mismatch: {a} vs {b}")


def _check_metric_consistency(root: Path) -> None:
    summary_csv = root / "runs/aggregated/summary_table.csv"
    results_json = root / "runs/aggregated/results_by_model.json"
    calib_json = root / "runs/aggregated/calibration/calibration_summary.json"
    metric_json = root / "runs/aggregated/metric_robustness/metric_robustness_summary.json"
    selective_json = root / "runs/aggregated/selective_analysis/selective_threshold_summary.json"
    summary_tex = root / "tables/summary.tex"
    calib_tex = root / "tables/calibration.tex"
    robust_tex = root / "tables/robustness.tex"
    metric_tex = root / "tables/metric_robustness.tex"

    import csv

    summary_rows = {r["model"]: r for r in csv.DictReader(summary_csv.open(encoding="utf-8"))}
    results = json.loads(results_json.read_text(encoding="utf-8"))
    for model, r in summary_rows.items():
        _assert_close(
            f"{model} summary_csv mismatch@0.9 vs results_json",
            float(r["mismatch_rate_overall_tau_0.9"]),
            float(results[model]["mismatch_rate_overall_tau_0.9"]),
        )

    tex_rows = [r for r in _extract_tabular_rows(summary_tex) if "/" in r[0]]
    for row in tex_rows:
        model = row[0]
        _assert_close(
            f"{model} tables/summary.tex mismatch@0.9 vs summary_csv",
            _parse_percent_cell(row[3]),
            float(summary_rows[model]["mismatch_rate_overall_tau_0.9"]),
        )

    calib = json.loads(calib_json.read_text(encoding="utf-8"))["models"]
    calib_rows = [r for r in _extract_tabular_rows(calib_tex) if "/" in r[0]]
    for row in calib_rows:
        model = row[0]
        _assert_close(
            f"{model} tables/calibration.tex mismatch before vs calibration json",
            _parse_percent_cell(row[3]),
            float(calib[model]["metrics"]["mismatch_at_0_9_before"]),
        )
        _assert_close(
            f"{model} tables/calibration.tex mismatch after vs calibration json",
            _parse_percent_cell(row[4]),
            float(calib[model]["metrics"]["mismatch_at_0_9_after"]),
        )

    robust_rows = [r for r in _extract_tabular_rows(robust_tex) if "/" in r[0]]
    for row in robust_rows:
        model = row[0]
        _assert_close(
            f"{model} tables/robustness.tex within-model mismatch vs results_json",
            _parse_percent_cell(row[1]),
            float(results[model]["mismatch_rate_overall_within_model_q20_tau_0.9"]),
        )

    metric = json.loads(metric_json.read_text(encoding="utf-8"))["models"]
    metric_rows = [r for r in _extract_tabular_rows(metric_tex) if "/" in r[0]]
    for row in metric_rows:
        model = row[0]
        _assert_close(
            f"{model} tables/metric_robustness.tex chrf mismatch vs metric_robustness json",
            _parse_percent_cell(row[4]),
            float(metric[model]["summary"]["mismatch_chrf_tau_0_9"]),
        )

    selective = json.loads(selective_json.read_text(encoding="utf-8"))["models"]
    for model in sorted(selective):
        tau09 = next(
            (x for x in selective[model]["thresholds"] if abs(float(x["threshold"]) - 0.9) < 1e-9),
            None,
        )
        if tau09 is None:
            raise SystemExit(f"{model} missing tau=0.9 row in selective threshold summary")
        _assert_close(
            f"{model} selective mismatch@0.9 vs results_json",
            float(tau09["mismatch_rate"]),
            float(results[model]["mismatch_rate_overall_tau_0.9"]),
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manuscript", default="revised_submission_with_new_results.tex")
    ap.add_argument("--meta", default="runs/aggregated/meta.json")
    ap.add_argument("--examples", default="paper/top_mismatch_examples.md")
    args = ap.parse_args()

    # 1) hard fail if LaTeX tables drift from regenerated artifacts
    _run([
        "python3",
        "tools/export_latex_tables.py",
        "--check",
    ])

    # 2) manuscript wiring checks
    manuscript = ROOT / args.manuscript
    _check_tex_inputs(manuscript)
    _check_core_values(manuscript, ROOT / args.meta)
    _check_examples_file(ROOT / args.examples)
    _check_metric_consistency(ROOT)

    print("OK: paper/repo consistency checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
