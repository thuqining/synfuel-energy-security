"""
ammonia_consumption.py -- national apparent consumption of ammonia (2026-10-07).

Replaces the earlier allocation of world ammonia to countries by EDGAR's
chemical-sector CO2, which credited large petrochemical economies with
ammonia they do not use (Saudi Arabia, South Korea, Japan) and missed
importers that have no chemical CO2 (Morocco). Apparent consumption is the
standard industry measure:

    consumption = production + imports - exports          (t NH3, 2025)

  2026-10-07 (b): moved to the latest data. Production is the 2025 estimate
  of USGS Mineral Commodity Summaries 2026 (Nitrogen, "World ammonia
  production") for the 22 listed countries; the "Other countries" total
  (12,000 kt N) is shared out in proportion to their 2023 Minerals Yearbook
  production. Trade is each reporter's latest Comtrade year, 2025, else 2024,
  else 2023; a mirror flow sums each partner's latest reported year.

  production  USGS Minerals Yearbook 2023, Nitrogen, Table 12 "Ammonia:
              world production, by country or locality" (kt N; x 17/14).
              Countries not listed produced none (USGS note: only Taiwan and
              Tajikistan may have produced ammonia without an estimate).
  trade       UN Comtrade, HS 281410 (anhydrous ammonia), 2023, reporter
              totals with partner World; for producers that do not report
              their exports (Russia, Algeria, Qatar, ...) the mirror flow,
              i.e. the imports their partners report from them.

Consumption is clipped at zero and rescaled so the world total equals the
2025 world production of the demand grid (USGS MCS 2026, 194.3 Mt NH3).
Writes data/cost/ammonia_consumption.csv.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import inputs

U = inputs.PROJECT / "data" / "demand" / "usgs"
NH3_PER_N = 17.0 / 14.0

# names in the USGS table and in Comtrade -> the model's country names
NAME = {"United States": "United States of America", "USA": "United States of America",
        "Franc": "France", "Greec": "Greece", "Ukrain": "Ukraine",
        "Korea, North": "North Korea", "Rep. of Korea": "South Korea",
        "Türkiye": "Turkey", "T\u7709rkiye": "Turkey", "Viet Nam": "Vietnam",
        "Dominican Rep.": "Dominican Republic", "Bosnia Herzegovina": "Bosnia and Herzegovina",
        "Côte d'Ivoire": "Ivory Coast", "C\u4e48te d'Ivoire": "Ivory Coast",
        "Dem. Rep. of the Congo": "Democratic Republic of the Congo",
        "Congo": "Republic of the Congo", "Lao People's Dem. Rep.": "Laos",
        "United Rep. of Tanzania": "United Republic of Tanzania", "Serbia": "Republic of Serbia",
        "Bolivia (Plurinational State of)": "Bolivia", "Bahamas": "The Bahamas",
        "Timor-Leste": "East Timor", "Rep. of Moldova": "Moldova", "Other Asia, nes": "Taiwan",
        "Cabo Verde": "Cabo Verde", "Central African Rep.": "Central African Republic"}
# producers whose exports reach Comtrade only through their partners
MIRROR = ["Russia", "Algeria", "Qatar", "Libya", "Nigeria", "Bahrain", "Argentina",
          "Mexico", "Bangladesh"]


def _name(s: str) -> str:
    s = str(s).strip()
    return NAME.get(s, s)


# USGS Mineral Commodity Summaries 2026, Nitrogen: plant production 2025e, kt N
MCS2026_2025 = {"United States of America": 14000, "Algeria": 2000, "Australia": 1500,
                "Canada": 3800, "China": 49000, "Egypt": 4000, "Germany": 2000, "India": 15000,
                "Indonesia": 6000, "Iran": 4800, "Malaysia": 1500, "Netherlands": 2000,
                "Nigeria": 2000, "Oman": 2000, "Pakistan": 3800, "Poland": 1700, "Qatar": 3000,
                "Russia": 15000, "Saudi Arabia": 5200, "Trinidad and Tobago": 3300,
                "Uzbekistan": 1300, "Vietnam": 1400}
MCS2026_OTHER = 12000
YEARS = (2025, 2024, 2023)


def production_2025_t() -> pd.Series:
    """2025 production, t NH3: MCS 2026 for the listed countries, the rest of
    the MCS 'Other countries' total by 2023 Minerals Yearbook shares"""
    p23 = production_t()
    listed = pd.Series(MCS2026_2025, dtype=float)
    assert all(c in p23.index for c in listed.index), [c for c in listed.index if c not in p23.index]
    other = p23.drop(listed.index)
    other = other / other.sum() * MCS2026_OTHER * 1e3 * NH3_PER_N
    return pd.concat([listed * 1e3 * NH3_PER_N, other])


def production_t() -> pd.Series:
    t = pd.read_excel(U / "myb1-2023-nitro-ERT.xlsx", "T12", header=None).iloc[6:69, [0, 10]]
    t.columns = ["country", "n_kt"]
    # footnote markers: trailing digits and the 'e' (estimated) flag on the name
    t["country"] = (t.country.astype(str).str.replace(r"\d+$", "", regex=True)
                    .str.replace(r"(?<=[a-z])e$", "", regex=True).str.strip())
    t["country"] = t.country.map(_name)
    t["n_kt"] = pd.to_numeric(t.n_kt, errors="coerce").fillna(0.0)    # '--' = zero
    return t.set_index("country").n_kt * 1e3 * NH3_PER_N


def _kg(d: pd.DataFrame) -> pd.Series:
    # net weight in kg; where a reporter gives none (Korea, Morocco, Chile) the
    # alternative quantity, which Comtrade states in kg for this code
    return d.netWgt.where(d.netWgt > 0, d.qty.where(d.qty > 0, d.altQty))


def _comtrade_year(flow: str, year: int) -> pd.Series:
    d = pd.DataFrame(json.load(open(U / f"comtrade_281410_{year}_{flow}.json", encoding="utf-8"))["data"])
    return pd.Series(_kg(d).to_numpy() / 1e3, index=d.reporterDesc.map(_name)).groupby(level=0).sum()


LATEST_YEAR = {}


def _comtrade(flow: str) -> pd.Series:
    """each reporter's latest reported year, 2025 else 2024 else 2023 (t)"""
    out = pd.Series(dtype=float)
    for y in YEARS:
        s = _comtrade_year(flow, y)
        new = s.index.difference(out.index)
        out = pd.concat([out, s[new]])
        for c in new:
            LATEST_YEAR[(flow, c)] = y
    return out


