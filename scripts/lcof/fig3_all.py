"""
fig3_all.py — Fig. 3 for the 139 economies of Figs 4-5 (2026-10-21), compact: one column per economy.

Rows (columns) in the paper's order (fig_main_sites._share_order: import share, bill per mille of GDP, cost
ratio; net exporters after the divider). Core-30 names in black (prices as in Fig. 3); the others in grey
(prices built by the paper's rule for missing prices). Data: console/index.html (console/build_console.py).

    python -m lcof.fig3_all <out stem>
"""
import json, sys
from pathlib import Path
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

R = Path(r"D:\document\postdoc\Research\synthetic_fuel\release")
OUT = Path(sys.argv[1])
t = (R / "console/index.html").read_text(encoding="utf-8")
D = json.JSONDecoder().raw_decode(t[t.index("const DATA=") + 11:])[0]
C, order = D["countries"], D["order"]["f3amm"]
import pandas as pd
K139 = set(pd.read_csv(R / "work/caselow/2030/data/security_budget.csv", index_col=0).index)
rows = [c for c in order["rows"] if c in K139]
split = sum(1 for c in order["rows"][:order["split"]] if c in K139)
SHORT = {"United States of America": "United States", "Dominican Republic": "Dominican Rep.", "China": "China (Mainland)",
         "Taiwan": "China (Taiwan)", "United Kingdom": "United Kingdom", "Bosnia and Herzegovina": "Bosnia & Herz.",
         "Central African Republic": "Central African Rep.", "Democratic Republic of the Congo": "DR Congo",
         "Republic of the Congo": "Congo", "United Republic of Tanzania": "Tanzania", "Trinidad and Tobago": "Trinidad & Tobago",
         "Papua New Guinea": "Papua New Guinea", "United Arab Emirates": "UAE", "Republic of Serbia": "Serbia",
         "North Macedonia": "N. Macedonia", "Equatorial Guinea": "Eq. Guinea", "eSwatini": "Eswatini"}
mpl.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"], "font.size": 6,
                     "axes.linewidth": 0.5, "xtick.major.width": 0.5, "ytick.major.width": 0.5,
                     "xtick.labelsize": 5.2, "ytick.labelsize": 6, "pdf.fonttype": 42})
BEST, GREY, CRIS = "#0B4F9E", "#8C8C8C", "#D55E00"
MM = 1 / 25.4
n = len(rows)
half = int(np.ceil(n / 2))
parts = [rows[:half], rows[half:]]
fig = plt.figure(figsize=(183 * MM, 196 * MM))
gs = fig.add_gridspec(5, 1, height_ratios=[0.07, 1, 0.42, 0.07, 1], hspace=0.04, left=0.06, right=0.995, top=0.965, bottom=0.115)
lo, hi = 10, 160
for k, part in enumerate(parts):
    ax_e = fig.add_subplot(gs[3 * k])
    ax = fig.add_subplot(gs[3 * k + 1], sharex=ax_e)
    x = np.arange(len(part))
    for i, c in enumerate(part):
        d = C[c]
        e = d.get("E_amm")
        if e is not None:
            ax_e.add_patch(Rectangle((i - 0.45, 0), 0.9, 1, fc=mpl.colormaps["Reds"](0.08 + 0.82 * e), ec="none"))
        pr, bx = d["pr"]["amm"], d["box"]["ammonia"]
        core = pr.get("core")
        # normal prices: gray bar (IQR) with a thin 1st-99th line; disruption: orange line and diamond
        ax.plot([i, i], [pr["n"][0], pr["n"][4]], color=GREY, lw=0.4, alpha=0.7, zorder=1)
        ax.add_patch(Rectangle((i - 0.38, pr["n"][1]), 0.76, pr["n"][3] - pr["n"][1], fc=GREY, alpha=0.45, ec="none", zorder=2))
        ax.plot([i + 0.18, i + 0.18], [pr["d"][0], pr["d"][4]], color=CRIS, lw=0.5, zorder=3)
        ax.plot(i + 0.18, pr["d"][2], marker="D", ms=1.9, color=CRIS, mec="none", zorder=4)
        # domestic green ammonia: blue bar at the median (IQR as a short box)
        ax.add_patch(Rectangle((i - 0.42, bx[1]), 0.84, max(bx[3] - bx[1], 0.6), fc=BEST, ec="none", zorder=5))
    if split is not None:
        # divider before the first net exporter in this half
        j0 = rows.index(part[0])
        if j0 <= split < j0 + len(part):
            xs = split - j0 - 0.5
            for a in (ax, ax_e):
                a.axvline(xs, color="#8A94A0", lw=0.6, ls=(0, (4, 2)), zorder=6)
            ax.text(xs + 0.4, hi * 0.92, "net exporters", fontsize=5.5, color="#5A6570", va="top")
    ax.set_yscale("log")
    ax.set_ylim(lo, hi)
    ax.set_yticks([10, 20, 40, 80, 160])
    ax.set_yticklabels(["10", "20", "40", "80", "160"])
    ax.grid(axis="y", color="#E6E6E6", lw=0.4, zorder=0)
    ax.set_xlim(-0.6, half - 0.4)
    ax.set_xticks(x)
    labs = ax.set_xticklabels([SHORT.get(c, c) for c in part], rotation=90)
    for lab, c in zip(labs, part):
        lab.set_color("#1A1A1A" if C[c]["pr"]["amm"].get("core") else "#7A8794")
    ax.tick_params(axis="x", length=0, pad=1.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.set_ylabel("US$ per MMBtu", fontsize=6)
    ax_e.set_ylim(0, 1)
    ax_e.axis("off")
    ax_e.text(-0.8, 0.5, "Import\nshare", fontsize=5.5, ha="right", va="center", color="#3A4550")
    fig.text(0.006, ax_e.get_position().y1 + 0.004, "ab"[k], fontsize=8, fontweight="bold", va="bottom")
# legend
h = [Rectangle((0, 0), 1, 1, fc=BEST), Rectangle((0, 0), 1, 1, fc=GREY, alpha=0.45),
     plt.Line2D([], [], color=CRIS, marker="D", ms=2.5, lw=0.6)]
fig.legend(h, ["Green ammonia, lowest-cost cell (IQR over 20 weather years)", "Normal price (IQR; line 1st–99th)",
               "Disruption price (median; line 1st–99th)"], loc="upper center", ncol=3, fontsize=6, frameon=False,
           bbox_to_anchor=(0.53, 1.0), handlelength=1.4)
fig.savefig(OUT.with_suffix(".pdf"))
fig.savefig(OUT.with_suffix(".png"), dpi=200)
print("saved", OUT, n, "economies; split", split)
