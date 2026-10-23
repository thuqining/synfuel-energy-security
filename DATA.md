# Data

All data are licensed under CC BY 4.0 (`data/LICENSE`), except third-party files, which remain subject to the terms of their publishers (sources in the table and in Supplementary Table 3 of the paper). Hourly capacity factors (`cf_global_final/data/cf_hourly/`, 3.0 GB) are attached to the GitHub release and archived on Zenodo.

`<case>` is one of `2025mid` (2025 central costs; Figs 1-3), `2030`, `2040`, `2050` (lowest-tier costs; Figs 4-5). Each case folder holds the processed inputs (a copy of `data/cost`) and every model output. Units: costs in 2025 US$; energy in GJ or MMBtu (lower heating value), as stated in the column names.

| Folder | File (pattern) | Files | Size | Content | Written by | Read by |
|---|---|---|---|---|---|---|
| `cf_global_final/data/cf_yearly` | `cf_global_<year>.nc` | 20 | 9.7 MB | output of `generate_cf_global`: FINAL global capacity-factor generator (Python/atlite) | generate_cf_global | aggregate_global, cell_land_area, corridor_maps, fig5_chain |
| `cf_global_final/data/cost` | `cf_global_<year>.csv` | 20 | 8.5 MB | cell metadata and annual capacity factors (technology assignment, IEC class) | generate_cf_global | aggregate_global, cell_land_area, corridor_maps, fig5_chain |
| `cf_global_final/data/grid` | `grid_cells.csv` | 1 | 0.3 MB | output of `01_define_grid`: Build the 2.5-degree global analysis grid for the synthetic-fuels TEA. | 01_define_grid | plot_style |
| `cf_global_final/data/grid` | `grid_cells.gpkg` | 1 | 1.4 MB | 2.5-degree grid cells (land and coastal) | 01_define_grid | plot_style |
| `cf_global_final/data/grid` | `tech_assignment_ref.csv` | 1 | 0.2 MB | output of `make_class_ref`: CLIMATOLOGICAL technology assignment per cell. | make_class_ref | generate_cf_global, generate_cf_hourly, inputs |
| `cf_global_final/data/grid/naturalearth` | `ne_10m_admin_0_countries.README.html` | 1 | 39 kB |  |  |  |
| `cf_global_final/data/grid/naturalearth` | `ne_10m_admin_0_countries.VERSION.txt` | 1 | 0 kB |  |  |  |
| `cf_global_final/data/grid/naturalearth` | `ne_10m_admin_0_countries.cpg` | 1 | 0 kB | input read by `01_define_grid` |  | 01_define_grid, capex_2030low, capex_tiers, cell_land_area |
| `cf_global_final/data/grid/naturalearth` | `ne_10m_admin_0_countries.dbf` | 1 | 0.9 MB | input read by `01_define_grid` |  | 01_define_grid, capex_2030low, capex_tiers, cell_land_area |
| `cf_global_final/data/grid/naturalearth` | `ne_10m_admin_0_countries.prj` | 1 | 0 kB | input read by `01_define_grid` |  | 01_define_grid, capex_2030low, capex_tiers, cell_land_area |
| `cf_global_final/data/grid/naturalearth` | `ne_10m_admin_0_countries.shp` | 1 | 8.8 MB | Natural Earth admin-0 country boundaries, 1:10m, v5.1.1 (public domain) |  | 01_define_grid, capex_2030low, capex_tiers, cell_land_area |
| `cf_global_final/data/grid/naturalearth` | `ne_10m_admin_0_countries.shx` | 1 | 2 kB | input read by `01_define_grid` |  | 01_define_grid, capex_2030low, capex_tiers, cell_land_area |
| `cf_global_final/data/grid/naturalearth` | `ne_110m_admin_0_countries.zip` | 1 | 4.9 MB |  |  |  |
| `data/co2/climate_trace` | `co2_sources_climatetrace_<year>.csv` | 1 | 2.0 MB | Climate TRACE facility-level CO2 point sources | co2_sources | fig_si_feedstocks |
| `data/cost` | `ammonia_consumption.csv` | 1 | 15 kB | national nitrogen balance in ammonia equivalent (USGS, UN Comtrade) | ammonia_consumption, nitrogen_consumption | audit_figure3, demand_grid, fetch_nitrogen_trade, fig5a_chain |
| `data/cost` | `ammonia_consumption_<year>basis.csv` | 1 | 9 kB | output of `ammonia_consumption`: national apparent consumption of ammonia (2026-10-07). | ammonia_consumption, nitrogen_consumption | audit_figure3, demand_grid, fetch_nitrogen_trade, fig5a_chain |
| `data/cost` | `ammonia_consumption_nh3only.csv` | 1 | 11 kB | input read by `nitrogen_consumption` |  | nitrogen_consumption |
| `data/cost` | `atb_capex_index.csv` | 1 | 1 kB |  |  |  |
| `data/cost` | `atb_raw_subset.csv` | 1 | 1 kB |  |  |  |
| `data/cost` | `battery_check_<year>.csv` | 1 | 8 kB |  |  |  |
| `data/cost` | `bench_cf_Berlin.csv` | 1 | 0.3 MB |  |  |  |
| `data/cost` | `bench_cf_Chile-best.csv` | 1 | 0.2 MB |  |  |  |
| `data/cost` | `bench_cf_Riyadh.csv` | 1 | 0.3 MB |  |  |  |
| `data/cost` | `bootstrap_demo.csv` | 1 | 1 kB |  |  |  |
| `data/cost` | `breakeven_carbon_<year>.csv` | 1 | 0.1 MB | input read by `make_paper_tables` |  | make_paper_tables, map_base, map_layers |
| `data/cost` | `candidate_cities_eval.csv` | 1 | 5 kB |  |  |  |
| `data/cost` | `capex_by_country.csv` | 1 | 37 kB | country capital costs and synthesis location factor used in the case | capex_2030low, capex_tiers, case_low | flex_prepare_lowest, inputs |
| `data/cost` | `capex_by_country_<year>high.csv` | 4 | 0.2 MB | country capital costs, highest tier | capex_2030low, capex_tiers, case_low | flex_prepare_lowest, inputs |
| `data/cost` | `capex_by_country_<year>low.csv` | 4 | 0.2 MB | country solar, wind and electrolyzer capital costs, lowest tier | capex_2030low, capex_tiers, case_low | flex_prepare_lowest, inputs |
| `data/cost` | `capex_by_country_<year>low_log.csv` | 1 | 21 kB | output of `capex_2030low`: 2030 lowest-cost capex layer (2026-10-07). | capex_2030low, capex_tiers, case_low | flex_prepare_lowest, inputs |
| `data/cost` | `capex_by_country_<year>mid.csv` | 4 | 0.2 MB | country capital costs, central tier | capex_2030low, capex_tiers, case_low | flex_prepare_lowest, inputs |
| `data/cost` | `capex_by_country_ghr<year>.csv` | 1 | 37 kB | input read by `capex_2030low` |  | capex_2030low, capex_tiers |
| `data/cost` | `capex_by_country_ghr<year>_high.csv` | 1 | 25 kB | input read by `capex_2030low` |  | capex_2030low, capex_tiers |
| `data/cost` | `capex_by_country_ghr<year>_low.csv` | 1 | 25 kB | input read by `capex_2030low` |  | capex_2030low, capex_tiers |
| `data/cost` | `capex_by_country_ghr<year>_mainline.csv` | 1 | 31 kB | input read by `capex_2030low` |  | capex_2030low, capex_tiers |
| `data/cost` | `capex_by_country_iea<year>.csv` | 1 | 31 kB |  |  |  |
| `data/cost` | `cell_land_area.csv` | 1 | 0.1 MB | national land area in each 2.5-degree cell |  | cell_land_area, supply_demand |
| `data/cost` | `cell_security_year.csv` | 1 | 10 kB | output of `global_trajectory`: the globally aggregated result plus the demand-concentration numbers. | global_trajectory |  |
| `data/cost` | `cf_global_<year>.csv` | 1 | 0.6 MB | cell metadata and annual capacity factors (technology assignment, IEC class) | generate_cf_global | aggregate_global, cell_land_area, corridor_maps, fig5_chain |
| `data/cost` | `cf_global_<year>_matlab.csv` | 1 | 0.2 MB | output of `generate_cf_global`: FINAL global capacity-factor generator (Python/atlite) | generate_cf_global | aggregate_global, cell_land_area, corridor_maps, fig5_chain |
| `data/cost` | `chain_q.csv` | 1 | 0.1 MB | expected disruption share by economy and fuel chain | fig5a_chain | corridor_maps, make_fig5_tables |
| `data/cost` | `co2_cost_by_cell.csv` | 1 | 0.3 MB | cheapest CO2 source of each land cell and its delivered price (US$/t) |  | case_low, export_source_data, fig5a_chain, fig_main_framework |
| `data/cost` | `co2_cost_by_cell_neutral.csv` | 1 | 0.2 MB | input read by `case_low` |  | case_low, fig_si_feedstocks |
| `data/cost` | `co2_cost_by_cell_neutral_longterm.csv` | 1 | 0.2 MB | input read by `case_low` |  | case_low |
| `data/cost` | `compare_integrated.csv` | 1 | 0 kB |  |  |  |
| `data/cost` | `core30.csv` | 1 | 1 kB | output of `coreset`: ONE definition of the 30 core economies shown in every main-text figure and table (the global aggregates use a | coreset, fig_main_cities, fig_main_demand_struct | audit_figure3, export_source_data, make_fig3_tables, risk_all_countries |
| `data/cost` | `core30_cities.csv` | 1 | 5 kB | output of `fig_main_cities`: MAIN-TEXT city figure: the 30 core cities (one demand centre per core-30 economy) with cost, weather risk, mar | fig_main_cities |  |
| `data/cost` | `core30_demand_struct.csv` | 1 | 2 kB | output of `fig_main_demand_struct`: the demand side, economy by economy: what each core-30 addressable fossil-fuel bill is actually made of, fuel  | fig_main_demand_struct |  |
| `data/cost` | `core30_sites.csv` | 1 | 45 kB | copy of core30_sites_ammonia.csv | fig_main_sites | audit_figure3, export_source_data, make_fig3_tables, security_budget |
| `data/cost` | `core30_sites_ammonia.csv` | 1 | 45 kB | Fig. 3: green ammonia cost, normal and disruption price quantiles, import risk index, bill |  | export_source_data, si_fig3_tables |
| `data/cost` | `core30_sites_ammonia_washout12m.csv` | 1 | 45 kB |  |  |  |
| `data/cost` | `core30_sites_ammonia_washout3m.csv` | 1 | 42 kB |  |  |  |
| `data/cost` | `core30_sites_ft.csv` | 1 | 65 kB | Supplementary Fig. (diesel and jet version of Fig. 3) |  |  |
| `data/cost` | `core30_sites_ft_washout12m.csv` | 1 | 61 kB |  |  |  |
| `data/cost` | `core30_sites_ft_washout3m.csv` | 1 | 67 kB |  |  |  |
| `data/cost` | `corridors_discussion.csv` | 1 | 1 kB | input read by `fig_si_corridors` |  | fig_si_corridors, map_layers |
| `data/cost` | `country_fossil_exposure.csv` | 1 | 10 kB | output of `regional_prices`: turn three global markers into a per-country monthly fossil price, and measure how differently each country is | regional_prices |  |
| `data/cost` | `crisis_by_country_event.csv` | 1 | 21 kB |  |  |  |
| `data/cost` | `deck_summary.json` | 1 | 22 kB |  |  |  |
| `data/cost` | `demand_by_fuel.csv` | 1 | 22 kB | output of `demand`: the measured demand layer for the security ledger. | demand | demand_grid, fig_main_framework, security |
| `data/cost` | `demand_by_fuel_owid.csv` | 1 | 18 kB |  |  |  |
| `data/cost` | `demand_fuel_grid.csv` | 1 | 0.5 MB | addressable demand by land cell and fuel (GJ/yr) | demand_grid | audit_figure3, fig5_chain, fig5a_chain, fig_main_demand_struct |
| `data/cost` | `dynamic_ops_global.csv` | 1 | 0.3 MB |  |  |  |
| `data/cost` | `dynamic_ops_summary.csv` | 1 | 1 kB |  |  |  |
| `data/cost` | `ed_crisis_by_country_regime.csv` | 1 | 0.3 MB | output of `fig_main_crisis`: Extended Data: each dated disruption, economy by economy, on Figure 3's comparator and rules. | fig_main_crisis | make_fig3_tables |
| `data/cost` | `ed_crisis_pooled_by_fuel.csv` | 1 | 1 kB | output of `fig_main_crisis`: Extended Data: each dated disruption, economy by economy, on Figure 3's comparator and rules. | fig_main_crisis |  |
| `data/cost` | `fig3_risk_all_countries.csv` | 1 | 52 kB | import risk index for every modeled country (Supplementary Table) |  | risk_all_countries |
| `data/cost` | `fig5a_chain.csv` | 1 | 17 kB | Fig. 4a: portfolio mix, CO2 displaced, cost premium, security margin, net premium, carbon price | fig5a_chain, fig5a_sens, make_fig5_tables | case_low, corridor_maps, export_source_data, fig4_years |
| `data/cost` | `fig5a_chain_sensitivity.csv` | 1 | 0.2 MB | output of `fig5a_sens`: sensitivity of the chain-basis Figure 5a (for the SI). | fig5a_sens, make_fig5_tables |  |
| `data/cost` | `fig5b_chain_pairs.csv` | 1 | 0.1 MB | Fig. 4b: country-fuel blocks of the abatement cost curve | fig5_chain | export_source_data, map_layers |
| `data/cost` | `fig5b_chain_trajectory.csv` | 1 | 3 kB | Fig. 4b: CO2 displaced with security value and on cost alone (Gt/yr) | fig5_chain | export_source_data, test_paper |
| `data/cost` | `fig_budget_sources.csv` | 1 | 3 kB |  |  |  |
| `data/cost` | `fig_budget_sources_README.md` | 1 | 3 kB |  |  |  |
| `data/cost` | `figure3_country_audit.csv` | 1 | 94 kB | Fig. 3 inputs per economy: import exposure, supplier concentration, price basis |  | audit_figure3, export_source_data, fig5a_chain, fig_main_crisis |
| `data/cost` | `figure3_download_gap_manifest.csv` | 1 | 8 kB |  |  |  |
| `data/cost` | `figure3_event_audit.csv` | 1 | 37 kB | input read by `audit_figure3` |  | audit_figure3 |
| `data/cost` | `figure3_event_coverage_summary.csv` | 1 | 1 kB |  |  |  |
| `data/cost` | `figure3_member_event_audit.csv` | 1 | 70 kB | input read by `audit_figure3` |  | audit_figure3, fig_main_crisis |
| `data/cost` | `figure3_washout_sensitivity.csv` | 1 | 36 kB | input read by `audit_figure3` |  | audit_figure3 |
| `data/cost` | `final30_portfolio.csv` | 1 | 6 kB |  |  |  |
| `data/cost` | `firm_tornado_summary.csv` | 1 | 1 kB |  |  |  |
| `data/cost` | `flex20_fig2_cells.csv` | 1 | 0.4 MB |  |  |  |
| `data/cost` | `flex20_summary.csv` | 1 | 1 kB |  |  |  |
| `data/cost` | `flex60_fig2_cells.csv` | 1 | 0.4 MB |  |  |  |
| `data/cost` | `flex60_summary.csv` | 1 | 1 kB |  |  |  |
| `data/cost` | `flex70_fig2_cells.csv` | 1 | 0.4 MB |  |  |  |
| `data/cost` | `flex70_summary.csv` | 1 | 1 kB |  |  |  |
| `data/cost` | `flex_grid_summary.csv` | 1 | 1 kB |  |  |  |
| `data/cost` | `flex_sensitivity_summary.csv` | 1 | 1 kB |  |  |  |
| `data/cost` | `flex_tornado_summary.csv` | 1 | 1 kB |  |  |  |
| `data/cost` | `ft9425_fig2_cells.csv` | 1 | 0.4 MB |  |  |  |
| `data/cost` | `ft9425_summary.csv` | 1 | 1 kB |  |  |  |
| `data/cost` | `fuel_reco_stats.csv` | 1 | 1 kB | output of `demand_grid`: gridded fuel-demand proxy and the plant recommendation. | demand_grid | fig_main_cost, make_paper_tables |
| `data/cost` | `fuel_recommendation.csv` | 1 | 0.3 MB | output of `demand_grid`: gridded fuel-demand proxy and the plant recommendation. | demand_grid | fig_main_cost |
| `data/cost` | `gap_country_fuel.csv` | 1 | 87 kB | output of `gap`: the single quantity behind the policy, crisis and vulnerability readings: | gap |  |
| `data/cost` | `global_trajectory.csv` | 1 | 3 kB | global CO2 displaced by cost year | fig5_chain, global_trajectory | export_source_data, fig4_years, fig_main_demand_struct, fig_main_framework |
| `data/cost` | `global_trajectory_countries.csv` | 1 | 0.2 MB | addressable demand and CO2 by economy and fuel | global_trajectory | export_source_data, fig_main_demand_struct, fig_main_framework, map_base |
| `data/cost` | `island_strategy.csv` | 1 | 8 kB |  |  |  |
| `data/cost` | `jodi_gas_dep_core30.csv` | 1 | 2 kB |  |  |  |
| `data/cost` | `land_screen.csv` | 1 | 9 kB | output of `land_screen`: country-level screened land availability for the renewable build, replacing the uniform 2%-of-land cap. | land_screen | supply_demand |
| `data/cost` | `lcof_countries_<year>.csv` | 1 | 40 kB | input read by `gap` |  | gap, policy |
| `data/cost` | `lcof_countries_fuels_<year>.csv` | 1 | 0.3 MB | input read by `gap` |  | gap, policy |
| `data/cost` | `lcof_fuels_<year>.csv` | 1 | 41 kB |  |  |  |
| `data/cost` | `lcof_global_stats.csv` | 1 | 7.7 MB | levelized cost of each fuel per land cell (mean and firm, US$/GJ) | aggregate_global |  |
| `data/cost` | `lcof_global_stats_reg.csv` | 1 | 4.3 MB |  |  |  |
| `data/cost` | `lcof_sites_<year>.csv` | 1 | 5 kB |  |  |  |
| `data/cost` | `lcoh_global_<year>.csv` | 20 | 9.1 MB | output of `case_low`: the lowest-cost main case (2026-10-07) for one cost year: collect the 20-weather-year flexible-synthesis LP, b | case_low | aggregate_global, audit_vintage, export_source_data, fig5a_chain |
| `data/cost` | `lcoh_global_<year>_reg.csv` | 20 | 10.7 MB | linear-program result per land cell for one weather year (LCOH, capacities) | case_low | aggregate_global, audit_vintage, export_source_data, fig5a_chain |
| `data/cost` | `lcoh_global_<year>_reg_ghr<year>.csv` | 40 | 21.4 MB | output of `case_low`: the lowest-cost main case (2026-10-07) for one cost year: collect the 20-weather-year flexible-synthesis LP, b | case_low | aggregate_global, audit_vintage, export_source_data, fig5a_chain |
| `data/cost` | `lcoh_global_<year>_reg_iea.csv` | 20 | 10.7 MB | output of `case_low`: the lowest-cost main case (2026-10-07) for one cost year: collect the 20-weather-year flexible-synthesis LP, b | case_low | aggregate_global, audit_vintage, export_source_data, fig5a_chain |
| `data/cost` | `lcoh_global_<year>_reg_iea_test.csv` | 1 | 1 kB | output of `case_low`: the lowest-cost main case (2026-10-07) for one cost year: collect the 20-weather-year flexible-synthesis LP, b | case_low | aggregate_global, audit_vintage, export_source_data, fig5a_chain |
| `data/cost` | `lcoh_global_<year>_reg_prewaccfix.csv` | 20 | 9.6 MB | output of `case_low`: the lowest-cost main case (2026-10-07) for one cost year: collect the 20-weather-year flexible-synthesis LP, b | case_low | aggregate_global, audit_vintage, export_source_data, fig5a_chain |
| `data/cost` | `lcoh_global_fixed.csv` | 1 | 0.1 MB | input read by `security_budget` |  | security_budget |
| `data/cost` | `lcoh_robustness.csv` | 1 | 0 kB |  |  |  |
| `data/cost` | `lcoh_robustness_sample.csv` | 1 | 1 kB |  |  |  |
| `data/cost` | `lcos_demo.csv` | 1 | 3 kB |  |  |  |
| `data/cost` | `lcos_global.csv` | 1 | 0.7 MB |  |  |  |
| `data/cost` | `lcos_global_snapshot.csv` | 1 | 0.3 MB |  |  |  |
| `data/cost` | `lowest_case_scalars.csv` | 1 | 0 kB | cost multipliers of the lowest-cost case by cost year | capex_2030low | case_low, flex_prepare_lowest |
| `data/cost` | `matching_cost.csv` | 1 | 0.1 MB |  |  |  |
| `data/cost` | `matching_premium_by_site.csv` | 1 | 1 kB |  |  |  |
| `data/cost` | `net_dep_jodi_overrides.csv` | 1 | 5 kB | output of `security_budget`: how much security does 1%, 2%, 3% of GDP buy? | security_budget |  |
| `data/cost` | `offshore_projects_osm.csv` | 1 | 0 kB |  |  |  |
| `data/cost` | `owid_energy.csv` | 1 | 9.2 MB | Our World in Data energy dataset (Energy Institute) used for net import dependence |  | audit_figure3, demand, risk_all_countries, security_budget |
| `data/cost` | `parity_years.csv` | 1 | 2 kB | input read by `fig_main_cities` |  | fig_main_cities, make_paper_tables |
| `data/cost` | `policy_ci_headroom.csv` | 1 | 6 kB |  |  |  |
| `data/cost` | `policy_inventory.csv` | 1 | 3 kB |  |  |  |
| `data/cost` | `policy_public_cost.csv` | 1 | 1 kB |  |  |  |
| `data/cost` | `policy_rule_ci.csv` | 1 | 0 kB |  |  |  |
| `data/cost` | `policy_stack.csv` | 1 | 1 kB |  |  |  |
| `data/cost` | `policy_tau_by_rule.csv` | 1 | 0 kB |  |  |  |
| `data/cost` | `policy_tau_by_rule_vintage.csv` | 1 | 0 kB |  |  |  |
| `data/cost` | `puerto_rico_proxy.csv` | 1 | 4 kB |  |  |  |
| `data/cost` | `regional_cf_<year>.csv` | 1 | 0.4 MB |  |  |  |
| `data/cost` | `regional_cf_<year>_corrected.csv` | 1 | 0.4 MB |  |  |  |
| `data/cost` | `reserve_dividend.csv` | 1 | 31 kB |  |  |  |
| `data/cost` | `reserves_cover.csv` | 1 | 4 kB | output of `reserves`: strategic and commercial oil stocks as a security BUFFER. | reserves |  |
| `data/cost` | `reserves_resilience.csv` | 1 | 8 kB |  |  |  |
| `data/cost` | `sd_map_classes.csv` | 1 | 0.1 MB | Fig. 2 class of each land cell (cost and demand terciles) | fig_sd_map | corridor_maps, export_source_data, fig_si_corridors, map_base |
| `data/cost` | `sd_regimes.csv` | 1 | 69 kB |  |  |  |
| `data/cost` | `sea_cell_cost_check.csv` | 1 | 42 kB |  |  |  |
| `data/cost` | `security_budget.csv` | 1 | 0.1 MB | Fig. 5: share of demand and of net imports replaced at 1-3% of GDP, land ceiling | security_budget | audit_figure3, case_low, corridor_maps, export_source_data |
| `data/cost` | `security_budget_dac.csv` | 1 | 0.1 MB | output of `security_budget`: how much security does 1%, 2%, 3% of GDP buy? | security_budget |  |
| `data/cost` | `security_by_fuel.csv` | 1 | 33 kB | output of `security`: Phase-1 of the unified security ledger (SECURITY_METHOD.md). | security |  |
| `data/cost` | `security_events.csv` | 1 | 4 kB | input read by `gap` |  | gap, reserves, security |
| `data/cost` | `security_index.csv` | 1 | 54 kB | value of fuel lost and expected disruption share per economy | fig5a_chain, security | corridor_maps, demand_grid, fig5_chain, fig_si_voll_map |
| `data/cost` | `security_parity.csv` | 1 | 3 kB | input read by `coreset` |  | coreset |
| `data/cost` | `security_scenarios.csv` | 1 | 33 kB | output of `security`: Phase-1 of the unified security ledger (SECURITY_METHOD.md). | security |  |
| `data/cost` | `sens_electrolyser_ghr<year>_high.csv` | 1 | 0 kB |  |  |  |
| `data/cost` | `sens_electrolyser_ghr<year>_low.csv` | 1 | 0 kB |  |  |  |
| `data/cost` | `sens_update_co2.csv` | 1 | 4 kB |  |  |  |
| `data/cost` | `supplier_shares_audit.csv` | 1 | 8 kB | output of `fetch_supplier_mirror`: audit of the top-supplier shares in vulnerability_inputs.csv (2026-10-07): some reporters book part or all of  | fetch_supplier_mirror | fetch_vulnerability |
| `data/cost` | `supply_demand.csv` | 1 | 37 kB | output of `supply_demand`: can each country actually supply its own demand, at what cost, and with what security gain? | supply_demand | case_low, export_source_data, fig5a_chain, fig_main_framework |
| `data/cost` | `syn150_fig2_cells.csv` | 1 | 0.4 MB |  |  |  |
| `data/cost` | `syn150_summary.csv` | 1 | 1 kB |  |  |  |
| `data/cost` | `syn200_fig2_cells.csv` | 1 | 0.4 MB |  |  |  |
| `data/cost` | `syn200_summary.csv` | 1 | 1 kB |  |  |  |
| `data/cost` | `tab_paths.tex` | 1 | 1 kB | output of `make_tab_paths`: Supplementary Table tab:paths: (a) median hydrogen cost at the 29 case systems by build year (vintage_fuels.cs | make_tab_paths |  |
| `data/cost` | `tech_assignment.csv` | 1 | 0.1 MB | output of `make_class_ref`: CLIMATOLOGICAL technology assignment per cell. | make_class_ref | generate_cf_global, generate_cf_hourly, inputs |
| `data/cost` | `tier_scalars.csv` | 1 | 1 kB | cost multipliers by tier (lowest, central, highest) and cost year | capex_tiers | case_low |
| `data/cost` | `top_sites.csv` | 1 | 1 kB |  |  |  |
| `data/cost` | `trajectory_dea_atb.csv` | 1 | 2 kB | input read by `capex_2030low` |  | capex_2030low, capex_tiers |
| `data/cost` | `trajectory_index.csv` | 1 | 4 kB | input read by `audit_vintage` |  | audit_vintage, capex_2030low, capex_tiers |
| `data/cost` | `transport_delivered.csv` | 1 | 0.4 MB | output of `transport`: would a demand cell rather buy fuel from a cheaper cell and pay for transport? (2026-09-24: Fig | transport |  |
| `data/cost` | `transport_summary.csv` | 1 | 1 kB | output of `transport`: would a demand cell rather buy fuel from a cheaper cell and pay for transport? (2026-09-24: Fig | transport | fig_si_corridors, map_layers, transport_flows |
| `data/cost` | `us_h2_etoh.csv` | 1 | 12 kB |  |  |  |
| `data/cost` | `vintage_bound.csv` | 1 | 1 kB |  |  |  |
| `data/cost` | `vintage_check_<year>_Moderate.csv` | 1 | 5 kB |  |  |  |
| `data/cost` | `vintage_crossing.csv` | 1 | 0.2 MB |  |  |  |
| `data/cost` | `vintage_fuels.csv` | 1 | 1.6 MB | input read by `audit_vintage` |  | audit_vintage, demand_grid, make_tab_paths |
| `data/cost` | `vintage_sites.csv` | 1 | 2.6 MB | input read by `audit_vintage` |  | audit_vintage |
| `data/cost` | `vintage_sites_base.csv` | 1 | 2.4 MB |  |  |  |
| `data/cost` | `vintage_sites_ghr<year>.csv` | 1 | 2.6 MB |  |  |  |
| `data/cost` | `vintage_sites_waccm2.csv` | 1 | 2.4 MB |  |  |  |
| `data/cost` | `vintage_wacc_compare.csv` | 1 | 32 kB |  |  |  |
| `data/cost` | `volatility_by_fuel.csv` | 1 | 1 kB |  |  |  |
| `data/cost` | `volatility_ratio.csv` | 1 | 4 kB |  |  |  |
| `data/cost` | `vulnerability_index.csv` | 1 | 6 kB | output of `supply_demand`: can each country actually supply its own demand, at what cost, and with what security gain? | supply_demand | audit_figure3, fig_main_cities, make_fig3_tables, make_paper_tables |
| `data/cost` | `vulnerability_inputs.csv` | 1 | 34 kB | supplier shares and Herfindahl indices of crude, refined and gas imports (UN Comtrade) |  | audit_figure3, fetch_supplier_mirror, fetch_vulnerability, fig5a_chain |
| `data/cost` | `vulnerability_inputs_gdp<year>.csv` | 1 | 33 kB |  |  |  |
| `data/cost` | `wacc_by_country.csv` | 1 | 14 kB | input read by `inputs` |  | inputs |
| `data/cost` | `wacc_by_country_v1.csv` | 1 | 7 kB |  |  |  |
| `data/cost` | `wacc_fix_impact.csv` | 1 | 1 kB |  |  |  |
| `data/cost` | `water_cost_by_cell.csv` | 1 | 0.2 MB | input read by `fig_pptx_pairs` |  | fig_pptx_pairs, fig_si_feedstocks, inputs |
| `data/cost` | `wind_class_multiplier.csv` | 1 | 0.1 MB |  |  |  |
| `data/cost/flexlow` | `costs_<year>.cluster_only.npz` | 1 | 25 kB | output of `flex_prepare_lowest`: cost inputs for the 20-weather-year flexible-synthesis runs of the lowest-cost case (2026-10-07): one costs_<y | flex_prepare_lowest | audit_figure3, audit_vintage, co2_feedstock, co2_sources |
| `data/cost/flexlow` | `costs_<year>.npz` | 4 | 0.1 MB | per-cell cost inputs of the linear programs for one cost case | flex_prepare_lowest | audit_figure3, audit_vintage, co2_feedstock, co2_sources |
| `data/cost/flexlow` | `costs_<year>high.npz` | 4 | 0.1 MB | output of `flex_prepare_lowest`: cost inputs for the 20-weather-year flexible-synthesis runs of the lowest-cost case (2026-10-07): one costs_<y | flex_prepare_lowest | audit_figure3, audit_vintage, co2_feedstock, co2_sources |
| `data/cost/flexlow` | `costs_<year>mid.npz` | 4 | 0.1 MB | output of `flex_prepare_lowest`: cost inputs for the 20-weather-year flexible-synthesis runs of the lowest-cost case (2026-10-07): one costs_<y | flex_prepare_lowest | audit_figure3, audit_vintage, co2_feedstock, co2_sources |
| `data/cost/flexlow/run_2025/out` | `part_<year>_<chunk>.csv` | 1000 | 13.3 MB | linear-program results per cell and weather year, one chunk of cells |  |  |
| `data/cost/flexlow/run_2025high/out` | `part_<year>_<chunk>.csv` | 1000 | 14.0 MB | linear-program results per cell and weather year, one chunk of cells |  |  |
| `data/cost/flexlow/run_2025mid/out` | `part_<year>_<chunk>.csv` | 1000 | 13.5 MB | linear-program results per cell and weather year, one chunk of cells |  |  |
| `data/cost/flexlow/run_2030/out` | `part_<year>_<chunk>.csv` | 1000 | 13.3 MB | linear-program results per cell and weather year, one chunk of cells |  |  |
| `data/cost/flexlow/run_2030high/out` | `part_<year>_<chunk>.csv` | 1000 | 13.5 MB | linear-program results per cell and weather year, one chunk of cells |  |  |
| `data/cost/flexlow/run_2030mid/out` | `part_<year>_<chunk>.csv` | 1000 | 13.5 MB | linear-program results per cell and weather year, one chunk of cells |  |  |
| `data/cost/flexlow/run_2040/out` | `part_<year>_<chunk>.csv` | 1000 | 14.1 MB | linear-program results per cell and weather year, one chunk of cells |  |  |
| `data/cost/flexlow/run_2040high/out` | `part_<year>_<chunk>.csv` | 1000 | 13.7 MB | linear-program results per cell and weather year, one chunk of cells |  |  |
| `data/cost/flexlow/run_2040mid/out` | `part_<year>_<chunk>.csv` | 1000 | 13.7 MB | linear-program results per cell and weather year, one chunk of cells |  |  |
| `data/cost/flexlow/run_2050/out` | `part_<year>_<chunk>.csv` | 1000 | 13.0 MB | linear-program results per cell and weather year, one chunk of cells |  |  |
| `data/cost/flexlow/run_2050high/out` | `part_<year>_<chunk>.csv` | 1000 | 14.7 MB | linear-program results per cell and weather year, one chunk of cells |  |  |
| `data/cost/flexlow/run_2050mid/out` | `part_<year>_<chunk>.csv` | 1000 | 14.3 MB | linear-program results per cell and weather year, one chunk of cells |  |  |
| `data/demand/ei_2026` | `statistical review of world energy narrow format.csv` | 1 | 21.1 MB |  |  |  |
| `data/demand/un_energy/raw_biomass` | `un_biomass_tes.xml` | 1 | 1.2 MB | UN Energy Statistics Database, total energy supply of primary solid biofuels and charcoal by country (SDMX); adds traditional biomass to national primary energy use in the value of lost fuel (2026-10-21) |  | un_energy |
| `data/gdp_projections` | `imf_weo_gdp_2023_2031.json` | 1 | 43 kB | IMF World Economic Outlook real GDP growth 2023-2031 (DataMapper API); GDP projected from 2025 to 2030 |  | gdp_projection, security_budget |
| `data/gdp_projections` | `ssp2_gdp_v3.2.csv` | 1 | 0.4 MB | SSP v3.2 (OECD ENV-Growth 2025) SSP2 GDP by country, extracted from ssp_basic_drivers_release_3.2_full.xlsx (not redistributed); growth after 2030 |  | gdp_projection, security_budget |
| `data/demand/un_energy` | `un_net_dependence.csv` | 1 | 18 kB | output of `un_trade`: oil and gas net import dependence from the UN Energy Statistics Database, for the economies the Energy Institu | un_trade | security_budget |
| `data/demand/un_energy` | `un_sector_fuel_tj.csv` | 1 | 0.4 MB | output of `un_energy`: national fossil fuel use by sector from the UN Energy Statistics Database, the LEVEL that demand_grid anchors  | un_energy | security_budget |
| `data/demand/un_energy/raw` | `area_codes.csv` | 1 | 5 kB | output of `un_energy`: national fossil fuel use by sector from the UN Energy Statistics Database, the LEVEL that demand_grid anchors  | un_energy |  |
| `data/demand/usgs/nitrogen` | `par_100_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_104_<year>_all.json` | 1 | 76 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_108_<year>_all.json` | 1 | 46 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_116_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_120_<year>_all.json` | 1 | 87 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_124_<year>_all.json` | 1 | 0.3 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_12_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_132_<year>_all.json` | 1 | 46 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_136_<year>_all.json` | 1 | 27 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_140_<year>_all.json` | 1 | 4 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_144_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_152_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_156_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_170_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_174_<year>_all.json` | 1 | 6 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_178_<year>_all.json` | 1 | 57 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_180_<year>_all.json` | 1 | 84 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_188_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_191_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_196_<year>_all.json` | 1 | 99 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_203_<year>_all.json` | 1 | 0.3 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_204_<year>_all.json` | 1 | 34 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_208_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_20_<year>_all.json` | 1 | 18 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_212_<year>_all.json` | 1 | 39 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_214_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_218_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_222_<year>_all.json` | 1 | 94 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_231_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_233_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_234_<year>_all.json` | 1 | 50 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_242_<year>_all.json` | 1 | 64 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_246_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_24_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_251_<year>_all.json` | 1 | 0.4 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_258_<year>_all.json` | 1 | 23 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_262_<year>_all.json` | 1 | 32 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_266_<year>_all.json` | 1 | 44 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_268_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_270_<year>_all.json` | 1 | 16 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_275_<year>_all.json` | 1 | 38 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_276_<year>_all.json` | 1 | 0.4 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_288_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_28_<year>_all.json` | 1 | 33 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_300_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_308_<year>_all.json` | 1 | 47 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_31_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_320_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_328_<year>_all.json` | 1 | 61 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_32_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_340_<year>_all.json` | 1 | 91 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_344_<year>_all.json` | 1 | 62 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_348_<year>_all.json` | 1 | 0.3 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_352_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_360_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_364_<year>_all.json` | 1 | 92 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_368_<year>_all.json` | 1 | 32 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_36_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_372_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_376_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_380_<year>_all.json` | 1 | 0.3 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_384_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_388_<year>_all.json` | 1 | 89 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_392_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_398_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_400_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_404_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_40_<year>_all.json` | 1 | 0.3 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_410_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_414_<year>_all.json` | 1 | 81 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_417_<year>_all.json` | 1 | 89 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_418_<year>_all.json` | 1 | 68 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_422_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_426_<year>_all.json` | 1 | 32 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_428_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_430_<year>_all.json` | 1 | 32 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_440_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_442_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_446_<year>_all.json` | 1 | 3 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_44_<year>_all.json` | 1 | 34 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_450_<year>_all.json` | 1 | 67 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_454_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_458_<year>_all.json` | 1 | 0.3 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_462_<year>_all.json` | 1 | 85 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_466_<year>_all.json` | 1 | 91 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_470_<year>_all.json` | 1 | 87 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_478_<year>_all.json` | 1 | 54 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_480_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_484_<year>_all.json` | 1 | 66 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_48_<year>_all.json` | 1 | 55 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_490_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_496_<year>_all.json` | 1 | 48 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_498_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_499_<year>_all.json` | 1 | 89 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_500_<year>_all.json` | 1 | 18 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_504_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_508_<year>_all.json` | 1 | 83 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_512_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_516_<year>_all.json` | 1 | 69 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_51_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_528_<year>_g0.json` | 1 | 58 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_528_<year>_g1.json` | 1 | 52 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_528_<year>_g2.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_528_<year>_g3.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_528_<year>_g4.json` | 1 | 92 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_528_<year>_g5.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_52_<year>_all.json` | 1 | 47 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_533_<year>_all.json` | 1 | 26 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_554_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_558_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_562_<year>_all.json` | 1 | 36 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_566_<year>_all.json` | 1 | 61 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_56_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_579_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_586_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_591_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_598_<year>_all.json` | 1 | 59 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_600_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_604_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_608_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_60_<year>_all.json` | 1 | 23 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_616_<year>_all.json` | 1 | 0.3 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_620_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_626_<year>_all.json` | 1 | 31 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_634_<year>_all.json` | 1 | 67 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_642_<year>_all.json` | 1 | 0.3 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_646_<year>_all.json` | 1 | 92 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_64_<year>_all.json` | 1 | 23 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_670_<year>_all.json` | 1 | 33 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_678_<year>_all.json` | 1 | 17 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_682_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_686_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_688_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_68_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_690_<year>_all.json` | 1 | 55 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_699_<year>_all.json` | 1 | 0.3 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_702_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_703_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_704_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_705_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_70_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_710_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_716_<year>_all.json` | 1 | 87 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_724_<year>_all.json` | 1 | 0.4 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_728_<year>_all.json` | 1 | 15 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_72_<year>_all.json` | 1 | 40 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_740_<year>_all.json` | 1 | 42 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_748_<year>_all.json` | 1 | 45 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_752_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_757_<year>_all.json` | 1 | 0.3 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_762_<year>_all.json` | 1 | 51 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_764_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_768_<year>_all.json` | 1 | 30 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_76_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_776_<year>_all.json` | 1 | 15 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_780_<year>_all.json` | 1 | 92 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_784_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_788_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_792_<year>_all.json` | 1 | 0.3 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_800_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_804_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_807_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_818_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_826_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_834_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_842_<year>_all.json` | 1 | 0.3 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_84_<year>_all.json` | 1 | 78 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_854_<year>_all.json` | 1 | 53 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_858_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_860_<year>_all.json` | 1 | 0.1 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_882_<year>_all.json` | 1 | 16 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_887_<year>_all.json` | 1 | 29 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_894_<year>_all.json` | 1 | 0.2 MB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_8_<year>_all.json` | 1 | 50 kB |  |  |  |
| `data/demand/usgs/nitrogen` | `par_96_<year>_all.json` | 1 | 34 kB |  |  |  |
| `data/grid` | `grid_cells.csv` | 1 | 0.3 MB | output of `01_define_grid`: Build the 2.5-degree global analysis grid for the synthetic-fuels TEA. | 01_define_grid | plot_style |
| `data/grid` | `grid_cells.gpkg` | 1 | 1.4 MB | 2.5-degree grid cells (land and coastal) | 01_define_grid | plot_style |
| `data/grid/naturalearth` | `ne_10m_admin_0_countries.README.html` | 1 | 39 kB |  |  |  |
| `data/grid/naturalearth` | `ne_10m_admin_0_countries.VERSION.txt` | 1 | 0 kB |  |  |  |
| `data/grid/naturalearth` | `ne_10m_admin_0_countries.cpg` | 1 | 0 kB | input read by `01_define_grid` |  | 01_define_grid, capex_2030low, capex_tiers, cell_land_area |
| `data/grid/naturalearth` | `ne_10m_admin_0_countries.dbf` | 1 | 0.9 MB | input read by `01_define_grid` |  | 01_define_grid, capex_2030low, capex_tiers, cell_land_area |
| `data/grid/naturalearth` | `ne_10m_admin_0_countries.prj` | 1 | 0 kB | input read by `01_define_grid` |  | 01_define_grid, capex_2030low, capex_tiers, cell_land_area |
| `data/grid/naturalearth` | `ne_10m_admin_0_countries.shp` | 1 | 8.8 MB | Natural Earth admin-0 country boundaries, 1:10m, v5.1.1 (public domain) |  | 01_define_grid, capex_2030low, capex_tiers, cell_land_area |
| `data/grid/naturalearth` | `ne_10m_admin_0_countries.shx` | 1 | 2 kB | input read by `01_define_grid` |  | 01_define_grid, capex_2030low, capex_tiers, cell_land_area |
| `data/grid/naturalearth` | `ne_110m_admin_0_countries.zip` | 1 | 4.9 MB |  |  |  |
| `data/jodi` | `GAS_world_NewFormat.zip` | 1 | 1.7 MB |  |  |  |
| `data/jodi` | `STAGING_world_NewFormat.csv` | 1 | 12.9 MB | JODI-Gas world database |  | security_budget |
| `data/jodi` | `jodi_oil_net.csv` | 1 | 0.3 MB | JODI-Oil net trade |  | security_budget |
| `data/jodi` | `oil_primary_<year>.csv` | 2 | 23.2 MB |  |  |  |
| `data/jodi` | `oil_secondary_<year>.csv` | 2 | 52.9 MB |  |  |  |
| `data/prices` | `cmo-historical-data-monthly.xlsx` | 1 | 0.6 MB | World Bank Commodity Price Data (Pink Sheet) |  |  |
| `data/prices` | `country_gas_prices.csv` | 1 | 0.2 MB | output of `fetch_country_prices`: real COUNTRY-LEVEL energy prices from open official APIs. | fetch_country_prices | gap |
| `data/prices` | `country_import_prices_monthly_gj.csv` | 1 | 3.2 MB | monthly import prices of each economy (US$/GJ, nominal) | import_prices |  |
| `data/prices` | `diesel_usgc.xls` | 1 | 40 kB | EIA US Gulf Coast ultra-low-sulfur diesel spot price |  | prices |
| `data/prices` | `fossil_monthly_gj_lhv.csv` | 1 | 0.1 MB | monthly fossil benchmark prices (US$/GJ, LHV) | prices | import_prices |
| `data/prices` | `jet_usgc.xls` | 1 | 56 kB | EIA US Gulf Coast kerosene-type jet fuel spot price |  | prices |
| `data/prices/figure3_risk` | `coal_supplier_hhi_<year>.csv` | 1 | 1 kB | input read by `audit_figure3` |  | audit_figure3 |
| `data/prices/figure3_risk` | `ft_supplier_hhi_<year>.csv` | 1 | 10 kB | input read by `audit_figure3` |  | audit_figure3 |
| `data/prices/figure3_risk` | `ft_trade_balance_annual.csv` | 1 | 56 kB | input read by `audit_figure3` |  | audit_figure3 |
| `data/prices/figure3_risk` | `gas_supplier_hhi_<year>.csv` | 1 | 6 kB | input read by `audit_figure3` |  | audit_figure3 |
| `data/prices/figure3_risk` | `reporter_codes_world.csv` | 1 | 3 kB | input read by `risk_all_countries` |  | risk_all_countries |
| `data/prices/figure3_risk` | `world_risk_inputs.csv` | 1 | 0.4 MB | input read by `risk_all_countries` |  | risk_all_countries |
| `data/prices/fx` | `bis_cpi_core30_monthly.csv` | 1 | 0.7 MB | BIS consumer price indices |  | fig_main_sites |
| `data/prices/fx` | `bis_xru_core30_monthly.csv` | 1 | 0.9 MB | BIS exchange rates |  | fig_main_sites |
| `data/prices/fx` | `imf_cpi_core8_monthly.csv` | 1 | 0.2 MB | input read by `fig_main_sites` |  | fig_main_sites |
| `data/prices/fx` | `us_cpi_monthly.csv` | 1 | 53 kB | US CPI-U (BLS), deflator to 2025 US$ |  | audit_figure3, fig_main_sites |
| `data/prices/imports_ammonia` | `ammonia_supplier_hhi_<year>.csv` | 1 | 9 kB | input read by `audit_figure3` |  | audit_figure3 |
| `data/prices/imports_ammonia` | `ammonia_trade_balance.csv` | 1 | 39 kB | input read by `import_prices` |  | import_prices |
| `data/prices/imports_ammonia` | `ammonia_trade_balance_annual_supplement.csv` | 1 | 3 kB | input read by `import_prices` |  | import_prices |
| `data/prices/sg_mops` | `sg_mops_all_products_wide.csv` | 1 | 0.7 MB | Singapore MOPS product prices (Platts assessments republished by KNOC Petronet; use subject to the publisher's terms) |  | gap |
| `data/prices/sg_mops` | `sg_mops_products.csv` | 1 | 2.2 MB | input read by `import_prices` |  | import_prices |
| `work/caselow/<case>/data` | `ammonia_consumption.csv` | 4 | 59 kB | national nitrogen balance in ammonia equivalent (USGS, UN Comtrade) | ammonia_consumption, nitrogen_consumption | audit_figure3, demand_grid, fetch_nitrogen_trade, fig5a_chain |
| `work/caselow/<case>/data` | `ammonia_consumption_<year>basis.csv` | 4 | 35 kB | output of `ammonia_consumption`: national apparent consumption of ammonia (2026-10-07). | ammonia_consumption, nitrogen_consumption | audit_figure3, demand_grid, fetch_nitrogen_trade, fig5a_chain |
| `work/caselow/<case>/data` | `ammonia_consumption_nh3only.csv` | 4 | 42 kB | input read by `nitrogen_consumption` |  | nitrogen_consumption |
| `work/caselow/<case>/data` | `atb_capex_index.csv` | 4 | 4 kB |  |  |  |
| `work/caselow/<case>/data` | `atb_raw_subset.csv` | 4 | 4 kB |  |  |  |
| `work/caselow/<case>/data` | `battery_check_<year>.csv` | 4 | 31 kB |  |  |  |
| `work/caselow/<case>/data` | `bench_cf_Berlin.csv` | 4 | 1.0 MB |  |  |  |
| `work/caselow/<case>/data` | `bench_cf_Chile-best.csv` | 4 | 0.9 MB |  |  |  |
| `work/caselow/<case>/data` | `bench_cf_Riyadh.csv` | 4 | 1.0 MB |  |  |  |
| `work/caselow/<case>/data` | `bootstrap_demo.csv` | 4 | 2 kB |  |  |  |
| `work/caselow/<case>/data` | `breakeven_carbon_<year>.csv` | 4 | 0.5 MB | input read by `make_paper_tables` |  | make_paper_tables, map_base, map_layers |
| `work/caselow/<case>/data` | `candidate_cities_eval.csv` | 4 | 18 kB |  |  |  |
| `work/caselow/<case>/data` | `capex_by_country.csv` | 4 | 0.2 MB | country capital costs and synthesis location factor used in the case | capex_2030low, capex_tiers, case_low | flex_prepare_lowest, inputs |
| `work/caselow/<case>/data` | `capex_by_country_<year>high.csv` | 10 | 0.4 MB | country capital costs, highest tier | capex_2030low, capex_tiers, case_low | flex_prepare_lowest, inputs |
| `work/caselow/<case>/data` | `capex_by_country_<year>low.csv` | 16 | 0.8 MB | country solar, wind and electrolyzer capital costs, lowest tier | capex_2030low, capex_tiers, case_low | flex_prepare_lowest, inputs |
| `work/caselow/<case>/data` | `capex_by_country_<year>low_log.csv` | 4 | 82 kB | output of `capex_2030low`: 2030 lowest-cost capex layer (2026-10-07). | capex_2030low, capex_tiers, case_low | flex_prepare_lowest, inputs |
| `work/caselow/<case>/data` | `capex_by_country_<year>mid.csv` | 10 | 0.4 MB | country capital costs, central tier | capex_2030low, capex_tiers, case_low | flex_prepare_lowest, inputs |
| `work/caselow/<case>/data` | `capex_by_country_ghr<year>.csv` | 4 | 0.1 MB | input read by `capex_2030low` |  | capex_2030low, capex_tiers |
| `work/caselow/<case>/data` | `capex_by_country_ghr<year>_high.csv` | 4 | 100 kB | input read by `capex_2030low` |  | capex_2030low, capex_tiers |
| `work/caselow/<case>/data` | `capex_by_country_ghr<year>_low.csv` | 4 | 99 kB | input read by `capex_2030low` |  | capex_2030low, capex_tiers |
| `work/caselow/<case>/data` | `capex_by_country_ghr<year>_mainline.csv` | 4 | 0.1 MB | input read by `capex_2030low` |  | capex_2030low, capex_tiers |
| `work/caselow/<case>/data` | `capex_by_country_iea<year>.csv` | 4 | 0.1 MB |  |  |  |
| `work/caselow/<case>/data` | `cell_land_area.csv` | 4 | 0.5 MB | national land area in each 2.5-degree cell |  | cell_land_area, supply_demand |
| `work/caselow/<case>/data` | `cell_security_year.csv` | 4 | 39 kB | output of `global_trajectory`: the globally aggregated result plus the demand-concentration numbers. | global_trajectory |  |
| `work/caselow/<case>/data` | `cf_global_<year>.csv` | 4 | 2.4 MB | cell metadata and annual capacity factors (technology assignment, IEC class) | generate_cf_global | aggregate_global, cell_land_area, corridor_maps, fig5_chain |
| `work/caselow/<case>/data` | `cf_global_<year>_matlab.csv` | 4 | 0.8 MB | output of `generate_cf_global`: FINAL global capacity-factor generator (Python/atlite) | generate_cf_global | aggregate_global, cell_land_area, corridor_maps, fig5_chain |
| `work/caselow/<case>/data` | `chain_q.csv` | 4 | 0.4 MB | expected disruption share by economy and fuel chain | fig5a_chain | corridor_maps, make_fig5_tables |
| `work/caselow/<case>/data` | `co2_cost_by_cell.csv` | 4 | 1.1 MB | cheapest CO2 source of each land cell and its delivered price (US$/t) |  | case_low, export_source_data, fig5a_chain, fig_main_framework |
| `work/caselow/<case>/data` | `co2_cost_by_cell_neutral.csv` | 4 | 0.8 MB | input read by `case_low` |  | case_low, fig_si_feedstocks |
| `work/caselow/<case>/data` | `co2_cost_by_cell_neutral_longterm.csv` | 4 | 0.7 MB | input read by `case_low` |  | case_low |
| `work/caselow/<case>/data` | `compare_integrated.csv` | 4 | 1 kB |  |  |  |
| `work/caselow/<case>/data` | `core30.csv` | 4 | 3 kB | output of `coreset`: ONE definition of the 30 core economies shown in every main-text figure and table (the global aggregates use a | coreset, fig_main_cities, fig_main_demand_struct | audit_figure3, export_source_data, make_fig3_tables, risk_all_countries |
| `work/caselow/<case>/data` | `core30_cities.csv` | 4 | 19 kB | output of `fig_main_cities`: MAIN-TEXT city figure: the 30 core cities (one demand centre per core-30 economy) with cost, weather risk, mar | fig_main_cities |  |
| `work/caselow/<case>/data` | `core30_demand_struct.csv` | 4 | 8 kB | output of `fig_main_demand_struct`: the demand side, economy by economy: what each core-30 addressable fossil-fuel bill is actually made of, fuel  | fig_main_demand_struct |  |
| `work/caselow/<case>/data` | `core30_sites.csv` | 4 | 0.2 MB | copy of core30_sites_ammonia.csv | fig_main_sites | audit_figure3, export_source_data, make_fig3_tables, security_budget |
| `work/caselow/<case>/data` | `core30_sites_ammonia.csv` | 4 | 0.2 MB | Fig. 3: green ammonia cost, normal and disruption price quantiles, import risk index, bill |  | export_source_data, si_fig3_tables |
| `work/caselow/<case>/data` | `core30_sites_ammonia_washout12m.csv` | 4 | 0.2 MB |  |  |  |
| `work/caselow/<case>/data` | `core30_sites_ammonia_washout3m.csv` | 4 | 0.1 MB |  |  |  |
| `work/caselow/<case>/data` | `core30_sites_ft.csv` | 4 | 0.2 MB | Supplementary Fig. (diesel and jet version of Fig. 3) |  |  |
| `work/caselow/<case>/data` | `core30_sites_ft_washout12m.csv` | 4 | 0.2 MB |  |  |  |
| `work/caselow/<case>/data` | `core30_sites_ft_washout3m.csv` | 4 | 0.2 MB |  |  |  |
| `work/caselow/<case>/data` | `corridors_discussion.csv` | 4 | 3 kB | input read by `fig_si_corridors` |  | fig_si_corridors, map_layers |
| `work/caselow/<case>/data` | `country_fossil_exposure.csv` | 4 | 41 kB | output of `regional_prices`: turn three global markers into a per-country monthly fossil price, and measure how differently each country is | regional_prices |  |
| `work/caselow/<case>/data` | `crisis_by_country_event.csv` | 4 | 83 kB |  |  |  |
| `work/caselow/<case>/data` | `deck_summary.json` | 4 | 86 kB |  |  |  |
| `work/caselow/<case>/data` | `demand_by_fuel.csv` | 4 | 87 kB | output of `demand`: the measured demand layer for the security ledger. | demand | demand_grid, fig_main_framework, security |
| `work/caselow/<case>/data` | `demand_by_fuel_owid.csv` | 4 | 73 kB |  |  |  |
| `work/caselow/<case>/data` | `demand_fuel_grid.csv` | 4 | 2.1 MB | addressable demand by land cell and fuel (GJ/yr) | demand_grid | audit_figure3, fig5_chain, fig5a_chain, fig_main_demand_struct |
| `work/caselow/<case>/data` | `dynamic_ops_global.csv` | 4 | 1.1 MB |  |  |  |
| `work/caselow/<case>/data` | `dynamic_ops_summary.csv` | 4 | 5 kB |  |  |  |
| `work/caselow/<case>/data` | `ed_crisis_by_country_regime.csv` | 4 | 1.2 MB | output of `fig_main_crisis`: Extended Data: each dated disruption, economy by economy, on Figure 3's comparator and rules. | fig_main_crisis | make_fig3_tables |
| `work/caselow/<case>/data` | `ed_crisis_pooled_by_fuel.csv` | 4 | 3 kB | output of `fig_main_crisis`: Extended Data: each dated disruption, economy by economy, on Figure 3's comparator and rules. | fig_main_crisis |  |
| `work/caselow/<case>/data` | `fig3_risk_all_countries.csv` | 4 | 0.2 MB | import risk index for every modeled country (Supplementary Table) |  | risk_all_countries |
| `work/caselow/<case>/data` | `fig5a_chain.csv` | 4 | 73 kB | Fig. 4a: portfolio mix, CO2 displaced, cost premium, security margin, net premium, carbon price | fig5a_chain, fig5a_sens, make_fig5_tables | case_low, corridor_maps, export_source_data, fig4_years |
| `work/caselow/<case>/data` | `fig5a_chain_sensitivity.csv` | 4 | 0.7 MB | output of `fig5a_sens`: sensitivity of the chain-basis Figure 5a (for the SI). | fig5a_sens, make_fig5_tables |  |
| `work/caselow/<case>/data` | `fig5b_chain_pairs.csv` | 4 | 0.6 MB | Fig. 4b: country-fuel blocks of the abatement cost curve | fig5_chain | export_source_data, map_layers |
| `work/caselow/<case>/data` | `fig5b_chain_trajectory.csv` | 4 | 13 kB | Fig. 4b: CO2 displaced with security value and on cost alone (Gt/yr) | fig5_chain | export_source_data, test_paper |
| `work/caselow/<case>/data` | `fig_budget_sources.csv` | 4 | 14 kB |  |  |  |
| `work/caselow/<case>/data` | `fig_budget_sources_README.md` | 4 | 11 kB |  |  |  |
| `work/caselow/<case>/data` | `figure3_country_audit.csv` | 4 | 0.4 MB | Fig. 3 inputs per economy: import exposure, supplier concentration, price basis |  | audit_figure3, export_source_data, fig5a_chain, fig_main_crisis |
| `work/caselow/<case>/data` | `figure3_download_gap_manifest.csv` | 4 | 34 kB |  |  |  |
| `work/caselow/<case>/data` | `figure3_event_audit.csv` | 4 | 0.1 MB | input read by `audit_figure3` |  | audit_figure3 |
| `work/caselow/<case>/data` | `figure3_event_coverage_summary.csv` | 4 | 3 kB |  |  |  |
| `work/caselow/<case>/data` | `figure3_member_event_audit.csv` | 4 | 0.3 MB | input read by `audit_figure3` |  | audit_figure3, fig_main_crisis |
| `work/caselow/<case>/data` | `figure3_washout_sensitivity.csv` | 4 | 0.1 MB | input read by `audit_figure3` |  | audit_figure3 |
| `work/caselow/<case>/data` | `final30_portfolio.csv` | 4 | 25 kB |  |  |  |
| `work/caselow/<case>/data` | `firm_tornado_summary.csv` | 4 | 5 kB |  |  |  |
| `work/caselow/<case>/data` | `flex20_fig2_cells.csv` | 4 | 1.6 MB |  |  |  |
| `work/caselow/<case>/data` | `flex20_summary.csv` | 4 | 5 kB |  |  |  |
| `work/caselow/<case>/data` | `flex60_fig2_cells.csv` | 4 | 1.6 MB |  |  |  |
| `work/caselow/<case>/data` | `flex60_summary.csv` | 4 | 5 kB |  |  |  |
| `work/caselow/<case>/data` | `flex70_fig2_cells.csv` | 4 | 1.6 MB |  |  |  |
| `work/caselow/<case>/data` | `flex70_summary.csv` | 4 | 5 kB |  |  |  |
| `work/caselow/<case>/data` | `flex_grid_summary.csv` | 4 | 4 kB |  |  |  |
| `work/caselow/<case>/data` | `flex_sensitivity_summary.csv` | 4 | 5 kB |  |  |  |
| `work/caselow/<case>/data` | `flex_tornado_summary.csv` | 4 | 5 kB |  |  |  |
| `work/caselow/<case>/data` | `ft9425_fig2_cells.csv` | 4 | 1.6 MB |  |  |  |
| `work/caselow/<case>/data` | `ft9425_summary.csv` | 4 | 5 kB |  |  |  |
| `work/caselow/<case>/data` | `fuel_reco_stats.csv` | 4 | 2 kB | output of `demand_grid`: gridded fuel-demand proxy and the plant recommendation. | demand_grid | fig_main_cost, make_paper_tables |
| `work/caselow/<case>/data` | `fuel_recommendation.csv` | 4 | 1.1 MB | output of `demand_grid`: gridded fuel-demand proxy and the plant recommendation. | demand_grid | fig_main_cost |
| `work/caselow/<case>/data` | `gap_country_fuel.csv` | 4 | 0.3 MB | output of `gap`: the single quantity behind the policy, crisis and vulnerability readings: | gap |  |
| `work/caselow/<case>/data` | `global_trajectory.csv` | 4 | 13 kB | global CO2 displaced by cost year | fig5_chain, global_trajectory | export_source_data, fig4_years, fig_main_demand_struct, fig_main_framework |
| `work/caselow/<case>/data` | `global_trajectory_countries.csv` | 4 | 0.7 MB | addressable demand and CO2 by economy and fuel | global_trajectory | export_source_data, fig_main_demand_struct, fig_main_framework, map_base |
| `work/caselow/<case>/data` | `island_strategy.csv` | 4 | 31 kB |  |  |  |
| `work/caselow/<case>/data` | `jodi_gas_dep_core30.csv` | 4 | 6 kB |  |  |  |
| `work/caselow/<case>/data` | `land_screen.csv` | 4 | 38 kB | output of `land_screen`: country-level screened land availability for the renewable build, replacing the uniform 2%-of-land cap. | land_screen | supply_demand |
| `work/caselow/<case>/data` | `lcof_countries_<year>.csv` | 4 | 0.2 MB | input read by `gap` |  | gap, policy |
| `work/caselow/<case>/data` | `lcof_countries_fuels_<year>.csv` | 4 | 1.3 MB | input read by `gap` |  | gap, policy |
| `work/caselow/<case>/data` | `lcof_fuels_<year>.csv` | 4 | 0.2 MB |  |  |  |
| `work/caselow/<case>/data` | `lcof_global_stats.csv` | 4 | 30.6 MB | levelized cost of each fuel per land cell (mean and firm, US$/GJ) | aggregate_global |  |
| `work/caselow/<case>/data` | `lcof_global_stats_reg.csv` | 4 | 17.0 MB |  |  |  |
| `work/caselow/<case>/data` | `lcof_sites_<year>.csv` | 4 | 20 kB |  |  |  |
| `work/caselow/<case>/data` | `lcoh_global_<year>.csv` | 80 | 36.2 MB | output of `case_low`: the lowest-cost main case (2026-10-07) for one cost year: collect the 20-weather-year flexible-synthesis LP, b | case_low | aggregate_global, audit_vintage, export_source_data, fig5a_chain |
| `work/caselow/<case>/data` | `lcoh_global_<year>_reg.csv` | 80 | 42.1 MB | linear-program result per land cell for one weather year (LCOH, capacities) | case_low | aggregate_global, audit_vintage, export_source_data, fig5a_chain |
| `work/caselow/<case>/data` | `lcoh_global_fixed.csv` | 4 | 0.5 MB | input read by `security_budget` |  | security_budget |
| `work/caselow/<case>/data` | `lcoh_robustness.csv` | 4 | 2 kB |  |  |  |
| `work/caselow/<case>/data` | `lcoh_robustness_sample.csv` | 4 | 6 kB |  |  |  |
| `work/caselow/<case>/data` | `lcos_demo.csv` | 4 | 13 kB |  |  |  |
| `work/caselow/<case>/data` | `lcos_global.csv` | 4 | 2.9 MB |  |  |  |
| `work/caselow/<case>/data` | `lcos_global_snapshot.csv` | 4 | 1.1 MB |  |  |  |
| `work/caselow/<case>/data` | `lowest_case_scalars.csv` | 4 | 2 kB | cost multipliers of the lowest-cost case by cost year | capex_2030low | case_low, flex_prepare_lowest |
| `work/caselow/<case>/data` | `matching_cost.csv` | 4 | 0.5 MB |  |  |  |
| `work/caselow/<case>/data` | `matching_premium_by_site.csv` | 4 | 5 kB |  |  |  |
| `work/caselow/<case>/data` | `net_dep_jodi_overrides.csv` | 4 | 21 kB | output of `security_budget`: how much security does 1%, 2%, 3% of GDP buy? | security_budget |  |
| `work/caselow/<case>/data` | `offshore_projects_osm.csv` | 4 | 0 kB |  |  |  |
| `work/caselow/<case>/data` | `owid_energy.csv` | 4 | 36.9 MB | Our World in Data energy dataset (Energy Institute) used for net import dependence |  | audit_figure3, demand, risk_all_countries, security_budget |
| `work/caselow/<case>/data` | `parity_years.csv` | 4 | 6 kB | input read by `fig_main_cities` |  | fig_main_cities, make_paper_tables |
| `work/caselow/<case>/data` | `policy_ci_headroom.csv` | 4 | 22 kB |  |  |  |
| `work/caselow/<case>/data` | `policy_inventory.csv` | 4 | 13 kB |  |  |  |
| `work/caselow/<case>/data` | `policy_public_cost.csv` | 4 | 3 kB |  |  |  |
| `work/caselow/<case>/data` | `policy_rule_ci.csv` | 4 | 1 kB |  |  |  |
| `work/caselow/<case>/data` | `policy_stack.csv` | 4 | 3 kB |  |  |  |
| `work/caselow/<case>/data` | `policy_tau_by_rule.csv` | 4 | 1 kB |  |  |  |
| `work/caselow/<case>/data` | `policy_tau_by_rule_vintage.csv` | 4 | 1 kB |  |  |  |
| `work/caselow/<case>/data` | `puerto_rico_proxy.csv` | 4 | 18 kB |  |  |  |
| `work/caselow/<case>/data` | `regional_cf_<year>.csv` | 4 | 1.5 MB |  |  |  |
| `work/caselow/<case>/data` | `regional_cf_<year>_corrected.csv` | 4 | 1.7 MB |  |  |  |
| `work/caselow/<case>/data` | `reserve_dividend.csv` | 4 | 0.1 MB |  |  |  |
| `work/caselow/<case>/data` | `reserves_cover.csv` | 4 | 16 kB | output of `reserves`: strategic and commercial oil stocks as a security BUFFER. | reserves |  |
| `work/caselow/<case>/data` | `reserves_resilience.csv` | 4 | 33 kB |  |  |  |
| `work/caselow/<case>/data` | `sd_map_classes.csv` | 4 | 0.5 MB | Fig. 2 class of each land cell (cost and demand terciles) | fig_sd_map | corridor_maps, export_source_data, fig_si_corridors, map_base |
| `work/caselow/<case>/data` | `sd_regimes.csv` | 4 | 0.3 MB |  |  |  |
| `work/caselow/<case>/data` | `sea_cell_cost_check.csv` | 4 | 0.2 MB |  |  |  |
| `work/caselow/<case>/data` | `security_budget.csv` | 4 | 0.4 MB | Fig. 5: share of demand and of net imports replaced at 1-3% of GDP, land ceiling | security_budget | audit_figure3, case_low, corridor_maps, export_source_data |
| `work/caselow/<case>/data` | `security_budget_dac.csv` | 4 | 0.4 MB | output of `security_budget`: how much security does 1%, 2%, 3% of GDP buy? | security_budget |  |
| `work/caselow/<case>/data` | `security_by_fuel.csv` | 4 | 0.1 MB | output of `security`: Phase-1 of the unified security ledger (SECURITY_METHOD.md). | security |  |
| `work/caselow/<case>/data` | `security_events.csv` | 4 | 17 kB | input read by `gap` |  | gap, reserves, security |
| `work/caselow/<case>/data` | `security_index.csv` | 4 | 0.2 MB | value of fuel lost and expected disruption share per economy | fig5a_chain, security | corridor_maps, demand_grid, fig5_chain, fig_si_voll_map |
| `work/caselow/<case>/data` | `security_parity.csv` | 4 | 14 kB | input read by `coreset` |  | coreset |
| `work/caselow/<case>/data` | `security_scenarios.csv` | 4 | 0.1 MB | output of `security`: Phase-1 of the unified security ledger (SECURITY_METHOD.md). | security |  |
| `work/caselow/<case>/data` | `supplier_shares_audit.csv` | 4 | 30 kB | output of `fetch_supplier_mirror`: audit of the top-supplier shares in vulnerability_inputs.csv (2026-10-07): some reporters book part or all of  | fetch_supplier_mirror | fetch_vulnerability |
| `work/caselow/<case>/data` | `supply_demand.csv` | 4 | 0.1 MB | output of `supply_demand`: can each country actually supply its own demand, at what cost, and with what security gain? | supply_demand | case_low, export_source_data, fig5a_chain, fig_main_framework |
| `work/caselow/<case>/data` | `syn150_fig2_cells.csv` | 4 | 1.6 MB |  |  |  |
| `work/caselow/<case>/data` | `syn150_summary.csv` | 4 | 5 kB |  |  |  |
| `work/caselow/<case>/data` | `syn200_fig2_cells.csv` | 4 | 1.6 MB |  |  |  |
| `work/caselow/<case>/data` | `syn200_summary.csv` | 4 | 5 kB |  |  |  |
| `work/caselow/<case>/data` | `tab_paths.tex` | 4 | 5 kB | output of `make_tab_paths`: Supplementary Table tab:paths: (a) median hydrogen cost at the 29 case systems by build year (vintage_fuels.cs | make_tab_paths |  |
| `work/caselow/<case>/data` | `tech_assignment.csv` | 4 | 0.4 MB | output of `make_class_ref`: CLIMATOLOGICAL technology assignment per cell. | make_class_ref | generate_cf_global, generate_cf_hourly, inputs |
| `work/caselow/<case>/data` | `tier_scalars.csv` | 4 | 2 kB | cost multipliers by tier (lowest, central, highest) and cost year | capex_tiers | case_low |
| `work/caselow/<case>/data` | `top_sites.csv` | 4 | 5 kB |  |  |  |
| `work/caselow/<case>/data` | `trajectory_dea_atb.csv` | 4 | 7 kB | input read by `capex_2030low` |  | capex_2030low, capex_tiers |
| `work/caselow/<case>/data` | `trajectory_index.csv` | 4 | 15 kB | input read by `audit_vintage` |  | audit_vintage, capex_2030low, capex_tiers |
| `work/caselow/<case>/data` | `transport_delivered.csv` | 4 | 1.7 MB | output of `transport`: would a demand cell rather buy fuel from a cheaper cell and pay for transport? (2026-09-24: Fig | transport |  |
| `work/caselow/<case>/data` | `transport_summary.csv` | 4 | 4 kB | output of `transport`: would a demand cell rather buy fuel from a cheaper cell and pay for transport? (2026-09-24: Fig | transport | fig_si_corridors, map_layers, transport_flows |
| `work/caselow/<case>/data` | `us_h2_etoh.csv` | 4 | 48 kB |  |  |  |
| `work/caselow/<case>/data` | `vintage_bound.csv` | 4 | 5 kB |  |  |  |
| `work/caselow/<case>/data` | `vintage_check_<year>_Moderate.csv` | 4 | 19 kB |  |  |  |
| `work/caselow/<case>/data` | `vintage_crossing.csv` | 4 | 0.8 MB |  |  |  |
| `work/caselow/<case>/data` | `vintage_fuels.csv` | 4 | 6.4 MB | input read by `audit_vintage` |  | audit_vintage, demand_grid, make_tab_paths |
| `work/caselow/<case>/data` | `vintage_sites.csv` | 4 | 10.5 MB | input read by `audit_vintage` |  | audit_vintage |
| `work/caselow/<case>/data` | `vintage_sites_base.csv` | 4 | 9.7 MB |  |  |  |
| `work/caselow/<case>/data` | `vintage_sites_ghr<year>.csv` | 4 | 10.5 MB |  |  |  |
| `work/caselow/<case>/data` | `vintage_sites_waccm2.csv` | 4 | 9.7 MB |  |  |  |
| `work/caselow/<case>/data` | `vintage_wacc_compare.csv` | 4 | 0.1 MB |  |  |  |
| `work/caselow/<case>/data` | `volatility_by_fuel.csv` | 4 | 2 kB |  |  |  |
| `work/caselow/<case>/data` | `volatility_ratio.csv` | 4 | 17 kB |  |  |  |
| `work/caselow/<case>/data` | `vulnerability_index.csv` | 4 | 24 kB | output of `supply_demand`: can each country actually supply its own demand, at what cost, and with what security gain? | supply_demand | audit_figure3, fig_main_cities, make_fig3_tables, make_paper_tables |
| `work/caselow/<case>/data` | `vulnerability_inputs.csv` | 4 | 0.1 MB | supplier shares and Herfindahl indices of crude, refined and gas imports (UN Comtrade) |  | audit_figure3, fetch_supplier_mirror, fetch_vulnerability, fig5a_chain |
| `work/caselow/<case>/data` | `vulnerability_inputs_gdp<year>.csv` | 4 | 0.1 MB |  |  |  |
| `work/caselow/<case>/data` | `wacc_by_country.csv` | 4 | 57 kB | input read by `inputs` |  | inputs |
| `work/caselow/<case>/data` | `wacc_by_country_v1.csv` | 4 | 30 kB |  |  |  |
| `work/caselow/<case>/data` | `wacc_fix_impact.csv` | 4 | 6 kB |  |  |  |
| `work/caselow/<case>/data` | `water_cost_by_cell.csv` | 4 | 0.6 MB | input read by `fig_pptx_pairs` |  | fig_pptx_pairs, fig_si_feedstocks, inputs |
| `work/caselow/<case>/data` | `wind_class_multiplier.csv` | 4 | 0.6 MB |  |  |  |
| `work/caselow/<case>/jodi` | `GAS_world_NewFormat.zip` | 4 | 6.8 MB |  |  |  |
| `work/caselow/<case>/jodi` | `STAGING_world_NewFormat.csv` | 4 | 51.7 MB | JODI-Gas world database |  | security_budget |
| `work/caselow/<case>/jodi` | `jodi_oil_net.csv` | 4 | 1.3 MB | JODI-Oil net trade |  | security_budget |
| `work/caselow/<case>/jodi` | `oil_primary_<year>.csv` | 8 | 92.7 MB |  |  |  |
| `work/caselow/<case>/jodi` | `oil_secondary_<year>.csv` | 8 | 211.5 MB |  |  |  |
