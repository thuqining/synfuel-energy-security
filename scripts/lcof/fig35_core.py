"""
fig35_core.py — main-text Figs 3 and 5 (2026-10-21): a, the 30 core economies (lcof.fig3_cols / lcof.fig5_cols, one
row); b, a world map of all 139 economies (lcof.figmap, in the style of Fig. 2). The 139-economy charts go to the SI.

    python -m lcof.fig35_core fig3 <out stem> [a_mm b_mm]
    python -m lcof.fig35_core fig5 <out stem> [a_mm b_mm]
"""
import json
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd

mpl.use("Agg")

from lcof import fig3_cols, fig5_cols, figmap
from lcof.fig_main_cost import MM
from lcof.figcheck import report

R = Path(__file__).resolve().parents[2]


def _data():
    t = (R / "console/index.html").read_text(encoding="utf-8")
    return json.JSONDecoder().raw_decode(t[t.index("const DATA=") + 11:])[0]["countries"]


def core30():
    return set(pd.read_csv(R / "work/caselow/2030/data/fig5a_chain.csv", index_col=0).index)


def k139():
    return list(pd.read_csv(R / "work/caselow/2030/data/security_budget.csv", index_col=0).index)


def fig3_classes():
    """domestic green ammonia (lowest-cost cell, median weather year, with delivery) against the economy's own
    disruption-period ammonia price"""
    C, cat = _data(), {}
    for c in k139():
        d = C.get(c, {})
        pr, bx, e = d.get("pr", {}).get("amm"), d.get("box", {}).get("ammonia"), d.get("E_amm")
        if not pr or not bx:
            continue
        m = bx[2]
        cat[c] = "x" if (e is None or e <= 0) else ("med" if m <= pr["d"][2] else ("p90" if m <= pr["d"][4] else "above"))
    colors = {"med": "#0B4F9E", "p90": "#7FB2E0", "above": "#D9D9D9", "x": "#DDB967"}
    # 2026-10-22 (user): "above both" was redundant; the middle class lies between the two percentiles
    labels = {"med": "< median", "p90": "median–90th percentile", "above": "> 90th percentile",
              "x": "Net exporters"}
    return cat, colors, labels, "Green ammonia vs disruption price"


def fig5_classes(year="2030"):
    C = _data()
    cat = {c: C[c]["f5"][year]["grp"] for c in k139() if C.get(c, {}).get("f5", {}).get(year)}
    colors = {"imports covered": "#0B4F9E", "budget binds": "#A8CCEC", "land binds": "#9A9A9A",
              "net exporter": "#DDB967"}
    labels = {"imports covered": "Imports covered", "budget binds": "Budget binds", "land binds": "Land binds",
              "net exporter": "Net exporters"}
    return cat, colors, labels, None


