"""
fig_main_framework.py — MAIN-TEXT Figure 1, version 5: ONE clean layer.

A single horizontal value chain: wind + solar -> electrolysis (with the
water-splitting reaction) -> hydrogen store -> five synthesis routes
(each with its governing reaction, coloured by fuel) -> the industries
they serve. The security contrast is a single element: a crisis-prone
import route arriving at the same industries from the right, and one
thin verdict strip underneath. No sub-panels, no data thumbnails.

From scripts/:  conda run -n synfuel python -u -m lcof.fig_main_framework
Output: cf_global_final/figures/pptx/fig_main_framework.(pdf|png)
"""
from __future__ import annotations

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import (FancyBboxPatch, FancyArrowPatch, Polygon,
                                Circle, Rectangle)
from matplotlib.path import Path

mpl.use("Agg")

from .fig_main_cost import MM, NAT_RC
from .fig_pptx_pairs import OUT

mpl.rcParams.update(NAT_RC)

DARK = "#14304A"
BLUE, ORANGE, RED, GREEN, PURPLE, SKY = ("#0072B2", "#E69F00", "#D55E00",
                                         "#009E73", "#CC79A7", "#56B4E9")
GREY = "#6A7683"
INK = "#3A4550"
FS = 7.4                        # 2026-10-08: Nature 5-7 pt at print size (figure is drawn 188 mm, set at 180 mm)


# The axes is drawn at 1 data unit = 1 mm, so a width in points is
# PT * width in data units.
PT = 25.4 / 72.0
# How far the VISIBLE tip of a "-|>" head falls short of its end point:
# matplotlib pulls the head's tip vertex back by lw / (2 sin t), t = the
# head's half-angle, so that a MITRED outline would end on the point, but
# FancyArrowPatch strokes with ROUND joins, which reach only lw / 2 past
# the vertex. In mm per point of line width:
_TIP_SHORT = (0.5 / (0.2 / np.hypot(0.4, 0.2)) - 0.5) * PT
TOUCH = 0.1          # mm a tip runs into the outline it arrives at


def _rim(edge, lw, side):
    """The outer face of an outline whose path runs at `edge` (data mm)
    and is stroked `lw` points wide; side = +1 for the face toward +x/+y,
    -1 for the face toward -x/-y."""
    return edge + side * lw * PT / 2.0


def _arrow(ax, *pts, color=GREY, lw=1.4, ms=10, zorder=4):
    """An arrow through pts (data mm) with its head on the last point.

    Drawn as ONE path, so an elbow is a round join with no seam, and
    with no shrink at either end: the tail starts exactly where it is
    put (on a line's centre, or on a box's outline) and the visible tip
    lands exactly on the last point (_TIP_SHORT is added back)."""
    v = np.asarray(pts, dtype=float)
    d = v[-1] - v[-2]
    v[-1] = v[-1] + d / np.hypot(*d) * _TIP_SHORT * lw
    ax.add_patch(FancyArrowPatch(path=Path(v), arrowstyle="-|>", lw=lw,
                                 color=color, mutation_scale=ms,
                                 zorder=zorder))


def _box(ax, x, y, w, h, color, title, sub=None, fc="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.45,rounding_size=1.0",
                                fc=fc, ec=color, lw=1.2, zorder=3))
    ax.text(x + w / 2, y + h / 2 + (2.1 if sub else 0), title,
            ha="center", va="center", fontsize=FS, color=color,
            fontweight="bold", zorder=5)
    if sub:
        ax.text(x + w / 2, y + h / 2 - 2.5, sub, ha="center",
                va="center", fontsize=FS - 1, color=INK, zorder=5)


def _turbine(ax, x, y, s=1.0, color=BLUE):
    ax.plot([x, x], [y, y + 8 * s], color=color, lw=1.4,
            solid_capstyle="round")
    for ang in (90, 210, 330):
        a = np.deg2rad(ang)
        ax.plot([x, x + 3.8 * s * np.cos(a)],
                [y + 8 * s, y + 8 * s + 3.8 * s * np.sin(a)],
                color=color, lw=1.4, solid_capstyle="round")
    ax.add_patch(Circle((x, y + 8 * s), 0.55 * s, fc="white", ec=color,
                        lw=1.0, zorder=5))


def _pv(ax, x, y, color=ORANGE):
    ax.add_patch(Polygon([(x, y), (x + 8, y), (x + 10, y + 4.4),
                          (x + 2, y + 4.4)], closed=True, fc=color,
                         ec="white", lw=0.7, alpha=0.9))
    ax.plot([x + 1.5, x + 9.2], [y + 2.2, y + 2.2], color="white",
            lw=0.7)
    for f in (0.35, 0.68):
        ax.plot([x + 8 * f + 1.0, x + 8 * f + 1.6],
                [y + 0.3, y + 4.1], color="white", lw=0.7)


def _tank(ax, x, y, w=9.5, h=10.5, color=BLUE):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.4,rounding_size=2.4",
                                fc="white", ec=color, lw=1.3, zorder=3))
    ax.text(x + w / 2, y + h / 2 + 1.7, "H$_2$", ha="center",
            va="center", fontsize=FS + 1, color=color,
            fontweight="bold", zorder=5)
    ax.text(x + w / 2, y + h / 2 - 2.3, "store", ha="center",
            va="center", fontsize=FS - 1, color=INK, zorder=5)


