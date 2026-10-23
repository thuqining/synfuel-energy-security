"""
fig_si_tiers.py - Supplementary figure (2026-10-09): fuel costs and core results across the three
cost tiers and four cost years. a-f, median levelized cost of each fuel over the 2,740 land cells
(US$/MMBtu, trade unit on the right axis), lowest/central/highest tier; the settings of the main
figures (2025 central, 2030-2050 lowest) are ringed. g-i, economies whose 1%-of-GDP portfolio is
justified (Fig. 4a), CO2 displaced with and without the security value (Fig. 5 since 2026-10-22), and the median
share of demand that 1% of GDP buys (Fig. 6).

Reads work/caselow/lcos_tiers.csv (lcos_tiers.py) and tier_table.csv (tier_table.py).
From scripts/:  python -m lcof.fig_si_tiers <caselow dir> <out dir>
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

mpl.use("Agg")
from .fig_main_cost import MM, NAT_RC

INK, GREY = "#1F2A36", "#5A6570"
TIER = {"low": ("lowest", "#0B4F9E", "-", "o"), "mid": ("central", "#4A90D9", (0, (4, 1.5)), "s"),
        "high": ("highest", "#8FB8E3", (0, (1.2, 1.2)), "^")}
YEARS = [2025, 2030, 2040, 2050]
FUELS = [("hydrogen", "Hydrogen", "US\\$ kg$^{-1}$", 0.120 / 1.0551),
         ("ammonia", "Ammonia", "US\\$ t$^{-1}$", 18.6 / 1.0551),
         ("methanol", "Methanol", "US\\$ t$^{-1}$", 19.9 / 1.0551),
         ("e-methane", "e-Methane", None, None),
         ("e-jet/e-diesel", "e-Jet / e-diesel", "US\\$ bbl$^{-1}$", 0.0351 * 158.987 / 1.0551),
         ("ethanol", "Ethanol", "US\\$ gal$^{-1}$", 0.0212 * 3.78541 / 1.0551)]
MAIN = {(2025, "mid"), (2030, "low"), (2040, "low"), (2050, "low")}


def _style(ax):
    ax.set_xticks(YEARS)
    ax.set_xlim(2023, 2052)
    ax.tick_params(labelsize=6, length=2)
    for s in ("top",):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", alpha=0.25, lw=0.4)


def _lines(ax, get, label_end=False):
    for t, (nm, col, ls, mk) in TIER.items():
        y = [get(yr, t) for yr in YEARS]
        ax.plot(YEARS, y, color=col, ls=ls, lw=1.1, marker=mk, ms=3, mfc=col, mec=col, zorder=3)
        if label_end:
            ax.text(2050.8, y[-1], nm, fontsize=6, color=col, va="center", ha="left")


def main(cdir: str, odir: str):
    mpl.rcParams.update(NAT_RC)
    mpl.rcParams.update({"pdf.fonttype": 42})
    c = pd.read_csv(Path(cdir) / "lcos_tiers.csv").set_index(["fuel", "year", "tier"])
    r = pd.read_csv(Path(cdir) / "tier_table.csv").set_index(["year", "tier"])
    # 2026-10-22 (every SI figure covers the 139 economies): panels g and i count all 118 net importers
    # (sensitivity/all139_sens.py); the core-30 counts stay in Supplementary Table tab:paths
    import json
    a139 = {(x["year"], x["tier"]): x for x in
            json.loads((Path(cdir) / "sensitivity" / "all139_sens.json").read_text(encoding="utf-8"))["paths"]}
    fig = plt.figure(figsize=(183 * MM, 165 * MM))
    gs = fig.add_gridspec(3, 3, left=0.07, right=0.90, bottom=0.06, top=0.93, wspace=0.62, hspace=0.55)
    for k, (f, title, unit, mult) in enumerate(FUELS):
        ax = fig.add_subplot(gs[k // 3, k % 3])
        _lines(ax, lambda yr, t: c.loc[(f, yr, t), "med"])
        ax.set_ylim(0, None)
        ax.set_title(f"{'abcdef'[k]}  {title}", fontsize=7, loc="left", fontweight="bold", color=INK)
        if k % 3 == 0:
            ax.set_ylabel("US\\$ MMBtu$^{-1}$", fontsize=6)
        if unit:
            sec = ax.secondary_yaxis("right", functions=(lambda v, m=mult: v * m, lambda v, m=mult: v / m))
            sec.tick_params(labelsize=6, length=2, colors=GREY)
            sec.set_ylabel(unit, fontsize=6, color=GREY)
        _style(ax)
        if not unit:
            ax.spines["right"].set_visible(False)
    ax = fig.add_subplot(gs[2, 0])
    _lines(ax, lambda yr, t: a139[(yr, t)]["justified"])
    ax.set_ylim(0, 50)
    ax.set_ylabel("net importers (of 118)", fontsize=6)
    ax.set_title("g  Portfolios justified", fontsize=7, loc="left", fontweight="bold", color=INK)
    _style(ax)
    ax = fig.add_subplot(gs[2, 1])
    # grouped bars: per cost year one bar per tier; solid = on cost alone, hatched = added by the security value
    from matplotlib.patches import Patch
    mpl.rcParams["hatch.linewidth"] = 0.5
    bw = 0.26
    for j, (t, (nm, col, ls, mk)) in enumerate(TIER.items()):
        xs = [i + (j - 1) * bw for i in range(len(YEARS))]
        cost = [r.loc[(yr, t), "gt_cost"] for yr in YEARS]
        sec = [r.loc[(yr, t), "gt_sec"] - r.loc[(yr, t), "gt_cost"] for yr in YEARS]
        ax.bar(xs, cost, width=bw * 0.9, color=col, ec="none", zorder=3)
        ax.bar(xs, sec, bottom=cost, width=bw * 0.9, color="white", ec=col, lw=0.5, hatch="//////", zorder=3)
    ax.legend(handles=[Patch(fc=GREY, ec="none", label="on cost alone"),
                       Patch(fc="white", ec=GREY, hatch="//////", lw=0.5, label="added by security value")],
              loc="upper left", fontsize=6, frameon=False, handlelength=1.6)
    ax.set_ylim(0, 2.6)
    ax.set_ylabel("GtCO$_2$ yr$^{-1}$", fontsize=6)
    ax.set_title("h  CO$_2$ displaced (Fig. 5)", fontsize=7, loc="left", fontweight="bold", color=INK)
    _style(ax)
    ax.set_xticks(range(len(YEARS)))
    ax.set_xticklabels([str(y) for y in YEARS])
    ax.set_xlim(-0.55, len(YEARS) - 0.45)
    ax = fig.add_subplot(gs[2, 2])
    _lines(ax, lambda yr, t: a139[(yr, t)]["cov_3"])
    ax.set_ylim(0, 80)
    ax.set_ylabel("net importers (of 118)", fontsize=6)
    ax.set_title("i  Imports covered at 3% of GDP (Fig. 6)", fontsize=7, loc="left", fontweight="bold", color=INK)
    _style(ax)
    from matplotlib.lines import Line2D
    hs = [Line2D([], [], color=col, ls=ls, lw=1.1, marker=mk, ms=3, label=f"{nm} cost tier")
          for nm, col, ls, mk in TIER.values()]
    hs.append(Patch(fc=TIER["low"][1], ec="none", label="bars in h: lowest, central, highest (left to right)"))
    fig.legend(handles=hs, loc="upper left", bbox_to_anchor=(0.06, 0.998), ncol=4, fontsize=6, frameon=False,
               handlelength=2.4, columnspacing=1.6)
    out = Path(odir)
    fig.savefig(out / "fig_si_tiers.pdf")
    fig.savefig(out / "fig_si_tiers.png", dpi=300)
    print("saved", out / "fig_si_tiers.pdf")


if __name__ == "__main__":
    main(*sys.argv[1:])