def fig5_years(stem, a_mm=88.0, b_mm=40.0):
    """2026-10-21: Fig. 5 with all three cost years. a, the core 30: for each economy three bars (2030, 2040, 2050
    costs, left to right), each the share of fuel demand made at home with 1, 2 and 3% of GDP (dark to light blue),
    a black cap at that year's land ceiling, and the imported share (red triangle). Groups and order of 2030.
    b, the 139 economies by binding constraint at 2030, 2040 and 2050 costs."""
    from matplotlib.lines import Line2D
    from matplotlib.patches import Rectangle, Patch
    from lcof.figgroups import mark_groups, count, col_font
    from lcof.fig3_rows import SHORT
    t = (R / "console/index.html").read_text(encoding="utf-8")
    D = json.JSONDecoder().raw_decode(t[t.index("const DATA=") + 11:])[0]
    C, core = D["countries"], core30()
    rows = [c for c in D["order"]["f5"]["2030"] if c in core]
    years = ("2030", "2040", "2050")
    BC, INK, RED = ["#0B4F9E", "#4A90D9", "#A8CCEC"], "#1A1A1A", "#CB181D"
    GLAB = {"imports covered": "Imports covered", "budget binds": "Budget binds", "land binds": "Land binds",
            "net exporter": "Net exporters"}
    grp = lambda c: C[c]["f5"]["2030"]["grp"]
    fig = plt.figure(figsize=(183 * MM, (a_mm + b_mm) * MM))
    sa, sb = fig.subfigures(2, 1, height_ratios=[a_mm, b_mm], hspace=0)
    top_mm, bot_mm = 15.0, 19.0
    ax = sa.add_axes([0.06, bot_mm / a_mm, 0.935, 1 - (top_mm + bot_mm) / a_mm])
    ax.set_xlim(-0.6, len(rows) - 0.4)
    fs = col_font(ax, 1.0)
    # 2026-10-21: drawn like Fig. 4a: per economy three cost years (2030, 2040, 2050, left to right) in the colours
    # and shapes of Fig. 4a; each a line from the share 1% of GDP buys (filled marker) to the share 3% buys (open
    # marker), with a tick at 2%; a black tick at that year's land ceiling; the imported share as a red triangle
    from lcof.fig4a_cols import YC, MK
    yc = {y: YC[int(y)] for y in years}
    mk = {y: MK[int(y)] for y in years}
    off = (-0.27, 0.0, 0.27)
    for i, c in enumerate(rows):
        imp = C[c]["f5"]["2030"]["imp"]
        if imp and imp > 0:
            ax.plot([i - 0.42, i + 0.42], [min(imp, 100)] * 2, color=RED, lw=0.9, zorder=2, solid_capstyle="butt")
        for j, y in enumerate(years):
            r = C[c]["f5"][y]
            x = i + off[j]
            ax.plot([x, x], [r["s1"], r["s3"]], color=yc[y], lw=0.9, zorder=3, solid_capstyle="butt")
            ax.plot([x - 0.07, x + 0.07], [r["s2"]] * 2, color=yc[y], lw=0.9, zorder=3, solid_capstyle="butt")
            ax.scatter([x], [r["s3"]], s=9, marker=mk[y], facecolor="white", edgecolor=yc[y], linewidths=0.7,
                       zorder=4, clip_on=False)
            ax.scatter([x], [r["s1"]], s=9, marker=mk[y], color=yc[y], lw=0, zorder=5, clip_on=False)
            if r["land"] < 99.95:
                ax.plot([x - 0.12, x + 0.12], [r["land"]] * 2, color=INK, lw=1.2, solid_capstyle="butt", zorder=6)
    mark_groups((ax,), ax, rows, grp, GLAB, count(rows, grp), pad_pt=4.5, fontsize=7.0, band_axes=())
    ax.set_ylim(0, 100)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_yticklabels(["0", "25", "50", "75", "100"], fontsize=6.5)
    ax.set_ylabel("Share of fuel demand made at home (%)", fontsize=7, labelpad=2)
    ax.set_xticks(range(len(rows)))
    ax.set_xticklabels([SHORT.get(c, c) for c in rows], rotation=90, fontsize=fs, color=INK)
    ax.tick_params(axis="x", length=0, pad=1.5)
    ax.tick_params(axis="y", length=2, pad=1.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    h = [Line2D([], [], ls="none", marker=mk[y], ms=3.6, color=yc[y]) for y in years]
    h += [Line2D([], [], ls="none", marker="o", ms=3.4, color=INK),
          Line2D([], [], ls="none", marker="o", ms=3.4, mfc="white", mec=INK, mew=0.7),
          Line2D([], [], color=INK, lw=0.9, marker="_", ms=4, markevery=[1]),
          Line2D([], [], color=INK, lw=1.2), Line2D([], [], color=RED, lw=0.9)]
    sa.legend(h, [f"{y}" for y in years] + ["1% of GDP", "3% of GDP", "2% of GDP (tick)", "Land ceiling",
                                            "Imported share"], loc="upper center", ncol=8, fontsize=7.0,
              frameon=False, bbox_to_anchor=(0.53, 1.0), handlelength=1.3, columnspacing=1.2, borderaxespad=0.2)
    # b: three maps, one per cost year, key below
    # 2026-10-21: not the year blues of a: imports covered in the security green, budget binds in Fig. 2's muted
    # purple, land binds gray, net exporters sand as in Figs 3 and 4
    colors = {"imports covered": "#2E8B57", "budget binds": "#B3A6CC", "land binds": "#9A9A9A",
              "net exporter": "#DDB967"}
    hd = None
    for j, y in enumerate(years):
        cat = {c: C[c]["f5"][y]["grp"] for c in k139() if C.get(c, {}).get("f5", {}).get(y)}
        ax_m, hd = figmap.draw(sb, cat, colors, GLAB, rect=(0.005 + j * 0.332, 0.16, 0.325, 0.74), legend=False)
        ax_m.set_title(f"{y} costs", fontsize=7.0, fontweight="bold", pad=1.5)
    # one key for the three maps, without counts (they differ by year; the caption gives them)
    hd = [Patch(fc=colors[k], ec="none", label=GLAB[k]) for k in colors]
    sb.legend(handles=hd, loc="lower center", ncol=4, fontsize=7.0, frameon=False, bbox_to_anchor=(0.5, 0.0),
              handlelength=1.5, columnspacing=1.6, borderaxespad=0.2)
    for s, letter, mm in ((sa, "a", a_mm), (sb, "b", b_mm)):
        s.text(0.004, 1 - 1.2 / mm, letter, fontsize=8, fontweight="bold", ha="left", va="top")
    report(fig, Path(stem).name)
    out = Path(stem)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out.with_suffix(".pdf"))
    fig.savefig(out.with_suffix(".png"), dpi=300)
    plt.close(fig)
    print(f"saved {out}.(pdf|png): {a_mm} + {b_mm} mm")


