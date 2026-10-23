"""
fig5_cols.py — Fig. 5 for all 139 economies at one cost year (2026-10-21; main text 2030, SI 2040 and 2050),
within Nature's 170 mm height: one column per economy, the list wrapped into two stacked rows.

Groups and order of security_budget._figure (imports covered, budget binds, land binds, net exporters; each by
the share 1% of GDP buys); GDP projected to the cost year (lcof.gdp_projection). Per column: the share of
addressable demand made at home with 1, 2 and 3% of GDP (dark to light blue), hatched unused land up to the land
ceiling (black cap) and the imported share (red triangle). Data: console/index.html (console/build_console.py).

    python -m lcof.fig5_cols <out stem> <year> [height_mm]
"""
import json
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

from lcof.fig3_rows import SHORT, MM
from lcof.figgroups import split_rows, mark_groups, count, col_font

R = Path(__file__).resolve().parents[2]
BC = ["#0B4F9E", "#4A90D9", "#A8CCEC"]
INK = "#1A1A1A"
GLAB = {"imports covered": "Imports covered", "budget binds": "Budget binds", "land binds": "Land binds",
        "net exporter": "Net exporters"}


def main(stem, year="2030", height_mm=150.0, fig=None, subset=None):
    mpl.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"], "font.size": 5.5,
                         "axes.linewidth": 0.5, "ytick.major.width": 0.5, "pdf.fonttype": 42,
                         "hatch.color": "#7F8A95", "hatch.linewidth": 0.5})
    t = (R / "console/index.html").read_text(encoding="utf-8")
    D = json.JSONDecoder().raw_decode(t[t.index("const DATA=") + 11:])[0]
    C, rows = D["countries"], D["order"]["f5"][year]
    n = len(rows)
    grp = lambda c: C[c]["f5"][year]["grp"]
    if subset is not None:          # 2026-10-21: e.g. the core 30 for the main text, drawn in one row
        rows = [c for c in rows if c in subset]
    blocks, width = split_rows(rows, grp, {"imports covered", "budget binds"}) if subset is None \
        else ([rows], len(rows))
    counts = count(rows, grp)
    own = fig is None              # 2026-10-21: fig may be a SubFigure (lcof.fig5_core); then nothing is saved
    if own:
        fig = plt.figure(figsize=(183 * MM, height_mm * MM))
    # 2026-10-21: margins in millimetres (as at 150 mm), so extra height goes to the plots
    top_mm, bot_mm, gap_mm = 10.0, 17.0, 23.0
    nr = len(blocks)
    row_mm = (height_mm - top_mm - bot_mm - gap_mm * (nr - 1)) / nr
    gs = fig.add_gridspec(nr, 1, hspace=gap_mm / row_mm, left=0.06, right=0.995,
                          top=1 - top_mm / height_mm, bottom=bot_mm / height_mm)
    w = 0.38
    for k, blk in enumerate(blocks):
        ax = fig.add_subplot(gs[k])
        ax.set_xlim(-0.6, len(blk) - 0.4)
        fs = 5.0                        # 2026-10-22: SI 139, one size for the names
        for i, c in enumerate(blk):
            r = C[c]["f5"][year]
            lv = [0, r["s1"], r["s2"], r["s3"]]
            for j in range(3):
                if lv[j + 1] > lv[j]:
                    ax.add_patch(Rectangle((i - w, lv[j]), 2 * w, lv[j + 1] - lv[j], fc=BC[j], ec="none", zorder=2))
            if r["land"] > r["s3"] + 0.05:
                ax.add_patch(Rectangle((i - w, r["s3"]), 2 * w, r["land"] - r["s3"], fc="#ECEEF0", ec="none",
                                       hatch="//////", lw=0, zorder=1))
            if r["land"] < 99.95:
                ax.plot([i - 0.46, i + 0.46], [r["land"]] * 2, color=INK, lw=1.5, solid_capstyle="butt", zorder=3)
            if r["imp"] and r["imp"] > 0:
                ax.plot(i, min(r["imp"], 100), marker="v", ms=3.4, color="#CB181D", mec="none", zorder=4, clip_on=False)
        mark_groups((ax,), ax, blk, grp, GLAB, counts, pad_pt=4.5, fontsize=7.0, band_axes=())   # 2026-10-21: no background bands
        ax.set_xlim(-0.6, len(blk) - 0.4)
        ax.set_ylim(0, 100)
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.set_yticklabels(["0", "25", "50", "75", "100"], fontsize=6)
        ax.set_ylabel("Share of fuel demand made at home (%)", fontsize=7, labelpad=2)
        ax.set_xticks(range(len(blk)))
        ax.set_xticklabels([SHORT.get(c, c) for c in blk], rotation=90, fontsize=fs, color=INK)
        ax.tick_params(axis="x", length=0, pad=1.5)
        ax.tick_params(axis="y", length=2, pad=1.5)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    h = [Rectangle((0, 0), 1, 1, fc=BC[0]), Rectangle((0, 0), 1, 1, fc=BC[1]), Rectangle((0, 0), 1, 1, fc=BC[2]),
         Rectangle((0, 0), 1, 1, fc="#ECEEF0", hatch="//////"), plt.Line2D([], [], color=INK, lw=1.5),
         plt.Line2D([], [], color="#CB181D", marker="v", ls="none", ms=3.8)]
    fig.legend(h, ["1% of GDP", "2% of GDP", "3% of GDP", "Unused land", "Land ceiling", "Imported share"],
               loc="upper center", ncol=6, fontsize=7.0, frameon=False, bbox_to_anchor=(0.53, 1.0), handlelength=1.3,
               columnspacing=1.4, borderaxespad=0.2)
    if not own:
        return
    from lcof.figcheck import report
    report(fig, Path(stem).name)
    out = Path(stem)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out.with_suffix(".pdf"))
    fig.savefig(out.with_suffix(".png"), dpi=300)
    plt.close(fig)
    print(f"saved {out}.(pdf|png): {n} economies, {year}, {height_mm} mm")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "2030", float(sys.argv[3]) if len(sys.argv) > 3 else 150.0)
