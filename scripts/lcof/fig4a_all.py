"""
fig4a_all.py — Fig. 4a for all 139 economies, on its own page (2026-10-21).

The marks, colours, axis compression and row order of fig4_years / fig5a_chain.draw_a_circles,
sized for 139 rows: net importers grouped by the first cost year in which the 1%-of-GDP portfolio is
justified (net premium at or below the carbon price), then by the 2030 net premium; net exporters
below. Data: console/build/fig4a_all_<year>.csv (lcof.console_export, all economies, projected GDP).

    python -m lcof.fig4a_all <out stem>
"""
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

R = Path(__file__).resolve().parents[2]
BUILD = R / "console" / "build"
W = R / "work" / "caselow"
YEARS = (2030, 2040, 2050)
MM = 1 / 25.4
INKC, SECC, MAG, SHADE, LBL, GREYC = "#0B4F9E", "#1B7A4B", "#B4116F", "#E3F2EA", "#5A6570", "#8A94A0"
SHORT = {"United States of America": "United States", "Dominican Republic": "Dominican Rep.", "China": "China (Mainland)",
         "Taiwan": "China (Taiwan)", "Bosnia and Herzegovina": "Bosnia and Herz.", "Central African Republic": "Central African Rep.",
         "Democratic Republic of the Congo": "DR Congo", "Republic of the Congo": "Congo", "United Republic of Tanzania": "Tanzania",
         "Trinidad and Tobago": "Trinidad and Tobago", "United Arab Emirates": "UAE", "Republic of Serbia": "Serbia",
         "North Macedonia": "North Macedonia", "Equatorial Guinea": "Equatorial Guinea"}
# the axis of draw_a_circles: linear between B and B2, compressed fourfold outside
B, K, B2, K2 = -200.0, 0.25, 1000.0, 0.25


def fwd(x):
    x = np.asarray(x, float)
    return np.where(x < B, B + (x - B) * K, np.where(x > B2, B2 + (x - B2) * K2, x))


def load():
    data = {y: pd.read_csv(BUILD / f"fig4a_all_{y}.csv", index_col=0) for y in YEARS}
    sb = pd.read_csv(W / "2030" / "data" / "security_budget.csv", index_col=0)
    d30 = data[2030]
    imp = sb.import_pct.reindex(d30.index) > 0

    def first(c):
        for y in YEARS:
            dy = data[y]
            if c in dy.index and float(dy.net_usd_t[c]) <= float(dy.p_co2_usd_t[c]):
                return y
        return 9999
    ok = d30.net_usd_t.notna()
    imps = sorted(d30.index[imp & ok], key=lambda c: (first(c), float(d30.net_usd_t[c])))
    exps = sorted(d30.index[~imp & ok], key=lambda c: float(d30.net_usd_t[c]))
    return data, imps, exps, {c: first(c) for c in imps}