def _tanker(ax, x, y, color=RED):
    ax.add_patch(Polygon([(x, y + 2.4), (x + 16, y + 2.4),
                          (x + 14.2, y), (x + 1.8, y)], closed=True,
                         fc=color, ec="none", alpha=0.9))
    ax.add_patch(Rectangle((x + 10.6, y + 2.4), 3.4, 2.6, fc=color,
                           ec="none", alpha=0.75))
    for wx in np.linspace(x - 1, x + 17, 8):
        ax.plot([wx, wx + 1.7], [y - 1.0, y - 1.0], color=SKY, lw=0.8,
                alpha=0.8)


def _battery(ax, x, y, w=7.0, h=3.8, color=GREEN):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.25,rounding_size=0.7",
                                fc="white", ec=color, lw=1.2, zorder=3))
    ax.add_patch(Rectangle((x + w + 0.45, y + h * 0.28), 0.9, h * 0.44,
                           fc=color, ec="none", zorder=3))
    for i in range(3):
        ax.add_patch(Rectangle((x + 0.7 + i * 2.0, y + 0.7), 1.4,
                               h - 1.4, fc=color, ec="none", alpha=0.85,
                               zorder=4))


def _elz(ax, x, y, w=12.0, h=9.0, color=BLUE):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.35,rounding_size=1.0",
                                fc="#F7FAFD", ec=color, lw=1.2, zorder=3))
    ax.plot([x + 1.2, x + w - 1.2], [y + h - 2.6, y + h - 2.6],
            color=SKY, lw=0.9, zorder=4)
    for px, col in ((x + w * 0.38, color), (x + w * 0.62, ORANGE)):
        ax.plot([px, px], [y + 1.3, y + h - 2.2], color=col, lw=2.4,
                solid_capstyle="round", zorder=4)
    for bx, by in ((x + w * 0.30, y + h - 1.9),
                   (x + w * 0.46, y + h - 1.3),
                   (x + w * 0.58, y + h - 1.9),
                   (x + w * 0.72, y + h - 1.2)):
        ax.add_patch(Circle((bx, by), 0.35, fc="white", ec=color,
                            lw=0.7, zorder=5))


def _vessel(ax, x, y, w=10.0, h=6.4, color=BLUE):
    for lx in (x + 1.8, x + w - 2.9):
        ax.add_patch(Rectangle((lx, y - 1.4), 1.1, 1.6, fc="#9DBAD6",
                               ec="none", zorder=2))
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.3,rounding_size=3.0",
                                fc="white", ec=color, lw=1.3, zorder=3))
    ax.text(x + w / 2, y + h / 2, "H$_2$", ha="center", va="center",
            fontsize=FS + 1, color=color, fontweight="bold", zorder=5)


def _bolt(ax, x, y, s=1.0, color=ORANGE, halo="white"):
    """a small lightning flash: the mark of a link that can fail."""
    pts = [(0.00, 1.00), (-0.55, 0.05), (-0.10, 0.05), (-0.30, -1.00),
           (0.55, 0.10), (0.10, 0.10), (0.36, 1.00)]
    poly = [(x + px * 1.5 * s, y + py * 2.6 * s) for px, py in pts]
    ax.add_patch(Polygon(poly, closed=True, fc=halo, ec=halo, lw=2.4,
                         joinstyle="round", zorder=6))
    ax.add_patch(Polygon(poly, closed=True, fc=color, ec="white",
                         lw=0.5, zorder=7))


def _refinery(ax, x, y, s=1.0, color=RED):
    """distillation columns + stack: the refining link of the chain."""
    for dx, h in ((0.0, 7.0), (3.0, 5.2), (5.8, 6.2)):
        ax.add_patch(Rectangle((x + dx * s, y), 2.0 * s, h * s,
                               fc="white", ec=color, lw=1.0, zorder=5))
    ax.add_patch(Polygon([(x + 8.6 * s, y), (x + 10.4 * s, y),
                          (x + 9.9 * s, y + 8.4 * s),
                          (x + 9.1 * s, y + 8.4 * s)], closed=True,
                         fc="white", ec=color, lw=1.0, zorder=5))
    ax.plot([x - 0.4 * s, x + 11.0 * s], [y, y], color=color, lw=1.1,
            zorder=5)


