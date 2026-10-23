"""
fig4_years.py — Figure 4 at three build years (2026-10-07):
columns 2030 / 2040 / 2050, row a = the 1%-of-GDP security portfolio per tonne
(draw_a_circles, one row order across the columns, set by 2030), row b = the
abatement-cost curve cut at zero (fig5_chain._curve_to_zero).

Each build year is its own sandbox of the lowest-cost case (lcof.case_low), whose
LCOF already sits at that year's costs, so the decline path g_f(t) is one here.
Demand, fossil comparators, the event record and carbon prices are today's.

From scripts/:  python -m lcof.fig4_years <workdir_2030> <workdir_2040> <workdir_2050> <out_stem>
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

mpl.use("Agg")

from . import inputs
from . import case_low as C
from . import fig5_chain as F5
from .fig_main_cost import MM, NAT_RC
from .global_trajectory import REGION_COL
from .fig5a_chain import draw_a_circles

mpl.rcParams.update(NAT_RC)
YEARS = (2025, 2030, 2040, 2050)          # any subset can be drawn; row order is set by the first
# row b shares one cost axis, one compression and one set of ticks across the build years
YLO_B, SQZ_B, XT_B = -600.0, 2.0, [0, 1, 2, 3, 4, 5]
for _y in YEARS:
    F5._YLO[_y], F5._SQZ[_y], F5._XT[_y] = YLO_B, SQZ_B, XT_B
INKC, SECC, MAG, SHADE = "#0B4F9E", "#1B7A4B", "#B4116F", "#E3F2EA"


def year_data(year: int, work: str):
    inputs.MAPS = Path(work) / "data"
    C.apply_params(year)
    d = pd.read_csv(inputs.MAPS / "fig5a_chain.csv", index_col=0)
    F5._decline = lambda fuels: {f: np.ones(len(F5.VY)) for f in fuels}   # costs already at `year`
    p, tj, _ = F5.panel_b_data(write=False)
    p = p.drop(columns=["pi_2050", "pi_rest_2050"]).rename(
        columns={"pi_2025": f"pi_{year}", "pi_rest_2025": f"pi_rest_{year}"})
    return d, p, tj


def _nice(x, step):
    return float(np.floor(x / step) * step) if x < 0 else float(np.ceil(x / step) * step)


def _b_tranches(p, yr):
    """the tranches of panel b (as fig5_chain._curve_to_zero builds them): width in Gt and
    cost in US$ per tonne"""
    pi, pr = p[f"pi_{yr}"].to_numpy(), p[f"pi_rest_{yr}"].to_numpy()
    w = np.clip(p.w_usd_gj.to_numpy(), 0, None)
    ef, imp = p.ef.to_numpy(), p.imp_gj.to_numpy()
    return pd.DataFrame({"wd": np.r_[imp * ef, (p.dem_gj.to_numpy() - imp) * ef] / 1e9,
                         "c": np.r_[(pi - w) / ef, pr / ef]}).query("wd > 0")


def shared_ranges(data):
    """2026-10-08: axes follow the data, one range per row across the columns.
    Row a: from the lowest net cost to the highest premium, 6 % padding, round hundreds.
    Row b: width to the end of the US$300/t window; floor at the cost above which 99 % of
    the paying demand lies (thin slivers below are cut and reported, as before)."""
    a_vals = pd.concat([pd.concat([d.net_usd_t, d.gross_usd_t]) for d, _, _ in data.values()])
    span = float(a_vals.max() - a_vals.min())
    xa = (min(_nice(float(a_vals.min()) - 0.06 * span, 100), -100.0), _nice(float(a_vals.max()) + 0.06 * span, 100))
    xb, yb = 0.0, 0.0
    for y, (_, p, _) in data.items():
        tr = _b_tranches(p, y)
        xb = max(xb, float(tr.wd[tr.c <= F5._CAP].sum()))
        neg = tr[tr.c <= 0].sort_values("c")
        if len(neg):
            cum = neg.wd.cumsum() / neg.wd.sum()
            yb = min(yb, float(neg.c[cum >= 0.01].iloc[0]))   # 2026-10-13: 1st percentile
    yb = min(_nice(1.1 * yb, 100), -100.0)
    xb = xb * 1.02
    step = next(s for s in (0.25, 0.5, 1.0, 2.0) if xb / s <= 6)
    return xa, (xb, yb, list(np.arange(0, xb + 1e-9, step)))


PAY_SHARE = 0.72     # share of the panel-b width given to the demand that pays off
                     # (2026-10-14: 0.75 -> 0.72, so 'Costlier with security value' clears the dashed line)


def b_axes(p, yr):
    """2026-10-08: each panel b on its own range, the axis mainly showing the demand
    that pays off. x runs to the panel's own end of the US$300/t window; right of the dashed
    line (the security-paying edge zs) the axis is compressed so that 0..zs takes PAY_SHARE of
    the width; the floor is the cost above which 99 % of the paying demand lies.
    Returns xmax, ylo, compression k, ticks."""
    tr = _b_tranches(p, yr)
    xmax = float(tr.wd[tr.c <= F5._CAP].sum())
    neg = tr[tr.c <= 0].sort_values("c")
    zs = float(neg.wd.sum())
    cum = neg.wd.cumsum() / zs
    ylo = min(_nice(1.1 * float(neg.c[cum >= 0.01].iloc[0]), 100), -100.0)   # 2026-10-13: 1st percentile
    k = max(1.0, PAY_SHARE / (1 - PAY_SHARE) * (xmax - zs) / zs)
    s1 = next(s for s in (0.05, 0.1, 0.2, 0.25, 0.5, 1.0) if zs / s <= 4)
    s2 = next(s for s in (0.5, 1.0, 2.0) if (xmax - zs) / s <= 4)
    lo = list(np.arange(0, zs + 1e-9, s1))
    hi = [v for v in np.arange(s2, xmax + 1e-9, s2) if v > zs]
    # drop a tick within 7 % of the axis width of the dashed line or of the previous tick
    width = zs + (xmax - zs) / k
    keep, last = [], zs
    for v in hi:
        u = zs + (v - zs) / k
        if u - last > 0.07 * width:
            keep.append(v)
            last = u
    hi = keep
    return xmax, ylo, k, [round(v, 3) for v in lo + hi]


def main(stem, *pairs):
    """pairs: 'year=workdir' for each column, in column order"""
    works = {int(a.split("=", 1)[0]): a.split("=", 1)[1] for a in pairs}
    cols = list(works)
    data = {y: year_data(y, w) for y, w in works.items()}
    w30, y0 = works[cols[0]], cols[0]
    # 2026-10-08: row a also on each column's own range
    # 2026-10-13: one horizontal range for all columns of row a, as for row b
    xa_all = shared_ranges(data)[0]
    xa = {y: xa_all for y in cols}
    bax = {}
    for y in cols:
        xb, yb, kb, tb = b_axes(data[y][1], y)
        F5._XT[y], F5._SQZ[y] = tb, kb
        bax[y] = (xb, yb)
    # 2026-10-13: one vertical range for all columns of row b (the lowest floor)
    y_common = min(v[1] for v in bax.values())
    bax = {y: (v[0], y_common) for y, v in bax.items()}
    for y in cols:
        xb, yb, kb, tb = b_axes(data[y][1], y)
        print(f"panel b {y}: 0 to {xb:.2f} Gt, floor {yb:.0f} US$/t, right of the dashed line compressed {kb:.1f}x")
    for y in cols:
        print(f"panel a {y}: {xa[y][0]:.0f} to {xa[y][1]:.0f} US$/t")
    # one row order for all columns: 2030 net cost, importers above exporters
    inputs.MAPS = Path(w30) / "data"
    sb = pd.read_csv(inputs.MAPS / "security_budget.csv", index_col=0)
    d30 = data[y0][0]
    imp = sb.import_pct.reindex(d30.index) > 0
    order = {"exps": list(d30.net_usd_t[~imp].sort_values(ascending=False).index),
             "imps": list(d30.net_usd_t[imp].sort_values(ascending=False).index)}
    # 2026-10-13: importers grouped by the first cost year in which the portfolio is justified
    # (net premium at or below the carbon price), then by the 2030 net premium, so the green rings
    # form a staircase across the columns; the list runs bottom to top
    def _first(c):
        for y in cols:
            dy = data[y][0]
            if c in dy.index and float(dy.net_usd_t[c]) <= float(dy.p_co2_usd_t[c]):
                return y
        return 9999
    top_down = sorted(order["imps"], key=lambda c: (_first(c), float(d30.net_usd_t[c])))
    order["imps"] = top_down[::-1]
    print("row groups:", {y: [c for c in top_down if _first(c) == y] for y in list(cols) + [9999]})

    # 2026-10-08: <= 200 mm tall so the page does not shrink it below 5 pt (Nature: 5-7 pt at print size)
    fig = plt.figure(figsize=(183 * MM, 200 * MM))      # <= 200 mm (Nature 5-7 pt at print size)
    outer = fig.add_gridspec(2, 1, height_ratios=[1.6, 1.3], hspace=0.22,
                             left=0.135, right=0.99, top=0.93, bottom=0.055)
    # 2026-10-08: row b a little more space between panels, for each panel's own cost labels
    ga = outer[0].subgridspec(1, len(cols), wspace=0.20)
    gb = outer[1].subgridspec(1, len(cols), wspace=0.20 if len(cols) < 4 else 0.30)
    RCOL = dict(REGION_COL)
    present = set()
    bs = []
    for k, y in enumerate(cols):
        d, p, tj = data[y]
        inputs.MAPS = Path(works[y]) / "data"
        a = fig.add_subplot(ga[0, k])
        draw_a_circles(a, d, margin="column", order=order, ylabels=(k == 0), legend=False,
                       group_labels=(k == len(cols) - 1), band_label=True, xlim=xa[y],
                       mark_justified=True, net_column=len(cols) < 4)   # four columns: margin only
        a.set_title(f"{y}", fontsize=7.5, fontweight="bold", pad=4)
        if k == len(cols) // 2:
            a.set_xlabel("Abatement cost (US\\$ tCO$_2^{-1}$)", fontsize=7)   # 2026-10-13: same unit as panel b
        b = fig.add_subplot(gb[0, k])
        present |= F5._curve_to_zero(b, p, y, RCOL, tj, xmax=bax[y][0], ylo=bax[y][1], inside=True)
        bs.append(b)
        # 2026-10-13: the same labelled ticks in every panel b
        b.set_yticks(np.arange(bax[y][1], 300 + 1, 100))
        if k:
            b.set_ylabel("")
            pass                                       # each panel b keeps its own cost labels
        if k == len(cols) // 2:
            b.set_xlabel("Cumulative CO$_2$ displaced (Gt yr$^{-1}$)", fontsize=7)
    # one key for row a across the top, one for row b above it (Fig. 4 style: keys drawn like the marks)
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    ha = [Line2D([], [], marker="o", ls="none", ms=5.5, mfc="white", mec=INKC, label="Cost premium"),   # 2026-10-13: terms as in the caption and text
          Line2D([], [], marker="o", ls="none", ms=5.5, color=INKC, label="Net premium"),
          Line2D([], [], color=SECC, lw=1.3, marker="<", ms=4, markevery=[0], label="Security margin"),
          Line2D([], [], marker="|", ls="none", ms=9, mew=1.2, color=MAG, label="Carbon price"),
          Line2D([], [], marker="o", ls="none", ms=7.5, mfc="none", mec=SECC, mew=1.3,
                 label="Justified"),
]
    fig.legend(handles=ha, loc="lower center", bbox_to_anchor=(0.56, 0.955), ncol=5, fontsize=6.5,
               frameon=False, handlelength=1.2, handletextpad=0.4, columnspacing=1.0)
    names = [r for r in RCOL if r in present]
    short = {"Rest of Asia and Oceania": "Rest of Asia & Oceania", "China": "China (Mainland)"}
    bs[0].legend([Rectangle((0, 0), 1, 1, fc=RCOL[r]) for r in names], [short.get(r, r) for r in names],
                 fontsize=6, frameon=False, ncol=6, loc="lower left", bbox_to_anchor=(-0.02, 1.04),
                 handlelength=1.1, columnspacing=0.8, borderaxespad=0.0)
    fig.text(0.005, 0.985, "a", fontsize=8, fontweight="bold", ha="left", va="top")
    fig.text(0.005, 0.385, "b", fontsize=8, fontweight="bold", ha="left", va="top")
    out = Path(stem)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(out.with_suffix(".png"), dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {out}.(pdf|png)")


if __name__ == "__main__":
    main(*sys.argv[1:])
