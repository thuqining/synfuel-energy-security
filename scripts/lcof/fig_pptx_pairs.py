"""
fig_pptx_pairs.py — paired figures for the results PPT (16:9 slides).

  INPUT LAYERS (two panels per page):
    pair_cf.png        solar CF | wind CF (2025)
    pair_co2.png       CO2 delivered price | optimal SOURCE (industrial/biogenic/DAC)
    pair_water.png     water price | sourcing method (fresh/desal/desal+transport)
    pair_wacc_epc.png  WACC | synthesis EPC location factor
    pair_pv_wind.png   PV CAPEX | wind CAPEX
    pair_ez_bat.png    electrolyser CAPEX | battery CAPEX
    pair_tank_h2.png   H2 tank CAPEX | (example) FT synthesis CAPEX

  RESULTS (two panels per page, per fuel):
    fuel_<name>.png    median cost in NATIVE unit | interannual CV
                       (median over the 20 weather years, regional mainline)

  SYNTHESIS (one page):
    best_fuel.png      cheapest non-H2 fuel per cell | its price ($/MMBtu)

From scripts/:  conda run -n synfuel python -u -m lcof.fig_pptx_pairs
Outputs in cf_global_final/figures/pptx/
"""
from __future__ import annotations

import sys
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

mpl.use("Agg")

from . import inputs, params as P

sys.path.insert(0, str(inputs.PROJECT / "cf_global_final" / "python"))
import plot_style as ps                                    # noqa: E402

YEARS = list(range(2006, 2026))
SUFFIX = "_reg"
OUT = inputs.PROJECT / "cf_global_final" / "figures" / "pptx"
OUT.mkdir(parents=True, exist_ok=True)

mpl.rcParams.update({"font.family": "sans-serif",
                     "font.sans-serif": ["Arial", "DejaVu Sans"],
                     "font.size": 12, "axes.titlesize": 14,
                     "axes.linewidth": 0.5})

_GRID = ps.load_grid()
_COUNTRIES = ps.load_countries()
_LAND_UNION = ps.land_union(_COUNTRIES)


def geo_panel(ax, values, cmap, vmin, vmax, cbar_label, title, norm=None):
    """norm: pass a matplotlib Normalize (e.g. TwoSlopeNorm) when the colour
    scale must pin a meaningful midpoint — a diverging ramp is wrong unless its
    neutral colour sits exactly on zero."""
    cells = _GRID.copy()
    cells["val"] = cells["cell_id"].map(values)
    raster = cells[(cells.cell_type == "land") & cells.val.notna()].copy()
    raster = gpd.clip(raster, _LAND_UNION)
    kw = dict(norm=norm) if norm is not None else dict(vmin=vmin, vmax=vmax)
    raster.plot(column="val", cmap=cmap, ax=ax, linewidth=0, **kw)
    land_c = set(cells.loc[cells.cell_type == "land", "country"].dropna())
    islands = _COUNTRIES[~_COUNTRIES.country.isin(land_c | {"Greenland"})].copy()
    if len(islands):
        cent = islands.geometry.representative_point()
        pts = np.column_stack([cent.x.to_numpy(), cent.y.to_numpy()])
        islands["val"] = ps._nearest_cell_values(cells, pts)
        islands = islands[np.isfinite(islands.val)]
        islands.plot(column="val", cmap=cmap, ax=ax, linewidth=0, **kw)
    _COUNTRIES.boundary.plot(ax=ax, color="0.35", linewidth=0.15)
    ax.set_xlim(-180, 180); ax.set_ylim(-58, 84)
    ax.set_xticks([]); ax.set_yticks([]); ax.set_aspect("equal")
    ax.set_title(title, loc="left", fontsize=14)
    sm = plt.cm.ScalarMappable(
        cmap=cmap, norm=norm if norm is not None
        else mpl.colors.Normalize(vmin, vmax))
    cb = ax.figure.colorbar(sm, ax=ax, shrink=0.82, pad=0.015, aspect=22)
    cb.set_label(cbar_label, fontsize=11)
    cb.ax.tick_params(labelsize=10, width=0.4)


