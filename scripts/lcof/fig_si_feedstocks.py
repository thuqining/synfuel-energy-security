"""
fig_si_feedstocks.py - Supplementary figure (Note 2): the two bought feeds of
the synthesis cascade, each as its resource and its least-cost delivered price
(2026-10-05; replaces fig_feedstocks.py, whose CO2 panel showed the retired
climate-neutral-only layer).

  a  (2026-10-05) the cheapest CO2 source of each cell: industrial point
     source, biogenic source, or direct air capture where no point source
     lies within 1,000 km (co2_cost_by_cell.csv)
  b  delivered CO2 price per cell, equation (s:co2source): the cheapest
     source within reach plus US$6/t per 100 km (co2_cost_by_cell.csv, the
     layer every figure uses)
  c  the cheapest climate-neutral source per cell, biogenic or direct air
     capture (co2_cost_by_cell_neutral.csv, the sensitivity case)
  d  delivered CO2 price in that case
  e  water source per cell: freshwater, coastal desalination, or
     desalination with long-distance conveyance (water-stressed countries)
  f  delivered water price per cell (water_cost_by_cell.csv)

From scripts/:  python -u -m lcof.fig_si_feedstocks
Writes cf_global_final/figures/pptx/fig_si_feedstocks.(pdf|png).
"""
from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

mpl.use("Agg")

from . import inputs
from .fig_main_cost import MM, NAT_RC, _nat_map
from .fig_pptx_pairs import OUT, _COUNTRIES

mpl.rcParams.update(NAT_RC)
mpl.rcParams.update({"pdf.fonttype": 42, "font.size": 7})
FOSSIL_C, BIO_C, DAC_C = "#5A6570", "#009E73", "#B07AA1"
# 2026-10-05: three hues, not three shades of blue
WCOL = ["#9ECAE1", "#E69F00", "#542788"]          # freshwater, coastal desal, inland desal (conveyed)
WLAB = ["Freshwater", "Desalination, coastal", "Desalination, inland"]


def _spacer(fig, ax):
    """the colour bar the right-hand maps carry, drawn and hidden, so the
    left-hand maps have the same size and position; their keys go there"""
    sm = plt.cm.ScalarMappable(cmap="Greys", norm=mpl.colors.Normalize(0, 1))
    cb = fig.colorbar(sm, ax=ax, orientation="horizontal", shrink=0.55, pad=0.02, aspect=32)
    cb.ax.set_visible(False)


def _base(ax):
    _COUNTRIES.plot(ax=ax, color="#EEF0F2", linewidth=0, rasterized=True)
    _COUNTRIES.boundary.plot(ax=ax, color="0.55", linewidth=0.1, rasterized=True)
    ax.set_xlim(-180, 180)
    ax.set_ylim(-58, 84)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect("equal")
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_anchor("N")