def _industry(ax, x, y, w, h, kind, color, label, dots=()):
    """a demand box: neutral border, icon on a soft badge, and small
    coloured dots repeating the fuels that serve this sector."""
    FILL = "#DCE4EB"
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.45,rounding_size=1.0",
                                fc="white", ec=color, lw=1.1,
                                zorder=3))
    cx = x + 6.6
    cy = y + h / 2
    ax.add_patch(Circle((cx, cy), 3.7, fc="#EFF3F7", ec="none",
                        zorder=4))
    if kind == "farm":                       # a wheat stalk
        ax.plot([cx, cx], [cy - 2.6, cy + 2.2], color=color, lw=1.2,
                solid_capstyle="round", zorder=6)
        for k in range(3):
            yy = cy - 0.9 + k * 1.1
            for sgn in (-1, 1):
                ax.plot([cx, cx + sgn * 1.5], [yy, yy + 1.2],
                        color=color, lw=1.1, solid_capstyle="round",
                        zorder=6)
        ax.add_patch(Circle((cx, cy + 2.5), 0.45, fc=color, ec="none",
                            zorder=6))
    elif kind == "house":
        ax.add_patch(Polygon([(cx - 2.4, cy - 2.3), (cx + 2.4, cy - 2.3),
                              (cx + 2.4, cy + 0.5), (cx, cy + 2.6),
                              (cx - 2.4, cy + 0.5)], closed=True,
                             fc="white", ec=color, lw=1.1, zorder=5))
        ax.add_patch(Polygon([(cx - 2.7, cy + 0.4), (cx, cy + 2.75),
                              (cx + 2.7, cy + 0.4), (cx + 2.4, cy + 0.5),
                              (cx, cy + 2.6), (cx - 2.4, cy + 0.5)],
                             closed=True, fc=FILL, ec=color, lw=0.9,
                             zorder=6))
        ax.plot([cx + 0.8, cx - 0.35, cx + 0.35, cx - 0.8],
                [cy + 0.8, cy - 0.05, cy - 0.25, cy - 1.6], color=color,
                lw=1.1, solid_capstyle="round", zorder=6)
    elif kind == "ship":                     # container ship
        ax.add_patch(Polygon([(cx - 3.3, cy + 0.3), (cx + 3.3, cy + 0.3),
                              (cx + 2.2, cy - 1.5), (cx - 2.4, cy - 1.5)],
                             closed=True, fc=FILL, ec=color, lw=1.1,
                             zorder=5))
        for k, bx in enumerate((cx - 2.1, cx - 0.5, cx + 1.1)):
            ax.add_patch(Rectangle((bx, cy + 0.5), 1.35, 1.05,
                                   fc="white", ec=color, lw=0.8,
                                   zorder=6))
        ax.plot([cx - 3.0, cx + 3.0], [cy - 2.2, cy - 2.2], color=color,
                lw=0.8, alpha=0.55, zorder=5)
    elif kind == "plane":
        ax.plot([cx - 3.0, cx + 3.1], [cy - 0.3, cy + 0.4], color=color,
                lw=2.0, solid_capstyle="round", zorder=6)
        ax.add_patch(Polygon([(cx - 0.4, cy), (cx - 2.4, cy + 2.2),
                              (cx - 1.1, cy + 0.15)], closed=True,
                             fc=FILL, ec=color, lw=0.9, zorder=6))
        ax.add_patch(Polygon([(cx - 0.2, cy - 0.1), (cx - 2.0, cy - 1.9),
                              (cx - 0.85, cy - 0.25)], closed=True,
                             fc=FILL, ec=color, lw=0.9, zorder=6))
        ax.plot([cx + 2.2, cx + 1.5], [cy + 1.3, cy + 0.25],
                color=color, lw=1.1, solid_capstyle="round", zorder=6)
    elif kind == "truck":
        ax.add_patch(FancyBboxPatch((cx - 3.2, cy - 0.9), 4.0, 2.6,
                                    boxstyle="round,pad=0.05,"
                                    "rounding_size=0.3", fc=FILL,
                                    ec=color, lw=1.0, zorder=5))
        ax.add_patch(FancyBboxPatch((cx + 1.1, cy - 0.9), 1.9, 1.8,
                                    boxstyle="round,pad=0.05,"
                                    "rounding_size=0.35", fc="white",
                                    ec=color, lw=1.0, zorder=5))
        ax.add_patch(Rectangle((cx + 1.5, cy - 0.15), 1.0, 0.75,
                               fc=FILL, ec=color, lw=0.6, zorder=6))
        for wx in (cx - 2.1, cx + 0.2, cx + 2.1):
            ax.add_patch(Circle((wx, cy - 1.35), 0.55, fc=color,
                                ec="white", lw=0.5, zorder=6))
    ax.text(x + 13.0, y + h / 2, label, ha="left", va="center",
            fontsize=FS, color=INK, zorder=5)
    for i, cd in enumerate(dots):            # the fuels that serve it
        ax.add_patch(Circle((x + w - 3.2 - 2.6 * i, y + 2.2), 0.85,
                            fc=cd, ec="white", lw=0.5, zorder=6))


def _chip(ax, x, y, txt, fc, ec, tc, fs=8):
    ax.add_patch(FancyBboxPatch((x, y), 1.9 * len(txt) + 2.4, 4.6,
                                boxstyle="round,pad=0.4,rounding_size=1.2",
                                fc=fc, ec=ec, lw=0.9, zorder=6))
    ax.text(x + (1.9 * len(txt) + 2.4) / 2, y + 2.3,
            txt.replace("$", "\\$"), ha="center",
            va="center", fontsize=fs, color=tc, fontweight="bold",
            zorder=7)


