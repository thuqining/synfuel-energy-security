"""
fig5_years.py — Figure 5 (what 1-3 % of GDP buys) for several build years, stacked
vertically (2026-10-08), from the lowest-cost sandboxes of lcof.case_low.

From scripts/:  python -m lcof.fig5_years <out_stem> 2030=<workdir> 2040=<workdir> ...
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

mpl.use("Agg")

from . import inputs
from . import case_low as C
from .fig_main_cost import MM, NAT_RC

mpl.rcParams.update(NAT_RC)
FOOT = "* no net-trade record"


def main(stem, *pairs):
    works = {int(a.split("=", 1)[0]): a.split("=", 1)[1] for a in pairs}
    from . import security_budget as SB
    from .coreset import core_countries
    n = len(works)
    # Nature's full page: 183 mm wide, at most ~240 mm tall. Up to three build years stacked;
    # four (2025-2050, 2026-10-08) as a 2 x 2 grid, each panel with its own country labels
    grid = n == 4
    if grid:
        fig, axs = plt.subplots(2, 2, figsize=(183 * MM, 225 * MM))
        fig.subplots_adjust(left=0.105, right=0.925, top=0.925, bottom=0.06, hspace=0.13, wspace=0.62)
        axes = list(axs.ravel())
    else:
        # 2026-10-08: 220 mm tall fills the page with its caption, so the 5-7 pt text is not shrunk
        fig, axes = plt.subplots(n, 1, figsize=(183 * MM, min(220.0, 84.0 * n) * MM))
        fig.subplots_adjust(left=0.15, right=0.88, top=0.965, bottom=0.05, hspace=0.12)
        axes = [axes] if n == 1 else list(axes)
    for k, (y, w) in enumerate(works.items()):
        inputs.MAPS = Path(w) / "data"
        C.apply_params(y)
        df, curves = SB.compute(write=False)
        core = [c for c in core_countries(df.index) if c in df.index]
        d = df.loc[core]
        ax = axes[k]
        SB._figure(d, curves, ax=ax, legend=(k == 0))
        ax.tick_params(axis="y", labelsize=5.6, length=0, pad=2)
        if grid:
            ax.tick_params(axis="x", labelsize=6)
            for t in ax.texts:                    # group names a touch smaller in the narrow panels
                if t.get_fontweight() == "bold":
                    t.set_fontsize(6)
        for t in list(ax.texts):                     # the footnote once, under the last panel
            if t.get_text().startswith(FOOT):
                if grid:                             # 2 x 2: once, bottom left of the figure
                    foot = t.get_text()
                    t.remove()
                elif k < n - 1:
                    t.remove()
                else:
                    t.set_position((0.0, -0.16))
        if grid and k == 0:                          # the key centred above both columns
            leg = ax.get_legend()
            leg.set_bbox_to_anchor((0.5, 0.995), transform=fig.transFigure)
            leg._loc = 9
        last_row = k >= n - 2 if grid else k == n - 1
        if not last_row:
            ax.set_xlabel("")
            ax.tick_params(axis="x", labelbottom=False)
        elif grid:
            ax.xaxis.label.set_fontsize(6.5)
        print(f"{y}: 1% of GDP buys a median {d.cov_1.median():.0%} of fuel demand; imports covered at "
              f"1/2/3%: {int(((d.import_pct > 0) & (d.ret_sf_1 >= 0.995)).sum())}/"
              f"{int(((d.import_pct > 0) & (d.ret_sf_2 >= 0.995)).sum())}/"
              f"{int(((d.import_pct > 0) & (d.ret_sf_3 >= 0.995)).sum())}", flush=True)
    for k, (ax, y) in enumerate(zip(axes, works)):
        x0 = 0.005 if not grid or k % 2 == 0 else ax.get_position().x0 - 0.10
        fig.text(x0, ax.get_position().y1 + 0.004, f"{'abcd'[k]}   {y}", fontsize=8,
                 fontweight="bold", va="bottom")
    if grid:
        fig.text(0.005, 0.008, foot, fontsize=6, color="#555555", ha="left", va="bottom")
    out = Path(stem)
    fig.savefig(out.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(out.with_suffix(".png"), dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {out}.(pdf|png)")


if __name__ == "__main__":
    main(*sys.argv[1:])