def fig5_panels(stem, panel_mm=34.0, map_mm=40.0):
    """2026-10-21: Fig. 5 as before, one panel per cost year (a 2030, b 2040, c 2050) for the core 30, bars stacked
    for 1, 2 and 3% of GDP (dark to light blue), unused land hatched up to the land ceiling (black cap), imported
    share (red triangle); one economy order for all three (the groups and order of 2030), groups marked on a, names
    under c. d, the 139 economies by binding constraint at 2030, 2040 and 2050 costs."""
    from matplotlib.lines import Line2D
    from matplotlib.patches import Rectangle, Patch
    from lcof.figgroups import mark_groups, count, col_font
    from lcof.fig3_rows import SHORT
    mpl.rcParams.update({"hatch.color": "#7F8A95", "hatch.linewidth": 0.5})
    t = (R / "console/index.html").read_text(encoding="utf-8")
    D = json.JSONDecoder().raw_decode(t[t.index("const DATA=") + 11:])[0]
    C, core = D["countries"], core30()
    rows = [c for c in D["order"]["f5"]["2030"] if c in core]
    years = ("2030", "2040", "2050")
    BC, INK, RED = ["#0B4F9E", "#4A90D9", "#A8CCEC"], "#1A1A1A", "#CB181D"
    GLAB = {"imports covered": "Imports covered", "budget binds": "Budget binds", "land binds": "Land binds",
            "net exporter": "Net exporters"}
    grp = lambda c: C[c]["f5"]["2030"]["grp"]
    leg_mm, grp_mm, gap_mm, name_mm = 7.0, 8.0, 4.0, 19.0
    top_mm = leg_mm + grp_mm + 3 * panel_mm + 2 * gap_mm + name_mm
    fig = plt.figure(figsize=(183 * MM, (top_mm + map_mm) * MM))
    sa, sb = fig.subfigures(2, 1, height_ratios=[top_mm, map_mm], hspace=0)
    axes = []
    for j, y in enumerate(years):
        y1 = top_mm - leg_mm - grp_mm - (j + 1) * panel_mm - j * gap_mm
        ax = sa.add_axes([0.085, y1 / top_mm, 0.91, panel_mm / top_mm])
        axes.append(ax)
        ax.set_xlim(-0.6, len(rows) - 0.4)
        w = 0.38
        for i, c in enumerate(rows):
            r = C[c]["f5"][y]
            lv = [0, r["s1"], r["s2"], r["s3"]]
            for k in range(3):
                if lv[k + 1] > lv[k]:
                    ax.add_patch(Rectangle((i - w, lv[k]), 2 * w, lv[k + 1] - lv[k], fc=BC[k], ec="none", zorder=2))
            if r["land"] > r["s3"] + 0.05:
                ax.add_patch(Rectangle((i - w, r["s3"]), 2 * w, r["land"] - r["s3"], fc="#ECEEF0", ec="none",
                                       hatch="//////", lw=0, zorder=1))
            if r["land"] < 99.95:
                ax.plot([i - 0.46, i + 0.46], [r["land"]] * 2, color=INK, lw=1.5, solid_capstyle="butt", zorder=3)
            if r["imp"] and r["imp"] > 0:
                ax.plot(i, min(r["imp"], 100), marker="v", ms=3.4, color=RED, mec="none", zorder=4, clip_on=False)
        ax.set_ylim(0, 100)
        ax.set_yticks([0, 50, 100])
        ax.set_yticklabels(["0", "50", "100"], fontsize=6.5)
        # the cost year in the left margin, upright beside the axis (no text over the bars)
        sa.text(0.047, (y1 + panel_mm / 2) / top_mm, f"{y} costs", rotation=90, ha="center", va="center",
                fontsize=7, fontweight="bold", color=INK)
        ax.tick_params(axis="y", length=2, pad=1.5)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        sa.text(0.004, (y1 + panel_mm) / top_mm, "abc"[j], fontsize=8, fontweight="bold", ha="left", va="top")
        if j < 2:
            ax.set_xticks([])
        else:
            ax.set_xticks(range(len(rows)))
            ax.set_xticklabels([SHORT.get(c, c) for c in rows], rotation=90, fontsize=col_font(ax, 1.0), color=INK)
            ax.tick_params(axis="x", length=0, pad=1.5)
    mark_groups(tuple(axes), axes[0], rows, grp, GLAB, count(rows, grp), pad_pt=4.5, fontsize=7.0, band_axes=())
    sa.text(0.022, (top_mm - leg_mm - grp_mm - (3 * panel_mm + 2 * gap_mm) / 2) / top_mm,
            "Share of fuel demand made at home (%)", rotation=90, ha="center", va="center", fontsize=7, color=INK)
    h = [Rectangle((0, 0), 1, 1, fc=BC[0]), Rectangle((0, 0), 1, 1, fc=BC[1]), Rectangle((0, 0), 1, 1, fc=BC[2]),
         Rectangle((0, 0), 1, 1, fc="#ECEEF0", hatch="//////"), Line2D([], [], color=INK, lw=1.5),
         Line2D([], [], color=RED, marker="v", ls="none", ms=3.8)]
    sa.legend(h, ["1% of GDP", "2% of GDP", "3% of GDP", "Unused land", "Land ceiling", "Imported share"],
              loc="upper center", ncol=6, fontsize=7.0, frameon=False, bbox_to_anchor=(0.53, 1.0), handlelength=1.3,
              columnspacing=1.4, borderaxespad=0.2)
    colors = {"imports covered": "#2E8B57", "budget binds": "#B3A6CC", "land binds": "#9A9A9A",
              "net exporter": "#DDB967"}
    for j, y in enumerate(years):
        cat = {c: C[c]["f5"][y]["grp"] for c in k139() if C.get(c, {}).get("f5", {}).get(y)}
        ax_m, _ = figmap.draw(sb, cat, colors, GLAB, rect=(0.005 + j * 0.332, 0.16, 0.325, 0.74), legend=False)
        ax_m.set_title(f"{y} costs", fontsize=7.0, fontweight="bold", pad=1.5)
    sb.legend(handles=[Patch(fc=colors[k], ec="none", label=GLAB[k]) for k in colors], loc="lower center", ncol=4,
              fontsize=7.0, frameon=False, bbox_to_anchor=(0.5, 0.0), handlelength=1.5, columnspacing=1.6,
              borderaxespad=0.2)
    sb.text(0.004, 1 - 1.2 / map_mm, "d", fontsize=8, fontweight="bold", ha="left", va="top")
    report(fig, Path(stem).name)
    out = Path(stem)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out.with_suffix(".pdf"))
    fig.savefig(out.with_suffix(".png"), dpi=300)
    plt.close(fig)
    print(f"saved {out}.(pdf|png): {top_mm:.0f} + {map_mm:.0f} mm")


