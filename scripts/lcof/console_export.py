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


def fuel_boxes():
    """Fig. 3's domestic-cost box for every economy and fuel (2025mid case): the cell with the lowest
    median cost over the 20 weather years, that cell's cost in each weather year, plus Fig. 3's
    US$1/GJ delivery (hydrogen without delivery). e-kerosene shares e-diesel's train."""
    import numpy as np
    from lcof import fig_main_sites as F
    frames = {y: pd.read_csv(inputs.MAPS / f"lcoh_global_{y}{F.SUFFIX}.csv")
              .set_index("cell_id")[["lcoh_usd_gj", "lcoe_usd_mwh"]] for y in F.YEARS}
    meta = inputs.load_meta(2025)
    land = meta[meta.cell_type == "land"]
    avail = frames[F.YEARS[0]].index
    co2 = pd.read_csv(inputs.MAPS / "co2_cost_by_cell.csv").set_index("cell_id").co2_cost
    cand = [i for i in land.index if i in avail]
    groups = land.loc[cand].groupby("country")
    rec = []
    for fuel in ("hydrogen", "ammonia", "e-methane", "methanol", "e-diesel", "ethanol"):
        if fuel == "hydrogen":
            med_all = pd.concat([frames[y].loc[cand, "lcoh_usd_gj"] for y in F.YEARS], axis=1).median(axis=1)
        else:
            med_all = F._cost_all(fuel, frames, meta, cand, co2)
        for c, grp in groups:
            best_id = int(med_all.loc[grp.index].idxmin())
            if fuel == "hydrogen":
                best = np.array([float(frames[y].loc[best_id, "lcoh_usd_gj"]) for y in F.YEARS]) * F.MMB
            else:
                best = F._syn(fuel, frames, meta, best_id, co2) + F.TRANSPORT_USD_GJ * F.MMB
            rec.append(dict(country=c, fuel=fuel, best_cell=best_id, n_weather_years=len(best),
                            **{f"p{q:02d}": float(np.percentile(best, q)) for q in (1, 25, 50, 75, 99)}))
    d = pd.DataFrame(rec).round(3)
    d.to_csv(OUT / "fuel_box_2025.csv", index=False)
    print(d.country.nunique(), "economies x", d.fuel.nunique(), "fuels ->", OUT / "fuel_box_2025.csv")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if inputs.MAPS.parent.name == "2025mid":
        return fuel_boxes()
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
