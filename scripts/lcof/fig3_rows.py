"""
fig3_rows.py — Fig. 3 for the 139 economies of Figs 4-5 (2026-10-21), one row per economy in two side-by-side
blocks, sized so that figure and caption fill one page.

Rows in the paper's order (fig_main_sites._share_order: import share, bill per mille of GDP, cost ratio; net
exporters below the dashed line). Per row: import share of the ammonia chain (red cell), normal price (grey,
IQR with a 1st-99th line), disruption price (orange line and median diamond), domestic green ammonia from the
lowest-cost cell over 20 weather years (blue box, IQR). Core-30 names black (prices as in Fig. 3), others grey
(prices by the paper's rule for missing prices). Data: console/index.html (console/build_console.py).

    python -m lcof.fig3_rows <out stem> [height_mm]
"""
import json
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle

R = Path(__file__).resolve().parents[2]
MM = 1 / 25.4
BEST, GREY, CRIS = "#0B4F9E", "#8C8C8C", "#D55E00"
SHORT = {"United States of America": "United States", "Dominican Republic": "Dominican Rep.", "China": "China (Mainland)",
         "Taiwan": "China (Taiwan)", "Bosnia and Herzegovina": "Bosnia and Herz.", "Central African Republic": "Central African Rep.",
         "Democratic Republic of the Congo": "DR Congo", "Republic of the Congo": "Congo", "United Republic of Tanzania": "Tanzania",
         "United Arab Emirates": "UAE", "Republic of Serbia": "Serbia"}


def data():
    t = (R / "console/index.html").read_text(encoding="utf-8")
    D = json.JSONDecoder().raw_decode(t[t.index("const DATA=") + 11:])[0]
    C, order = D["countries"], D["order"]["f3amm"]
    k139 = set(pd.read_csv(R / "work/caselow/2030/data/security_budget.csv", index_col=0).index)
    rows = [c for c in order["rows"] if c in k139]
    split = sum(1 for c in order["rows"][:order["split"]] if c in k139)
    return C, rows, split


def main(stem, height_mm=150.0):
    mpl.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"], "font.size": 5.5,
                         "axes.linewidth": 0.5, "xtick.major.width": 0.5, "pdf.fonttype": 42})
    C, rows, split = data()
    n = len(rows)
    half = int(np.ceil(n / 2))
    blocks = [(rows[:half], 0), (rows[half:], half)]
    fig = plt.figure(figsize=(183 * MM, height_mm * MM))
    gs = fig.add_gridspec(1, 2, wspace=0.36, left=0.105, right=0.985, top=0.915, bottom=0.055)
    lo, hi = 10, 200
    for k, (blk, off) in enumerate(blocks):
        sub = gs[0, k].subgridspec(1, 2, width_ratios=[0.07, 1], wspace=0.03)
        ae, ax = fig.add_subplot(sub[0, 0]), fig.add_subplot(sub[0, 1])
        for i, c in enumerate(blk):
            d = C[c]
            e = d.get("E_amm")
            if e is not None:
                ae.add_patch(Rectangle((0, i - 0.45), 1, 0.9, fc=mpl.colormaps["Reds"](0.08 + 0.82 * e), ec="none"))
            pr, bx = d["pr"]["amm"], d["box"]["ammonia"]
            ax.plot([pr["n"][0], pr["n"][4]], [i, i], color=GREY, lw=0.4, alpha=0.7, zorder=1)
            ax.add_patch(Rectangle((pr["n"][1], i - 0.36), pr["n"][3] - pr["n"][1], 0.72, fc=GREY, alpha=0.45, ec="none", zorder=2))
            ax.plot([pr["d"][0], pr["d"][4]], [i + 0.2, i + 0.2], color=CRIS, lw=0.5, zorder=3)
            ax.plot(pr["d"][2], i + 0.2, marker="D", ms=1.9, color=CRIS, mec="none", zorder=4)
            ax.add_patch(Rectangle((bx[1], i - 0.4), max(bx[3] - bx[1], 0.6), 0.8, fc=BEST, ec="none", zorder=5))
        j = split - off                                      # first net exporter in this block
        if 0 < j < len(blk):
            for a in (ax, ae):
                a.axhline(j - 0.5, color="#8A94A0", lw=0.6, ls=(0, (4, 2)), zorder=6)
            ax.text(hi * 0.97, j - 0.1, "net exporters", fontsize=5.3, color="#5A6570", ha="right", va="top")
        for a in (ax, ae):
            a.set_ylim(len(blk) - 0.5, -0.5)
        ae.set_xlim(0, 1)
        ae.set_xticks([])
        ae.set_yticks(range(len(blk)))
        labs = ae.set_yticklabels([SHORT.get(c, c) for c in blk], fontsize=5.4)
        for lab, c in zip(labs, blk):
            lab.set_color("#1A1A1A" if C[c]["pr"]["amm"].get("core") else "#7A8794")
        ae.tick_params(axis="y", length=0, pad=1.5)
        for sp in ae.spines.values():
            sp.set_visible(False)
        ae.set_title("Import\nshare", fontsize=5.3, color="#3A4550", pad=2)
        ax.set_xscale("log")
        ax.set_xlim(lo, hi)
        ax.set_xticks([10, 20, 40, 80, 160])
        ax.set_xticklabels(["10", "20", "40", "80", "160"], fontsize=5.6)
        ax.set_yticks([])
        ax.grid(axis="x", color="#E6E6E6", lw=0.4, zorder=0)
        for sp in ("top", "right", "left"):
            ax.spines[sp].set_visible(False)
        ax.set_xlabel("US\\$ per MMBtu (LHV)", fontsize=6, labelpad=2)
        ax.tick_params(axis="x", length=2, pad=1.5)
    h = [Rectangle((0, 0), 1, 1, fc=BEST), Rectangle((0, 0), 1, 1, fc=GREY, alpha=0.45),
         plt.Line2D([], [], color=CRIS, marker="D", ms=2.5, lw=0.6),
         Rectangle((0, 0), 1, 1, fc=mpl.colormaps["Reds"](0.9))]
    fig.legend(h, ["Green ammonia, lowest-cost cell (IQR, 20 weather years)", "Normal price (IQR; line 1st–99th)",
                   "Disruption price (median; line 1st–99th)", "Import share (white 0% to dark red 100%)"],
               loc="upper center", ncol=4, fontsize=5.8, frameon=False, bbox_to_anchor=(0.53, 1.0), handlelength=1.3,
               columnspacing=1.0)
    out = Path(stem)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out.with_suffix(".pdf"))
    fig.savefig(out.with_suffix(".png"), dpi=300)
    plt.close(fig)
    print(f"saved {out}.(pdf|png): {n} economies, {split} net importers")


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 150.0)
