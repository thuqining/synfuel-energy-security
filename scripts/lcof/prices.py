"""
prices.py — monthly fossil price series, verified and converted to one unit.

SOURCES (all free and citable, downloaded not recalled)
  World Bank Commodity Price Data ("Pink Sheet"), monthly, nominal USD:
      Brent / Dubai / WTI crude, Henry Hub gas, European gas (TTF from
      Apr-2015), Japan LNG import price (cif), Australian & South African
      steam coal, urea.
  US EIA monthly spot prices: US Gulf Coast ultra-low-sulfur diesel and
      kerosene-type jet fuel. Real product prices matter: in June 2022 diesel
      reached $4.29/gal, ABOVE the July 2008 peak of $3.82/gal, even though
      crude was lower — a crack-spread blow-out that a "crude + fixed crack"
      estimate would miss entirely.

UNITS  everything is converted to $/GJ on a LOWER-heating-value basis and
       reported as $/MMBtu (LHV).

Three traps handled explicitly:
  1. HHV vs LHV — gas is quoted per MMBtu on a GROSS (HHV) basis while our
     fuels are LHV; LHV(gas) = 0.90 x HHV, so $/GJ(LHV) = 1.053 x $/MMBtu(HHV).
     (Hydrogen is worse still: LHV 120 vs HHV 142 MJ/kg, an 18 % gap.)
  2. Currency — every series here is already nominal USD, so no FX conversion
     is applied; a EUR/USD series would only be needed to add a euro-quoted
     marker such as raw TTF in EUR/MWh.
  3. Hub vs delivered — Henry Hub is a US hub price, TTF a European hub price,
     and Japan LNG a delivered (cif) price. Importers are compared against
     their own delivered marker, never against Henry Hub.

CAVEAT ON ASIA  the Pink Sheet's Japan LNG series is the customs-cleared
  IMPORT price, which is contract-weighted and oil-linked. It rose to about
  $24/MMBtu in 2022 while JKM spot exceeded $50. JKM is proprietary, so our
  Asian crisis exposure is deliberately CONSERVATIVE.

From scripts/:  conda run -n synfuel python -m lcof.prices
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import inputs

PRICES = inputs.PROJECT / "data" / "prices"
XLSX = PRICES / "CMO-Historical-Data-Monthly.xlsx"

# ---- energy conversions, LHV basis ------------------------------------------
# 1 MMBtu = 1.05506 GJ. Used as the multiplier $/GJ -> $/MMBtu; divide to invert.
MMBTU_PER_GJ = 1.05506
GJ_PER_BBL_CRUDE = 5.72        # LHV: ~42.5 GJ/t, 7.43 bbl/t
GAS_HHV_TO_LHV = 0.90          # LHV / HHV for natural gas
GJ_PER_T_COAL = 25.1           # steam coal, 6000 kcal/kg NAR
GJ_PER_GAL_DIESEL = 0.1353     # 3.785 L x 0.835 kg/L x 42.8 MJ/kg
GJ_PER_GAL_JET = 0.1309        # 3.785 L x 0.804 kg/L x 43.0 MJ/kg
# urea -> implied ammonia: 2 NH3 + CO2 -> urea, 0.567 t NH3 per t urea
UREA_TO_NH3 = 0.567
UREA_CONV_COST = 65.0          # $/t urea, granulation + CO2 + margin
GJ_PER_T_NH3 = 18.6            # LHV

PINK = {
    "Crude oil, Brent": ("brent", "bbl"),
    "Crude oil, Dubai": ("dubai", "bbl"),
    "Crude oil, WTI": ("wti", "bbl"),
    "Natural gas, US": ("gas_us", "mmbtu_hhv"),
    "Natural gas, Europe": ("gas_eu", "mmbtu_hhv"),
    "Liquefied natural gas, Japan": ("lng_jp", "mmbtu_hhv"),
    "Coal, Australian": ("coal_au", "mt_coal"),
    "Coal, South African **": ("coal_za", "mt_coal"),
    "Urea": ("urea", "mt_urea"),
}

# published reference points; the parse must reproduce them or we do not use it
CHECKS = [
    ("brent", "2008-07", 133.0, 6, "2008 peak month (monthly average)"),
    ("brent", "2020-04", 23.3, 12, "COVID trough, monthly average — note the "
                                   "$19 figure often quoted is an intra-month spot low"),
    ("brent", "2022-03", 112.5, 8, "invasion spike"),
    ("gas_us", "2005-12", 13.0, 15, "post-Katrina Henry Hub"),
    ("gas_us", "2020-06", 1.6, 25, "COVID trough"),
    ("gas_eu", "2022-08", 70.0, 20, "European gas crisis peak (TTF)"),
    ("lng_jp", "2022-09", 23.7, 15, "Japan cif IMPORT price — contract-linked, "
                                    "not JKM spot"),
    ("diesel", "2022-06", 4.29, 8, "US Gulf Coast diesel peak, $/gal"),
    ("diesel", "2008-07", 3.82, 8, "2008 diesel peak, $/gal"),
    ("jet", "2020-04", 0.61, 20, "COVID jet trough, $/gal"),
]


def _read_eia(fname: str) -> pd.Series:
    d = pd.read_excel(PRICES / fname, sheet_name="Data 1", header=2)
    d.columns = ["date", "price"]
    d = d.dropna()
    idx = pd.PeriodIndex(pd.to_datetime(d["date"]), freq="M")
    return pd.Series(pd.to_numeric(d["price"].values, errors="coerce"), index=idx)


def load_raw() -> pd.DataFrame:
    """All series in their NATIVE units, indexed by month."""
    if not XLSX.exists():
        raise SystemExit(f"missing {XLSX} — download the Pink Sheet first")
    raw = pd.read_excel(XLSX, sheet_name="Monthly Prices", header=None)
    # normalise header text: the sheet carries stray trailing spaces
    names = [" ".join(str(c).split()) for c in raw.iloc[4].tolist()]
    df = raw.iloc[6:].copy()
    df.columns = ["period"] + names[1:]
    df = df[df["period"].astype(str).str.match(r"^\d{4}M\d{2}$")]
    idx = pd.PeriodIndex(df["period"].str.replace("M", "-"), freq="M")
    out = pd.DataFrame(index=idx)
    for col, (short, _) in PINK.items():
        if col not in df.columns:
            raise SystemExit(f"column '{col}' missing — Pink Sheet layout changed")
        out[short] = pd.to_numeric(pd.Series(df[col].values).replace("…", np.nan),
                                   errors="coerce").values
    out["diesel"] = _read_eia("diesel_usgc.xls").reindex(out.index)
    out["jet"] = _read_eia("jet_usgc.xls").reindex(out.index)
    return out


def verify(raw: pd.DataFrame, loud: bool = True) -> None:
    bad = []
    if loud:
        print("verification against published reference points:")
    for name, period, expect, tol, note in CHECKS:
        got = raw.loc[pd.Period(period, "M"), name]
        err = abs(got / expect - 1) * 100 if np.isfinite(got) else np.inf
        ok = err <= tol
        if loud:
            print(f"  [{'OK ' if ok else 'FAIL'}] {name:7s} {period} got {got:8.2f} "
                  f"expect ~{expect:7.2f} ({err:4.1f} %)  {note}")
        if not ok:
            bad.append((name, period))
    if bad:
        raise SystemExit(f"price parse failed validation at {bad} — series not used")
    if loud:
        print("  all reference points pass\n")


def to_gj_lhv(raw: pd.DataFrame) -> pd.DataFrame:
    g = pd.DataFrame(index=raw.index)
    for _, (short, unit) in PINK.items():
        v = raw[short]
        if unit == "bbl":
            g[short] = v / GJ_PER_BBL_CRUDE
        elif unit == "mmbtu_hhv":
            g[short] = v / MMBTU_PER_GJ / GAS_HHV_TO_LHV
        elif unit == "mt_coal":
            g[short] = v / GJ_PER_T_COAL
        elif unit == "mt_urea":
            # derived cross-check only: implied ammonia price from urea
            g["ammonia_implied"] = ((v - UREA_CONV_COST) / UREA_TO_NH3) / GJ_PER_T_NH3
    g["diesel"] = raw["diesel"] / GJ_PER_GAL_DIESEL
    g["jet"] = raw["jet"] / GJ_PER_GAL_JET
    return g


def load(verified: bool = True, loud: bool = False) -> pd.DataFrame:
    """Monthly fossil prices in $/GJ (LHV)."""
    raw = load_raw()
    if verified:
        verify(raw, loud=loud)
    return to_gj_lhv(raw)


def main():
    raw = load_raw()
    print(f"parsed {raw.index[0]} to {raw.index[-1]}  ({len(raw)} months, "
          f"{raw.shape[1]} series)\n")
    verify(raw)
    g = to_gj_lhv(raw)
    w = g.loc["2006":"2025"]
    print("2006-2025 in $/MMBtu (LHV) — min / median / max / peak-to-trough:")
    for c in ("brent", "diesel", "jet", "gas_us", "gas_eu", "lng_jp",
              "coal_au", "ammonia_implied"):
        s = (w[c].dropna() * MMBTU_PER_GJ)
        if s.empty:
            continue
        print(f"  {c:16s} {s.min():7.2f} {s.median():7.2f} {s.max():7.2f}"
              f"   x{s.max()/s.min():5.1f}")
    out = PRICES / "fossil_monthly_gj_lhv.csv"
    g.to_csv(out)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
