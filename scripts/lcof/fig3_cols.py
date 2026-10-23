"""
fig3_cols.py — Fig. 3 (ammonia) and its SI versions for the other fuels, for the 139 economies of Figs 4-5
(2026-10-21), within Nature's 170 mm height. One column per economy, drawn as the published Fig. 3
(lcof.fig_main_sites) turned upright: domestic fuel from the lowest-cost cell as a blue box (IQR over 20 weather
years) with 10th-90th whiskers and a white median; normal price as a grey band (10th-90th) with a white median;
disruption price as a capped orange line (10th-90th) with an orange median diamond (2026-10-22: 10th-90th, the
90th percentile being the test of the paper, in place of 1st-99th). Above each row: import share
of the fuel's chain (%, red cells) and the bill at normal prices (per mille of GDP).

Columns in the paper's order (fig_main_sites._share_order: import share, bill, cost ratio), cut into two rows at a
group boundary: economies importing their whole chain on top; partial importers and net exporters below (lcof.
figgroups). An asterisk marks prices not observed for the economy (core-30 rule for ammonia and diesel + jet;
regional estimates for the other fuels).

    python -m lcof.fig3_cols <out stem> [fuel] [height_mm]
    fuel: ammonia (default), e-diesel (diesel and jet fuel), e-methane, methanol, ethanol, hydrogen
"""
import json
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle

from lcof.fig3_rows import SHORT, MM
from lcof.figgroups import split_rows, mark_groups, count, col_font, INK

R = Path(__file__).resolve().parents[2]
BEST, GREY_P, CRIS = "#0B4F9E", "#8C8C8C", "#D55E00"
PK = {"ammonia": "amm", "e-diesel": "ft", "e-methane": "em", "methanol": "meoh", "ethanol": "eth", "hydrogen": "h2"}
NAME = {"ammonia": "Green ammonia", "e-diesel": "E-diesel/e-jet fuel", "e-methane": "E-methane", "methanol": "Methanol",
        "ethanol": "Ethanol", "hydrogen": "Hydrogen"}
LAB = {"full": "Imports the whole chain", "part": "Imports part of the chain", "x": "Net exporters"}
# legend names as in the published Fig. 3 (fig_main_sites: syn / fos)
KEYS = {"ammonia": ("Green ammonia", "Fossil ammonia"), "e-diesel": ("E-diesel/e-jet fuel", "Fossil diesel/jet fuel"),
        "e-methane": ("E-methane", "Natural gas"), "methanol": ("Synthetic methanol", "Gas-based methanol"),
        "ethanol": ("Synthetic ethanol", "Fossil diesel/jet fuel"), "hydrogen": ("Green hydrogen", "Gray hydrogen")}


def data(fuel):
    t = (R / "console/index.html").read_text(encoding="utf-8")
    D = json.JSONDecoder().raw_decode(t[t.index("const DATA=") + 11:])[0]
    C, pk = D["countries"], PK[fuel]
    order = D["order"]["f3" + pk]
    k139 = set(pd.read_csv(R / "work/caselow/2030/data/security_budget.csv", index_col=0).index)
    rows = [c for c in order["rows"] if c in k139 and C[c].get("box", {}).get(fuel) and C[c].get("pr", {}).get(pk)]
    E = (lambda c: C[c].get("E_amm")) if pk == "amm" else (lambda c: C[c].get("E_ft")) if pk == "ft" else \
        (lambda c: C[c].get("Ech", {}).get(fuel))
    return C, pk, rows, E


