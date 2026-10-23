"""
Build the stand-alone results console (console/index.html).

Collects every economy's and every cell's results from the four paper cases
into one JSON object and inlines it into template.html, so index.html opens
offline in any browser. Fig. 4a for all economies comes from
lcof.console_export (run it first for 2030, 2040 and 2050).

    python console/build_console.py
"""
import json
import math
from pathlib import Path

import sys

import geopandas as gpd
import numpy as np
import pandas as pd

R = Path(__file__).resolve().parents[1]
W = R / "work" / "caselow"
SD = R / "source_data"
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(R / "scripts"))
YEARS = (2030, 2040, 2050)                 # optimistic cost years of Figs 4-5 (cell cost maps too)
F4YEARS = (2025, 2030, 2040, 2050)         # Figs 4-5 columns; 2025 = central costs, the 2025mid case
CASE = {2025: "2025mid", 2030: "2030", 2040: "2040", 2050: "2050"}
FUELS = ["hydrogen", "ammonia", "e-methane", "methanol", "e-kerosene", "e-diesel", "ethanol"]
DFUELS = ["ammonia", "e-methane", "methanol", "e-kerosene", "e-diesel", "ethanol", "marine"]
GJ_PER_MMBTU = 1.055056
DELIVERY = 1.06          # US$/MMBtu, Fig. 3


def num(x, nd=3):
    if x is None:
        return None
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(x):
        return None
    return round(x, nd)


def geometry():
    g = gpd.read_file(R / "data/grid/naturalearth/ne_10m_admin_0_countries.shp")[["ADMIN", "ISO_A3", "geometry"]]
    g = g[g.ADMIN != "Antarctica"].copy()
    g["geometry"] = g.geometry.simplify(0.15, preserve_topology=True)
    # d3-geo draws spherical polygons and needs clockwise exterior rings (GeoJSON from shapely is anticlockwise,
    # which d3 reads as the whole globe minus the country)
    from shapely.geometry import MultiPolygon, Polygon
    from shapely.geometry.polygon import orient

    def cw(geom):
        if isinstance(geom, Polygon):
            return orient(geom, sign=-1.0)
        if isinstance(geom, MultiPolygon):
            return MultiPolygon([orient(p, sign=-1.0) for p in geom.geoms])
        return geom
    g["geometry"] = g.geometry.apply(cw)
    g = g[~g.geometry.is_empty]
    feats = []
    for _, r in g.iterrows():
        gj = json.loads(gpd.GeoSeries([r.geometry]).to_json())["features"][0]["geometry"]

        def rnd(c):
            return [rnd(x) for x in c] if isinstance(c[0], list) else [round(c[0], 2), round(c[1], 2)]
        gj["coordinates"] = rnd(gj["coordinates"])
        feats.append({"type": "Feature", "properties": {"name": r.ADMIN}, "geometry": gj})
    return {"type": "FeatureCollection", "features": feats}


def cells():
    c1 = pd.read_excel(SD / "Fig1.xlsx", "cell_costs").set_index("cell_id")
    c2 = pd.read_excel(SD / "Fig2.xlsx", "cells").set_index("cell_id")
    dg = pd.read_csv(W / "2025mid/data/demand_fuel_grid.csv", index_col=0)
    fut = {y: pd.read_csv(HERE / f"build/cell_costs_{y}.csv", index_col=0) for y in YEARS}
    out = []
    for cid, r in c1.iterrows():
        q = c2.loc[cid]
        d = dg.loc[cid] if cid in dg.index else None
        rec = {"id": int(cid), "c": r.country, "x": float(r.lon), "y": float(r.lat),
               "cost": [num(r[f + "_usd_mmbtu"], 1) for f in FUELS],
               "mix": num(q.production_cost_usd_mmbtu, 1),
               "dem": num(q.addressable_demand_million_mmbtu_per_yr, 3),
               "cat": q.category, "ct": q.cost_tercile, "dt": q.demand_tercile,
               "cy": {str(y): [num(fut[y].at[cid, f], 1) if cid in fut[y].index else None for f in FUELS]
                      for y in YEARS}}
        if d is not None:
            rec["co2"] = num(d.total_tco2 / 1e6, 4)          # Mt CO2 of the fossil fuels addressed
        out.append(rec)
    return out, c1


