import argparse
import subprocess
import sys
from pathlib import Path

def run(cmd: list[str]) -> None:
    print("\n>>", " ".join(cmd), flush=True)
    p = subprocess.run(cmd)
    if p.returncode != 0:
        raise SystemExit(p.returncode)

def run_parallel(cmds: list[list[str]]) -> None:
    procs = []
    for cmd in cmds:
        print("\n>> (bg)", " ".join(cmd), flush=True)
        procs.append(subprocess.Popen(cmd))
    rc = 0
    for p in procs:
        r = p.wait()
        rc = rc or r
    if rc != 0:
        raise SystemExit(rc)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/models.yaml")
    ap.add_argument("--mode", choices=["sequential", "parallel-providers"], default="sequential",
                    help="parallel-providers runs Step 2 in parallel (openai/anthropic/gemini).")
    ap.add_argument("--max_samples", type=int, default=None,
                    help="Optional: limit samples for Step 2 (API cost control).")
    ap.add_argument("--dry_run", action="store_true",
                    help="No APIs: Step 2 uses hyp=ref and conf=0.5.")
    ap.add_argument("--providers", default=None,
                    help="Comma-separated providers subset for Step 2, e.g. openai,anthropic,gemini")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent
    cfg = str(root / args.config)

    # Step 1
    run([sys.executable, "src/01_make_dataset.py", "--config", cfg])

    # Step 2
    common2 = [sys.executable, "src/02_translate_and_confidence.py",
               "--config", cfg,
               "--input", "data/wmt_sample.jsonl",
               "--outdir", "runs/raw"]
    if args.max_samples is not None:
        common2 += ["--max_samples", str(args.max_samples)]
    if args.dry_run:
        common2 += ["--dry_run"]

    if args.mode == "sequential":
        if args.providers:
            run(common2 + ["--providers", args.providers])
        else:
            run(common2)
    else:
        # parallel per provider (best effort)
        provs = (args.providers.split(",") if args.providers else ["openai", "anthropic", "gemini"])
        cmds = [common2 + ["--providers", p.strip()] for p in provs]
        run_parallel(cmds)

    # Step 3
    run([sys.executable, "src/03_features_and_metrics.py",
         "--config", cfg,
         "--input_dir", "runs/raw",
         "--output", "runs/aggregated/dataframe.csv"])

    # Step 4
    run([sys.executable, "src/04_analysis_and_plots.py",
         "--config", cfg,
         "--input", "runs/aggregated/dataframe.csv",
         "--outdir", "figures",
         "--results", "runs/aggregated/results_by_model.json",
         "--summary", "runs/aggregated/summary_table.csv",
         "--examples", "paper/top_mismatch_examples.md"])

    print("\n✅ Done. Outputs in runs/aggregated/, figures/, paper/")

if __name__ == "__main__":
    main()
