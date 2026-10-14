"""Supplementary Table tab:lcostiers and panel a of tab:paths: levelized cost of every fuel by tier and year.
Run from any directory: python work/caselow/sensitivity/lcos_tiers.py"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import os
from pathlib import Path

import numpy as np
import pandas as pd

from lcof import inputs, params as P, case_low as C
from lcof.supply_demand import lcof_cells

W = ROOT / "work" / "caselow"
MM = P.MMBTU_PER_GJ
# GJ -> trade unit multipliers (as fig_main_framework)
UNIT = {"hydrogen": ("US$/kg", 0.120), "ammonia": ("US$/t", 18.6), "methanol": ("US$/t", 19.9),
        "e-methane": ("US$/MMBtu", MM), "e-jet/e-diesel": ("US$/bbl", 0.0351 * 158.987),
        "ethanol": ("US$/gal", 0.0212 * 3.78541)}
rows = []
for y in (2025, 2030, 2040, 2050):
    for tier in ("low", "mid", "high"):
        tag = f"{y}" + ("" if tier == "low" else tier)
        os.environ["LCOF_TIER"] = "" if tier == "low" else tier
        inputs.MAPS = W / tag / "data"
        C.apply_params(y, None if tier == "low" else tier)
        meta = inputs.load_meta(2025)
        land = meta[meta.cell_type == "land"].copy()
        h = pd.concat([pd.read_csv(inputs.MAPS / f"lcoh_global_{wy}_reg.csv").set_index("cell_id")[["lcoh_usd_gj", "lcoe_usd_mwh"]]
                       for wy in range(2006, 2026)]).groupby(level=0).median()
        land = land.join(h, how="inner")
        co2 = pd.read_csv(inputs.MAPS / "co2_cost_by_cell.csv").set_index("cell_id").co2_cost.reindex(land.index).fillna(P.C_CO2_DAC)
        lc = lcof_cells(land, co2)
        series = {"hydrogen": land.lcoh_usd_gj, "ammonia": lc["ammonia"], "methanol": lc["methanol"],
                  "e-methane": lc["e-methane"], "e-jet/e-diesel": lc["e-kerosene"], "ethanol": lc["ethanol"]}
        for f, v in series.items():
            v = v.dropna().to_numpy()
            p5, p50, p95 = np.percentile(v, [5, 50, 95])
            u, k = UNIT[f]
            rows.append(dict(year=y, tier=tier, fuel=f, p5=p5 * MM, med=p50 * MM, p95=p95 * MM,
                             unit=u, p5_u=p5 * k, med_u=p50 * k, p95_u=p95 * k))
        print(y, tier, {r["fuel"]: round(r["med"], 1) for r in rows[-6:]}, flush=True)
out = pd.DataFrame(rows)
out.to_csv(W / "lcos_tiers.csv", index=False)
print(out.round(1).to_string())
