"""
fig5_rows.py — Fig. 5 for all 139 economies at one cost year (2026-10-21; main text 2030, SI 2040 and 2050),
one row per economy in two side-by-side blocks, sized so that figure and caption fill one page.

Groups and order of security_budget._figure (imports covered, budget binds, land binds, net exporters; each by
the share 1% of GDP buys); GDP projected to the cost year (lcof.gdp_projection). Per row: the share of addressable
demand made at home with 1, 2 and 3% of GDP (dark to light blue), hatched unused land up to the land ceiling
(black end cap) and the imported share (red pin). Data: console/index.html (console/build_console.py).

    python -m lcof.fig5_rows <out stem> <year> [height_mm]
"""
import json
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

R = Path(__file__).resolve().parents[2]
MM = 1 / 25.4
BC = ["#0B4F9E", "#4A90D9", "#A8CCEC"]
GLAB = {"imports covered": "Imports\ncovered", "budget binds": "Budget\nbinds", "land binds": "Land\nbinds",
        "net exporter": "Net\nexporters"}
SHORT = {"United States of America": "United States", "Dominican Republic": "Dominican Rep.", "China": "China (Mainland)",
         "Taiwan": "China (Taiwan)", "Bosnia and Herzegovina": "Bosnia and Herz.", "Central African Republic": "Central African Rep.",
         "Democratic Republic of the Congo": "DR Congo", "Republic of the Congo": "Congo", "United Republic of Tanzania": "Tanzania",
         "United Arab Emirates": "UAE", "Republic of Serbia": "Serbia"}


def main(stem, year="2030", height_mm=160.0):
    mpl.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"], "font.size": 5.5,
                         "axes.linewidth": 0.5, "xtick.major.width": 0.5, "pdf.fonttype": 42,
                         "hatch.color": "#7F8A95", "hatch.linewidth": 0.5})
    t = (R / "console/index.html").read_text(encoding="utf-8")
    D = json.JSONDecoder().raw_decode(t[t.index("const DATA=") + 11:])[0]
    C, rows = D["countries"], D["order"]["f5"][year]
    n = len(rows)
    half = int(np.ceil(n / 2))
    fig = plt.figure(figsize=(183 * MM, height_mm * MM))
    gs = fig.add_gridspec(1, 2, wspace=0.42, left=0.105, right=0.93, top=0.94, bottom=0.06)
    for k, blk in enumerate((rows[:half], rows[half:])):
        ax = fig.add_subplot(gs[0, k])
        for i, c in enumerate(blk):
            r = C[c]["f5"][year]
            lv = [0, r["s1"], r["s2"], r["s3"]]
            for j in range(3):
                if lv[j + 1] > lv[j]:
                    ax.add_patch(Rectangle((lv[j], i - 0.38), lv[j + 1] - lv[j], 0.76, fc=BC[j], ec="none", zorder=2))
            if r["land"] > r["s3"] + 0.05:
                ax.add_patch(Rectangle((r["s3"], i - 0.38), r["land"] - r["s3"], 0.76, fc="#ECEEF0", ec="none",
                                       hatch="//////", lw=0, zorder=1))
            if r["land"] < 99.95:
                ax.plot([r["land"]] * 2, [i - 0.46, i + 0.46], color="#1A1A1A", lw=1.3, solid_capstyle="butt", zorder=3)
            if r["imp"] and r["imp"] > 0:
                ax.plot(min(r["imp"], 100), i - 0.15, marker="v", ms=2.4, color="#CB181D", mec="none", zorder=4)
        g = [C[c]["f5"][year]["grp"] for c in blk]
        s = 0
        for j in range(1, len(blk) + 1):
            if j < len(blk) and g[j] != g[j - 1]:
                ax.axhline(j - 0.5, color="#1A1A1A", lw=0.5, alpha=0.6,
                           ls=(0, (4, 2)) if g[j] == "net exporter" else "-", zorder=5)
            if j == len(blk) or g[j] != g[s]:
                ax.text(103, (s + j - 1) / 2, GLAB[g[s]], ha="left", va="center", fontsize=5.6, color="#3A4550", clip_on=False)
                s = j
        ax.set_ylim(len(blk) - 0.5, -0.5)
        ax.set_xlim(0, 100)
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.set_xticklabels(["0", "25", "50", "75", "100%"], fontsize=5.6)
        ax.set_yticks(range(len(blk)))
        labs = ax.set_yticklabels([SHORT.get(c, c) for c in blk], fontsize=5.4)
        for lab, c in zip(labs, blk):
            lab.set_color("#1A1A1A" if C[c].get("core") else "#7A8794")
        ax.tick_params(axis="y", length=0, pad=1.5)
        ax.tick_params(axis="x", length=2, pad=1.5)
        ax.grid(axis="x", color="#E6E6E6", lw=0.4, zorder=0)
        for sp in ("top", "right", "left"):
            ax.spines[sp].set_visible(False)
        ax.set_xlabel("Share of addressable fuel demand made at home", fontsize=6, labelpad=2)
    h = [Rectangle((0, 0), 1, 1, fc=BC[0]), Rectangle((0, 0), 1, 1, fc=BC[1]), Rectangle((0, 0), 1, 1, fc=BC[2]),
         Rectangle((0, 0), 1, 1, fc="#ECEEF0", hatch="//////"), plt.Line2D([], [], color="#1A1A1A", lw=1.3),
         plt.Line2D([], [], color="#CB181D", marker="v", ls="none", ms=3.2)]
    fig.legend(h, ["1% of GDP", "2% of GDP", "3% of GDP", "unused land", "land ceiling", "imported share"], loc="upper center",
               ncol=6, fontsize=5.8, frameon=False, bbox_to_anchor=(0.52, 1.0), handlelength=1.3)
    out = Path(stem)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out.with_suffix(".pdf"))
    fig.savefig(out.with_suffix(".png"), dpi=300)
    plt.close(fig)
    print(f"saved {out}.(pdf|png): {n} economies, {year}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "2030", float(sys.argv[3]) if len(sys.argv) > 3 else 160.0)
