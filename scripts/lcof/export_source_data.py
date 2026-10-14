"""
export_source_data.py -- Source Data files for the main figures (one Excel workbook per figure, as Nature
Energy asks): the numbers each panel draws, with a README sheet naming the figure, panels, units and the files
the values come from.

From scripts/:  python -m lcof.export_source_data <out_dir>
Cases: work/caselow/2025mid (Figs 1-3, 2025 central costs) and work/caselow/2030, 2040, 2050 (Figs 4-5,
lowest-tier costs).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from . import inputs
from .coreset import core_countries

W = inputs.PROJECT / "work" / "caselow"
EJ_TO_BN_MMBTU = 0.947817            # 1 EJ = 0.9478 billion MMBtu
YEARS = (2030, 2040, 2050)


def _use_case(case: str, year: int):
    from . import case_low as C
    os.environ.pop("LCOF_TIER", None)
    if "mid" in case:
        os.environ["LCOF_TIER"] = "mid"
    inputs.MAPS = W / case / "data"
    C.apply_params(year)


def _readme(title, rows):
    return pd.DataFrame({"Item": [r[0] for r in rows], "Description": [r[1] for r in rows]}).pipe(
        lambda d: pd.concat([pd.DataFrame({"Item": ["Figure"], "Description": [title]}), d], ignore_index=True))


def _write(path, sheets):
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        for name, df in sheets.items():
            df.to_excel(xw, sheet_name=name[:31], index=False)
    print("wrote", path)


def fig1(out):
    _use_case("2025mid", 2025)
    from . import fig_main_framework as F, supply_demand as SD
    keep = {}
    orig = SD.lcof_cells

    def capture(land, co2):
        res = orig(land, co2)
        keep["land"], keep["lcof"] = land.copy(), res.copy()
        return res
    SD.lcof_cells = capture
    try:
        bars = F._cost_ranges()
    finally:
        SD.lcof_cells = orig
    box = pd.DataFrame([dict(fuel=b[0], p01_usd_mmbtu=b[2], p25_usd_mmbtu=b[7], median_usd_mmbtu=b[3],
                             p75_usd_mmbtu=b[8], p99_usd_mmbtu=b[4]) for b in bars]).round(2)
    # the figure's trading-unit label under each box: median (interquartile range)
    box["trading_unit_median_iqr"] = [str(b[6]).replace("\\$", "$").replace("–", "-") for b in bars]
    # the dots in each sector: the fuels that can serve it (Fig. 1, right; demand_grid.FUEL_MAP)
    sectors = pd.DataFrame([
        ("agriculture", "ammonia"),
        ("buildings + industry", "e-methane"), ("buildings + industry", "e-jet / e-diesel"),
        ("chemicals + shipping", "methanol"), ("chemicals + shipping", "ammonia"),
        ("aviation", "e-jet / e-diesel"),
        ("road transport", "ethanol"), ("road transport", "e-jet / e-diesel")], columns=["sector", "fuel"])
    from . import params as P
    land, lcof = keep["land"], keep["lcof"]
    cells = pd.DataFrame({"cell_id": land.index, "country": land.country.to_numpy(),
                          "lon": land.lon.to_numpy(), "lat": land.lat.to_numpy(),
                          "hydrogen_usd_mmbtu": land.lcoh_usd_gj.to_numpy() * P.MMBTU_PER_GJ})
    for f in ("ammonia", "e-methane", "methanol", "e-kerosene", "e-diesel", "ethanol"):
        cells[f"{f}_usd_mmbtu"] = lcof[f].reindex(land.index).to_numpy() * P.MMBTU_PER_GJ
    mix, tot = F._demand_mix()
    dem = pd.DataFrame({"route": [m[0] for m in mix],
                        "addressable_demand_bn_mmbtu_per_yr": [m[2] * EJ_TO_BN_MMBTU for m in mix]})
    dem["share_pct"] = 100 * dem.addressable_demand_bn_mmbtu_per_yr / dem.addressable_demand_bn_mmbtu_per_yr.sum()
    _write(out / "Fig1.xlsx", {
        "README": _readme("Fig. 1 - production framework, costs and addressable demand (2025 central costs)", [
            ("box_statistics", "Middle, box plots: 1st, 25th, 50th, 75th and 99th percentiles across the 2,740 land cells "
                               "of each cell's median levelized cost over 20 weather years; US$ per MMBtu, lower heating "
                               "value. trading_unit_median_iqr is the label under each box: median (interquartile range) "
                               "in the unit in which the fuel is traded"),
            ("cell_costs", "Levelized cost of hydrogen and of each fuel for every land cell (the values behind the boxes); "
                           "the e-jet / e-diesel box pools e-kerosene and e-diesel"),
            ("demand_by_route", "Right, bar: addressable demand of the 139 economies by production route, billion MMBtu "
                                "per year (total 76.1), and its share in percent; marine fuel counted 70% methanol and "
                                "30% ammonia"),
            ("sector_fuel_map", "Right, dots: the fuels that can serve each end use sector"),
            ("Left", "The production chain (left) is a schematic; its model is described in the Methods"),
            ("Source", "work/caselow/2025mid/data (lcoh_global_<year>_reg.csv, co2_cost_by_cell.csv, "
                       "global_trajectory_countries.csv); code lcof.fig_main_framework")]),
        "box_statistics": box, "cell_costs": cells.round(3), "demand_by_route": dem.round(2),
        "sector_fuel_map": sectors})


def fig2(out):
    _use_case("2025mid", 2025)
    c = pd.read_csv(inputs.MAPS / "sd_map_classes.csv")
    meta = inputs.load_meta(2025)
    c = c.join(meta[["lon", "lat"]], on="cell_id")
    cost_lab = {2: "low", 1: "middle", 0: "high"}       # s = 2 is the cheapest cost tercile
    dem_lab = {0: "low", 1: "middle", 2: "high"}
    d = pd.DataFrame({"cell_id": c.cell_id, "country": c.country, "lon": c.lon, "lat": c.lat,
                      "production_cost_usd_mmbtu": c.cost, "addressable_demand_million_mmbtu_per_yr": c.dem,
                      "cost_tercile": c.s.map(cost_lab), "demand_tercile": c.d.map(dem_lab)})
    d["category"] = np.where((c.s == 2) & (c.d == 2), "build-first",
                    np.where((c.s == 2) & (c.d == 0), "export-oriented",
                    np.where((c.s == 0) & (c.d == 2), "supply-strained",
                    np.where((c.s == 0) & (c.d == 0), "limited near-term potential", "intermediate"))))
    _write(out / "Fig2.xlsx", {
        "README": _readme("Fig. 2 - supply-demand map (2025 central costs)", [
            ("cells", "Every land cell: demand-weighted levelized cost of the fuels its market uses (US$ per MMBtu), "
                      "addressable demand (million MMBtu per year), tercile classes and the nine-way category"),
            ("Note", "Terciles of cost and demand across land cells; demand terciles over cells with more than 0.06 "
                     "million MMBtu per year (the rest join the lowest class). Thresholds: US$83 and US$111 per MMBtu "
                     "for cost, 1.5 and 15 million MMBtu per year for demand. The map colors each cell by its "
                     "category (cost tercile x demand tercile); map boundaries are smoothed for display only"),
            ("Source", "work/caselow/2025mid/data/sd_map_classes.csv; code lcof.supply_demand, lcof.fig_sd_map")]),
        "cells": d.round(3)})


def fig3(out):
    s = pd.read_csv(W / "2025mid" / "data" / "core30_sites_ammonia.csv").rename(
        columns={"crisis_p98_mmbtu": "crisis_p99_mmbtu"})
    cols = {"country": "economy",
            "best_p01_mmbtu": "green_ammonia_p01", "best_p25_mmbtu": "green_ammonia_p25",
            "best_med_mmbtu": "green_ammonia_median", "best_p75_mmbtu": "green_ammonia_p75",
            "best_p99_mmbtu": "green_ammonia_p99",
            "quiet_p01_mmbtu": "normal_price_p01", "quiet_p25_mmbtu": "normal_price_p25",
            "quiet_med_mmbtu": "normal_price_median", "quiet_p75_mmbtu": "normal_price_p75",
            "quiet_p99_mmbtu": "normal_price_p99",
            "crisis_p01_mmbtu": "disruption_price_p01", "crisis_p25_mmbtu": "disruption_price_p25",
            "crisis_med_mmbtu": "disruption_price_median", "crisis_p75_mmbtu": "disruption_price_p75",
            "crisis_p99_mmbtu": "disruption_price_p99",
            "supply_risk": "import_risk_index", "import_exposure_pct": "import_exposure_pct",
            "quiet_bill_bn_usd": "ammonia_market_bn_usd_per_yr", "buy_basis": "price_basis"}
    d = s[list(cols)].rename(columns=cols)
    gdp = pd.read_csv(W / "2025mid" / "data" / "security_budget.csv", index_col=0).gdp_usd
    d.insert(d.columns.get_loc("ammonia_market_bn_usd_per_yr") + 1, "ammonia_market_per_mille_gdp",
             1e3 * d.ammonia_market_bn_usd_per_yr * 1e9 / d.economy.map(gdp))
    _write(out / "Fig3.xlsx", {
        "README": _readme("Fig. 3 - ammonia prices during disruptions vs domestic green ammonia (2025 central costs)", [
            ("economies", "Per economy: green ammonia from the lowest-cost cell incl. US$1.06/MMBtu delivery, across 20 "
                          "weather years; matched national ammonia price in normal months and in disruption months "
                          "(1st, 25th, 50th, 75th, 99th percentiles); all in 2025 US$ per MMBtu (LHV). Import risk index "
                          "R_c = sqrt(E_c H_c) from 0 to 1 (first right column); annual ammonia market at the normal "
                          "price, in billion US$ and per mille of GDP (second right column); import_exposure_pct = 0 "
                          "marks the economies below the dashed line (no net imports in the ammonia supply chain)"),
            ("Units", "Prices and costs US$ per MMBtu; 1 t of ammonia = 17.6 MMBtu (LHV)"),
            ("Source", "work/caselow/2025mid/data/core30_sites_ammonia.csv, figure3_country_audit.csv; code "
                       "lcof.fig_main_sites, lcof.audit_figure3")]),
        "economies": d.round(3)})


def _blocks(p, yr, tj):
    """the blocks of the Fig. 4b abatement-cost curve, as lcof.fig5_chain._curve_to_zero builds them"""
    from .fig5_chain import _CAP
    pi, pi_r = p[f"pi_{yr}"].to_numpy(), p[f"pi_rest_{yr}"].to_numpy()
    w, ef, imp = np.clip(p.w_usd_gj.to_numpy(), 0, None), p.ef.to_numpy(), p.imp_gj.to_numpy()
    sec = pd.concat([
        pd.DataFrame({"country": p.country, "fuel": p.fuel, "part": "net imports", "wd": imp * ef / 1e9,
                      "c": (pi - w) / ef, "prem": pi / ef, "region": p.region}),
        pd.DataFrame({"country": p.country, "fuel": p.fuel, "part": "rest of demand",
                      "wd": (p.dem_gj.to_numpy() - imp) * ef / 1e9, "c": pi_r / ef, "prem": pi_r / ef,
                      "region": p.region})])
    sec = sec[sec.wd > 0].copy()
    sec["sec_only"] = (sec.prem > 0) & (sec.c <= 0)
    pos = sec[(sec.c > 0) & (sec.c <= _CAP)].sort_values("c", kind="stable")
    neg = sec[sec.c <= 0]
    neg = pd.concat([neg[~neg.sec_only].sort_values("c", kind="stable"), neg[neg.sec_only].sort_values("c", kind="stable")])
    bars = pd.concat([neg.assign(dear=False), pos.assign(dear=True)]).reset_index(drop=True)
    bars["x0"] = bars.wd.cumsum() - bars.wd
    t = tj.set_index("year")
    assert abs(float(neg.wd.sum()) - float(t.sec_gt[yr])) < 1e-6
    bars["group"] = np.where(bars.dear, "costlier with security value",
                    np.where(bars.sec_only, "pays off with security value", "pays off without security value"))
    return pd.DataFrame({"x_start_gtco2_per_yr": bars.x0, "width_gtco2_per_yr": bars.wd,
                         "net_premium_usd_per_tco2": bars.c, "cost_premium_usd_per_tco2": bars.prem,
                         "group": bars.group, "region": bars.region, "country": bars.country, "fuel": bars.fuel,
                         "demand_part": bars.part})


def _above_cap(p, yr=2025):
    """CO2 of the blocks whose net premium lies above the top of the Fig. 4b axis (named in the caption)"""
    from .fig5_chain import _CAP
    pi, pi_r = p[f"pi_{yr}"].to_numpy(), p[f"pi_rest_{yr}"].to_numpy()
    w, ef, imp = np.clip(p.w_usd_gj.to_numpy(), 0, None), p.ef.to_numpy(), p.imp_gj.to_numpy()
    wd = np.concatenate([imp * ef / 1e9, (p.dem_gj.to_numpy() - imp) * ef / 1e9])
    c = np.concatenate([(pi - w) / ef, pi_r / ef])
    return float(wd[(wd > 0) & (c > _CAP)].sum())


def fig4(out):
    sheets, totals = {}, []
    for y in YEARS:
        d = pd.read_csv(W / str(y) / "data" / "fig5a_chain.csv")
        sb = pd.read_csv(W / str(y) / "data" / "security_budget.csv", index_col=0)
        a = pd.DataFrame({"economy": d.country,
                          "net_importer": d.country.map(sb.import_pct) > 0,
                          "chain_import_share_pct": d.chain_import_share * 100,
                          "imports_replaced_pct": d.retired_share * 100,
                          "co2_displaced_mt_per_yr": d.co2_mt,
                          "cost_premium_usd_per_tco2": d.gross_usd_t,
                          "security_margin_usd_per_tco2": d.gross_usd_t - d.net_usd_t,
                          "net_premium_usd_per_tco2": d.net_usd_t,
                          "carbon_price_usd_per_tco2": d.p_co2_usd_t})
        a["justified"] = a.net_premium_usd_per_tco2 <= a.carbon_price_usd_per_tco2
        sheets[f"a_{y}"] = a.round(2)
        p = pd.read_csv(W / str(y) / "data" / "fig5b_chain_pairs.csv")
        tj = pd.read_csv(W / str(y) / "data" / "fig5b_chain_trajectory.csv")
        sheets[f"b_{y}"] = _blocks(p, 2025, tj).round(5)
        t = tj.set_index("year").loc[2025]
        totals.append(dict(cost_year=y, co2_displaced_with_security_gtco2=t.sec_gt,
                           co2_displaced_cost_only_gtco2=t.cost_gt,
                           co2_above_axis_top_gtco2=_above_cap(p)))
    sheets["b_totals"] = pd.DataFrame(totals).round(3)
    # rows of panel a are grouped by the first cost year in which the portfolio is justified
    first = {}
    for y in YEARS:
        a = sheets[f"a_{y}"]
        for e in a.economy[a.justified]:
            first.setdefault(e, y)
    for y in YEARS:
        sheets[f"a_{y}"]["first_justified_cost_year"] = sheets[f"a_{y}"].economy.map(first).astype("Int64")
    readme = _readme("Fig. 4 - security value, deployment and CO2 abatement (lowest-tier costs 2030, 2040, 2050)", [
        ("a_<year>", "Panel a: portfolio that up to 1% of GDP a year buys in each of the 30 economies; cost premium, "
                     "security margin and net premium in US$ per tonne of CO2 displaced, carbon price in force; "
                     "justified when the net premium does not exceed the carbon price (green ring); the security "
                     "margin is the arrow from the open to the filled circle. first_justified_cost_year groups the "
                     "rows (empty: not justified at any cost year); net_importer = False marks the economies below "
                     "the dashed line"),
        ("b_<year>", "Panel b: blocks of the abatement-cost curve of addressable demand in 139 economies (each country-"
                     "fuel pair split into net imports, at the net premium, and the rest of demand); x from x_start, "
                     "width in GtCO2 per year, height in US$ per tCO2. The figure clips heights below -US$700 and shows "
                     "blocks up to US$300"),
        ("b_totals", "CO2 displaced with the security value and on cost alone (dashed and dotted lines), and the "
                     "CO2 of blocks above the top of the axis (US$300 per tCO2), in GtCO2 per year"),
        ("Source", "work/caselow/<year>/data/fig5a_chain.csv, fig5b_chain_pairs.csv, fig5b_chain_trajectory.csv; "
                   "code lcof.fig5a_chain, lcof.fig5_chain, lcof.fig4_years")])
    _write(out / "Fig4.xlsx", {"README": readme, **sheets})


def fig5(out):
    sheets = {}
    for y in YEARS:
        sb = pd.read_csv(W / str(y) / "data" / "security_budget.csv", index_col=0)
        d = sb.reindex([c for c in core_countries(sb.index) if c in sb.index])
        imp = d.import_pct > 0
        covered = imp & (d.ret_sf_3 >= 0.995)
        land = imp & ~covered & (d.cov_3 >= d.max_cov - 1e-6) & (d.max_cov < 1 - 1e-6)
        grp = np.where(~imp, "net exporter", np.where(covered, "imports covered",
                       np.where(land, "land binds", "budget binds")))
        sheets[str(y)] = pd.DataFrame({
            "economy": d.index, "group": grp,
            "share_made_at_home_1pct_gdp": d.cov_1 * 100, "share_made_at_home_2pct_gdp": d.cov_2 * 100,
            "share_made_at_home_3pct_gdp": d.cov_3 * 100, "land_ceiling_pct": d.max_cov * 100,
            "net_import_share_pct": d.import_pct * 100,
            "imports_replaced_1pct_gdp": d.ret_sf_1 * 100, "imports_replaced_3pct_gdp": d.ret_sf_3 * 100,
            # starred in the figure: the tick is one minus domestic production over consumption
            "no_net_trade_record": d.index.isin(["Kenya", "Dominican Republic", "Madagascar"])}).round(2)
    readme = _readme("Fig. 5 - fiscal capacity and land availability (lowest-tier costs 2030, 2040, 2050)", [
        ("<year>", "Per economy: share of addressable fuel demand made at home with annual support for the cost "
                   "premium capped at 1%, 2% and 3% of GDP (bars), land ceiling (5% of screened eligible land, at most "
                   "2% of territory; end caps), net import share of oil- and gas-based fuels (red ticks), share of net "
                   "imports replaced, and the group of the figure; all in percent. Hatching is the part of the land "
                   "ceiling above the 3%-of-GDP bar. no_net_trade_record = True marks the starred economies, whose "
                   "tick is one minus domestic production over consumption. Sheets 2030, 2040 and 2050 are panels "
                   "a, b and c"),
        ("Source", "work/caselow/<year>/data/security_budget.csv; code lcof.security_budget, lcof.fig5_years")])
    _write(out / "Fig5.xlsx", {"README": readme, **sheets})


def main(out_dir="source_data"):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for f in (fig1, fig2, fig3, fig4, fig5):
        f(out)


if __name__ == "__main__":
    main(*sys.argv[1:])