def main():
    src = pd.read_csv(inputs.PROJECT / "data" / "co2" / "climate_trace" / "co2_sources_climatetrace_2025.csv")
    co2 = pd.read_csv(inputs.MAPS / "co2_cost_by_cell.csv")
    neu = pd.read_csv(inputs.MAPS / "co2_cost_by_cell_neutral.csv")
    wat = pd.read_csv(inputs.MAPS / "water_cost_by_cell.csv")

    # three rows: CO2 as used in every figure; CO2 when it must be climate
    # neutral (biogenic or direct air capture, the sensitivity case); water
    fig = plt.figure(figsize=(183 * MM, 165 * MM))
    H, Y = 0.295, (0.685, 0.355, 0.025)
    axs = [fig.add_axes([x, y, 0.49, H]) for y in Y for x in (0.00, 0.51)]
    a, b, c, d, e, f = axs

    # a: the cheapest source of each cell, all three kinds in one map (
    # 2026-10-05): industrial point source, biogenic source, or direct air
    # capture where no point source lies within 1,000 km
    _base(a)
    acol = [FOSSIL_C, BIO_C, DAC_C]
    kind = co2.pathway.astype(str).map({"industrial": 0, "biogenic": 1, "DAC": 2})
    _nat_map(fig, a, dict(zip(co2.cell_id, kind)), mpl.colors.ListedColormap(acol), -0.5, 2.5, "", "")
    fig.axes[-1].set_visible(False)
    a.legend(handles=[Patch(color=acol[0], label="Industrial point source"),
                      Patch(color=acol[1], label="Biogenic source"),
                      Patch(color=acol[2], label="Direct air capture")],
             fontsize=7, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.04), ncol=3,
             borderaxespad=0.0, handlelength=1.0, columnspacing=1.0)

    # b: delivered CO2 price, main case
    _nat_map(fig, b, dict(zip(co2.cell_id, co2.co2_cost)), "YlOrBr", 50, 200,
             "Delivered CO$_2$ price (US\\$ t$^{-1}$)", "")

    # c: cheapest climate-neutral source
    _base(c)
    ncol = [BIO_C, DAC_C]
    code = (neu.pathway.astype(str) == "DAC").astype(int)
    _nat_map(fig, c, dict(zip(neu.cell_id, code)), mpl.colors.ListedColormap(ncol), -0.5, 1.5, "", "")
    fig.axes[-1].set_visible(False)
    c.legend(handles=[Patch(color=ncol[0], label="Biogenic source"), Patch(color=ncol[1], label="Direct air capture")],
             fontsize=7, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.04), ncol=2,
             borderaxespad=0.0, handlelength=1.0)

    # d: delivered CO2 price, climate-neutral case
    _nat_map(fig, d, dict(zip(neu.cell_id, neu.co2_cost)), "YlOrBr", 50, 500,
             "Delivered CO$_2$ price, climate-neutral (US\\$ t$^{-1}$)", "")

    # e: water source
    _base(e)
    lut = mpl.colors.ListedColormap(WCOL)
    _nat_map(fig, e, dict(zip(wat.cell_id, wat.method.astype(int) - 1)), lut, -0.5, 2.5, "", "")
    fig.axes[-1].set_visible(False)            # the categorical panel needs a key, not a colour bar
    e.legend(handles=[Patch(color=col, label=lab) for col, lab in zip(WCOL, WLAB)], fontsize=7,
             frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.04), ncol=3, borderaxespad=0.0,
             handlelength=1.0, columnspacing=1.0)

    # f: delivered water price
    _nat_map(fig, f, dict(zip(wat.cell_id, wat.water_cost)), "PuBu", 0.5, 2.0,
             "Delivered water price (US\\$ t$^{-1}$)", "")

    for ax, letter in zip(axs, "abcdef"):
        ax.text(0.0, 1.0, letter, transform=ax.transAxes, fontsize=8, fontweight="bold", va="top")
    fig.savefig(OUT / "fig_si_feedstocks.pdf", bbox_inches="tight", dpi=300)   # rasterized layers at 300 dpi keep the PDF small
    fig.savefig(OUT / "fig_si_feedstocks.png", dpi=600, bbox_inches="tight")
    plt.close(fig)

    nb = int(src.carbon_type.astype(str).str.contains("bio").sum())
    pw = co2.pathway.astype(str)
    print(f"  main case: DAC {int((pw == 'DAC').sum())} cells (no point source within 1,000 km); "
          f"non-DAC price range {co2.co2_cost[pw != 'DAC'].min():.0f}-{co2.co2_cost[pw != 'DAC'].max():.0f} US$/t")
    pn = neu.pathway.astype(str)
    print(f"saved fig_si_feedstocks.(pdf|png): {len(src):,} sources ({nb} biogenic), "
          f"{src.co2_t_per_year.sum() / 1e9:.1f} Gt/yr; main case: industrial {int((pw == 'industrial').sum())}, "
          f"biogenic {int((pw == 'biogenic').sum())} cells, price median {co2.co2_cost.median():.0f} "
          f"(range {co2.co2_cost.min():.0f}-{co2.co2_cost.max():.0f}) US$/t, distance median "
          f"{co2.distance_km.median():.0f} km; climate-neutral: DAC {int((pn == 'DAC').sum())}, biogenic "
          f"{int((pn == 'biogenic').sum())} cells, biogenic price median "
          f"{neu.co2_cost[pn == 'biogenic'].median():.0f} (range {neu.co2_cost[pn == 'biogenic'].min():.0f}-"
          f"{neu.co2_cost[pn == 'biogenic'].max():.0f}); water: freshwater {int((wat.method == 1).sum())}, "
          f"coastal desal {int((wat.method == 2).sum())}, desal + conveyance {int((wat.method == 3).sum())} cells, "
          f"price {wat.water_cost.min():.2f}-{wat.water_cost.max():.2f} US$/t")


if __name__ == "__main__":
    main()