def main(stem):
    mpl.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"], "font.size": 5.5,
                         "axes.linewidth": 0.5, "xtick.major.width": 0.5, "pdf.fonttype": 42})
    data, imps, exps, first = load()
    rows = imps + exps                                # top to bottom
    n = len(rows)
    ypos = {c: i for i, c in enumerate(rows)}
    fig = plt.figure(figsize=(183 * MM, 238 * MM))
    gs = fig.add_gridspec(1, 3, wspace=0.07, left=0.13, right=0.905, top=0.955, bottom=0.04)
    xlo, xhi = -950.0, 1200.0
    ticks = [-800, -200, 0, 500, 1000]
    for k, y in enumerate(YEARS):
        ax = fig.add_subplot(gs[0, k])
        d = data[y]
        ax.axvspan(float(fwd(xlo)), 0, color=SHADE, lw=0, zorder=0)
        for b in (B, B2):                            # axis breaks
            ax.axvline(float(fwd(b)), color="#CCCCCC", lw=0.4, ls=(0, (2, 2)), zorder=1)
        for c in rows:
            if c not in d.index:
                continue
            i = ypos[c]
            g, nt, pc = float(d.gross_usd_t[c]), float(d.net_usd_t[c]), float(d.p_co2_usd_t[c])
            gx, nx = float(fwd(np.clip(g, xlo, xhi))), float(fwd(np.clip(nt, xlo, xhi)))
            if c in imps and abs(gx - nx) > 12:
                ax.annotate("", xy=(nx + 6, i), xytext=(gx - 6, i),
                            arrowprops=dict(arrowstyle="-|>", color=SECC, lw=0.6, mutation_scale=4, shrinkA=0, shrinkB=0),
                            zorder=3)
            ax.scatter([gx], [i], s=5.5, facecolor="white", edgecolor=INKC, linewidths=0.5, zorder=4, clip_on=False)
            ax.scatter([nx], [i], s=5.5, color=INKC, lw=0, zorder=5, clip_on=False)
            ax.plot([float(fwd(pc))] * 2, [i - 0.42, i + 0.42], color=MAG, lw=0.8, zorder=6)
            if c in imps and nt <= pc:
                ax.scatter([nx], [i], s=16, facecolor="none", edgecolor=SECC, linewidths=0.6, zorder=7, clip_on=False)
        # group dividers: first justified year, then the exporters
        groups = [first[c] for c in imps] + ["x"] * len(exps)
        for j in range(1, n):
            if groups[j] != groups[j - 1]:
                ax.axhline(j - 0.5, color="#1A1A1A" if groups[j] == "x" else GREYC, lw=0.5,
                           ls=(0, (4, 2)) if groups[j] == "x" else "-", alpha=0.8, zorder=2)
        if k == 2:
            s = 0
            lab = {2030: "Justified\nat 2030\ncosts", 2040: "Justified\nat 2040\ncosts", 2050: "Justified\nat 2050\ncosts",
                   9999: "Not justified\nby 2050", "x": "Net\nexporters"}
            for j in range(1, n + 1):
                if j == n or groups[j] != groups[s]:
                    ax.text(1.03, 1 - ((s + j - 1) / 2 + 0.5) / n, lab[groups[s]] + f"\n({j - s})", transform=ax.transAxes,
                            fontsize=5.8, color=LBL, ha="left", va="center")
                    s = j
        ax.set_ylim(n - 0.5, -0.5)
        ax.set_xlim(float(fwd(xlo)), float(fwd(xhi)))
        ax.set_xticks([float(fwd(t)) for t in ticks])
        ax.set_xticklabels([f"{t:,}".replace("-", "−") for t in ticks], fontsize=5.5)
        ax.set_yticks(range(n))
        if k == 0:
            labs = ax.set_yticklabels([SHORT.get(c, c) for c in rows], fontsize=5.0)
        else:
            ax.set_yticklabels([])
        ax.tick_params(axis="y", length=0, pad=1.5)
        ax.tick_params(axis="x", length=2, pad=1.5)
        ax.grid(axis="x", alpha=0.2, lw=0.4)
        for sp in ("top", "right", "left"):
            ax.spines[sp].set_visible(False)
        ax.set_title(f"{y}", fontsize=7.5, fontweight="bold", pad=3)
        if k == 1:
            ax.set_xlabel("Abatement cost (US\\$ tCO$_2^{-1}$)", fontsize=6.5, labelpad=2)
    ha = [Line2D([], [], marker="o", ls="none", ms=3.5, mfc="white", mec=INKC, label="Cost premium"),
          Line2D([], [], marker="o", ls="none", ms=3.5, color=INKC, label="Net premium"),
          Line2D([], [], color=SECC, lw=1.0, marker="<", ms=3, markevery=[0], label="Security margin"),
          Line2D([], [], marker="|", ls="none", ms=7, mew=1.0, color=MAG, label="Carbon price"),
          Line2D([], [], marker="o", ls="none", ms=5.5, mfc="none", mec=SECC, mew=0.9, label="Justified")]
    fig.legend(handles=ha, loc="lower center", bbox_to_anchor=(0.52, 0.968), ncol=5, fontsize=6.3, frameon=False,
               handlelength=1.2, handletextpad=0.4, columnspacing=1.0)
    out = Path(stem)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out.with_suffix(".pdf"))
    fig.savefig(out.with_suffix(".png"), dpi=300)
    plt.close(fig)
    print(f"saved {out}.(pdf|png): {len(imps)} importers, {len(exps)} exporters; justified by year",
          {y: sum(1 for c in imps if first[c] == y) for y in (2030, 2040, 2050, 9999)})


