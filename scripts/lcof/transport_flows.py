"""
transport_flows.py — the cell-to-cell flows behind Supplementary Note 6,
for drawing arrows on the job-talk maps. transport.py solves the capped
sourcing rules as linear programmes but writes only cell totals; this module
re-solves the same programmes (same inputs, same candidate rule, same LP) at
the central transport rate and keeps the flows. Before writing, it checks
that the solution reproduces transport_summary.csv (build-first share of
demand: 44% within countries, 63% across borders).

Writes cf_global_final/figures/slides2026/v14/_flows_<rule>.csv only
(nothing in data/cost).

From scripts/:  python -m lcof.transport_flows
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.optimize import linprog

from . import inputs
from . import transport as TR

OUT = inputs.PROJECT / "cf_global_final" / "figures" / "slides2026" / "v14"
OUT.mkdir(parents=True, exist_ok=True)


def main(t=TR.T_MAIN):
    land, L, D = TR.fig2_layer()
    n = len(land)
    tot = D.sum(axis=1)
    wmix = D.sum() / D.sum().sum()
    W = D.div(tot.replace(0, np.nan), axis=0).fillna(wmix)
    B = W.to_numpy() @ L.to_numpy().T
    local = np.diag(B).copy()
    dist = TR.haversine_km(land.lat.to_numpy(), land.lon.to_numpy())
    same = land.country.to_numpy()[:, None] == land.country.to_numpy()[None, :]
    eye = np.eye(n, dtype=bool)
    dem = tot.to_numpy()
    spare, mu = TR.spare_h2(land, D)
    mubar = (W * mu).sum(axis=1).to_numpy()
    cls = pd.read_csv(inputs.MAPS / "sd_map_classes.csv", index_col=0).reindex(land.index)
    qc0 = float(cls.cost[cls.s == 2].max())
    deep = (cls.d == 2).to_numpy()
    bf_fig2 = ((cls.s == 2) & (cls.d == 2)).to_numpy()
    summ = pd.read_csv(inputs.MAPS / "transport_summary.csv")
    summ = summ[np.isclose(summ.t_per_1000km, t)].set_index("rule")
    C = B + np.where(eye, 0.0, TR.T0 + t * dist / 1000.0)
    for rule in ("domestic-capped", "open-capped"):
        Cc = np.where(eye | (~same if rule == "domestic-capped" else False), np.inf, C)
        cand = np.argsort(Cc, axis=1)[:, :TR.K_CAND]
        ok = (Cc[np.arange(n)[:, None], cand] < local[:, None]) & (spare.to_numpy()[cand] > 0) & (dem[:, None] > 0)
        I_ = np.repeat(np.arange(n), cand.shape[1])[ok.ravel()]
        J_ = cand.ravel()[ok.ravel()]
        m = len(I_)
        cost = np.concatenate([C[I_, J_], local]) * 1.0
        Aeq = sparse.hstack([sparse.csr_matrix((np.ones(m), (I_, np.arange(m))), shape=(n, m)),
                             sparse.identity(n, format="csr")], format="csr")
        Aub = sparse.hstack([sparse.csr_matrix((mubar[I_], (J_, np.arange(m))), shape=(n, m)),
                             sparse.csr_matrix((n, n))], format="csr")
        res = linprog(cost, A_ub=Aub, b_ub=spare.to_numpy() / 1e6, A_eq=Aeq, b_eq=dem / 1e6,
                      bounds=(0, None), method="highs")
        assert res.status == 0, res.message
        x = res.x * 1e6
        imp = np.bincount(I_, weights=x[:m], minlength=n)
        spend = np.bincount(I_, weights=x[:m] * C[I_, J_], minlength=n) + x[m:] * local
        deliv = np.where(dem > 0, spend / np.where(dem > 0, dem, 1), local)
        bf_new = ((deliv * TR.MMB <= qc0) | bf_fig2) & deep
        share = float(dem[bf_new].sum() / dem.sum())
        want = float(summ.build_first_demand_share[rule])
        assert abs(share - want) < 5e-4, (rule, share, want)
        keep = x[:m] > 1.0
        ids = land.index.to_numpy()
        fl = pd.DataFrame({
            "dest": ids[I_[keep]], "src": ids[J_[keep]],
            "dest_country": land.country.to_numpy()[I_[keep]], "src_country": land.country.to_numpy()[J_[keep]],
            "dest_lat": land.lat.to_numpy()[I_[keep]], "dest_lon": land.lon.to_numpy()[I_[keep]],
            "src_lat": land.lat.to_numpy()[J_[keep]], "src_lon": land.lon.to_numpy()[J_[keep]],
            "gj": x[:m][keep], "km": dist[I_[keep], J_[keep]],
            "delivered_mmbtu": C[I_[keep], J_[keep]] * TR.MMB, "local_mmbtu": local[I_[keep]] * TR.MMB,
        })
        fl.to_csv(OUT / f"_flows_{rule}.csv", index=False)
        print(f"{rule}: build-first share {share:.4f} (summary {want:.4f}); {len(fl)} flows, "
              f"{fl.gj.sum() / 1e9:.2f} EJ moved; {int((fl.dest_country != fl.src_country).sum())} cross-border")


if __name__ == "__main__":
    main()
