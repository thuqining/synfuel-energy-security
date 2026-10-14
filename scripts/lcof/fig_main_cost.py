"""
fig_main_cost.py — MAIN-TEXT Figure 1 at true Nature specification.

  a  (hero)  median LCOH over the 20 weather years — the level
  b  (hero)  the recommended synthetic-fuel plant per cell (non-H2 layer):
             top-1 fuel by demand share x cost competitiveness (EDGAR
             sectoral demand proxy, see demand_grid.py); dots mark
             contested cells where the runner-up is within 60% of the
             winner; grey = sparse local demand (export-oriented site)

Nature spec: double column 183 mm, Arial 5-7 pt, panel letters 8 pt bold,
line weights <= 0.75 pt, vector PDF + 600 dpi PNG.

From scripts/:  conda run -n synfuel python -u -m lcof.fig_main_cost
Output: cf_global_final/figures/pptx/fig_main_cost.(pdf|png)
"""
from __future__ import annotations

import json
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

mpl.use("Agg")

from . import inputs, params as P
from .fig_pptx_pairs import (OUT, SUFFIX, YEARS, _GRID, _COUNTRIES,
                             _LAND_UNION, gpd, ps)

MM = 1 / 25.4
NAT_RC = {
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "DejaVu Sans"],
    "font.size": 7, "axes.titlesize": 7, "axes.labelsize": 7,   # 2026-10-08: Nature 5-7 pt
    "xtick.labelsize": 7, "ytick.labelsize": 7,
    "axes.linewidth": 0.5, "xtick.major.width": 0.5,
    "ytick.major.width": 0.5, "lines.linewidth": 0.75,
}
# fig_pptx_pairs resets rcParams to deck sizes at import — re-assert ours
mpl.rcParams.update(NAT_RC)


def _nat_map(fig, ax, values, cmap, vmin, vmax, cbar_label, title):
    """geo_panel redrawn at Nature type sizes with a slim colorbar."""
    cells = _GRID.copy()
    cells["val"] = cells["cell_id"].map(values)
    raster = cells[(cells.cell_type == "land") & cells.val.notna()].copy()
    raster = gpd.clip(raster, _LAND_UNION)
    raster.plot(column="val", cmap=cmap, ax=ax, linewidth=0,
                vmin=vmin, vmax=vmax, rasterized=True)
    land_c = set(cells.loc[cells.cell_type == "land", "country"].dropna())
    isl = _COUNTRIES[~_COUNTRIES.country.isin(land_c | {"Greenland"})].copy()
    if len(isl):
        cent = isl.geometry.representative_point()
        pts = np.column_stack([cent.x.to_numpy(), cent.y.to_numpy()])
        isl["val"] = ps._nearest_cell_values(cells, pts)
        isl = isl[np.isfinite(isl.val)]
        isl.plot(column="val", cmap=cmap, ax=ax, linewidth=0,
                 vmin=vmin, vmax=vmax, rasterized=True)
    _COUNTRIES.boundary.plot(ax=ax, color="0.4", linewidth=0.1)
    ax.set_xlim(-180, 180); ax.set_ylim(-58, 84)
    ax.set_xticks([]); ax.set_yticks([]); ax.set_aspect("equal")
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title(title, loc="left", fontsize=8, x=0.024)
    ax.set_anchor("N")
    sm = plt.cm.ScalarMappable(cmap=cmap,
                               norm=mpl.colors.Normalize(vmin, vmax))
    cb = fig.colorbar(sm, ax=ax, orientation="horizontal", shrink=0.55,
                      pad=0.02, aspect=32)
    cb.set_label(cbar_label, fontsize=8)
    cb.ax.tick_params(labelsize=8, width=0.4, length=2.5)
    cb.outline.set_linewidth(0.4)
BLUE, GREY, ORANGE = "#4C72B0", "#98A3AD", "#DD8452"
SITES = ["Chile", "Namibia", "China", "Morocco", "United States of America",
         "Germany", "Japan"]
SHORT = {"United States of America": "United States"}


def _pl(ax, s, dx=-0.06):
    ax.text(dx, 1.10, s, transform=ax.transAxes, fontsize=8,
            fontweight="bold", va="top")


FUELS = ["e-methane", "e-diesel", "methanol", "e-kerosene", "ammonia",
         "ethanol", "marine"]
FCOL = {"e-methane": "#009E73", "e-diesel": "#D55E00",
        "methanol": "#E69F00", "e-kerosene": "#56B4E9",
        "ammonia": "#0072B2", "ethanol": "#CC79A7", "marine": "#F0E442"}
SPARSE_C = "#E4E4E4"
# demand-side figures show what is burned today, not synthetic-fuel use:
# the incumbent fuel first, the synthetic substitute (and colour) in
# brackets, so the demand map and the bill read as demand
DEMAND_LABEL = {"e-methane": "gas (e-methane)", "e-diesel": "diesel (e-diesel)",
                "methanol": "methanol", "e-kerosene": "jet fuel (e-kerosene)",
                "ammonia": "ammonia", "ethanol": "gasoline (ethanol)",
                "marine": "fuel oil (marine e-methanol/e-ammonia)"}