def cat_panel(ax, codes, palette, labels, title):
    """codes: dict cell_id -> int category index."""
    cells = _GRID.copy()
    cells["val"] = cells["cell_id"].map(codes)
    raster = cells[(cells.cell_type == "land") & cells.val.notna()].copy()
    raster = gpd.clip(raster, _LAND_UNION)
    raster["col"] = raster["val"].astype(int).map(dict(enumerate(palette)))
    raster.plot(color=raster["col"], ax=ax, linewidth=0)
    _COUNTRIES.boundary.plot(ax=ax, color="0.35", linewidth=0.15)
    ax.set_xlim(-180, 180); ax.set_ylim(-58, 84)
    ax.set_xticks([]); ax.set_yticks([]); ax.set_aspect("equal")
    ax.set_title(title, loc="left", fontsize=14)
    handles = [Patch(facecolor=palette[i], label=labels[i])
               for i in range(len(labels))]
    ax.legend(handles=handles, loc="lower left", fontsize=10, frameon=False)


def pair(fname, draw_left, draw_right, height=4.6):
    fig, axes = plt.subplots(1, 2, figsize=(16, height))
    draw_left(axes[0]); draw_right(axes[1])
    fig.tight_layout(w_pad=1.4)
    fig.savefig(OUT / fname, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print("saved", fname)


# ------------------------------ data ------------------------------------------
def load_all():
    meta = inputs.load_meta(2025)
    frames = {y: pd.read_csv(inputs.MAPS / f"lcoh_global_{y}{SUFFIX}.csv")
              .set_index("cell_id") for y in YEARS}
    cells = frames[YEARS[0]].index
    lcoh = np.column_stack([frames[y].loc[cells, "lcoh_usd_gj"] for y in YEARS])
    lcoe = np.column_stack([frames[y].loc[cells, "lcoe_usd_mwh"]
                            for y in YEARS]) / 3.6
    return meta, cells, lcoh, lcoe


def cascade_years(meta, cells, lcoh, lcoe, fuel):
    f = P.FUELS[fuel]
    wacc = meta.loc[cells, "wacc"].to_numpy(float)
    syn_loc = meta.loc[cells, "syn_loc"].fillna(1.0).to_numpy(float)
    syn = np.array([(P.crf(w, f["syn_life"]) + f["syn_opex"]) * f["syn_capex"]
                    / (P.CF_SYN * 8760 * 3.6) for w in wacc]) * syn_loc
    co2 = meta.loc[cells, "co2_cost"].to_numpy(float)
    co2 = np.where(np.isfinite(co2), co2, P.C_CO2_DAC)
    return (lcoh / f["eta_syn"]
            + (f["mu_co2"] * co2 + f["mu_n2"] * P.C_N2_DEFAULT + syn)[:, None]
            + f["mu_el"] * lcoe)


NATIVE = {  # fuel -> (multiplier from $/GJ, axis label)
    "hydrogen": (0.120, "$ / kg H2"),
    "ammonia": (18.6, "$ / t NH3"),
    "methanol": (19.9, "$ / t MeOH"),
    "e-methane": (3.6, "$ / MWh"),
    "e-diesel": (0.0358, "$ / litre"),
    "e-kerosene": (0.0351, "$ / litre"),
    "ethanol": (26.8, "$ / t EtOH"),
}


def main():
    meta, cells, lcoh, lcoe = load_all()
    land = meta.loc[cells]

    # ---------- input pairs ----------
    pair("pair_cf.png",
         lambda ax: geo_panel(ax, land.pv_cf.to_dict(), "YlGnBu", 0.05, 0.28,
                              "capacity factor", "Solar PV capacity factor (2025)"),
         lambda ax: geo_panel(ax, land.wind_cf.to_dict(), "YlGnBu", 0.10, 0.55,
                              "capacity factor", "Onshore wind capacity factor (2025)"))

    co2df = pd.read_csv(inputs.MAPS / "co2_cost_by_cell.csv").set_index("cell_id")
    pcode = co2df.pathway.str.lower().map(
        {"industrial": 0, "biogenic": 1, "dac": 2}).to_dict()
    pair("pair_co2.png",
         lambda ax: geo_panel(ax, co2df.co2_cost.to_dict(), "YlOrRd", 40, 500,
                              "$ / t CO2", "Delivered CO2 price (optimal source)"),
         lambda ax: cat_panel(ax, pcode, ["#4C78A8", "#59A14F", "#E45756"],
                              ["industrial point source", "biogenic (fermentation, pulp)",
                               "DAC (no source nearby)"],
                              "Optimal CO2 source"))

    wat = pd.read_csv(inputs.MAPS / "water_cost_by_cell.csv").set_index("cell_id")
    wcode = {}
    for cid, r in wat.iterrows():
        if not bool(r.stressed):
            wcode[cid] = 0
        elif r.dist_coast_km <= 200:
            wcode[cid] = 1
        else:
            wcode[cid] = 2
    pair("pair_water.png",
         lambda ax: geo_panel(ax, wat.water_cost.to_dict(), "PuBu", 0.5, 2.0,
                              "$ / m3", "Delivered water price"),
         lambda ax: cat_panel(ax, wcode, ["#59A14F", "#4C78A8", "#B279A2"],
                              ["freshwater (unstressed)", "desalination (coastal)",
                               "desalination + inland transport"],
                              "Water sourcing (stress-constrained optimum)"))

    pair("pair_wacc_epc.png",
         lambda ax: geo_panel(ax, (land.wacc * 100).to_dict(), "RdPu", 4, 14,
                              "%", "WACC (country risk)"),
         lambda ax: geo_panel(ax, land.syn_loc.to_dict(), "YlGn", 0.7, 1.15,
                              "factor (US = 1.0)", "Synthesis-plant EPC location factor"))

    pair("pair_pv_wind.png",
         lambda ax: geo_panel(ax, (land.pv_capex / 1e3).to_dict(), "YlGn", 500, 1600,
                              "$ / kW", "Utility PV CAPEX (IRENA 2023)"),
         lambda ax: geo_panel(ax, (land.wind_capex / 1e3).to_dict(), "YlGn", 900, 2600,
                              "$ / kW", "Onshore wind CAPEX (IRENA 2023)"))

    pair("pair_ez_bat.png",
         lambda ax: geo_panel(ax, (land.ez_capex / 1e3).to_dict(), "YlGn", 300, 1500,
                              "$ / kW", "Electrolyser CAPEX (procurement)"),
         lambda ax: geo_panel(ax, (land.bat_e_capex / 1e3).to_dict(), "YlGn", 100, 240,
                              "$ / kWh", "Battery system CAPEX (procurement)"))

    pair("pair_tank_h2.png",
         lambda ax: geo_panel(ax, (land.tank_capex / 1e3).to_dict(), "YlGn", 8, 18,
                              "$ / kWh H2", "H2 buffer tank CAPEX"),
         lambda ax: geo_panel(ax, (1000 * land.syn_loc).to_dict(), "YlGn", 650, 1200,
                              "$ / kW fuel", "Synthesis CAPEX example (FT train)"))

    # ---------- per-fuel result pairs ----------
    summary = []
    fields = {}
    for fuel in P.FUELS:
        lcof = cascade_years(meta, cells, lcoh, lcoe, fuel)
        fields[fuel] = lcof
        mult, unit = NATIVE[fuel]
        med = np.median(lcof, axis=1) * mult
        cv = lcof.std(axis=1) / lcof.mean(axis=1)
        vmin, vmax = np.quantile(med, [0.02, 0.95])
        med_d = pd.Series(med, index=cells).to_dict()
        cv_d = pd.Series(cv, index=cells).to_dict()
        pair(f"fuel_{fuel.replace('-', '')}.png",
             lambda ax, d=med_d, lo=vmin, hi=vmax, u=unit, fl=fuel:
                 geo_panel(ax, d, "YlGnBu_r", lo, hi, u,
                           f"{fl} — median cost, 20 weather years"),
             lambda ax, d=cv_d, fl=fuel:
                 geo_panel(ax, d, "YlOrRd", 0.0, 0.10, "CV of annual cost",
                           f"{fl} — interannual variability"))
        summary.append((fuel, np.median(med), unit))

    # ---------- best non-H2 fuel per cell ($/MMBtu) ----------
    NONH2 = ["ammonia", "methanol", "e-methane", "e-diesel", "e-kerosene",
             "ethanol"]
    med_gj = np.column_stack([np.median(fields[f], axis=1) for f in NONH2])
    win = med_gj.argmin(axis=1)
    win_price = med_gj.min(axis=1) * P.MMBTU_PER_GJ
    # margin over the runner-up: with the H2-only eta convention ammonia wins
    # every cell, so the categorical panel alone says one word — the margin
    # map is where the information now lives
    two = np.sort(med_gj, axis=1)
    margin = (two[:, 1] - two[:, 0]) * P.MMBTU_PER_GJ
    PALETTE = ["#4C78A8", "#F58518", "#59A14F", "#E45756", "#B279A2", "#76B7B2"]
    pair("best_fuel.png",
         lambda ax: cat_panel(ax, pd.Series(win, index=cells).to_dict(),
                              PALETTE, NONH2,
                              "Cheapest synthetic fuel beyond hydrogen (median)"),
         lambda ax: geo_panel(ax, pd.Series(margin, index=cells).to_dict(),
                              "YlGnBu", 0,
                              float(np.quantile(margin, 0.95)), "$ / MMBtu",
                              "Its margin over the runner-up"))
    counts = pd.Series([NONH2[i] for i in win]).value_counts()
    print("\nbest non-H2 fuel, cell counts:")
    print(counts.to_string())

    # ---------- cheapest CARBON-BASED fuel (H2 and NH3 both excluded) -------
    # With ammonia winning every cell, this is where the carbon-fuel
    # geography lives: the methanol/e-methane split is set by the delivered
    # CO2 cost, the only fuel-specific spatial input.
    CARBON = ["methanol", "e-methane", "e-diesel", "e-kerosene", "ethanol"]
    med_c = np.column_stack([np.median(fields[f], axis=1) for f in CARBON])
    win_c = med_c.argmin(axis=1)
    price_c = med_c.min(axis=1) * P.MMBTU_PER_GJ
    PAL_C = ["#F58518", "#59A14F", "#E45756", "#B279A2", "#76B7B2"]
    pair("best_fuel_carbon.png",
         lambda ax: cat_panel(ax, pd.Series(win_c, index=cells).to_dict(),
                              PAL_C, CARBON,
                              "Cheapest carbon-based fuel (median; H2 and "
                              "NH3 excluded)"),
         lambda ax: geo_panel(ax, pd.Series(price_c, index=cells).to_dict(),
                              "YlGnBu_r", float(np.quantile(price_c, 0.02)),
                              float(np.quantile(price_c, 0.95)), "$ / MMBtu",
                              "Cost of that fuel"))
    counts_c = pd.Series([CARBON[i] for i in win_c]).value_counts()
    print("\nbest carbon-based fuel, cell counts:")
    print(counts_c.to_string())
    print("\nmedian-of-median native prices:")
    for fuel, v, unit in summary:
        print(f"  {fuel:12s} {v:8.1f} {unit}")


if __name__ == "__main__":
    main()