def countries(c1):
    rk = pd.read_csv(W / "2025mid/data/fig3_risk_all_countries.csv")
    dg = pd.read_csv(W / "2025mid/data/demand_fuel_grid.csv", index_col=0)
    meta = pd.read_excel(SD / "Fig2.xlsx", "cells").set_index("cell_id")
    dg = dg.join(meta[["country"]], how="inner")
    dem = dg.groupby("country")[[f + "_gj" for f in DFUELS]].sum() / GJ_PER_MMBTU / 1e9   # billion MMBtu
    co2 = dg.groupby("country").total_tco2.sum() / 1e6
    f3 = pd.read_excel(SD / "Fig3.xlsx", "economies").set_index("economy")
    best = c1.groupby("country")[[f + "_usd_mmbtu" for f in FUELS]].min()
    C = {}

    def get(c):
        return C.setdefault(c, {"name": c})
    for _, r in rk.iterrows():
        k = "amm" if r.version == "ammonia" else "ft"
        d = get(r.country)
        d["E_" + k] = num(r.exposure)
        d["H_" + k] = num(r.hhi_effective)
        d["trade_" + k] = r.trade_status if isinstance(r.trade_status, str) else None
        if isinstance(r.note, str):
            d["note_" + k] = r.note
    # fallback import shares: where trade records give no Fig. 3 value, the chain share the security value uses
    # (nitrogen balance, or national gas / oil net import dependence; lcof.fig5a_chain.chain_inputs)
    cq = pd.read_csv(W / "2030/data/chain_q.csv")
    for k, fuel in (("amm", "ammonia"), ("ft", "e-diesel")):
        for _, r in cq[cq.fuel == fuel].iterrows():
            d = get(r.country)
            if d.get("E_" + k) is None and num(r.e) is not None:
                d["E_" + k] = num(r.e)
                d["fb_" + k] = True
    # each fuel's own chain import share as the security value uses it (gas for e-methane, methanol and hydrogen,
    # the oil chain for ethanol); ammonia and diesel + jet keep the Fig. 3 shares above
    for _, r in cq[cq.fuel.isin(["e-methane", "methanol", "ethanol", "hydrogen"])].iterrows():
        if num(r.e) is not None:
            get(r.country).setdefault("Ech", {})[r.fuel] = num(r.e)
    for c, r in best.iterrows():
        d = get(c)
        d["best"] = [num(r[f + "_usd_mmbtu"], 1) for f in FUELS]
        d["best_amm_delivered"] = num(r["ammonia_usd_mmbtu"] + DELIVERY, 1)
    for c, r in dem.iterrows():
        d = get(c)
        d["dem"] = [num(r[f + "_gj"], 4) for f in DFUELS]
        d["dem_tot"] = num(r.sum(), 4)
        d["co2_mt"] = num(co2[c], 2)
    # Fig. 3 domestic-cost box for every economy and fuel (lcof.console_export on the 2025mid case)
    for _, r in pd.read_csv(HERE / "build/fuel_box_2025.csv").iterrows():
        get(r.country).setdefault("box", {})[r.fuel] = [num(r[q], 2) for q in ("p10", "p25", "p50", "p75", "p90")]   # 2026-10-22: 10th-90th whiskers
    # normal / disruption prices and bill for every economy by the paper's rules (lcof.console_export.fig3_prices_all);
    # the core 30 reproduce Fig. 3 and its SI diesel and jet version
    gdp = pd.read_csv(W / "2025mid/data/security_budget.csv", index_col=0).gdp_usd
    core = set(f3.index)
    for k, key in (("amm", "ammonia"), ("ft", "ft")):
        for _, r in pd.read_csv(HERE / f"build/fig3_prices_{key}.csv").iterrows():
            c = r.country
            pm = num(r.bill_bn_usd * 1e9 / gdp[c] * 1000, 4) if c in gdp.index else None
            get(c).setdefault("pr", {})[k] = {
                "n": [num(r[f"normal_p{q:02d}"], 2) for q in (10, 25, 50, 75, 90)],
                "d": [num(r[f"disruption_p{q:02d}"], 2) for q in (10, 25, 50, 75, 90)],
                "bill": num(r.bill_bn_usd, 3), "pm": pm, "core": c in core, "basis": r.basis}
    # the other fuels on their model comparators (lcof.console_export.fig3_prices_other)
    PK = {"e-methane": "em", "methanol": "meoh", "ethanol": "eth", "hydrogen": "h2"}
    for _, r in pd.read_csv(HERE / "build/fig3_prices_other.csv").iterrows():
        c = r.country
        get(c).setdefault("pr", {})[PK[r.fuel]] = {
            "n": [num(r[f"normal_p{q:02d}"], 2) for q in (10, 25, 50, 75, 90)],
            "d": [num(r[f"disruption_p{q:02d}"], 2) for q in (10, 25, 50, 75, 90)],
            "bill": num(r.bill_bn_usd, 3), "pm": num(r.bill_bn_usd * 1e9 / gdp[c] * 1000, 4) if c in gdp.index else None,
            "core": False, "obs": bool(r.observed), "basis": r.basis}
    for c, r in f3.iterrows():
        d = get(c)
        d["core"] = True
        d["f3"] = {k: num(v, 3) if not isinstance(v, str) else v for k, v in r.items() if k != "import_risk_index"}
    imp30 = pd.read_csv(W / "2030/data/security_budget.csv", index_col=0).import_pct > 0
    for y in F4YEARS:
        a = pd.read_csv(HERE / f"build/fig4a_all_{CASE[y]}.csv", index_col=0)
        sb = pd.read_csv(W / f"{CASE[y]}/data/security_budget.csv", index_col=0)
        for c, r in a.iterrows():
            d = get(c)
            imp = bool(imp30.get(c, False))          # fig4_years: importers = net imports in the 2030 case
            d["imp"] = imp
            # justified as in fig4_years._first: net premium at or below the carbon price
            just = bool(np.isfinite(r.net_usd_t) and r.net_usd_t <= r.p_co2_usd_t)
            d.setdefault("f4", {})[str(y)] = {
                "gross": num(r.gross_usd_t, 1), "net": num(r.net_usd_t, 1),
                "margin": num(r.gross_usd_t - r.net_usd_t, 1), "pco2": num(r.p_co2_usd_t, 1),
                "co2": num(r.co2_mt, 2), "E": num(r.chain_import_share), "ret": num(r.retired_share),
                "cov": num(r.cov), "spend": num(r.spend_bn, 2), "sv": num(r.sec_value_bn, 2),
                "imp": bool(imp), "just": just}
        for c, r in sb.iterrows():
            d = get(c)
            imp = r.import_pct > 0
            covered = imp and r.ret_sf_3 >= 0.995
            land = imp and not covered and r.cov_3 >= r.max_cov - 1e-6 and r.max_cov < 1 - 1e-6
            grp = "net exporter" if not imp else "imports covered" if covered else \
                "land binds" if land else "budget binds"
            d.setdefault("f5", {})[str(y)] = {
                "s1": num(r.cov_1 * 100, 1), "s2": num(r.cov_2 * 100, 1), "s3": num(r.cov_3 * 100, 1),
                "land": num(r.max_cov * 100, 1), "imp": num(r.import_pct * 100, 1),
                "r1": num(r.ret_sf_1 * 100, 1) if imp else None, "r3": num(r.ret_sf_3 * 100, 1) if imp else None,
                "grp": grp, "gdp": num(r.gdp_usd / 1e9, 1), "c1": num(r.cov_1, 8)}
    for c, d in C.items():
        f4 = d.get("f4")
        if f4:
            first = [y for y in YEARS if f4.get(str(y), {}).get("just")]      # the paper's columns, 2030-2050
            d["first_just"] = first[0] if first else None
    return C


