"""
fig4_core.py — Fig. 4 for the main text (2026-10-21): a, the 1%-of-GDP portfolio per tonne for the 30 core economies
at 2030, 2040 and 2050 costs (lcof.fig4a_cols, one row); b, a world map of all 139 economies coloured by the first
cost year in which the portfolio is justified (no outline for the core economies); c, the abatement-cost curves cut at zero
(lcof.fig4b_only, short form). The full 139-economy version of a goes to the Supplementary Information.

From scripts/:  python -m lcof.fig4_core <out stem> 2030=<workdir> 2040=<workdir> 2050=<workdir> [a_mm b_mm c_mm]
"""
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Patch

mpl.use("Agg")

from lcof import fig4a_cols, fig4b_only, inputs
from lcof.fig4a_all import load
from lcof.fig_main_cost import MM
from lcof.figcheck import report

R = Path(__file__).resolve().parents[2]
# 2026-10-21: in the style of Fig. 2 (fig_sd_map): its no-data gray, mid-gray 0.1 pt borders and map extent; justified
# years in muted greens (green = justified/security throughout Fig. 4), exporters in Fig. 2's sand tone
# 2026-10-22: five classes, the three cost years in the blues of a, not justified, net exporters
CAT_C = {2030: "#253494", 2040: "#2C7FB8", 2050: "#41B6C4", 9999: "#D9D9D9", "x": "#DDB967"}   # years: blues of a
CAT_L = {2030: "Justified at 2030 costs", 2040: "Justified at 2040 costs", 2050: "Justified at 2050 costs",
         9999: "Not justified by 2050", "x": "Net exporters"}
NODATA = "#D5D5D5"


def core30():
    return list(pd.read_csv(R / "work/caselow/2030/data/fig5a_chain.csv", index_col=0).index)


def draw_map(sf):
    data, imps, exps, first = load()
    cat = {c: first.get(c, 9999) for c in imps}
    cat.update({c: "x" for c in exps})
    ne = gpd.read_file(inputs.PROJECT / "data" / "grid" / "naturalearth" / "ne_10m_admin_0_countries.shp")[
        ["ADMIN", "geometry"]]
    ne = ne[ne.ADMIN != "Antarctica"]
    # 2026-10-22: borders simplified to 0.05 degrees (about 5 km), invisible at print size; keeps the PDF small
    ne["geometry"] = ne.geometry.simplify(0.05, preserve_topology=True)
    missing = sorted(set(cat) - set(ne.ADMIN))
    assert not missing, missing
    ne["cat"] = ne.ADMIN.map(cat)
    ax = sf.add_axes([0.0, 0.0, 1.0, 1.0])          # 2026-10-21: full width, as Fig. 2
    # 2026-10-21: regions outside the 139 modelled economies are left blank (borders only)
    for k, col in CAT_C.items():
        sub = ne[ne.cat == k]
        if len(sub):
            sub.plot(ax=ax, color=col, linewidth=0)
    ne.boundary.plot(ax=ax, color="0.4", linewidth=0.1)
    ax.set_xlim(-180, 180)
    ax.set_ylim(-58, 84)
    ax.set_aspect("equal")
    ax.axis("off")
    counts = pd.Series(cat).value_counts()
    hd = [Patch(fc=CAT_C[k], ec="none", label=f"{CAT_L[k]} ({int(counts.get(k, 0))})") for k in CAT_C]
    # key on the open South Pacific at the lower left, next to the map, as the key of Fig. 2
    ax.legend(handles=hd, loc="lower left", bbox_to_anchor=(0.005, 0.03), fontsize=7.0, frameon=False,
              handlelength=1.5, handleheight=1.0, labelspacing=0.45, borderaxespad=0.0, alignment="left")


def main(stem, pairs, a_mm=74.0, b_mm=60.0, c_mm=50.0):
    # 2026-10-22: c_mm = 0 leaves out the abatement-cost curves, now a figure of their own (lcof.fig_macc)
    fig = plt.figure(figsize=(183 * MM, (a_mm + b_mm + c_mm) * MM))
    if c_mm > 0:
        sa, sb, sc = fig.subfigures(3, 1, height_ratios=[a_mm, b_mm, c_mm], hspace=0)
    else:
        sa, sb = fig.subfigures(2, 1, height_ratios=[a_mm, b_mm], hspace=0)
    fig4a_cols.main(stem, a_mm, fig=sa, subset=set(core30()))
    draw_map(sb)
    if c_mm > 0:
        fig4b_only.main(stem, *pairs, height_mm=c_mm, fig=sc)
    for s, letter, mm in ((sa, "a", a_mm), (sb, "b", b_mm)) + (((sc, "c", c_mm),) if c_mm > 0 else ()):
        s.text(0.004, 1 - 1.2 / mm, letter, fontsize=8, fontweight="bold", ha="left", va="top")
    report(fig, Path(stem).name)
    out = Path(stem)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out.with_suffix(".pdf"))
    fig.savefig(out.with_suffix(".png"), dpi=300)
    plt.close(fig)
    print(f"saved {out}.(pdf|png): {a_mm} + {b_mm} + {c_mm} mm")


if __name__ == "__main__":
    args = sys.argv[1:]
    pairs = [a for a in args[1:] if "=" in a]
    nums = [float(a) for a in args[1:] if "=" not in a]
    main(args[0], pairs, *nums)