def main_compact(stem):
    """2030 marks for every economy in two side-by-side blocks, with the 2040 and 2050 net premiums as
    lighter dots on the same row, so 139 economies fit one page at >= 5 pt."""
    mpl.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"], "font.size": 5.5,
                         "axes.linewidth": 0.5, "xtick.major.width": 0.5, "pdf.fonttype": 42})
    data, imps, exps, first = load()
    rows = imps + exps
    n = len(rows)
    half = int(np.ceil(n / 2))
    blocks = [rows[:half], rows[half:]]
    groups = {c: first.get(c, "x") for c in rows}
    d30, d40, d50 = data[2030], data[2040], data[2050]
    C40, C50 = "#5B8FD0", "#A9C6EA"
    xlo, xhi = -950.0, 1200.0
    ticks = [-800, -200, 0, 500, 1000]
    fig = plt.figure(figsize=(183 * MM, 197 * MM))
    gs = fig.add_gridspec(1, 2, wspace=0.50, left=0.115, right=0.895, top=0.95, bottom=0.05)
    lab = {2030: "Justified at 2030 costs", 2040: "Justified at 2040 costs", 2050: "Justified at 2050 costs",
           9999: "Not justified by 2050", "x": "Net exporters"}
    for k, blk in enumerate(blocks):
        ax = fig.add_subplot(gs[0, k])
        ax.axvspan(float(fwd(xlo)), 0, color=SHADE, lw=0, zorder=0)
        for b in (B, B2):
            ax.axvline(float(fwd(b)), color="#CCCCCC", lw=0.4, ls=(0, (2, 2)), zorder=1)
        for i, c in enumerate(blk):
            g, nt, pc = (float(d30.gross_usd_t[c]), float(d30.net_usd_t[c]), float(d30.p_co2_usd_t[c]))
            gx, nx = float(fwd(np.clip(g, xlo, xhi))), float(fwd(np.clip(nt, xlo, xhi)))
            imp = c in imps
            if imp and abs(gx - nx) > 12:
                ax.annotate("", xy=(nx + 7, i), xytext=(gx - 7, i),
                            arrowprops=dict(arrowstyle="-|>", color=SECC, lw=0.6, mutation_scale=4, shrinkA=0, shrinkB=0), zorder=3)
            for dd, col in ((d40, C40), (d50, C50)):
                if c in dd.index and np.isfinite(dd.net_usd_t[c]):
                    ax.scatter([float(fwd(np.clip(dd.net_usd_t[c], xlo, xhi)))], [i], s=5, color=col, lw=0, zorder=4)
            ax.scatter([gx], [i], s=9, facecolor="white", edgecolor=INKC, linewidths=0.6, zorder=5, clip_on=False)
            ax.scatter([nx], [i], s=9, color=INKC, lw=0, zorder=6, clip_on=False)
            ax.plot([float(fwd(pc))] * 2, [i - 0.4, i + 0.4], color=MAG, lw=0.9, zorder=7)
            if imp and nt <= pc:
                ax.scatter([nx], [i], s=26, facecolor="none", edgecolor=SECC, linewidths=0.7, zorder=8, clip_on=False)
        gl = [groups[c] for c in blk]
        s = 0
        for j in range(1, len(blk) + 1):
            if j < len(blk) and gl[j] != gl[j - 1]:
                ax.axhline(j - 0.5, color="#1A1A1A" if gl[j] == "x" else GREYC, lw=0.5,
                           ls=(0, (4, 2)) if gl[j] == "x" else "-", alpha=0.8, zorder=2)
            if j == len(blk) or gl[j] != gl[s]:
                cnt = sum(1 for c in rows if groups[c] == gl[s])
                ax.text(1.02, 1 - ((s + j - 1) / 2 + 0.5) / len(blk), lab[gl[s]].replace(" by", "\nby").replace(" at", "\nat")
                        + f" ({cnt})", transform=ax.transAxes, fontsize=5.6, color=LBL, ha="left", va="center")
                s = j
        ax.set_ylim(len(blk) - 0.5, -0.5)
        ax.set_xlim(float(fwd(xlo)), float(fwd(xhi)))
        ax.set_xticks([float(fwd(t)) for t in ticks])
        ax.set_xticklabels([f"{t:,}".replace("-", "−") for t in ticks], fontsize=5.6)
        ax.set_yticks(range(len(blk)))
        ax.set_yticklabels([SHORT.get(c, c) for c in blk], fontsize=5.5)
        ax.tick_params(axis="y", length=0, pad=1.5)
        ax.tick_params(axis="x", length=2, pad=1.5)
        ax.grid(axis="x", alpha=0.2, lw=0.4)
        for sp in ("top", "right", "left"):
            ax.spines[sp].set_visible(False)
        ax.set_xlabel("Abatement cost (US\\$ tCO$_2^{-1}$)", fontsize=6.3, labelpad=2)
    ha = [Line2D([], [], marker="o", ls="none", ms=3.8, mfc="white", mec=INKC, label="Cost premium, 2030"),
          Line2D([], [], marker="o", ls="none", ms=3.8, color=INKC, label="Net premium, 2030"),
          Line2D([], [], marker="o", ls="none", ms=3.2, color=C40, label="2040"),
          Line2D([], [], marker="o", ls="none", ms=3.2, color=C50, label="2050"),
          Line2D([], [], color=SECC, lw=1.0, marker="<", ms=3, markevery=[0], label="Security margin"),
          Line2D([], [], marker="|", ls="none", ms=7, mew=1.0, color=MAG, label="Carbon price"),
          Line2D([], [], marker="o", ls="none", ms=5.5, mfc="none", mec=SECC, mew=0.9, label="Justified (2030)")]
    fig.legend(handles=ha, loc="lower center", bbox_to_anchor=(0.52, 0.958), ncol=7, fontsize=6.0, frameon=False,
               handlelength=1.1, handletextpad=0.3, columnspacing=0.8)
    out = Path(stem)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out.with_suffix(".pdf"))
    fig.savefig(out.with_suffix(".png"), dpi=300)
    plt.close(fig)
    print(f"saved {out}.(pdf|png) compact: {len(imps)} importers, {len(exps)} exporters")


if __name__ == "__main__":
    (main_compact if len(sys.argv) > 2 and sys.argv[2] == "compact" else main)(sys.argv[1])
