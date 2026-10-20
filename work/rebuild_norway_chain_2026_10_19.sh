#!/usr/bin/env bash
# 2026-10-19 (second pass): the rebuilt Fig. 3 audit (Norway a net exporter of the ammonia chain) did not reach
# the chain inputs of Figs 4-5, which read figure3_country_audit.csv from each case. Copy the 2025mid audit into
# data/cost, then rebuild the four main cases, the disruption heatmap, the tier cases and the SI analyses.
# Run from release/.
cd "$(dirname "$0")/.."
cp work/caselow/2025mid/data/figure3_country_audit.csv data/cost/figure3_country_audit.csv
bash work/rebuild_2026_10_19.sh
cd scripts
export PYTHONPATH="$(cygpath -w "$PWD")"
R() { conda run -n synfuel --cwd "$(cygpath -w "$PWD")" python -u "$@"; }
echo "=== disruption heatmap ($(date +%T))"
LCOF_TIER=mid R ../work/caselow/run_mod.py ../work/caselow/2025mid 2025 lcof.fig_main_crisis || echo "FAILED crisis"
cd ..
bash work/rebuild_tiers_2026_10_19.sh
cd scripts
echo "=== SI tables and Source Data ($(date +%T))"
R ../work/caselow/run_mod.py ../work/caselow/2030 2030 lcof.make_fig5_tables || echo "FAILED fig5 tables"
R -m lcof.export_source_data ../source_data || echo "FAILED source data"
R -m lcof.test_paper || echo "FAILED test_paper"
echo "=== all done ($(date +%T))"
