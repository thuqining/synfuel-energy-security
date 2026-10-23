"""
fig_sd_map.py — supply MEETS demand on one map (Bolun's merge of the
cost map and the demand map).

Every land cell is classed on two axes at once:
  supply   terciles of the median firm-hydrogen cost (cheapest = best)
  demand   terciles of the reconciled addressable synthetic-fuel demand

and painted from a 3x3 bivariate palette: blue = cheap hydrogen but no
market, magenta = a market but expensive hydrogen, DEEP PURPLE = both,
i.e. the places worth building first. A 3x3 key sits in the corner.

From scripts/:  conda run -n synfuel python -u -m lcof.fig_sd_map
Output: cf_global_final/figures/pptx/fig_sd_map.(pdf|png)
        data/cost/sd_map_classes.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

mpl.use("Agg")

from . import inputs
from . import params as P
from .fig_main_cost import MM, NAT_RC, FUELS
from .fig_pptx_pairs import (OUT, SUFFIX, YEARS, _GRID, _COUNTRIES,
                             _LAND_UNION, gpd)

mpl.rcParams.update(NAT_RC)

UMM = 1.0551
KG = 0.12                       # $/GJ (LHV) -> $/kg H2
MMB_PER_GJ = 1.0551             # $/GJ -> $/MMBtu (team common unit)
KG_TO_MMBTU = MMB_PER_GJ / KG   # $/kg H2 -> $/MMBtu
DEM_MIN = 0.5 * 1e3 * KG / MMB_PER_GJ / 1e3   # the old 0.5 kt H2
#   floor, expressed in million MMBtu of fuel, so the same thin
#   markets stay out of the demand classing
KT_TO_MMMBTU = KG / MMB_PER_GJ  # kt H2 -> million MMBtu:
#   1 kt = 1e6 kg x 0.12 GJ/kg = 1.2e5 GJ = 1.14e5 MMBtu = 0.114 M
# rows: supply class (0 dearest .. 2 cheapest), cols: demand class
BIV = [["#EDEDED", "#F2A0C6", "#E6007E"],
       ["#8FC0E8", "#B072B8", "#B4116F"],
       ["#0F6FD1", "#6A34B8", "#33095E"]]
NODATA = "#D5D5D5"
N = 5                           # display classes per axis (quintiles)


def _blend_biv(u, v, biv=None):
    """continuous bilinear interpolation over a 3x3 bivariate palette:
    u = cheapness rank (1 = cheapest), v = demand rank (1 = deepest).
    Keeps exactly the chosen tones; the map becomes fully smooth."""
    base = np.array([[mpl.colors.to_rgb(c) for c in row]
                     for row in (biv or BIV)])
    u = np.clip(np.asarray(u, float), 0, 1) * 2.0
    v = np.clip(np.asarray(v, float), 0, 1) * 2.0
    i0 = np.minimum(u.astype(int), 1)
    j0 = np.minimum(v.astype(int), 1)
    fu = (u - i0)[..., None]
    fv = (v - j0)[..., None]
    return (base[i0, j0] * (1 - fu) * (1 - fv)
            + base[i0 + 1, j0] * fu * (1 - fv)
            + base[i0, j0 + 1] * (1 - fu) * fv
            + base[i0 + 1, j0 + 1] * fu * fv)


def _fmt(v):
    return f"{v:.1f}" if v < 10 else f"{v:.0f}"


ND = 12                         # display classes per axis


def _paln(n=ND, biv=None):
    """n x n discrete palette sampled from the continuous blend, so the
    map keeps the chosen tones but steps through them gently."""
    return [[mpl.colors.to_hex(_blend_biv(i / (n - 1), j / (n - 1),
                                          biv))
             for j in range(n)] for i in range(n)]


def _key(ax, pal, qc_lbl, qd_lbl, kx=-161.0, ky=-44.0, S=30.0,
         tcol=None, big=False):
    """an n x n stepped key drawn like a real pair of axes, turned a
    quarter-turn anticlockwise from the way the palette is indexed:
    fuel demand runs UP the side (deepest market at the top) and
    hydrogen cost along the bottom (dearest to the right), so both
    axes read in the conventional direction and the build-first corner
    sits top-left. qc_lbl / qd_lbl are (fraction, value) pairs on the
    cheapness / demand axes, as the classing produces them."""
    n = len(pal)
    # big (2026-10-05: the key was hard to read): a larger
    # key with larger type; the paper's map uses it
    FT, FL, SW, DY = (7.0, 7.0, 3.0, 7.0) if big else (7.0, 7.0, 2.4, 6.0)   # 2026-10-22: main-text 7 pt
    if big:
        S, kx, ky = 36.0, -163.0, -46.0
    # the ground covers the key and its titles only: the verdict list
    # to its right already sits on open ocean, and a wider patch
    # reached across the Peruvian coast
    ax.add_patch(plt.Rectangle((kx - 22.0, ky - 12.4), S + (66.0 if big else 58.5),
                               S + 14.8, fc="white", ec="none",
                               alpha=0.9, zorder=4))
    sq = S / n
    for si in range(n):
        for di in range(n):
            ax.add_patch(plt.Rectangle((kx + di * sq,
                                        ky + si * sq), sq, sq,
                                       fc=pal[si][di], ec="white",
                                       lw=0.3, zorder=5))
    ax.add_patch(plt.Rectangle((kx, ky), S, S, fc="none", ec="#1A1A1A",
                               lw=0.6, zorder=6))
    for f, v in qd_lbl:                      # demand along the bottom
        x = kx + f * S
        ax.plot([x, x], [ky, ky - 1.0], color="#1A1A1A", lw=0.5,
                zorder=6, clip_on=False)
        ax.text(x, ky - 2.6, _fmt(v), fontsize=FT,   # 2026-10-22: clear of the cost labels at 7 pt
                ha="center", va="top", color="#1A1A1A", zorder=6)
    for f, v in qc_lbl:                      # cost up the side, cheap high
        y = ky + f * S
        ax.plot([kx, kx - 1.0], [y, y], color="#1A1A1A", lw=0.5,
                zorder=6, clip_on=False)
        ax.text(kx - 1.7, y, _fmt(v), fontsize=FT,
                ha="right", va="center", color="#1A1A1A", zorder=6)
    # the verdicts sit to the RIGHT of the key as a short list, so no
    # label crosses the palette or another label
    # 2026-10-05: parallel names, as the text uses them
    verdicts = [(pal[n - 1][n - 1], "Build-first"),
                (pal[n - 1][0], "Export-oriented"),
                (pal[0][n - 1], "Supply-strained"),
                (pal[0][0], "Limited potential")]
    lx = kx + S + 3.2
    for k, (col, txt) in enumerate(verdicts):
        ly = ky + S - 3.0 - k * DY
        ax.add_patch(plt.Rectangle((lx, ly - SW / 2), SW, SW, fc=col,
                                   ec="#3A4550", lw=0.3, zorder=6))
        ax.text(lx + SW + 1.0, ly, txt, fontsize=FL, ha="left",
                va="center", color="#3A4550", zorder=6)
    # the demand axis is the SYNTHETIC-FUEL market of the cell, stated
    # in the hydrogen it would take to make it, not a demand for
    # hydrogen as a product; the caption carries that sentence
    # name then unit in parentheses, the usual form, wrapped because
    # the demand unit spelled out is wider than the key is tall
    # a taller key lets the unit stand on one line: 10^6 rather than
    # "million", which also keeps an M for million away from the MM
    # of MMBtu
    ax.text(kx + S / 2, ky - (7.8 if big else 6.3),
            "Demand\n(million MMBtu yr$^{-1}$)",
            fontsize=7, ha="center", va="top", color="#1A1A1A",
            linespacing=1.3, zorder=6)
    ax.text(kx - 18.2, ky + S / 2,
            "Cost\n(US\$ MMBtu$^{-1}$)", fontsize=7,
            ha="center", va="center", rotation=90, linespacing=1.3,
            color="#1A1A1A", zorder=6)


def _classes8(df, biv=None):
    """octile classes on both axes + the quartile labels for the key."""
    qs = np.arange(1, ND) / ND
    qc8 = df.cost.quantile(qs).to_numpy()
    import os                        # 2026-10-08: later cost years on the reference year's cost cuts
    if os.environ.get("LCOF_SD_REF"):
        qc8 = pd.read_csv(os.environ["LCOF_SD_REF"], index_col=0).cost.quantile(qs).to_numpy()
    s8 = (ND - 1) - np.digitize(df.cost, qc8)
    live = df.dem > DEM_MIN
    qd8 = df.dem[live].quantile(qs).to_numpy()
    d8 = pd.Series(np.digitize(df.dem, qd8), index=df.index)
    d8[~live] = 0
    pal = _paln(n=ND, biv=biv)   # n must follow ND, not its default
    col = pd.Series([pal[s][d] for s, d in zip(s8, d8)], index=df.index)
    # the ticks are class boundaries, so the key's grid and the map's
    # isolines are the same cuts. With four bands or fewer every
    # boundary is labelled (terciles at three bands, quartiles at
    # four); above that only the three nearest the quartiles, or the
    # axis would carry seven numbers.
    ks = (tuple(range(1, ND)) if ND <= 4
          else (ND // 4, ND // 2, 3 * ND // 4))
    qc_lbl = [(1 - k / ND, qc8[k - 1]) for k in ks]
    qd_lbl = [(k / ND, qd8[k - 1]) for k in ks]
    # the ends of each axis as well as its internal cuts, so the key
    # states the range the map covers and not only where it is divided.
    # Cheap sits at the top of the cost axis, so the minimum cost is the
    # fraction-1 end; the demand axis starts at the thin-market floor.
    qc_lbl = ([(1.0, float(df.cost.min()))] + qc_lbl
              + [(0.0, float(df.cost.max()))])
    qd_lbl = ([(0.0, float(df.dem[live].min()))] + qd_lbl
              + [(1.0, float(df.dem.max()))])
    return col, pal, qc_lbl, qd_lbl


def main():
    # ---- both axes in the cell's own fuel ----------------------------------
    # cost: the demand-weighted levelized cost of the fuels this cell's
    # market needs, $/MMBtu of final fuel. Carbon is priced at the cell's
    # own cheapest CLIMATE-NEUTRAL source, so the weight on carbon is the
    # local demand mix times each fuel's carbon intensity rather than a
    # chosen number. Water is already inside the Stage-1 hydrogen cost
    # (0.09 t per MMBtu, at most $0.17 there) and nitrogen is unpriced,
    # because the air-separation unit's own electricity carries it.
    from .supply_demand import lcof_cells
    frames = {y: pd.read_csv(inputs.MAPS / f"lcoh_global_{y}{SUFFIX}.csv")
              .set_index("cell_id") for y in YEARS}
    cells = frames[YEARS[0]].index
    med_h2 = pd.Series(np.median(np.column_stack(
        [frames[y].loc[cells, "lcoh_usd_gj"] for y in YEARS]), axis=1),
        index=cells)
    med_el = pd.Series(np.median(np.column_stack(
        [frames[y].loc[cells, "lcoe_usd_mwh"] for y in YEARS]), axis=1),
        index=cells)

    meta = inputs.load_meta(2025)
    land = meta[meta.cell_type == "land"].copy()
    land = land.join(pd.DataFrame({"lcoh_usd_gj": med_h2,
                                   "lcoe_usd_mwh": med_el}), how="inner")
    land = land[np.isfinite(land.lcoh_usd_gj)]
    # each cell pays for the cheapest carbon it can actually reach
    # today: an industrial point source for 94% of the map at a median
    # $72/t, a biogenic source for 48 cells, and direct air capture at
    # $500 for the 105 Arctic cells with neither within range.
    co2 = pd.read_csv(inputs.MAPS / "co2_cost_by_cell.csv") \
            .set_index("cell_id").co2_cost.reindex(land.index)
    co2 = co2.fillna(P.C_CO2_DAC)
    lcof = lcof_cells(land, co2)               # $/GJ fuel, per fuel

    dg = pd.read_csv(inputs.MAPS / "demand_fuel_grid.csv", index_col=0)
    dem_gj = dg[[f + "_gj" for f in FUELS]].reindex(land.index).fillna(0.0)
    dem_gj.columns = FUELS
    tot_gj = dem_gj.sum(axis=1)
    # a cell with no market of its own is costed on the world mix, so it
    # still carries a comparable number
    wmix = dem_gj.sum() / dem_gj.sum().sum()
    sh = dem_gj.div(tot_gj.replace(0, np.nan), axis=0)
    sh = sh.fillna(wmix)
    # a price per MMBtu is 1.0551 times the price per GJ, because the MMBtu
    # is the larger unit; prices.py and every other figure convert this way.
    # The energy amount on the next line goes the other way (GJ / 1.0551).
    cost = (lcof[FUELS] * sh[FUELS]).sum(axis=1) * MMB_PER_GJ
    dem = tot_gj / MMB_PER_GJ / 1e6            # million MMBtu of fuel
    print("carbon weight = local demand mix x each fuel's intensity; "
          "world mix used for the %d cells with no market"
          % int((tot_gj <= 0).sum()))

    df = pd.DataFrame({"cost": cost, "dem": dem})
    df = df.join(land[["country"]], how="inner").dropna(subset=["cost"])

    # ---- classes -----------------------------------------------------------
    # terciles (kept: the regimes map and the headline statistics use them)
    qc = df.cost.quantile([1 / 3, 2 / 3]).to_numpy()
    # 2026-10-08 (maps for 2025/2030/2040/2050): later cost years keep the reference
    # year's cost breaks, so the cheap class can grow; LCOF_SD_REF = that year's sd_map_classes.csv
    import os
    _ref = os.environ.get("LCOF_SD_REF")
    if _ref:
        _rc = pd.read_csv(_ref, index_col=0).cost
        qc = _rc.quantile([1 / 3, 2 / 3]).to_numpy()
        print(f"cost breaks fixed at the reference year's terciles: {qc.round(2)} US$/MMBtu")
    df["s"] = 2 - np.digitize(df.cost, qc)
    live = df.dem[df.dem > DEM_MIN]
    qd = live.quantile([1 / 3, 2 / 3]).to_numpy()
    df["d"] = np.digitize(df.dem, qd)
    df.loc[df.dem <= DEM_MIN, "d"] = 0
    df["code"] = df.s * 3 + df.d
    # quintiles (the display: finer colour, class breaks on the key)
    qs = np.arange(1, N) / N
    qc5 = (_rc if _ref else df.cost).quantile(qs).to_numpy()
    df["s5"] = (N - 1) - np.digitize(df.cost, qc5)
    qd5 = live.quantile(qs).to_numpy()
    df["d5"] = np.digitize(df.dem, qd5)
    df.loc[df.dem <= DEM_MIN, "d5"] = 0
    df["code25"] = df.s5 * N + df.d5
    df.round(4).to_csv(inputs.MAPS / "sd_map_classes.csv")

    top = df[(df.s == 2) & (df.d == 2)]
    print(f"cost terciles: <=${qc[0]:.2f}, <=${qc[1]:.2f}/MMBtu | demand "
          f"terciles: <={qd[0]:.1f}, <={qd[1]:.1f} M MMBtu/yr")
    print(f"cheap-and-in-demand (top tercile both): {len(top)} of "
          f"{len(df)} cells, {top.dem.sum() / df.dem.sum():.0%} of world "
          f"demand")
    t5 = df[(df.s5 >= N - 2) & (df.d5 >= N - 2)]
    print(f"top two quintiles of both (the darkest key corner): "
          f"{len(t5)} cells, {t5.dem.sum() / df.dem.sum():.0%} of world "
          f"demand")
    print("cost quintile breaks $/MMBtu: "
          + ", ".join(f"{v:.2f}" for v in qc5))
    print("demand quintile breaks M MMBtu/yr: "
          + ", ".join(f"{v:.2f}" for v in qd5))
    print("  leading economies (cells, M MMBtu/yr):")
    g = top.groupby("country").agg(cells=("dem", "size"),
                                   dem=("dem", "sum"))
    for c, r in g.nlargest(8, "dem").iterrows():
        print(f"    {c:26s} {int(r.cells):3d}  {r.dem:8.0f}")

    # ---- map ---------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(183 * MM, 104 * MM))
    fig.subplots_adjust(left=0.005, right=0.995, top=0.985, bottom=0.005)
    col, pal, qc_lbl, qd_lbl = _classes8(df)
    _draw(ax, col, colours=True)
    _key(ax, pal, qc_lbl, qd_lbl)

    fig.savefig(OUT / "fig_sd_map.pdf", bbox_inches="tight")
    fig.savefig(OUT / "fig_sd_map.png", dpi=600, bbox_inches="tight")
    plt.close(fig)
    print("saved fig_sd_map.(pdf|png), sd_map_classes.csv")


def _blend(a, b):
    """bilinear blend of four corners: white (neither), blue (supply
    only), magenta (demand only), deep purple (both). a, b in [0, 1]."""
    import numpy as np
    W = np.array([0.960, 0.960, 0.960])
    B = np.array([0.060, 0.435, 0.820])       # cheap hydrogen
    M = np.array([0.902, 0.000, 0.494])       # deep market
    P4 = np.array([0.200, 0.035, 0.369])      # both
    a = a[:, None]
    b = b[:, None]
    return (W * (1 - a) * (1 - b) + B * a * (1 - b)
            + M * (1 - a) * b + P4 * a * b)


def continuous():
    """the same two layers, continuous, with two colour bars."""
    import numpy as np
    import pandas as pd
    df = pd.read_csv(inputs.MAPS / "sd_map_classes.csv", index_col=0)
    # percentile ranks: robust to the long tails on both axes
    a = (1.0 - df.cost.rank(pct=True)) ** 0.75        # cheaper -> 1
    live = df.dem > DEM_MIN
    b = pd.Series(0.0, index=df.index)
    b[live] = df.dem[live].rank(pct=True) ** 0.75     # only real markets
    rgb = _blend(a.to_numpy(), b.to_numpy())
    col = pd.Series([mpl.colors.to_hex(c) for c in rgb], index=df.index)

    fig, ax = plt.subplots(figsize=(183 * MM, 104 * MM))
    fig.subplots_adjust(left=0.005, right=0.995, top=0.985, bottom=0.005)
    g_cells = _GRID.copy()
    g_cells["c"] = g_cells["cell_id"].map(col)
    base = gpd.clip(g_cells[(g_cells.cell_type == "land")
                            & g_cells.c.isna()], _LAND_UNION)
    if len(base):
        base.plot(ax=ax, color=NODATA, linewidth=0, rasterized=True)
    rast = gpd.clip(g_cells[g_cells.c.notna()], _LAND_UNION)
    rast.plot(ax=ax, color=rast.c.tolist(), linewidth=0, rasterized=True)
    _COUNTRIES.boundary.plot(ax=ax, color="0.4", linewidth=0.1)
    ax.set_xlim(-180, 180)
    ax.set_ylim(-58, 84)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect("equal")
    for s in ax.spines.values():
        s.set_visible(False)

    # two colour bars, drawn as image strips so they show the real ramps
    for k, (lab, c1) in enumerate((
            ("cheaper hydrogen $\\rightarrow$", (0.060, 0.435, 0.820)),
            ("more hydrogen-equivalent demand $\\rightarrow$",
             (0.870, 0.180, 0.560)))):
        cax = fig.add_axes([0.055, 0.135 - k * 0.075, 0.20, 0.022])
        ramp = np.linspace(0, 1, 256)[None, :]
        cm = mpl.colors.LinearSegmentedColormap.from_list(
            f"r{k}", [(0.960, 0.960, 0.960), c1])
        cax.imshow(ramp, aspect="auto", cmap=cm)
        cax.set_xticks([])
        cax.set_yticks([])
        for s in cax.spines.values():
            s.set_visible(False)
        cax.set_xlabel(lab, fontsize=8, labelpad=2, color="#3A4550")
    ax.text(-176, -33, "where both are high the colours mix to deep "
            "purple:\nthe places worth building first", fontsize=8,
            color="#4F1C99", fontweight="bold", va="top",
            linespacing=1.3)

    fig.savefig(OUT / "fig_sd_map_cont.pdf", bbox_inches="tight")
    fig.savefig(OUT / "fig_sd_map_cont.png", dpi=600, bbox_inches="tight")
    plt.close(fig)
    print("saved fig_sd_map_cont.(pdf|png) — continuous variant")


def _draw(ax, cells_col, cmap=None, norm=None, colours=None):
    """paint the land cells of _GRID from a per-cell series."""
    g = _GRID.copy()
    g["v"] = g["cell_id"].map(cells_col)
    miss = gpd.clip(g[(g.cell_type == "land") & g.v.isna()], _LAND_UNION)
    if len(miss):
        miss.plot(ax=ax, color=NODATA, linewidth=0, rasterized=True)
    live = gpd.clip(g[g.v.notna()], _LAND_UNION)
    if colours is not None:
        live.plot(ax=ax, color=live.v.tolist(), linewidth=0,
                  rasterized=True)
    else:
        live.plot(column="v", cmap=cmap, norm=norm, ax=ax, linewidth=0,
                  rasterized=True)
    _COUNTRIES.boundary.plot(ax=ax, color="0.4", linewidth=0.1)
    ax.set_xlim(-180, 180)
    ax.set_ylim(-58, 84)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect("equal")
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_anchor("N")


# a higher-contrast variant of the same 3x3 scheme: the cost axis of
# the high-demand column runs light magenta -> magenta -> near-black
# violet, so cells that differ in cost inside one crowded market (all
# of Europe, all of east Asia) separate on the page. Same data, same
# class definition; only the tones and the number of steps change.
BIV_HI = [["#F2F2F2", "#F9B6D6", "#FF3DA1"],
          ["#7FB8E8", "#C061B4", "#A80063"],
          ["#0B5FC4", "#5B22A8", "#210545"]]


def _rank_fields(df):
    """the two axes as continuous percentile ranks on the 60x144 grid:
    u = cheapness (1 = cheapest), v = demand depth (0 where no market).
    Same ordering as the octile classes, without the steps."""
    import pandas as pd
    meta = inputs.load_meta(2025)
    u = 1.0 - df.cost.rank(pct=True)
    import os
    if os.environ.get("LCOF_SD_REF"):
        # 2026-10-08: rank against the reference year's cost distribution, so a later cost
        # year's cheaper cells move into the cheaper classes instead of being re-ranked
        ref = np.sort(pd.read_csv(os.environ["LCOF_SD_REF"], index_col=0).cost.to_numpy())
        u = pd.Series(1.0 - np.searchsorted(ref, df.cost.to_numpy(), side="right") / len(ref),
                      index=df.index).clip(0.0, 1.0)
    live = df.dem > DEM_MIN
    v = pd.Series(0.0, index=df.index)
    v[live] = df.dem[live].rank(pct=True)
    lat = meta.lat.reindex(df.index)
    lon = meta.lon.reindex(df.index)
    i = np.floor((lat.to_numpy() + 63.75) / 2.5).astype(int)
    j = (np.floor((lon.to_numpy() + 181.25) / 2.5).astype(int)) % 144
    U = np.full((60, 144), np.nan)
    V = np.full((60, 144), np.nan)
    ok = (i >= 0) & (i < 60)
    U[i[ok], j[ok]] = u.to_numpy()[ok]
    V[i[ok], j[ok]] = v.to_numpy()[ok]
    return U, V


def _fill_nearest(A, with_distance=False):
    """extend the field into the ocean by nearest neighbour so the
    interpolation has no holes, and report how far each point is from
    real data: land that is more than a cell away from any assessed
    cell (Greenland, the high Arctic) must not inherit a colour."""
    from scipy.ndimage import distance_transform_edt
    m = np.isnan(A)
    if not m.any():
        return (A, np.zeros_like(A)) if with_distance else A
    dist, idx = distance_transform_edt(m, return_distances=True,
                                       return_indices=True)
    out = A[tuple(idx)]
    return (out, dist) if with_distance else out


def _land_clip_patch(ax):
    """a matplotlib patch of the dissolved land polygon, for clipping."""
    from matplotlib.path import Path as MPath
    from matplotlib.patches import PathPatch
    from shapely.geometry import MultiPolygon
    geom = _LAND_UNION
    polys = geom.geoms if isinstance(geom, MultiPolygon) else [geom]
    verts, codes = [], []
    for poly in polys:
        for ring in [poly.exterior] + list(poly.interiors):
            xy = np.asarray(ring.coords)
            if len(xy) < 3:
                continue
            verts.append(xy)
            codes.append(np.r_[MPath.MOVETO,
                               np.full(len(xy) - 1, MPath.LINETO)])
    path = MPath(np.vstack(verts), np.concatenate(codes))
    return PathPatch(path, transform=ax.transData, fc="none", ec="none")


def full_smooth(zoom_factor=8, biv=None, tag="smooth", alpha=1.0):
    """fig_sd_map_full, painted as an interpolated field.

    Display only: the ranks are bilinearly interpolated between cell
    centres and the bivariate palette is applied continuously, so the
    map reads as a surface rather than as tiles. Every number in the
    text and in the key is still computed on the 2,740 cells.
    """
    import pandas as pd
    from scipy.ndimage import zoom as ndzoom
    df = pd.read_csv(inputs.MAPS / "sd_map_classes.csv", index_col=0)
    U, V = _rank_fields(df)
    Uf, dist = _fill_nearest(U, with_distance=True)
    Uz = ndzoom(Uf, zoom_factor, order=1, mode="nearest")
    Vz = ndzoom(_fill_nearest(V), zoom_factor, order=1, mode="nearest")
    Dz = ndzoom(dist, zoom_factor, order=1, mode="nearest")
    rgb = _blend_biv(np.clip(Uz, 0, 1), np.clip(Vz, 0, 1), biv)
    if alpha < 1.0:
        # alpha mixes the interpolated field with the cells' own colours
        # (nearest upsampling): edges soften, cell-scale contrast stays
        Un = ndzoom(Uf, zoom_factor, order=0, mode="nearest")
        Vn = ndzoom(_fill_nearest(V), zoom_factor, order=0, mode="nearest")
        tiled = _blend_biv(np.clip(Un, 0, 1), np.clip(Vn, 0, 1), biv)
        rgb = alpha * rgb + (1.0 - alpha) * tiled
    far = Dz > 1.2                       # no assessed cell within a cell
    rgb[far] = mpl.colors.to_rgb(NODATA)

    fig, ax = plt.subplots(figsize=(183 * MM, 78 * MM))
    fig.subplots_adjust(left=0.005, right=0.995, top=0.99, bottom=0.005)
    im = ax.imshow(rgb, origin="lower", interpolation="bilinear",
                   extent=(-181.25, 178.75, -63.75, 86.25), zorder=1,
                   rasterized=True)
    im.set_clip_path(_land_clip_patch(ax))
    _COUNTRIES.boundary.plot(ax=ax, color="0.4", linewidth=0.1)
    ax.set_xlim(-180, 180)
    ax.set_ylim(-58, 84)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect("equal")
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_anchor("N")
    col, pal, qc_lbl, qd_lbl = _classes8(df, biv=biv)
    _key(ax, pal, qc_lbl, qd_lbl)
    fig.savefig(OUT / f"fig_sd_map_full_{tag}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"fig_sd_map_full_{tag}.png", dpi=600,
                bbox_inches="tight")
    plt.close(fig)
    print(f"saved fig_sd_map_full_{tag}.(pdf|png) — interpolated field, "
          f"{zoom_factor}x between cell centres")


def full_crisp(zoom_factor=10, biv=None, tag="crisp"):
    """fig_sd_map_full as an isarithmic map: crisp, and not blocky.

    The two rank fields are interpolated between cell centres as in
    full_smooth, but the interpolated field is then RE-CLASSED into the
    same ND classes the key shows. Colour is therefore flat inside a
    class (no blur) while the boundary between classes follows a
    contour of the interpolated field (no 2.5-degree steps). Display
    only: classes, counts and key values still come from the cells.
    """
    import pandas as pd
    from scipy.ndimage import zoom as ndzoom
    df = pd.read_csv(inputs.MAPS / "sd_map_classes.csv", index_col=0)
    U, V = _rank_fields(df)
    Uf, dist = _fill_nearest(U, with_distance=True)
    Uz = ndzoom(Uf, zoom_factor, order=1, mode="nearest")
    Vz = ndzoom(_fill_nearest(V), zoom_factor, order=1, mode="nearest")
    Dz = ndzoom(dist, zoom_factor, order=1, mode="nearest")

    pal = _paln(n=ND, biv=biv)
    lut = np.array([[mpl.colors.to_rgb(c) for c in row] for row in pal])
    ui = np.clip((np.clip(Uz, 0, 1) * ND).astype(int), 0, ND - 1)
    vi = np.clip((np.clip(Vz, 0, 1) * ND).astype(int), 0, ND - 1)
    rgb = lut[ui, vi]
    rgb[Dz > 1.2] = mpl.colors.to_rgb(NODATA)

    fig, ax = plt.subplots(figsize=(183 * MM, 78 * MM))
    fig.subplots_adjust(left=0.005, right=0.995, top=0.99, bottom=0.005)
    im = ax.imshow(rgb, origin="lower", interpolation="nearest",
                   extent=(-181.25, 178.75, -63.75, 86.25), zorder=1,
                   rasterized=True)
    im.set_clip_path(_land_clip_patch(ax))
    _COUNTRIES.boundary.plot(ax=ax, color="0.4", linewidth=0.1)
    ax.set_xlim(-180, 180)
    ax.set_ylim(-58, 84)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect("equal")
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_anchor("N")
    col, pal2, qc_lbl, qd_lbl = _classes8(df, biv=biv)
    _key(ax, pal2, qc_lbl, qd_lbl)
    stem = "fig_sd_map_full" + (f"_{tag}" if tag else "")
    fig.savefig(OUT / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{stem}.png", dpi=600, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {stem}.(pdf|png) — {ND} classes on an "
          f"interpolated field, {zoom_factor}x")


def full_hicontrast():
    """fig_sd_map_full, redrawn with BIV_HI and finer steps."""
    import pandas as pd
    global ND
    df = pd.read_csv(inputs.MAPS / "sd_map_classes.csv", index_col=0)
    nd_old = ND
    ND = 16
    fig, c = plt.subplots(figsize=(183 * MM, 78 * MM))
    fig.subplots_adjust(left=0.005, right=0.995, top=0.99, bottom=0.005)
    col, pal, qc_lbl, qd_lbl = _classes8(df, biv=BIV_HI)
    _draw(c, col, colours=True)
    _key(c, pal, qc_lbl, qd_lbl)
    fig.savefig(OUT / "fig_sd_map_full_hicontrast.pdf",
                bbox_inches="tight")
    fig.savefig(OUT / "fig_sd_map_full_hicontrast.png", dpi=600,
                bbox_inches="tight")
    plt.close(fig)
    ND = nd_old
    print("saved fig_sd_map_full_hicontrast.(pdf|png) — 16 classes")


# the fused map's palette, assigned so that brightness tracks the
# verdict rather than the intensity of either variable: the two
# cheap-hydrogen corners take the two saturated hues (blue where no
# market is near, amber where the market is deep), the deep market
# that its own resource cannot serve cheaply takes black, and the
# corner with neither takes white. So the best case is the
# brightest thing on the page and the worst is the darkest. A black
# hairline cannot be seen on that black corner, which is why the
# internal borders below are drawn in a mid grey.
# the same two variables with the LIGHTNESS carrying quality instead
# of intensity: cheapness runs dark -> bright, demand runs blue ->
# orange, so the opportunity corner (cheap hydrogen, deep market) is
# the brightest and warmest thing on the page and the dear, deeply
# committed markets sit dark. The cost is that the empty, dear
# interiors go dark too, which the dark-corner convention avoids.
BIV_BG = [["#27323F", "#4A3A2C", "#6E3F10"],
          ["#6E93B4", "#A18E76", "#C87C15"],
          ["#BFE1F6", "#EADBAA", "#FFC223"]]


BIV_BO = [["#F7F7F7", "#FAEBC4", "#F3C64B"],
          ["#A6C8DF", "#CFC09B", "#DC9426"],
          ["#0072B2", "#7A6E86", "#A63603"]]


def _variogram(pts, z, nlag=18, hmax=14.0, nsamp=1400, seed=0):
    """Fit an exponential semivariogram to one rank field, in grid
    units: gamma(h) = nugget + (sill - nugget) (1 - exp(-3h/range)).
    Pairs are subsampled; 1,400 points give about a million pairs."""
    from scipy.optimize import curve_fit
    gen = np.random.default_rng(seed)
    k = min(nsamp, len(z))
    s = gen.choice(len(z), k, replace=False)
    P, Z = pts[s], z[s]
    d = np.hypot(P[:, None, 0] - P[None, :, 0],
                 P[:, None, 1] - P[None, :, 1])
    g = 0.5 * (Z[:, None] - Z[None, :]) ** 2
    iu = np.triu_indices(k, 1)
    d, g = d[iu], g[iu]
    edges = np.linspace(0.0, hmax, nlag + 1)
    idx = np.digitize(d, edges) - 1
    hs, gs = [], []
    for b in range(nlag):
        m = idx == b
        if m.sum() > 50:
            hs.append(d[m].mean())
            gs.append(g[m].mean())
    hs, gs = np.array(hs), np.array(gs)

    def model(h, nug, sill, rng):
        return nug + (sill - nug) * (1.0 - np.exp(-3.0 * h / rng))

    p0 = [gs[0] * 0.5, gs[-1], hmax / 3.0]
    try:
        par, _ = curve_fit(model, hs, gs, p0=p0, maxfev=20000,
                           bounds=([0.0, 1e-9, 0.3],
                                   [gs[-1], gs[-1] * 4.0, hmax * 2.0]))
    except Exception:
        par = p0
    return model, tuple(float(x) for x in par)


def _krige(A, zoom, k=24, halo=1.6, seed=0):
    """Ordinary kriging of one rank field from the 2.5-degree cell
    centres onto a zoom-times finer grid.

    A bilinear zoom of a coarse mesh leaves the cell centres visible as
    diamond-shaped artefacts, and the class boundaries drawn on it
    inherit the mesh. Kriging weights each neighbour by the fitted
    spatial correlation instead, so the surface is smooth in the way
    the data supports. Local: each target point uses its k nearest
    observations, which avoids a dense 2,740-square solve per point.
    Longitude wraps, so the observations are replicated either side of
    the dateline and the seam is interpolated rather than cut.
    """
    from scipy.spatial import cKDTree
    from scipy.ndimage import distance_transform_edt, zoom as ndzoom
    ny, nx = A.shape
    ii, jj = np.nonzero(~np.isnan(A))
    z = A[ii, jj]
    pts = np.column_stack([np.r_[ii, ii, ii],
                           np.r_[jj, jj - nx, jj + nx]]).astype(float)
    zz = np.r_[z, z, z]
    model, par = _variogram(np.column_stack([ii, jj]).astype(float), z,
                            seed=seed)

    dist = distance_transform_edt(np.isnan(A))
    Dz = ndzoom(dist, zoom, order=1, mode="nearest")
    Y, X = np.mgrid[0:ny * zoom, 0:nx * zoom]
    ty = (Y + 0.5) / zoom - 0.5
    tx = (X + 0.5) / zoom - 0.5
    want = Dz <= halo
    T = np.column_stack([ty[want], tx[want]])

    tree = cKDTree(pts)
    nb = tree.query(T, k=k, workers=-1)[1]
    out = np.empty(T.shape[0])
    CH = 40000
    for a in range(0, len(T), CH):
        b = min(a + CH, len(T))
        nbi = nb[a:b]
        P = pts[nbi]
        Zn = zz[nbi]
        dnn = np.hypot(P[:, :, None, 0] - P[:, None, :, 0],
                       P[:, :, None, 1] - P[:, None, :, 1])
        d0 = np.hypot(P[:, :, 0] - T[a:b, None, 0],
                      P[:, :, 1] - T[a:b, None, 1])
        m = b - a
        M = np.zeros((m, k + 1, k + 1))
        M[:, :k, :k] = model(dnn, *par)
        M[:, np.arange(k), np.arange(k)] = 0.0
        M[:, :k, k] = 1.0
        M[:, k, :k] = 1.0
        r = np.zeros((m, k + 1))
        r[:, :k] = model(d0, *par)
        r[:, k] = 1.0
        M[:, np.arange(k), np.arange(k)] += 1e-9
        w = np.linalg.solve(M, r[:, :, None])[:, :k, 0]
        out[a:b] = np.einsum("mk,mk->m", w, Zn)
    F = np.zeros((ny * zoom, nx * zoom))
    F[want] = np.clip(out, 0.0, 1.0)
    return F, Dz, par


def full_krige(zoom_factor=10, biv=None, tag="krige", k=24, big_key=False):
    """fig_sd_map_full with the interpolation done by ordinary kriging
    and the result re-classed into the same ND classes the key shows.
    Display only: classes, counts and key values still come from the
    2,740 cells."""
    import pandas as pd
    df = pd.read_csv(inputs.MAPS / "sd_map_classes.csv", index_col=0)
    U, V = _rank_fields(df)
    Uz, Dz, pu = _krige(U, zoom_factor, k=k)
    Vz, _, pv = _krige(V, zoom_factor, k=k)

    pal = _paln(n=ND, biv=biv)
    lut = np.array([[mpl.colors.to_rgb(c) for c in row] for row in pal])
    ui = np.clip((np.clip(Uz, 0, 1) * ND).astype(int), 0, ND - 1)
    vi = np.clip((np.clip(Vz, 0, 1) * ND).astype(int), 0, ND - 1)
    rgb = lut[ui, vi]
    rgb[Dz > 1.2] = mpl.colors.to_rgb(NODATA)

    fig, ax = plt.subplots(figsize=(183 * MM, 78 * MM))
    fig.subplots_adjust(left=0.005, right=0.995, top=0.99, bottom=0.005)
    im = ax.imshow(rgb, origin="lower", interpolation="nearest",
                   extent=(-181.25, 178.75, -63.75, 86.25), zorder=1,
                   rasterized=True)
    clip = _land_clip_patch(ax)
    im.set_clip_path(clip)
    # the class boundaries drawn as isolines: with three bands per
    # axis the steps are wide enough to read, and the lines say that
    # a boundary is a contour of the field, not an artefact
    ext = (-181.25, 178.75, -63.75, 86.25)
    yy = np.linspace(ext[2], ext[3], Uz.shape[0])
    xx = np.linspace(ext[0], ext[1], Uz.shape[1])
    lev = np.arange(1, ND) / ND
    for F in (Uz, Vz):
        cs = ax.contour(xx, yy, np.where(Dz <= 1.2, F, np.nan),
                        levels=lev, colors="#3A4550",
                        linewidths=0.11, alpha=0.45, zorder=2.5)
        cs.set_clip_path(clip)          # matplotlib 3.8+: one artist
    _COUNTRIES.boundary.plot(ax=ax, color="#1A1A1A", linewidth=0.09,
                             zorder=2)
    gpd.GeoSeries([_LAND_UNION]).boundary.plot(
        ax=ax, color="#1A1A1A", linewidth=0.18, zorder=3)
    ax.set_xlim(-180, 180)
    ax.set_ylim(-58, 84)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect("equal")
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_anchor("N")
    col, pal2, qc_lbl, qd_lbl = _classes8(df, biv=biv)
    _key(ax, pal2, qc_lbl, qd_lbl, big=big_key)
    stem = "fig_sd_map_full" + ("_" + tag if tag else "")
    fig.savefig(OUT / (stem + ".pdf"), bbox_inches="tight")
    fig.savefig(OUT / (stem + ".png"), dpi=600, bbox_inches="tight")
    plt.close(fig)
    print("saved %s.(pdf|png) - %d classes, ordinary kriging at %dx, "
          "%d neighbours; variogram range %.1f / %.1f cells "
          "(cost / demand), nugget share %.2f / %.2f"
          % (stem, ND, zoom_factor, k, pu[2], pv[2],
             pu[0] / pu[1], pv[0] / pv[1]))


def full(nd=3, biv=None):
    """the fused map alone, full width: THE main-text figure. The two
    ingredient layers keep their own figures (the hydrogen cost map in
    Extended Data, the demand maps in the demand figure).

    Rendered isarithmically on the high-contrast palette: colour is
    flat inside a class, and a class boundary follows a contour of the
    interpolated rank field instead of the 2.5-degree cell edge, so the
    map reads as a field rather than as tiles. The interpolation is
    ordinary kriging against a fitted exponential variogram, which
    beats the bilinear zoom it replaced on leave-one-out error and
    leaves none of its diamond artefacts. Classes, counts and key
    values still come from the cells. full_grid() keeps the plain cell
    rendering for the record.
    """
    global ND
    nd_old = ND
    ND = nd
    try:
        full_krige(zoom_factor=10, biv=biv if biv is not None else BIV_BO,
                   tag="", big_key=True)
    finally:
        ND = nd_old


def full_grid():
    """fig_sd_map_full as plain 2.5-degree cells, the pre-isarithmic
    rendering. Kept so the two can be compared."""
    import pandas as pd
    df = pd.read_csv(inputs.MAPS / "sd_map_classes.csv", index_col=0)

    fig, c = plt.subplots(figsize=(183 * MM, 78 * MM))
    fig.subplots_adjust(left=0.005, right=0.995, top=0.99, bottom=0.005)
    col, pal, qc_lbl, qd_lbl = _classes8(df)
    _draw(c, col, colours=True)
    _key(c, pal, qc_lbl, qd_lbl)

    fig.savefig(OUT / "fig_sd_map_full_grid.pdf", bbox_inches="tight")
    fig.savefig(OUT / "fig_sd_map_full_grid.png", dpi=600,
                bbox_inches="tight")
    plt.close(fig)
    print("saved fig_sd_map_full_grid.(pdf|png) — plain cells")


# candidate bivariate palettes, all in the same 3x3 convention as BIV
# (row = supply class dearest->cheapest, col = demand class none->deep)
PALETTES = {
    "blue x magenta (current)": BIV,
    "Stevens dark violet (blue x red)":
        [["#CABED0", "#BC7C8F", "#AE3A4E"],
         ["#89A1C8", "#806A8A", "#77324C"],
         ["#4885C1", "#435786", "#3F2949"]],
    "Stevens dark blue (muted red x blue)":
        [["#E8E8E8", "#E4ACAC", "#C85A5A"],
         ["#B0D5DF", "#AD9EA5", "#985356"],
         ["#64ACBE", "#627F8C", "#574249"]],
    "green supply x blue demand":
        [["#E8E8E8", "#B5C0DA", "#6C83B5"],
         ["#B8D6BE", "#90B2B3", "#567994"],
         ["#73AE80", "#5A9178", "#2A5A5B"]],
    "teal x pink":
        [["#F1F1F1", "#E6A5C8", "#D9418C"],
         ["#9CCFC8", "#9A9EC2", "#8F3C7F"],
         ["#31A29B", "#3A6F96", "#3B2E64"]],
    "gold demand x blue supply":
        [["#E8E8E8", "#E0C47C", "#C8932B"],
         ["#94BFDD", "#9AA680", "#8F7B2E"],
         ["#3D7DB8", "#4A6B71", "#4A4A2A"]],
}


def palettes():
    """the fused map under six candidate palettes, one sheet, so the
    choice is made by looking, not arguing."""
    df = pd.read_csv(inputs.MAPS / "sd_map_classes.csv", index_col=0)
    a_rank = 1.0 - df.cost.rank(pct=True)
    b_rank = pd.Series(0.0, index=df.index)
    lv = df.dem > 0.5
    b_rank[lv] = df.dem[lv].rank(pct=True)

    nrow, ncol = 3, 2
    fig = plt.figure(figsize=(183 * MM, 190 * MM))
    for k, (name, biv) in enumerate(PALETTES.items()):
        r, cix = divmod(k, ncol)
        ax = fig.add_axes([0.005 + cix * 0.5, 0.665 - r * 0.325,
                           0.49, 0.30])
        rgb = _blend_biv(a_rank.to_numpy(), b_rank.to_numpy(), biv)
        col = pd.Series([mpl.colors.to_hex(cc) for cc in rgb],
                        index=df.index)
        _draw(ax, col, colours=True)
        ax.set_title(name, fontsize=8, pad=2,
                     color=biv[2][2], fontweight="bold")
        # small key square, no numbers: this sheet is about the colours
        n = 96
        g = (np.arange(n) + 0.5) / n
        img = _blend_biv(np.repeat(g[:, None], n, 1),
                         np.repeat(g[None, :], n, 0), biv)
        ax.imshow(img, extent=(-176, -146, -54, -24), origin="lower",
                  interpolation="bilinear", zorder=5)

    fig.savefig(OUT / "fig_sd_palettes.pdf", bbox_inches="tight")
    fig.savefig(OUT / "fig_sd_palettes.png", dpi=450,
                bbox_inches="tight")
    plt.close(fig)
    print("saved fig_sd_palettes.(pdf|png) — 6 candidate palettes")


def palette_finals():
    """the fused map, full size, in the two shortlisted alternative
    palettes: Stevens dark violet and teal x pink."""
    import pandas as pd
    df = pd.read_csv(inputs.MAPS / "sd_map_classes.csv", index_col=0)
    picks = {"dkviolet": PALETTES["Stevens dark violet (blue x red)"],
             "tealpink": PALETTES["teal x pink"]}
    for tag, biv in picks.items():
        fig, c = plt.subplots(figsize=(183 * MM, 78 * MM))
        fig.subplots_adjust(left=0.005, right=0.995, top=0.99,
                            bottom=0.005)
        col, pal, qc_lbl, qd_lbl = _classes8(df, biv)
        _draw(c, col, colours=True)
        _key(c, pal, qc_lbl, qd_lbl, tcol=biv[2][2])
        fig.savefig(OUT / f"fig_sd_map_{tag}.pdf", bbox_inches="tight")
        fig.savefig(OUT / f"fig_sd_map_{tag}.png", dpi=450,
                    bbox_inches="tight")
        plt.close(fig)
        print(f"saved fig_sd_map_{tag}.(pdf|png)")


if __name__ == "__main__":
    import sys
    if "--krige" in sys.argv:
        ND = 16
        full_krige(biv=BIV_HI, tag="krige")
        full_krige(biv=BIV_BO, tag="krige_bo")
        full_krige(biv=BIV_BG, tag="krige_bright")
    elif "--crisp" in sys.argv:
        full_crisp()
    elif "--smooth" in sys.argv:
        full_smooth()
    elif "--soft" in sys.argv:
        full_smooth(zoom_factor=6, alpha=0.45, tag="soft")
    elif "--hicontrast" in sys.argv:
        full_hicontrast()
    else:
        main()
        continuous()
        full()
        full_grid()
