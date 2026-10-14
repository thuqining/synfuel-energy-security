"""
ei_energy.py — national oil, gas and coal consumption from the Energy
Institute Statistical Review of World Energy, 2026 edition (data to 2025).

Used for two things:
  * the growth of each country's use of each fossil fuel from the UN base
    year (2023) to the latest year (2025), which carries the UN sector levels
    forward in demand_grid;
  * each country's 2025 gas use, which caps the e-methane market, and its
    2025 oil and gas use, which Figure 1 compares the market against.

Consumption is in net calorific (lower heating value) terms; oil includes
international aviation and marine bunkers and excludes biofuels. The file
names 79 countries individually for oil (76 gas, 77 coal); the rest appear
only inside regional groups, and those countries fall back to EDGAR.

Source file: data/demand/ei_2026/Statistical Review of World Energy
Narrow format.csv, downloaded from
https://www.energyinst.org/statistical-review/resources-and-data-downloads
"""
from __future__ import annotations

import pandas as pd

from . import inputs

EID = inputs.PROJECT / "data" / "demand" / "ei_2026"
FILE = "Statistical Review of World Energy Narrow format.csv"
VARS = {"GAS": "gas_tes_ej", "OIL": "oil_tes_ej", "COAL": "coal_tes_ej"}
BASE_YEAR, LATEST_YEAR = 2023, 2025
# the UN codes a few countries together with a small territory; the Energy
# Institute uses the plain ISO code
UN_TO_ISO = {"251": "250", "382": "380", "579": "578", "757": "756"}


def _table() -> pd.DataFrame:
    d = pd.read_csv(EID / FILE, low_memory=False)
    d = d[d.ISO3166_numeric.notna() & d.Var.isin(VARS.values())].copy()
    d["iso"] = d.ISO3166_numeric.astype(int).astype(str).str.zfill(3)
    return d


def by_country(countries) -> pd.DataFrame:
    """GJ per model country: columns GAS/OIL/COAL for BASE and LATEST year,
    NaN where the Energy Institute has no figure of its own."""
    from .un_energy import _name_map
    d = _table()
    piv = d.pivot_table(index=["iso", "Var"], columns="Year", values="Value",
                        aggfunc="sum")
    nm = {c: UN_TO_ISO.get(a, a) for c, a in _name_map(list(countries)).items()}
    rows = {}
    for c, iso in nm.items():
        r = {}
        for g, v in VARS.items():
            for y in (BASE_YEAR, LATEST_YEAR):
                try:
                    r[f"{g}_{y}"] = float(piv.loc[(iso, v), y]) * 1e9
                except KeyError:
                    r[f"{g}_{y}"] = float("nan")
        rows[c] = r
    out = pd.DataFrame(rows).T
    out.index.name = "country"
    return out


def growth(countries) -> pd.DataFrame:
    """LATEST / BASE per fuel group, NaN where either year is missing or
    the base is zero."""
    t = by_country(countries)
    g = pd.DataFrame({k: t[f"{k}_{LATEST_YEAR}"] / t[f"{k}_{BASE_YEAR}"]
                      for k in VARS})
    return g.where(t[[f"{k}_{BASE_YEAR}" for k in VARS]].to_numpy() > 0)
