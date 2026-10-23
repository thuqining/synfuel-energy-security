"""
fig4b_only.py — row b of Fig. 4 (abatement-cost curves cut at zero, 2030 / 2040 / 2050) as its own figure
(2026-10-21), now that Fig. 4a covers 139 economies and fills a page. Same data, axes and marks as
fig4_years row b (fig5_chain._curve_to_zero), one shared vertical range and region key on top.

From scripts/:  python -m lcof.fig4b_only <out stem> 2030=<workdir> 2040=<workdir> 2050=<workdir>
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

mpl.use("Agg")

from . import inputs
from . import fig5_chain as F5
from .fig_main_cost import MM, NAT_RC
from .global_trajectory import REGION_COL
from .fig4_years import year_data, b_axes

mpl.rcParams.update(NAT_RC)


def main(stem, *pairs, height_mm=80.0, fig=None):
    works = {int(a.split("=", 1)[0]): a.split("=", 1)[1] for a in pairs}
    cols = list(works)
    data = {y: year_data(y, w) for y, w in works.items()}
    bax = {}
    for y in cols:
        xb, yb, kb, tb = b_axes(data[y][1], y)
        F5._SQZ2.pop(y, None)                   # no compression left over from an earlier call
        # 2026-10-22 (user): every panel leaves at least 40% of its width to the cost-only group and 36% to
        # the dearer demand right of the dashed line, so the two-line names fit; the security-only group
        # is compressed only where it must be (2030)
        tt = data[y][2].set_index("year")
        zs, zc = float(tt.sec_gt[y]), float(tt.cost_gt[y])
        FC, FR = 0.40, 0.36
        W0 = zs + (xb - zs) / kb
        if zc > 0 and (zc / W0 < FC or (xb - zs) / kb / W0 < FR):
            W = zc / FC
            k2 = (zs - zc) / ((1 - FC - FR) * W)
            if k2 < 1.0:                        # the security-only group fits uncompressed
                k2, W = 1.0, zs / (1 - FR)
            # 2026-10-22: whole-number factors, so the "k×" on the axis is exact; rounded up for the security
            # group and down right of the dashed line, so the two outer groups keep at least their share
            k2 = float(np.ceil(k2 - 1e-9))
            W = (zc + (zs - zc) / k2) / (1 - FR)
            kb = max(1.0, float(np.floor((xb - zs) / (FR * W) + 1e-9)))
            W = zc + (zs - zc) / k2 + (xb - zs) / kb
            F5._SQZ2[y] = k2
            fwd = lambda v: v if v <= zc else (zc + (v - zc) / k2 if v <= zs else zc + (zs - zc) / k2 + (v - zs) / kb)
            keep, last = [], -1.0
            for v in [v for v in tb if v <= zc + 1e-9 or v > zs or k2 == 1.0]:
                if fwd(v) - last > 0.07 * W:
                    keep.append(v)
                    last = fwd(v)
            tb = keep
        F5._XT[y], F5._SQZ[y] = tb, kb
        bax[y] = (xb, yb)
    y_common = min(v[1] for v in bax.values())
    # 2026-10-21: fig may be a SubFigure (lcof.fig4_combo draws a over b on one page); then nothing is saved
    own = fig is None
    if own:
        fig = plt.figure(figsize=(183 * MM, height_mm * MM))
    short = height_mm < 70                                # 2026-10-21: a strip under the 139-economy Fig. 4a
    gb = fig.add_gridspec(1, len(cols), wspace=0.30, left=0.09, right=0.99,   # 2026-10-22: y title inside the page
                          top=1 - 9.5 / height_mm, bottom=10.0 / height_mm)
    present, bs = set(), []
    for k, y in enumerate(cols):
        d, p, tj = data[y]
        inputs.MAPS = Path(works[y]) / "data"
        b = fig.add_subplot(gb[0, k])
        present |= F5._curve_to_zero(b, p, y, dict(REGION_COL), tj, xmax=bax[y][0], ylo=y_common, inside=True,
                                     totals_low=short)
        b.set_yticks(np.arange(y_common, 300 + 1, 200 if short else 100))
        b.set_title(f"{y}", fontsize=7, fontweight="bold", pad=2 if short else 4)
        if k:
            b.set_ylabel("")
        elif short:
            b.set_ylabel("Abatement cost" + chr(10) + r"(US\$ tCO$_2^{-1}$)", fontsize=7, labelpad=2)
        if k == len(cols) // 2:
            b.set_xlabel("Cumulative CO$_2$ displaced (Gt yr$^{-1}$)", fontsize=7)
        bs.append(b)
    names = [r for r in REGION_COL if r in present]
    nick = {"Rest of Asia and Oceania": "Rest of Asia & Oceania", "China": "China (Mainland)"}
    fig.legend([Rectangle((0, 0), 1, 1, fc=REGION_COL[r]) for r in names], [nick.get(r, r) for r in names],
               fontsize=7, frameon=False, ncol=len(names), loc="upper center", bbox_to_anchor=(0.53, 1.0),
               handlelength=1.1, columnspacing=1.0, borderaxespad=0.2)
    if not own:
        return
    from lcof.figcheck import report
    report(fig, Path(stem).name)
    out = Path(stem)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out.with_suffix(".pdf"))
    fig.savefig(out.with_suffix(".png"), dpi=300)
    plt.close(fig)
    print(f"saved {out}.(pdf|png): {height_mm} mm")


if __name__ == "__main__":
    main(*sys.argv[1:])
