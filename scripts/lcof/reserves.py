"""
reserves.py — strategic and commercial oil stocks as a security BUFFER.

Reserves enter the ledger twice. As a VALUATION anchor they are already
in: the revealed-preference band of the MACC is priced from what states
pay for strategic stocks. What was missing is the BUFFER role: a country
holding S days of net-import cover only suffers the part of a disruption
that outlasts its stocks, so its expected disrupted share q_eff shrinks by

  phi_oil = sum_s r_s * max(0, D_s - S) / sum_s r_s * D_s

over the catalogue's scenario classes (supplier cut-off and chokepoint,
central rate and median duration from the 2000-2026 events: about
0.26/yr for 8 months and 0.15/yr for 3.5 months) — the same rates and
durations that built q_eff. Blended across services by the country's oil
share of import exposure (gas storage data is EU/US-only, so gas is left
UNBUFFERED — conservative in the direction that overstates the stock
benefit's absence, i.e. reserve-adjusted parity years shown are an upper
bound on the delay):

  phi_c = oil_share_c * phi_oil_c + (1 - oil_share_c) * 1.0

Reserve-adjusted security parity then uses threshold thr' = thr * phi_c.

Data: JODI-Oil world database (https://www.jodidata.org/oil/), monthly
closing stocks (CLOSTLV) and trade flows, ~100 countries, KBBL; stocks
include government AND industry holdings. Mean over the last 24 reported
months. Products = TOTCRUDE + TOTPRODS. Fuel-product stockpiles
(methanol / ammonia) have no public global inventory data — but strategic
stocks exist only on the fossil side, which is where the modelled
disruption bites; a synthetic plant is a buffer of unlimited duration.

From scripts/:  conda run -n synfuel python -u -m lcof.reserves
Output: data/cost/reserves_cover.csv (country, days_cover_oil, phi)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import inputs

RES = inputs.PROJECT / "data" / "reserves"

# scenario classes DERIVED from the same event catalogue security.py
# uses (rate = central events/yr, duration = median months -> days),
# so an edit to security_events.csv cannot leave this module behind
# (the old hard-coded pair (0.157, 240), (0.10, 180) drifted silently)
from .security import _scenario_rates as _sc_rates

_sc, _n_ev = _sc_rates()
CLASSES = [(float(np.sqrt(_sc[t][0][0] * _sc[t][0][1])),
            float(_sc[t][1]) * 30.44) for t in ("s1", "s2")]

# JODI REF_AREA (ISO2) -> Natural-Earth style country names used everywhere
ISO2 = {
    "AE": "United Arab Emirates", "AL": "Albania", "AO": "Angola",
    "AR": "Argentina", "AT": "Austria", "AU": "Australia",
    "AZ": "Azerbaijan", "BA": "Bosnia and Herzegovina", "BD": "Bangladesh",
    "BE": "Belgium", "BG": "Bulgaria", "BH": "Bahrain", "BN": "Brunei",
    "BO": "Bolivia", "BR": "Brazil", "BY": "Belarus", "CA": "Canada",
    "CH": "Switzerland", "CL": "Chile", "CN": "China", "CO": "Colombia",
    "CR": "Costa Rica", "CY": "Cyprus", "CZ": "Czechia",
    "DE": "Germany", "DK": "Denmark", "DO": "Dominican Republic",
    "DZ": "Algeria", "EC": "Ecuador", "EE": "Estonia", "EG": "Egypt",
    "ES": "Spain", "ET": "Ethiopia", "FI": "Finland", "FR": "France",
    "GB": "United Kingdom", "GE": "Georgia", "GH": "Ghana",
    "GR": "Greece", "GT": "Guatemala", "HN": "Honduras", "HR": "Croatia",
    "HU": "Hungary", "ID": "Indonesia", "IE": "Ireland", "IL": "Israel",
    "IN": "India", "IQ": "Iraq", "IR": "Iran", "IS": "Iceland",
    "IT": "Italy", "JM": "Jamaica", "JO": "Jordan", "JP": "Japan",
    "KE": "Kenya", "KR": "South Korea", "KW": "Kuwait",
    "KZ": "Kazakhstan", "LB": "Lebanon", "LK": "Sri Lanka",
    "LT": "Lithuania", "LU": "Luxembourg", "LV": "Latvia", "LY": "Libya",
    "MA": "Morocco", "MD": "Moldova", "MK": "North Macedonia",
    "MM": "Myanmar", "MN": "Mongolia", "MX": "Mexico", "MY": "Malaysia",
    "NE": "Niger", "NG": "Nigeria", "NI": "Nicaragua",
    "NL": "Netherlands", "NO": "Norway", "NZ": "New Zealand",
    "OM": "Oman", "PA": "Panama", "PE": "Peru", "PH": "Philippines",
    "PK": "Pakistan", "PL": "Poland", "PT": "Portugal", "PY": "Paraguay",
    "QA": "Qatar", "RO": "Romania", "RS": "Serbia", "RU": "Russia",
    "SA": "Saudi Arabia", "SD": "Sudan", "SE": "Sweden",
    "SG": "Singapore", "SI": "Slovenia", "SK": "Slovakia",
    "SV": "El Salvador", "SY": "Syria", "TH": "Thailand",
    "TN": "Tunisia", "TR": "Turkey", "TT": "Trinidad and Tobago",
    "TW": "Taiwan", "TZ": "United Republic of Tanzania", "UA": "Ukraine",
    "US": "United States of America", "UY": "Uruguay",
    "UZ": "Uzbekistan", "VE": "Venezuela", "VN": "Vietnam",
    "YE": "Yemen", "ZA": "South Africa",
}


def _load(kind: str, product: str) -> pd.DataFrame:
    """KBBL and CONVBBL are complementary — each country reports in one;
    combine with native barrels taking precedence."""
    frames = []
    for y in (2023, 2024, 2025):
        d = pd.read_csv(RES / f"{kind}_{y}.csv")
        d = d[(d.ENERGY_PRODUCT == product)
              & d.UNIT_MEASURE.isin(["KBBL", "CONVBBL"])]
        frames.append(d)
    d = pd.concat(frames)
    d["v"] = pd.to_numeric(d.OBS_VALUE, errors="coerce")
    return d.dropna(subset=["v"])


def build() -> pd.DataFrame:
    parts = {}
    for kind, product in (("primary", "CRUDEOIL"),
                          ("secondary", "TOTPRODS")):
        d = _load(kind, product)
        pivs = {u: d[d.UNIT_MEASURE == u].pivot_table(
            index=["REF_AREA", "TIME_PERIOD"],
            columns="FLOW_BREAKDOWN", values="v", aggfunc="first")
            for u in ("KBBL", "CONVBBL")}
        parts[kind] = pivs["KBBL"].combine_first(pivs["CONVBBL"])
    out = []
    for iso, name in ISO2.items():
        rows = []
        for kind in ("primary", "secondary"):
            piv = parts[kind]
            if iso not in piv.index.get_level_values(0):
                continue
            p = piv.loc[iso].sort_index().tail(24)
            rows.append(p)
        if not rows:
            continue
        stock = sum(float(p["CLOSTLV"].mean()) for p in rows
                    if "CLOSTLV" in p and np.isfinite(p["CLOSTLV"].mean()))
        imp = sum(float(p["TOTIMPSB"].mean()) for p in rows
                  if "TOTIMPSB" in p
                  and np.isfinite(p["TOTIMPSB"].mean()))
        exp = sum(float(p["TOTEXPSB"].mean()) for p in rows
                  if "TOTEXPSB" in p
                  and np.isfinite(p["TOTEXPSB"].mean()))
        net_day = (imp - exp) / 30.44          # KBBL/month -> KBBL/day
        if stock <= 0:
            continue
        days = np.inf if net_day <= 0.5 else stock / net_day
        out.append((name, stock, net_day, days))
    df = pd.DataFrame(out, columns=["country", "stock_kbbl",
                                    "net_imp_kbd", "days_cover_oil"]
                      ).set_index("country")

    # phi_oil per country, then blend by the ledger's oil exposure share
    def phi_oil(S):
        if not np.isfinite(S):
            return 0.0
        num = sum(r * max(0.0, D - S) for r, D in CLASSES)
        den = sum(r * D for r, D in CLASSES)
        return num / den

    df["phi_oil"] = df.days_cover_oil.map(phi_oil)
    sec = pd.read_csv(inputs.MAPS / "security_index.csv", index_col=0)
    osh = sec.oil_share.clip(0, 1)
    df["phi"] = (osh.reindex(df.index).fillna(0.5) * df.phi_oil
                 + (1 - osh.reindex(df.index).fillna(0.5)) * 1.0)

    # ---- audits -----------------------------------------------------------
    imp_ctys = df[np.isfinite(df.days_cover_oil)]
    med = imp_ctys.days_cover_oil.median()
    print(f"{len(df)} countries with stock data; importers "
          f"{len(imp_ctys)}; median days of oil cover {med:.0f}")
    for c in ("United States of America", "Japan", "China", "Germany"):
        if c in df.index:
            print(f"  {c:28s} {df.loc[c, 'days_cover_oil']:6.0f} d "
                  f"phi_oil {df.loc[c, 'phi_oil']:.2f} "
                  f"phi {df.loc[c, 'phi']:.2f}")
    assert 60 <= med <= 200, "median stock cover implausible vs IEA 90-day"
    if "Japan" in imp_ctys.index:
        assert imp_ctys.loc["Japan", "days_cover_oil"] > 90, \
            "Japan below its IEA obligation — check units"
    df.round(3).to_csv(inputs.MAPS / "reserves_cover.csv")
    print("saved reserves_cover.csv")
    return df


if __name__ == "__main__":
    build()
