"""Supplementary Table tab:mfsens: oil-to-gas loss ratio m_f = 1.3 (main) vs 1.0.
Run from any directory: python work/caselow/sensitivity/mf_sens.py"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import os
from pathlib import Path
import numpy as np
import pandas as pd

os.environ.pop("LCOF_TIER", None)
from lcof import inputs, case_low as C
from lcof import fig5a_chain as A
from lcof import fig5_chain as F5
from lcof import fig4_years as Y

W = ROOT / "work" / "caselow"
rows = []
for year in (2030, 2040, 2050):
    inputs.MAPS = W / str(year) / "data"
    C.apply_params(year)
    sb = pd.read_csv(inputs.MAPS / "security_budget.csv", index_col=0)
    ref = pd.read_csv(inputs.MAPS / "fig5a_chain.csv", index_col=0)
    for mf in (1.3, 1.0):
        A.M_F["oil"] = mf                      # same dict object is used by fig5_chain
        d = A.compute(write=False, verbose=False)
        imp = sb.import_pct.reindex(d.index) > 0
        just = d.index[imp & (d.net_usd_t <= d.p_co2_usd_t)]
        neg = d.index[imp & (d.net_usd_t <= 0)]
        margin = (d.gross_usd_t - d.net_usd_t)[imp]
        F5._decline = lambda fuels: {f: np.ones(len(F5.VY)) for f in fuels}
        p, tj, _ = F5.panel_b_data(write=False)
        pi, pr = p["pi_2025"].to_numpy(), p["pi_rest_2025"].to_numpy()
        w = np.clip(p.w_usd_gj.to_numpy(), 0, None); ef = p.ef.to_numpy(); impg = p.imp_gj.to_numpy(); dem = p.dem_gj.to_numpy()
        zs = (impg * ef)[(pi - w) <= 0].sum() / 1e9 + ((dem - impg) * ef)[pr <= 0].sum() / 1e9
        zc = (impg * ef)[pi <= 0].sum() / 1e9 + ((dem - impg) * ef)[pr <= 0].sum() / 1e9
        if mf == 1.3:
            chk = np.allclose(d.net_usd_t.reindex(ref.index), ref.net_usd_t, equal_nan=True)
        rows.append(dict(year=year, m_f=mf, justified=len(just), security_alone=len(neg),
                         median_margin=round(float(margin.median()), 0), Gt_with_security=round(zs, 3),
                         Gt_cost_only=round(zc, 3), names=", ".join(sorted(just)),
                         reproduces_csv=chk if mf == 1.3 else ""))
    A.M_F["oil"] = 1.3
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 200)
r = pd.DataFrame(rows)
print(r.drop(columns="names").to_string(index=False))
for _, x in r.iterrows():
    print(x.year, x.m_f, "->", x.names)
