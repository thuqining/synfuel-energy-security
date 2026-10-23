"""
console_export.py — Fig. 4a for every economy, for the interactive console.

Runs fig5a_chain.compute (same merit order, 1% of GDP, chain security value)
on every economy in security_budget.csv instead of the core 30, and writes
console/build/fig4a_all_<year>.csv. Run per case with run_mod.py:

    python ../work/caselow/run_mod.py ../work/caselow/2030 2030 lcof.console_export
"""
import sys
from pathlib import Path

import pandas as pd

from lcof import fig5a_chain as A, inputs

OUT = Path(__file__).resolve().parents[2] / "console" / "build"


def fuel_boxes():
    """Fig. 3's domestic-cost box for every economy and fuel (2025mid case): the cell with the lowest
    median cost over the 20 weather years, that cell's cost in each weather year, plus Fig. 3's
    US$1/GJ delivery (hydrogen without delivery). e-kerosene shares e-diesel's train."""
    import numpy as np
    from lcof import fig_main_sites as F
    frames = {y: pd.read_csv(inputs.MAPS / f"lcoh_global_{y}{F.SUFFIX}.csv")
              .set_index("cell_id")[["lcoh_usd_gj", "lcoe_usd_mwh"]] for y in F.YEARS}
    meta = inputs.load_meta(2025)
    land = meta[meta.cell_type == "land"]
    avail = frames[F.YEARS[0]].index
    co2 = pd.read_csv(inputs.MAPS / "co2_cost_by_cell.csv").set_index("cell_id").co2_cost
    cand = [i for i in land.index if i in avail]
    groups = land.loc[cand].groupby("country")
    rec = []
    for fuel in ("hydrogen", "ammonia", "e-methane", "methanol", "e-diesel", "ethanol"):
        if fuel == "hydrogen":
            med_all = pd.concat([frames[y].loc[cand, "lcoh_usd_gj"] for y in F.YEARS], axis=1).median(axis=1)
        else:
            med_all = F._cost_all(fuel, frames, meta, cand, co2)
        for c, grp in groups:
            best_id = int(med_all.loc[grp.index].idxmin())
            if fuel == "hydrogen":
                best = np.array([float(frames[y].loc[best_id, "lcoh_usd_gj"]) for y in F.YEARS]) * F.MMB
            else:
                best = F._syn(fuel, frames, meta, best_id, co2) + F.TRANSPORT_USD_GJ * F.MMB
            rec.append(dict(country=c, fuel=fuel, best_cell=best_id, n_weather_years=len(best),
                            **{f"p{q:02d}": float(np.percentile(best, q)) for q in (1, 10, 25, 50, 75, 90, 99)}))
    d = pd.DataFrame(rec).round(3)
    d.to_csv(OUT / "fuel_box_2025.csv", index=False)
    print(d.country.nunique(), "economies x", d.fuel.nunique(), "fuels ->", OUT / "fuel_box_2025.csv")


