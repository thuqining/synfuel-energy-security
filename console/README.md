# Synthetic Fuel Security Atlas (interactive console)

`index.html` is a stand-alone page: open it in a browser. All data and D3 (v7.9.0, `vendor/d3.min.js`, ISC licence)
are inlined, so it works offline; web fonts fall back to system fonts without a connection.

Map layers
- Sec. 1, per 2.5° land cell (2,740 cells): production cost of each fuel at 2025 central and 2030, 2040, 2050 optimistic costs; demand-weighted cost of the cell's fuel mix.
- Sec. 2, per cell: addressable demand; the nine supply-demand classes of Fig. 2. Per economy: addressable demand, import share of the
  ammonia and of the diesel and jet fuel chains (where trade records give no Fig. 3 value, the fallback share the security
  value uses, marked *), supplier concentration (HHI).
- Sec. 3: lowest-cost domestic fuel of each type (2025 central costs, delivered); cost ratio to the normal median price and position against the
  disruption median (core 30 only, the economies with matched price histories).
- Sec. 4, by cost year (2025 central costs, the 2025mid case; 2030, 2040, 2050 optimistic; 1% of GDP): cost premium, security margin, net premium, carbon price,
  first cost year in which the portfolio is justified, CO2 displaced.
- Sec. 5, by cost year: share of demand made at home at 1% and 3% of GDP, land ceiling, net imports replaced, binding limit.

Figure tabs: Fig. 1 (cost distributions for 2025-2050, demand by route), Fig. 2 (class counts), Fig. 3 for every economy and
fuel (domestic-cost box across 20 weather years; matched prices for ammonia and diesel + jet fuel in the core 30), Fig. 4a and 5 for every economy, Fig. 4b (abatement cost curve) with the selected economy highlighted,
and a sortable table that can be copied as CSV. Gray hatching marks economies without data for a layer.

Rebuild (from the repository root, after the four cases in `work/caselow` exist):

```
cd scripts
python ../work/caselow/run_mod.py ../work/caselow/2025mid 2025 lcof.console_export
python ../work/caselow/run_mod.py ../work/caselow/2030 2030 lcof.console_export
python ../work/caselow/run_mod.py ../work/caselow/2040 2040 lcof.console_export
python ../work/caselow/run_mod.py ../work/caselow/2050 2050 lcof.console_export
cd ..
python console/build_console.py
```

Row orders and groups follow the paper's code (Fig. 3 fig_main_sites._share_order, Fig. 4a fig4_years, Fig. 5
security_budget._figure); for the core 30 they reproduce the published figures. On the 2025mid case `lcof.console_export`
also rebuilds Fig. 3's normal and disruption prices and bill for every economy by the paper's rules (the core 30
reproduce Fig. 3 and its SI version; elsewhere ammonia uses the urea-implied price at the region's own/urea ratio and
diesel + jet the regional import-market price, as the paper does for missing prices), runs Fig. 4a at 2025 central
costs, and writes Fig. 3's domestic-cost box for every economy and fuel (the Fig. 3
code path; reproduces the core-30 boxes of Fig. 3 and its SI diesel and jet version). On 2030-2050 it runs the Fig. 4a calculation (`lcof.fig5a_chain.compute`) for all 139 economies instead of the
core 30; for the core 30 it reproduces `fig5a_chain.csv` exactly. Everything else is read from `source_data/` and the case outputs.
