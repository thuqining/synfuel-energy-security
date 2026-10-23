"""
fig4_combo.py — Fig. 4 on one page (2026-10-21): a, the 1%-of-GDP portfolio per tonne for 139 economies and three
cost years (lcof.fig4a_cols); b, the abatement-cost curves cut at zero (lcof.fig4b_only, short form). Both drawn as
subfigures of one 183 mm wide figure, so the manuscript includes a single file.

From scripts/:  python -m lcof.fig4_combo <out stem> 2030=<workdir> 2040=<workdir> 2050=<workdir> [a_mm] [b_mm]
"""
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

mpl.use("Agg")

from lcof import fig4a_cols, fig4b_only
from lcof.fig_main_cost import MM
from lcof.figcheck import report


def main(stem, pairs, a_mm=118.0, b_mm=48.0):
    fig = plt.figure(figsize=(183 * MM, (a_mm + b_mm) * MM))
    sa, sb = fig.subfigures(2, 1, height_ratios=[a_mm, b_mm], hspace=0)
    fig4a_cols.main(stem, a_mm, fig=sa)
    fig4b_only.main(stem, *pairs, height_mm=b_mm, fig=sb)
    for s, letter, mm in ((sa, "a", a_mm), (sb, "b", b_mm)):
        s.text(0.004, 1 - 1.2 / mm, letter, fontsize=8, fontweight="bold", ha="left", va="top")
    report(fig, Path(stem).name)
    out = Path(stem)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out.with_suffix(".pdf"))
    fig.savefig(out.with_suffix(".png"), dpi=300)
    plt.close(fig)
    print(f"saved {out}.(pdf|png): {a_mm} + {b_mm} mm")


if __name__ == "__main__":
    args = sys.argv[1:]
    pairs = [a for a in args[1:] if "=" in a]
    nums = [float(a) for a in args[1:] if "=" not in a]
    main(args[0], pairs, *nums)