def orders(C):
    """row orders exactly as the paper draws them (top to bottom)."""
    out = {}
    # Fig. 3 (fig_main_sites._share_order): importers by import share (%, rounded), then the bill (per mille of
    # GDP, one decimal), then the cost ratio (lower on top); net exporters of the chain below, by supply risk
    rk = pd.read_csv(W / "2025mid/data/fig3_risk_all_countries.csv")
    for k, key, fuel in (("amm", "ammonia", "ammonia"), ("ft", "ft", "e-diesel"), ("em", "ammonia", "e-methane"),
                         ("meoh", "ammonia", "methanol"), ("eth", "ft", "ethanol"), ("h2", "ammonia", "hydrogen")):
        V = rk[rk.version == key].set_index("country").supply_risk
        rows = [c for c, d in C.items() if d.get("pr", {}).get(k) and d.get("box", {}).get(fuel)]
        E = {c: (C[c].get("E_" + k) if k in ("amm", "ft") else C[c].get("Ech", {}).get(fuel)) for c in rows}
        imp = [c for c in rows if E[c] is not None and E[c] > 0]
        exp_ = [c for c in rows if E[c] is not None and E[c] <= 0]
        none = [c for c in rows if E[c] is None]

        def key_(c):
            pr = C[c]["pr"][k]
            bill = round(pr["pm"], 1) if pr["pm"] is not None else -1.0
            ratio = C[c]["box"][fuel][2] / pr["n"][2] if pr["n"][2] else math.inf
            return (round(100 * E[c], 0), bill, -ratio)
        imp.sort(key=key_, reverse=True)
        from lcof.coreset import CORE30_LIST
        ci = {c: i for i, c in enumerate(CORE30_LIST)}
        exp_.sort(key=lambda c: (-(V.get(c) if np.isfinite(V.get(c, np.nan)) else -1.0), -ci.get(c, -1), c))
        out["f3" + k] = {"rows": imp + exp_ + sorted(none), "split": len(imp), "nodata": len(imp) + len(exp_)}
    # Fig. 4a (fig4_years.main): importers grouped by the first cost year justified, then by the 2030 net premium;
    # net exporters below, by the 2030 net premium
    f4 = {c: d for c, d in C.items() if d.get("f4", {}).get("2030", {}).get("net") is not None}
    fj = lambda c: C[c].get("first_just") or 9999
    imp = sorted([c for c in f4 if C[c].get("imp")], key=lambda c: (fj(c), C[c]["f4"]["2030"]["net"]))
    exp_ = sorted([c for c in f4 if not C[c].get("imp")], key=lambda c: C[c]["f4"]["2030"]["net"])
    out["f4"] = {"rows": imp + exp_, "split": len(imp)}
    # Fig. 5 (security_budget._figure): imports covered, budget binds, land binds, net exporters; each by the
    # share made at home at 1% of GDP, highest on top
    G = ["imports covered", "budget binds", "land binds", "net exporter"]
    out["f5"] = {}
    for y in F4YEARS:
        rows = [c for c, d in C.items() if d.get("f5", {}).get(str(y))]
        rows.sort(key=lambda c: (G.index(C[c]["f5"][str(y)]["grp"]), -(C[c]["f5"][str(y)]["c1"] or 0)))
        out["f5"][str(y)] = rows
    return out


