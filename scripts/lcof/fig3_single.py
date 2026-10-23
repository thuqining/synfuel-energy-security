"""
fig3_single.py — Fig. 3 for the 139 economies of Figs 4-5 in one column (2026-10-21), full page (caption on
the next page), drawn as the published Fig. 3 (lcof.fig_main_sites): domestic green ammonia as a blue box (IQR
over 20 weather years) with 1st-99th whiskers and a white median; normal price as a grey band (1st-99th) with a
white median; disruption price as a capped orange line (1st-99th) with an orange median diamond; import share of
the ammonia chain as a red cell. 139 rows leave ~1.3 mm per row, so names alternate left and right (>= 5 pt).
Rows in the paper's order (fig_main_sites._share_order); net exporters below the dashed line. Core-30 names black
(prices as in Fig. 3), others grey (prices by the paper's rule for missing prices).

    python -m lcof.fig3_single <out stem> [height_mm]
"""
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

from lcof.fig3_rows import data, SHORT, MM

BEST, GREY_P, CRIS = "#0B4F9E", "#8C8C8C", "#D55E00"


def main(stem, height_mm=197.0):
    mpl.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"], "font.size": 5.5,
                         "axes.linewidth": 0.5, "xtick.major.width": 0.5, "pdf.fonttype": 42})
    C, rows, split = data()
    n = len(rows)
    fig = plt.figure(figsize=(183 * MM, height_mm * MM))
    # left names | prices | right names | import share
    gs = fig.add_gridspec(1, 4, width_ratios=[1, 0.03, 0.075, 0.085], wspace=0.0, left=0.135, right=0.985, top=0.975, bottom=0.035)
    ax, an, ae, ab = (fig.add_subplot(gs[0, k]) for k in range(4))
    lo, hi = 10, 200
    h = 0.34                                           # half-height of a box, in rows
    for i, c in enumerate(rows):
        d = C[c]
        pr, bx = d["pr"]["amm"], d["box"]["ammonia"]
        # normal price: grey band 1st-99th, white median
        ax.add_patch(Rectangle((pr["n"][0], i - h * 0.8), pr["n"][4] - pr["n"][0], 2 * h * 0.8, fc=GREY_P, alpha=0.55, ec="none", zorder=1))
        ax.plot([pr["n"][2]] * 2, [i - h * 0.8, i + h * 0.8], color="white", lw=0.6, zorder=2)
        # disruption price: capped orange line 1st-99th, diamond at the median
        ax.plot([pr["d"][0], pr["d"][4]], [i, i], color=CRIS, lw=0.55, zorder=3)
        for x in (pr["d"][0], pr["d"][4]):
            ax.plot([x, x], [i - h * 0.6, i + h * 0.6], color=CRIS, lw=0.55, zorder=3)
        ax.plot(pr["d"][2], i, marker="D", ms=1.7, color=CRIS, mec="none", zorder=4)
        # domestic green ammonia: whiskers 1st-99th, box IQR, white median
        ax.plot([bx[0], bx[4]], [i, i], color=BEST, lw=0.5, zorder=5)
        ax.add_patch(Rectangle((bx[1], i - h), max(bx[3] - bx[1], 0.5), 2 * h, fc=BEST, ec="none", zorder=6))
        ax.plot([bx[2]] * 2, [i - h, i + h], color="white", lw=0.5, zorder=7)
        e = d.get("E_amm")
        if e is not None:
            ae.add_patch(Rectangle((0, i - 0.5), 1, 1, fc=mpl.colormaps["Reds"](0.08 + 0.82 * e), ec="white", lw=0.15))
            ae.text(0.5, i, f"{100 * e:.0f}", ha="center", va="center", fontsize=5.0,
                    color="white" if e > 0.5 else "#3A4550")
        pm = pr.get("pm")
        if pm is not None:
            ab.text(0.55, i, f"{pm:.1f}" if (pm >= 0.05 or pm == 0) else "<0.1", ha="center", va="center",
                    fontsize=5.0, color="#3A4550")
        # faint guide from the row to its name, so the alternating labels stay attached to their rows
        ax.axhline(i, color="#EDEFF2", lw=0.35, zorder=0)
        name = SHORT.get(c, c)
        col = "#1A1A1A" if d["pr"]["amm"].get("core") else "#7A8794"
        ax.text(lo / 1.03, i, name, ha="right", va="center", fontsize=5.0, color=col, clip_on=False)
    if 0 < split < n:
        for a in (ax, ae):
            a.axhline(split - 0.5, color="#8A94A0", lw=0.6, ls=(0, (4, 2)), zorder=8)
        ab.axhline(split - 0.5, color="#8A94A0", lw=0.6, ls=(0, (4, 2)))
        ax.text(hi / 1.05, split - 0.2, "net exporters", fontsize=5.3, color="#5A6570", ha="right", va="top")
    for a in (ax, an, ae, ab):
        a.set_ylim(n - 0.5, -0.5)
        a.set_yticks([])
    ab.set_xlim(0, 1)
    ab.axis("off")
    ab.set_title("Bill\n(‰ of GDP)", fontsize=5.3, color="#3A4550", pad=2)
    an.set_xlim(0, 1)
    an.axis("off")
    ae.set_xlim(0, 1)
    ae.set_xticks([])
    for sp in ae.spines.values():
        sp.set_visible(False)
    ae.set_title("Import\nshare (%)", fontsize=5.3, color="#3A4550", pad=2)
    ax.set_xscale("log")
    ax.set_xlim(lo, hi)
    ax.set_xticks([10, 20, 40, 80, 160])
    ax.set_xticklabels(["10", "20", "40", "80", "160"], fontsize=5.8)
    ax.grid(axis="x", color="#E6E6E6", lw=0.4, zorder=0)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.set_xlabel("Ammonia price and domestic cost, US\\$ per MMBtu (LHV)", fontsize=6.2, labelpad=2)
    ax.tick_params(axis="x", length=2, pad=1.5)
    hd = [Rectangle((0, 0), 1, 1, fc=BEST), Rectangle((0, 0), 1, 1, fc=GREY_P, alpha=0.55),
          plt.Line2D([], [], color=CRIS, marker="D", ms=2.5, lw=0.6), Rectangle((0, 0), 1, 1, fc=mpl.colormaps["Reds"](0.9))]
    fig.legend(hd[:3], ["Green ammonia", "Normal price", "Disruption price"],
               loc="upper center", ncol=3, fontsize=6.0, frameon=False, bbox_to_anchor=(0.53, 1.0), handlelength=1.3,
               columnspacing=1.8, borderaxespad=0.2)
    out = Path(stem)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out.with_suffix(".pdf"))
    fig.savefig(out.with_suffix(".png"), dpi=300)
    plt.close(fig)
    print(f"saved {out}.(pdf|png): {n} economies, {split} net importers")


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 197.0)
