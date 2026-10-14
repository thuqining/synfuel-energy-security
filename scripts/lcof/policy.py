"""
policy.py — policy-adjusted competitiveness of synthetic fuels.

Core metric: BREAK-EVEN CARBON PRICE per country and fuel,

    tau*_f(c) = (LCOF_f(c) - p_fossil_f(c)) / (EF_fossil_f - EF_synfuel_f)

= the carbon price [$ / t CO2] at which the synthetic fuel reaches cost parity
with its fossil counterpart at that location.  Compared against ACTUAL 2025
carbon prices (EU ETS etc.) it answers "where does existing policy already
close the gap" without assuming any hypothetical tax level.

Fairness rules implemented:
  * symmetric carbon pricing: fossil pays for its combustion CO2; the synfuel
    is credited only in the climate-neutral CO2 case (EF_syn = 0); with
    industrial CO2 the fuel re-emits fossil carbon once -> EF_syn = half the
    combustion EF (carbon used twice before release).
  * same value-chain point: wholesale prices, excise taxes excluded.
  * subsidies (45V-style) are transfers, not resource costs -> reported as a
    separate wedge, never inside LCOF.

All prices $/GJ (LHV); emission factors t CO2 per GJ (combustion, IPCC).
Fossil reference prices are 2025 wholesale levels (update as needed).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# ---- combustion emission factors, t CO2 / GJ (IPCC 2006 defaults) ------------
EF = {"diesel": 0.0741, "kerosene": 0.0715, "natgas": 0.0561, "coal": 0.0946,
      # production-chain EF for the non-combusted comparators:
      "grey_h2": 0.080,      # SMR ~9.5 kg CO2/kg H2
      "grey_nh3": 0.129,     # SMR Haber-Bosch ~2.4 t CO2/t NH3
      "fuel_oil": 0.0774}    # residual fuel oil, IPCC 2006

# ---- fossil comparator: (price $/GJ, EF key) ---------------------------------
# gas-linked comparators (grey H2/NH3, e-methane) are priced off the REGIONAL
# gas price so high-gas-price regions face an equally expensive fossil
# counterpart (symmetry rule); oil products are world-market.
FOSSIL = {
    "hydrogen":  dict(price="grey_h2",  ef="grey_h2",  label="grey H2 (SMR, regional gas)"),
    "ammonia":   dict(price="grey_nh3", ef="grey_nh3", label="grey NH3 (SMR, regional gas)"),
    "methanol":  dict(price=15.1, ef="diesel",   label="fossil MeOH $300/t"),
    "e-methane": dict(price=None, ef="natgas",   label="regional natural gas"),
    "e-diesel":  dict(price=15.4, ef="diesel",   label="wholesale diesel $0.55/L"),
    "e-kerosene": dict(price=14.8, ef="kerosene", label="wholesale jet $0.52/L"),
    "ethanol":   dict(price=15.4, ef="diesel",   label="vs diesel (fuel use)"),
    "marine":    dict(price="hsfo", ef="fuel_oil", label="marine fuel oil (Singapore HSFO 380 cst)"),
}


def grey_h2_price(country: str, verified: bool = True) -> float:
    """Incumbent hydrogen $/GJ. From the verified panel where available (which
    also blends coal gasification where that is the route actually used);
    otherwise gas/eta + a non-fuel adder (capex+O&M ~ $4/GJ)."""
    if verified:
        v = _verified().get(country)
        if v is not None:
            return v[1]
    return gas_price(country, verified=False) / 0.72 + 4.0


def grey_nh3_price(country: str, verified: bool = True) -> float:
    """SMR Haber-Bosch ammonia $/GJ: 1.16 GJ_H2/GJ_NH3 (same 180 kg H2/t
    chemistry as the green route — symmetry) + synthesis ~ $3.5/GJ."""
    if verified:
        v = _verified().get(country)
        if v is not None:
            return v[2]
    return 1.16 * grey_h2_price(country, verified=False) + 3.5

# regional wholesale natural-gas price, $/GJ (2025 approx: HH ~3.5, TTF ~9.5)
GAS_REGION = {
    "North America": 3.5, "Middle East": 3.0, "Russia+CIS": 3.5, "Europe": 9.5,
    "Asia importer": 10.5, "Latin America": 6.0, "Africa": 5.0, "Oceania": 8.0,
}
GAS_GROUP = {
    "United States of America": "North America", "Canada": "North America",
    "Mexico": "North America", "Saudi Arabia": "Middle East", "Iran": "Middle East",
    "Iraq": "Middle East", "Qatar": "Middle East", "United Arab Emirates": "Middle East",
    "Kuwait": "Middle East", "Oman": "Middle East", "Russia": "Russia+CIS",
    "Kazakhstan": "Russia+CIS", "Turkmenistan": "Russia+CIS", "Uzbekistan": "Russia+CIS",
    "Azerbaijan": "Russia+CIS", "Algeria": "Africa", "Egypt": "Africa",
    "Nigeria": "Africa", "Libya": "Africa", "Australia": "Oceania",
    "New Zealand": "Oceania", "Japan": "Asia importer", "South Korea": "Asia importer",
    "China": "Asia importer", "India": "Asia importer", "Taiwan": "Asia importer",
    "Argentina": "Latin America", "Brazil": "Latin America", "Chile": "Latin America",
    "Bolivia": "Latin America", "Peru": "Latin America", "Colombia": "Latin America",
}
EUROPE = {"Germany","France","United Kingdom","Netherlands","Belgium","Spain","Italy",
          "Portugal","Poland","Czechia","Austria","Switzerland","Denmark","Sweden",
          "Norway","Finland","Ireland","Greece","Hungary","Romania","Bulgaria",
          "Slovakia","Slovenia","Croatia","Estonia","Latvia","Lithuania","Luxembourg",
          "Ukraine","Serbia","Turkey"}


# ---- verified benchmark, preferred over the regional table above -------------
# The GAS_REGION table is a coarse 2025 estimate written before the price panel
# was downloaded, and it is wrong by up to a factor of two (Chile 6.3 against an
# actual 13.4 $/MMBtu).  gap.py builds a monthly, country-level panel from the
# World Bank Pink Sheet, EIA, Eurostat and ECB series; take the 20-year median
# month from there and fall back to the table only for countries the panel does
# not cover.  Loaded lazily so importing policy.py stays cheap.
_VERIFIED: dict | None = None


def _verified() -> dict:
    """{country: (gas, grey_H2, grey_NH3)} $/GJ LHV, median month 2006-2025."""
    global _VERIFIED
    if _VERIFIED is None:
        from .gap import (country_gas_monthly, grey_h2, NH3_H2_INTENSITY,
                          NH3_NONFUEL)
        gasdf, g = country_gas_monthly()
        _VERIFIED = {}
        for c in gasdf.columns:
            h2 = grey_h2(c, gasdf[c], g)
            _VERIFIED[c] = (float(gasdf[c].median()), float(h2.median()),
                            float((NH3_H2_INTENSITY * h2 + NH3_NONFUEL).median()))
    return _VERIFIED


def gas_price(country: str, verified: bool = True) -> float:
    if verified:
        v = _verified().get(country)
        if v is not None:
            return v[0]
    if country in EUROPE:
        return GAS_REGION["Europe"]
    return GAS_REGION.get(GAS_GROUP.get(country, ""), 7.0)   # default mid


# ---- carbon prices in force in 2025, US$/t CO2 ---------------------------------
# 2026-10-08 ("all countries at the latest market price, check them all"): emissions
# trading systems at their 2025 full-year average, carbon taxes at the 2025 statutory rate,
# converted at 2025 average exchange rates (ECB / Bank of Finland: EUR 1.13, GBP 1.32,
# JPY 149.6, CNY 7.18, KRW ~1,420, ZAR 17.9 per USD-equivalent). One price per economy, applied
# to every fuel use (an upper bound on coverage, see Methods). Previous values (World Bank
# dashboard approximations, 2024) in comments.
EU_ETS_2025 = 74.40 * 1.13          # front-Dec EUA 2025 average EUR 74.40 (LSEG)       [was 80]
CARBON_PRICE = {
    **{c: round(EU_ETS_2025, 1) for c in (
        "Germany", "France", "Netherlands", "Belgium", "Spain", "Italy", "Portugal", "Poland",
        "Czechia", "Austria", "Denmark", "Sweden", "Finland", "Ireland", "Greece", "Hungary",
        "Romania", "Bulgaria", "Slovakia", "Slovenia", "Croatia", "Estonia", "Latvia",
        "Lithuania", "Luxembourg", "Cyprus", "Malta", "Iceland")},
    "Norway": round(EU_ETS_2025, 1),     # EU ETS (EEA); national CO2 tax on top not added   [was 90]
    "United Kingdom": round(49.41 * 1.32, 1),   # UK ETS: GBP 49.41, mean UKA settlement over the
                                                # 12 months to 11 Nov 2025 (GOV.UK)       [was 50]
    "China": round(62.36 / 7.18, 1),     # national ETS, CEA 2025 average CNY 62.36 (LSEG)  [was 13]
    "South Korea": round(9500 / 1420, 1),  # K-ETS, KAU 2025 traded KRW ~8,600-12,750; ~9,500 [was 8]
    "Japan": round(289 / 149.6, 1),      # Tax for climate change mitigation JPY 289/t; GX-ETS
                                         # compulsory only from April 2026              [was 10]
    "Australia": round(35.5 * 0.645, 1),  # Safeguard Mechanism, ACCU spot ~AUD 35.5 (CER)   [was 22]
    "South Africa": round(236 / 17.9, 1),  # Carbon Tax Act headline rate R236/t for 2025      [was 9]
    "Chile": 5.0,                        # green tax US$5/t (unchanged)
    "United States of America": 28.0,    # California cap-and-trade, 2025 auction mean US$28.1;
                                         # no federal price (regional upper bound)      [was 15]
    "Canada": round(95 / 1.40, 1),       # federal OBPS benchmark CAD 95/t (consumer charge
                                         # removed April 2025)                          [was 65]
    "Switzerland": round(120 / 0.83, 1),  # CO2 levy CHF 120/t                             [was 130]
    "New Zealand": 35.0, "Mexico": 4.0,  # not re-verified (outside the assessed core)
    "Indonesia": 2.4,                    # power-sector ETS, IDXCarbon H1-2025 mean ~IDR 39,500/t [new]
    # Israel: a carbon levy began in 2025 through excise on coal, gas, LPG and fuel oil only (motor
    # fuels excluded, no per-tonne-CO2 rate published) -> not added for the displaced fuels.
}


def breakeven(lcof_gj: float, fuel: str, country: str,
              carbon_case: str = "neutral", p_fossil: float | None = None) -> dict:
    """tau* [$/t CO2] for one fuel at one site + the actual local carbon price.

    carbon_case 'neutral'   : biogenic/DAC CO2, EF_syn = 0
                'industrial': fossil point-source CO2 reused once -> EF_syn =
                              0.5 x combustion EF of the fuel itself
    """
    f = FOSSIL[fuel]
    if p_fossil is not None:
        pass                      # caller supplies the comparator
    elif f["price"] is None:
        p_fossil = gas_price(country)
    elif f["price"] == "grey_h2":
        p_fossil = grey_h2_price(country)
    elif f["price"] == "grey_nh3":
        p_fossil = grey_nh3_price(country)
    else:
        p_fossil = f["price"]
    ef_fossil = EF[f["ef"]]
    ef_syn = 0.0
    if carbon_case == "industrial" and f["ef"] in ("diesel", "kerosene", "natgas"):
        ef_syn = 0.5 * EF[f["ef"]]
    d_ef = ef_fossil - ef_syn
    tau = (lcof_gj - p_fossil) / d_ef if d_ef > 0 else np.nan
    actual = CARBON_PRICE.get(country, 0.0)
    return {"fuel": fuel, "country": country, "carbon_case": carbon_case,
            "lcof_usd_gj": lcof_gj, "p_fossil_usd_gj": p_fossil,
            "fossil_ref": f["label"], "delta_ef_t_gj": d_ef,
            "tau_star_usd_t": tau, "carbon_price_now": actual,
            "competitive_now": bool(np.isfinite(tau) and tau <= actual)}


def breakeven_table(fuels_csv: str | pd.DataFrame,
                    carbon_case: str = "neutral") -> pd.DataFrame:
    """tau* for every country in a lcof_countries_fuels CSV (same carbon case
    used for the LCOF pick and for EF_syn)."""
    df = fuels_csv if isinstance(fuels_csv, pd.DataFrame) else pd.read_csv(fuels_csv)
    rows = []
    sel = df[df.carbon_case == carbon_case]
    for _, r in sel.iterrows():
        rows.append(breakeven(r["lcof_usd_gj"], r["fuel"], r["country"], carbon_case))
    return pd.DataFrame(rows)
