#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PASS=0
FAIL=0
WARN=0

die() { echo "[FAIL] $*"; FAIL=$((FAIL+1)); }
ok() { echo "[PASS] $*"; PASS=$((PASS+1)); }
warn() { echo "[WARN] $*"; WARN=$((WARN+1)); }

check_file() {
  local path="$1"
  if [[ -f "$path" ]]; then ok "file exists: $path"; else die "missing file: $path"; fi
}

check_glob_any() {
  local label="$1"; shift
  if compgen -G "$1" > /dev/null; then ok "$label present ($1)"; else die "$label missing ($1)"; fi
}

echo "Reviewer check: deterministic offline artifact readiness"
check_glob_any "Bundled snapshot raw JSONL" "runs/snapshots/20260228_000439/raw/*.jsonl"
check_file "runs/aggregated/dataframe.csv"
check_file "tables/summary.tex"
check_file "tables/corr.tex"
check_file "tables/robustness.tex"
check_file "tables/calibration.tex"
check_file "tables/metric_robustness.tex"
check_file "tables/semantic_audit.tex"
check_file "tables/prompt_sensitivity_status.tex"
check_file "figures/fig1_scatter_difficulty_vs_conf.pdf"
check_file "figures/fig2_reliability_diagram_overlay.pdf"
check_file "figures/fig3_mismatch_by_difficulty_bucket.pdf"
check_file "figures/fig4_efficiency_frontier.pdf"

if python3 tools/consistency_check.py --config configs/models.yaml >/tmp/reviewer_consistency.log 2>&1; then
  ok "consistency checker passes"
else
  die "consistency checker failed (see /tmp/reviewer_consistency.log)"
fi

if command -v latexmk >/dev/null 2>&1; then
  if latexmk -pdf -interaction=nonstopmode -halt-on-error revised_submission_with_new_results.tex >/tmp/reviewer_latex.log 2>&1; then
    ok "latex build succeeded"
  else
    die "latex build failed (see /tmp/reviewer_latex.log)"
  fi
else
  warn "latexmk not installed; TeX compile check skipped"
fi

# citation keys sanity: citations in TeX must exist in references.bib + added_refs.bib
if python3 - <<'PY'
import re
from pathlib import Path

tex = Path('revised_submission_with_new_results.tex').read_text(encoding='utf-8')
keys = []
for m in re.finditer(r'\\cite\w*\{([^}]*)\}', tex):
    keys.extend([k.strip() for k in m.group(1).split(',') if k.strip()])

bib_text = Path('references.bib').read_text(encoding='utf-8') + "\n" + Path('added_refs.bib').read_text(encoding='utf-8')
bib_keys = set(re.findall(r'@\w+\{\s*([^,\s]+)', bib_text))
missing = sorted(set(keys) - bib_keys)
if missing:
    print('MISSING_KEYS=' + ','.join(missing))
    raise SystemExit(1)
print(f'OK_KEYS={len(set(keys))}')
PY
then
  ok "all citation keys resolve in bundled bibliography files"
else
  die "citation key resolution failed"
fi

echo ""
echo "Summary: PASS=$PASS WARN=$WARN FAIL=$FAIL"
if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