def fig5_rows(stem, panel_mm=32.0):
    """2026-10-21: Fig. 5 with one row per cost year (a 2030, b 2040, c 2050): on the left the core 30 as stacked bars
    (1, 2, 3% of GDP, unused land, land ceiling, imported share), on the right the 139 economies of that year by
    binding constraint. 2026-10-22: each row grouped and ordered by its own year (classes change with costs), so
    every row carries its own group brackets and economy names."""
    from matplotlib.lines import Line2D
    from matplotlib.patches import Rectangle, Patch
    from lcof.figgroups import mark_groups, count, col_font
    from lcof.fig3_rows import SHORT
    mpl.rcParams.update({"hatch.color": "#7F8A95", "hatch.linewidth": 0.5})
    t = (R / "console/index.html").read_text(encoding="utf-8")
    D = json.JSONDecoder().raw_decode(t[t.index("const DATA=") + 11:])[0]
    C, core = D["countries"], core30()
    rows = [c for c in D["order"]["f5"]["2030"] if c in core]
    years = ("2030", "2040", "2050")
    BC, INK, RED = ["#0B4F9E", "#4A90D9", "#A8CCEC"], "#1A1A1A", "#CB181D"
    GLAB = {"imports covered": "Imports\ncovered", "budget binds": "Budget\nbinds", "land binds": "Land\nbinds",
            "net exporter": "Net\nexporters"}
    MLAB = {"imports covered": "Imports covered", "budget binds": "Budget binds", "land binds": "Land binds",
            "net exporter": "Net exporters"}
    colors = {"imports covered": "#2E8B57", "budget binds": "#B3A6CC", "land binds": "#9A9A9A",
              "net exporter": "#DDB967"}
    # 2026-10-22: one economy order for all rows (2030), names once under c; each row's classes as a strip of cells
    # above the bars, in the colours of the maps
    leg_mm, strip_mm, gap_mm, name_mm = 11.0, 3.0, 4.5, 19.0
    row_mm = strip_mm + 0.8 + panel_mm
    H = leg_mm + 3 * row_mm + 2 * gap_mm + name_mm
    rows = [c for c in D["order"]["f5"]["2030"] if c in core]
    fig = plt.figure(figsize=(183 * MM, H * MM))
    # 2026-10-21: each map exactly as tall as its bar panel (equal-aspect world map, 142 x 360 degrees), the bars
    # take the rest of the width
    mw = panel_mm * 360 / 142 / 183
    mx0 = 1 - mw - 0.002
    bx0 = 0.085
    bw_ = mx0 - 0.02 - bx0
    axes = []
    for j, y in enumerate(years):
        y1 = H - leg_mm - j * (row_mm + gap_mm) - row_mm
        ax = fig.add_axes([bx0, y1 / H, bw_, panel_mm / H])
        st = fig.add_axes([bx0, (y1 + panel_mm + 0.8) / H, bw_, strip_mm / H])
        st.set_xlim(-0.6, len(rows) - 0.4)
        st.set_ylim(0, 1)
        st.axis("off")
        for i, c in enumerate(rows):
            st.add_patch(Rectangle((i - 0.46, 0), 0.92, 1, fc=colors[C[c]["f5"][y]["grp"]], ec="none"))
        axes.append(ax)
        ax.set_xlim(-0.6, len(rows) - 0.4)
        w = 0.38
        for i, c in enumerate(rows):
            r = C[c]["f5"][y]
            lv = [0, r["s1"], r["s2"], r["s3"]]
            for k in range(3):
                if lv[k + 1] > lv[k]:
                    ax.add_patch(Rectangle((i - w, lv[k]), 2 * w, lv[k + 1] - lv[k], fc=BC[k], ec="none", zorder=2))
            if r["land"] > r["s3"] + 0.05:
                ax.add_patch(Rectangle((i - w, r["s3"]), 2 * w, r["land"] - r["s3"], fc="#ECEEF0", ec="none",
                                       hatch="//////", lw=0, zorder=1))
            if r["land"] < 99.95:
                ax.plot([i - 0.46, i + 0.46], [r["land"]] * 2, color=INK, lw=1.3, solid_capstyle="butt", zorder=3)
            if r["imp"] and r["imp"] > 0:
                ax.plot(i, min(r["imp"], 100), marker="v", ms=3.0, color=RED, mec="none", zorder=4, clip_on=False)
        ax.set_ylim(0, 100)
        ax.set_yticks([0, 50, 100])
        ax.set_yticklabels(["0", "50", "100"], fontsize=6.5)
        ax.tick_params(axis="y", length=2, pad=1.5)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        if j < 2:
            ax.set_xticks([])
        else:
            ax.set_xticks(range(len(rows)))
            ax.set_xticklabels([SHORT.get(c, c) for c in rows], rotation=90, fontsize=col_font(ax, 1.0), color=INK)
            ax.tick_params(axis="x", length=0, pad=1.5)
        # 2026-10-21: a short axis title per panel; the panel letter and the cost year side by side at the top left
        ax.set_ylabel("Fuel demand met\ndomestically (%)", fontsize=6.5, labelpad=2)
        fig.text(0.004, (y1 + row_mm) / H, "abc"[j], fontsize=8, fontweight="bold", ha="left", va="top")
        fig.text(0.022, (y1 + row_mm) / H, f"{y}", fontsize=7, fontweight="bold", ha="left", va="top", color=INK)
        # the map of the same cost year, centred on the row
        cat = {c: C[c]["f5"][y]["grp"] for c in k139() if C.get(c, {}).get("f5", {}).get(y)}
        figmap.draw(fig, cat, colors, MLAB, rect=(mx0, y1 / H, mw, panel_mm / H), legend=False)
    h = [Rectangle((0, 0), 1, 1, fc=BC[0]), Rectangle((0, 0), 1, 1, fc=BC[1]), Rectangle((0, 0), 1, 1, fc=BC[2]),
         Rectangle((0, 0), 1, 1, fc="#ECEEF0", hatch="//////"), Line2D([], [], color=INK, lw=1.3),
         Line2D([], [], color=RED, marker="v", ls="none", ms=3.6)]
    # 2026-10-21: the bar key over the bars, the map key over the maps
    fig.legend(h, ["1% of GDP", "2% of GDP", "3% of GDP", "Unused land", "Land ceiling", "Imported share"],
               loc="upper center", ncol=3, fontsize=7.0, frameon=False, bbox_to_anchor=(bx0 + bw_ / 2, 1.0),
               handlelength=1.3, columnspacing=1.4, borderaxespad=0.2)
    # 2026-10-22: the map key in the space under the 2050 map, level with the economy names under the bars
    fig.legend(handles=[Patch(fc=colors[k], ec="none", label=MLAB[k]) for k in colors], loc="upper center", ncol=2,
               fontsize=7.0, frameon=False, bbox_to_anchor=(mx0 + mw / 2, (name_mm - 3.0) / H), handlelength=1.3,
               columnspacing=1.6, borderaxespad=0.0)
    report(fig, Path(stem).name)
    out = Path(stem)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out.with_suffix(".pdf"))
    fig.savefig(out.with_suffix(".png"), dpi=300)
    plt.close(fig)
    print(f"saved {out}.(pdf|png): {H:.0f} mm")


