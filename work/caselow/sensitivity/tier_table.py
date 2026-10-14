"""Supplementary Table tab:paths (panel b) and the cost medians of panel a: every cost year x cost tier.
Run from any directory: python work/caselow/sensitivity/tier_table.py"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import os
import sys

import numpy as np
import pandas as pd

from lcof import inputs, params as P, case_low as C
from lcof import fig4_years as F4
from lcof.coreset import core_countries
from lcof.supply_demand import lcof_cells

W = str(ROOT / "work" / "caselow") + "/"
MM = P.MMBTU_PER_GJ
rows = []
for y in (2025, 2030, 2040, 2050):
    for tier in ("low", "mid", "high"):
        tag = f"{y}" + ("" if tier == "low" else tier)
        os.environ["LCOF_TIER"] = "" if tier == "low" else tier
        inputs.MAPS = Path(W + tag + "/data")
        C.apply_params(y, None if tier == "low" else tier)
        meta = inputs.load_meta(2025)
        land = meta[meta.cell_type == "land"].copy()
        h = pd.concat([pd.read_csv(inputs.MAPS / f"lcoh_global_{wy}_reg.csv").set_index("cell_id")[["lcoh_usd_gj", "lcoe_usd_mwh"]]
                       for wy in range(2006, 2026)]).groupby(level=0).median()
        land = land.join(h, how="inner")
        co2 = pd.read_csv(inputs.MAPS / "co2_cost_by_cell.csv").set_index("cell_id").co2_cost.reindex(land.index).fillna(P.C_CO2_DAC)
        lc = lcof_cells(land, co2)
        jet = pd.concat([lc["e-kerosene"], lc["e-diesel"]]).median()
        d = pd.read_csv(inputs.MAPS / "fig5a_chain.csv", index_col=0)
        sb = pd.read_csv(inputs.MAPS / "security_budget.csv", index_col=0)
        core = [c for c in core_countries(sb.index) if c in sb.index]
        s = sb.loc[core]; im = s.import_pct > 0
        cov = [int((im & (s[f"ret_sf_{b}"] >= 0.995)).sum()) for b in (1, 2, 3)]
        _, p, tj = F4.year_data(y, W + tag)
        pi, pr = p[f"pi_{y}"].to_numpy(), p[f"pi_rest_{y}"].to_numpy()
        w = np.clip(p.w_usd_gj.to_numpy(), 0, None); ef, imp = p.ef.to_numpy(), p.imp_gj.to_numpy()
        r = pd.concat([pd.DataFrame({"wd": imp * ef / 1e9, "c": (pi - w) / ef, "prem": pi / ef}),
                       pd.DataFrame({"wd": (p.dem_gj.to_numpy() - imp) * ef / 1e9, "c": pr / ef, "prem": pr / ef})])
        r = r[r.wd > 0]
        rows.append(dict(year=y, tier=tier,
                         h2_mmbtu=land.lcoh_usd_gj.median() * MM, h2_kg=land.lcoh_usd_gj.median() * 0.120,
                         nh3_t=lc["ammonia"].median() * 18.6, jet_bbl=jet * 0.0351 * 158.987,
                         justified=len(d[d.net_usd_t <= d.p_co2_usd_t]),
                         gt_sec=r.wd[r.c <= 0].sum(), gt_cost=r.wd[r.prem <= 0].sum(),
                         cov1=s.cov_1.median(), cov_1=cov[0], cov_2=cov[1], cov_3=cov[2]))
        print(rows[-1], flush=True)
out = pd.DataFrame(rows)
out.round(3).to_csv(W + "tier_table.csv", index=False)
print(out.round(2).to_string())
