"""
demand.py — the measured demand layer for the security ledger.

Extracts, per country, the latest observed year of fossil-fuel CONSUMPTION
(oil, gas, coal, TWh -> GJ) and total primary energy use from the OWID
energy dataset (BP/EI Statistical Review lineage). This replaces two v1
proxies at once: E_use inferred from the net-import share (now measured),
and the missing demand bound on SaR (unserved energy cannot exceed what the
country actually consumes).

From scripts/:  conda run -n synfuel python -u -m lcof.demand
Writes data/cost/demand_by_fuel.csv
"""
from __future__ import annotations

import pandas as pd

from . import inputs

TWH_TO_GJ = 3.6e6

# OWID names -> the country names the rest of the repo uses
RENAME = {"United States": "United States of America",
          "Czechia": "Czechia", "Turkey": "Turkey",
          "Democratic Republic of Congo":
              "Democratic Republic of the Congo",
          "Congo": "Republic of the Congo",
          # 2026-09-26: these three used to miss every join
          "Serbia": "Republic of Serbia",
          "Tanzania": "United Republic of Tanzania",
          "Bahamas": "The Bahamas"}


EI_VARS = {"primary_gj": "tes_ej", "oil_gj": "oil_tes_ej", "gas_gj": "gas_tes_ej",
           "coal_gj": "coal_tes_ej"}


def _to_2025(out: pd.DataFrame, owid: pd.DataFrame) -> None:
    """2026-10-07: carry each country's OWID level forward to 2025 with the
    Energy Institute Statistical Review 2026 growth from the OWID year to 2025,
    fuel by fuel, so the value of fuel lost (GDP per unit of energy use) pairs
    2025 GDP with 2025 energy use while keeping one accounting method (OWID's)
    across countries. Countries the Review does not list keep their latest
    OWID year (column year_energy records which)."""
    ei = pd.read_csv(inputs.PROJECT / "data" / "demand" / "ei_2026" /
                     "Statistical Review of World Energy Narrow format.csv", low_memory=False)
    ei = ei[ei.Var.isin(EI_VARS.values()) & ei.ISO3166_alpha3.notna()]
    iso = (owid.dropna(subset=["iso_code"]).drop_duplicates("country")
           .set_index("country").iso_code)
    out["year_energy"] = out.year
    for c in out.index:
        code = iso.get(c)
        if not isinstance(code, str):
            continue
        e = ei[ei.ISO3166_alpha3 == code]
        if e.empty:
            continue
        y0 = int(out.at[c, "year"])
        moved = False
        for col, var in EI_VARS.items():
            s = e[e.Var == var].set_index("Year").Value
            if 2025 in s.index and y0 in s.index and s[y0] > 0:
                out.at[c, col] = out.at[c, col] * s[2025] / s[y0]
                moved = True
        if moved:
            out.at[c, "year_energy"] = 2025


def build() -> pd.DataFrame:
    d = pd.read_csv(inputs.MAPS / "owid_energy.csv",
                    usecols=["country", "iso_code", "year", "oil_consumption",
                             "gas_consumption", "coal_consumption",
                             "primary_energy_consumption",
                             "energy_per_gdp"])
    d = d.replace({"country": RENAME})
    keep = []
    for c, g in d[d.year >= 2015].groupby("country"):
        g = g.dropna(subset=["primary_energy_consumption"])
        if not len(g):
            continue
        r = g.sort_values("year").iloc[-1]
        keep.append(dict(
            country=c, year=int(r.year),
            oil_gj=(r.oil_consumption or 0) * TWH_TO_GJ,
            gas_gj=(r.gas_consumption or 0) * TWH_TO_GJ,
            coal_gj=(r.coal_consumption or 0) * TWH_TO_GJ,
            primary_gj=r.primary_energy_consumption * TWH_TO_GJ))
    out = pd.DataFrame(keep).set_index("country")

    # observed DECOUPLING drift: CAGR of GDP-per-energy = -CAGR of
    # energy_per_gdp over ~25 years. This is the growth rate of the value a
    # lost GJ destroys — the dynamics of CoDF — and it is an OBSERVED trend,
    # not a forecast, extrapolated only as a declared scenario axis.
    drift = {}
    for c, g in d[d.year >= 1995].groupby("country"):
        g = g.dropna(subset=["energy_per_gdp"]).sort_values("year")
        if len(g) < 15:
            continue
        y0, y1 = g.iloc[0], g.iloc[-1]
        n = y1.year - y0.year
        if n >= 15 and y0.energy_per_gdp > 0 and y1.energy_per_gdp > 0:
            drift[c] = (y0.energy_per_gdp / y1.energy_per_gdp) ** (1 / n) - 1
    out["codf_drift"] = pd.Series(drift).clip(-0.01, 0.05)
    _to_2025(out, d)
    out["fossil_gj"] = out[["oil_gj", "gas_gj", "coal_gj"]].sum(axis=1)
    out.to_csv(inputs.MAPS / "demand_by_fuel.csv")
    return out


def main():
    out = build()
    print(f"demand layer: {len(out)} countries, data years "
          f"{out.year.min()}-{out.year.max()}")
    w = out.loc[out.index == "World"]
    if len(w):
        print(f"world fossil demand {w.fossil_gj.iloc[0]/1e9:.0f} EJ "
              f"(sanity: ~490 EJ expected)")
    assert (out.fossil_gj <= out.primary_gj * 1.05 + 1e9).all(), \
        "fossil exceeds primary somewhere"
    print("DEMAND LAYER CHECKS PASSED")


if __name__ == "__main__":
    main()
