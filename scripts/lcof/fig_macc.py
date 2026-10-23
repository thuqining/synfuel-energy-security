"""
fig_macc.py — the abatement-cost curves cut at zero (2030 / 2040 / 2050) as a figure of their own (2026-10-22,
formerly Fig. 4c). The three build years are stacked, each across the full page width, on one common
x axis: true scale up to X1 Gt, which holds all the demand that pays off in every year, and compressed by the same
factor beyond it, so the dotted (cost only) and dashed (with security value) lines can be compared across years.
Same data and marks as fig4b_only / fig5_chain._curve_to_zero.

From scripts/:  python -m lcof.fig_macc <out stem> 2030=<workdir> 2040=<workdir> 2050=<workdir>
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

mpl.use("Agg")

from . import inputs
from . import fig5_chain as F5
from .fig_main_cost import MM, NAT_RC
from .global_trajectory import REGION_COL
from .fig4_years import year_data, b_axes

mpl.rcParams.update(NAT_RC)

X1 = 2.0             # Gt: true scale up to here (the demand that pays off with security value is 1.86 Gt in 2050)
RIGHT = 0.12         # share of the width left for the compressed demand beyond X1 (the paying part first)


def main(stem, *pairs, row_mm=40.0):
    works = {int(a.split("=", 1)[0]): a.split("=", 1)[1] for a in pairs}
    years = list(works)
    data = {y: year_data(y, w) for y, w in works.items()}
    ax_ = {y: b_axes(data[y][1], y) for y in years}
    xmax = max(v[0] for v in ax_.values())
    ylo = min(v[1] for v in ax_.values()) - 100.0     # 2026-10-22: room under the deepest bars for the group names
    k = float(np.ceil((xmax - X1) / (RIGHT / (1 - RIGHT) * X1)))
    F5._COMMON = (X1, k)
    ticks = [0, 0.5, 1.0, 1.5, 2.0] + [v for v in (3, 4, 5, 6) if v <= xmax]
    for y in years:
        F5._XT[y], F5._SQZ[y] = ticks, k
        F5._SQZ2.pop(y, None)
    top_mm, bot_mm, gap_mm = 9.0, 11.0, 4.0
    H = top_mm + bot_mm + len(years) * row_mm + (len(years) - 1) * gap_mm
    fig = plt.figure(figsize=(183 * MM, H * MM))
    gs = fig.add_gridspec(len(years), 1, hspace=gap_mm / row_mm, left=0.075, right=0.99,
                          top=1 - top_mm / H, bottom=bot_mm / H)
    present = set()
    for i, y in enumerate(years):
        d, p, tj = data[y]
        inputs.MAPS = Path(works[y]) / "data"
        b = fig.add_subplot(gs[i])
        present |= F5._curve_to_zero(b, p, y, dict(REGION_COL), tj, xmax=xmax, ylo=ylo, inside=True)
        b.set_yticks(np.arange(ylo + 100.0, 300 + 1, 200))     # ticks on the hundreds as before
        b.set_ylabel("")
        b.text(0.995, 0.98, f"{y} costs", transform=b.transAxes, fontsize=7, fontweight="bold", ha="right", va="top")
        if i < len(years) - 1:
            b.tick_params(axis="x", labelbottom=False)
        else:
            b.set_xlabel("Cumulative CO$_2$ displaced (Gt yr$^{-1}$)", fontsize=7)
    fig.text(0.004, (bot_mm + 0.5 * (H - top_mm - bot_mm)) / H, "Abatement cost (US\\$ tCO$_2^{-1}$)",
             rotation=90, ha="left", va="center", fontsize=7)
    names = [r for r in REGION_COL if r in present]
    nick = {"Rest of Asia and Oceania": "Rest of Asia & Oceania", "China": "China (Mainland)"}
    fig.legend([Rectangle((0, 0), 1, 1, fc=REGION_COL[r]) for r in names], [nick.get(r, r) for r in names],
               fontsize=7, frameon=False, ncol=len(names), loc="upper center", bbox_to_anchor=(0.53, 1.0),
               handlelength=1.1, columnspacing=1.0, borderaxespad=0.2)
    F5._COMMON = None
    from lcof.figcheck import report
    report(fig, Path(stem).name)
    out = Path(stem)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out.with_suffix(".pdf"))
    fig.savefig(out.with_suffix(".png"), dpi=300)
    plt.close(fig)
    print(f"saved {out}.(pdf|png): {H:.0f} mm; common axis true to {X1} Gt, {k:g}x beyond, to {xmax:.2f} Gt")


if __name__ == "__main__":
    main(*sys.argv[1:])
