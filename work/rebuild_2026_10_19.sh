#!/usr/bin/env bash
# 2026-10-19 rebuild after the nitrogen-balance (Norway mirror, CAR name) and EUR/USD-anchor corrections:
# the four main cases (README steps 4 and 6), then Figs 1-3 on 2025mid (step 5). Run from release/.
set -e
cd "$(dirname "$0")/../scripts"
export PYTHONPATH="$(cygpath -w "$PWD")"
R() { conda run -n synfuel --cwd "$(cygpath -w "$PWD")" python -u "$@"; }
for c in 2025mid 2030 2040 2050; do
  y=${c%mid}
  if [ "$c" = "2025mid" ]; then export LCOF_TIER=mid; else unset LCOF_TIER; fi
  echo "=== case $c ($(date +%T))"
  R -m lcof.case_low "$y" ../data/cost/flexlow/run_$c/out ../work/caselow/$c build fig4 fig5
  R ../work/caselow/run_mod.py ../work/caselow/$c "$y" lcof.fig5_chain
done
export LCOF_TIER=mid
echo "=== Figs 1-3 on 2025mid ($(date +%T))"
R ../work/caselow/rerun_fig3.py
for m in lcof.fig_main_framework lcof.fig_sd_map lcof.fig_sd_map_zoom lcof.fig_main_demand_struct; do
  R ../work/caselow/run_mod.py ../work/caselow/2025mid 2025 $m
done
echo "=== test_paper ($(date +%T))"
R -m lcof.test_paper || true
echo "=== done ($(date +%T))"
