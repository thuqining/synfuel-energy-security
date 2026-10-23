"""
fig_rows139.py — the 139-economy SI versions of Figs 3, 4a and 6 with one economy per row (2026-10-22: no
upright economy names), in two blocks side by side on one page. Names and the numbers beside them read level;
groups open with a bold heading row; the 30 core economies are in bold. Marks and colours as the main figures
(fig3_cols, fig4a_cols, fig35_core.fig5_horizontal). Data: console/index.html and console/build (as those).

From scripts/:  python -m lcof.fig_rows139 <out stem> fig3 <fuel>   |   fig4a   |   fig6 <year>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.lines as ml
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.legend_handler import HandlerBase
from matplotlib.patches import Rectangle

from lcof.fig3_rows import SHORT, MM

R = Path(__file__).resolve().parents[2]
INK, RULE = "#1A1A1A", "#C8CDD2"
NAME_PT, NUM_PT, TXT_PT = 6.0, 6.0, 7.0      # economy names and row numbers; headings, ticks and keys


def _rc():
    mpl.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"],
                         "font.size": TXT_PT, "axes.linewidth": 0.5, "xtick.major.width": 0.5,
                         "xtick.labelsize": TXT_PT, "pdf.fonttype": 42, "hatch.linewidth": 0.5})


def _core():
    import pandas as pd
    return set(pd.read_csv(R / "work/caselow/2030/data/fig5a_chain.csv", index_col=0).index)


def _slots(rows, group_of, label_of):
    """rows in order -> [('h', heading) | ('r', economy)], a heading before each group, then cut into two blocks of
    near-equal length; a block that starts inside a group repeats its heading with '(continued)'"""
    from collections import Counter
    n = Counter(group_of(c) for c in rows)
    s, prev = [], None
    for c in rows:
        if group_of(c) != prev:
            prev = group_of(c)
            s.append(("h", f"{label_of(prev)} ({n[prev]})"))
        s.append(("r", c))
    half = int(np.ceil(len(s) / 2))
    a, b = s[:half], s[half:]
    if b and b[0][0] == "r":
        head = [x for x in a if x[0] == "h"][-1][1]
        b = [("h", head.split(" (")[0] + " (continued)")] + b
    if a and a[-1][0] == "h":                      # no heading alone at the foot of a block
        b, a = [a[-1]] + b, a[:-1]
    return [a, b]


def _page(height_mm, nslots, ncols_mm, key_mm=13.0, axis_mm=12.0):
    """figure and, per block, the plot axes; name and number columns sit left of each plot (ncols_mm wide)"""
    fig = plt.figure(figsize=(183 * MM, height_mm * MM))
    name_mm, gap_mm, edge_mm = 21.0, 5.0, 1.0
    right_mm = 3.5                          # 2026-10-22: room for the half of the last tick label
    blk_mm = (183 - edge_mm - right_mm - gap_mm) / 2
    plot_mm = blk_mm - name_mm - ncols_mm
    y0, h = axis_mm / height_mm, (height_mm - key_mm - axis_mm) / height_mm
    axes = []
    for k in range(2):
        x = (edge_mm + k * (blk_mm + gap_mm) + name_mm + ncols_mm) / 183
        ax = fig.add_axes([x, y0, plot_mm / 183, h])
        ax.set_ylim(nslots - 0.5, -0.9)       # 2026-10-22: room between the top axis line and the first row
        axes.append(ax)
    return fig, axes, name_mm, ncols_mm, plot_mm


def _rows(ax, blk, core, name_of, col_x, ncols_mm, plot_mm):
    """names (bold for the core 30) and headings for one block; returns {economy: slot}"""
    tr = ax.get_yaxis_transform()
    fx = lambda mm: -(mm) / plot_mm          # millimetres left of the plot, in axes fraction
    pos = {}
    for i, (kind, v) in enumerate(blk):
        if kind == "h":
            ax.text(fx(ncols_mm + 20.5), i, v, transform=tr, ha="left", va="center", fontsize=TXT_PT,
                    fontweight="bold", color=INK, clip_on=False, zorder=8,
                    bbox=dict(fc="white", ec="none", pad=0.4))     # a long heading may reach over the plot
            if i:
                ax.plot([fx(ncols_mm + 20.5), 1.0], [i - 0.5, i - 0.5], transform=tr, color=RULE, lw=0.4,
                        clip_on=False, zorder=0.5)
        else:
            pos[v] = i
            ax.text(fx(ncols_mm + 0.8), i, name_of(v), transform=tr, ha="right", va="center", fontsize=NAME_PT,
                    fontweight="bold" if v in core else "normal", color=INK, clip_on=False)
    return pos, fx


def _finish(fig, axes, stem, xlabel):
    for ax in axes:
        ax.set_yticks([])
        for sp in ("left", "right"):
            ax.spines[sp].set_visible(False)
        ax.tick_params(axis="x", length=2, pad=1.5, top=True, labeltop=False)   # numbers under the rows only
        ax.set_xlabel(xlabel, fontsize=TXT_PT, labelpad=2)
    from lcof.figcheck import report
    report(fig, Path(stem).name)
    out = Path(stem)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out.with_suffix(".pdf"))
    fig.savefig(out.with_suffix(".png"), dpi=300)
    plt.close(fig)


# ---------------------------------------------------------------- Fig. 3 for every fuel
def fig3(stem, fuel="ammonia", height_mm=213.0):
    from lcof import fig3_cols as F
    import pandas as pd
    _rc()
    C, pk, rows, E = F.data(fuel)
    core = _core()
    grp = lambda c: "x" if (E(c) is None or E(c) <= 0) else ("full" if E(c) >= 0.995 else "part")
    if pk in ("amm", "ft"):
        own = pd.read_csv(R / "console/build" / f"fig3_prices_{'ammonia' if pk == 'amm' else 'ft'}.csv",
                          index_col=0).own_share
        observed = lambda c: bool(own.get(c, 0) > 0)
    else:
        observed = lambda c: C[c]["pr"][pk].get("obs")
    blocks = _slots(rows, grp, F.LAB.get)
    ns = max(len(b) for b in blocks)
    fig, axes, name_mm, ncols_mm, plot_mm = _page(height_mm, ns, 16.0)
    # 2026-10-22: the axis spans every mark of the fuel (10th-90th percentiles), on round values of the log scale
    vals = [v for c in rows for v in (C[c]["pr"][pk]["n"][0], C[c]["pr"][pk]["d"][0], C[c]["box"][fuel][0],
                                      C[c]["pr"][pk]["n"][4], C[c]["pr"][pk]["d"][4], C[c]["box"][fuel][4])
            if v is not None and np.isfinite(v) and v > 0]
    lo = max(v for v in (1.0, 1.25, 1.6, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0) if v <= 0.92 * min(vals))
    hi = min(v for v in (160.0, 200.0, 250.0, 320.0, 400.0) if v >= 1.08 * max(vals))
    bill = fuel != "hydrogen"               # hydrogen is not a final fuel: no bill (as SI Fig. sitesh2)
    for ax, blk in zip(axes, blocks):
        pos, fx = _rows(ax, blk, core, lambda c: SHORT.get(c, c) + ("" if observed(c) else "*"), None, ncols_mm,
                        plot_mm)
        tr = ax.get_yaxis_transform()
        for c, i in pos.items():
            pr, bx = C[c]["pr"][pk], C[c]["box"][fuel]
            n10, _, nm, _, n90 = pr["n"]
            ax.add_patch(Rectangle((n10, i - 0.34), n90 - n10, 0.68, fc=F.GREY_P, alpha=0.6, ec="none", zorder=2))
            ax.plot([nm, nm], [i - 0.34, i + 0.34], color="white", lw=1.0, zorder=3, solid_capstyle="butt")
            ax.plot([bx[0], bx[4]], [i, i], color=F.BEST, lw=0.7, zorder=4)
            ax.add_patch(Rectangle((bx[1], i - 0.22), max(bx[3] - bx[1], bx[2] * 0.015), 0.44, fc=F.BEST,
                                   alpha=0.85, ec="none", zorder=5))
            d10, _, dm, _, d90 = pr["d"]
            ax.plot([d10, d90], [i, i], color=F.CRIS, lw=0.8, zorder=7, solid_capstyle="butt")
            for x in (d10, d90):
                ax.plot([x, x], [i - 0.24, i + 0.24], color=F.CRIS, lw=0.8, zorder=7)
            ax.plot([dm], [i], marker="D", ms=2.6, mfc=F.CRIS, mec="white", mew=0.4, zorder=8)
            e = E(c)
            if e is not None:                # import share: shaded cell with its number, then the bill
                ax.add_patch(Rectangle((fx(ncols_mm - 0.3), i - 0.42), 5.4 / plot_mm, 0.84, transform=tr,
                                       fc=mpl.colormaps["Reds"](0.08 + 0.82 * e), ec="none", clip_on=False))
                ax.text(fx(ncols_mm - 3.0), i, f"{100 * e:.0f}", transform=tr, ha="center", va="center",
                        fontsize=NUM_PT, color="white" if e > 0.5 else INK, clip_on=False)
            pm = pr.get("pm")
            if bill and pm is not None and np.isfinite(pm):
                ax.text(fx(4.5), i, "0" if pm == 0 else (f"{pm:.1f}" if pm >= 0.05 else "<0.1"), transform=tr,
                        ha="center", va="center", fontsize=NUM_PT, color=INK, clip_on=False)
        ax.text(fx(ncols_mm - 3.0), -1.1, "Import" + chr(10) + "(%)", transform=tr, ha="center",
                va="bottom", fontsize=NUM_PT, color=INK, clip_on=False, linespacing=1.0)
        if bill:
            ax.text(fx(4.5), -1.1, "Bill" + chr(10) + "(‰ GDP)", transform=tr, ha="center", va="bottom",
                    fontsize=NUM_PT, color=INK, clip_on=False, linespacing=1.0)
        ax.set_xscale("log")
        ax.set_xlim(lo, hi)
        xt = [v for v in (1.25, 2.5, 5, 10, 20, 40, 80, 160, 320) if lo <= v <= hi]
        ax.set_xticks(xt)
        ax.set_xticks([], minor=True)
        ax.set_xticklabels([f"{v:g}" for v in xt])
        ax.grid(axis="x", color="#E6E6E6", lw=0.4, zorder=0)
    syn, fos = F.KEYS[fuel]
    _keys3(fig, syn, fos)
    _finish(fig, axes, stem, "US\\$ per MMBtu")
    print(f"saved {stem}: {fuel}, {len(rows)} economies, {ns} rows a block")


def _keys3(fig, syn, fos):
    from lcof.fig3_cols import BEST, GREY_P, CRIS

    class _Box(HandlerBase):
        def create_artists(self, legend, orig, x0, y0, w, h, fs_, trans):
            yc = y0 + h / 2
            return [ml.Line2D([x0, x0 + w], [yc, yc], color=BEST, lw=0.7, transform=trans),
                    Rectangle((x0 + 0.28 * w, yc - 0.3 * h), 0.44 * w, 0.6 * h, fc=BEST, alpha=0.85, lw=0,
                              transform=trans)]

    class _Band(HandlerBase):
        def create_artists(self, legend, orig, x0, y0, w, h, fs_, trans):
            yc = y0 + h / 2
            return [Rectangle((x0, yc - 0.32 * h), w, 0.64 * h, fc=GREY_P, alpha=0.6, lw=0, transform=trans),
                    ml.Line2D([x0 + w / 2] * 2, [yc - 0.32 * h, yc + 0.32 * h], color="white", lw=1.2,
                              transform=trans)]

    class _Cap(HandlerBase):
        def create_artists(self, legend, orig, x0, y0, w, h, fs_, trans):
            yc = y0 + h / 2
            out = [ml.Line2D([x0, x0 + w], [yc, yc], color=CRIS, lw=0.9, transform=trans)]
            out += [ml.Line2D([x, x], [yc - 0.28 * h, yc + 0.28 * h], color=CRIS, lw=0.9, transform=trans)
                    for x in (x0, x0 + w)]
            out.append(ml.Line2D([x0 + w / 2], [yc], marker="D", ms=3.0, mfc=CRIS, mec="white", mew=0.4, ls="none",
                                 transform=trans))
            return out
    kn, kc, kb = object(), object(), object()
    fig.legend([kn, kc, kb], [fos + " (normal)", fos + " (disruption)", syn],
               handler_map={kn: _Band(), kc: _Cap(), kb: _Box()}, loc="upper center", ncol=3, fontsize=TXT_PT,
               frameon=False, bbox_to_anchor=(0.5, 1.0), handlelength=2.4, columnspacing=2.2, borderaxespad=0.2)


# ---------------------------------------------------------------- Fig. 6 (budget) at one cost year
def fig6(stem, year="2030", height_mm=213.0):
    _rc()
    t = (R / "console/index.html").read_text(encoding="utf-8")
    D = json.JSONDecoder().raw_decode(t[t.index("const DATA=") + 11:])[0]
    C, rows = D["countries"], D["order"]["f5"][year]
    core = _core()
    MLAB = {"imports covered": "Imports covered", "budget binds": "Budget binds", "land binds": "Land binds",
            "net exporter": "Net exporters"}
    BC, RED = ["#0B4F9E", "#4A90D9", "#A8CCEC"], "#CB181D"
    grp = lambda c: C[c]["f5"][year]["grp"]
    blocks = _slots(rows, grp, MLAB.get)
    ns = max(len(b) for b in blocks)
    fig, axes, name_mm, ncols_mm, plot_mm = _page(height_mm, ns, 0.0)
    h = 0.34
    for ax, blk in zip(axes, blocks):
        pos, _ = _rows(ax, blk, core, lambda c: SHORT.get(c, c), None, 0.0, plot_mm)
        for c, i in pos.items():
            r = C[c]["f5"][year]
            lv = [0, r["s1"], r["s2"], r["s3"]]
            for k in range(3):
                if lv[k + 1] > lv[k]:
                    ax.add_patch(Rectangle((lv[k], i - h), lv[k + 1] - lv[k], 2 * h, fc=BC[k], ec="none", zorder=2))
            if r["land"] > r["s3"] + 0.05:
                ax.add_patch(Rectangle((r["s3"], i - h), r["land"] - r["s3"], 2 * h, fc="white", ec="#8C96A0",
                                       hatch="////", lw=0, zorder=1))
            if r["land"] < 99.95:
                ax.plot([r["land"]] * 2, [i - 0.44, i + 0.44], color=INK, lw=1.0, solid_capstyle="butt", zorder=3)
            if r["imp"] and r["imp"] > 0:
                ax.plot(min(r["imp"], 100), i, marker="<", ms=2.6, color=RED, mec="none", zorder=4, clip_on=False)
        ax.set_xlim(-2.5, 102.5)             # markers at 0 and 100% clear of the axis ends
        for sp in ("bottom", "top"):
            ax.spines[sp].set_bounds(0, 100)
        ax.set_xticks([0, 25, 50, 75, 100])
    hb = [Rectangle((0, 0), 1, 1, fc=BC[0]), Rectangle((0, 0), 1, 1, fc=BC[1]), Rectangle((0, 0), 1, 1, fc=BC[2]),
          Rectangle((0, 0), 1, 1, fc="white", ec="#8C96A0", hatch="////", lw=0), ml.Line2D([], [], color=INK, lw=1.2),
          ml.Line2D([], [], color=RED, marker="<", ls="none", ms=3.4)]
    fig.legend(hb, ["1% of GDP", "2% of GDP", "3% of GDP", "Unused land", "Land ceiling", "Imported share"],
               loc="upper center", ncol=6, fontsize=TXT_PT, frameon=False, bbox_to_anchor=(0.5, 1.0),
               handlelength=1.3, columnspacing=1.4, borderaxespad=0.2)
    _finish(fig, axes, stem, f"Fuel demand met domestically at {year} costs (%)")
    print(f"saved {stem}: {year}, {len(rows)} economies, {ns} rows a block")


# ---------------------------------------------------------------- Fig. 4a for every economy
def fig4a(stem, height_mm=213.0):
    from lcof import fig4a_cols as A
    from lcof.fig4a_all import load, fwd, YEARS, MAG
    _rc()
    data, imps, exps, first = load()
    d50 = data[2050]
    gap50 = {c: float(d50.net_usd_t[c] - d50.p_co2_usd_t[c]) for c in imps if c in d50.index}
    imps = [c for c in imps if first.get(c) != 9999] + \
        sorted([c for c in imps if first.get(c) == 9999], key=lambda c: gap50.get(c, 1e9))
    rows = imps + exps
    grp = lambda c: first.get(c, "x")
    core = _core()
    blocks = _slots(rows, grp, A.LAB.get)
    ns = max(len(b) for b in blocks)
    fig, axes, name_mm, ncols_mm, plot_mm = _page(height_mm, ns, 15.0)
    d30 = data[2030]
    fmt = lambda v: f"{v:,.0f}".replace("-", "−")
    off = {2030: -0.27, 2040: 0.0, 2050: 0.27}
    ylo, yhi, FLOOR = -1050.0, 1200.0, -820.0
    for ax, blk in zip(axes, blocks):
        pos, fx = _rows(ax, blk, core, lambda c: SHORT.get(c, c), None, ncols_mm, plot_mm)
        tr = ax.get_yaxis_transform()
        ax.axvspan(float(fwd(ylo)), 0.0, color=A.ZERO_C, lw=0, zorder=0.2)
        for c, i in pos.items():
            if c in d30.index and np.isfinite(d30.net_usd_t[c]):
                ax.text(fx(ncols_mm - 6.3), i, fmt(float(d30.gross_usd_t[c] - d30.net_usd_t[c])), transform=tr,
                        ha="right", va="center", fontsize=NUM_PT, color=A.RING_C, clip_on=False)
                ax.text(fx(0.9), i, fmt(float(d30.net_usd_t[c])), transform=tr, ha="right", va="center",
                        fontsize=NUM_PT, color=A.YC[2030], clip_on=False)
            pc = float(fwd(float(d30.p_co2_usd_t[c])))
            ax.plot([pc, pc], [i - 0.42, i + 0.42], color=MAG, lw=0.9, zorder=2)
            for y in YEARS:
                d = data[y]
                if c not in d.index or not np.isfinite(d.net_usd_t[c]):
                    continue
                yy = i + off[y]
                g = float(fwd(np.clip(d.gross_usd_t[c], FLOOR, yhi)))
                nt = float(d.net_usd_t[c])
                nv = float(fwd(np.clip(nt, FLOOR, yhi)))
                ax.plot([g, nv], [yy, yy], color=A.MARGIN_C, lw=0.7, zorder=3, solid_capstyle="butt")
                ax.scatter([g], [yy], s=3.5, marker=A.MK[y], facecolor="white", edgecolor=A.YC[y], linewidths=0.45,
                           zorder=4)
                ax.scatter([nv], [yy], s=3.5, marker=A.MK[y], color=A.YC[y], lw=0, zorder=5)
                if c in imps and nt <= float(d.p_co2_usd_t[c]):
                    ax.scatter([nv], [yy], s=9, marker="o", facecolor="none", edgecolor=A.RING_C, linewidths=0.6,
                               zorder=6)
        ax.text(fx(ncols_mm - 6.3), -1.1, "Margin" + chr(10) + "2030", transform=tr, ha="right", va="bottom",
                fontsize=NUM_PT, color=A.RING_C, clip_on=False, linespacing=1.0)
        ax.text(fx(0.9), -1.1, "Net" + chr(10) + "2030", transform=tr, ha="right", va="bottom", fontsize=NUM_PT,
                color=A.YC[2030], clip_on=False, linespacing=1.0)
        ticks = [-200, 0, 500, 1000]         # (below -200 the axis is compressed; the band marks net < 0)
        ax.set_xlim(float(fwd(ylo)), float(fwd(yhi)))
        ax.set_xticks([float(fwd(v)) for v in ticks])
        ax.set_xticklabels([fmt(v) for v in ticks])
        for b in (-200.0, 1000.0):
            ax.axvline(float(fwd(b)), color="#CCCCCC", lw=0.4, ls=(0, (2, 2)), zorder=1)
    h = [ml.Line2D([], [], ls="none", marker=A.MK[y], ms=3.2, color=A.YC[y], label=f"{y}") for y in YEARS]
    h += [ml.Line2D([], [], ls="none", marker="o", ms=2.6, mfc="white", mec=INK, mew=0.5, label="Cost premium"),
          ml.Line2D([], [], ls="none", marker="o", ms=2.6, color=INK, label="Net premium"),
          ml.Line2D([], [], color=A.MARGIN_C, lw=1.1, label="Security margin"),
          ml.Line2D([], [], ls="none", marker="o", ms=4.2, mfc="none", mec=A.RING_C, mew=0.8, label="Justified"),
          ml.Line2D([], [], color=MAG, lw=1.0, label="Carbon price")]
    fig.legend(handles=h, loc="upper center", ncol=8, fontsize=TXT_PT, frameon=False, bbox_to_anchor=(0.5, 1.0),
               handlelength=1.2, columnspacing=1.0, handletextpad=0.4, borderaxespad=0.2)
    _finish(fig, axes, stem, "Abatement cost (US\\$ tCO$_2^{-1}$)")
    print(f"saved {stem}: {len(rows)} economies, {ns} rows a block")


if __name__ == "__main__":
    a = sys.argv[1:]
    {"fig3": lambda: fig3(a[0], *a[2:3]), "fig4a": lambda: fig4a(a[0]), "fig6": lambda: fig6(a[0], *a[2:3])}[a[1]]()