def fig3_prices_all(key):
    """Fig. 3's normal and disruption price distributions for every economy, by the paper's own
    rules (lcof.fig_main_sites.main): ammonia = the economy's own import price filled from the
    urea-implied price at its own ratio; else the administered-gas route; else the urea-implied
    price at its region's median own/urea ratio (economies outside the core 30 take the region of
    their representative point). Diesel + jet = the economy's own import price filled from its
    import market; economies with no import price of their own stay empty, as in the paper."""
    import numpy as np
    from lcof import fig_main_sites as F, import_prices as IP, global_trajectory as GT
    qa = pd.read_csv(inputs.MAPS / "figure3_country_audit.csv")
    qa = qa[qa.version == key].set_index("country")
    gasdf, g = F.country_gas_monthly()
    imp = F.load_import_prices()
    meta = inputs.load_meta(2025)
    land = meta[meta.cell_type == "land"]
    pts = land.groupby("country")[["lon", "lat"]].mean()
    dg = pd.read_csv(inputs.MAPS / "demand_fuel_grid.csv", index_col=0)
    by_c = dg[["e-diesel_gj", "e-kerosene_gj"]].join(meta[["country"]]).groupby("country").sum()
    dem_gj = (by_c.sum(axis=1) if key == "ft" else
              dg[["ammonia_gj"]].join(meta[["country"]]).groupby("country").ammonia_gj.sum())
    con = F.PR.load(verified=True).ammonia_implied.reindex(gasdf.index).dropna()
    reg_of = {"China": "Asia-Pacific", "Rest of Asia and Oceania": "Asia-Pacific", "Europe": "Europe",
              "Americas": "Americas", "Africa": "Middle East and Africa", "Middle East": "Middle East and Africa"}
    rep_c = {}
    for c, r in IP.NH3_REGION.items():
        rep_c.setdefault(r, c)
    rec = []
    for c in sorted(pts.index):
        try:
            if key == "ft":
                tot = by_c.loc[c].sum() if c in by_c.index else 0.0
                wj = float(by_c.loc[c, "e-kerosene_gj"] / tot) if tot > 0 else 0.0
                own, _ = F.country_buy_monthly(c, 1.0 - wj, wj, imp)
                s, basis = F.country_buy_monthly_filled(c, 1.0 - wj, wj, imp)
                if s.empty:
                    continue
                grey = s.dropna() * F.MMB
            else:
                s_nh3, why = F.country_ammonia_monthly(c, imp)
                own = s_nh3
                if len(s_nh3):
                    ov = pd.concat([s_nh3, con], axis=1, keys=["own", "con"]).dropna()
                    ratio = float((ov.own / ov.con).median()) if len(ov) >= 12 else 1.0
                    grey = s_nh3.combine_first(con * ratio).dropna() * F.MMB
                    basis = f"own import price, filled from the urea-implied price x {ratio:.3f}"
                elif c in F.NH3_GAS_ROUTE:
                    grey = F.fossil_for_fuel("ammonia", gasdf[c], g, c).dropna() * F.MMB
                    basis = "administered national gas price"
                else:
                    reg = IP.NH3_REGION.get(c) or reg_of[GT.region_of(c, *pts.loc[c, ["lon", "lat"]])]
                    k_reg, n_reg = F.nh3_regional_urea_ratio(rep_c[reg], imp)
                    grey = con * k_reg * F.MMB
                    basis = f"urea-implied price x {reg} ratio {k_reg:.3f}"
            grey = F._real_2025(grey)
            quiet, crisis, _ = F.paired_event_price_distributions(grey, key, washout_months=F.FIG3_PRIMARY_WASHOUT)
            if not len(quiet):
                continue
            q = lambda a, p: float(np.percentile(a, p)) if len(a) else np.nan
            rec.append(dict(country=c, version=key, basis=basis, own_share=len(own) / len(grey) if len(grey) else np.nan,
                            # the bill as audit_figure3 defines it: demand x normal median price (2025 US$)
                            bill_bn_usd=float(qa.estimated_quiet_bill_bn_usd[c]) if c in qa.index and np.isfinite(qa.estimated_quiet_bill_bn_usd[c])
                            else dem_gj.get(c, 0.0) * q(quiet, 50) / F.MMB / 1e9,
                            n_quiet=len(quiet), n_crisis=len(crisis),
                            **{f"normal_p{p:02d}": q(quiet, p) for p in (1, 10, 25, 50, 75, 90, 99)},
                            **{f"disruption_p{p:02d}": q(crisis, p) for p in (1, 10, 25, 50, 75, 90, 99)}))
        except Exception as e:                      # noqa: BLE001 - one economy's gap must not stop the rest
            print("  ", key, c, "skipped:", str(e)[:80])
    d = pd.DataFrame(rec).round(3)
    d.to_csv(OUT / f"fig3_prices_{key}.csv", index=False)
    print(key, len(d), "economies ->", OUT / f"fig3_prices_{key}.csv")