def _cost_ranges():
    """LCOF per fuel across every candidate land cell (2025, each cell's
    cheapest CO2 source, the same carbon layer as Fig. 2),
    on the same global grid as every map: minimum, median and maximum in
    $/MMBtu (LHV), plus the median in the unit each trade thinks in."""
    import pandas as pd
    from . import inputs, params as P
    from .fig_pptx_pairs import SUFFIX, YEARS
    from .supply_demand import lcof_cells

    meta = inputs.load_meta(2025)
    land = meta[meta.cell_type == "land"].copy()
    # each cell's median over the 20 weather years, the same cost Fig. 2
    # uses, rather than the single 2025 weather year
    frames = {y: pd.read_csv(inputs.MAPS / f"lcoh_global_{y}{SUFFIX}.csv")
              .set_index("cell_id") for y in YEARS}
    cells = frames[YEARS[0]].index
    med = pd.DataFrame({
        k: np.median(np.column_stack([frames[y].loc[cells, k] for y in YEARS]),
                     axis=1)
        for k in ("lcoh_usd_gj", "lcoe_usd_mwh")}, index=cells)
    land = land.join(med, how="inner")
    land = land[np.isfinite(land.lcoh_usd_gj)]
    # carbon at the cheapest source within reach of each cell, industrial
    # point sources included, exactly as the supply-demand map (Fig. 2)
    # prices it; DAC only where a cell reaches nothing else
    co2 = pd.read_csv(inputs.MAPS / "co2_cost_by_cell.csv")             .set_index("cell_id").co2_cost.reindex(land.index)             .fillna(P.C_CO2_DAC)
    lcof = lcof_cells(land, co2)                  # $/GJ, per fuel
    mmb = P.MMBTU_PER_GJ

    def pct(cols):
        if cols == ["hydrogen"]:            # the carrier: Stage-1 LCOH
            v = land.lcoh_usd_gj.to_numpy() * mmb
        else:
            v = np.concatenate([lcof[c].dropna().to_numpy()
                                for c in cols]) * mmb
        # 2026-10-08: a box plot - whiskers 1st-99th, box 25th-75th percentile,
        # white line the median (the 1 % of cells at each end is left out)
        return np.percentile(v, [1, 25, 50, 75, 99])   # 2026-10-13: 1st-99th everywhere in the paper

    # 2026-10-08: jet and diesel per barrel, ethanol per US gallon; GJ per unit from the
    # params LHV per litre (kerosene 35.1 MJ/L x 158.987 L; ethanol 21.2 MJ/L x 3.785 L)
    EXTRA = {("e-kerosene", "$/bbl"): 0.0351 * 158.987, ("ethanol", "$/gal"): 0.0212 * 3.78541}

    def native(f, unit, med_mmbtu):
        mult = EXTRA.get((f, unit), P.FUELS[f]["native"].get(unit))
        if mult is None:
            return ""
        v = med_mmbtu / mmb * mult
        if unit == "$/t":
            return f"$\\approx$\\${v:,.0f}/t"
        if unit == "$/L":
            return f"$\\approx$\\${v:.2f}/L"
        if unit == "$/kg":
            return f"$\\approx$\\${v:.1f}/kg"
        if unit == "$/MMBtu":
            return f"$\\approx$\\${v:.0f}/MMBtu"
        return f"$\\approx$\\${v:.0f}/MWh"

    def native_range(f, unit, q1, med, q3):
        """2026-10-07: the cost in the unit each trade quotes, printed under
        the bar ($/MMBtu stays the shared axis); since 2026-10-08 the median and, in
        brackets, the interquartile range (2026-10-13; before: 1st-99th)"""
        mult = EXTRA.get((f, unit)) or P.FUELS[f]["native"][unit]
        if f == "hydrogen":                      # params has no native unit for the carrier
            mult = 0.120                         # GJ (LHV) per kg H2
        a, m, b = (x / mmb * mult for x in (q1, med, q3))
        if unit == "$/t":
            return f"US\${m:,.0f}/t ({a:,.0f}–{b:,.0f})"
        if unit == "$/L":
            return f"US\${m:.2f}/L ({a:.2f}–{b:.2f})"
        if unit == "$/kg":
            return f"US\${m:.1f}/kg ({a:.1f}–{b:.1f})"
        if unit == "$/bbl":
            return f"US\${m:,.0f}/bbl ({a:,.0f}–{b:,.0f})"
        if unit == "$/gal":
            return f"US\${m:.2f}/gal ({a:.2f}–{b:.2f})"
        if unit == "$/MMBtu":                    # 2026-10-08: gas trades per MMBtu
            return f"US\${m:.0f}/MMBtu ({a:.0f}–{b:.0f})"
        return f"US\${m:.0f}/MWh ({a:.0f}–{b:.0f})"

    bars = []
    for label, col, cols, unit in (
            ("hydrogen", DARK, ["hydrogen"], "$/kg"),
            ("ammonia", "#0072B2", ["ammonia"], "$/t"),
            ("e-methane", "#009E73", ["e-methane"], "$/MMBtu"),
            ("methanol", "#E69F00", ["methanol"], "$/t"),
            ("e-jet / e-diesel", "#56B4E9", ["e-kerosene", "e-diesel"],
             "$/bbl"),
            ("ethanol", "#CC79A7", ["ethanol"], "$/gal")):
        p5, p25, p50, p75, p95 = pct(cols)
        # (label, colour, whisker low, median, whisker high, median native, native label, box low, box high)
        bars.append((label, col, p5, p50, p95,
                     # 2026-10-13: the trade-unit line gives the median and
                     # the interquartile range (the box), the whiskers stay 1st-99th
                     native(cols[0], unit, p50), native_range(cols[0], unit, p25, p50, p75), p25, p75))
        print(f"    {label:18s} p1 {p5:6.1f} | {p25:6.1f} / {p50:6.1f} / {p75:6.1f} | p99 {p95:6.1f} "
              f"$/MMBtu   {bars[-1][6]}")
    return bars


