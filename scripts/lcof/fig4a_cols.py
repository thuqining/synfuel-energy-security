"""
fig4a_cols.py — Fig. 4a for all 139 economies and all three cost years within Nature's 170 mm height
(2026-10-21). One column per economy, cut into two rows at a group boundary (justified at 2030, 2040 or 2050
costs on top; not justified by 2050 and net exporters below), each group marked (lcof.figgroups). In each column
three thin vertical lines, one per cost year (2030, 2040, 2050, dark to light blue), from the cost premium (open
circle) down to the net premium (filled circle), so the line length is the security margin; a green ring marks a
justified portfolio (net premium at or below the carbon price, magenta tick). Above each row: the 2030 security
margin and net premium (US$ per tCO2). Axis compression and order as fig4_years (importers by the first cost year
justified, then the 2030 net premium; net exporters last). Data: console/build/fig4a_all_<year>.csv.

    python -m lcof.fig4a_cols <out stem> [height_mm]
"""
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

from lcof.fig4a_all import load, fwd, B, B2, YEARS, SHORT, MM, SECC, MAG, SHADE
from lcof.figgroups import split_rows, mark_groups, count, col_font, INK

# 2026-10-21: cost years by shade AND shape (never shade alone); the security margin a light green line in the
# background, the justified ring dark green on top, the below-zero band neutral gray
YC = {2030: "#253494", 2040: "#2C7FB8", 2050: "#41B6C4"}   # 2026-10-21: YlGnBu steps, kept apart from the gray
MK = {2030: "o", 2040: "s", 2050: "^"}
MARGIN_C, RING_C, ZERO_C = "#8CC79F", "#1B7A4B", "#EBEBEB"
LAB = {2030: "Justified 2030", 2040: "Justified 2040", 2050: "Justified 2050",   # first cost year justified
       9999: "Not justified by 2050", "x": "Net exporters"}
# 2026-10-21: two-line names for the one-row core version, where a group can be one column wide
LAB2 = {2030: "Justified\n2030", 2040: "Justified\n2040", 2050: "Justified\n2050", 9999: "Not justified\nby 2050",
        "x": "Net\nexporters"}


