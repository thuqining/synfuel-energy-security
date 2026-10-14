"""
land_screen.py — country-level screened land availability for the
renewable build, replacing the uniform 2%-of-land cap.

Method (screening note, 2026-08-18): from four WDI series,
    s_eligible = max(0, (1 - p) * (1 - f - 0.90 a))
with a = agricultural land share (2023, FAO), f = forest share (2023,
FAO), p = terrestrial protected-area share (2025, Protected Planet).
Forests are excluded, 90% of agricultural land is excluded, protected
areas scale the remainder proportionally. The renewable buildout then
uses 5% of the eligible pool as the BASELINE and 10% as the HIGH
sensitivity, i.e. roughly 1% and 2% of total land at the median.

Outputs data/cost/land_screen.csv (country, s_eligible,
land_baseline, land_high). Cached: re-fetches only with --refresh.

From scripts/:  conda run -n synfuel python -u -m lcof.land_screen
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from . import inputs
from .fetch_vulnerability import _get, _wb_join

OUT = inputs.MAPS / "land_screen.csv"
WB = ("https://api.worldbank.org/v2/country/all/indicator/{ind}"
      "?format=json&per_page=20000&date={date}")
DEV_BASE, DEV_HIGH = 0.05, 0.10


def _wdi(ind: str, date: str) -> pd.Series:
    vals = {}
    page, pages = 1, 1
    while page <= pages:
        d = _get(WB.format(ind=ind, date=date) + f"&page={page}")
        meta, rows = d[0], d[1] or []
        pages = meta["pages"]
        for r in rows:
            if r["value"] is None:
                continue
            c = r["country"]["value"]
            y = int(r["date"])
            if c not in vals or y > vals[c][0]:
                vals[c] = (y, float(r["value"]))
        page += 1
    return pd.Series({k: v[1] for k, v in vals.items()})


def build(refresh: bool = False) -> pd.DataFrame:
    if OUT.exists() and not refresh:
        return pd.read_csv(OUT, index_col=0)
    meta = inputs.load_meta(2025)
    names = sorted(meta.loc[meta.cell_type == "land", "country"]
                   .dropna().unique())
    agri = _wdi("AG.LND.AGRI.ZS", "2023")
    frst = _wdi("AG.LND.FRST.ZS", "2023")
    prot = _wdi("ER.LND.PTLD.ZS", "2020:2025")
    a = _wb_join(agri, names) / 100.0
    f = _wb_join(frst, names) / 100.0
    p = _wb_join(prot, names) / 100.0
    s = ((1 - p) * (1 - f - 0.90 * a)).clip(lower=0)
    # the screening note flags shares above 2% of territory for local
    # geospatial review before they may be treated as plausible; cap
    # the baseline there (and the high case at twice the cap)
    df = pd.DataFrame({"agri_share": a, "forest_share": f,
                       "protected_share": p, "s_eligible": s,
                       "land_baseline": (DEV_BASE * s).clip(upper=0.02),
                       "land_high": (DEV_HIGH * s).clip(upper=0.04)})
    df["capped"] = DEV_BASE * s > 0.02
    med = df.land_baseline.median()
    df["filled"] = df.land_baseline.isna()
    df["land_baseline"] = df.land_baseline.fillna(med)
    df["land_high"] = df.land_high.fillna(2 * med)
    df.round(5).to_csv(OUT)
    print(f"land_screen.csv: {len(df)} countries, "
          f"{int(df.filled.sum())} filled with the median; baseline "
          f"median {med:.2%} of land, IQR "
          f"{df.land_baseline.quantile(.25):.2%}-"
          f"{df.land_baseline.quantile(.75):.2%}")
    return df


def main():
    df = build(refresh="--refresh" in sys.argv)
    from .coreset import CORE30_LIST
    d = df.reindex([c for c in CORE30_LIST if c in df.index])
    print(d[["s_eligible", "land_baseline", "land_high"]]
          .round(4).to_string())


if __name__ == "__main__":
    main()
