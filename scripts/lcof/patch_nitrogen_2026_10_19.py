"""
patch_nitrogen_2026_10_19.py -- apply the 2026-10-19 corrections to the nitrogen balance without the raw
Comtrade totals (tot_*.json, not shipped with the release):

  Norway       reports 3 kt N of nitrogen exports, under 1% of what its partners report importing from it;
               nitrogen_consumption.MIRROR now includes it, and its exports are the mirror flow, 633,356 t N
               from 112 partners (each partner's latest year 2025/2024/2023; preview-API pull of 2026-10-19,
               same method as nitrogen_consumption._mirror_t_n)
  Central African Republic
               Comtrade name 'Central African Rep.' now mapped to the model's name (ammonia_consumption.NAME)

then recomputes the derived columns exactly as nitrogen_consumption.build does (n_use_raw_t, n_import_share,
consumption_t rescaled to 160 Mt N x 17/14 of ammonia), and rescales the ammonia column of
demand_fuel_grid.csv country by country (demand_grid spreads each country's consumption over its cells with fixed
weights, so the cell values scale with the national total).

From scripts/:  python -m lcof.patch_nitrogen_2026_10_19 [data dir, default data/cost]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from . import inputs
from .ammonia_consumption import NH3_PER_N

NORWAY_MIRROR_T_N = 633356.0
NORWAY_PARTNERS = 112
WORLD_NH3_T = 160.0e6 * NH3_PER_N


def patch(d: Path):
    p = d / "ammonia_consumption.csv"
    a = pd.read_csv(p, index_col=0)
    old = a.consumption_t.copy()
    if "Central African Rep." in a.index:
        a = a.rename(index={"Central African Rep.": "Central African Republic"})
        old = old.rename(index={"Central African Rep.": "Central African Republic"})
    a.loc["Norway", "n_exports_t"] = NORWAY_MIRROR_T_N
    a.loc["Norway", "exports_source"] = f"mirror ({NORWAY_PARTNERS} partners)"
    a["n_use_raw_t"] = (a.n_production_t + a.n_imports_t - a.n_exports_t).clip(lower=0.0)
    net = (a.n_imports_t - a.n_exports_t).clip(lower=0.0)
    a["n_import_share"] = np.where(a.n_use_raw_t > 0, (net / a.n_use_raw_t).clip(upper=1.0), np.nan)
    scale = WORLD_NH3_T / (a.n_use_raw_t.sum() * NH3_PER_N)
    a["consumption_t"] = a.n_use_raw_t * NH3_PER_N * scale
    a.round(3).to_csv(p, index_label="country")
    ratio = (a.consumption_t / old).replace([np.inf, -np.inf], np.nan).fillna(1.0)
    print(f"{d}: Norway use {a.at['Norway', 'n_use_raw_t'] / 1e3:.0f} kt N, import share "
          f"{a.at['Norway', 'n_import_share']:.3f}; scale x{scale:.4f}; Norway consumption "
          f"{old['Norway'] / 1e6:.3f} -> {a.at['Norway', 'consumption_t'] / 1e6:.3f} Mt NH3")

    g = d / "demand_fuel_grid.csv"
    if g.exists():
        fuel = pd.read_csv(g, index_col=0)
        meta = inputs.load_meta(2025)
        ctry = meta.country.reindex(fuel.index)
        r = ctry.map(ratio).fillna(1.0)
        before = fuel.ammonia_gj.sum()
        for col in ("ammonia_gj", "ammonia"):
            fuel[col] = fuel[col] * r
        fuels = [c for c in fuel.columns if not c.endswith("_gj") and c != "total_tco2"]
        fuel["total_tco2"] = fuel[fuels].sum(axis=1)
        fuel.to_csv(g)
        print(f"{g.name}: ammonia {before / 1e9:.3f} -> {fuel.ammonia_gj.sum() / 1e9:.3f} PJ x1e3 "
              f"(EJ), Norway cells x{ratio.get('Norway', 1):.3f}")


if __name__ == "__main__":
    patch(Path(sys.argv[1]) if len(sys.argv) > 1 else inputs.MAPS)