def main(stem, height_mm=165.0, fig=None, subset=None):
    mpl.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"], "font.size": 5.5,
                         "axes.linewidth": 0.5, "ytick.major.width": 0.5, "pdf.fonttype": 42})
    data, imps, exps, first = load()
    if subset is not None:          # 2026-10-21: e.g. the core 30 for the main text, drawn in one row
        imps = [c for c in imps if c in subset]
        exps = [c for c in exps if c in subset]
    d50 = data[2050]
    gap50 = {c: float(d50.net_usd_t[c] - d50.p_co2_usd_t[c]) for c in imps if c in d50.index}
    # 2026-10-21: economies not justified by 2050 are ordered by how far their 2050 net premium lies above the
    # carbon price, closest first; the justified groups keep the 2030 net-premium order
    imps = [c for c in imps if first.get(c) != 9999] + \
        sorted([c for c in imps if first.get(c) == 9999], key=lambda c: gap50.get(c, 1e9))
    rows = imps + exps
    grp = lambda c: first.get(c, "x")
    # 2026-10-21: justified groups and net exporters on top, not justified below (rows of similar length)
    blocks, width = split_rows(rows, grp, {2030, 2040, 2050, "x"}) if subset is None else ([rows], len(rows))
    counts = count(rows, grp)
    ylo, yhi = -1050.0, 1200.0      # 2026-10-22: rings at the floor clear of the bottom axis line
    FLOOR = -820.0                  # 2026-10-21: values below sit here, a ring width above the axis
    ticks = [-800, -200, 0, 500, 1000]
    off = {2030: -0.27, 2040: 0.0, 2050: 0.27}
    fmt = lambda v: f"{v:,.0f}".replace("-", "−")
    d30 = data[2030]
    # 2026-10-21: fig may be a SubFigure (lcof.fig4_combo draws a over b on one page); then nothing is saved
    own = fig is None
    if own:
        fig = plt.figure(figsize=(183 * MM, height_mm * MM))
    # 2026-10-21: margins in millimetres, so the layout holds at any height (165 mm alone, ~118 mm above 4b):
    # legend and group names on top, rotated names below each row, two 5 mm rows of numbers per row
    top_mm, bot_mm, gap_mm, num_mm = (11.0 if subset is None else 14.0), 18.0, 24.0, 5.0
    nr = len(blocks)
    row_mm = (height_mm - top_mm - bot_mm - gap_mm * (nr - 1)) / nr
    gs = fig.add_gridspec(nr, 1, hspace=gap_mm / row_mm, left=0.085, right=0.995,
                          top=1 - top_mm / height_mm, bottom=bot_mm / height_mm)
    # 2026-10-21: the justified groups carry the message, so their columns are wider; net exporters (no
    # security margin) get narrow columns
    # 2026-10-22 (co-author): in the 30-economy main figure the numbers are set level and the names slanted, so
    # the net exporters' columns are widened to hold three digits
    level = subset is not None
    # (7 pt numbers: about 1 mm between three-digit numbers, 0.6 mm between the four-character negatives)
    wt = lambda c: (0.95 if level else 0.6) if grp(c) == "x" else (1.2 if level and grp(c) in (2030, 2040, 2050) else 1.0)
    for k, blk in enumerate(blocks):
        w = np.array([wt(c) for c in blk])
        xe = np.r_[0.0, np.cumsum(w)] - 0.5           # column edges
        xs = (xe[:-1] + xe[1:]) / 2                  # column centres
        sg = gs[k].subgridspec(3, 1, height_ratios=[num_mm, num_mm, row_mm - 2 * num_mm - 0.4], hspace=0.02)
        am, an, ax = (fig.add_subplot(sg[j]) for j in range(3))
        # 2026-10-21: the numbers stand on white, coloured as the marks they report: the security margin
        # green, the 2030 net premium dark blue
        for a, lab, col in ((am, "Margin\n2030", RING_C), (an, "Net\n2030", YC[2030])):
            a.set_xlim(xe[0] - 0.1, xe[-1] + 0.1)   # 2026-10-21: each row fills the width
            a.set_ylim(0, 1)
            a.axis("off")
            a.text(-1.0, 0.5, lab, ha="right", va="center", fontsize=7.0 if subset is not None else 6.0, color=col,
                   clip_on=False)
        ax.set_xlim(xe[0] - 0.1, xe[-1] + 0.1)
        T = 7.0 if subset is not None else 6.0   # 2026-10-22: main text 7 pt, SI (139) 6 pt
        fsz = [col_font(ax, wi, hi=T) for wi in w] if subset is not None else [5.0] * len(w)   # SI: 5 pt
        # ring diameter: the spacing between neighbouring years in the column, at most 2.4 mm (in points^2)
        unit_mm = ax.get_window_extent().width / ax.figure.dpi * 25.4 / (xe[-1] - xe[0] + 0.2)
        ring_s = [(min(0.27 * wi * unit_mm * 0.95, 2.4) / 0.3528) ** 2 for wi in w]
        ax.fill_between([xe[0] - 0.1, xe[-1] + 0.1], float(fwd(ylo)), 0, color=ZERO_C, lw=0, zorder=0.2)
        # 2026-10-21: the band named on the panel, centred on the widest run of columns of one group whose net
        # premiums all stay above zero, on a patch of the band's own colour so no grid or divider line crosses it
        def _clear(c):
            return all(not (c in data[y].index and np.isfinite(data[y].net_usd_t[c]) and data[y].net_usd_t[c] < 0)
                       for y in YEARS)
        best, s = (0, 0), None
        for j in range(len(blk) + 1):
            ok = j < len(blk) and _clear(blk[j]) and (s is None or grp(blk[j]) == grp(blk[s]))
            if ok and s is None:
                s = j
            elif not ok and s is not None:
                if xe[j] - xe[s] > xe[best[1]] - xe[best[0]]:
                    best = (s, j)
                s = j if (j < len(blk) and _clear(blk[j])) else None
        if best[1] > best[0]:
            ax.text((xe[best[0]] + xe[best[1]]) / 2, (float(fwd(ylo)) + float(fwd(-200.0))) / 2, "Net premium < 0",
                    ha="center", va="center", fontsize=T, color="#6B6B6B", zorder=2.5,
                    bbox=dict(fc=ZERO_C, ec="none", pad=1.0))
        for b in (B, B2):
            ax.plot([xe[0] - 0.1, xe[-1] + 0.1], [float(fwd(b))] * 2, color="#CCCCCC", lw=0.4, ls=(0, (2, 2)), zorder=1)
        for i, c in enumerate(blk):
            imp = c in imps
            if c in d30.index and np.isfinite(d30.net_usd_t[c]):
                sm, sn = fmt(float(d30.gross_usd_t[c] - d30.net_usd_t[c])), fmt(float(d30.net_usd_t[c]))
                f_ = T if level else fsz[i]          # 2026-10-22 (user): 7 pt like the rest of the main figure
                am.text(xs[i], 0.5, sm, rotation=0 if level else 90,
                        ha="center", va="center", fontsize=f_, color=RING_C)
                an.text(xs[i], 0.5, sn, rotation=0 if level else 90, ha="center", va="center", fontsize=f_,
                        color=YC[2030])
            ax.plot([xs[i] - 0.45 * w[i], xs[i] + 0.45 * w[i]], [float(fwd(float(d30.p_co2_usd_t[c])))] * 2, color=MAG,
                    lw=1.0, zorder=2)
            for y in YEARS:
                d = data[y]
                if c not in d.index or not np.isfinite(d.net_usd_t[c]):
                    continue
                x = xs[i] + off[y] * w[i]
                # values below the axis floor stop just above it, clear of the axis line
                g = float(fwd(np.clip(d.gross_usd_t[c], FLOOR, yhi)))
                nt = float(d.net_usd_t[c])
                nv = float(fwd(np.clip(nt, FLOOR, yhi)))
                # 2026-10-21: the line from cost premium to net premium is the security margin, drawn green as
                # in the text; the cost year is read from the marker shape and shade
                ax.plot([x, x], [g, nv], color=MARGIN_C, lw=0.8, zorder=3, solid_capstyle="butt")
                ax.scatter([x], [g], s=4.5, marker=MK[y], facecolor="white", edgecolor=YC[y], linewidths=0.5, zorder=4,
                           clip_on=False)
                ax.scatter([x], [nv], s=4.5, marker=MK[y], color=YC[y], lw=0, zorder=5, clip_on=False)
                # 2026-10-21: a justified portfolio is ringed in green whatever its year's marker, the ring as wide
                # as the spacing between the three years allows (so rings never run into each other)
                if imp and nt <= float(d.p_co2_usd_t[c]):
                    ax.scatter([x], [nv], s=ring_s[i], marker="o", facecolor="none", edgecolor=RING_C,
                               linewidths=0.75, zorder=6, clip_on=False)
        mark_groups((am, an, ax), am, blk, grp, LAB if subset is None else LAB2, counts, band_axes=(), edges=xe,
                    fontsize=7.0)
        ax.set_xlim(xe[0] - 0.1, xe[-1] + 0.1)
        ax.set_ylim(float(fwd(ylo)), float(fwd(yhi)))
        ax.set_yticks([float(fwd(t)) for t in ticks])
        ax.set_yticklabels([f"{t:,}".replace("-", "−") for t in ticks], fontsize=T)
        ax.set_ylabel("Abatement cost\n(US\\$ tCO$_2^{-1}$)", fontsize=7, labelpad=2)
        ax.set_xticks(xs)
        ax.set_xticklabels([SHORT.get(c, c) for c in blk], rotation=45 if level else 90, color=INK,
                           ha="right" if level else "center", rotation_mode="anchor" if level else "default")
        for lab, f in zip(ax.get_xticklabels(), fsz):
            lab.set_fontsize(T if level else f)
        ax.tick_params(axis="x", length=0, pad=1.5)
        ax.tick_params(axis="y", length=2, pad=1.5)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    h = [Line2D([], [], ls="none", marker=MK[y], ms=3.6, color=YC[y], label=f"{y}") for y in YEARS]
    h += [Line2D([], [], ls="none", marker="o", ms=2.8, mfc="white", mec=INK, mew=0.6, label="Cost premium"),
          Line2D([], [], ls="none", marker="o", ms=2.8, color=INK, label="Net premium"),
          Line2D([], [], color=MARGIN_C, lw=1.2, label="Security margin"),
          Line2D([], [], ls="none", marker="o", ms=5.0, mfc="none", mec=RING_C, mew=0.9, label="Justified"),
          Line2D([], [], color=MAG, lw=1.0, label="Carbon price")]
    fig.legend(handles=h, loc="upper center", ncol=9, fontsize=7.0, frameon=False, bbox_to_anchor=(0.53, 1.0),
               handlelength=1.2, columnspacing=1.0, handletextpad=0.4, borderaxespad=0.2)
    if not own:
        return
    from lcof.figcheck import report
    report(fig, Path(stem).name)
    out = Path(stem)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out.with_suffix(".pdf"))
    fig.savefig(out.with_suffix(".png"), dpi=300)
    plt.close(fig)
    print(f"saved {out}.(pdf|png): rows {[len(b) for b in blocks]}, groups {dict(counts)}")


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 165.0)
