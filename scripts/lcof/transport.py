"""
transport.py — would a demand cell rather buy fuel from a cheaper cell and
pay for transport?  (2026-09-24: Fig. 2 compares cost and demand
cell by cell; this is the global check that local production is not
beaten by moving fuel from cheaper land.)

Cost basis = Fig. 2 exactly: each cell's levelized cost of the fuels its
own market needs (median weather year, CO2 at the cell's cheapest source),
weighted by that market's fuel mix. For destination i and source j,

    delivered_ij = sum_f w_if L_jf + [j != i] (T0 + t * d_ij / 1000)

with w_if the fuel shares of i's demand, L_jf the source's levelized cost
of fuel f, d_ij the great-circle distance (km), T0 a fixed handling and
terminal charge and t the variable transport cost ($/GJ per 1000 km).
T0 = $1/GJ (the adder Fig. 3 uses); t = 0.5, 1 (central), 2. For scale:
long-haul tankers move ammonia and methanol ~12,000 km for ~$0.7-1.1/GJ,
so t = 1 is an overland (pipeline, rail) rate rather than a sea rate.

Three sourcing rules:
  local        Fig. 2 as drawn (every cell makes its own fuel)
  domestic     cheapest source within the same country, no capacity limit
  open         cheapest source anywhere, no capacity limit
  open-capped  cheapest sources anywhere, but a source can only export the
               land-limited hydrogen it does not need for its own market
               (linear programme; local production stays available at the
               local cost, as in Fig. 2)

Outputs data/cost/transport_delivered.csv (cell level, central case),
data/cost/transport_summary.csv (all cases) and
cf_global_final/figures/pptx/fig_transport.(pdf|png).

From scripts/:  conda run -n synfuel python -u -m lcof.transport
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from scipy import sparse
from scipy.optimize import linprog

mpl.use("Agg")

from . import inputs, params as P
from .fig_main_cost import FUELS, MM, NAT_RC, _nat_map
from .fig_pptx_pairs import OUT, SUFFIX, YEARS

mpl.rcParams.update(NAT_RC)
MMB = P.MMBTU_PER_GJ
T0 = 1.0
T_CASES = (0.5, 1.0, 2.0)
T_MAIN = 1.0
import os
K_CAND = int(os.environ.get("TRANSPORT_K", 100000))   # all cheaper sources compete (400 did not converge)


def fig2_layer():
    """The Fig. 2 inputs: per land cell, LCOF by fuel ($/GJ) and demand by
    fuel (GJ/yr), built exactly as fig_sd_map.main builds them."""
    from .supply_demand import lcof_cells
    frames = {y: pd.read_csv(inputs.MAPS / f"lcoh_global_{y}{SUFFIX}.csv")
              .set_index("cell_id") for y in YEARS}
    cells = frames[YEARS[0]].index
    med_h2 = pd.Series(np.median(np.column_stack(
        [frames[y].loc[cells, "lcoh_usd_gj"] for y in YEARS]), axis=1), index=cells)
    med_el = pd.Series(np.median(np.column_stack(
        [frames[y].loc[cells, "lcoe_usd_mwh"] for y in YEARS]), axis=1), index=cells)
    meta = inputs.load_meta(2025)
    land = meta[meta.cell_type == "land"].copy()
    land = land.join(pd.DataFrame({"lcoh_usd_gj": med_h2, "lcoe_usd_mwh": med_el}),
                     how="inner")
    land = land[np.isfinite(land.lcoh_usd_gj)]
    co2 = pd.read_csv(inputs.MAPS / "co2_cost_by_cell.csv").set_index("cell_id") \
        .co2_cost.reindex(land.index).fillna(P.C_CO2_DAC)
    L = lcof_cells(land, co2)[FUELS]
    dg = pd.read_csv(inputs.MAPS / "demand_fuel_grid.csv", index_col=0)
    D = dg[[f + "_gj" for f in FUELS]].reindex(land.index).fillna(0.0)
    D.columns = FUELS
    ok = L.notna().all(axis=1)
    return land[ok], L[ok], D[ok]


def haversine_km(lat, lon):
    la, lo = np.radians(lat), np.radians(lon)
    dla = la[:, None] - la[None, :]
    dlo = lo[:, None] - lo[None, :]
    a = np.sin(dla / 2) ** 2 + np.cos(la)[:, None] * np.cos(la)[None, :] * np.sin(dlo / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def spare_h2(land, D):
    """land-limited hydrogen a cell can export after its own market (GJ/yr)"""
    from .supply_demand import firm_h2_potential_gj
    caps = pd.read_csv(inputs.MAPS / f"lcoh_global_2025{SUFFIX}.csv").set_index("cell_id")
    lc = land.join(caps[["cap_pv", "cap_wind"]], how="left")
    pot = firm_h2_potential_gj(lc).reindex(land.index).fillna(0.0)
    mu = pd.Series({f: 1.0 / P.FUELS[f]["eta_syn"] for f in FUELS})
    own = (D * mu).sum(axis=1)
    return (pot - own).clip(lower=0.0), mu


def main():
    land, L, D = fig2_layer()
    n = len(land)
    tot = D.sum(axis=1)
    wmix = D.sum() / D.sum().sum()
    W = D.div(tot.replace(0, np.nan), axis=0).fillna(wmix)
    B = W.to_numpy() @ L.to_numpy().T              # B[i, j]: i's basket made at j
    local = np.diag(B).copy()
    dist = haversine_km(land.lat.to_numpy(), land.lon.to_numpy())
    same = land.country.to_numpy()[:, None] == land.country.to_numpy()[None, :]
    eye = np.eye(n, dtype=bool)
    dem = tot.to_numpy()
    spare, mu = spare_h2(land, D)
    mubar = (W * mu).sum(axis=1).to_numpy()        # GJ H2 per GJ of i's basket

    # Fig. 2 classes straight from its own class file, so the baseline is
    # exactly the published map (327 cells, 39% of demand)
    cls = pd.read_csv(inputs.MAPS / "sd_map_classes.csv", index_col=0).reindex(land.index)
    cost_mmb = local * MMB
    assert np.allclose(cls.cost.to_numpy(), cost_mmb, rtol=1e-3, equal_nan=True), "cost basis differs from Fig. 2"
    qc = [float(cls.cost[cls.s == 2].max()), float(cls.cost[cls.s == 1].max())]
    deep = (cls.d == 2).to_numpy()
    bf_fig2 = ((cls.s == 2) & (cls.d == 2)).to_numpy()
    rows, cell_out = [], None
    for t in T_CASES:
        C = B + np.where(eye, 0.0, T0 + t * dist / 1000.0)
        for rule in ("domestic", "domestic-capped", "open", "open-capped"):
            if rule == "domestic":
                Cm = np.where(same, C, np.inf)
                j = Cm.argmin(axis=1)
                deliv = Cm[np.arange(n), j]
                src_dist = dist[np.arange(n), j]
            elif rule == "open":
                j = C.argmin(axis=1)
                deliv = C[np.arange(n), j]
                src_dist = dist[np.arange(n), j]
            else:  # capped rules
                # candidate sources: the K cheapest non-local deliveries that
                # beat local production, plus local production itself
                Cc = np.where(eye | (~same if rule == "domestic-capped" else False), np.inf, C)
                cand = np.argsort(Cc, axis=1)[:, :K_CAND]
                I_, J_ = [], []
                for i in range(n):
                    for jj in cand[i]:
                        if Cc[i, jj] < local[i] and spare.iloc[jj] > 0 and dem[i] > 0:
                            I_.append(i); J_.append(jj)
                I_, J_ = np.array(I_), np.array(J_)
                m = len(I_)
                # variables: x_ij (imports, GJ of i's basket), then local x_ii
                cost = np.concatenate([C[I_, J_], local]) * 1.0
                # quantities in PJ (costs stay in $/GJ): a tolerance-safe scaling
                # demand rows: sum_j x_ij + x_ii = dem_i
                Aeq = sparse.hstack([sparse.csr_matrix((np.ones(m), (I_, np.arange(m))), shape=(n, m)),
                                     sparse.identity(n, format="csr")], format="csr")
                # supply rows: sum_i mubar_i x_ij <= spare_j
                Aub = sparse.hstack([sparse.csr_matrix((mubar[I_], (J_, np.arange(m))), shape=(n, m)),
                                     sparse.csr_matrix((n, n))], format="csr")
                res = linprog(cost, A_ub=Aub, b_ub=spare.to_numpy() / 1e6, A_eq=Aeq, b_eq=dem / 1e6,
                              bounds=(0, None), method="highs")
                assert res.status == 0, res.message
                x = res.x * 1e6
                imp = np.bincount(I_, weights=x[:m], minlength=n)
                spend = np.bincount(I_, weights=x[:m] * C[I_, J_], minlength=n) + x[m:] * local
                deliv = np.where(dem > 0, spend / np.where(dem > 0, dem, 1), local)
                src_dist = np.where(imp > 0, np.bincount(I_, weights=x[:m] * dist[I_, J_], minlength=n)
                                    / np.where(imp > 0, imp, 1), 0.0)
                share_imp = np.where(dem > 0, imp / np.where(dem > 0, dem, 1), 0.0)
            saving = 1 - deliv / local
            if not rule.endswith("capped"):
                share_imp = (saving > 1e-9).astype(float)
            w = dem / dem.sum()
            cheap_new = (deliv * MMB <= qc[0]) | bf_fig2
            bf_old = bf_fig2
            bf_new = cheap_new & deep
            rows.append(dict(
                t_per_1000km=t, rule=rule,
                demand_share_imported=float((share_imp * w).sum()),
                cells_any_import=int((share_imp > 1e-6).sum()),
                median_saving_pct_importers=float(np.median(saving[share_imp > 1e-6]) * 100)
                if (share_imp > 1e-6).any() else 0.0,
                demand_weighted_saving_pct=float((saving * w).sum() * 100),
                median_source_km=float(np.median(src_dist[share_imp > 1e-6]))
                if (share_imp > 1e-6).any() else 0.0,
                build_first_cells=int(bf_new.sum()),
                build_first_demand_share=float(dem[bf_new].sum() / dem.sum()),
                build_first_cells_fig2=int(bf_old.sum()),
                build_first_demand_share_fig2=float(dem[bf_old].sum() / dem.sum())))
            print(f"t={t:.1f} {rule:11s}: imported {rows[-1]['demand_share_imported']:.1%} of demand, "
                  f"{rows[-1]['cells_any_import']} cells, median saving "
                  f"{rows[-1]['median_saving_pct_importers']:.1f}%, demand-weighted "
                  f"{rows[-1]['demand_weighted_saving_pct']:.1f}%, median source "
                  f"{rows[-1]['median_source_km']:.0f} km | build-first {bf_old.sum()} -> {bf_new.sum()} cells, "
                  f"{rows[-1]['build_first_demand_share_fig2']:.0%} -> {rows[-1]['build_first_demand_share']:.0%} of demand",
                  flush=True)
            if t == T_MAIN:
                if cell_out is None:
                    cell_out = pd.DataFrame({"country": land.country, "lat": land.lat, "lon": land.lon,
                                             "demand_gj": dem, "local_mmbtu": local * MMB},
                                            index=land.index)
                tag = rule.replace("-", "_")
                cell_out[f"deliv_{tag}_mmbtu"] = deliv * MMB
                cell_out[f"saving_{tag}_pct"] = saving * 100
                cell_out[f"imported_{tag}"] = share_imp
                cell_out[f"source_km_{tag}"] = src_dist
    summ = pd.DataFrame(rows)
    summ.round(4).to_csv(inputs.MAPS / "transport_summary.csv", index=False)
    cell_out.round(4).to_csv(inputs.MAPS / "transport_delivered.csv")
    figure(cell_out, summ)
    print("wrote transport_summary.csv, transport_delivered.csv")


def figure(c, summ):
    fig = plt.figure(figsize=(183 * MM, 150 * MM))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.35, 1.0], hspace=0.30, wspace=0.28,
                          left=0.07, right=0.985, top=0.97, bottom=0.08)
    a = fig.add_subplot(gs[0, :])
    b = fig.add_subplot(gs[1, 0])
    d = fig.add_subplot(gs[1, 1])
    vals = {int(k): float(v) for k, v in c.saving_open_capped_pct.items() if v > 0.05}
    _nat_map(fig, a, vals, "YlGnBu", 0, 60,
             "cost saving from buying fuel from a cheaper cell, % of local cost "
             "(uncoloured: local production is cheapest)", "")
    a.text(-0.01, 1.03, "a", transform=a.transAxes, fontsize=9, fontweight="bold", va="bottom")

    cols = {"domestic": "#C9CFD6", "domestic-capped": "#6B7682", "open": "#9ECAE1", "open-capped": "#0072B2"}
    labs = {"domestic": "within the country", "domestic-capped": "within the country, spare land only",
            "open": "anywhere", "open-capped": "anywhere, spare land only"}
    for rule, g in summ.groupby("rule"):
        b.plot(g.t_per_1000km, g.demand_share_imported * 100, "o-", color=cols[rule],
               label=labs[rule], lw=1.2, ms=4)
    b.set_xlabel("transport cost, US\\$ per GJ per 1,000 km (+\\$1/GJ handling)")
    b.set_ylabel("demand better served from\nanother cell, %")
    b.set_xticks(T_CASES)
    b.legend(frameon=False, fontsize=7, loc="center left", bbox_to_anchor=(0.02, 0.66))
    b.set_ylim(0, None)
    b.text(-0.18, 1.03, "b", transform=b.transAxes, fontsize=9, fontweight="bold", va="bottom")

    for rule, g in summ.groupby("rule"):
        d.plot(g.t_per_1000km, g.build_first_demand_share * 100, "o-", color=cols[rule], lw=1.2, ms=4)
    base = summ.build_first_demand_share_fig2.iloc[0] * 100
    d.axhline(base, color="#B4116F", lw=0.8, ls="--")
    d.text(T_CASES[0], base - 1.5, "Fig. 2 (local production only)", color="#B4116F", fontsize=7,
           va="top", ha="left")
    d.set_xlabel("transport cost, US\\$ per GJ per 1,000 km (+\\$1/GJ handling)")
    d.set_ylabel("demand in cheap-and-deep cells, %")
    d.set_xticks(T_CASES)
    d.set_ylim(0, None)
    d.text(-0.18, 1.03, "c", transform=d.transAxes, fontsize=9, fontweight="bold", va="bottom")
    for ax in (b, d):
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    fig.savefig(OUT / "fig_transport.pdf", bbox_inches="tight")
    fig.savefig(OUT / "fig_transport.png", dpi=600, bbox_inches="tight")
    plt.close(fig)
    print("saved fig_transport.(pdf|png)")


if __name__ == "__main__":
    main()