def _demand_mix():
    """What the demand column is worth: the addressable market, grouped
    into the five routes drawn above it. Basis = the same (economy,
    fuel) pairs the paper's headline uses, i.e. the assessed economies
    that carry both a national fossil comparator and a security ledger
    (global_trajectory_countries.csv, 97.9 EJ/yr), so the figure agrees
    with the abstract and the global-dividend section."""
    import pandas as pd
    from . import inputs

    gt = pd.read_csv(inputs.MAPS / "global_trajectory_countries.csv")
    ej = gt.groupby("fuel").dem_gj.sum() / 1e9
    # 2026-10-07: the marine fuel is made as e-methanol and e-ammonia (70/30 by
    # energy), so the bar counts it in those two routes
    grp = [("e-methane", "#009E73", {"e-methane": 1.0}),
           ("e-jet / e-diesel", "#56B4E9", {"e-kerosene": 1.0, "e-diesel": 1.0}),
           ("methanol", "#E69F00", {"methanol": 1.0, "marine": 0.7}),
           ("ammonia", "#0072B2", {"ammonia": 1.0, "marine": 0.3}),
           ("ethanol", "#CC79A7", {"ethanol": 1.0})]
    out = [(lab, col, float(sum(w * ej.get(f, 0.0) for f, w in fs.items())))
           for lab, col, fs in grp]
    tot = sum(v for *_, v in out)
    print(f"    addressable demand {tot:.1f} EJ/yr over "
          f"{gt.country.nunique()} economies: "
          + ", ".join(f"{l} {v:.1f}" for l, _, v in out))
    return out, tot


def _co2_ranges():
    """Industrial and biogenic price ranges of the carbon layer, $/t, and
    the direct-air-capture price, rounded as the box prints them."""
    import pandas as pd
    from . import inputs, params as P
    c = pd.read_csv(inputs.MAPS / "co2_cost_by_cell.csv")
    ind = c[c.pathway == "industrial"].co2_cost
    bio = c[c.pathway == "biogenic"].co2_cost
    return (int(round(ind.min())), int(round(ind.max())),
            int(round(bio.min())), int(round(bio.max())),
            int(round(P.C_CO2_DAC)))


def _observed_market():
    """The oil and gas those same economies burn, EJ per year: Energy
    Institute 2025 where it names the country, the latest OWID year
    otherwise. The caption compares the market against it."""
    import numpy as np
    import pandas as pd
    from . import inputs
    from .ei_energy import by_country, LATEST_YEAR

    gt = pd.read_csv(inputs.MAPS / "global_trajectory_countries.csv")
    base = sorted(gt.country.unique())
    ei = by_country(base)
    owid = pd.read_csv(inputs.MAPS / "demand_by_fuel.csv")
    last = owid.sort_values("year").groupby("country").last()
    gas = oil = 0.0
    n_ei = 0
    for c in base:
        g, o = ei.at[c, f"GAS_{LATEST_YEAR}"] if c in ei.index else np.nan,                ei.at[c, f"OIL_{LATEST_YEAR}"] if c in ei.index else np.nan
        if np.isfinite(o):
            n_ei += 1
            gas += 0.0 if not np.isfinite(g) else g
            oil += o
        elif c in last.index:
            gas += float(np.nan_to_num(last.at[c, "gas_gj"]))
            oil += float(np.nan_to_num(last.at[c, "oil_gj"]))
    gas, oil = gas / 1e9, oil / 1e9
    print(f"    observed market {gas + oil:.0f} EJ/yr over {len(base)} "
          f"economies (gas {gas:.0f}, oil {oil:.0f}; Energy Institute "
          f"{LATEST_YEAR} for {n_ei})")
    return gas, oil


