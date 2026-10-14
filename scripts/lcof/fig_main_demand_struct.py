"""
fig_main_demand_struct.py — the demand side, economy by economy: what
each core-30 addressable fossil-fuel bill is actually made of, fuel by
fuel, and how big it is.

The demand map (fig_main_demand_fuel) shows WHERE demand sits on the
grid; this figure shows WHAT it is per economy — the composition that
drives everything downstream: the gas-family weight of the import
exposure, the hydrogen intensity of the bill, and why ammonia is the
first tranche while e-methane is about a quarter of the market.

One row per core economy, stacked to 100% of the addressable bill,
sorted by bill size; the right block adds the PROJECTION: a 2025-2050
strip per economy showing the share of its bill that is
security-rational by each build year (fuel-resolved parity from
global_trajectory_countries.csv, ENTSOG anchor), then the bill size
(EJ of final fuel per year). Hatching marks the part of each fuel segment
that is net-imported today (gas-family segments at the country's gas
dependence, oil-family at its oil dependence — the same OWID/EI layer
as the budget figure), so the figure shows composition, size AND the
exposure the later figures price. Shares are a 2025 snapshot (EDGAR
sectoral map at UN/Energy Institute national levels, mapped fuel by
fuel), not an average.
Same fuel palette as the demand map, same type chips as the sites
figure.

From scripts/:  conda run -n synfuel python -u -m lcof.fig_main_demand_struct
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from . import inputs
from .coreset import CORE30_LIST, CORE30_TYPE
from .fig_main_cost import MM, NAT_RC, FUELS, FCOL, DEMAND_LABEL
from .params import MMBTU_PER_GJ as MMB
from .fig_pptx_pairs import OUT

SHORT = {"United States of America": "United States",
         "Dominican Republic": "Dominican Rep."}
TYPE_COL = {"large consumer": "#111111",
            "industrial importer": "#D55E00",
            "emerging importer": "#E69F00",
            "island state": "#56B4E9",
            "resource-rich builder": "#009E73"}


def main(*, write_data=True):
    plt.rcParams.update(NAT_RC)
    meta = inputs.load_meta(2025)
    dg = pd.read_csv(inputs.MAPS / "demand_fuel_grid.csv", index_col=0)
    cols = [f + "_gj" for f in FUELS]
    d = (dg[cols].join(meta[["country"]]).groupby("country")[cols].sum()
         .reindex(CORE30_LIST))
    tot = d.sum(axis=1)
    sh = d.div(tot, axis=0) * 100
    ex = list(tot.sort_values().index)          # drawn bottom -> top
    # net import dependence per fuel family (OWID/EI, the budget
    # figure's layer): gas family = e-methane/ammonia/methanol,
    # oil family = e-diesel/e-kerosene/ethanol
    from .security_budget import family_dependence
    dep_gas, dep_oil = family_dependence(CORE30_LIST)
    GASF = {"e-methane", "ammonia", "methanol"}
    dep = {f: (dep_gas if f in GASF else dep_oil).fillna(0.0)
           for f in FUELS}

    n = len(ex)
    fig, ax = plt.subplots(figsize=(183 * MM, 128 * MM))
    fig.subplots_adjust(left=0.145, right=0.985, top=0.925, bottom=0.075)
    # projection strip data: share of each bill security-rational by
    # build year t (fuel-resolved parity years, ENTSOG anchor);
    # (country, fuel) pairs without a comparator count as not rational
    # by 2050 — conservative
    gt = pd.read_csv(inputs.MAPS / "global_trajectory_countries.csv")
    vy = np.arange(2025, 2051)
    frac = {}
    for c in CORE30_LIST:
        g = gt[gt.country == c]
        tot_c = float(tot.get(c, np.nan))
        if len(g) == 0 or not np.isfinite(tot_c) or tot_c <= 0:
            frac[c] = np.full(len(vy), np.nan)
            continue
        # chain basis, as in Fig. 5b: a pair's net imports clear at its
        # security year, the rest of its demand only at cost parity
        dom = (g.dem_gj - g.imp_gj).clip(lower=0)
        frac[c] = np.array([(g.imp_gj[g.sec_imp <= t].sum()
                             + dom[g.cost_rest <= t].sum()) / tot_c for t in vy])

    ys = np.arange(n)
    left = np.zeros(n)
    plt.rcParams["hatch.linewidth"] = 0.6
    for f in FUELS:
        v = sh.loc[ex, f + "_gj"].to_numpy()
        ax.barh(ys, v, left=left, height=0.66, color=FCOL[f],
                zorder=2, label=DEMAND_LABEL[f])
        # the net-imported slice of this segment, hatched
        vi = v * dep[f].reindex(ex).to_numpy()
        ax.barh(ys, vi, left=left, height=0.66, color="none",
                edgecolor=(1, 1, 1, 0.75), hatch="//////", lw=0.0,
                zorder=3)
        left += v
    # the projection strip has been removed: this figure reports what
    # is observed today, and the build-year claim it used to carry is
    # made by the parity clock, after the security ledger is defined.
    # Set STRIP = True (or pass --strip) to draw it again.
    for i, c in enumerate(ex):
        # no type chips here: the type palette collided with the fuel
        # palette (both Okabe-Ito); types are shown in the sites figure
        t = tot[c] / 1e9 / MMB          # EJ -> billion MMBtu per year
        ax.text(112.0, i, f"{t:.2f}" if t < 0.1 else f"{t:.1f}",
                fontsize=7.5, va="center", ha="right", color="#333333")
    # a numeric column reads best right-aligned, decimals under
    # decimals, with the header right-aligned on the same edge
    for ly, txt in ((n + 1.6, "demand,"), (n + 0.6, "bn MMBtu/yr")):
        ax.text(112.0, ly, txt, fontsize=7.0, ha="right", va="top",
                color="#333333", fontweight="bold")

    ax.set_yticks(ys)
    ax.set_yticklabels([SHORT.get(c, c) for c in ex], fontsize=8)
    ax.set_xlim(0, 118)
    ax.set_ylim(-0.9, n + 1.9)
    ax.set_xticks(np.arange(0, 101, 20))
    ax.set_xlabel("share of addressable fuel demand (energy), %")
    ax.tick_params(axis="y", pad=9)
    import matplotlib.patches as mp
    # incumbent fuel on the first line, its synthetic substitute below
    leg = ax.legend(handles=[mp.Patch(color=FCOL[f], label=DEMAND_LABEL[f].replace(" (", "\n("))
                       for f in FUELS]
              # one key for the hatching: the solid remainder of every
              # segment is domestic fossil supply, not a separate fuel
              + [mp.Patch(fc="#9AA3AC", ec=(1, 1, 1, 0.85), hatch="//////",
                          lw=0, label="imported share")],
              fontsize=8, frameon=False, loc="lower left",
              bbox_to_anchor=(-0.01, 1.005), ncol=7, handlelength=0.9,
              columnspacing=0.6, borderaxespad=0.0)
    for txt in leg.get_texts():          # the bracketed line centred under the fuel
        txt.set_multialignment("center")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_bounds(-0.5, n - 0.5)
    ax.grid(axis="x", alpha=0.20, lw=0.4)
    ax.set_axisbelow(True)

    out = sh.loc[ex[::-1]].round(2)
    out["total_EJ"] = (tot[ex[::-1]] / 1e9).round(3)
    out["total_bn_MMBtu"] = (tot[ex[::-1]] / 1e9 / MMB).round(3)
    if write_data:
        out.to_csv(inputs.MAPS / "core30_demand_struct.csv")
    fig.savefig(OUT / "fig_main_demand_struct.pdf", bbox_inches="tight")
    fig.savefig(OUT / "fig_main_demand_struct.png", dpi=600,
                bbox_inches="tight")
    plt.close(fig)
    gas = sh["e-methane_gj"]
    print(f"saved fig_main_demand_struct.(pdf|png), {n} economies; "
          f"e-methane share median {gas.median():.0f}% "
          f"(min {gas.min():.0f} {gas.idxmin()}, max {gas.max():.0f} "
          f"{gas.idxmax()}); bills {tot.min()/1e9/MMB:.2f}-"
          f"{tot.max()/1e9/MMB:.1f} bn MMBtu/yr "
          f"({tot.min()/1e9:.2f}-{tot.max()/1e9:.1f} EJ/yr)")


if __name__ == "__main__":
    main()