def fig3_prices_other():
    """Normal and disruption price distributions for the fuels Fig. 3 does not draw, on the comparator the model
    prices them against (lcof.gap.fossil_for_fuel, security_budget._grey) and Fig. 3's event rules:
    e-methane = the national gas price, hydrogen = grey hydrogen, methanol = gas-based methanol (gas events);
    ethanol = the economy's diesel + jet price, the comparator the paper uses for it (oil events)."""
    import numpy as np
    from lcof import fig_main_sites as F, gap as G
    from lcof.regional_prices import gas_regime
    gasdf, g = F.country_gas_monthly()
    euro = pd.read_csv(inputs.PROJECT / "data" / "prices" / "country_gas_prices.csv")
    eurostat = set(euro[(euro.basis == "pretax") & (euro.usd_gj_lhv > 0)].geo_label)
    meta = inputs.load_meta(2025)
    dg = pd.read_csv(inputs.MAPS / "demand_fuel_grid.csv", index_col=0)
    dem = dg[["e-methane_gj", "methanol_gj", "ethanol_gj"]].join(meta[["country"]]).groupby("country").sum()
    q = lambda a, p: float(np.percentile(a, p)) if len(a) else np.nan

    def gas_basis(c):
        r = gas_regime(c)
        b = {"henry_hub": "Henry Hub (North American market)",
             "producer": "administered producer price",
             "ttf": "national price level (Eurostat) on the TTF monthly shape" if c in eurostat
             else "TTF at the EU median national/TTF ratio (regional estimate)"}.get(
            r, "LNG import price, Japan (World Bank)" if c == "Japan" else "Asian LNG marker (regional estimate)")
        obs = r in ("henry_hub", "producer") or (r == "ttf" and c in eurostat) or c == "Japan"
        if c in G.MIXED_GAS:
            b += ", blended with the regulated domestic price"
            obs = True
        return b, obs
    rec = []
    for c in sorted(gasdf.columns):
        b, obs = gas_basis(c)
        for fuel in ("e-methane", "hydrogen", "methanol"):
            grey = F._real_2025(G.fossil_for_fuel(fuel, gasdf[c], g, c).dropna() * F.MMB)
            quiet, crisis, _ = F.paired_event_price_distributions(grey, "ammonia", washout_months=F.FIG3_PRIMARY_WASHOUT)
            if not len(quiet):
                continue
            d_gj = float(dem.loc[c, f"{fuel}_gj"]) if fuel != "hydrogen" and c in dem.index else np.nan
            rec.append(dict(country=c, fuel=fuel, basis=("" if fuel == "e-methane" else
                                                         "grey hydrogen from " if fuel == "hydrogen" else
                                                         "gas-based methanol from ") + b, observed=obs,
                            bill_bn_usd=d_gj * q(quiet, 50) / F.MMB / 1e9,
                            **{f"normal_p{p:02d}": q(quiet, p) for p in (1, 10, 25, 50, 75, 90, 99)},
                            **{f"disruption_p{p:02d}": q(crisis, p) for p in (1, 10, 25, 50, 75, 90, 99)}))
    # ethanol: the diesel + jet distributions of fig3_prices_ft, with its own demand for the bill
    ft = pd.read_csv(OUT / "fig3_prices_ft.csv").set_index("country")
    for c, r in ft.iterrows():
        d_gj = float(dem.loc[c, "ethanol_gj"]) if c in dem.index else np.nan
        rec.append(dict(country=c, fuel="ethanol", basis="diesel and jet fuel price (the paper's ethanol comparator): " + r.basis,
                        observed=bool(r.own_share > 0), bill_bn_usd=d_gj * r.normal_p50 / F.MMB / 1e9,
                        **{k: r[k] for k in r.index if k.startswith(("normal_p", "disruption_p"))}))
    d = pd.DataFrame(rec).round(3)
    d.to_csv(OUT / "fig3_prices_other.csv", index=False)
    print(d.groupby("fuel").country.count().to_dict(), "->", OUT / "fig3_prices_other.csv")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if inputs.MAPS.parent.name == "2025mid":
        fig3_prices_all("ammonia")
        fig3_prices_all("ft")
        fig3_prices_other()
        fuel_boxes()                 # then, as for the later years, Fig. 4a at 2025 central costs
    orig = A.core_countries
    A.core_countries = lambda avail, n=30: sorted(avail)
    setup = A._setup()
    dem = setup[1]
    try:
        sb = pd.read_csv(inputs.MAPS / "security_budget.csv", index_col=0)
        si = pd.read_csv(inputs.MAPS / "security_index.csv", index_col=0)
        keep = [c for c in sb.index if c in dem.index and c in si.index]
        A.core_countries = lambda avail, n=30: [c for c in keep if c in set(avail)]
        d = A.compute(write=False, verbose=False, setup=setup)
    finally:
        A.core_countries = orig
    year = inputs.MAPS.parent.name
    d.to_csv(OUT / f"fig4a_all_{year}.csv")
    print(year, len(d), "economies ->", OUT / f"fig4a_all_{year}.csv")
    if year == "2025mid":            # 2025 cell costs come from Source Data Fig. 1
        return
    # cell production costs at this case's equipment costs (the layer Figs 4-5 use), US$/MMBtu
    from lcof import params as P
    land, lcof = setup[0], setup[3]
    cc = pd.DataFrame({"hydrogen": land.lcoh_usd_gj * P.MMBTU_PER_GJ}, index=land.index)
    for f in ("ammonia", "e-methane", "methanol", "e-kerosene", "e-diesel", "ethanol"):
        cc[f] = lcof[f].reindex(land.index) * P.MMBTU_PER_GJ
    cc.round(3).to_csv(OUT / f"cell_costs_{year}.csv")
    print(year, len(cc), "cells ->", OUT / f"cell_costs_{year}.csv")


if __name__ == "__main__":
    main()