def _mirror(country: str) -> float:
    """imports partners report from `country`, each partner at its latest year (t)"""
    got, total = set(), 0.0
    for y in YEARS:
        f = U / f"mirror_281410_{y}_{country}.json"
        if not f.exists():
            continue
        d = pd.DataFrame(json.load(open(f, encoding="utf-8"))["data"])
        if d.empty:
            continue
        d = d.assign(kg=_kg(d)).groupby("reporterCode").kg.sum()
        new = d.index.difference(list(got))
        total += float(d[new].sum())
        got |= set(new)
    return total / 1e3 if got else np.nan


def build(world_t: float = 160.0e6 * NH3_PER_N, write: bool = True) -> pd.DataFrame:
    prod = production_2025_t()
    imp, exp = _comtrade("M"), _comtrade("X")
    idx = prod.index.union(imp.index).union(exp.index)
    df = pd.DataFrame({"production_t": prod.reindex(idx).fillna(0.0),
                       "imports_t": imp.reindex(idx).fillna(0.0),
                       "exports_t": exp.reindex(idx)})
    df["exports_source"] = np.where(df.exports_t.notna(), "reported", "none reported")
    for c in MIRROR:
        if c in df.index and not np.isfinite(df.at[c, "exports_t"]):
            df.at[c, "exports_t"] = _mirror(c)
            df.at[c, "exports_source"] = "mirror (partner imports)"
    df["exports_t"] = df.exports_t.fillna(0.0)
    df["imports_year"] = [LATEST_YEAR.get(("M", c), np.nan) for c in df.index]
    df["exports_year"] = [LATEST_YEAR.get(("X", c), np.nan) for c in df.index]
    df["consumption_raw_t"] = (df.production_t + df.imports_t - df.exports_t).clip(lower=0.0)
    scale = world_t / df.consumption_raw_t.sum()
    df["consumption_t"] = df.consumption_raw_t * scale
    print(f"apparent consumption: {df.consumption_raw_t.sum() / 1e6:.1f} Mt NH3 "
          f"(world production {df.production_t.sum() / 1e6:.1f} Mt); scaled x{scale:.3f} "
          f"to the 2025 world total {world_t / 1e6:.1f} Mt")
    if write:
        df.round(1).to_csv(inputs.MAPS / "ammonia_consumption.csv", index_label="country")
    return df


if __name__ == "__main__":
    d = build()
    print(d.sort_values("consumption_t", ascending=False).head(30)
          .assign(**{k: lambda x, k=k: (x[k] / 1e6).round(2) for k in
                     ["production_t", "imports_t", "exports_t", "consumption_t"]})
          [["production_t", "imports_t", "exports_t", "exports_source", "consumption_t"]].to_string())
