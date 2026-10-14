"""supply_demand.py — can each country actually supply its own demand,
at what cost, and with what security gain? 

Per country:
  potential  = sum over land cells of the maximum firm-hydrogen output
               that fits on the cell's usable land, using the cell's own
               Stage-1 sizing (MW_pv + MW_wind per MW_H2) and
               conservative land-availability / power-density factors
  demand     = reconciled addressable synthetic-fuel demand (H2-
               equivalent, via fuel-specific H2 intensities)
  ratio      = potential / demand      (self-sufficiency)
  premium    = best-site LCOF - grey rival, per fuel, demand-weighted
  cost       = premium x demand        ($bn/yr and % of GDP)
  security   = ESD retired if the domestic flow replaces at-risk imports

Outputs data/cost/supply_demand.csv, tab_sd.tex (main text) and
fig_supply_demand.(pdf|png).

From scripts/:  conda run -n synfuel python -u -m lcof.supply_demand
"""
from __future__ import annotations

import os
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

mpl.use("Agg")

from . import inputs
from .fig_main_cost import MM, NAT_RC, FUELS
from .fig_pptx_pairs import OUT, SUFFIX
from .coreset import core_countries

mpl.rcParams.update(NAT_RC)

BLUE, ORANGE, GREEN, RED, GREY = ("#0072B2", "#E69F00", "#009E73",
                                  "#D55E00", "#9AA5AF")
UMM = 1.0551
R_EARTH = 6371.0
LAND_AVAIL = 0.02          # share of cell land usable for wind+PV (conservative)
PV_MW_KM2 = 30.0           # MW_dc per km2 (utility PV, ground-mount)
WIND_MW_KM2 = 3.0          # MW per km2 (onshore array density)
SPLIT_PV = 0.5             # of the usable land, half to PV, half to wind
GJ_PER_MWH = 3.6
# hydrogen intensity of each fuel, GJ_H2 per GJ_fuel: 1 / eta_syn from
# params, the same source the cascade and the supply-demand map use
from . import params as P
MU_H2 = {f: 1.0 / P.FUELS[f]["eta_syn"] for f in FUELS}
BS = chr(92)
NL = chr(10)
EOL = BS + BS
SHORT = {"United States of America": "United States",
         "United Kingdom of Great Britain and Northern Ireland":
         "United Kingdom", "United Arab Emirates": "UAE",
         "Russian Federation": "Russia",
         "Dominican Republic": "Dominican Rep."}


def cell_area_km2(lat: pd.Series, dlat: float = 2.5,
                  dlon: float = 2.5) -> pd.Series:
    la = np.deg2rad(lat)
    return (np.deg2rad(dlon) * R_EARTH * np.cos(la)
            * np.deg2rad(dlat) * R_EARTH)


def firm_h2_potential_gj(land: pd.DataFrame, land_avail=None,
                         scale: float = 1.0) -> pd.Series:
    """Land-limited firm hydrogen per cell, GJ/yr. The usable share of
    the cell is divided between PV and wind in the cell's OWN optimal
    capacity ratio (cap_pv : cap_wind from its Stage-1 sizing), so the
    land needed per MW of firm hydrogen is cap_pv/rho_pv +
    cap_wind/rho_wind. (An arbitrary 50/50 split was used before
    2026-08-21; it understated the ceilings by ~1.8x.)

    The usable share is COUNTRY-SPECIFIC: the WDI screening baseline
    (5% of the land left after excluding forests, 90% of agriculture
    and protected areas; median ~1.1% of territory). scale=2 gives the
    10%-of-eligible high case. Pass land_avail=<float> to force the
    old uniform share instead."""
    if land_avail is None:
        from .land_screen import build
        scr = build()
        share = land.country.map(scr.land_baseline) \
            .fillna(scr.land_baseline.median()) * scale
    else:
        share = pd.Series(land_avail, index=land.index) * scale
    # 2026-10-05: the usable share applies to the cell's own national land
    # (cell_land_area.csv: the country's territory inside the box, with land
    # that lies in neighbours' cells spread over the country's own cells),
    # not to the whole 2.5-degree box, which counted sea and neighbours' land
    la_f = inputs.MAPS / "cell_land_area.csv"
    if la_f.exists():
        la = pd.read_csv(la_f, index_col="cell_id").land_km2
        area = la.reindex(land.index)
        area = area.fillna(cell_area_km2(land.lat))
    else:
        area = cell_area_km2(land.lat)
    A = area.to_numpy() * share.to_numpy()
    need = land.cap_pv / PV_MW_KM2 + land.cap_wind / WIND_MW_KM2
    mw = np.where(need > 0, A / need, 0.0)
    return pd.Series(mw, index=land.index) * 8760 * GJ_PER_MWH