def main(stem, fuel="ammonia", height_mm=166.0, fig=None, subset=None):
    mpl.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"], "font.size": 5.5,
                         "axes.linewidth": 0.5, "ytick.major.width": 0.5, "pdf.fonttype": 42})
    C, pk, rows, E = data(fuel)

    def grp(c):
        e = E(c)
        return "x" if (e is None or e <= 0) else ("full" if e >= 0.995 else "part")
    if subset is not None:          # 2026-10-21: e.g. the core 30 for the main text, drawn in one row
        rows = [c for c in rows if c in subset]
    blocks, width = split_rows(rows, grp, {"full"}) if subset is None else ([rows], len(rows))
    counts = count(rows, grp)
    # 2026-10-21: an asterisk marks an economy without any month of its own price (customs records for ammonia,
    # any own price for diesel and jet fuel; an observed national gas price for the gas-based fuels), core or not
    if pk in ("amm", "ft"):
        own = pd.read_csv(R / "console/build" / f"fig3_prices_{'ammonia' if pk == 'amm' else 'ft'}.csv",
                          index_col=0).own_share
        observed = lambda c: bool(own.get(c, 0) > 0)
    else:
        observed = lambda c: C[c]["pr"][pk].get("obs")
    own_fig = fig is None          # 2026-10-21: fig may be a SubFigure (lcof.fig35_core); then nothing is saved
    if own_fig:
        fig = plt.figure(figsize=(183 * MM, height_mm * MM))
    # 2026-10-21: margins in millimetres (as at 166 mm), so extra height goes to the plots
    top_mm, bot_mm, gap_mm, num_mm = 11.0, 20.0, 25.5, 5.8
    # 2026-10-22 (co-author): in the 30-economy main figure names run at 45 degrees and the numbers above the
    # columns are set level; the 139-economy SI rows are too dense for either and stay upright
    level = subset is not None
    if level:
        bot_mm = 19.0                  # 2026-10-22 (co-author): a little more space between a and b
    nr = len(blocks)
    row_mm = (height_mm - top_mm - bot_mm - gap_mm * (nr - 1)) / nr
    outer = fig.add_gridspec(nr, 1, hspace=gap_mm / row_mm, left=0.08 if subset else 0.06, right=0.995,   # 2026-10-22: room for the 7 pt row labels
                             top=1 - top_mm / height_mm, bottom=bot_mm / height_mm)
    lo, hi = 3 if fuel == "hydrogen" else 10, 200
    # 2026-10-21: the published Fig. 3 marks (fig_main_sites, MERGED), turned upright and overlaid in one column:
    # normal price a wide translucent band with a white bar at its median; disruption price a thin capped line
    # with a white-edged diamond at its median; domestic fuel a box (interquartile range, floor width with a dark
    # edge when the range is too narrow to see) on a 10th-90th whisker with a white median line
    BAND_HW, BOX_HW, CAP_HW, PT = 0.40, 0.24, 0.26, 0.10
    for k, blk in enumerate(blocks):
        g = outer[k].subgridspec(3, 1, height_ratios=[num_mm, num_mm, row_mm - 2 * num_mm - 0.5], hspace=0.04)
        ae, ab, ax = (fig.add_subplot(g[j]) for j in range(3))
        for a in (ax, ae, ab):
            a.set_xlim(-0.6, len(blk) - 0.4)   # 2026-10-21: each row fills the width
        ax.set_yscale("log")
        ax.set_ylim(lo, hi)
        T = 7.0 if subset is not None else 6.0   # 2026-10-22: main text 7 pt, SI (139) 6 pt
        fs = col_font(ax, 1.0, hi=T) if subset is not None else 5.0   # SI 139: one size, 5 pt
        for i, c in enumerate(blk):
            d = C[c]
            pr, bx = d["pr"][pk], d["box"][fuel]
            n1, _, nm, _, n99 = pr["n"]
            ax.add_patch(Rectangle((i - BAND_HW, n1), 2 * BAND_HW, n99 - n1, fc=GREY_P, alpha=0.6, ec="none", zorder=2))
            ax.plot([i - BAND_HW, i + BAND_HW], [nm] * 2, color="white", lw=1.2, zorder=3, solid_capstyle="butt")
            ax.plot([i, i], [bx[0], bx[4]], color=BEST, lw=0.8, zorder=4)
            b_lo, b_hi = bx[1], bx[3]
            thin = (np.log10(max(b_hi, 1e-9)) - np.log10(max(b_lo, 1e-9))) < PT * 0.12
            if thin:                           # floor height on the log axis, dark edge, no median line
                m = bx[2]
                b_lo, b_hi = m / 10 ** (PT * 0.06), m * 10 ** (PT * 0.06)
            ax.add_patch(Rectangle((i - BOX_HW, b_lo), 2 * BOX_HW, b_hi - b_lo, fc=BEST, alpha=0.85, zorder=5,
                                   ec="#3D4650" if thin else "none", lw=0.45 if thin else 0))
            if not thin:
                ax.plot([i - BOX_HW, i + BOX_HW], [bx[2]] * 2, color="white", lw=0.9, zorder=6, solid_capstyle="butt")
            d1, _, dm, _, d99 = pr["d"]
            ax.plot([i, i], [d1, d99], color=CRIS, lw=0.9, zorder=7, solid_capstyle="butt")
            for y in (d1, d99):
                ax.plot([i - CAP_HW, i + CAP_HW], [y, y], color=CRIS, lw=0.9, zorder=7, solid_capstyle="butt")
            ax.plot([i], [dm], marker="D", ms=3.2, mfc=CRIS, mec="white", mew=0.5, zorder=8)
            e = E(c)
            if e is not None:
                ae.add_patch(Rectangle((i - 0.5, 0), 1, 1, fc=mpl.colormaps["Reds"](0.08 + 0.82 * e), ec="white", lw=0.2))
                ae.text(i, 0.5, f"{100 * e:.0f}", rotation=0 if level else 90, ha="center", va="center", fontsize=fs,
                        color="white" if e > 0.5 else INK)
            pm = pr.get("pm")
            if pm is not None and np.isfinite(pm):
                ab.text(i, 0.5, "0" if pm == 0 else (f"{pm:.1f}" if pm >= 0.05 else "<0.1"), rotation=0 if level else 90,
                        ha="center", va="center", fontsize=fs, color=INK)
        mark_groups((ae, ab, ax), ae, blk, grp, LAB, counts, fontsize=7.0, band_axes=())   # 2026-10-21: no background bands
        for a, lab in ((ae, "Import\nshare (%)"), (ab, "Bill\n(‰ GDP)")):
            a.set_ylim(0, 1)
            a.set_xticks([])
            a.set_yticks([])
            for sp in a.spines.values():
                sp.set_visible(False)
            a.text(-0.9, 0.5, lab, ha="right", va="center", fontsize=T, color=INK, clip_on=False)
        yt = [5, 10, 20, 40, 80, 160] if fuel == "hydrogen" else ([20, 40, 80, 160] if level else [10, 20, 40, 80, 160])   # 2026-10-22: no 10 beside the slanted first name
        ax.set_yticks(yt)
        ax.set_yticks([], minor=True)
        ax.set_yticklabels([str(v) for v in yt], fontsize=T)
        ax.set_ylabel("US\\$ per MMBtu", fontsize=7, labelpad=2)
        ax.set_xticks(range(len(blk)))
        ax.set_xticklabels([SHORT.get(c, c) + ("" if observed(c) else "*") for c in blk], rotation=45 if level else 90,
                           ha="right" if level else "center", rotation_mode="anchor" if level else "default",
                           fontsize=fs, color=INK)
        ax.tick_params(axis="x", length=0, pad=1.5)
        ax.tick_params(axis="y", length=2, pad=1.5)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    # keys as in the published Fig. 3 legend (fig_main_sites, MERGED): horizontal glyphs of the same marks
    from matplotlib.legend_handler import HandlerBase
    import matplotlib.lines as ml

    class _Box(HandlerBase):
        def create_artists(self, legend, orig, x0, y0, w, h, fs_, trans):
            yc = y0 + h / 2
            return [ml.Line2D([x0, x0 + w], [yc, yc], color=BEST, lw=0.8, transform=trans),
                    Rectangle((x0 + 0.28 * w, yc - 0.32 * h), 0.44 * w, 0.64 * h, fc=BEST, alpha=0.85, lw=0,
                              transform=trans),
                    ml.Line2D([x0 + 0.5 * w] * 2, [yc - 0.32 * h, yc + 0.32 * h], color="white", lw=0.9,
                              transform=trans)]

    class _Band(HandlerBase):
        def create_artists(self, legend, orig, x0, y0, w, h, fs_, trans):
            yc = y0 + h / 2
            return [ml.Line2D([x0, x0 + w], [yc, yc], color=GREY_P, lw=4.2, alpha=0.6, solid_capstyle="butt",
                              transform=trans),
                    ml.Line2D([x0 + w / 2] * 2, [yc - 0.30 * h, yc + 0.30 * h], color="white", lw=1.5,
                              solid_capstyle="butt", transform=trans)]

    class _Cap(HandlerBase):
        def create_artists(self, legend, orig, x0, y0, w, h, fs_, trans):
            yc = y0 + h / 2
            out = [ml.Line2D([x0, x0 + w], [yc, yc], color=CRIS, lw=1.0, solid_capstyle="butt", transform=trans)]
            for x in (x0, x0 + w):
                out.append(ml.Line2D([x, x], [yc - 0.28 * h, yc + 0.28 * h], color=CRIS, lw=1.0,
                                     solid_capstyle="butt", transform=trans))
            out.append(ml.Line2D([x0 + w / 2], [yc], marker="D", ms=3.4, mfc=CRIS, mec="white", mew=0.5, ls="none",
                                 transform=trans))
            return out

    kc, kn, kb = object(), object(), object()
    syn, fos = KEYS[fuel]
    fig.legend([kn, kc, kb], [fos + " (normal)", fos + " (disruption)", syn],   # 2026-10-21: normal, disruption, synthetic
               handler_map={kb: _Box(), kn: _Band(), kc: _Cap()}, loc="upper center", ncol=3, fontsize=7.0,
               frameon=False, bbox_to_anchor=(0.53, 1.0), handlelength=2.4, columnspacing=2.2, borderaxespad=0.3)
    if not own_fig:
        return
    from lcof.figcheck import report
    report(fig, Path(stem).name)
    out = Path(stem)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out.with_suffix(".pdf"))
    fig.savefig(out.with_suffix(".png"), dpi=300)
    plt.close(fig)
    print(f"saved {out}.(pdf|png): {fuel}, {len(rows)} economies, rows {[len(b) for b in blocks]}, groups {dict(counts)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "ammonia", float(sys.argv[3]) if len(sys.argv) > 3 else 166.0)
