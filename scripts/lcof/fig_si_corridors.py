"""
fig_si_corridors.py - Supplementary figure (2026-10-09: the transport corridors as a figure
with regional zooms, as in the job-talk deck): a, the six ammonia corridors of Supplementary
Table tab:corridors on the Fig. 2 supply-demand classes, each labelled with its transport cost and
how much cheaper the delivered ammonia is than production at the destination; b-g, six regions with
the largest cell-to-cell flows within countries when fuel can move on spare land (domestic-capped
rule at US$1 per GJ per 1,000 km, Supplementary Table tab:transport) and the corridors that start
or end there.

Reads the sandbox the caller points inputs.MAPS at (sd_map_classes.csv, corridors_discussion.csv,
transport_summary.csv and the cost layers); re-solves the flows with lcof.transport_flows into
the figure folder; writes fig_si_corridors.(pdf|png) to fig_pptx_pairs.OUT. The kriged Fig. 2 field
is recomputed (no cache from the talk folder).

From scripts/:  python ../work/caselow/run_mod.py <sandbox> 2025 lcof.fig_si_corridors  (LCOF_TIER=mid)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

mpl.use("Agg")

from . import inputs
from . import fig_pptx_pairs as FPP
from . import corridor_maps as V
from . import transport_flows as TTF
from .fig_main_cost import MM, NAT_RC

INK, GREY = "#1F2A36", "#5A6570"
FLOW = "#14304A"
# corridor order = rows of corridors_discussion.csv = V.CORR
SHORT = ["Iberia → Germany", "North Africa → Italy", "Inner Mongolia →\nNorth China Plain", "Pilbara → Japan",
         "Northern Chile → Rotterdam (Panama)", "Oman → Rotterdam (Suez)", "Oman → Rotterdam (Cape)"]
# label anchors (lon, lat) in open water / off the route
# 2026-10-22 (7 pt boxes): Inner Mongolia in the open Pacific south of Japan, Pilbara in the Indian Ocean, both
# with a leader, so no box covers land
AT = [(-33, 55), (-33, 38.5), (157, 16), (82, -30), (-108, -2), None, None]
NARROW = (2, 3)                       # boxes whose cost line is broken in two
ZOOMS = [("China", (72, 136, 17, 55)), ("India", (62, 100, 5, 37)), ("United States", (-126, -66, 22, 52)),
         ("Europe", (-14, 40, 28, 63)), ("Middle East", (30, 66, 10, 40)), ("Africa", (-20, 54, -38, 38))]


def _corridor(ax, pts, mode, lw=1.0):
    x, y = V._spline(pts)
    halo = [pe.withStroke(linewidth=(2.6 if mode == "land" else 2.0) * lw, foreground="white")]
    ax.plot(x, y, color=INK, lw=(1.4 if mode == "land" else 0.9) * lw, ls="-" if mode == "land" else (0, (3, 1.6)),
            zorder=7, path_effects=halo, solid_capstyle="round")
    ax.annotate("", xy=(x[-1], y[-1]), xytext=(x[-8], y[-8]), zorder=8,
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.9 * lw, mutation_scale=7 * lw,
                                shrinkA=0, shrinkB=0))
    return x, y


def _box(ax, xy, text, fs=6, lead=None):
    ax.text(xy[0], xy[1], text, fontsize=fs, color=INK, ha="center", va="center", zorder=9, linespacing=1.15,
            bbox=dict(boxstyle="round,pad=0.22", fc="white", ec="#B8C2CC", lw=0.4, alpha=0.95))
    if lead is not None:
        ax.plot([xy[0], lead[0]], [xy[1], lead[1]], color=GREY, lw=0.4, zorder=6.5)


def main():
    mpl.rcParams.update(NAT_RC)
    mpl.rcParams.update({"pdf.fonttype": 42})
    out = FPP.OUT
    tmp = out / "_corridors_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    V.OUT = tmp                      # kriging cache of this sandbox, never the talk folder's
    TTF.OUT = tmp
    TTF.main()                       # flows at US$1/GJ per 1,000 km, checked against transport_summary.csv
    fl = pd.read_csv(tmp / "_flows_domestic-capped.csv")
    cd = pd.read_csv(inputs.MAPS / "corridors_discussion.csv")
    assert len(cd) == len(V.CORR)
    SD, df, Uz, Vz, Dz = V._kriged()
    rgb = V._class_rgb(SD, Uz, Vz, Dz)

    W = 183 * MM
    fig = plt.figure(figsize=(W, 200 * MM))
    # ---- a: world -------------------------------------------------------------------
    ax = fig.add_axes([0.0, 0.585, 1.0, 0.395])
    ax.set_xlim(-180, 180); ax.set_ylim(-58, 84); ax.set_aspect("equal"); ax.axis("off")
    V._paint(ax, SD, rgb, lw=0.45)
    for k, (name, mode, pts, *_r) in enumerate(V.CORR):
        x, y = _corridor(ax, pts, mode)
        r = cd.iloc[k]
        if AT[k] is not None:
            lead = (x[len(x) // 2], y[len(y) // 2]) if mode == "land" else ((x[0], y[0]) if k == 3 else None)
            sep = ",\n" if k in NARROW else ", "
            _box(ax, AT[k], f"{SHORT[k]}\n+US\\${r.transport:.1f}/MMBtu{sep}{r.saving_pct:.0f}% cheaper", lead=lead)
    rs, rc = cd.iloc[5], cd.iloc[6]
    _box(ax, (78, -8), f"Oman → Rotterdam\nvia Suez +US\\${rs.transport:.1f}, {rs.saving_pct:.0f}% cheaper\n"
                       f"via the Cape +US\\${rc.transport:.1f}, {rc.saving_pct:.0f}% cheaper")
    fig.text(0.005, 0.975, "a", fontsize=8, fontweight="bold", va="top")
    # legend
    pal = V._pal(SD)
    hs = [Patch(fc=pal[2][2], ec="none", label="build-first (low cost, high demand); colors as Fig. 2"),
          Patch(fc=pal[2][0], ec="none", label="export-oriented (low cost, low demand)"),
          Patch(fc=pal[0][2], ec="none", label="supply-strained (high cost, high demand)"),
          Line2D([], [], color=INK, lw=1.4, label="overland corridor"),
          Line2D([], [], color=INK, lw=0.9, ls=(0, (3, 1.6)), label="sea corridor"),
          Line2D([], [], color=FLOW, lw=1.2, marker=">", ms=3, label="largest flows within countries (b–g)")]
    fig.legend(handles=hs, loc="lower center", bbox_to_anchor=(0.5, 0.545), ncol=3, fontsize=6, frameon=False,
               handlelength=1.8, columnspacing=1.4)
    # ---- b-g: zooms -----------------------------------------------------------------
    cmap = {"China": [2], "Europe": [0, 1], "Middle East": [5], "Africa": [6]}
    for k, (name, (x0, x1, y0, y1)) in enumerate(ZOOMS):
        r_, c_ = divmod(k, 3)
        rect = [c_ / 3 + 0.008, 0.285 - r_ * 0.285, 1 / 3 - 0.016, 0.215]
        ax = fig.add_axes(rect)
        ax.set_anchor("N")
        ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal")
        ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_edgecolor("#C8CFD8"); s.set_linewidth(0.5)
        V._paint(ax, SD, rgb, lw=1.0)
        m = (fl.dest_lon.between(x0, x1) & fl.dest_lat.between(y0, y1)
             & fl.src_lon.between(x0, x1) & fl.src_lat.between(y0, y1))
        g = fl[m].nlargest(10, "gj")
        if len(g):
            gmax = g.gj.max()
            for _, f in g.iterrows():
                lw = 0.4 + 1.1 * np.sqrt(f.gj / gmax)
                an = ax.annotate("", xy=(f.dest_lon, f.dest_lat), xytext=(f.src_lon, f.src_lat), zorder=7,
                                 arrowprops=dict(arrowstyle="-|>", color=FLOW, lw=lw, mutation_scale=4 + 2.5 * lw,
                                                 alpha=0.9, shrinkA=0.5, shrinkB=0.5,
                                                 path_effects=[pe.withStroke(linewidth=lw + 1.0, foreground="white")]))
                an.set_clip_on(True)
                an.arrow_patch.set_clip_box(ax.bbox)
        sub = []
        for i in cmap.get(name, []):
            nm, mode, pts, *_r = V.CORR[i]
            n0 = len(ax.lines)
            _corridor(ax, pts, mode, lw=1.0)
            for ln in ax.lines[n0:]:
                ln.set_clip_on(True)
            for ch in ax.texts + ax.patches:
                ch.set_clip_on(True)
            # 2026-10-22 (7 pt): the route only; its transport cost and saving are on the map of panel a
            sub.append(SHORT[i].replace(chr(10), chr(32)))
        if not sub:
            moved = g.gj.sum() / 1.0551e9 if len(g) else 0.0
            sub = ["ten largest within-country flows:", f"{moved:.2f} billion MMBtu a year"]
        top = rect[1] + rect[3]
        letter = "bcdefg"[k]
        H_mm = fig.get_figheight() * 25.4
        fig.text(rect[0], top + (1.5 + 3.0 * 2) / H_mm, f"{letter}  {name}", fontsize=7, fontweight="bold",
                 color=INK, va="bottom")
        fig.text(rect[0], top + 0.8 / H_mm, chr(10).join(sub), fontsize=7, color=GREY, va="bottom", linespacing=1.1)
    for a_ in fig.axes:
        a_.set_rasterization_zorder(5)     # map fill and boundaries rasterized; routes, arrows, text vector
    fig.savefig(out / "fig_si_corridors.pdf", bbox_inches="tight", dpi=300)
    fig.savefig(out / "fig_si_corridors.png", dpi=300, bbox_inches="tight")
    print("saved", out / "fig_si_corridors.pdf")


if __name__ == "__main__":
    main()
