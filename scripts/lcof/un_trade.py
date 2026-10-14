"""
un_trade.py — oil and gas net import dependence from the UN Energy
Statistics Database, for the economies the Energy Institute review names
only inside regional totals.

Net import dependence follows the Eurostat definition used for every other
economy in the paper, (imports - exports) / gross inland supply, with
gross inland supply approximated as production + imports - exports (stock
changes and bunkers are small for these economies and are left out):

  oil  production = crude oil (4100) + natural gas liquids (4200);
       imports and exports = crude, NGL and every oil product (46xx), so
       an economy that exports crude and imports refined fuel is a net
       importer only if the products outweigh the crude
  gas  natural gas (3000)

Source: UNSD Energy Statistics Database, SDMX dataflow DF_UNDATA_ENERGY
(https://data.un.org/ws/rest), transactions 01 production, 03 imports,
04 exports, 2019-2023; the latest year with all three flows reported (a
missing flow counts as zero once any flow of that year is reported).
Oil series are in tonnes with a per-series calorific factor, gas in TJ.

From scripts/:  conda run -n synfuel python -u -m lcof.un_trade [--fetch]
Outputs: data/demand/un_energy/raw/un_trade_{OIL,GAS}.xml
         data/demand/un_energy/un_trade_tj.csv
         data/demand/un_energy/un_net_dependence.csv
"""
from __future__ import annotations

import sys
import time
import urllib.request
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

from .un_energy import GROUPS, RAW, UND, G

URL = ("https://data.un.org/legacy/ws/rest/data/DF_UNDATA_ENERGY/"
       "A..{cm}.01+03+04/ALL/?startPeriod=2019&endPeriod=2023")
PRIMARY_OIL = ["4100", "4200"]
TRADE = {"OIL": PRIMARY_OIL + GROUPS["OIL"], "GAS": GROUPS["GAS"]}


def fetch():
    RAW.mkdir(parents=True, exist_ok=True)
    for grp, codes in TRADE.items():
        for attempt in range(4):
            try:
                with urllib.request.urlopen(URL.format(cm="+".join(codes)),
                                            timeout=300) as r:
                    (RAW / f"un_trade_{grp}.xml").write_bytes(r.read())
                break
            except Exception as e:                       # transient 5xx
                if attempt == 3:
                    raise
                print(f"  retry {grp}: {e}")
                time.sleep(10 * (attempt + 1))
        print(f"fetched {grp}")


def parse() -> pd.DataFrame:
    rows = []
    for grp in TRADE:
        root = ET.parse(RAW / f"un_trade_{grp}.xml").getroot()
        for ser in root.iter(G + "Series"):
            key = {v.get("id"): v.get("value") for v in ser.find(G + "SeriesKey")}
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
                rows.append((grp, key["REF_AREA"].zfill(3), key["COMMODITY"],
                             key["TRANSACTION"],
                             int(ob.find(G + "ObsDimension").get("value")), tj))
    df = pd.DataFrame(rows, columns=["group", "area", "commodity",
                                     "transaction", "year", "tj"])
    df.to_csv(UND / "un_trade_tj.csv", index=False)
    return df


def net_dependence(df: pd.DataFrame | None = None) -> pd.DataFrame:
    """one row per (area, group): year, production, imports, exports (TJ)
    and dep = clip((imp - exp) / (prod + imp - exp), 0, 1)."""
    if df is None:
        df = pd.read_csv(UND / "un_trade_tj.csv",
                         dtype={"area": str, "commodity": str, "transaction": str})
    df = df.assign(area=df.area.str.zfill(3))
    oil_prod = (df.group == "OIL") & (df.transaction == "01") & \
        ~df.commodity.isin(PRIMARY_OIL)
    df = df[~oil_prod]                    # refinery output is not supply
    p = df.groupby(["area", "group", "year", "transaction"]).tj.sum().unstack("transaction")
    p = p.reindex(columns=["01", "03", "04"]).fillna(0.0)
    p.columns = ["prod", "imp", "exp"]
    p = p.reset_index().sort_values("year").groupby(["area", "group"]).last()
    supply = p["prod"] + p.imp - p.exp
    p["dep"] = np.where(supply > 0, ((p.imp - p.exp) / supply).clip(0, 1),
                        np.where(p.imp - p.exp > 0, 1.0, 0.0))
    p = p.reset_index()
    p.to_csv(UND / "un_net_dependence.csv", index=False)
    return p


def main():
    if "--fetch" in sys.argv:
        fetch()
    parse()
    d = net_dependence()
    print(f"{d.area.nunique()} areas; oil rows {int((d.group == 'OIL').sum())}, "
          f"gas rows {int((d.group == 'GAS').sum())}")


if __name__ == "__main__":
    main()
