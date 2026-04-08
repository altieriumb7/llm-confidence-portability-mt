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
    expected_tables = ["summary", "corr", "calibration", "metric_robustness", "robustness"]
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

    print("OK: paper/repo consistency checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