def fig5_horizontal(stem, bars_mm=92.0, map_mm=19.5, years=("2030", "2040", "2050")):
    """2026-10-22: Fig. 5 with horizontal bars. Three columns, one per cost year (a 2030, b 2040, c 2050): the core 30
    as horizontal stacked bars (1, 2, 3% of GDP, unused land to the land ceiling, imported share), one economy order
    (2030) with the names once on the left; a cell at the left of each bar gives the economy's class that year in the
    colours of the maps; under each column the 139 economies of that year by binding constraint."""
    from matplotlib.lines import Line2D
    from matplotlib.patches import Rectangle, Patch
    from lcof.fig3_rows import SHORT
    mpl.rcParams.update({"hatch.color": "#7F8A95", "hatch.linewidth": 0.5})
    t = (R / "console/index.html").read_text(encoding="utf-8")
    D = json.JSONDecoder().raw_decode(t[t.index("const DATA=") + 11:])[0]
    C, core = D["countries"], core30()
    rows = [c for c in D["order"]["f5"]["2030"] if c in core]
    n = len(rows)
    # 2026-10-22 (co-author): years=("2030",) draws 2030 alone, bars across the page and the map under them at
    # the full page width (GDP after 2030 too speculative for the main figure; 2040 and 2050 stay in the SI)
    one = len(years) == 1
    BC, INK, RED = ["#0B4F9E", "#4A90D9", "#A8CCEC"], "#1A1A1A", "#CB181D"
    MLAB = {"imports covered": "Imports covered", "budget binds": "Budget binds", "land binds": "Land binds",
            "net exporter": "Net exporters"}
    colors = {"imports covered": "#2E8B57", "budget binds": "#B3A6CC", "land binds": "#9A9A9A",
              "net exporter": "#DDB967"}
    # 2026-10-22: both keys on top side by side; maps as wide as their bar columns, in the extent of Fig. 2
    x0, cgap = 0.150, 0.008
    colw = (0.982 - x0 - (len(years) - 1) * cgap) / len(years)   # right margin for the last "100" and edge markers
    if one:              # 2026-10-22 (user): room on the right for the group names written beside the bars
        colw = 0.845 - x0
    LAT = (-58, 84)                              # the extent of Fig. 2 (fig_sd_map), as Figs 3 and 4
    mx0, mw = (0.005, 0.99) if one else (None, colw)
    map_mm = mw * 183 * (LAT[1] - LAT[0]) / 360
    leg_mm, head_mm, axis_mm, gap_mm, mkey_mm = 11.0, 6.0, 9.0, 1.0, 5.5     # 2026-10-22: counts row under the maps
    if one:              # 2026-10-22 (user): bar key on top, groups named beside the bars, class key on the map
        leg_mm, mkey_mm = 6.0, 0.5
    H = leg_mm + head_mm + bars_mm + axis_mm + gap_mm + map_mm + mkey_mm
    fig = plt.figure(figsize=(183 * MM, H * MM))
    yb = H - leg_mm - head_mm - bars_mm
    for j, y in enumerate(years):
        xl = x0 + j * (colw + cgap)
        ax = fig.add_axes([xl, yb / H, colw, bars_mm / H])
        ax.set_ylim(n - 0.5, -0.5)
        ax.set_xlim(-1.0 if one else -9, 100)
        h = 0.36
        for i, c in enumerate(rows):
            r = C[c]["f5"][y]
            if not one:          # one year: the groups are named on the right instead of a coloured cell
                ax.add_patch(Rectangle((-8, i - 0.42), 6.5, 0.84, fc=colors[r["grp"]], ec="none", zorder=2))
            lv = [0, r["s1"], r["s2"], r["s3"]]
            for k in range(3):
                if lv[k + 1] > lv[k]:
                    ax.add_patch(Rectangle((lv[k], i - h), lv[k + 1] - lv[k], 2 * h, fc=BC[k], ec="none", zorder=2))
            if r["land"] > r["s3"] + 0.05:
                # 2026-10-22 (user): hatched, so it is not read as a class colour; the hatch takes its colour from
                # ec (lw 0, no outline): left to the rcParams it printed black in some rows and not at all in others
                ax.add_patch(Rectangle((r["s3"], i - h), r["land"] - r["s3"], 2 * h, fc="white", ec="#8C96A0",
                                       hatch="////", lw=0, zorder=1))
            if r["land"] < 99.95:
                ax.plot([r["land"]] * 2, [i - 0.46, i + 0.46], color=INK, lw=1.2, solid_capstyle="butt", zorder=3)
            if r["imp"] and r["imp"] > 0:
                ax.plot(min(r["imp"], 100), i, marker="<", ms=3.0, color=RED, mec="none", zorder=4, clip_on=False)
        if one:
            # each run of one group gets a bracket right of the bars and its name with the number of economies
            grp = [C[c]["f5"][y]["grp"] for c in rows]
            s = 0
            for e in range(1, n + 1):
                if e < n and grp[e] == grp[s]:
                    continue
                xb = 103.0
                ax.plot([xb, xb + 1.2, xb + 1.2, xb], [s - 0.35, s - 0.35, e - 1 + 0.35, e - 1 + 0.35], color=INK,
                        lw=0.6, clip_on=False)
                ax.text(xb + 2.6, (s + e - 1) / 2, f"{MLAB[grp[s]]}" + chr(10) + f"({e - s})", fontsize=7,
                        ha="left", va="center", color=INK, linespacing=1.1, clip_on=False)
                if e < n:            # a thin rule between the groups
                    ax.axhline(e - 0.5, xmin=0, xmax=1, color="#C8CDD2", lw=0.4, zorder=0.5)
                s = e
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.set_xticklabels(["0", "25", "50", "75", "100"], fontsize=7)
        ax.tick_params(axis="x", length=2, pad=1.5)
        ax.set_yticks(range(n))
        if j == 0:
            ax.set_yticklabels([SHORT.get(c, c) for c in rows], fontsize=7, color=INK)
        else:
            ax.set_yticklabels([])
        ax.tick_params(axis="y", length=0, pad=1.5)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_bounds(0, 100)
        if j == len(years) // 2:
            ax.set_xlabel("Fuel demand met domestically (%)", fontsize=7, labelpad=2)
        fig.text(0.004 if one else xl, (yb + bars_mm + 1.0) / H, "abc"[j], fontsize=8, fontweight="bold", ha="left", va="bottom")
        fig.text(xl + 0.02, (yb + bars_mm + 1.0) / H, f"{y} costs" if one else f"{y}", fontsize=7, fontweight="bold", ha="left",
                 va="bottom", color=INK)
        # the map of the same year under the column, as wide as the column
        cat = {c: C[c]["f5"][y]["grp"] for c in k139() if C.get(c, {}).get("f5", {}).get(y)}
        mxl = mx0 if one else xl
        figmap.draw(fig, cat, colors, MLAB, rect=(mxl, mkey_mm / H, mw, map_mm / H), legend=one, ylim=LAT)
        if one:
            fig.text(0.004, (mkey_mm + map_mm) / H, "b", fontsize=8, fontweight="bold", ha="left", va="top")
        # 2026-10-22 (user: the maps carry no numbers): under each map, the number of economies in each class
        cnt = pd.Series(cat).value_counts()
        yk = 1.6 / H
        # 2026-10-22 (user): spread evenly across the map's width, the number clear of its square
        for q, k in enumerate(colors if not one else ()):
            xq = mxl + (q + 0.5) * mw / 4 - 3.0 / 183
            fig.patches.append(Rectangle((xq, yk), 2.2 / 183, 2.2 / H, transform=fig.transFigure, fc=colors[k],
                                         ec="none"))
            fig.text(xq + 3.4 / 183, yk + 1.1 / H, f"{int(cnt.get(k, 0))}", fontsize=6, ha="left", va="center",
                     color=INK)
    hb = [Rectangle((0, 0), 1, 1, fc=BC[0]), Rectangle((0, 0), 1, 1, fc=BC[1]), Rectangle((0, 0), 1, 1, fc=BC[2]),
          Rectangle((0, 0), 1, 1, fc="white", ec="#8C96A0", hatch="////", lw=0), Line2D([], [], color=INK, lw=1.2),
          Line2D([], [], color=RED, marker="<", ls="none", ms=3.6)]
    # 2026-10-22: two key rows on top, centred on the panels: the bars, then the maps (and the class cells)
    xc = x0 + (len(years) * colw + (len(years) - 1) * cgap) / 2
    fig.legend(hb, ["1% of GDP", "2% of GDP", "3% of GDP", "Unused land", "Land ceiling", "Imported share"],
               loc="upper center", ncol=6, fontsize=7.0, frameon=False, bbox_to_anchor=(xc, 1.0),
               handlelength=1.3, columnspacing=1.4, borderaxespad=0.2)
    if not one:          # one year: the class key with its counts is drawn on the map (figmap.draw)
        fig.legend(handles=[Patch(fc=colors[k], ec="none", label=MLAB[k]) for k in colors], loc="upper center",
                   ncol=4, fontsize=7.0, frameon=False, bbox_to_anchor=(xc, 1 - 5.0 / H), handlelength=1.3,
                   columnspacing=1.6, borderaxespad=0.2)
    report(fig, Path(stem).name)
    out = Path(stem)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out.with_suffix(".pdf"))
    fig.savefig(out.with_suffix(".png"), dpi=300)
    plt.close(fig)
    print(f"saved {out}.(pdf|png): {H:.0f} mm")


