"""
un_energy.py — national fossil fuel use by sector from the UN Energy
Statistics Database, the LEVEL that demand_grid anchors its sectors to.

The emissions route in demand_grid estimates how much fuel a sector burns
by dividing its CO2 by one emission factor. That is sound for sectors that
burn one fuel, and poor where the fuel mix is mixed: industrial CO2 is
largely coal, yet it was converted at the gas factor, which overstated
industrial fuel use by about a third. Here the level comes from reported
statistics instead, and EDGAR keeps only its job of placing that level
inside each country.

Source: UNSD Energy Statistics Database, SDMX dataflow DF_UNDATA_ENERGY
(https://data.un.org/ws/rest), annual, all countries. Fossil fuels only
(natural gas, oil products, coal products); oil and coal series are
reported in tonnes with a per-series calorific factor (GJ/t), gas in TJ.
Latest complete year 2023 (2024 covers too few countries), with 2022 used
for any country and sector that has no 2023 figure.

Sectors, UN transaction codes -> model sector:
  IND       121  manufacturing, construction and non-fuel industry
  RCO       1231 households + 1235 commerce and public services
            + 1232 agriculture, forestry and fishing
  TRO       1221 road
  AVIATION  1223 domestic aviation + 052 international aviation bunkers
Shipping is not anchored: its emissions sit at sea, where no country can
be assigned, and chemicals and fertiliser are already calibrated to
production statistics in demand_grid.

From scripts/:  conda run -n synfuel python -u -m lcof.un_energy [--fetch]
Outputs: data/demand/un_energy/un_sector_fuel_tj.csv
         data/demand/un_energy/un_national_levels_gj.csv
"""
from __future__ import annotations

import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

from . import inputs

UND = inputs.PROJECT / "data" / "demand" / "un_energy"
RAW = UND / "raw"
URL = ("https://data.un.org/ws/rest/data/DF_UNDATA_ENERGY/"
       "A..{cm}.{tx}/ALL/?startPeriod=2022&endPeriod=2023")
YEAR, FALLBACK = 2023, 2022

GROUPS = {
    "GAS": ["3000"],
    "OIL": ["4610", "4620", "4630", "4640", "4651", "4652", "4653", "4661",
            "4669", "4670", "4680", "4694", "4699"],
    "COAL": ["0100", "0110", "0121", "0129", "0200", "0210", "0220", "0311",
             "0312", "0320", "0330", "0350", "0360", "0371", "0379", "0390"],
}
SECTORS = {"IND": ["121"],
           "RCO": ["1231", "1235", "1232"],
           "TRO": ["1221"],
           "AVIATION": ["1223", "052"]}
TX_ALL = sorted({t for v in SECTORS.values() for t in v})

# model country name -> UN area code, where the names differ
MANUAL = {"Czechia": "203", "Ethiopia": "231", "France": "251",
          "Iran": "364", "Italy": "382", "Ivory Coast": "384",
          "Laos": "418", "Norway": "579", "Republic of the Congo": "178",
          "Russia": "643", "South Korea": "410", "Switzerland": "757",
          "Syria": "760", "United States of America": "840",
          "North Korea": "408", "Republic of Serbia": "688",
          "The Bahamas": "044", "East Timor": "626",
          "Federated States of Micronesia": "583",
          "São Tomé and Principe": "678", "Falkland Islands": "238"}

G = "{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic}"


def fetch():
    """Download the three fuel groups (about 5 MB in all)."""
    RAW.mkdir(parents=True, exist_ok=True)
    for grp, codes in GROUPS.items():
        url = URL.format(cm="+".join(codes), tx="+".join(TX_ALL))
        with urllib.request.urlopen(url, timeout=300) as r:
            (RAW / f"un_{grp}.xml").write_bytes(r.read())
        print(f"fetched {grp}")


def parse() -> pd.DataFrame:
    """Generic SDMX-XML -> one row per area, commodity, transaction, year,
    in TJ."""
    rows = []
    for grp in GROUPS:
        root = ET.parse(RAW / f"un_{grp}.xml").getroot()
        for ser in root.iter(G + "Series"):
            key = {v.get("id"): v.get("value")
                   for v in ser.find(G + "SeriesKey")}
            sattr = {v.get("id"): v.get("value")
                     for v in (ser.find(G + "Attributes") or [])}
            for ob in ser.findall(G + "Obs"):
                val = ob.find(G + "ObsValue")
                if val is None:
                    continue
                a = {**sattr, **{v.get("id"): v.get("value")
                                 for v in (ob.find(G + "Attributes") or [])}}
                x = float(val.get("value")) * 10 ** int(a.get("UNIT_MULT", 0))
                unit = a.get("UNIT_MEASURE", "")
                if unit == "TJ":
                    tj = x
                elif unit == "TN" and a.get("CONVERSION_FACTOR"):
                    tj = x * float(a["CONVERSION_FACTOR"]) / 1e3
                else:
                    continue
                rows.append((grp, key["REF_AREA"], key["COMMODITY"],
                             key["TRANSACTION"],
                             int(ob.find(G + "ObsDimension").get("value")),
                             tj))
    df = pd.DataFrame(rows, columns=["group", "area", "commodity",
                                     "transaction", "year", "tj"])
    df.to_csv(UND / "un_sector_fuel_tj.csv", index=False)
    return df


