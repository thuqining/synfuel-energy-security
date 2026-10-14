"""
inputs.py — data loaders for the LCOF model.

Hourly CF: cf_global_final/data/cf_hourly/cf_hourly_<yr>.nc  (time x cell)
Cell meta: cf_global_final/data/cost/cf_global_<yr>.csv      (pv_mode, country...)
Maps:      data/cost/wacc_by_country.csv, water_cost_by_cell.csv,
           co2_cost_by_cell.csv
"""
from __future__ import annotations

import os

from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr

from . import params as P

PROJECT = Path(__file__).resolve().parents[2]
CF_HOURLY = PROJECT / "cf_global_final" / "data" / "cf_hourly"
CF_META = PROJECT / "cf_global_final" / "data" / "cost"
MAPS = PROJECT / "data" / "cost"


def load_meta(year: int = 2025) -> pd.DataFrame:
    """Per-cell metadata (country, pv_mode, annual CFs) indexed by cell_id.

    pv_mode is overridden by the CLIMATOLOGICAL assignment
    (tech_assignment_ref.csv) so the design does not depend on the weather year.
    """
    df = pd.read_csv(CF_META / f"cf_global_{year}.csv").set_index("cell_id")
    ref_path = PROJECT / "cf_global_final" / "data" / "grid" / "tech_assignment_ref.csv"
    if ref_path.exists():
        ref = pd.read_csv(ref_path).set_index("cell_id")
        df["pv_mode"] = ref["pv_mode_ref"].reindex(df.index).fillna(df["pv_mode"])

    wacc = pd.read_csv(MAPS / "wacc_by_country.csv")
    wmap = dict(zip(wacc["country"], wacc["wacc_pct"] / 100.0))
    df["wacc"] = df["country"].map(wmap).fillna(P.WACC_DEFAULT)

    water = pd.read_csv(MAPS / "water_cost_by_cell.csv").set_index("cell_id")
    df["water_cost"] = water["water_cost"].reindex(df.index)

    co2 = pd.read_csv(MAPS / "co2_cost_by_cell.csv").set_index("cell_id")
    df["co2_cost"] = co2["co2_cost"].reindex(df.index)
    df["co2_pathway"] = co2["pathway"].reindex(df.index)

    # regional CAPEX (IRENA country PV/wind, electrolyser procurement,
    # synthesis EPC location factor) — used by the regional mainline
    # LCOF_CAPEX_FILE: another country cost table (2026-10-07 IEA GHR 2025 electrolyser costs)
    cap_path = MAPS / os.environ.get("LCOF_CAPEX_FILE", "capex_by_country.csv")
    if cap_path.exists():
        cap = pd.read_csv(cap_path).set_index("country")
        df["pv_capex"] = df["country"].map(cap["pv_capex_usd_kw"] * 1e3)
        df["wind_capex"] = df["country"].map(cap["wind_capex_usd_kw"] * 1e3)
        df["ez_capex"] = df["country"].map(cap["electrolyser_capex_usd_kw"] * 1e3)
        df["syn_loc"] = df["country"].map(cap["syn_location_factor"]).fillna(1.0)
        if "battery_energy_usd_kwh" in cap.columns:
            df["bat_e_capex"] = df["country"].map(cap["battery_energy_usd_kwh"] * 1e3)
            df["bat_p_capex"] = df["country"].map(cap["battery_power_usd_kw"] * 1e3)
        if "h2_tank_usd_kwh" in cap.columns:
            df["tank_capex"] = df["country"].map(cap["h2_tank_usd_kwh"] * 1e3)
    return df


def open_year(year: int) -> xr.Dataset:
    return xr.open_dataset(CF_HOURLY / f"cf_hourly_{year}.nc")


def cell_profiles(ds: xr.Dataset, cell_id: int, pv_mode: str = "fixed"):
    """(cf_pv, cf_wind) hourly arrays for one land cell."""
    idx = int(np.where(ds["cell_id"].values == cell_id)[0][0])
    pv_var = "pv_track_cf" if str(pv_mode).startswith("track") else "pv_fixed_cf"
    cf_pv = ds[pv_var].isel(cell=idx).values.astype(float)
    cf_w = ds["wind_onshore_cf"].isel(cell=idx).values.astype(float)
    # cap at nameplate: stored Huld-model PV can slightly exceed 1 (no inverter
    # clip at generation time in the pre-2026-08 hourly files)
    return np.clip(np.nan_to_num(cf_pv), 0.0, 1.0), np.clip(np.nan_to_num(cf_w), 0.0, 1.0)


def nearest_land_cell(meta: pd.DataFrame, lon: float, lat: float) -> int:
    """cell_id of the nearest land cell to (lon, lat)."""
    land = meta[meta.cell_type == "land"]
    coslat = np.cos(np.deg2rad(lat))
    d2 = ((land.lon - lon) * coslat) ** 2 + (land.lat - lat) ** 2
    return int(d2.idxmin())
