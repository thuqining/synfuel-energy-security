# Energy security and domestic synthetic fuels — code and data

Code and data for

> N. Qi, Z. Fan, Y. Baker, B. Lu, D. Esposito, B. Xu. *Energy security can accelerate domestic synthetic fuel
> adoption and CO2 abatement.* (submitted to Nature Energy, 2026).

The repository reproduces every figure, table and number in the main text and Supplementary Information:
global synthetic fuel production costs on a 2.5° × 2.5° land grid (2,740 cells, 20 weather years), addressable
demand in 139 economies, matched import prices before and during supply disruptions (Fig. 3), the security value
of domestic supply per tonne of CO2 displaced (Fig. 4), the CO2 abatement it enables (Fig. 5), and deployment under
budget and land limits (Fig. 6).

- Code: MIT License (`LICENSE`)
- Data: CC BY 4.0 (`data/LICENSE`)
- Archived versions: code and data on Zenodo, https://doi.org/10.5281/zenodo.23357310 (all versions; v1.0.0:
  https://doi.org/10.5281/zenodo.23357311)
- v1.0.1 (2026-10-19): Fig. 2 adds regional maps of Europe, Japan and the Korean Peninsula, and South and Southeast
  Asia (`lcof.fig_sd_map_zoom`); "value of lost fuel" wording in two SI figures and the break-even table. No result
  changes (`lcof.test_paper` passes).
- v1.1.0 (2026-10-22): results of the revised manuscript. The value of lost fuel is GDP per unit of primary energy
  including traditional biomass; GDP is projected to each cost year for the national budgets (IMF World Economic
  Outlook to 2030, SSP2 after; `lcof.gdp_projection`, inputs in `data/gdp_projections/`); the Fig. 3 tail test is the
  90th percentile; import prices outside the 30 core economies use regional markets. Six main figures: Fig. 4 security
  value per tonne, Fig. 5 abatement cost curves, Fig. 6 budget and land at 2030 costs; all figures are redrawn by
  `lcof.make_paper_figs` and the 139-economy SI figures and tables by `lcof.fig_rows139` and `lcof.make_si139_tables`.
  `lcof.test_paper` checks the new numbers (ALL PAPER CHECKS PASSED); `lcof.audit_vintage` and `lcof.audit139` pass. Archived as
  https://doi.org/10.5281/zenodo.23583358.

---

## 1. Repository layout

The layout mirrors the working project, so every script runs without editing paths
(`scripts/lcof/inputs.py` locates all data relative to the repository root).

```
scripts/lcof/             Python package: optimization, demand, prices, security value, allocation, figures, tables
scripts/plot_style.py     shared plotting style
cf_global_final/          ERA5 -> hourly capacity factors (dataprep/, python/, docs/); grid, cell metadata and annual
                          capacity factors in data/; data/cf_hourly/ (3.0 GB) is downloaded separately
data/cost/                processed model inputs (cost assumptions and tiers, country data, demand grid, prices, CO2, land)
data/cost/flexlow/        linear-program results per cell and weather year for every cost year and tier
data/demand/, data/prices/, data/co2/, data/grid/, data/jodi/
                          other inputs read by the pipeline (Energy Institute, UN Energy Statistics, UN Comtrade nitrogen
                          trade, price series, Climate TRACE, Natural Earth, JODI)
work/caselow/<case>/      the four cases quoted in the paper (2025mid: Figs 1-3; 2030, 2040, 2050: Figs 4-6), each with
                          its inputs and every model output
work/caselow/*.py         drivers: run_mod.py (run one module on a case), rerun_fig3.py
source_data/              Source Data: one Excel workbook per main figure (Fig1.xlsx ... Fig6.xlsx)
console/                  interactive results console (index.html, opens offline): world map of every cell and economy,
                          Figs 3-6 for all economies; rebuilt by console/build_console.py (see console/README.md)
DATA.md                   every data file: content, size, the module that writes it and the modules that read it
```

`DATA.md` lists every data file, its content, size, the module that writes it and the modules that read it.
`python -m lcof.export_source_data ../source_data` rebuilds the Source Data workbooks from the four cases.

## 2. System requirements

