"""
regional_prices.py — turn three global markers into a per-country monthly
fossil price, and measure how differently each country is actually exposed.

WHY THIS IS NEEDED
  A world price is not what a buyer pays. Gas is regionally priced: over
  2006-2025 Henry Hub moved 8.5x peak-to-trough, the European marker 44x and
  the Japanese import price 4x. Oil products, by contrast, are globally
  arbitraged, so their regional spread is mostly freight and tax.

MAPPING RULES (documented, not hidden)
  gas   NORTH AMERICA        -> Henry Hub series
        EUROPE + neighbours  -> European (TTF) series
        ASIA importers       -> Japan LNG cif series
        DOMESTIC PRODUCERS   -> a regulated domestic price: these countries do
                                NOT track international markers. Modelled as a
                                low, weakly-linked price (a floor plus a small
                                share of the international move).
        elsewhere            -> the LNG import series (they buy at the margin)
  oil products               -> the global wholesale marker for every country;
                                pre-tax, so national excise is deliberately out.

The producer category matters: Russia, Iran, Saudi Arabia, Algeria, Qatar,
Turkmenistan and others price gas administratively. Applying TTF to them would
invent a shock they never experienced.

From scripts/:  conda run -n synfuel python -m lcof.regional_prices
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import inputs, prices as PR

# ---- country -> gas pricing regime ------------------------------------------
NA = {"United States of America", "Canada", "Mexico"}
EUROPE = {"Germany", "France", "United Kingdom", "Netherlands", "Belgium",
          "Spain", "Italy", "Portugal", "Poland", "Czechia", "Austria",
          "Switzerland", "Denmark", "Sweden", "Norway", "Finland", "Ireland",
          "Greece", "Hungary", "Romania", "Bulgaria", "Slovakia", "Slovenia",
          "Croatia", "Estonia", "Latvia", "Lithuania", "Luxembourg", "Ukraine",
          "Republic of Serbia", "Serbia", "Bosnia and Herzegovina", "Albania",
          "North Macedonia", "Montenegro", "Kosovo", "Moldova", "Belarus",
          "Turkey", "Iceland", "Malta", "Cyprus"}
ASIA_IMPORT = {"Japan", "South Korea", "Taiwan", "China", "India", "Pakistan",
               "Bangladesh", "Thailand", "Vietnam", "Philippines", "Singapore",
               "Sri Lanka", "Nepal", "Cambodia", "Laos", "Myanmar", "Mongolia",
               "New Zealand", "Chile", "Brazil", "Argentina", "Uruguay",
               "Paraguay", "Peru", "Colombia", "Ecuador", "Panama",
               "Dominican Republic", "Jamaica", "Cuba", "Haiti", "Puerto Rico",
               "South Africa", "Kenya", "Morocco", "Jordan",
               "Lebanon", "Tunisia"}
# administratively priced domestic gas: level and how much of the international
# move passes through (0 = fully insulated, 1 = fully linked)
PRODUCER = {
    "Russia": (2.0, 0.10), "Iran": (1.5, 0.05), "Turkmenistan": (1.5, 0.05),
    "Uzbekistan": (2.0, 0.10), "Kazakhstan": (2.5, 0.15),
    "Azerbaijan": (2.5, 0.20), "Saudi Arabia": (1.5, 0.05),
    "Qatar": (1.5, 0.10), "United Arab Emirates": (2.5, 0.20),
    "Kuwait": (2.0, 0.10), "Oman": (2.5, 0.20), "Iraq": (1.5, 0.05),
    "Algeria": (1.5, 0.05), "Libya": (1.5, 0.05), "Egypt": (3.0, 0.25),
    "Nigeria": (2.5, 0.15), "Angola": (2.5, 0.15), "Venezuela": (1.0, 0.05),
    "Bolivia": (2.5, 0.20), "Trinidad and Tobago": (2.5, 0.25),
    # Israel has produced its own gas since Tamar (2013) and Leviathan
    # (2019) and sells it on fixed-price domestic contracts escalated
    # against the generation tariff, reported around $4.7 per MMBtu.
    # The passthrough is lower than Australia's at a similar level
    # because there is no liquefaction terminal, so no LNG netback
    # links the domestic price to the international marker; exports
    # leave by pipeline under long-term contracts. Before Tamar,
    # Israel imported Egyptian pipeline gas, and that supply was
    # repeatedly cut in 2011-12 — one regime per country over the
    # whole window is the convention here, and the forward-looking
    # price is the domestic one.
    "Israel": (4.5, 0.15),
    "Indonesia": (4.0, 0.35), "Malaysia": (4.0, 0.35), "Brunei": (3.0, 0.25),
    "Australia": (5.0, 0.40), "Papua New Guinea": (3.0, 0.25),
}


def gas_regime(country: str) -> str:
    if country in PRODUCER:
        return "producer"
    if country in NA:
        return "henry_hub"
    if country in EUROPE:
        return "ttf"
    if country in ASIA_IMPORT:
        return "lng_import"
    return "lng_import"


def country_gas_series(country: str, g: pd.DataFrame) -> pd.Series:
    """Monthly delivered gas price in $/GJ (LHV) for one country."""
    r = gas_regime(country)
    if r == "henry_hub":
        return g["gas_us"]
    if r == "ttf":
        return g["gas_eu"]
    if r == "lng_import":
        return g["lng_jp"]
    base, passthrough = PRODUCER[country]
    intl = g["lng_jp"]
    return base + passthrough * (intl - intl.median())


def build(window=("2006", "2025")) -> pd.DataFrame:
    g = PR.load(verified=True).loc[window[0]:window[1]]
    meta = inputs.load_meta(2025)
    land = meta[meta.cell_type == "land"]
    rows = []
    for c in sorted(land.country.dropna().unique()):
        gas = country_gas_series(c, g).dropna()
        rows.append(dict(
            country=c, regime=gas_regime(c),
            gas_min=gas.min(), gas_med=gas.median(), gas_max=gas.max(),
            gas_ratio=gas.max() / gas.min(),
            gas_cv=gas.std() / gas.mean(),
            diesel_med=g["diesel"].median(), diesel_max=g["diesel"].max(),
            diesel_ratio=g["diesel"].max() / g["diesel"].min()))
    return pd.DataFrame(rows).set_index("country")


def main():
    df = build()
    out = inputs.MAPS / "country_fossil_exposure.csv"
    df.round(3).to_csv(out)
    M = PR.MMBTU_PER_GJ
    print("countries by gas pricing regime:")
    print(df.regime.value_counts().to_string())
    print("\nvolatility of the gas price each country actually faces:")
    print(f"{'regime':12s} {'median $/MMBtu':>15s} {'peak/trough':>12s} {'CV':>7s}")
    for r, s in df.groupby("regime"):
        print(f"{r:12s} {s.gas_med.median()*M:15.2f} {s.gas_ratio.median():12.1f}"
              f" {s.gas_cv.median():7.2f}")
    print("\nexamples ($/MMBtu, LHV):")
    for c in ("United States of America", "Germany", "Japan", "China",
              "Russia", "Saudi Arabia", "Australia", "Kenya"):
        if c in df.index:
            r = df.loc[c]
            print(f"  {c:26s} {r.regime:11s} med {r.gas_med*M:6.2f} "
                  f"max {r.gas_max*M:7.2f}  x{r.gas_ratio:5.1f}  CV {r.gas_cv:.2f}")
    print(f"\nwrote {out}")
    print("\nNOTE oil products use one global wholesale marker for every country "
          f"(median {df.diesel_med.iloc[0]*M:.2f}, peak {df.diesel_max.iloc[0]*M:.2f} "
          f"$/MMBtu, x{df.diesel_ratio.iloc[0]:.1f}) — pre-tax, so national "
          "excise is deliberately excluded.")


if __name__ == "__main__":
    main()