def draw_reco(b, meta):
    """the recommendation map, single clean layer: fill = the planner's
    choice (largest discounted NPV / earliest break-even among fuels with
    a bankable local market); grey = no bankable local market (export
    site). Runner-ups and security variants live in the SI, not here."""
    rec = pd.read_csv(inputs.MAPS / "fuel_recommendation.csv", index_col=0)
    code = rec.top1.map({f: i for i, f in enumerate(FUELS)}).astype(float)
    code[rec["sparse"]] = np.nan

    cellsg = _GRID.copy()
    cellsg["val"] = cellsg["cell_id"].map(code)
    landg = cellsg[cellsg.cell_type == "land"].copy()
    base = gpd.clip(landg[landg.cell_id.map(rec["sparse"]).fillna(True)],
                    _LAND_UNION)
    if len(base):
        base.plot(ax=b, color=SPARSE_C, linewidth=0, rasterized=True)
    rast = gpd.clip(landg[landg.val.notna()], _LAND_UNION)
    rast.plot(column="val", cmap=mpl.colors.ListedColormap(
        [FCOL[f] for f in FUELS]), ax=b, linewidth=0, vmin=-0.5,
        vmax=len(FUELS) - 0.5, rasterized=True)
    _COUNTRIES.boundary.plot(ax=b, color="0.4", linewidth=0.1)

    b.set_xlim(-180, 180); b.set_ylim(-58, 84)
    b.set_xticks([]); b.set_yticks([]); b.set_aspect("equal")
    for sp in b.spines.values():
        sp.set_visible(False)
    b.set_anchor("N")
    import matplotlib.patches as mp
    hdl = [mp.Patch(color=FCOL[f], label=f) for f in FUELS]
    hdl += [mp.Patch(color=SPARSE_C, label="export site")]
    b.legend(handles=hdl, loc="lower left", fontsize=8, frameon=False,
             handlelength=1.0, borderaxespad=0.1, ncol=2,
             columnspacing=0.9, handletextpad=0.5, labelspacing=0.35)


def draw_reco_table(t):
    """the evaluation numbers behind the colours, as a strip below the
    map: per winner — cells won, median LCOF vs its grey rival
    ($/MMBtu), addressable market won, median break-even year."""
    t.set_axis_off()
    st = pd.read_csv(inputs.MAPS / "fuel_reco_stats.csv")
    st = st.sort_values("cells", ascending=False)
    cols = [("winner", 0.045, "left"), ("cells won", 0.30, "right"),
            ("median LCOF\n$/MMBtu", 0.44, "right"),
            ("grey rival\n$/MMBtu", 0.58, "right"),
            ("market won\nPJ/yr", 0.73, "right"),
            ("median\nbreak-even", 0.88, "right")]
    for htxt, xx, haa in cols:
        t.text(xx, 0.97, htxt, transform=t.transAxes, fontsize=8,
               color="#555555", ha=haa, va="top", linespacing=1.1)
    for k, (_, r) in enumerate(st.iterrows()):
        yy = 0.66 - k * 0.115
        t.scatter(0.018, yy + 0.03, marker="s", s=9, color=FCOL[r.fuel],
                  transform=t.transAxes, clip_on=False)
        vals = [r.fuel, f"{r.cells:.0f}", f"{r.lcof_mmbtu:.0f}",
                f"{r.rival_mmbtu:.0f}", f"{r.demand_pj:,.0f}",
                "beyond 2050" if not np.isfinite(r.tstar_med)
                else f"{r.tstar_med:.0f}"]
        for (_, xx, haa), v in zip(cols, vals):
            t.text(xx, yy, v, transform=t.transAxes, fontsize=8,
                   color="#333333", ha=haa)


def main():
    frames = {y: pd.read_csv(inputs.MAPS / f"lcoh_global_{y}{SUFFIX}.csv")
              .set_index("cell_id") for y in YEARS}
    cells = frames[YEARS[0]].index
    lcoh = np.column_stack([frames[y].loc[cells, "lcoh_usd_gj"]
                            for y in YEARS])
    firm = pd.Series(lcoh.max(axis=1), index=cells)
    meta = inputs.load_meta(2025)
    land = meta[meta.cell_type == "land"]

    fig = plt.figure(figsize=(183 * MM, 92 * MM))
    a = fig.add_subplot(111)
    fig.subplots_adjust(left=0.005, right=0.995, top=0.94, bottom=0.02)

    med = pd.Series(np.median(lcoh, axis=1), index=cells)

    # ---- the hero: median LCOH, $/kg H2 -----------------------------------
    KG = 0.12                    # $/GJ (LHV) -> $/kg H2 (120 MJ/kg)
    _nat_map(fig, a, (med.clip(upper=80) * KG).to_dict(), "YlGnBu_r",
             15 * KG, 80 * KG, "median LCOH, \\$/kg H$_2$ (LHV)", "")

    fig.savefig(OUT / "fig_main_cost.pdf", bbox_inches="tight")
    fig.savefig(OUT / "fig_main_cost.png", dpi=600, bbox_inches="tight")
    plt.close(fig)
    print("saved fig_main_cost.(pdf|png)  183 mm double column")


if __name__ == "__main__":
    main()
