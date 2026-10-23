# fig_budget_sources.csv — data dictionary

One row per core-30 economy; every number behind the budget figures
(Figs 5–6), with its source. Regenerated together with the core set
(script: scratch `fig6_sources.py`, promoted values from
`land_screen.py` and `security_budget.py`). All shares are fractions
(0–1) unless noted. Accessed dates refer to the API pulls cached in
`data/cost/`.

| column | definition | unit | source | accessed |
|---|---|---|---|---|
| country | economy name (UN-style; "United States of America") | — | — | — |
| agri_share_WDI2023 | agricultural land share of territory | fraction | World Bank WDI `AG.LND.AGRI.ZS` (FAO), year 2023 | 2026-08-28 |
| forest_share_WDI2023 | forest land share of territory | fraction | World Bank WDI `AG.LND.FRST.ZS` (FAO), year 2023 | 2026-08-28 |
| protected_share_WDPA | terrestrial protected-area share | fraction | World Bank WDI `ER.LND.PTLD.ZS` (UNEP-WCMC Protected Planet), latest 2020–25 | 2026-08-28 |
| eligible_share | max(0, (1−p)(1−f−0.9a)) — screening rule of 2026-08-18 | fraction | derived | — |
| dev_share_baseline | 5% of eligible, capped at 2% of territory | fraction | derived (`land_screen.py`) | — |
| capped_at_2pct | True where the 2% review cap binds | bool | derived | — |
| potential_H2_EJ | firm-hydrogen potential on screened land, cell-optimal PV/wind mix | EJ/yr | derived (`supply_demand.firm_h2_potential_gj`) | — |
| demand_H2eq_EJ | addressable demand in hydrogen equivalent | EJ/yr | derived (EDGAR v8.0 2022 demand grid × cascade μ) | — |
| self_sufficiency | potential / demand | ratio | derived | — |
| ceiling_share_of_bill | share of the addressable bill reachable at the land ceiling | fraction | derived (`security_budget.py` max_cov) | — |
| dep_oil_OWID | net oil import dependence max(0, 1−production/consumption) | fraction | OWID energy dataset (EI Statistical Review lineage), latest year | 2026-08-28 |
| dep_gas_OWID | net gas import dependence, same construction | fraction | same | 2026-08-28 |
| owid_year | observation year of the dependence values | year | same | — |
| gas_family_weight | share of the addressable bill in gas-substituting fuels (e-methane, ammonia, methanol) | fraction | derived (demand grid) | — |
| bill_import_share | gas_family_weight·dep_gas + (1−·)·dep_oil, clipped to [0,1] | fraction | derived — THE import tick in Fig 5 | — |

Related: `security_events.csv` now carries `source`/`accessed`/`censored`
columns per event (2026 Hormuz right-censored, ongoing as of
2026-08-29); `land_screen.csv` holds the full-country screening;
`core30.csv` freezes the set.
