"""
corridor_maps.py — talk graphics for the v4 job-talk deck, built on the
V1.4 manuscript (2026-10-02). In v4 each method has its own slide and is
followed by the figure it produces, and every method slide shows the paper's
own equation with its terms named (Methods and Supplementary Information).
Nothing here is new analysis.

  title    jt14_title_bg: the Fig. 2 field as the paper draws it (ordinary
           kriging between cell centres, re-classed), lightened, with the
           three chokepoints and the European gas price; 300 dpi
  logic    jt14_logic and jt14_logic_p1..p4 (one part highlighted)
  methods  jt14_m_lp, jt14_m_demand, jt14_m_match, jt14_m_prices,
           jt14_m_security, jt14_m_voll, jt14_m_tipping, jt14_m_trajectory,
           jt14_m_budget (the fuel cascade keeps jt13_m_cascade)
  fig2     jt14_f2_cost, jt14_f2_demand, jt14_f2_pair, jt14_f2_merged,
           jt14_f2_corridors (transparent overlay), all on one geometry so the
           merge animation lines up
  zoom     jt14_zoom6: six regions with the cell-to-cell flows of
           Supplementary Note 6 (transport_flows) and the corridors
  smooth   jt14_smooth: one region as computed (2.5-degree cells) and as drawn
  table    jt14_table1: Table 1 typeset on its own (pdflatex, pdftoppm)

From scripts/:  python -m lcof.corridor_maps [jobs]
Outputs:        cf_global_final/figures/slides2026/v14/*.png
Nothing here writes to data/cost or to the paper's figure folder.
"""
from __future__ import annotations

import re
import shutil
import subprocess

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

mpl.use("Agg")

from . import inputs
from .map_layers import (BLUE, FITTED, GREEN, GREY, INK, LIGHT, PALE, PURPLE, RED, STYLE,
                                  W, H, _arrow, _box, _fit_text)

OUT = inputs.PROJECT / "cf_global_final" / "figures" / "slides2026" / "v14"
OUT.mkdir(parents=True, exist_ok=True)
MAG, INKC, GREYC, SHADE = "#B4116F", "#1F3A5F", "#8A94A0", "#E3F2EA"   # Fig. 4a markers
PART_COL = {1: BLUE, 2: "#A0661A", 3: RED, 4: GREEN, 5: PURPLE}
UMM = 1.0551                                                           # GJ per MMBtu
EXT = (-181.25, 178.75, -63.75, 86.25)                                 # the 60 x 144 grid
MAPW = 12.9
MAPH = MAPW * 142 / 360


def _style():
    mpl.rcParams.update(mpl.rcParamsDefault)
    mpl.rcParams.update(STYLE)
    mpl.rcParams.update({"text.latex.preamble": r"\usepackage{amsmath}\usepackage{amssymb}"})


def _save(fig, name, dpi=220, **kw):
    fig.savefig(OUT / f"{name}.png", dpi=dpi, facecolor=kw.pop("facecolor", "white"), **kw)
    plt.close(fig)
    print(f"  saved {name}")