def main():
    fig, ax = plt.subplots(figsize=(183 * MM, 100 * MM))
    fig.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.0)
    ax.set_xlim(0, 183)
    ax.set_ylim(0, 100)
    ax.set_axis_off()

    ROWS = [75.5, 63.0, 50.5, 38.0, 25.5]        # box bottoms, h 10
    HB = 10.0
    YC = [yb + HB / 2 for yb in ROWS]            # row centres
    CY = YC[2]                                   # chain centreline
    BUSX, CIRX = 59.0, 62.5                      # H2 bus / feed circles
    # route boxes: 2 mm right of v19, so each hydrogen arrow's head shows
    # whole between its feed circle and its box (it was buried under the
    # circle), and the column sits in its card with the same margin on
    # both sides (1.3 mm, the bus's margin on the left)
    BXL, BXW = 68.0, 36.0
    BXR = BXL + BXW
    # where every arrow into a demand box ends: on its outline
    IND_TIP = _rim(126.0 - 0.45, 1.1, -1) + TOUCH

    # three stages, each on ONE continuous tinted ground that WRAPS its
    # own content with the same margin — no frames, no broken edges, and
    # nothing drawn across a boundary; a small-cap word above each
    # carries the reading order
    # one height for all three: the tallest stage (the fuel column, which
    # carries the CO2 feed under it and the N2 note above it) sets it
    CY0, CY1 = 2.5, 93.5
    CARDS = [(3.0, 56.5, CY0, CY1, "#EDF4FA",
              "RENEWABLE ELECTRICITY  →  HYDROGEN"),
             (57.5, 106.0, CY0, CY1, "#FBF3E8", "HYDROGEN  →  FUEL"),
             (123.5, 181.0, CY0, CY1, "#F1F3F5", "DEMAND")]
    HY = 96.8
    for x0, x1, y0, y1, tint, lab in CARDS:
        ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0,
                                    boxstyle="round,pad=0.0,"
                                    "rounding_size=2.2",
                                    fc=tint, ec="none", zorder=0))
        ax.text((x0 + x1) / 2, HY, lab, fontsize=FS - 1, color=GREY,
                ha="center", va="center", zorder=6, fontweight="bold")

    # ---- stage 1: wind and solar drop onto one node, the battery hangs
    # below it, and the node feeds the electrolyser and the store --------
    _turbine(ax, 9.5, 67.5, s=1.35)
    _turbine(ax, 14.5, 67.1, s=1.05)
    _pv(ax, 16.0, 66.0)
    ax.text(13.5, 63.0, "wind + solar", fontsize=FS, ha="center",
            color=INK, fontweight="bold")
    # one line carries the electrons: generation drops onto it, the
    # battery hangs below it, and it feeds the electrolyser
    ax.plot([16.0, 16.0], [31.3, 61.5], color=BLUE, lw=1.3, zorder=3,
            solid_capstyle="round")
    _battery(ax, 12.5, 27.5)
    ax.text(21.8, 29.4, "battery", fontsize=FS - 1, color=INK,
            va="center", ha="left")
    # the electrolyser sits 1.5 mm left of v19, so the arrow on to the
    # store has a real shaft (it was a bare head between the two)
    EX, EY, EW, EH = 27.5, 47.0, 12.0, 17.0      # electrolyser box
    # tail on the electricity line (the arrow is 0.2 pt wider than the
    # line, so its round tail cap sits 0.1 pt right of centre to stay
    # flush with the line's left side); tip on the electrolyser outline
    _arrow(ax, (16.0 + (1.5 - 1.3) / 2.0 * PT, CY),
           (_rim(EX - 0.35, 1.2, -1) + TOUCH, CY), color=BLUE, lw=1.5)
    _elz(ax, EX, EY, w=EW, h=EH)
    ax.text(EX + 6.0, 43.8, "electrolysis", fontsize=FS, ha="center",
            color=BLUE, fontweight="bold")
    ax.text(EX + 7.0, 71.6, "H$_2$O · US\\$0.6–1.9/t", fontsize=FS - 1.8,
            color=INK, ha="center", zorder=6)
    _arrow(ax, (EX + 7.0, 69.9),
           (EX + 7.0, _rim(EY + EH + 0.35, 1.2, +1) - TOUCH),
           color=GREY, lw=1.0, ms=7)
    # electrolyser -> store: from one outline to the other
    _arrow(ax, (_rim(EX + EW + 0.35, 1.2, +1), CY),
           (_rim(45.0 - 0.3, 1.3, -1) + TOUCH, CY), color=BLUE, lw=1.5)
    _vessel(ax, 45.0, CY - 4.0, w=9.5, h=8.0)
    # "storage", not "store": it is the pressurized H2 tank the LP sizes
    # to carry the electrolyser's output through calm spells
    ax.text(49.75, 43.8, "storage", fontsize=FS - 1, ha="center",
            color=INK)

    # H2 bus: one vertical manifold, straight branches into each route
    ax.plot([54.9, BUSX], [CY, CY], color=BLUE, lw=1.3,
            solid_capstyle="round", zorder=4)
    ax.plot([BUSX, BUSX], [YC[-1], YC[0]], color=BLUE, lw=1.3,
            solid_capstyle="round", zorder=4)

    # N2 into the ammonia branch, straight from air: it is not bought,
    # but it is not free either — the air-separation unit's own power
    # is the largest auxiliary-electricity term in the cascade
    # nitrogen is never bought — its cost is the on-site air-separation
    # unit's own power, which the caption states; the figure says only
    # where it comes from
    ax.text(CIRX + 6.5, 90.0, "N$_2$ from air", fontsize=FS - 1.8,
            color=INK, ha="center", zorder=6)
    # the feed circles are r 2.5, outlined 0.8 pt; a tip ends on that
    # outline (the circle, drawn above, covers the last TOUCH of it)
    CIR_RIM = _rim(2.5, 0.8, +1) - TOUCH
    _arrow(ax, (CIRX, 88.1), (CIRX, YC[0] + CIR_RIM), color=GREY,
           lw=1.0, ms=7)

    # the CO2 feed sits under the fuel boxes, in the stage that uses it;
    # one manifold rises from it through every carbon route's feed circle
    # same left and right edge as the fuel boxes above it, and a clear
    # gap to the lowest of them
    ax.add_patch(FancyBboxPatch((BXL, 13.8), BXW, 8.0,
                                boxstyle="round,pad=0.45,rounding_size=1.0",
                                fc="white", ec=GREY, lw=1.0, zorder=3))
    ax.text(BXL + BXW / 2, 19.7, "CO$_2$ feed", fontsize=FS - 1.5,
            color=DARK, fontweight="bold", ha="center", va="center",
            zorder=5)
    # the ranges are read from the carbon layer the cost bars use, so the
    # box can never disagree with the figure it sits in
    ci0, ci1, cb0, cb1, cdac = _co2_ranges()
    # 2026-10-08: with "US$" the two sources no longer fit one line; DAC = direct air capture (caption)
    for ly, txt in ((17.1, f"industry US\\${ci0}–{ci1}/t"),
                    (15.0, f"biomass US\\${cb0}–{cb1}/t · DAC US\\${cdac}/t")):
        ax.text(BXL + BXW / 2, ly, txt, fontsize=FS - 2.0, color=INK,
                ha="center", va="center", zorder=5)
    # one path: out of the box's outline, round the elbow, up through the
    # carbon routes' circles to the e-methane one
    _arrow(ax, (_rim(BXL - 0.45, 1.0, -1), 17.8), (CIRX, 17.8),
           (CIRX, YC[1] - CIR_RIM), color=GREY, lw=1.1, ms=8)

    # ---- the routes, each carrying its LCOF range on a shared axis --------
    bars = _cost_ranges()                       # hydrogen first, then fuels
    # the fuel axis keeps the route boxes' width but is centred on its
    # stage card, like the other two bottom rows; the cost bars move with it
    AXW = BXW - 4.0
    C2 = (CARDS[1][0] + CARDS[1][1]) / 2.0
    XL, XR = C2 - AXW / 2.0, C2 + AXW / 2.0
    # the axis ends on a labelled tick just above the dearest bar, so its
    # full length is read against a number rather than running on blank
    top = max(b[4] for b in bars)
    STEP = 50.0 if top > 100 else 25.0
    vmax = float(np.ceil(top / STEP) * STEP)

    # the hydrogen bar lives in stage 1, where hydrogen is made, on its
    # own copy of the SAME scale (same dollars per unit of width), so
    # each card carries the cost of what it produces
    # the hydrogen axis ends at its own top (same scale as the fuel axis),
    # and that shorter axis, its bar and its title are centred on stage 1
    H_TOP = float(np.ceil(bars[0][4] / STEP) * STEP)
    H_LEN = (XR - XL) * H_TOP / vmax
    XL2 = (CARDS[0][0] + CARDS[0][1]) / 2.0 - H_LEN / 2.0
    XR2 = XL2 + (XR - XL)
    AXY = 11.0

    def xv(v):
        return XL + (XR - XL) * v / vmax

    def xv2(v):
        return XL2 + (XR2 - XL2) * v / vmax

    def _range_bar(yc_bar, col, lo, p50, hi, xf=None, q1=None, q3=None):
        xf = xf or xv
        # 2026-10-08: box plot - whiskers 5th-95th percentile with end caps,
        # box 25th-75th percentile, white median line
        ax.plot([xf(lo), xf(q1)], [yc_bar, yc_bar], color=col, lw=1.0, zorder=4,
                solid_capstyle="butt")
        ax.plot([xf(q3), xf(hi)], [yc_bar, yc_bar], color=col, lw=1.0, zorder=4,
                solid_capstyle="butt")
        for xw in (lo, hi):
            ax.plot([xf(xw), xf(xw)], [yc_bar - 0.55, yc_bar + 0.55], color=col, lw=1.0, zorder=4)
        ax.add_patch(FancyBboxPatch(
            (xf(q1), yc_bar - 0.95), xf(q3) - xf(q1), 1.9,
            boxstyle="round,pad=0.0,rounding_size=0.5", fc=col,
            ec="none", alpha=0.85, zorder=5))
        ax.plot([xf(p50), xf(p50)], [yc_bar - 0.95, yc_bar + 0.95],
                color="white", lw=1.2, zorder=6)
        # no numbers on the bars: the axis below carries the scale, the
        # caption the medians

    def _axis(x0, x1, xf, title=None, amax=None):
        # amax shortens an axis without changing its scale: the hydrogen
        # axis ends at its own labelled top, on the same dollars per unit
        # of width as the fuel axis
        step = STEP
        amax = vmax if amax is None else amax
        x1 = xf(amax)
        ax.plot([x0, x1], [AXY, AXY], color=GREY, lw=0.7, zorder=3)
        for tv in np.arange(0, amax + 1, step):
            ax.plot([xf(tv), xf(tv)], [AXY, AXY - 0.6], color=GREY,
                    lw=0.6, zorder=3)
            ax.text(xf(tv), AXY - 1.4, f"{tv:.0f}", fontsize=FS - 2.0,
                    color=GREY, ha="center", va="top", zorder=6)
        if title:
            ax.text((x0 + x1) / 2, AXY - 5.2, title, fontsize=FS - 1.5,
                    color=INK, ha="center", va="center", zorder=6)

    routes = [
        ("ammonia", "#0072B2", "N$_2$", "farm", "agriculture",
         ["#0072B2"]),
        ("e-methane", "#009E73", "CO$_2$", "house",
         "buildings + industry", ["#009E73", "#56B4E9"]),
        ("methanol", "#E69F00", "CO$_2$", "ship",
         "chemicals + shipping", ["#E69F00", "#0072B2"]),
        ("e-jet / e-diesel", "#56B4E9", "CO$_2$", "plane",
         "aviation", ["#56B4E9"]),
        ("ethanol", "#CC79A7", "CO$_2$", "truck", "road transport",
         ["#CC79A7", "#56B4E9"]),
    ]
    for (name, col, feed, kind, ind, sup), yb, yc, br in zip(
            routes, ROWS, YC, bars[1:]):
        ax.add_patch(FancyBboxPatch((BXL, yb), BXW, HB,
                                    boxstyle="round,pad=0.45,"
                                    "rounding_size=1.0",
                                    fc="white", ec=col, lw=1.2, zorder=3))
        ax.text(BXL + BXW / 2, yb + 7.4, name, ha="center", va="center",
                fontsize=FS, color=col, fontweight="bold", zorder=5)
        _range_bar(yb + 3.1, col, br[2], br[3], br[4], q1=br[7], q3=br[8])
        # centred in the box (min-max bars start at its left edge, 2026-10-08)
        ax.text(BXL + BXW / 2, yb + 0.75, br[6], fontsize=FS - 2.0,
                color=GREY, ha="center", va="center", zorder=6)
        # tail on the bus's centre line (same width, so the round cap
        # closes the T, and the bus's end corners, with no seam); it runs
        # under the feed circle and its head lands on the box outline
        _arrow(ax, (BUSX, yc), (_rim(BXL - 0.45, 1.2, -1) + TOUCH, yc),
               color=BLUE, lw=1.3)
        ax.add_patch(Circle((CIRX, yc), 2.5, fc="white", ec=GREY,
                            lw=0.8, zorder=6))
        ax.text(CIRX, yc, feed, fontsize=FS - 1.6, ha="center",
                va="center", color=INK, zorder=7)
        _arrow(ax, (_rim(BXR + 0.45, 1.2, +1), yc), (IND_TIP, yc),
               color=col, lw=1.3)
        # the box itself is neutral — demand is fuel-agnostic — but the
        # dots repeat every fuel that can serve the sector, so a reader
        # sees at once where two routes compete
        _industry(ax, 126, yb, 52.5, HB, kind, "#5A6570", ind,
                  dots=sup)

    # a sector can be served by more than one fuel — the paper's own
    # sector-to-fuel mapping sends ammonia to shipping and chemicals
    # too, and e-diesel to road transport alongside ethanol. The
    # vertical run simply crosses the arrows it passes (2026-10-03: the
    # white "hop" halo read as a broken line, so it was removed).
    # 2026-10-13: e-diesel also replaces the oil burned in buildings and
    # industry (demand_grid.FUEL_MAP), about 30% of its demand, so a third
    # run goes UP from its box; rows below run down, rows above run up
    def _second(r_from, r_to, col, xv):
        s = -1 if r_to > r_from else +1
        y0 = YC[r_from] + s * 2.6
        y1 = YC[r_to] - s * 2.6
        # one path, box outline to box outline, round joins at both elbows
        _arrow(ax, (_rim(BXR + 0.45, 1.2, +1), y0), (xv, y0), (xv, y1),
               (IND_TIP, y1), color=col, lw=1.0, zorder=5)

    _second(0, 2, "#0072B2", 114.0)   # ammonia -> chemicals + shipping
    _second(3, 4, "#56B4E9", 118.0)   # e-diesel -> road transport
    _second(3, 1, "#56B4E9", 118.0)   # e-diesel -> buildings + industry (oil)

    # the carrier all five share — a dashed reference row, same column
    # the carrier, priced in the stage that makes it: under the store,
    # inside the first card, on the same scale as the fuels
    hyd = bars[0]
    _range_bar(17.0, DARK, hyd[2], hyd[3], hyd[4], xf=xv2, q1=hyd[7], q3=hyd[8])
    # 2026-10-08: no second ($/kg) scale; the $/kg median and IQR
    # are written under the bar, as for the fuels
    ax.text((xv2(0) + xv2(H_TOP)) / 2, 14.6, hyd[6], fontsize=FS - 2.0, color=GREY,
            ha="center", va="center", zorder=6)
    _axis(XL2, XR2, xv2,
          title="levelized cost of hydrogen (US\\$ MMBtu$^{-1}$)",
          amax=H_TOP)
    _axis(XL, XR, xv,
          title="levelized cost of synthetic fuel (US\\$ MMBtu$^{-1}$)")

    # ---- what the demand column is worth: one bar, the hard-to-electrify
    # demand split into the five routes in the colours of their fuel
    # boxes, with each route's share. Kept to one bar and one short line;
    # the size of today's oil and gas market it is a slice of is stated
    # in the caption rather than drawn.
    mix, mix_tot = _demand_mix()
    _observed_market()                      # printed for the caption only
    DX0, DX1 = 126.0, 178.5
    SCALE = (DX1 - DX0) / mix_tot
    ON_LIGHT = {"#56B4E9", "#E69F00"}
    left = DX0
    # largest route first, so the bar reads from the biggest market down
    for lab, col, v in sorted(mix, key=lambda m: -m[2]):
        w = v * SCALE
        ax.add_patch(FancyBboxPatch(
            (left, 16.2), w, 2.6,
            boxstyle="round,pad=0.0,rounding_size=0.0", fc=col,
            ec="white", lw=0.8, zorder=5))
        if w >= 2.0:
            ax.text(left + w / 2, 17.5, f"{100 * v / mix_tot:.0f}",
                    fontsize=FS - 2.0,
                    color=INK if col in ON_LIGHT else "white",
                    ha="center", va="center", zorder=6)
        left += w
    from . import params as P
    # P.MMBTU_PER_GJ is GJ per MMBtu (1.0551), so EJ -> bn MMBtu divides
    ax.text((DX0 + DX1) / 2, AXY - 5.2,
            f"demand by fuel (% of {mix_tot / P.MMBTU_PER_GJ:.0f} "
            "billion MMBtu per year)",
            fontsize=FS - 1.5, color=INK, ha="center", va="center",
            zorder=6)

    fig.savefig(OUT / "fig_main_framework.pdf", bbox_inches="tight")
    fig.savefig(OUT / "fig_main_framework.png", dpi=600,
                bbox_inches="tight")
    plt.close(fig)
    print("saved fig_main_framework.(pdf|png)  v20 joined connectors")


if __name__ == "__main__":
    main()