def fuel_classes(fuel):
    """Fig. 3b classes for any fuel: domestic cost (lowest-cost cell, median weather year) against the economy's own
    disruption-period comparator price"""
    pk = {"ammonia": "amm", "e-diesel": "ft", "e-methane": "em", "methanol": "meoh", "ethanol": "eth",
          "hydrogen": "h2"}[fuel]
    C, cat = _data(), {}
    for c in k139():
        d = C.get(c, {})
        pr, bx = d.get("pr", {}).get(pk), d.get("box", {}).get(fuel)
        e = d.get("E_amm") if pk == "amm" else d.get("E_ft") if pk == "ft" else d.get("Ech", {}).get(fuel)
        if not pr or not bx:
            continue
        m = bx[2]
        cat[c] = "x" if (e is None or e <= 0) else ("med" if m <= pr["d"][2] else ("p90" if m <= pr["d"][4] else "above"))
    return cat


def si_fuel_maps(stem):
    """2026-10-22: SI, one map per fuel (e-diesel and e-jet fuel, e-methane, methanol, ethanol, hydrogen), 139
    economies classed as Fig. 3b: domestic fuel below the median, between the median and the 90th percentile, or
    above the 90th percentile of the disruption-period price, or net exporter of the chain."""
    from matplotlib.patches import Patch
    _, colors, labels, _ = fig3_classes()
    fuels = [("e-diesel", "E-diesel and e-jet fuel"), ("e-methane", "E-methane"), ("methanol", "Methanol"),
             ("ethanol", "Ethanol"), ("hydrogen", "Hydrogen")]
    mw = 0.49
    mh_mm = mw * 183 * 142 / 360
    row_mm = mh_mm + 6.0
    H = 3 * row_mm + 1.0
    fig = plt.figure(figsize=(183 * MM, H * MM))
    for k, (f, title) in enumerate(fuels):
        r, ccol = divmod(k, 2)
        x = 0.005 + ccol * 0.505
        yb = H - 1.0 - (r + 1) * row_mm
        ax, _ = figmap.draw(fig, fuel_classes(f), colors, labels, rect=(x, yb / H, mw, mh_mm / H), legend=False)
        fig.text(x, (yb + mh_mm + 1.0) / H, "abcde"[k], fontsize=8, fontweight="bold", ha="left", va="bottom")
        fig.text(x + 0.02, (yb + mh_mm + 1.0) / H, title, fontsize=7, fontweight="bold", ha="left", va="bottom")
    # the key in the free sixth slot, lower right
    fig.legend(handles=[Patch(fc=colors[k], ec="none", label=labels[k]) for k in colors], loc="center",
               fontsize=7.0, frameon=False, bbox_to_anchor=(0.005 + 0.505 + mw / 2, (row_mm / 2) / H),
               handlelength=1.5, labelspacing=0.6, borderaxespad=0.2,
               title="Domestic fuel against the disruption-period price", title_fontsize=7.0)
    report(fig, Path(stem).name)
    out = Path(stem)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out.with_suffix(".pdf"))
    fig.savefig(out.with_suffix(".png"), dpi=300)
    plt.close(fig)
    print(f"saved {out}.(pdf|png): {H:.0f} mm")


