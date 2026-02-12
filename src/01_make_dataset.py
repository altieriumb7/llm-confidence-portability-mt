import argparse
import json
import random
import subprocess
from pathlib import Path

from utils.common import load_config


def sacrebleu_echo(testset: str, langpair: str, side: str):
    cmd = ["sacrebleu", "-t", testset, "-l", langpair, "--echo", side]
    out = subprocess.check_output(cmd, text=True)
    return [x.strip() for x in out.splitlines() if x.strip()]


def fallback_data():
    src = [
        "The committee approved the proposal after a long debate.",
        "She said the weather would improve by tomorrow morning.",
        "Researchers released a new benchmark for machine translation.",
        "The train arrived late because of heavy snow.",
        "This method improves calibration on difficult inputs.",
    ]
    ref = [
        "Der Ausschuss genehmigte den Vorschlag nach einer langen Debatte.",
        "Sie sagte, das Wetter werde sich bis morgen früh verbessern.",
        "Forscher veröffentlichten einen neuen Benchmark für maschinelle Übersetzung.",
        "Der Zug kam wegen starken Schneefalls verspätet an.",
        "Diese Methode verbessert die Kalibrierung bei schwierigen Eingaben.",
    ]
    return src, ref


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/models.yaml")
    args = ap.parse_args()

    cfg = load_config(args.config)
    g = cfg["global"]

    try:
        src = sacrebleu_echo(g["testset"], g["langpair"], "src")
        ref = sacrebleu_echo(g["testset"], g["langpair"], "ref")
        data_source = "sacrebleu"
    except Exception:
        src, ref = fallback_data()
        data_source = "fallback"

    rows = [{"id": i, "src": s, "ref": r} for i, (s, r) in enumerate(zip(src, ref))]
    n = min(len(rows), g["n"])
    rnd = random.Random(g["seed"])
    rnd.shuffle(rows)
    sampled = rows[:n]

    out_path = Path("data/wmt_sample.jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for i, row in enumerate(sampled):
            row["id"] = i
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    Path("runs/logs").mkdir(parents=True, exist_ok=True)
    with open("runs/logs/dataset_config.json", "w", encoding="utf-8") as f:
        json.dump({**g, "dataset_source": data_source}, f, indent=2)

    print(f"Wrote {n} rows to {out_path} (source={data_source})")


if __name__ == "__main__":
    main()
