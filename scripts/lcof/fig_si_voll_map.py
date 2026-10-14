"""
fig_si_voll_map.py - Supplementary figure (Note 4): the value of fuel lost,
v_c, in the higher (reference) case that Fig. 4 uses, for every economy
with data (2026-10-05; replaces the September draft fig_security_codf.png,
which showed the central case in $/GJ).

v_c is proportional to GDP per unit of national fuel use and is scaled so
that the European median equals the ENTSOG planning value, US$175 per GJ
(security.py, column codf_hi_usd_gj of security_index.csv). Shown in US$ per
MMBtu, the paper's unit, in green, the paper's colour for security value.

From scripts/:  python -u -m lcof.fig_si_voll_map
Writes cf_global_final/figures/pptx/fig_si_voll_map.(pdf|png).
"""
from __future__ import annotations

import geopandas as gpd
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

mpl.use("Agg")

from . import inputs, params as P
from .fig_main_cost import MM, NAT_RC
from .fig_pptx_pairs import OUT

mpl.rcParams.update(NAT_RC)
mpl.rcParams.update({"pdf.fonttype": 42})

BINS = [0, 50, 100, 150, 200, 300, 650]          # US$ per MMBtu (2026-10-09: Ireland 603)
NODATA = "#E4E6E9"


def main():
    si = pd.read_csv(inputs.MAPS / "security_index.csv", index_col=0)
    v = (si.codf_hi_usd_gj * P.MMBTU_PER_GJ).dropna()
    assert v.max() < BINS[-1]
    ne = gpd.read_file(inputs.PROJECT / "cf_global_final" / "data" / "grid" / "naturalearth" /
                       "ne_10m_admin_0_countries.shp")[["ADMIN", "geometry"]]
    ne = ne[ne.ADMIN != "Antarctica"]
    missing = sorted(set(v.index) - set(ne.ADMIN))
    assert not missing, missing
    m = ne.merge(v.rename("v"), left_on="ADMIN", right_index=True, how="left")

    cmap = mpl.colors.ListedColormap(mpl.colormaps["Greens"](np.linspace(0.15, 0.95, len(BINS) - 1)))
    norm = mpl.colors.BoundaryNorm(BINS, cmap.N)

    fig, ax = plt.subplots(figsize=(183 * MM, 86 * MM))
    fig.subplots_adjust(left=0.005, right=0.995, top=0.995, bottom=0.005)
    m[m.v.isna()].plot(ax=ax, color=NODATA, linewidth=0)
    m[m.v.notna()].plot(ax=ax, column="v", cmap=cmap, norm=norm, linewidth=0)
    ne.boundary.plot(ax=ax, color="#5A6570", linewidth=0.12)
    ax.set_xlim(-180, 180)
    ax.set_ylim(-58, 84)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect("equal")
    for s in ax.spines.values():
        s.set_visible(False)

    # a stepped key on the open Pacific, as in Fig. 2
    cax = fig.add_axes([0.06, 0.24, 0.20, 0.032])
    cb = fig.colorbar(mpl.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax, orientation="horizontal",
                      ticks=BINS, spacing="uniform")
    cb.ax.set_xticklabels([f"{b:,}" for b in BINS], fontsize=6.5)
    cb.ax.tick_params(length=2, width=0.5)
    cb.outline.set_linewidth(0.5)
    cb.ax.set_title("Value of fuel lost (US\\$ MMBtu$^{-1}$)", fontsize=7, pad=3)
    fig.text(0.06, 0.17, "No data", fontsize=6.5, va="center", ha="left", color="#3A4550",
             transform=fig.transFigure)
    fig.patches.append(mpl.patches.Rectangle((0.035, 0.158), 0.018, 0.024, transform=fig.transFigure,
                                             fc=NODATA, ec="#5A6570", lw=0.3))

    fig.savefig(OUT / "fig_si_voll_map.pdf", bbox_inches="tight")
    fig.savefig(OUT / "fig_si_voll_map.png", dpi=600, bbox_inches="tight")
    plt.close(fig)
    eu = ("Germany", "France", "Italy", "Spain", "Netherlands", "Belgium", "Poland", "Austria", "Portugal",
          "Greece", "Hungary", "Czechia", "Slovakia", "Lithuania", "Latvia", "Estonia", "Croatia", "Slovenia",
          "Ireland", "Finland", "Sweden", "Denmark", "Romania", "Bulgaria")
    eu_med = float(v.reindex([c for c in eu if c in v.index]).median())
    print(f"saved fig_si_voll_map.(pdf|png): {len(v)} economies; median US${v.median():.0f}/MMBtu "
          f"(p10-p90 {v.quantile(.1):.0f}-{v.quantile(.9):.0f}), European median {eu_med:.0f}; "
          f"highest: " + ", ".join(f"{c} {x:.0f}" for c, x in v.nlargest(6).items())
          + "; lowest: " + ", ".join(f"{c} {x:.0f}" for c, x in v.nsmallest(4).items()))
    for b0, b1 in zip(BINS[:-1], BINS[1:]):
        print(f"    {b0:>3}-{b1:<3}: {int(((v >= b0) & (v < b1)).sum())}")


if __name__ == "__main__":
    main()