def macc():
    out = {}
    tot = pd.read_excel(SD / "Fig4.xlsx", "b_totals").set_index("cost_year")
    for y in YEARS:
        b = pd.read_excel(SD / "Fig4.xlsx", f"b_{y}")
        out[str(y)] = {
            "blocks": [[num(r.x_start_gtco2_per_yr, 5), num(r.width_gtco2_per_yr, 5), num(r.net_premium_usd_per_tco2, 1),
                        num(r.cost_premium_usd_per_tco2, 1), r.group, r.region, r.country, r.fuel, r.demand_part]
                       for _, r in b.iterrows()],
            "tot": {k: num(v, 3) for k, v in tot.loc[y].items()}}
    return out


def main():
    cl, c1 = cells()
    f1 = {"box": pd.read_excel(SD / "Fig1.xlsx", "box_statistics").to_dict("records"),
          "routes": pd.read_excel(SD / "Fig1.xlsx", "demand_by_route").to_dict("records"),
          "sectors": pd.read_excel(SD / "Fig1.xlsx", "sector_fuel_map").to_dict("records")}
    data = {"geo": geometry(), "cells": cl, "countries": countries(c1), "macc": macc(), "fig1": f1,
            "fuels": FUELS, "dfuels": DFUELS, "years": [str(y) for y in F4YEARS], "cyears": [str(y) for y in YEARS]}
    data["order"] = orders(data["countries"])
    s = json.dumps(data, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    body = (HERE / "template.html").read_text(encoding="utf-8").replace("/*__DATA__*/null", s)
    # index.html carries D3 inline (vendor/d3.min.js, v7.9.0, ISC licence) so it also opens offline
    tag = '<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>'
    assert body.count(tag) == 1
    d3js = (HERE / "vendor" / "d3.min.js").read_text(encoding="utf-8").replace("</script", "<\\/script")
    html = ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            '</head><body>\n' + body.replace(tag, "<script>" + d3js + "</script>") + '\n</body></html>\n')
    (HERE / "index.html").write_text(html, encoding="utf-8")
    (HERE / "build" / "page_body.html").write_text(body, encoding="utf-8")   # same page without the document shell
    print("index.html", round(len(html) / 1e6, 2), "MB;", len(cl), "cells;", len(data["countries"]), "economies")


if __name__ == "__main__":
    main()
