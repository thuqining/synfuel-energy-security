"""
fig5_all.py — Fig. 5 for all 139 economies at one cost year (2026-10-21; main text 2030, SI 2040 and 2050).

Groups and order of security_budget._figure: imports covered, budget binds, land binds, net exporters, each by
the share 1% of GDP buys. GDP projected to the cost year (lcof.gdp_projection). Data: console/index.html.

    python -m lcof.fig5_all <out stem> <year>
"""
import json, sys
from pathlib import Path
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

R = Path(r"D:\document\postdoc\Research\synthetic_fuel\release")
OUT = Path(sys.argv[1])
YEAR = sys.argv[2] if len(sys.argv) > 2 else "2030"
t = (R / "console/index.html").read_text(encoding="utf-8")
D = json.JSONDecoder().raw_decode(t[t.index("const DATA=") + 11:])[0]
C, rows = D["countries"], D["order"]["f5"][YEAR]
SHORT = {"United States of America": "United States", "Dominican Republic": "Dominican Rep.", "China": "China (Mainland)",
         "Taiwan": "China (Taiwan)", "Bosnia and Herzegovina": "Bosnia & Herz.", "Central African Republic": "Central African Rep.",
         "Democratic Republic of the Congo": "DR Congo", "Republic of the Congo": "Congo", "United Republic of Tanzania": "Tanzania",
         "Trinidad and Tobago": "Trinidad & Tobago", "United Arab Emirates": "UAE", "Republic of Serbia": "Serbia",
         "North Macedonia": "N. Macedonia", "Equatorial Guinea": "Eq. Guinea"}
mpl.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"], "font.size": 6,
                     "axes.linewidth": 0.5, "xtick.labelsize": 5.2, "ytick.labelsize": 6, "pdf.fonttype": 42,
                     "hatch.color": "#7F8A95", "hatch.linewidth": 0.5})
BC = ["#0B4F9E", "#4A90D9", "#A8CCEC"]
GRP = ["imports covered", "budget binds", "land binds", "net exporter"]
GLAB = {"imports covered": "Imports covered", "budget binds": "Budget binds", "land binds": "Land binds", "net exporter": "Net exporters"}
MM = 1 / 25.4
n = len(rows)
half = int(np.ceil(n / 2))
parts = [rows[:half], rows[half:]]
fig = plt.figure(figsize=(183 * MM, 170 * MM))
gs = fig.add_gridspec(3, 1, height_ratios=[1, 0.40, 1], hspace=0.04, left=0.075, right=0.995, top=0.95, bottom=0.115)
for k, part in enumerate(parts):
    ax = fig.add_subplot(gs[2 * k])
    for i, c in enumerate(part):
        r = C[c]["f5"][YEAR]
        lv = [0, r["s1"], r["s2"], r["s3"]]
        for j in range(3):
            if lv[j + 1] > lv[j]:
                ax.add_patch(Rectangle((i - 0.4, lv[j]), 0.8, lv[j + 1] - lv[j], fc=BC[j], ec="none", zorder=2))
        if r["land"] > r["s3"] + 0.05:
            ax.add_patch(Rectangle((i - 0.4, r["s3"]), 0.8, r["land"] - r["s3"], fc="#ECEEF0", ec="none", hatch="//////", lw=0, zorder=1))
        if r["land"] < 99.95:
            ax.plot([i - 0.46, i + 0.46], [r["land"], r["land"]], color="#1A1A1A", lw=1.4, solid_capstyle="butt", zorder=3)
        if r["imp"] and r["imp"] > 0:
            ax.plot(i, min(r["imp"], 100), marker="v", ms=2.6, color="#CB181D", mec="none", zorder=4)
    # group bands and labels
    gs_ = [C[c]["f5"][YEAR]["grp"] for c in part]
    s = 0
    for j in range(1, len(part) + 1):
        if j == len(part) or gs_[j] != gs_[s]:
            if j < len(part):
                ax.axvline(j - 0.5, color="#1A1A1A", lw=0.5, alpha=0.6, ls=(0, (4, 2)) if gs_[j] == "net exporter" else "-", zorder=5)
            ax.text((s + j - 1) / 2, 104, GLAB[gs_[s]], ha="center", va="bottom", fontsize=5.8, color="#3A4550")
            s = j
    ax.set_xlim(-0.6, half - 0.4)
    ax.set_ylim(0, 112)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_yticklabels(["0", "25", "50", "75", "100%"])
    ax.grid(axis="y", color="#E6E6E6", lw=0.4, zorder=0)
    ax.set_xticks(np.arange(len(part)))
    labs = ax.set_xticklabels([SHORT.get(c, c) + ("*" if False else "") for c in part], rotation=90)
    for lab, c in zip(labs, part):
        lab.set_color("#1A1A1A" if C[c].get("core") else "#7A8794")
    ax.tick_params(axis="x", length=0, pad=1.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.set_ylabel("Share of fuel demand made at home", fontsize=6)
    fig.text(0.006, ax.get_position().y1 + 0.03, "ab"[k], fontsize=8, fontweight="bold", va="bottom")
h = [Rectangle((0, 0), 1, 1, fc=BC[0]), Rectangle((0, 0), 1, 1, fc=BC[1]), Rectangle((0, 0), 1, 1, fc=BC[2]),
     Rectangle((0, 0), 1, 1, fc="#ECEEF0", hatch="//////"), plt.Line2D([], [], color="#1A1A1A", lw=1.4),
     plt.Line2D([], [], color="#CB181D", marker="v", ls="none", ms=3.5)]
fig.legend(h, ["1% GDP", "2% GDP", "3% GDP", "unused land", "land ceiling", "imported share"], loc="upper center", ncol=6,
           fontsize=6, frameon=False, bbox_to_anchor=(0.53, 1.0), handlelength=1.4)
fig.savefig(OUT.with_suffix(".pdf"))
fig.savefig(OUT.with_suffix(".png"), dpi=200)
print("saved", OUT, n, "economies")
