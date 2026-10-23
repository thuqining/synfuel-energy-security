"""
fig_si_workflow.py - Supplementary Fig.: how the data, models and figures connect
(2026-10-05; Nature Energy papers commonly give such an overview at the start of
Methods). Three columns on tinted grounds, as in Fig. 1: input data, the six
model steps (numbered, with their Supplementary Note), and the main figures,
each tagged with the steps that feed it. No crossing arrows.

From scripts/:  python -u -m lcof.fig_si_workflow
Writes cf_global_final/figures/pptx/fig_si_workflow.(pdf|png).
"""
from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

mpl.use("Agg")

from .fig_main_cost import MM, NAT_RC
from .fig_pptx_pairs import OUT

mpl.rcParams.update(NAT_RC)
mpl.rcParams.update({"pdf.fonttype": 42, "mathtext.default": "regular"})   # CO2 subscript in the text font

INK, GREY = "#1F2A36", "#5A6570"
GROUND = {"data": "#EEF3F8", "model": "#F8F1E7", "result": "#F1F2F4"}
ACCENT = "#1F5F8B"

# step: (title, detail, note)
# 2026-10-22: all text at 7 pt, so the descriptions run to three shorter lines; six main figures (the
# abatement cost curves became Fig. 5, the budget figure Fig. 6)
STEPS = [
    ("Production costs",
     "one hourly program per cell and\nweather year: power, storage,\nelectrolyzer, flexible synthesis", "Note 3"),
    ("Addressable demand",
     "sector maps anchored to national\nenergy balances", "Note 3"),
    ("Import prices and exposure",
     "monthly prices in and out of\ndisruptions; chain exposure and\nsupplier concentration", "Note 4"),
    ("Security value",
     "expected shortfall (from disruption\nrates) × value of lost fuel", "Note 5"),
    ("National budgets and land",
     "premium filled in merit order at\n1–3% of GDP, within land limits", "Note 6"),
    ("Carbon and trajectory",
     "displaced CO$_2$ at 2030–2050\ncosts, abatement cost curves", "Note 5"),
]
DATA = [
    "ERA5 weather 2006–2025; IEA, IRENA,\nDEA, NREL ATB costs (Note 2); cost\nof capital; Climate TRACE CO$_2$",
    "EDGAR sector emissions; UN energy\nbalances; Energy Institute",
    "UN Comtrade, Eurostat, EIA, national\ncustoms, USGS nitrogen; World Bank\nPink Sheet; JODI-Gas; US CPI-U",
    "IEA, EIA, CRS, GAO and OIES event\nrecords; ENTSOG and ACER; IEA\nstock obligations",
    "World Development Indicators\n(GDP); screened land",
    "IPCC emission factors; World\nBank carbon prices",
]
RESULTS = [
    ("Fig. 1", "framework, costs\nand demand", (1, 2)),
    ("Fig. 2", "supply–demand\nmismatch", (1, 2)),
    ("Fig. 3", "ammonia against\nimport prices", (1, 2, 3)),
    ("Fig. 4", "security value and\njustified portfolios", (1, 2, 3, 4, 5, 6)),
    ("Fig. 5", "abatement cost\ncurves", (1, 2, 3, 4, 6)),
    ("Fig. 6", "budget and land\nlimits", (1, 2, 3, 5)),
]


def _box(ax, x, y, w, h, fc, ec="none", lw=0.0, r=1.2):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
                                fc=fc, ec=ec, lw=lw, zorder=2))


def _badge(ax, x, y, k, r=2.0):
    ax.add_patch(plt.Circle((x, y), r, fc=ACCENT, ec="none", zorder=4))
    ax.text(x, y, str(k), ha="center", va="center", fontsize=7, color="white", fontweight="bold", zorder=5)


def main():
    W, H = 183.0, 125.0
    fig = plt.figure(figsize=(W * MM, H * MM))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)
    ax.axis("off")

    cols = {"data": (2, 54), "model": (60, 64), "result": (130, 51)}
    for key, (x, w) in cols.items():
        _box(ax, x, 3, w, H - 6, GROUND[key], r=2.5)
    for key, title in (("data", "INPUT DATA"), ("model", "MODEL STEPS"), ("result", "MAIN FIGURES")):
        x, w = cols[key]
        ax.text(x + w / 2, 8.5, title, ha="center", va="center", fontsize=7, color=GREY, fontweight="bold")

    top, rh = 14.0, 17.6
    for k, ((title, detail, note), data) in enumerate(zip(STEPS, DATA), start=1):
        y = top + (k - 1) * rh
        xd, wd = cols["data"]
        ax.text(xd + 3, y + rh / 2 - 0.6, data, ha="left", va="center", fontsize=7, color=INK, linespacing=1.2)
        xm, wm = cols["model"]
        _box(ax, xm + 3, y + 1.2, wm - 6, rh - 2.4, "white", ec="#C9CED3", lw=0.5)
        _badge(ax, xm + 7.5, y + rh / 2, k)
        ax.text(xm + 11.5, y + 4.6, title, ha="left", va="center", fontsize=7, color=INK, fontweight="bold")
        ax.text(xm + wm - 4.5, y + 4.6, note, ha="right", va="center", fontsize=7, color=GREY)
        ax.text(xm + 11.5, y + 7.0, detail, ha="left", va="top", fontsize=7, color=INK, linespacing=1.15)
        # data -> step arrow, touching the box edge
        ax.annotate("", xy=(xm + 3, y + rh / 2), xytext=(xd + wd - 1.5, y + rh / 2),
                    arrowprops=dict(arrowstyle="-|>", color=GREY, lw=0.6, mutation_scale=6,
                                    shrinkA=0, shrinkB=0), zorder=3)

    xr, wr = cols["result"]
    rr = (H - 6 - (top - 3)) / len(RESULTS)
    for j, (fig_id, what, feeds) in enumerate(RESULTS):
        y = top + j * rr
        _box(ax, xr + 3, y + 1.4, wr - 6, rr - 2.8, "white", ec="#C9CED3", lw=0.5)
        ax.text(xr + 6, y + 3.6, fig_id, ha="left", va="top", fontsize=7, color=INK, fontweight="bold")
        ax.text(xr + 16, y + 3.6, what, ha="left", va="top", fontsize=7, color=INK, linespacing=1.15)
        ax.text(xr + 6, y + rr - 4.6, "from steps", ha="left", va="center", fontsize=7, color=GREY)
        for n, s in enumerate(feeds):
            _badge(ax, xr + 22 + n * 4.2, y + rr - 4.6, s, r=1.8)
    # model -> results arrow (one, at mid height)
    ax.annotate("", xy=(xr + 1.5, H / 2), xytext=(cols["model"][0] + cols["model"][1] - 1.5, H / 2),
                arrowprops=dict(arrowstyle="-|>", color=GREY, lw=0.8, mutation_scale=7, shrinkA=0, shrinkB=0))
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"fig_si_workflow.{ext}", dpi=300)
    plt.close(fig)
    print("saved fig_si_workflow.(pdf|png)")


if __name__ == "__main__":
    main()