- Tested on Windows 11 (Python 3.11.15) and Linux (Python 3.11, cluster runs of the linear programs).
- Python packages and versions: `environment.yml` (numpy 2.4, pandas 3.0, scipy 1.17, xarray 2026.4,
  geopandas 1.1, matplotlib 3.10, linopy 0.7, highspy 1.14, atlite 0.6.1, openpyxl 3.1).
- Solver: the production-cost linear programs were solved with **Gurobi 13.0** (academic licence; barrier, no
  crossover). The free solver **HiGHS** (installed with `highspy`) gives the same levelized costs to four decimals
  on test cells, at about 60 s instead of about 5 s per linear program. Set `LCOF_SOLVER=highs` before step 3 of
  section 5 (the code also falls back to HiGHS automatically when no Gurobi licence is found). All other steps need no commercial software.
- Hardware: any recent laptop for the figures and tables (8 GB RAM); the full set of linear programs
  (2,740 cells x 20 weather years per cost case) is best run on a workstation or cluster.

## 3. Installation (about 10 minutes)

```bash
git clone https://github.com/[user]/[repository].git
cd [repository]
conda env create -f environment.yml
conda activate synfuel
```

Hourly capacity factors (3.0 GB, 20 netCDF files) are only needed to re-run the linear programs. Download them
from the assets of the GitHub release (https://github.com/thuqining/synfuel-energy-security/releases/tag/v1.0.0) into `cf_global_final/data/cf_hourly/`.

## 4. Demo: check and redraw the paper's results (about 5 minutes)

From `scripts/`:

```bash
# 1. check every number quoted in the abstract and main text against the four cases (seconds)
python -m lcof.test_paper            # prints ALL PAPER CHECKS PASSED

# 2. redraw Figs 3-6 from the stored results (a few minutes)
python -m lcof.make_paper_figs ../work/caselow/demo fig3_core fig4_core fig5_core fig6_core
```

Expected output: `fig3_core.pdf` ... `fig6_core.pdf` identical to Figs 3-6 of the paper, and for Fig. 5 the console
lines `b 2030: 0.853 Gt with security, 0.275 on cost only`, ... `b 2050: 1.864 Gt with security, 1.190 on cost only`.
`python -m lcof.make_paper_figs <out dir>` with no names redraws every main and SI figure.

## 5. Full reproduction

Run all commands from `scripts/`. `run_mod.py <case dir> <cost year> <module>` runs one module on a case
(cost tier from the case name: `2025mid` = central tier; `2030`, `2040`, `2050` = lowest tier).

| Step | Command | Output | Time |
|---|---|---|---|
| 1. Capacity factors (optional) | `cf_global_final/dataprep/*` then `cf_global_final/python/generate_cf_hourly.py` (needs ERA5 via the ARCO mirror) | `cf_global_final/data/cf_hourly/cf_hourly_<year>.nc` | days |
| 2. Cost inputs per case | `python -m lcof.flex_prepare_lowest` | `data/cost/flexlow/costs_<case>.npz` | minutes |
| 3. Linear programs | `python -m lcof.flex_local ../data/cost/flexlow/costs_<case>.npz ../data/cost/flexlow/run_<case> 24` | `run_<case>/out/part_*.csv` | 2-4 h (Gurobi, 24 processes) |
| 4. Build a case | `python -m lcof.case_low <year> ../data/cost/flexlow/run_<case>/out ../work/caselow/<case> build fig4 fig5` | `work/caselow/<case>/data` | 5 min |
| 5. Figs 1-3 (2025mid) | `python ../work/caselow/rerun_fig3.py`; `run_mod.py ... lcof.fig_main_framework`, `lcof.fig_sd_map`, `lcof.fig_sd_map_zoom` (Fig. 2 with regional maps) | figures and `core30_sites_*.csv` | 5 min |
| 6. Fig. 5 data (abatement cost curves) | `run_mod.py ../work/caselow/<year> <year> lcof.fig5_chain` | `fig5b_chain_*.csv` | 1 min per year |
| 7. Console data (Figs 3-6 for 139 economies) | `python ../console/build_console.py` | `console/index.html`, `console/build/*.csv` | minutes |
| 8. Figures | `python -m lcof.make_paper_figs <out dir>` | every main and SI figure | 10 min |
| 9. SI tables | `lcof.make_fig3_tables`, `lcof.risk_all_countries`, `lcof.make_fig5_tables`, `lcof.make_tab_breakeven`, `lcof.make_tab_budget_si`, `lcof.make_tab_paths`, `lcof.make_si139_tables` | `tab_*.tex` | minutes |
| 10. Check | `python -m lcof.test_paper`; `python -m lcof.audit139` | ALL PAPER CHECKS PASSED; FAILURES: 0 | seconds |

The central and highest cost tiers (Supplementary Note 2) are built the same way with `LCOF_TIER=mid` or
`LCOF_TIER=high` and the corresponding `costs_<year><tier>.npz`.

## 6. Supplementary analyses

Each Supplementary table or paragraph that needs more than the four main cases has a driver in
`work/caselow/sensitivity/` (run from any directory) or a module in `scripts/lcof/` (run from `scripts/`).

| Supplementary item | Command | Needs |
|---|---|---|
| Cost years x tiers (Supplementary Table `tab:paths`, Supplementary Fig. `tiers`) | `python work/caselow/sensitivity/build_case.py <year> <low/mid/high>` for the 12 cases, then `python work/caselow/sensitivity/tier_table.py` | LP results in `data/cost/flexlow` |
| Levelized cost by tier (`tab:lcostiers`) | `python work/caselow/sensitivity/lcos_tiers.py` | the 12 cases |
| Oil-to-gas loss ratio m_f = 1.0 (`tab:mfsens`) | `python work/caselow/sensitivity/mf_sens.py` | cases 2030, 2040, 2050 |
| Land limit (`tab:landsens`) | `python work/caselow/sensitivity/land_sens.py` | cases 2030, 2040, 2050 |
| Fig. 4a sensitivity (`tab:fig5sens`) | `python ../work/caselow/run_mod.py ../work/caselow/2030 2030 lcof.fig5a_sens` (and `2025mid 2025`) | cases 2030, 2025mid |
| Ireland at GNI* (Supplementary Note 5) | `python work/caselow/sensitivity/variants.py gni` | cases 2025mid, 2030 |
| Coastal cells at offshore wind cost (Supplementary Note 3) | `python work/caselow/sensitivity/variants.py offshore` | case 2025mid, `work/sens_results` |
| Equipment cost drivers, synthesis flexibility, battery (`tab:drivers`, `tab:minload`, `tab:battery`) | `python -m lcof.sens_summary` | `work/sens_results` (from `work/sens_pkg/sens_flex.py`) |
| Recovery buffer (`tab:washout`) | `python ../work/caselow/rerun_fig3.py` | case 2025mid |
| Source Data workbooks | `python -m lcof.export_source_data ../source_data` | the four main cases |

The equipment and flexibility runs (`work/sens_pkg`) re-solve every land cell at its median weather year with
one input changed: `python work/sens_pkg/sens_flex.py --groups all` (about 60,000 linear programs) writes
`work/sens_pkg/out/<variant>/part_*.csv`; copy these folders to `work/sens_results/out/`, where
`lcof.sens_summary` and `variants.py offshore` read them (the results of the paper are already there).

## 7. Data sources

Processed inputs and the third-party series the pipeline reads are included, with their sources; they remain subject to the terms of their publishers (for example, Singapore MOPS prices are Platts assessments republished by KNOC Petronet). Raw downloads (ERA5 fields, bulk trade and price files) are not redistributed; they come from public sources cited in
the paper (Supplementary Table 3): ERA5 (Copernicus), EDGAR, UN Energy Statistics, Energy Institute Statistical
Review, UN Comtrade, Eurostat Comext, EIA, World Bank Pink Sheet and World Development Indicators, JODI,
Climate TRACE, WRI Aqueduct, Natural Earth, IEA and IRENA cost reports, Damodaran country risk premiums, IMF World
Economic Outlook (GDP growth to 2030) and the SSP v3.2 database (SSP2 GDP, OECD ENV-Growth 2025; the processed
series is in `data/gdp_projections/ssp2_gdp_v3.2.csv`, the raw workbook is not redistributed).

## 8. Citation

Please cite the paper and the Zenodo archive:

Qi, N., Fan, Z., Baker, Y., Lu, B., Esposito, D. & Xu, B. Code and data for "Energy security can accelerate
domestic synthetic fuel adoption and CO2 abatement". Zenodo https://doi.org/10.5281/zenodo.23357310 (2026).
