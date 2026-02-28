from pathlib import Path
import re

P = Path("src/04_analysis_and_plots.py")

def find_summary_dict_span(lines):
    # Find the first line containing summary.append(
    start_call = None
    for i, ln in enumerate(lines):
        if "summary.append" in ln:
            start_call = i
            break
    if start_call is None:
        raise SystemExit("[ERROR] Could not find 'summary.append' in file.")

    # From start_call forward, find the first '{'
    start_dict = None
    start_col = None
    for i in range(start_call, len(lines)):
        j = lines[i].find("{")
        if j != -1:
            start_dict, start_col = i, j
            break
    if start_dict is None:
        raise SystemExit("[ERROR] Could not find '{' after summary.append(")

    # Now brace-match until the dict closes (depth returns to 0)
    depth = 0
    in_squote = False
    in_dquote = False
    escape = False

    for i in range(start_dict, len(lines)):
        ln = lines[i]
        for k, ch in enumerate(ln):
            # crude string handling: ignore braces inside "..." or '...'
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == "'" and not in_dquote:
                in_squote = not in_squote
                continue
            if ch == '"' and not in_squote:
                in_dquote = not in_dquote
                continue
            if in_squote or in_dquote:
                continue

            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return start_call, start_dict, i  # call-line, dict-start-line, dict-end-line

    raise SystemExit("[ERROR] Could not find matching '}' for summary.append dict.")

def main():
    txt = P.read_text(encoding="utf-8")
    lines = txt.splitlines(True)

    start_call, start_dict, end_dict = find_summary_dict_span(lines)
    block = "".join(lines[start_dict:end_dict+1])

    # Already fixed?
    if '"median_conf"' in block and '"valid_conf_count"' in block and '"total_count"' in block:
        print("ℹ️ summary.append already contains the extra fields. Nothing to do.")
        return

    # Decide indentation (match existing key lines inside dict)
    indent = None
    for ln in lines[start_dict:end_dict+1]:
        if re.search(r'"\w+"\s*:\s*', ln):
            indent = re.match(r"^\s*", ln).group(0)
            break
    if indent is None:
        indent = " " * 16  # fallback

    insert_lines = [
        f'{indent}"median_conf": conf_stats["median_conf"],\n',
        f'{indent}"mismatch_rate_overall_tau_0.9": results[label].get("mismatch_rate_overall_tau_0.9", float("nan")),\n',
        f'{indent}"valid_conf_count": len(valid_conf),\n',
        f'{indent}"total_count": len(d),\n',
    ]

    # Insert before avg_total_latency_s if present, else before closing brace
    new_block_lines = []
    inserted = False
    for ln in lines[start_dict:end_dict+1]:
        if (not inserted) and ("avg_total_latency_s" in ln):
            new_block_lines.extend(insert_lines)
            inserted = True
        new_block_lines.append(ln)

    if not inserted:
        # insert right before last '}' line in dict
        new_block_lines = lines[start_dict:end_dict]
        new_block_lines.extend(insert_lines)
        new_block_lines.append(lines[end_dict])

    # Write back with backup
    bak = P.with_suffix(".py.bak_summaryfix2")
    if not bak.exists():
        bak.write_text(txt, encoding="utf-8")

    lines2 = lines[:start_dict] + new_block_lines + lines[end_dict+1:]
    P.write_text("".join(lines2), encoding="utf-8")
    print(f"✅ Patched summary.append block. Backup: {bak}")

if __name__ == "__main__":
    main()
