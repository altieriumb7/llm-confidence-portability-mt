import json
from pathlib import Path

RAW = Path("runs/raw/gemini__gemini-2.5-flash.jsonl")
OUT_IDS = Path("runs/analysis/missing_conf_gemini_flash_ids.txt")
OUT_JSONL_CLEAN = Path("runs/raw/gemini__gemini-2.5-flash.jsonl.cleaned")

def trunc(s, n=140):
    s = (s or "").replace("\n", " ").strip()
    return s[:n] + ("…" if len(s) > n else "")

def main():
    if not RAW.exists():
        raise SystemExit(f"[ERROR] Missing file: {RAW}")

    rows = []
    missing = []
    with RAW.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            rows.append(r)
            conf = r.get("conf", r.get("confidence"))
            hyp = r.get("hyp") or r.get("translation")
            if conf is None and hyp:
                missing.append(r)

    ids = [str(r.get("id")) for r in missing if r.get("id") is not None]

    OUT_IDS.write_text("\n".join(ids) + ("\n" if ids else ""), encoding="utf-8")

    # also write a cleaned file (keeps all rows that have confidence OR no translation)
    kept = []
    for r in rows:
        conf = r.get("conf", r.get("confidence"))
        hyp = r.get("hyp") or r.get("translation")
        if conf is None and hyp:
            continue
        kept.append(r)

    with OUT_JSONL_CLEAN.open("w", encoding="utf-8") as f:
        for r in kept:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Total rows in file: {len(rows)}")
    print(f"Missing-confidence rows (have hyp but conf=None): {len(missing)}")
    print(f"Wrote IDs: {OUT_IDS}")
    print(f"Wrote cleaned jsonl (without those rows): {OUT_JSONL_CLEAN}")

    if missing:
        print("\nIDs + previews:")
        for r in missing:
            print(f"- id={r.get('id')}  hyp='{trunc(r.get('hyp') or r.get('translation'))}'  warnings='{trunc(r.get('parse_warnings',''))}'")

if __name__ == "__main__":
    main()
