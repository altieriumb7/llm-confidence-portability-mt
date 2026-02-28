#!/usr/bin/env python3
import argparse, csv, json
from pathlib import Path
from datetime import datetime, timezone

def read_jsonl(path: Path):
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                # keep going; malformed lines shouldn't kill the export
                continue
    return rows

def safe_slug(s: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in s).strip("_")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw_dir", default="runs/raw")
    ap.add_argument("--out_dir", default="runs/exports")
    ap.add_argument("--dedupe_last", action="store_true", help="keep last occurrence per (id) within each model file")
    args = ap.parse_args()

    raw_dir = Path(args.raw_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted([p for p in raw_dir.glob("*.jsonl") if p.is_file()])
    if not files:
        print(f"[export] No raw files found under {raw_dir}")
        return 0

    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "raw_dir": str(raw_dir),
        "out_dir": str(out_dir),
        "models": {},
    }

    combined_path = out_dir / "translations_all_models.csv"
    combined_fields = [
        "provider","model_id","id","src","ref","hyp","conf",
        "parse_warnings","timestamp_utc",
        "latency_translate_s","latency_conf_s","input_tokens","output_tokens"
    ]
    combined_rows = []

    for fp in files:
        name = fp.name.replace(".jsonl","")
        if "__" not in name:
            # skip unexpected files
            continue
        provider, model_id = name.split("__", 1)

        rows = read_jsonl(fp)
        if args.dedupe_last:
            by_id = {}
            for r in rows:
                if "id" in r:
                    by_id[str(r["id"])] = r
            rows = list(by_id.values())

        # per-model outputs
        model_slug = f"{provider}__{safe_slug(model_id)}"
        per_model_csv = out_dir / f"{model_slug}.csv"
        per_model_inputs = out_dir / f"{model_slug}.inputs_used.jsonl"
        per_model_ids = out_dir / f"{model_slug}.ids.txt"

        fields = ["id","src","ref","hyp","conf","parse_warnings","timestamp_utc"]
        valid_conf = 0
        total = 0

        with per_model_csv.open("w", newline="", encoding="utf-8") as fcsv, \
             per_model_inputs.open("w", encoding="utf-8") as fin, \
             per_model_ids.open("w", encoding="utf-8") as fids:
            w = csv.DictWriter(fcsv, fieldnames=fields)
            w.writeheader()

            for r in rows:
                if "id" not in r:
                    continue
                total += 1
                conf = r.get("conf", r.get("confidence"))
                if conf is not None:
                    valid_conf += 1

                out = {
                    "id": r.get("id"),
                    "src": r.get("src"),
                    "ref": r.get("ref"),
                    "hyp": r.get("hyp") or r.get("translation"),
                    "conf": conf,
                    "parse_warnings": r.get("parse_warnings",""),
                    "timestamp_utc": r.get("timestamp_utc",""),
                }
                w.writerow(out)

                fin.write(json.dumps({"id": r.get("id"), "src": r.get("src"), "ref": r.get("ref")}, ensure_ascii=False) + "\n")
                fids.write(str(r.get("id")) + "\n")

                combined_rows.append({
                    "provider": provider,
                    "model_id": model_id,
                    "id": r.get("id"),
                    "src": r.get("src"),
                    "ref": r.get("ref"),
                    "hyp": r.get("hyp") or r.get("translation"),
                    "conf": conf,
                    "parse_warnings": r.get("parse_warnings",""),
                    "timestamp_utc": r.get("timestamp_utc",""),
                    "latency_translate_s": r.get("latency_translate_s"),
                    "latency_conf_s": r.get("latency_conf_s"),
                    "input_tokens": r.get("input_tokens"),
                    "output_tokens": r.get("output_tokens"),
                })

        manifest["models"][f"{provider}/{model_id}"] = {
            "raw_file": str(fp),
            "export_csv": str(per_model_csv),
            "inputs_used_jsonl": str(per_model_inputs),
            "ids_txt": str(per_model_ids),
            "rows_total": total,
            "valid_conf": valid_conf,
        }
        print(f"[export] {provider}/{model_id}: rows={total} valid_conf={valid_conf} -> {per_model_csv.name}")

    with combined_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=combined_fields)
        w.writeheader()
        for r in combined_rows:
            w.writerow(r)

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[export] wrote combined: {combined_path}")
    print(f"[export] wrote manifest: {out_dir/'manifest.json'}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
