"""Supplementary Table tab:landsens: the land limit doubled, or half of farmland excluded.
Run from any directory: python work/caselow/sensitivity/land_sens.py"""
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
from lcof import security_budget as SB
from lcof import land_screen as LS
from lcof.coreset import core_countries

W = ROOT / "work" / "caselow"
orig_build = LS.build


def build_farm50(refresh=False):
    df = orig_build().copy()
    a, f, p = df.agri_share, df.forest_share, df.protected_share
    s = ((1 - p) * (1 - f - 0.50 * a)).clip(lower=0)
    base = (LS.DEV_BASE * s).clip(upper=0.02)
    df["land_baseline"] = base.fillna(df.land_baseline)
    return df


def groups(d):
    is_x = d.import_pct <= 0.0
    covered = ~is_x & (d.ret_sf_3 >= 0.995)
    land = ~is_x & ~covered & (d.cov_3 >= d.max_cov - 1e-6) & (d.max_cov < 1 - 1e-6)
    budget = ~is_x & ~covered & ~land
    return is_x, covered, land, budget


rows = []
for year in (2030, 2040, 2050):
    inputs.MAPS = W / str(year) / "data"
    C.apply_params(year)
    for case in ("main", "A: 10% of eligible, cap 4%", "B: exclude 50% of farmland"):
        LS.build = build_farm50 if case.startswith("B") else orig_build
        df, _ = SB.compute(scale=2.0 if case.startswith("A") else 1.0, write=False)
        core = [c for c in core_countries(df.index) if c in df.index]
        d = df.loc[core]
        is_x, cov, land, bud = groups(d)
        us = "United States of America"
        rows.append(dict(year=year, case=case, covered=int(cov.sum()), land=int(land.sum()), budget=int(bud.sum()),
                         exporters=int(is_x.sum()), constrained=int(land.sum() + bud.sum()),
                         median_cov1=round(100 * float(d.cov_1.median()), 0),
                         US_cov1=round(100 * float(d.cov_1[us]), 2), US_maxcov=round(100 * float(d.max_cov[us]), 2),
                         land_list=", ".join(sorted(d.index[land]))))
    LS.build = orig_build
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 200)
r = pd.DataFrame(rows)
print(r.drop(columns="land_list").to_string(index=False))
for _, x in r.iterrows():
    print(x.year, x.case, "| land-limited:", x.land_list)
