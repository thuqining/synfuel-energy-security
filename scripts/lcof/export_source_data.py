"""
export_source_data.py -- Source Data files for the main figures (one Excel workbook per figure, as Nature
Energy asks): the numbers each panel draws, with a README sheet naming the figure, panels, units and the files
the values come from.

From scripts/:  python -m lcof.export_source_data <out_dir>
Cases: work/caselow/2025mid (Figs 1-3, 2025 central costs) and work/caselow/2030, 2040, 2050 (Figs 4-6,
lowest-tier costs; Fig. 6 at 2030). Figs 3, 4b and 6b also read the console data (console/index.html), as the
figures do (2026-10-22: six-figure layout).
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


def _console():
    """2026-10-22: Figs 3-6 draw from the console data (console/index.html), so the Source Data read it too"""
    import json
    t = (inputs.PROJECT / "console" / "index.html").read_text(encoding="utf-8")
    return json.JSONDecoder().raw_decode(t[t.index("const DATA=") + 11:])[0]


P5 = ("p10", "p25", "p50", "p75", "p90")


def fig3(out):
    from .fig35_core import fig3_classes
    D = _console()
    C = D["countries"]
    k139 = pd.read_csv(W / "2030" / "data" / "security_budget.csv", index_col=0).index
    core = set(pd.read_csv(W / "2030" / "data" / "fig5a_chain.csv", index_col=0).index)
    own = pd.read_csv(inputs.PROJECT / "console" / "build" / "fig3_prices_ammonia.csv", index_col=0).own_share
    cat, _, lab, _ = fig3_classes()
    rows = [c for c in D["order"]["f3amm"]["rows"] if c in k139 and C[c].get("box", {}).get("ammonia")
            and C[c].get("pr", {}).get("amm")]

    def row(c):
        d, pr, bx, e = C[c], C[c]["pr"]["amm"], C[c]["box"]["ammonia"], C[c].get("E_amm")
        r = {"economy": c, "core_30": c in core,
             "group": "net exporter" if (e is None or e <= 0) else ("imports the whole chain" if e >= 0.995
                                                                   else "imports part of the chain"),
             "import_share_pct": None if e is None else 100 * e,
             "ammonia_bill_bn_usd_per_yr": pr["bill"], "ammonia_bill_per_mille_gdp": pr["pm"],
             "own_import_price_series": bool(own.get(c, 0) > 0), "price_basis": pr["basis"]}
        r.update({f"green_ammonia_{p}": v for p, v in zip(P5, bx)})
        r.update({f"normal_price_{p}": v for p, v in zip(P5, pr["n"])})
        r.update({f"disruption_price_{p}": v for p, v in zip(P5, pr["d"])})
        r["panel_b_class"] = lab[cat[c]] if c in cat else None
        return r
    a = pd.DataFrame([row(c) for c in rows if c in core])
    b = pd.DataFrame([row(c) for c in rows])
    _write(out / "Fig3.xlsx", {
        "README": _readme("Fig. 3 - ammonia prices during disruptions vs domestic green ammonia (2025 central costs)", [
            ("a", "Panel a, the 30 representative economies in the order of the figure: green ammonia from the "
                  "economy's lowest-cost cell incl. US$1.06/MMBtu delivery across 20 weather years (box: 25th-75th, "
                  "whiskers: 10th-90th percentiles); the matched national ammonia price in normal months (gray bar) "
                  "and in disruption months (orange line, diamond at the median), 10th-90th percentiles; all in 2025 "
                  "US$ per MMBtu (LHV). Rows above the panel: import share of the ammonia supply chain E_c (%) and "
                  "the annual ammonia bill at normal prices (per mille of GDP). own_import_price_series = False "
                  "marks the asterisked economies"),
            ("b", "Panel b, all 139 economies, same columns; panel_b_class gives the map class (median cost of "
                  "domestic green ammonia below the median or the 90th percentile of the disruption price; economies "
                  "that import none of their ammonia supply chain are net exporters)"),
            ("Units", "Prices and costs US$ per MMBtu; 1 t of ammonia = 17.6 MMBtu (LHV)"),
            ("Source", "console/index.html (built by console/build_console.py from lcof.console_export), "
                       "console/build/fig3_prices_ammonia.csv; code lcof.fig35_core, lcof.fig3_cols")]),
        "a": a.round(3), "b": b.round(3)})


def _blocks(p, yr, tj):
    """the blocks of the Fig. 5 abatement-cost curve, as lcof.fig5_chain._curve_to_zero builds them"""
    from .fig5_chain import _CAP
    pi, pi_r = p[f"pi_{yr}"].to_numpy(), p[f"pi_rest_{yr}"].to_numpy()
    w, ef, imp = np.clip(p.w_usd_gj.to_numpy(), 0, None), p.ef.to_numpy(), p.imp_gj.to_numpy()
    sec = pd.concat([
        pd.DataFrame({"country": p.country, "fuel": p.fuel, "part": "imported supply", "wd": imp * ef / 1e9,
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
    """CO2 of the blocks whose net premium lies above the top of the Fig. 5 axis (named in the caption)"""
    from .fig5_chain import _CAP
    pi, pi_r = p[f"pi_{yr}"].to_numpy(), p[f"pi_rest_{yr}"].to_numpy()
    w, ef, imp = np.clip(p.w_usd_gj.to_numpy(), 0, None), p.ef.to_numpy(), p.imp_gj.to_numpy()
    wd = np.concatenate([imp * ef / 1e9, (p.dem_gj.to_numpy() - imp) * ef / 1e9])
    c = np.concatenate([(pi - w) / ef, pi_r / ef])
    return float(wd[(wd > 0) & (c > _CAP)].sum())


def fig4(out):
    from .fig4a_all import load
    sheets = {}
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
    first = {}
    for y in YEARS:
        a = sheets[f"a_{y}"]
        for e in a.economy[a.justified]:
            first.setdefault(e, y)
    for y in YEARS:
        sheets[f"a_{y}"]["first_justified_cost_year"] = sheets[f"a_{y}"].economy.map(first).astype("Int64")
    data, imps, exps, fy = load()
    sheets["b"] = pd.DataFrame(
        [{"economy": c, "net_importer": True,
          "first_justified_cost_year": None if fy[c] == 9999 else fy[c]} for c in imps]
        + [{"economy": c, "net_importer": False, "first_justified_cost_year": None} for c in exps]
    ).astype({"first_justified_cost_year": "Int64"})
    for y in YEARS:
        dy = data[y]
        sheets["b"][f"security_margin_usd_per_tco2_{y}"] = sheets["b"].economy.map(dy.gross_usd_t - dy.net_usd_t).round(2)
        sheets["b"][f"net_premium_usd_per_tco2_{y}"] = sheets["b"].economy.map(dy.net_usd_t).round(2)
    sheets["b"]["carbon_price_usd_per_tco2"] = sheets["b"].economy.map(data[2030].p_co2_usd_t).round(2)
    readme = _readme("Fig. 4 - security value per tonne of CO2 displaced (lowest-tier costs 2030, 2040, 2050; GDP "
                     "projected to each cost year)", [
        ("a_<year>", "Panel a: portfolio that up to 1% of GDP a year buys in each of the 30 economies; cost premium "
                     "(open marker), security margin (green line) and net premium (filled marker) in US$ per tonne of "
                     "CO2 displaced, carbon price in force (magenta line); justified (green ring) when the net "
                     "premium does not exceed the carbon price. Markers by cost year: circles 2030, squares 2040, "
                     "triangles 2050. first_justified_cost_year groups the rows (empty: not justified by 2050); "
                     "net_importer = False marks the net oil and gas exporters shown separately"),
        ("b", "Panel b: first cost year in which the 1%-of-GDP portfolio is justified, for all 139 economies "
              "(empty for net importers: not justified by 2050; net exporters shown separately), with the security "
              "margin and net premium of each cost year"),
        ("Source", "work/caselow/<year>/data/fig5a_chain.csv, security_budget.csv; console/build/fig4a_all_<year>.csv; "
                   "code lcof.fig5a_chain, lcof.fig4a_all, lcof.fig4_core")])
    _write(out / "Fig4.xlsx", {"README": readme, **sheets})


def fig5(out):
    sheets, totals = {}, []
    for y in YEARS:
        p = pd.read_csv(W / str(y) / "data" / "fig5b_chain_pairs.csv")
        tj = pd.read_csv(W / str(y) / "data" / "fig5b_chain_trajectory.csv")
        sheets[str(y)] = _blocks(p, 2025, tj).round(5)
        t = tj.set_index("year").loc[2025]
        totals.append(dict(cost_year=y, co2_displaced_with_security_gtco2=t.sec_gt,
                           co2_displaced_cost_only_gtco2=t.cost_gt,
                           security_gain_gtco2=t.sec_gt - t.cost_gt,
                           co2_above_axis_top_gtco2=_above_cap(p)))
    readme = _readme("Fig. 5 - abatement cost curves of addressable demand in 139 economies (lowest-tier costs "
                     "2030, 2040, 2050)", [
        ("<year>", "Blocks of the curve: each country-fuel pair split into its imported supply (demand times the "
                   "import share of its supply chain), at the cost premium less the security margin, and the rest "
                   "of its demand, at the cost premium; x from x_start, width in GtCO2 per year, height (net premium) "
                   "in US$ per tCO2; group: pays off without security value (solid), with security value (hatched), "
                   "costlier (gray). The figure shows blocks up to US$300 per tCO2, cuts the axis at -US$900 per "
                   "tCO2, and compresses the shared x axis 12-fold beyond 2 GtCO2 per year"),
        ("totals", "CO2 displaced with the security value (dashed line) and on fuel cost alone (dotted line), their "
                   "difference, and the CO2 of blocks above US$300 per tCO2, in GtCO2 per year"),
        ("Source", "work/caselow/<year>/data/fig5b_chain_pairs.csv, fig5b_chain_trajectory.csv; code "
                   "lcof.fig5_chain, lcof.fig_macc")])
    _write(out / "Fig5.xlsx", {"README": readme, **sheets, "totals": pd.DataFrame(totals).round(3)})


def fig6(out):
    from .fig35_core import fig5_classes
    D = _console()
    sb = pd.read_csv(W / "2030" / "data" / "security_budget.csv", index_col=0)
    core = set(pd.read_csv(W / "2030" / "data" / "fig5a_chain.csv", index_col=0).index)
    rows = [c for c in D["order"]["f5"]["2030"] if c in core]
    d = sb.reindex(rows)
    imp = d.import_pct > 0
    covered = imp & (d.ret_sf_3 >= 0.995)
    land = imp & ~covered & (d.cov_3 >= d.max_cov - 1e-6) & (d.max_cov < 1 - 1e-6)
    grp = np.where(~imp, "net exporter", np.where(covered, "imports covered",
                   np.where(land, "land binds", "budget binds")))
    a = pd.DataFrame({
        "economy": d.index, "group": grp,
        "share_made_at_home_1pct_gdp": d.cov_1 * 100, "share_made_at_home_2pct_gdp": d.cov_2 * 100,
        "share_made_at_home_3pct_gdp": d.cov_3 * 100, "land_ceiling_pct": d.max_cov * 100,
        "net_import_share_pct": d.import_pct * 100,
        "imports_replaced_1pct_gdp": d.ret_sf_1 * 100, "imports_replaced_3pct_gdp": d.ret_sf_3 * 100,
        "gdp_2030_bn_usd": d.gdp_usd / 1e9}).round(2)
    cls = fig5_classes("2030")[0]
    b = pd.DataFrame({"economy": list(cls), "group": list(cls.values())})
    b["core_30"] = b.economy.isin(core)
    readme = _readme("Fig. 6 - fiscal capacity and land availability (lowest-tier 2030 costs, GDP projected to 2030)", [
        ("a", "Panel a, the 30 economies in the order of the figure: share of addressable fuel demand made at home "
              "with annual support for the cost premium capped at 1%, 2% and 3% of GDP (bars), land ceiling (5% of "
              "screened eligible land, at most 2% of territory; black end caps; the hatched part is unused land "
              "beyond the 3%-of-GDP bar), net import share of oil- and gas-based fuels (red triangles), share of net "
              "imports replaced, and the group named by the brackets on the right; all in percent"),
        ("b", "Panel b, all 139 economies by the same groups (map)"),
        ("Source", "work/caselow/2030/data/security_budget.csv; console/index.html; code lcof.security_budget, "
                   "lcof.fig35_core")])
    _write(out / "Fig6.xlsx", {"README": readme, "a": a, "b": b})


def main(out_dir="source_data"):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for f in (fig1, fig2, fig3, fig4, fig5, fig6):
        f(out)


if __name__ == "__main__":
    main(*sys.argv[1:])
