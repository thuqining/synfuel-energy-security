#!/usr/bin/env bash
# 2026-10-19: rebuild the eight remaining cost-year x tier cases and the supplementary analyses that read them
# (README section 6), after the nitrogen-balance and EUR/USD-anchor corrections. Run from release/.
cd "$(dirname "$0")/.."
R() { conda run -n synfuel --cwd "$(cygpath -w "$PWD/scripts")" python -u "$@"; }
for yt in "2025 low" "2025 high" "2030 mid" "2030 high" "2040 mid" "2040 high" "2050 mid" "2050 high"; do
  echo "=== tier case $yt ($(date +%T))"
  R "$(cygpath -w "$PWD/work/caselow/sensitivity/build_case.py")" $yt || echo "FAILED $yt"
done
echo "=== supplementary analyses ($(date +%T))"
for s in tier_table lcos_tiers mf_sens land_sens; do
  R "$(cygpath -w "$PWD/work/caselow/sensitivity/$s.py")" || echo "FAILED $s"
done
R "$(cygpath -w "$PWD/work/caselow/sensitivity/variants.py")" gni || echo "FAILED gni"
export PYTHONPATH="$(cygpath -w "$PWD/scripts")"
LCOF_TIER=mid R "$(cygpath -w "$PWD/work/caselow/run_mod.py")" "$(cygpath -w "$PWD/work/caselow/2025mid")" 2025 lcof.fig5a_sens || echo "FAILED fig5a_sens 2025"
R "$(cygpath -w "$PWD/work/caselow/run_mod.py")" "$(cygpath -w "$PWD/work/caselow/2030")" 2030 lcof.fig5a_sens || echo "FAILED fig5a_sens 2030"
echo "=== done ($(date +%T))"