def si_fig3_core(stem, fuel="e-diesel", height_mm=130.0):
    """SI: the Fig. 3a panel for another fuel, core 30"""
    fig = plt.figure(figsize=(183 * MM, height_mm * MM))
    fig3_cols.main(stem, fuel, height_mm, fig=fig, subset=core30())
    report(fig, Path(stem).name)
    out = Path(stem)
    fig.savefig(out.with_suffix(".pdf"))
    fig.savefig(out.with_suffix(".png"), dpi=300)
    plt.close(fig)
    print(f"saved {out}.(pdf|png)")


def main(which, stem, a_mm=None, b_mm=72.0):
    if which == "simaps":
        return si_fuel_maps(stem)
    if which == "si3ft":
        return si_fig3_core(stem)
    if which == "fig5h":
        return fig5_horizontal(stem)
    if which == "fig6":            # 2026-10-22: the budget figure, 2030 only (now Fig. 6)
        return fig5_horizontal(stem, bars_mm=a_mm or 92.0, years=("2030",))
    if which == "fig5r":
        return fig5_rows(stem)
    if which == "fig5p":
        return fig5_panels(stem)
    if which == "fig5y":
        return fig5_years(stem, *( [a_mm] if a_mm else []))
    a_mm = a_mm or (100.0 if which == "fig3" else 80.0)
    fig = plt.figure(figsize=(183 * MM, (a_mm + b_mm) * MM))
    sa, sb = fig.subfigures(2, 1, height_ratios=[a_mm, b_mm], hspace=0)
    if which == "fig3":
        fig3_cols.main(stem, "ammonia", a_mm, fig=sa, subset=core30())
        cat, colors, labels, title = fig3_classes()
    else:
        fig5_cols.main(stem, "2030", a_mm, fig=sa, subset=core30())
        cat, colors, labels, title = fig5_classes()
    figmap.draw(sb, cat, colors, labels, title)
    for s, letter, mm in ((sa, "a", a_mm), (sb, "b", b_mm)):
        s.text(0.004, 1 - 1.2 / mm, letter, fontsize=8, fontweight="bold", ha="left", va="top")
    report(fig, Path(stem).name)
    out = Path(stem)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out.with_suffix(".pdf"))
    fig.savefig(out.with_suffix(".png"), dpi=300)
    plt.close(fig)
    print(f"saved {out}.(pdf|png): {a_mm} + {b_mm} mm; map classes {pd.Series(cat).value_counts().to_dict()}")


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], *[float(x) for x in a[2:]])
