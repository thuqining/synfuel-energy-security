"""
make_class_ref.py — CLIMATOLOGICAL technology assignment per cell.

IEC wind class and PV mode are investment decisions and must not depend on the
weather year: cells near the class boundaries (7.5 / 9.0 m/s) or the tracking
fallback threshold (fixed CF 0.17) otherwise flip technology between years
(342/2740 land cells flip IEC class in >=1 of the 20 years).

Builds data/grid/tech_assignment_ref.csv from the 20 annual cf_global CSVs:
  cell_id, wspd100_20yr, iec_class_ref, pv_fixed_20yr, pv_mode_ref

Usage:  conda run -n synfuel python python/make_class_ref.py
"""
from pathlib import Path
import os
import numpy as np, pandas as pd

import generate_cf_global as G

PROJECT = Path(os.environ.get("SYNF_DATA", Path(__file__).resolve().parents[1]))
YEARS = range(2006, 2026)

ws, pf = [], []
for yr in YEARS:
    df = pd.read_csv(PROJECT / "data" / "cost" / f"cf_global_{yr}.csv").set_index("cell_id")
    ws.append(df["mean_wspd100"])
    pf.append(df["pv_fixed"])
meta = df  # last year for country/cell_type
wspd20 = pd.concat(ws, axis=1).mean(axis=1)
pvfix20 = pd.concat(pf, axis=1).mean(axis=1)

cls = np.where(wspd20 < G.WSPD_THRESH[0], "III",
      np.where(wspd20 < G.WSPD_THRESH[1], "II", "I"))
pv_mode = [
    "tracking" if G.pv_is_tracking(meta.loc[c, "country"], pvfix20.loc[c]) else "fixed"
    for c in wspd20.index]

out = pd.DataFrame({"cell_id": wspd20.index,
                    "wspd100_20yr": wspd20.round(3).values,
                    "iec_class_ref": cls,
                    "pv_fixed_20yr": pvfix20.round(4).values,
                    "pv_mode_ref": pv_mode})
dest = PROJECT / "data" / "grid" / "tech_assignment_ref.csv"
out.to_csv(dest, index=False)

# report drift vs the per-year assignments
n_land = (meta.cell_type == "land").sum()
for yr in (2006, 2015, 2025):
    df = pd.read_csv(PROJECT / "data" / "cost" / f"cf_global_{yr}.csv").set_index("cell_id")
    land = df.cell_type == "land"
    dc = (df.loc[land, "iec_class"] != out.set_index("cell_id").loc[land[land].index, "iec_class_ref"]).sum()
    dp = (df.loc[land, "pv_mode"] != out.set_index("cell_id").loc[land[land].index, "pv_mode_ref"]).sum()
    print(f"{yr}: land cells differing from ref — iec {dc}, pv_mode {dp} (of {n_land})")
print(f"wrote {dest} ({len(out)} cells)")
