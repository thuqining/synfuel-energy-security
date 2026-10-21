"""
console_export.py — Fig. 4a for every economy, for the interactive console.

Runs fig5a_chain.compute (same merit order, 1% of GDP, chain security value)
on every economy in security_budget.csv instead of the core 30, and writes
console/build/fig4a_all_<year>.csv. Run per case with run_mod.py:

    python ../work/caselow/run_mod.py ../work/caselow/2030 2030 lcof.console_export
"""
import sys
from pathlib import Path

import pandas as pd

from lcof import fig5a_chain as A, inputs

OUT = Path(__file__).resolve().parents[2] / "console" / "build"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    orig = A.core_countries
    A.core_countries = lambda avail, n=30: sorted(avail)
    setup = A._setup()
    dem = setup[1]
    try:
        sb = pd.read_csv(inputs.MAPS / "security_budget.csv", index_col=0)
        si = pd.read_csv(inputs.MAPS / "security_index.csv", index_col=0)
        keep = [c for c in sb.index if c in dem.index and c in si.index]
        A.core_countries = lambda avail, n=30: [c for c in keep if c in set(avail)]
        d = A.compute(write=False, verbose=False, setup=setup)
    finally:
        A.core_countries = orig
    year = inputs.MAPS.parent.name
    d.to_csv(OUT / f"fig4a_all_{year}.csv")
    print(year, len(d), "economies ->", OUT / f"fig4a_all_{year}.csv")
    # cell production costs at this case's equipment costs (the layer Figs 4-5 use), US$/MMBtu
    from lcof import params as P
    land, lcof = setup[0], setup[3]
    cc = pd.DataFrame({"hydrogen": land.lcoh_usd_gj * P.MMBTU_PER_GJ}, index=land.index)
    for f in ("ammonia", "e-methane", "methanol", "e-kerosene", "e-diesel", "ethanol"):
        cc[f] = lcof[f].reindex(land.index) * P.MMBTU_PER_GJ
    cc.round(3).to_csv(OUT / f"cell_costs_{year}.csv")
    print(year, len(cc), "cells ->", OUT / f"cell_costs_{year}.csv")


if __name__ == "__main__":
    main()