def lcof_cells(land: pd.DataFrame, c_co2: float) -> pd.DataFrame:
    """LCOF per land cell per fuel, $/GJ_fuel: the Stage-2 cascade on the
    SAME global Stage-1 grid every map in the paper uses, so the cost of
    independence, the budget curve and the site figure share one layer.
    """
    lcoe_gj = land.lcoe_usd_mwh / 3.6
    out = {}
    for f in FUELS:
        spec = P.FUELS[f]
        syn = {w: P.syn_cost_per_gj(f, w) for w in land.wacc.unique()}
        syn_c = land.wacc.map(syn)
        # 2026-10-09: the synthesis charge carries the country location factor x the optimized
        # oversizing C_S/F of the flexible plant (capex syn_location_factor, as aggregate_global
        # and gap.py apply it). Default on since 2026-10-09 ; LCOF_SYN_LOC=0 reproduces V1.6.
        if os.environ.get("LCOF_SYN_LOC") != "0" and "syn_loc" in land.columns:
            syn_c = syn_c * land.syn_loc.fillna(1.0)
        out[f] = (MU_H2[f] * land.lcoh_usd_gj
                  + spec["mu_co2"] * c_co2
                  + spec["mu_n2"] * P.C_N2_DEFAULT
                  + syn_c
                  + spec["mu_el"] * lcoe_gj)
    return pd.DataFrame(out, index=land.index)