def _canvas(w=W, h=H):
    fig = plt.figure(figsize=(w, h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    return fig, ax


def _eq(ax, x, y, tex, fs, maxw, ha="left", va="center", color=INK):
    """a LaTeX equation at (x, y) in inches, shrunk until it is at most maxw wide"""
    fig = ax.figure
    r = fig.canvas.get_renderer()
    t = ax.text(x, y, tex, usetex=True, fontsize=fs, color=color, ha=ha, va=va, zorder=3)
    while fs > 12 and t.get_window_extent(renderer=r).width > maxw * fig.dpi:
        fs -= 0.5
        t.set_fontsize(fs)
    FITTED.append(("eq", fs))
    return t


def _words(ax, x, y, s, fs=16, color=GREY, bold=False, ha="left", va="center", lsp=1.25, **kw):
    return ax.text(x, y, s, fontsize=fs, color=color, fontweight="bold" if bold else "normal",
                   ha=ha, va=va, linespacing=lsp, zorder=3, **kw)


def _rule(ax, y, x0=0.3, x1=W - 0.3):
    ax.plot([x0, x1], [y, y], color="#C8CFD8", lw=1.0)


# ====================================================================== Fig. 2 field
def _sd():
    from . import fig_sd_map as SD
    df = pd.read_csv(inputs.MAPS / "sd_map_classes.csv", index_col=0)
    return SD, df


def _kriged():
    """the two rank fields of Fig. 2 kriged to 10x the grid, as fig_sd_map.full does"""
    SD, df = _sd()
    cache = OUT / "_fig2_kriged.npz"
    if cache.exists():
        z = np.load(cache)
        return SD, df, z["Uz"], z["Vz"], z["Dz"]
    U, V = SD._rank_fields(df)
    Uz, Dz, _ = SD._krige(U, 10, k=24)
    Vz, _, _ = SD._krige(V, 10, k=24)
    np.savez_compressed(cache, Uz=Uz, Vz=Vz, Dz=Dz)
    return SD, df, Uz, Vz, Dz


def _cuts():
    """tercile cuts of Fig. 2: cost (US$/MMBtu) and demand (million MMBtu/yr), as labels"""
    _, df = _sd()
    c = df.groupby("s").cost.min()
    d = df.groupby("d").dem.min()
    return (f"{c[2 - 1]:.0f}", f"{c[0]:.0f}"), (f"{d[1]:.1f}", f"{d[2]:.0f}")


def _pal(SD):
    return SD._paln(n=3, biv=SD.BIV_BO)          # rows dearest -> cheapest, columns no -> deep demand


def _class_rgb(SD, Uz, Vz, Dz, light=0.0, mode="both"):
    pal = _pal(SD)
    lut = np.array([[mpl.colors.to_rgb(c) for c in row] for row in pal])
    ui = np.clip((np.clip(Uz, 0, 1) * 3).astype(int), 0, 2)
    vi = np.clip((np.clip(Vz, 0, 1) * 3).astype(int), 0, 2)
    if mode == "cost":
        vi = np.zeros_like(vi)
    elif mode == "demand":
        ui = np.zeros_like(ui)
    rgb = lut[ui, vi]
    rgb[Dz > 1.2] = mpl.colors.to_rgb(SD.NODATA)
    return 1.0 - (1.0 - light) * (1.0 - rgb) if light else rgb


def _cell_rgb(SD, df):
    meta = inputs.load_meta(2025)
    lut = np.array([[mpl.colors.to_rgb(c) for c in row] for row in _pal(SD)])
    i = np.floor((meta.lat.reindex(df.index).to_numpy() + 63.75) / 2.5).astype(int)
    j = (np.floor((meta.lon.reindex(df.index).to_numpy() + 181.25) / 2.5).astype(int)) % 144
    rgb = np.ones((60, 144, 3))
    rgb[:] = mpl.colors.to_rgb(SD.NODATA)
    ok = (i >= 0) & (i < 60)
    rgb[i[ok], j[ok]] = lut[df.s.to_numpy()[ok], df.d.to_numpy()[ok]]
    return rgb


def _paint(ax, SD, rgb, lw=1.0, alpha=None):
    import geopandas as gpd
    img = rgb if alpha is None else np.dstack([rgb, np.full(rgb.shape[:2], alpha)])
    im = ax.imshow(img, origin="lower", interpolation="nearest", extent=EXT, zorder=1)
    im.set_clip_path(SD._land_clip_patch(ax))
    SD._COUNTRIES.boundary.plot(ax=ax, color="#1A1A1A", linewidth=0.16 * lw, zorder=2)
    gpd.GeoSeries([SD._LAND_UNION]).boundary.plot(ax=ax, color="#1A1A1A", linewidth=0.32 * lw, zorder=3)


def _map_fig(w=MAPW, transparent=False):
    fig = plt.figure(figsize=(w, w * 142 / 360))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(-180, 180)
    ax.set_ylim(-58, 84)
    ax.set_aspect("equal")
    ax.axis("off")
    if transparent:
        fig.patch.set_alpha(0)
        ax.patch.set_alpha(0)
    return fig, ax


def title_bg():
    _style()
    from . import prices as PR
    import geopandas as gpd
    SD, df, Uz, Vz, Dz = _kriged()
    rgb = _class_rgb(SD, Uz, Vz, Dz, light=0.36)
    Wt, Ht = 13.333, 7.5
    fig = plt.figure(figsize=(Wt, Ht))
    mh = Wt * 142 / 360
    ax = fig.add_axes([0, (Ht - 0.1 - mh) / Ht, 1, mh / Ht])
    im = ax.imshow(rgb, origin="lower", interpolation="bilinear", extent=EXT, zorder=1)
    im.set_clip_path(SD._land_clip_patch(ax))
    SD._COUNTRIES.boundary.plot(ax=ax, color="#C3CBD3", linewidth=0.25, zorder=2)
    gpd.GeoSeries([SD._LAND_UNION]).boundary.plot(ax=ax, color="#9FAAB5", linewidth=0.45, zorder=3)
    for lon, lat in ((56.3, 26.6), (43.3, 12.6), (32.5, 30.0)):      # Hormuz, Bab el-Mandeb, Suez
        for rad, a in ((3.4, 0.45), (2.1, 0.75)):
            ax.add_patch(Circle((lon, lat), rad, fill=False, ec="#C9765A", lw=1.5, alpha=a, zorder=4))
    ax.set_xlim(-180, 180)
    ax.set_ylim(-58, 84)
    ax.set_aspect("equal")
    ax.axis("off")
    g = PR.load(verified=False).loc["2006-01":"2026-08", "gas_eu"] * UMM
    t = np.array([p.year + (p.month - 0.5) / 12 for p in g.index])
    b = fig.add_axes([0, 0.012, 1, 0.20])
    b.fill_between(t, 0, g.values, color="#F4DDD2", lw=0)
    b.plot(t, g.values, color="#DDA084", lw=1.6, solid_joinstyle="round")
    b.set_xlim(2006, 2026.7)
    b.set_ylim(0, g.max() * 1.04)
    b.axis("off")
    f = fig.add_axes([0, 0, 1, 1], zorder=10)
    xs = np.linspace(0, 1, 512)
    u = np.clip((xs - 0.56) / (0.93 - 0.56), 0, 1)
    grad = 1.0 - u * u * (3 - 2 * u)                    # smoothstep: white under the title, map on the right
    f.imshow(np.dstack([np.ones((1, 512, 3)), grad[None, :, None] * 0.96]), extent=(0, 1, 0, 1),
             aspect="auto", interpolation="bicubic")
    f.set_xlim(0, 1)
    f.set_ylim(0, 1)
    f.axis("off")
    fig.savefig(OUT / "jt14_title_bg.png", dpi=300, facecolor="white")
    plt.close(fig)
    print("  saved jt14_title_bg")


# -------------------------------------------------------------- Fig. 2 sequence
def _key_cost(ax, pal, x0=-172, y0=-54, s=11.0):
    for k, r in enumerate((0, 1, 2)):                    # bottom: dearest third
        ax.add_patch(Rectangle((x0, y0 + k * s), s, s, fc=pal[r][0], ec="#555555", lw=0.6, zorder=6))
    c1, c2 = _cuts()[0]
    for k, lab in ((1, c2), (2, c1)):
        ax.text(x0 + s + 1.5, y0 + k * s, lab, fontsize=13, color=INK, va="center", zorder=6)
    ax.text(x0 + s + 1.5, y0 + 0.5 * s, "dearest third", fontsize=12, color=GREY, va="center", zorder=6)
    ax.text(x0 + s + 1.5, y0 + 2.5 * s, "cheapest third", fontsize=12, color=GREY, va="center", zorder=6)
    ax.text(x0, y0 + 3 * s + 3, "Cost, US\\$ per MMBtu", fontsize=14, color=INK, fontweight="bold", zorder=6)


def _key_demand(ax, pal, x0=-172, y0=-46, s=11.0):
    for k in range(3):
        ax.add_patch(Rectangle((x0 + k * s, y0), s, s, fc=pal[0][k], ec="#555555", lw=0.6, zorder=6))
    for k, lab in ((1, "1.5"), (2, "15")):
        ax.text(x0 + k * s, y0 - 2.0, lab, fontsize=13, color=INK, ha="center", va="top", zorder=6)
    ax.text(x0 + 3 * s + 2, y0 + s / 2, "deepest third", fontsize=12, color=GREY, va="center", zorder=6)
    ax.text(x0, y0 + s + 3, "Demand, million MMBtu per year", fontsize=14, color=INK, fontweight="bold",
            zorder=6)


def _key_both(ax, pal, x0=-164, y0=-45, s=10.0):
    for r in range(3):
        for c in range(3):
            ax.add_patch(Rectangle((x0 + c * s, y0 + r * s), s, s, fc=pal[r][c], ec="white", lw=0.8, zorder=6))
    c1, c2 = _cuts()[0]
    for r, lab in ((1, c2), (2, c1)):
        ax.text(x0 - 1.2, y0 + r * s, lab, fontsize=13.5, color=INK, ha="right", va="center", zorder=6)
    for c, lab in ((1, "1.5"), (2, "15")):
        ax.text(x0 + c * s, y0 - 1.2, lab, fontsize=13.5, color=INK, ha="center", va="top", zorder=6)
    ax.text(x0 - 12.5, y0 + 1.5 * s, "cost", fontsize=13.5, color=GREY, ha="center", va="center", rotation=90,
            zorder=6)
    ax.text(x0 + 1.5 * s, y0 - 7.0, "demand", fontsize=13.5, color=GREY, ha="center", va="center", zorder=6)
    roles = [(pal[2][2], "Build-first"), (pal[2][0], "Export-oriented"), (pal[0][2], "Supply-strained"),
             (pal[0][0], "Limited potential")]
    for k, (col, name) in enumerate(roles):
        y = y0 + 3 * s - 3.5 - k * 7.6
        ax.add_patch(Rectangle((x0 + 3 * s + 5, y - 2.8), 5.6, 5.6, fc=col, ec="#555555", lw=0.6, zorder=6))
        ax.text(x0 + 3 * s + 12.5, y, name, fontsize=13.5, color=INK, va="center", zorder=6)


def fig2_layers():
    _style()
    SD, df, Uz, Vz, Dz = _kriged()
    pal = _pal(SD)
    for name, mode, key in (("jt14_f2_cost", "cost", _key_cost), ("jt14_f2_demand", "demand", _key_demand),
                            ("jt14_f2_merged", "both", _key_both)):
        fig, ax = _map_fig()
        _paint(ax, SD, _class_rgb(SD, Uz, Vz, Dz, mode=mode))
        key(ax, pal)
        _save(fig, name, dpi=260)
    # the two inputs side by side, for the start of the merge slide
    fig = plt.figure(figsize=(MAPW, 3.05))
    for k, (mode, head) in enumerate((("cost", "Cost of the fuels each local market requires"),
                                      ("demand", "Addressable demand"))):
        ax = fig.add_axes([0.0 + k * 0.508, 0.0, 0.492, 0.84])
        ax.set_xlim(-180, 180)
        ax.set_ylim(-58, 84)
        ax.set_aspect("equal")
        ax.axis("off")
        _paint(ax, SD, _class_rgb(SD, Uz, Vz, Dz, mode=mode), lw=0.6)
        fig.text(0.246 + k * 0.508, 0.93, head, fontsize=16, color=INK, fontweight="bold", ha="center",
                 va="center")
    fig.text(0.5, 0.45, "+", fontsize=34, color=INK, ha="center", va="center", fontweight="bold")
    _save(fig, "jt14_f2_pair", dpi=260)
    corridors_overlay()


CORR = [  # name, mode, waypoints (lon, lat), short label, label centre (lon, lat), transport US$/MMBtu, saving %
    ("Iberia → Germany", "land", [(-4.0, 39.8), (3.0, 46.0), (10.0, 50.8)], "Iberia → Germany", (-31, 53.5),
     3.17, 10.3),
    ("North Africa → Italy", "land", [(4.0, 32.0), (8.0, 38.5), (11.5, 44.5)], "North Africa → Italy", (-33, 40),
     4.58, 46.2),
    ("Inner Mongolia → North China Plain", "land", [(108.5, 41.5), (113.5, 40.2), (116.5, 37.5)],
     "Inner Mongolia →\nBeijing", (159, 28), 2.28, 31.4),
    ("Pilbara → Japan", "sea", [(117.0, -20.0), (115.0, -10.5), (118.5, -1.5), (125.0, 9.5), (131.5, 22.0),
                                 (138.5, 33.8)], "Pilbara → Japan", (156, 5), 1.60, 52.4),
    ("Northern Chile → Rotterdam, via Panama", "sea",
     [(-71.0, -23.5), (-79.5, -8.0), (-79.8, 6.5), (-73.0, 14.0), (-60.0, 19.0), (-38.0, 22.0), (-20.0, 27.0),
      (-12.5, 36.5), (-10.8, 44.0), (-5.5, 48.8), (3.0, 51.8)], "Northern Chile → Rotterdam\n(via Panama)",
     (-112, 1), 2.08, 60.5),
    ("Oman → Rotterdam, via Suez", "sea",
     [(57.5, 19.3), (51.0, 13.6), (44.0, 12.3), (38.5, 20.5), (33.3, 28.8), (25.0, 34.0), (10.0, 37.6),
      (-6.0, 36.0), (-10.0, 41.0), (-6.5, 48.2), (3.0, 51.8)], None, None, 1.85, 45.8),
    ("Oman → Rotterdam, via the Cape", "sea",
     [(57.5, 19.3), (56.0, 5.0), (47.0, -15.0), (35.0, -31.0), (19.0, -37.0), (7.0, -24.0), (-6.0, -4.0),
      (-17.0, 15.0), (-16.0, 28.0), (-11.0, 40.0), (-6.5, 48.6), (3.0, 51.8)], None, None, 2.56, 44.8),
]


def _spline(pts, n=240):
    from scipy.interpolate import make_interp_spline
    P = np.array(pts, float)
    dd = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    k = min(3, len(P) - 1)
    tt = np.linspace(0, dd[-1], n)
    return make_interp_spline(dd, P[:, 0], k=k)(tt), make_interp_spline(dd, P[:, 1], k=k)(tt)


def _draw_corridor(ax, pts, mode, lw=1.0):
    x, y = _spline(pts)
    halo = [pe.withStroke(linewidth=(4.6 if mode == "land" else 3.4) * lw, foreground="white")]
    ax.plot(x, y, color=INK, lw=(2.6 if mode == "land" else 1.6) * lw, ls="-" if mode == "land" else (0, (4, 2)),
            zorder=7, path_effects=halo, solid_capstyle="round")
    ax.annotate("", xy=(x[-1], y[-1]), xytext=(x[-8], y[-8]), zorder=8,
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.6 * lw, mutation_scale=15 * lw,
                                shrinkA=0, shrinkB=0))
    return x, y


def _label(ax, xy, text, fs=10, leader_to=None):
    ax.text(xy[0], xy[1], text, fontsize=fs, color=INK, ha="center", va="center", zorder=9, linespacing=1.18,
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#B8C2CC", lw=0.6, alpha=0.95))
    if leader_to is not None:
        ax.plot([xy[0], leader_to[0]], [xy[1], leader_to[1]], color="#5A6570", lw=0.7, zorder=6.5)


def corridors_overlay():
    """the ammonia corridors of Supplementary Table 13 on the Fig. 2 geometry
    (a transparent overlay for the last click of the merge slide); every label
    sits in open ocean"""
    _style()
    fig, ax = _map_fig(transparent=True)
    for name, mode, pts, short, at, tr, sav in CORR:
        x, y = _draw_corridor(ax, pts, mode)
        if short:
            lead = (x[len(x) // 2], y[len(y) // 2]) if mode == "land" else None
            _label(ax, at, f"{short}\n+US\\${tr:.1f}, {sav:.0f}% cheaper", leader_to=lead)
    _label(ax, (77, -6), "Oman → Rotterdam\nvia Suez +US\\$1.9, 46% cheaper\nvia the Cape +US\\$2.6, 45% cheaper")
    ax.text(178, -56.5, "Ammonia corridors (Supplementary Table 13): + transport cost per MMBtu; "
            "% cheaper than making it at the destination", fontsize=10.5, color=GREY, ha="right", va="bottom",
            zorder=9)
    fig.savefig(OUT / "jt14_f2_corridors.png", dpi=260, transparent=True)
    plt.close(fig)
    print("  saved jt14_f2_corridors")


ZOOMS = [("China", (72, 136, 17, 55)), ("India", (62, 100, 5, 37)), ("United States", (-126, -66, 22, 52)),
         ("Europe", (-14, 40, 28, 63)), ("Middle East", (30, 66, 10, 40)), ("Africa", (-20, 54, -36, 38))]


def zoom6():
    """six regions of Fig. 2 with the largest flows within countries when fuel
    can move on spare land (Supplementary Note 6, domestic-capped rule, US$1/GJ
    per 1,000 km; the 40% -> 44% case) and the corridors that start or end
    there; the corridor numbers are in each panel's subtitle, off the map"""
    _style()
    SD, df, Uz, Vz, Dz = _kriged()
    rgb = _class_rgb(SD, Uz, Vz, Dz)
    fl = pd.read_csv(OUT / "_flows_domestic-capped.csv")
    fig = plt.figure(figsize=(12.9, 6.3))
    sub = {"China": "Inner Mongolia → Beijing:\n+US\\$2.3/MMBtu, 31% cheaper",
           "India": "build-first across most of the country",
           "United States": "build-first from Texas to the Midwest",
           "Europe": "Iberia → Germany +US\\$3.2, 10% cheaper\nN. Africa → Italy +US\\$4.6, 46% cheaper",
           "Middle East": "Oman → Rotterdam via Suez:\n+US\\$1.9/MMBtu, 46% cheaper",
           "Africa": "Oman → Rotterdam via the Cape:\n+US\\$2.6/MMBtu, 45% cheaper"}
    for k, (name, (x0, x1, y0, y1)) in enumerate(ZOOMS):
        r, c = divmod(k, 3)
        ax = fig.add_axes([c / 3 + 0.006, 0.495 - r * 0.49 + 0.005, 1 / 3 - 0.012, 0.355])
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_edgecolor("#C8CFD8")
        _paint(ax, SD, rgb, lw=2.2)
        m = (fl.dest_lon.between(x0, x1) & fl.dest_lat.between(y0, y1)
             & fl.src_lon.between(x0, x1) & fl.src_lat.between(y0, y1))
        g = fl[m].nlargest(10, "gj")
        if len(g):
            gmax = g.gj.max()
            for _, f in g.iterrows():
                lw = 0.7 + 2.0 * np.sqrt(f.gj / gmax)
                an = ax.annotate("", xy=(f.dest_lon, f.dest_lat), xytext=(f.src_lon, f.src_lat), zorder=7,
                                 arrowprops=dict(arrowstyle="-|>", color="#14304A", lw=lw,
                                                 mutation_scale=7 + 4 * lw, alpha=0.9, shrinkA=1, shrinkB=1,
                                                 path_effects=[pe.withStroke(linewidth=lw + 1.6,
                                                                             foreground="white")]))
                an.set_clip_on(True)
                an.arrow_patch.set_clip_box(ax.bbox)
        for cname, mode, pts, *_rest in CORR:
            use = ((name == "China" and cname.startswith("Inner"))
                   or (name == "Europe" and cname.split(" →")[0] in ("Iberia", "North Africa"))
                   or (name == "Middle East" and "Suez" in cname)
                   or (name == "Africa" and "Cape" in cname))
            if use:
                for art in ax.lines[-0:]:
                    pass
                n0 = len(ax.lines)
                _draw_corridor(ax, pts, mode, lw=1.1)
                for ln in ax.lines[n0:]:
                    ln.set_clip_on(True)
                for ch in ax.texts + ax.patches:
                    ch.set_clip_on(True)
        ax.apply_aspect()
        bb = ax.get_position()
        fig.text(bb.x0 + 0.002, bb.y1 + 0.088, name, fontsize=15.5, color=INK, fontweight="bold", va="bottom")
        fig.text(bb.x0 + 0.002, bb.y1 + 0.008, sub[name], fontsize=12, color=GREY, va="bottom", linespacing=1.12)
    _save(fig, "jt14_zoom6", dpi=240)


def smooth():
    _style()
    SD, df, Uz, Vz, Dz = _kriged()
    lon0, lon1, lat0, lat1 = 60.0, 130.0, 5.0, 55.0
    fig = plt.figure(figsize=(12.9, 5.25))
    panels = [("Computed: 2.5° cells", _cell_rgb(SD, df)),
              ("Displayed in Fig. 2: boundaries smoothed", _class_rgb(SD, Uz, Vz, Dz))]
    for k, (head, rgb) in enumerate(panels):
        ax = fig.add_axes([0.005 + k * 0.505, 0.0, 0.49, 0.89])
        _paint(ax, SD, rgb, lw=2.2)
        ax.set_xlim(lon0, lon1)
        ax.set_ylim(lat0, lat1)
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_edgecolor("#C8CFD8")
        fig.text(0.005 + k * 0.505, 0.955, head, fontsize=18, color=INK, fontweight="bold", va="center")
    _save(fig, "jt14_smooth", dpi=240)


# ====================================================================== logic
LOGIC = [   # 2026-10-06: five links, one per main figure
    (1, "Framework", "What does synthetic fuel cost,\nand how much could it serve?",
     "Hourly LP, 2,740 cells ×\n20 weather years; six\nfuels from hydrogen;\nhard-to-electrify demand",
     "Fig. 1: hydrogen is\n86–89% of fuel cost;\n76.2 billion MMBtu\na year of demand"),
    (2, "Supply–demand\nmismatch", "Where is it cheap, and\nwhere is it needed?",
     "Terciles of local cost\nand local demand;\ntransport between\ncells and corridors",
     "Fig. 2: 335 cells (12%)\nare cheap and\nhigh-demand and hold\n40% of demand"),
    (3, "Risk hedge", "Does domestic fuel hedge\nsupply disruption?",
     "Each economy's own\nprice in normal and\ndisruption months,\n30 economies",
     "Fig. 3: ammonia 1.85×\nthe normal price, yet\nbelow the disruption\nprice in 25 of 30"),
    (4, "Security &\nclimate value", "Is the hedge worth the premium,\nand what does it do for CO2?",
     "Expected fuel lost ×\nvalue of fuel lost, like\nlost load; per tonne\nof CO2",
     "Fig. 4: > US\\$100/t in 15\nof 26 importers; 7\njustified; 0.4 Gt CO2/yr\nnow, ~2 Gt by 2050"),
    (5, "Affordability", "How far can one country\ngo on its own?",
     "1–3% of GDP pays\nthe premium, within\nthe land ceiling",
     "Fig. 5: land or budget\nbinds in 21 of 26\nimporters"),
]


def logic(hi=None):
    _style()
    fig, ax = _canvas()
    _box(ax, 0.1, 5.42, W - 0.2, 0.78,
         "When do the energy-security and climate value of synthetic fuels outweigh their cost premium?",
         INK, fs=19, tag="logic q")
    x0, gap = 1.0, 0.22
    n = len(LOGIC)
    w = (W - x0 - 0.1 - gap * (n - 1)) / n
    for name, y in (("WHY", 4.25), ("METHOD", 3.11), ("RESULT", 1.28)):
        _words(ax, 0.08, y, name, fs=13.5, color=LIGHT, bold=True)
    texts = {"head": [], "why": [], "how": [], "res": []}
    for k, (part, head, why, how, res) in enumerate(LOGIC):
        x = x0 + k * (w + gap)
        col = PART_COL[part]
        a = 1.0 if hi in (None, part) else 0.2
        ax.add_patch(FancyBboxPatch((x, 4.62), w, 0.55, boxstyle="round,pad=0,rounding_size=0.08",
                                    fc=col, ec="none", alpha=a, zorder=2))
        th = _fit_text(ax, x, 4.62, w, 0.55, f"{part}  {head}", 18, "white", tag="logic head")
        th.set_alpha(1.0 if a == 1.0 else 0.9)
        texts["head"].append(th)
        t = _fit_text(ax, x, 3.86, w, 0.72, why, 14.0, INK, bold=False, pad=0.03, tag="logic why")
        t.set_fontsize(14.0 if FITTED[-1][1] >= 14.0 else FITTED[-1][1])
        t.set_alpha(a)
        t.set_fontstyle("italic")
        texts["why"].append(t)
        ax.add_patch(FancyBboxPatch((x, 2.42), w, 1.38, boxstyle="round,pad=0,rounding_size=0.08",
                                    fc=PALE, ec=col, lw=1.6, alpha=a, zorder=2))
        th = _fit_text(ax, x, 2.42, w, 1.38, how, 16, INK, bold=False, pad=0.06, tag="logic how")
        th.set_alpha(a)
        texts["how"].append(th)
        _arrow(ax, (x + w / 2, 2.36), (x + w / 2, 2.0), color=col if a == 1.0 else "#D5DAE0", lw=2.2, ms=16)
        ax.add_patch(FancyBboxPatch((x, 0.62), w, 1.32, boxstyle="round,pad=0,rounding_size=0.08",
                                    fc=col, ec="none", alpha=0.13 if a == 1.0 else 0.04, zorder=2))
        th = _fit_text(ax, x, 0.62, w, 1.32, res, 16, col, pad=0.06, tag="logic res")
        th.set_alpha(a)
        texts["res"].append(th)
        if k < n - 1:
            _arrow(ax, (x + w + 0.02, 3.11), (x + w + gap - 0.02, 3.11), color=LIGHT, lw=2.0, ms=15)
    for group in texts.values():                 # one size per row, the smallest that fits
        z = min(tt.get_fontsize() for tt in group)
        for tt in group:
            tt.set_fontsize(z)
    _words(ax, W / 2, 0.24, "Held at observed values: fossil prices, demand and carbon prices.   "
           "Projected forward: only the cost of the synthetic plant.", fs=15, color=GREY, ha="center")
    _save(fig, "jt14_logic" + (f"_p{hi}" if hi else ""))


# ====================================================================== methods
def m_lp():
    _style()
    fig, ax = _canvas()
    rows = [
        (r"$\min\;J=\sum_k\bigl[\mathrm{CRF}(r_c,n_k)+o_k\bigr]c_kC_k+c_w\,\omega\,\eta_E\sum_t p_t\,\Delta t$",
         "annual cost: capital at the country's\ncost of capital $r_c$, O&M and water"),
        (r"$C_P\,a_{P,t}+C_W\,a_{W,t}+\eta_B\,d_t=p_t+c_t+z_t,\qquad p_t\le C_E$",
         "power balance in every hour"),
        (r"$b_t-b_{t-1}=(\eta_B\,c_t-d_t)\,\Delta t,\quad 0\le c_t,\,d_t\le C_B,\quad 0\le b_t\le C_S$",
         "battery"),
        (r"$h_t-h_{t-1}=(\eta_E\,p_t-F)\,\Delta t,\qquad 0\le h_t\le C_H$",
         "hydrogen store; constant output $F$"),
        (r"$h_0=h_T,\qquad b_0=b_T$", "both stores end the year\nwhere they began"),
        (r"$L_{\mathrm{H_2}}=J^{*}/(8760\,F)$", "levelized cost of hydrogen"),
    ]
    y0, dy = 5.78, 0.86
    for k, (tex, lab) in enumerate(rows):
        y = y0 - k * dy
        _eq(ax, 0.25, y, tex, 22, 8.55)
        _words(ax, 9.05, y, lab, fs=16, color=GREY)
    ax.plot([8.88, 8.88], [y0 + 0.4, y0 - 5 * dy - 0.4], color="#C8CFD8", lw=1.0)
    _rule(ax, 0.86)
    _words(ax, 0.25, 0.43, "Chooses solar, wind, electrolyser, battery and hydrogen-store sizes $C_k$ and the hourly "
           "dispatch.  2,740 cells × 20 weather years\n= 54,800 linear programmes.  Every term is linear in $F$, "
           "so no plant size is assumed.  $\\eta_E$ = 0.65, $\\eta_B$ = 0.95.", fs=15.5, color=INK, lsp=1.35)
    _save(fig, "jt14_m_lp")


def m_demand():
    _style()
    fig, ax = _canvas()
    tex = (r"$D_{i,f}\;=\;\sum_s\;\underbrace{\alpha_s}_{\textrm{share synthetic fuel can serve}}\;"
           r"\underbrace{Q_{i,s}}_{\textrm{fuel use of sector } s \textrm{ in cell } i}\;"
           r"\underbrace{w_{s,f}}_{\textrm{share assigned to fuel } f}$")
    _eq(ax, W / 2, 5.45, tex, 28, 12.2, ha="center")
    rows = [("aviation", "100%", "e-kerosene"),
            ("shipping", "100%", "methanol 70%, ammonia 30%"),
            ("chemical feedstock", "100%", "ammonia 62%, methanol 38%"),
            ("industry, high-temperature heat", "40%", "gas share to e-methane, oil share to e-diesel"),
            ("road transport", "30%", "e-diesel 80%, ethanol 20%"),
            ("buildings, hard-to-retrofit heat", "20%", "gas share to e-methane, oil share to e-diesel"),
            ("power generation", "0%", "not addressed")]
    hy = 4.12
    for x, t, ha in ((0.4, "sector  $s$", "left"), (5.3, r"$\alpha_s$", "center"),
                     (6.45, r"fuel  $f$  ($w_{s,f}$)", "left")):
        _words(ax, x, hy, t, fs=16, color=LIGHT, bold=True, ha=ha)
    _rule(ax, hy - 0.25)
    for j, (a, s, f) in enumerate(rows):
        y = hy - 0.58 - j * 0.45
        _words(ax, 0.4, y, a, fs=17, color=INK)
        _words(ax, 5.3, y, s, fs=17, color=GREEN, bold=True, ha="center")
        _words(ax, 6.45, y, f, fs=17, color=GREY)
    _words(ax, W / 2, 0.3, "Fuel use located with EDGAR CO2 emissions (0.1° grid), anchored to the 2023 UN energy "
           "balances and brought\nforward to 2025: 76.2 billion MMBtu a year in 139 economies; a substitution "
           "scenario, not a forecast.", fs=15, color=INK, ha="center", lsp=1.3)
    _save(fig, "jt14_m_demand")


def m_match():
    _style()
    SD, _ = _sd()
    pal = _pal(SD)
    fig, ax = _canvas()
    _eq(ax, 0.3, 5.72, r"$\bar L_i=\sum_f\frac{D_{i,f}}{\sum_{f'}D_{i,f'}}\,L_{f,i}"
        r"\qquad\qquad D_i=\sum_f D_{i,f}$", 26, 7.6)
    _words(ax, 8.2, 5.72, "cost of the fuels the cell's own\nmarket uses, and its market size", fs=16)
    _eq(ax, 0.3, 4.55, r"$\mathcal{B}=\bigl\{\,i:\;\bar L_i\le\mathcal{Q}_{1/3}(\bar L),\;\;"
        r"D_i\ge\mathcal{Q}_{2/3}(D)\,\bigr\}$", 28, 7.6)
    _words(ax, 8.2, 4.55, "build-first cells: cheapest third\nof cost, highest third of demand", fs=16)
    _rule(ax, 3.82)
    gx, gy, s = 2.6, 0.78, 0.92
    (c1, c2), (d1, d2) = _cuts()
    for r in range(3):
        for c in range(3):
            ax.add_patch(Rectangle((gx + c * s, gy + r * s), s, s, fc=pal[r][c], ec="white", lw=1.5, zorder=2))
        _words(ax, gx - 0.12, gy + r * s + s / 2, [f"> {c2}", f"{c1}–{c2}", f"< {c1}"][r], fs=15, color=INK,
               ha="right")
    for c in range(3):
        _words(ax, gx + c * s + s / 2, gy - 0.22, [f"< {d1}", f"{d1}–{d2}", f"> {d2}"][c], fs=15, color=INK, ha="center")
    _words(ax, gx - 1.75, gy + 1.5 * s, "cost\nUS\\$/MMBtu", fs=14.5, color=GREY, ha="center", lsp=1.15)
    _words(ax, gx + 1.5 * s, gy - 0.5, "demand, million MMBtu/yr", fs=14.5, color=GREY, ha="center")
    roles = [(pal[2][2], "Build-first", "low cost, high demand: priority for early domestic deployment"),
             (pal[2][0], "Export-oriented", "low cost, low demand: potential export supply"),
             (pal[0][2], "Supply-strained", "high cost, high demand: needs imports or transport"),
             (pal[0][0], "Limited potential", "high cost, low demand: little near-term role")]
    for k, (col, name, txt) in enumerate(roles):
        y = 3.28 - k * 0.78
        ax.add_patch(Rectangle((5.55, y - 0.2), 0.4, 0.4, fc=col, ec="#8C96A3", lw=0.6, zorder=2))
        _words(ax, 6.15, y + 0.13, name, fs=17, color=INK, bold=True)
        _words(ax, 6.15, y - 0.2, txt, fs=15, color=GREY)
    _save(fig, "jt14_m_match")


def m_prices():
    _style()
    fig, ax = _canvas()
    _eq(ax, 0.3, 5.75, r"$\kappa_c=\dfrac{\mathrm{median}_y\,L_{f,i^*_c,y}+\delta}{p^{\mathcal{N}}_c}$", 26, 5.0)
    _words(ax, 5.25, 5.75, "cost ratio: fuel from the economy's cheapest cell (median of\n20 weather years, "
           "plus δ = US\\$1/GJ delivery) over the median\nnormal import price", fs=15.5)
    _eq(ax, 0.3, 4.42, r"$\mathrm{median}_y\,L_{f,i^*_c,y}+\delta\;\le\;P_{98}\bigl(p^{*}_{c,m,r}\bigr)$", 26, 5.0)
    _words(ax, 5.25, 4.42, "within the disruption range: below the 98th percentile\nof the economy's prices "
           "in disruption months", fs=15.5)
    _eq(ax, 0.3, 3.38, r"$R_c=\sqrt{E_c\,H_c}$", 26, 5.0)
    _words(ax, 5.25, 3.38, "import-risk index: imported share of the supply chain ×\nsupplier concentration "
           "(Herfindahl index of 2023 imports)", fs=15.5)
    _rule(ax, 2.72)
    steps = [("10 dated supply events,\n2011–2026: 7 oil,\n6 gas, 3 both", RED),
             ("event months, the 6\nmonths after and COVID\nleave the normal months", RED),
             ("NORMAL: 12 clean months\nbefore each regime\nDISRUPTION: regime months", INK),
             ("each economy's own\nprice series: customs\nwhere reported", BLUE)]
    n, gap, x0 = len(steps), 0.36, 0.1
    w = (W - 0.2 - gap * (n - 1)) / n
    for k, (txt, col) in enumerate(steps):
        x = x0 + k * (w + gap)
        _box(ax, x, 0.62, w, 1.82, txt, col, fs=16.5, tag="prices box")
        if k < n - 1:
            _arrow(ax, (x + w + 0.03, 1.53), (x + w + gap - 0.03, 1.53))
    _words(ax, W / 2, 0.24, "Ammonia: own customs prices in 14 economies, urea-implied in 11, administered gas cost "
           "in 5.   Diesel and jet fuel: customs prices.", fs=14.5, color=INK, ha="center")
    _save(fig, "jt14_m_prices")


def m_security():
    """security parity (main text eq. 1) and the expected fuel lost (Methods eq. 4)"""
    _style()
    fig, ax = _canvas()
    ax.add_patch(FancyBboxPatch((0.15, 4.72), W - 0.3, 1.45, boxstyle="round,pad=0,rounding_size=0.1",
                                fc="#F6E3DB", ec="none", zorder=1))
    tex2 = (r"$\underbrace{L_{c,f}-p_{c,f}}_{\textrm{extra cost}}\;\le\;"
            r"\underbrace{v_c\,m_f\,q_{c,f}}_{\textrm{security margin}}$")
    _eq(ax, 3.6, 5.5, tex2, 30, 6.4, ha="center")
    _words(ax, 7.3, 5.45, "security parity: build at home once the\nextra cost over the normal import price is\n"
           "no larger than the disruption loss it avoids", fs=15.5, color=INK)
    tex = (r"$q_{c,f}\;=\;\sum_{\ell}\;\underbrace{\rho_\ell}_{\substack{\textrm{events a year}\\"
           r"\textrm{cut-offs 0.26}\\\textrm{closures 0.15}}}\;"
           r"\underbrace{\frac{T_\ell}{12}}_{\substack{\textrm{duration, years}\\\textrm{8 and 3.5 months}}}\;"
           r"\underbrace{\varphi_{c,f,\ell}}_{\substack{\textrm{share of imports stranded}\\"
           r"\textrm{cut-off: largest supplier}\\\textrm{closure: all imports}}}\;"
           r"\underbrace{\bigl(1-M_{c,f,\ell}\bigr)}_{\substack{\textrm{not covered by oil stocks}\\"
           r"\textrm{IEA oil: half a cut-off,}\\\textrm{all of a closure}}}$")
    _eq(ax, 0.25, 2.75, tex, 30, 12.3)
    _words(ax, 0.25, 0.42, "q: the expected share of a marginal imported gigajoule lost each year.\n"
           "Rates and durations from the 2000–2026 part of a catalogue of 20 disruptions since 1956.",
           fs=15.5, color=INK, lsp=1.35)
    _save(fig, "jt14_m_security")


def _core_order():
    """Table 1's order: net importers by net cost per tonne, then the net exporters"""
    f = pd.read_csv(inputs.MAPS / "fig5a_chain.csv", index_col=0)
    sb = pd.read_csv(inputs.MAPS / "security_budget.csv", index_col=0)
    imp = [c for c in f.sort_values("net_usd_t").index if sb.import_pct.get(c, 0) > 0]
    exp = [c for c in f.sort_values("net_usd_t").index if sb.import_pct.get(c, 0) <= 0]
    return imp, exp, f


def m_voll():
    """the value of lost fuel (SI eqs S35-S36) and the security margin per
    unit of domestic fuel for the 30 economies (SI Table tab:chainq)"""
    _style()
    si = pd.read_csv(inputs.MAPS / "security_index.csv", index_col=0)
    q = pd.read_csv(inputs.MAPS / "chain_q.csv").set_index(["country", "fuel"]).q
    imp, exp, f = _core_order()
    order = imp + exp
    JUST = set(f.index[f.net_usd_t <= f.p_co2_usd_t])
    assert len(JUST) == 7 and "Germany" in JUST and "Israel" not in JUST, sorted(JUST)
    assert round(f.gross_usd_t["Germany"] - f.net_usd_t["Germany"]) == 382
    v = si.codf_hi_usd_gj.reindex(order) * UMM
    chains = [("Ammonia", "ammonia", 1.0), ("Gas", "e-methane", 1.0), ("Oil", "e-diesel", 1.3)]
    wv = pd.DataFrame({k: [v[c] * m * q.get((c, fu), 0.0) for c in order] for k, fu, m in chains}, index=order)
    assert round(v["Ireland"]) == 570 and round(v["Germany"]) == 261 and round(v["Chile"]) == 118
    assert round(q[("Germany", "ammonia")], 3) == 0.199 and round(q[("Ireland", "e-diesel")], 3) == 0.034
    ger = float(v["Germany"] * q[("Germany", "ammonia")])
    assert round(ger / UMM / 0.129) == 382, ger
    fig, ax = _canvas()
    # ---- left: the calculation
    _words(ax, 0.2, 5.98, "Power systems:  expected energy not served × value of lost load", fs=15.5, color=GREY)
    _words(ax, 0.2, 5.6, "Fuel:  expected fuel lost × value of fuel lost", fs=15.5, color=INK, bold=True)
    _eq(ax, 0.2, 4.85, r"$v_c=\lambda\,\dfrac{\mathrm{GDP}_c}{U_c}$", 26, 2.6)
    _words(ax, 2.95, 4.85, "value of a unit of fuel lost: GDP per unit\nof national fuel use; λ sets the European\n"
           "median to US\\$22/GJ (central) or US\\$175/GJ\n(EUR600/MWh, ENTSOG: the reference)", fs=13.5, lsp=1.2)
    _eq(ax, 0.2, 3.62, r"$w_{c,f}=v_c\,m_f\,q_{c,f}$", 26, 2.6)
    _words(ax, 2.95, 3.62, "security margin of a domestic unit of fuel,\nwhile its chain still imports; "
           "m = 1.0 gas\nfamily, 1.3 oil products", fs=13.5, lsp=1.2)
    _eq(ax, 0.2, 2.62, r"$\dfrac{\sum_f w_{c,f}\,r_{c,f}}{\Gamma_c}$", 24, 2.2)
    _words(ax, 2.95, 2.62, "per tonne of CO2 displaced: the arrows of\nFig. 4a", fs=13.5, lsp=1.2)
    ax.add_patch(FancyBboxPatch((0.15, 0.08), 6.1, 1.95, boxstyle="round,pad=0,rounding_size=0.08",
                                fc="#F6E3DB", ec="none", zorder=1))
    _words(ax, 0.3, 1.78, "Worked example: Germany, ammonia chain", fs=14.5, color=INK, bold=True)
    _words(ax, 0.3, 1.0, "q = 0.262 × 8/12 × 0.89 + 0.150 × 3.5/12 × 1 = 0.155 + 0.044 = 0.199\n"
           f"w = 261 × 1.0 × 0.199 = US\\${ger:.0f} per MMBtu of domestic ammonia\n"
           "÷ 0.136 t CO2 per MMBtu → US\\$382/t (Fig. 4a)", fs=13.5, color=INK, lsp=1.35)
    # ---- right: heat map of w
    x0, y0, cwid, rh = 8.92, 0.12, 0.99, 0.178
    cols = ["v", "Ammonia", "Gas", "Oil"]
    cmap = mpl.colormaps["Reds"]
    vmap = mpl.colormaps["Blues"]
    n = len(order)
    top = y0 + n * rh
    for j, cname in enumerate(cols):
        _words(ax, x0 + (j - 0.35) * cwid + cwid / 2 if j == 0 else x0 + (j - 0.35) * cwid + cwid / 2,
               top + 0.13, cname, fs=12.5, color=INK, bold=True, ha="center")
    _words(ax, x0 + 1.95 * cwid, top + 0.42, "w = v·m·q, US\\$ per MMBtu", fs=12.5, color=INK, ha="center")
    _words(ax, x0 - 0.35 * cwid + cwid / 2, top + 0.42, "US\\$/MMBtu", fs=11, color=GREY, ha="center")
    for i, c in enumerate(order):
        y = top - (i + 1) * rh
        just = c in JUST
        _words(ax, x0 - 0.42, y + rh / 2, {"United States of America": "United States",
               "Dominican Republic": "Dominican Rep."}.get(c, c), fs=10.5, color=INK, bold=just, ha="right")
        # v column
        xv = x0 - 0.35 * cwid
        ax.add_patch(Rectangle((xv, y), cwid * 0.95, rh * 0.94, fc=vmap(0.15 + 0.7 * min(v[c] / 600, 1)),
                               ec="none", zorder=2))
        _words(ax, xv + cwid * 0.475, y + rh / 2, f"{v[c]:.0f}", fs=10, color="white" if v[c] > 300 else INK,
               ha="center")
        for j, (k, _, _) in enumerate(chains, start=1):
            val = wv.at[c, k]
            xx = x0 + (j - 0.35) * cwid
            ax.add_patch(Rectangle((xx, y), cwid * 0.95, rh * 0.94, fc=cmap(min(val / 90, 1) * 0.9) if val > 0
                                   else "#F4F5F7", ec="none", zorder=2))
            _words(ax, xx + cwid * 0.475, y + rh / 2, f"{val:.0f}" if val >= 0.5 else "0", fs=10,
                   color="white" if val > 45 else INK, ha="center")
        if c == "Germany":
            ax.add_patch(Rectangle((x0 + 0.65 * cwid, y), cwid * 0.95, rh * 0.94, fill=False, ec=INK, lw=2.0,
                                   zorder=4))
    ysep = top - len(imp) * rh
    ax.plot([x0 - 2.0, x0 + 3.6 * cwid], [ysep, ysep], color=GREYC, lw=0.9, ls=(0, (4, 2)))
    _save(fig, "jt14_m_voll")
    print("    w ($/MMBtu) top:", wv.max(axis=1).sort_values(ascending=False).head(6).round(0).to_dict())


def m_tipping():
    _style()
    fig, ax = _canvas()
    tex = (r"$\underbrace{\frac{S_c}{\Gamma_c}}_{\textrm{extra cost}}\;-\;"
           r"\underbrace{\frac{\sum_f w_{c,f}\,r_{c,f}}{\Gamma_c}}_{\textrm{security margin}}\;\le\;"
           r"\underbrace{\tau_c}_{\textrm{carbon incentive}}$")
    _eq(ax, 0.3, 5.3, tex, 30, 7.2)
    _words(ax, 7.9, 5.4, "$S_c$: support, up to 1% of GDP, spent on\nthe lowest-premium fuels first\n"
           "$r_{c,f}$: imports of chain $f$ replaced\n$\\Gamma_c$: credited CO2 = displaced fuel × its\n"
           "emission factor\n$\\tau_c$: carbon price or tax in force, 2025", fs=15, color=GREY, lsp=1.3)
    _rule(ax, 3.55)

    def X(v):
        return 3.0 + (v + 600) / 1500 * 8.6
    y = 2.25
    ax.add_patch(Rectangle((X(-600), y - 0.55), X(0) - X(-600), 1.1, fc=SHADE, ec="none", zorder=0))
    ax.plot([X(0), X(0)], [y - 0.55, y + 0.55], color="#9AA3AC", lw=1.0, zorder=1)
    f5 = pd.read_csv(inputs.MAPS / "fig5a_chain.csv", index_col=0).loc["Germany"]
    g, n_, tau = round(f5.gross_usd_t), round(f5.net_usd_t), round(f5.p_co2_usd_t)
    assert (g, n_, tau) == (353, -29, 80), (g, n_, tau)
    ax.annotate("", xy=(X(n_) + 0.12, y), xytext=(X(g) - 0.16, y), zorder=2,
                arrowprops=dict(arrowstyle="-|>", color=GREYC, lw=2.0, mutation_scale=22))
    ax.plot([X(g)], [y], "o", ms=17, mfc="white", mec=INKC, mew=2.0, zorder=4)
    ax.plot([X(n_)], [y], "o", ms=13, color=INKC, zorder=4)
    ax.plot([X(tau), X(tau)], [y - 0.38, y + 0.38], color=MAG, lw=3.0, zorder=3)
    for vv in (-600, -300, 0, 300, 600, 900):
        ax.plot([X(vv), X(vv)], [y - 0.62, y - 0.7], color=INK, lw=1.0)
        _words(ax, X(vv), y - 0.9, f"{vv:,}".replace("-", "−"), fs=14, color=INK, ha="center")
    _words(ax, X(150), y - 1.28, "US\\$ per tonne of CO2  (Germany, Fig. 4a)", fs=14.5, color=GREY, ha="center")
    _words(ax, 0.25, y + 0.9, "How to read Fig. 4a", fs=16, color=INK, bold=True)
    _words(ax, X(g) + 0.2, y, f"extra cost {g}", fs=15, color=INKC, ha="left", va="center")
    _words(ax, X(tau) + 0.15, y - 0.14, f"security margin {g - n_}", fs=15, color=GREYC, ha="left",
           va="top")
    _words(ax, X(n_) - 0.2, y, f"net cost −{-n_}", fs=15, color=INKC, ha="right", va="center")
    _words(ax, X(tau), y + 0.48, f"carbon price {tau}", fs=14, color=MAG, ha="center", va="bottom")
    _words(ax, 0.25, y - 0.1, "justified where the\nfilled circle lies left\nof its magenta tick", fs=15,
           color=INK, lsp=1.25)
    _save(fig, "jt14_m_tipping")


def m_trajectory():
    _style()
    fig, ax = _canvas()
    tex = (r"$\mathrm{CO_2}(t)=\sum_{c,f}\epsilon_f\Big(\underbrace{I_{c,f}\,"
           r"\mathbf{1}\big[t^{\mathrm{sec}}_{c,f}\le t\big]}_{\textrm{net imports: from security parity}}"
           r"+\underbrace{\big(D_{c,f}-I_{c,f}\big)\,\mathbf{1}\big[t^{\mathrm{cost}}_{c,f}"
           r"\le t\big]}_{\textrm{other demand: from cost parity}}\Big)$")
    _eq(ax, W / 2, 5.25, tex, 28, 12.3, ha="center")
    lines = [("$t^{\\mathrm{sec}}_{c,f}$", "first build year with  extra cost ≤ security margin  (security parity)"),
             ("$t^{\\mathrm{cost}}_{c,f}$", "first build year with  synthetic cost ≤ normal fossil price  (cost parity)"),
             ("costs", "fall along the moderate technology pathway: median hydrogen −24% by 2030, −55% by 2050"),
             ("held", "demand, valuation, import exposure, fossil and carbon prices at their 2025 levels"),
             ("bound", "no land, budget or build-rate limit: an upper bound;  $I_{c,f}=0$ gives the "
                       "cost-parity line")]
    for k, (a, b) in enumerate(lines):
        y = 3.55 - k * 0.66
        _words(ax, 1.55, y, a, fs=17, color=GREEN, bold=True, ha="right")
        _words(ax, 1.85, y, b, fs=16.5, color=GREY)
    _save(fig, "jt14_m_trajectory")


def m_budget():
    _style()
    fig, ax = _canvas()
    tex = (r"$\sum_{i,f}\;\underbrace{\pi_{i,f}}_{\textrm{premium over the normal price}}\;"
           r"\underbrace{x_{i,f}}_{\textrm{domestic output}}\;\le\;"
           r"\underbrace{b\,\mathrm{GDP}_c}_{b\,=\,1,\,2,\,3\%}$")
    _eq(ax, W / 2, 5.35, tex, 30, 11.5, ha="center")
    boxes = [("ORDER\n\nlowest premium\nfirst, in Fig. 4a\nand Fig. 5", PURPLE),
             ("LAND\n\n5% of eligible land,\nat most 2% of\nnational territory,\non own national land", PURPLE),
             ("POTENTIAL\n\neach cell's hydrogen\nfrom its own\nsolar and wind", PURPLE),
             ("IMPORTS\n\na domestic GJ\nreplaces imports\nonly in its own\nfamily: gas or oil", PURPLE)]
    n, gap, x0 = len(boxes), 0.36, 0.1
    w = (W - 0.2 - gap * (n - 1)) / n
    for k, (txt, col) in enumerate(boxes):
        _box(ax, x0 + k * (w + gap), 0.75, w, 2.95, txt, col, fs=17.5, tag="budget box")
    _words(ax, W / 2, 0.3, "The budget covers only the premium; fuel buyers still pay the normal price.",
           fs=16, color=INK, ha="center")
    _save(fig, "jt14_m_budget")


# ====================================================================== Table 1
def table1():
    import tempfile
    from pathlib import Path
    src = Path(r"C:/Users/ALW/Desktop/synfuel_V1.4/main_V1.4.tex").read_text(encoding="utf-8")
    i = src.index("\\label{tab:summary}")
    j = src.index("\\begin{tabular}", i)
    k = src.index("\\end{tabular}", j) + len("\\end{tabular}")
    tab = src[j:k]
    tab = (tab.replace("Fig.~\\ref{fig:cities}", "Fig. 3").replace("Fig.~\\ref{fig:co2}a", "Fig. 4a")
           .replace("Fig.~\\ref{fig:budget}", "Fig. 5"))
    tab = re.sub(r"\\textcolor\{red\}\{(.*?)\}", r"\1", tab)
    doc = ("\\documentclass[border=4pt]{standalone}\n\\usepackage{booktabs}\\usepackage{helvet}"
           "\\renewcommand{\\familydefault}{\\sfdefault}\\usepackage[T1]{fontenc}\n"
           "\\begin{document}\\footnotesize\\setlength{\\tabcolsep}{4pt}\n" + tab + "\n\\end{document}\n")
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "t.tex").write_text(doc, encoding="utf-8")
        subprocess.run(["pdflatex", "-interaction=nonstopmode", "t.tex"], cwd=d, capture_output=True, check=True)
        subprocess.run(["pdftoppm", "-r", "500", "-png", "-singlefile", "t.pdf", "t"], cwd=d, check=True)
        shutil.copy2(d / "t.png", OUT / "jt14_table1.png")
    print("  saved jt14_table1")


def main():
    import sys
    jobs = sys.argv[1:] or ["title", "logic", "methods", "fig2", "zoom", "smooth", "table"]
    if "title" in jobs:
        title_bg()
    if "logic" in jobs:
        logic()
        for p in range(1, 6):
            logic(hi=p)
    if "methods" in jobs:
        m_lp(); m_demand(); m_match(); m_prices(); m_security(); m_voll(); m_tipping(); m_trajectory()
        m_budget()
    if "fig2" in jobs:
        fig2_layers()
    if "zoom" in jobs:
        zoom6()
    if "smooth" in jobs:
        smooth()
    if "table" in jobs:
        table1()
    if FITTED:
        small = [(t, f) for t, f in FITTED if f < 14.5]
        print(f"  fitted {len(FITTED)} labels; smallest {min(f for _, f in FITTED):.1f} pt"
              + (f"; below 14.5 pt: {small}" if small else ""))


if __name__ == "__main__":
    main()