def _name_map(countries) -> dict:
    ac = pd.read_csv(RAW / "area_codes.csv", dtype=str)
    norm = lambda s: re.sub(r"[^a-z]", "", str(s).lower())
    byname = {norm(n): c for c, n in zip(ac.code, ac.name)}
    out = {c: byname[norm(c)] for c in countries if norm(c) in byname}
    out.update({c: a for c, a in MANUAL.items() if c in set(countries)})
    return {c: a.zfill(3) for c, a in out.items()}


def national(df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Per model country: fossil GJ per anchored sector, latest year."""
    if df is None:
        df = pd.read_csv(UND / "un_sector_fuel_tj.csv",
                         dtype={"area": str, "transaction": str})
    df = df.assign(area=df.area.astype(str).str.zfill(3))
    out = {}
    for sec, tx in SECTORS.items():
        piv = (df[df.transaction.astype(str).isin(tx)]
               .groupby(["area", "year"]).tj.sum().unstack("year"))
        v = piv.get(YEAR)
        if FALLBACK in piv.columns:
            v = piv[FALLBACK] if v is None else v.fillna(piv[FALLBACK])
        out[sec] = v * 1e3                                   # TJ -> GJ
    lev = pd.DataFrame(out)
    meta = inputs.load_meta(2025)
    nm = _name_map(sorted(meta.country.dropna().unique()))
    res = pd.DataFrame({c: lev.loc[a] for c, a in nm.items()
                        if a in lev.index}).T
    res.index.name = "country"
    res.to_csv(UND / "un_national_levels_gj.csv")
    return res


def sector_fuel_levels() -> pd.DataFrame:
    """Per model country, fossil GJ in each anchored sector split by fuel
    group, for YEAR (FALLBACK for a country and sector with no YEAR figure).
    Columns are (sector, GAS | OIL | COAL). demand_grid grows each group to
    the latest year with that country's Energy Institute growth for the
    same fuel."""
    df = pd.read_csv(UND / "un_sector_fuel_tj.csv",
                     dtype={"area": str, "transaction": str})
    df = df.assign(area=df.area.astype(str).str.zfill(3))
    parts = {}
    for sec, tx in SECTORS.items():
        s = df[df.transaction.astype(str).isin(tx)]
        piv = s.groupby(["area", "group", "year"]).tj.sum().unstack("year")
        tot = piv.groupby(level="area").sum(min_count=1)
        pick = pd.Series(YEAR, index=tot.index)
        if YEAR in tot.columns and FALLBACK in tot.columns:
            pick = pick.where(tot[YEAR].notna(), FALLBACK)
        rows = {}
        for (area, grp), r in piv.iterrows():
            y = pick.get(area, YEAR)
            v = r.get(y)
            rows[(area, grp)] = 0.0 if pd.isna(v) else float(v) * 1e3   # TJ -> GJ
        parts[sec] = pd.Series(rows).unstack().fillna(0.0)
    meta = inputs.load_meta(2025)
    nm = _name_map(sorted(meta.country.dropna().unique()))
    out = {}
    for sec, tab in parts.items():
        for grp in ("GAS", "OIL", "COAL"):
            col = tab[grp] if grp in tab.columns else pd.Series(dtype=float)
            out[(sec, grp)] = pd.Series({c: col.get(a, float("nan"))
                                         for c, a in nm.items()})
    res = pd.DataFrame(out)
    res.index.name = "country"
    return res


def load_levels() -> pd.DataFrame:
    """National fossil GJ per anchored sector, indexed by model country."""
    return pd.read_csv(UND / "un_national_levels_gj.csv", index_col=0)


def main():
    if "--fetch" in sys.argv:
        fetch()
    df = parse()
    lev = national(df)
    print(f"UN levels for {len(lev)} model countries; world EJ: "
          + ", ".join(f"{k} {v / 1e9:.1f}" for k, v in lev.sum().items()))


if __name__ == "__main__":
    main()