def main():
    meta = inputs.load_meta(2025)
    land = meta[meta.cell_type == "land"].copy()
    lc = pd.read_csv(inputs.MAPS / f"lcoh_global_2025{SUFFIX}.csv") \
           .set_index("cell_id")
    land = land.join(lc[["cap_pv", "cap_wind", "lcoh_usd_gj",
                         "lcoe_usd_mwh"]], how="inner")
    land = land[np.isfinite(land.cap_pv) & np.isfinite(land.cap_wind)]

    # ---- technical potential per cell (MW_H2 firm) ------------------------
    land["pot_gj"] = firm_h2_potential_gj(land)          # GJ_H2 / yr
    pot = land.groupby("country").pot_gj.sum()

    # ---- demand in H2-equivalent + demand-weighted premium ----------------
    dg = pd.read_csv(inputs.MAPS / "demand_fuel_grid.csv", index_col=0)
    cols = [f + "_gj" for f in FUELS]
    dgc = dg.join(meta[["country"]]).groupby("country")[cols].sum()
    dem_fuel_gj = dgc.sum(axis=1)
    dem_h2_gj = sum(dgc[f + "_gj"] * MU_H2[f] for f in FUELS)

    # LCOF at each country's best domestic cell, on the global grid — the
    # same layer and the same "best cell" definition as Fig. 4
    # CO2 at each cell's cheapest source (industrial, biogenic or DAC), the
    # same carbon layer as Figs 2-4 (2026-09-17; DAC everywhere before)
    co2df = pd.read_csv(inputs.MAPS / "co2_cost_by_cell.csv").set_index("cell_id")
    cellwise = lcof_cells(land, co2df.co2_cost.reindex(land.index).fillna(P.C_CO2_DAC))
    best = land.groupby("country").lcoh_usd_gj.idxmin()
    lcof = cellwise.loc[best.to_numpy()].set_index(best.index)
    # the same comparators as the budget curve: Figure 3's own-import normal
    # prices for the core 30 (ammonia; diesel, jet and ethanol), the national
    # gas route or benchmark elsewhere, all in 2025 US$
    from .security_budget import _grey
    grey_tab = _grey(dgc.rename(columns=lambda k: k.replace("_gj", "")))
    prem_rows = {}
    fam_rows = {}
    for c in dgc.index:
        if c not in lcof.index:
            continue
        num = 0.0
        for f in FUELS:
            d = dgc.loc[c, f + "_gj"]
            if d <= 0 or f not in lcof.columns or not np.isfinite(
                    lcof.loc[c, f]):
                continue
            grey = float(grey_tab.loc[c, f]) if c in grey_tab.index else np.nan
            if not np.isfinite(grey):
                continue
            pf = max(lcof.loc[c, f] - grey, 0.0) * d
            num += pf
            fam = "gas" if f in ("e-methane", "ammonia", "methanol")                 else "oil"
            fam_rows.setdefault(c, {"gas": 0.0, "oil": 0.0})[fam] += pf
        prem_rows[c] = num          # $/yr at full substitution
    prem = pd.Series(prem_rows)
    fam = pd.DataFrame(fam_rows).T

    si = pd.read_csv(inputs.MAPS / "security_index.csv", index_col=0)
    df = pd.DataFrame({"pot_h2_gj": pot, "dem_h2_gj": dem_h2_gj,
                       "dem_fuel_gj": dem_fuel_gj,
                       "cost_usd": prem}).dropna()
    df = df[df.dem_fuel_gj > 0]
    df["ratio"] = df.pot_h2_gj / df.dem_h2_gj
    df["cost_bn"] = df.cost_usd / 1e9
    df["cost_gdp_pct"] = df.cost_usd / si.gdp_usd.reindex(df.index) * 100
    df["esd_bn"] = si.esd_c_usd.reindex(df.index) / 1e9
    df["esd_gdp_pct"] = si.esd_gdp_pct.reindex(df.index)
    df["esd_hi_gdp_pct"] = si.esd_gdp_hi_pct.reindex(df.index)
    gdp = si.gdp_usd.reindex(df.index)
    df["cost_gas_gdp_pct"] = fam.gas.reindex(df.index) / gdp * 100
    df["cost_oil_gdp_pct"] = fam.oil.reindex(df.index) / gdp * 100
    df["sar_gj"] = si.sar_c_gj.reindex(df.index)
    df["cover_sar"] = (df.pot_h2_gj / df.sar_gj.replace(0, np.nan)).clip(
        upper=50)
    df["V"] = pd.read_csv(inputs.MAPS / "vulnerability_index.csv",
                          index_col=0).V.reindex(df.index)
    df.to_csv(inputs.MAPS / "supply_demand.csv")

    n = len(df)
    self_suff = (df.ratio >= 1).mean()
    print(f"{n} economies; self-sufficient on screened land: "
          f"{self_suff:.0%}; median ratio {df.ratio.median():.1f}x; "
          f"median cost of full independence {df.cost_gdp_pct.median():.2f}"
          f"% GDP; median ESD {df.esd_gdp_pct.median():.2f}% GDP")
    gshare = (df.cost_gas_gdp_pct / df.cost_gdp_pct).median()
    print(f"gas-family share of the independence cost, median: "
          f"{gshare:.0%} (oil-linked liquids carry the rest)")
    for c in ["China", "India", "Japan", "South Korea", "Germany",
              "United States of America", "Vietnam", "Chile", "Morocco",
              "Cyprus", "Sri Lanka", "Madagascar", "Singapore", "Netherlands"]:
        if c in df.index:
            r = df.loc[c]
            print(f"  {SHORT.get(c, c):15s} ratio {r.ratio:6.1f}x  cost "
                  f"${r.cost_bn:6.1f}bn/yr = {r.cost_gdp_pct:5.2f}% GDP  "
                  f"ESD {r.esd_gdp_pct:5.2f}% GDP")

    # ---- table: 16 typical economies --------------------------------------
    EX = core_countries(df.index)                  # the core 30
    rows = []
    for c in EX:
        if c not in df.index:
            continue
        r = df.loc[c]
        rows.append(f"{SHORT.get(c, c)} & {r.dem_fuel_gj / UMM / 1e9:.2f} & "
                    f"{min(r.ratio, 999):.1f} & {r.cost_bn:.0f} & "
                    f"{r.cost_gdp_pct:.1f} & {r.cost_gas_gdp_pct:.1f} & "
                    f"{r.cost_oil_gdp_pct:.1f} & {r.esd_hi_gdp_pct:.2f} & "
                    + (f"{r.V:.2f}" if np.isfinite(r.V) else "--"))
    header = (" & demand & self- & " + BS + "multicolumn{4}{c}{cost of "
              "full independence, 2025} & loss & " + EOL + NL
              + BS + "cmidrule(lr){4-7}" + NL
              + " & (bn & suffi- & (" + BS + "$bn & (" + BS + "% & gas- & "
              "oil- & (" + BS + "% & " + EOL + NL
              + "Country & MMBtu/yr) & ciency & /yr) & GDP) & linked & "
              "linked & GDP) & $V$ " + EOL)
    body = (BS + "begin{tabular}{@{}l r r r r r r r r@{}}" + NL + BS
            + "toprule" + NL + header + NL + BS + "midrule" + NL
            + (" " + EOL + NL).join(rows) + " " + EOL + NL
            + BS + "bottomrule" + NL + BS + "end{tabular}" + NL)
    texdir = inputs.MAPS.parent.parent / "synthetic_fuel_nature"
    (texdir / "tab_sd.tex").write_text(body, encoding="utf-8")

    # ---- figure: self-sufficiency vs cost, 50 core economies --------------
    core = core_countries(df.index)
    d = df.loc[core]
    fig, (a, b) = plt.subplots(1, 2, figsize=(183 * MM, 118 * MM),
                               gridspec_kw=dict(width_ratios=[1.0, 1.0],
                                                wspace=0.55))
    fig.subplots_adjust(left=0.07, right=0.985, top=0.89, bottom=0.11)
    sz = 4 + 40 * (d.dem_fuel_gj / d.dem_fuel_gj.max()) ** 0.5
    col = np.where(d.ratio >= 1, BLUE, ORANGE)
    a.scatter(d.ratio, d.cost_gdp_pct, s=sz, c=col, alpha=0.75,
              edgecolors="white", linewidths=0.3)
    a.axvline(1, color=GREY, lw=0.6, ls=":")
    a.set_xscale("log")
    a.set_xlabel("domestic potential / addressable demand "
                 "(screened land, median 1.1%)")
    a.set_ylabel("cost of full independence, % of GDP per year")
    ytop = d.cost_gdp_pct.max() * 1.18
    a.set_ylim(0, ytop)
    a.text(1.08, ytop * 0.985, "self-sufficient", fontsize=8,
           color=BLUE, va="top")
    a.text(0.92, ytop * 0.985, "import-dependent", fontsize=8,
           color=ORANGE, va="top", ha="right")
    from .labels import place_labels
    names = [SHORT.get(c, c).replace("United States", "US")
             for c in d.index]
    xr = a.get_xlim()
    n_lab = place_labels(
        a, fig, d.ratio.to_numpy(), d.cost_gdp_pct.to_numpy(), names,
        order=np.argsort(-d.dem_fuel_gj.to_numpy()),
        reserved=[(xr[0], xr[1], ytop * 0.90, ytop)], logx=True)
    print(f"supply-demand labels placed: {n_lab} of {len(d)}")
    for sp in ("top", "right"):
        a.spines[sp].set_visible(False)
    a.text(-0.13, 1.19, "a", transform=a.transAxes, fontsize=9,
           fontweight="bold", va="top")

    # b: where the cost sits — gas-linked vs oil-linked fuels, exemplars
    ex = [c for c in EX if c in df.index]
    ex = sorted(ex, key=lambda c: -df.loc[c, "cost_gdp_pct"])
    ys = np.arange(len(ex))[::-1]
    gasv = df.loc[ex, "cost_gas_gdp_pct"].to_numpy()
    oilv = df.loc[ex, "cost_oil_gdp_pct"].to_numpy()
    b.barh(ys, gasv, color=GREEN, height=0.62,
           label="gas-linked fuels (e-methane, ammonia, methanol)")
    b.barh(ys, oilv, left=gasv, color=RED, height=0.62,
           label="oil-linked fuels (e-diesel, e-kerosene, ethanol)")
    b.scatter(df.loc[ex, "esd_hi_gdp_pct"], ys, marker="|", s=60,
              color="black", zorder=5,
              label="expected security loss (ENTSOG anchor)")
    b.set_yticks(ys)
    b.set_yticklabels([SHORT.get(c, c).replace("United States", "US")
                       for c in ex], fontsize=8)
    b.set_xlabel("cost of full independence at 2025 costs, "
                 "% of GDP per year")
    XMAX = 25.0
    b.set_xlim(0, XMAX)
    for c, y in zip(ex, ys):
        v = df.loc[c, "esd_hi_gdp_pct"]
        if v > XMAX:
            b.annotate(f"{v:.0f}%", (XMAX * 0.985, y),
                       textcoords="offset points", xytext=(-4, 0),
                       ha="right", va="center", fontsize=8,
                       arrowprops=dict(arrowstyle="-|>", lw=0.6,
                                       color="black"))
    b.legend(fontsize=8, frameon=False, loc="lower center",
             bbox_to_anchor=(0.42, 1.0), ncol=1, handlelength=1.0)
    for sp in ("top", "right"):
        b.spines[sp].set_visible(False)
    b.text(-0.32, 1.19, "b", transform=b.transAxes, fontsize=9,
           fontweight="bold", va="top")

    fig.savefig(OUT / "fig_supply_demand.pdf", bbox_inches="tight")
    fig.savefig(OUT / "fig_supply_demand.png", dpi=600,
                bbox_inches="tight")
    plt.close(fig)
    print("saved fig_supply_demand.(pdf|png), supply_demand.csv, tab_sd.tex")


if __name__ == "__main__":
    main()
