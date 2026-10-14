# Energy security and domestic synthetic fuels — code and data

Code and data for

> N. Qi, Z. Fan, Y. Baker, B. Lu, D. Esposito, B. Xu. *Energy security can accelerate domestic synthetic fuel
> adoption and CO2 abatement.* (submitted to Nature Energy, 2026).

The repository reproduces every figure, table and number in the main text and Supplementary Information:
global synthetic fuel production costs on a 2.5° × 2.5° land grid (2,740 cells, 20 weather years), addressable
demand in 139 economies, matched import prices before and during supply disruptions (Fig. 3), the security value
of domestic supply and the CO2 abatement it enables (Fig. 4), and deployment under budget and land limits (Fig. 5).

- Code: MIT License (`LICENSE`)
- Data: CC BY 4.0 (`data/LICENSE`)
- Archived versions: code and data on Zenodo, https://doi.org/10.5281/zenodo.[ID] (to be added on release)

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
work/caselow/<case>/      the four cases quoted in the paper (2025mid: Figs 1-3; 2030, 2040, 2050: Figs 4-5), each with
                          its inputs and every model output
work/caselow/*.py         drivers: run_mod.py (run one module on a case), rerun_fig3.py
source_data/              Source Data: one Excel workbook per main figure (Fig1.xlsx ... Fig5.xlsx)
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
from the GitHub release or Zenodo into `cf_global_final/data/cf_hourly/`.

## 4. Demo: check and redraw the paper's results (about 5 minutes)

From `scripts/`:

```bash
# 1. check every number quoted in the abstract and main text against the four cases (seconds)
python -m lcof.test_paper            # prints ALL PAPER CHECKS PASSED

# 2. redraw Figs 4 and 5 from the stored results (about 2 minutes)
python -m lcof.fig4_years ../work/caselow/demo/fig4 2030=../work/caselow/2030 2040=../work/caselow/2040 2050=../work/caselow/2050
python -m lcof.fig5_years ../work/caselow/demo/fig5 2030=../work/caselow/2030 2040=../work/caselow/2040 2050=../work/caselow/2050
```

Expected output: `fig4.pdf/png` and `fig5.pdf/png` identical to Figs 4 and 5 of the paper, and the console lines
`2030: 0.552 Gt with security, 0.274 on cost only`, ... `2050: 1.876 Gt ..., 1.190 on cost only`.

## 5. Full reproduction

Run all commands from `scripts/`. `run_mod.py <case dir> <cost year> <module>` runs one module on a case
(cost tier from the case name: `2025mid` = central tier; `2030`, `2040`, `2050` = lowest tier).

| Step | Command | Output | Time |
|---|---|---|---|
| 1. Capacity factors (optional) | `cf_global_final/dataprep/*` then `cf_global_final/python/generate_cf_hourly.py` (needs ERA5 via the ARCO mirror) | `cf_global_final/data/cf_hourly/cf_hourly_<year>.nc` | days |
| 2. Cost inputs per case | `python -m lcof.flex_prepare_lowest` | `data/cost/flexlow/costs_<case>.npz` | minutes |
| 3. Linear programs | `python -m lcof.flex_local ../data/cost/flexlow/costs_<case>.npz ../data/cost/flexlow/run_<case> 24` | `run_<case>/out/part_*.csv` | 2-4 h (Gurobi, 24 processes) |
| 4. Build a case | `python -m lcof.case_low <year> ../data/cost/flexlow/run_<case>/out ../work/caselow/<case> build fig4 fig5` | `work/caselow/<case>/data` | 5 min |
| 5. Figs 1-3 (2025mid) | `python ../work/caselow/rerun_fig3.py`; `run_mod.py ... lcof.fig_main_framework`, `lcof.fig_sd_map` | figures and `core30_sites_*.csv` | 5 min |
| 6. Fig. 4b data | `run_mod.py ../work/caselow/<year> <year> lcof.fig5_chain` | `fig5b_chain_*.csv` | 1 min per year |
| 7. Figs 4 and 5 | see Demo | `fig4`, `fig5` | 2 min |
| 8. SI tables | `lcof.make_fig3_tables`, `lcof.risk_all_countries`, `lcof.make_fig5_tables`, `lcof.make_tab_breakeven`, `lcof.make_tab_budget_si`, `lcof.make_tab_paths` | `synthetic_fuel_nature/tab_*.tex` | minutes |
| 9. Check | `python -m lcof.test_paper` | ALL PAPER CHECKS PASSED | seconds |

The central and highest cost tiers (Supplementary Note 2) are built the same way with `LCOF_TIER=mid` or
`LCOF_TIER=high` and the corresponding `costs_<year><tier>.npz`.

## 6. Data sources

Processed inputs and the third-party series the pipeline reads are included, with their sources; they remain subject to the terms of their publishers (for example, Singapore MOPS prices are Platts assessments republished by KNOC Petronet). Raw downloads (ERA5 fields, bulk trade and price files) are not redistributed; they come from public sources cited in
the paper (Supplementary Table 3): ERA5 (Copernicus), EDGAR, UN Energy Statistics, Energy Institute Statistical
Review, UN Comtrade, Eurostat Comext, EIA, World Bank Pink Sheet and World Development Indicators, JODI,
Climate TRACE, WRI Aqueduct, Natural Earth, IEA and IRENA cost reports, Damodaran country risk premiums.

## 7. Citation

Please cite the paper and the Zenodo archive (DOI above).
