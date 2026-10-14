"""
fetch_country_prices.py — real COUNTRY-LEVEL energy prices from open official APIs.

Sources (all public, no key):
  Eurostat nrg_pc_203  industrial natural gas prices, 37 European countries,
                       half-yearly 2007-2025, EUR per GJ (gross calorific
                       value), available EXCLUDING taxes and INCLUDING taxes.
                       Band I4 (100k-1M GJ/yr) ~ an industrial fuel buyer.
  Eurostat nrg_pc_205  industrial electricity prices, same geography (used as
                       an independent sanity check on our LCOE).
  ECB EXR              monthly USD per EUR, to convert to USD.
  EIA dnav             US state-level industrial gas prices (already fetched).

Output: data/prices/country_gas_prices.csv  (USD/GJ on a LHV basis, per country,
        per half-year, both pre-tax and tax-inclusive)

From scripts/:  conda run -n synfuel python -m lcof.fetch_country_prices
"""
from __future__ import annotations

import json
import urllib.request

import numpy as np
import pandas as pd

from . import inputs

UA = {"User-Agent": "Mozilla/5.0 (academic research; energy price collection)"}
ESTAT = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
         "{ds}?format=JSON&lang=EN&{q}")
ECB = ("https://data-api.ecb.europa.eu/service/data/EXR/M.USD.EUR.SP00.A"
       "?format=jsondata&startPeriod=2006-01")
OUT = inputs.PROJECT / "data" / "prices"
GAS_HHV_TO_LHV = 0.90          # Eurostat quotes GCV (= HHV)


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8"))


def _unstack(d: dict) -> pd.DataFrame:
    """JSON-stat -> tidy frame with one row per (geo, time)."""
    dims = d["id"]
    sizes = d["size"]
    idx = {k: list(d["dimension"][k]["category"]["index"].keys()) for k in dims}
    lab = {k: d["dimension"][k]["category"].get("label", {}) for k in dims}
    rows = []
    for flat, val in d["value"].items():
        rem = int(flat)
        coord = []
        for s in reversed(sizes):
            coord.append(rem % s)
            rem //= s
        coord = list(reversed(coord))
        rec = {k: idx[k][c] for k, c in zip(dims, coord)}
        rec["value"] = val
        rec["geo_label"] = lab["geo"].get(rec["geo"], rec["geo"])
        rows.append(rec)
    return pd.DataFrame(rows)


def eurostat_gas() -> pd.DataFrame:
    frames = []
    for tax, tag in (("X_TAX", "pretax"), ("I_TAX", "taxed")):
        q = (f"nrg_cons=GJ100000-999999&unit=GJ_GCV&tax={tax}&currency=EUR"
             f"&siec=G3000&freq=S")
        d = _get(ESTAT.format(ds="nrg_pc_203", q=q))
        df = _unstack(d)[["geo", "geo_label", "time", "value"]]
        df["basis"] = tag
        frames.append(df)
        print(f"  eurostat gas {tag}: {len(df)} obs, "
              f"{df.geo.nunique()} geos, {df.time.min()}..{df.time.max()}")
    return pd.concat(frames, ignore_index=True)


def ecb_fx() -> pd.Series:
    d = _get(ECB)
    ser = d["dataSets"][0]["series"]["0:0:0:0:0"]["observations"]
    times = d["structure"]["dimensions"]["observation"][0]["values"]
    out = {}
    for k, v in ser.items():
        out[times[int(k)]["id"]] = v[0]
    s = pd.Series(out, dtype=float)
    s.index = pd.PeriodIndex(s.index, freq="M")
    print(f"  ECB USD/EUR: {len(s)} months, {s.index[0]}..{s.index[-1]}, "
          f"range {s.min():.2f}-{s.max():.2f}")
    return s.sort_index()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print("fetching open country-level price data ...")
    gas = eurostat_gas()
    fx = ecb_fx()

    # half-year -> the two months at its centre, for the FX average
    def hy_to_fx(t: str) -> float:
        y, s = t.split("-S")
        months = (1, 6) if s == "1" else (7, 12)
        sel = fx[(fx.index.year == int(y)) & (fx.index.month >= months[0]) &
                 (fx.index.month <= months[1])]
        return float(sel.mean()) if len(sel) else np.nan

    gas["usd_per_eur"] = gas["time"].map(hy_to_fx)
    # EUR/GJ(GCV) -> USD/GJ(LHV)
    gas["usd_gj_lhv"] = gas["value"] * gas["usd_per_eur"] / GAS_HHV_TO_LHV
    gas = gas[gas.usd_gj_lhv.notna()]

    out = OUT / "country_gas_prices.csv"
    gas.to_csv(out, index=False)
    print(f"\nwrote {out}  ({len(gas)} rows, {gas.geo.nunique()} countries)")

    # ---- verification against known reference points ----
    # NOTE these bands are for the CONTRACT-WEIGHTED industrial price Eurostat
    # reports, which is far below spot. In H2-2022 TTF spot averaged ~$51/GJ
    # while German industry actually paid ~$20/GJ: legacy contracts and hedges
    # absorbed most of the shock. Both series are kept — spot is the marginal
    # signal a new buyer faces, the Eurostat series is what was actually paid.
    print("\nverification (industrial gas, band I4, USD/GJ LHV):")
    pre = gas[gas.basis == "pretax"].pivot_table(index="time", columns="geo_label",
                                                 values="usd_gj_lhv")
    for geo, t, lo, hi in (("Germany", "2022-S2", 14, 30),
                           ("Germany", "2020-S1", 6, 14),
                           ("France", "2022-S2", 14, 32),
                           ("Sweden", "2021-S1", 8, 30)):
        if geo in pre.columns and t in pre.index:
            v = pre.loc[t, geo]
            ok = lo <= v <= hi
            print(f"  [{'OK ' if ok else 'CHECK'}] {geo:10s} {t}: "
                  f"{v:6.2f} USD/GJ (plausible {lo}-{hi})")

    latest = pre.dropna(how="all").iloc[-1].dropna().sort_values()
    print(f"\ncountry spread in {pre.dropna(how='all').index[-1]} "
          f"(USD/GJ LHV, pre-tax):")
    print(f"  cheapest: {', '.join(f'{k} {v:.1f}' for k, v in latest.head(4).items())}")
    print(f"  dearest : {', '.join(f'{k} {v:.1f}' for k, v in latest.tail(4).items())}")
    print(f"  ratio dearest/cheapest = {latest.iloc[-1]/latest.iloc[0]:.1f}x")

    tax = gas[gas.basis == "taxed"].pivot_table(index="time", columns="geo_label",
                                                values="usd_gj_lhv")
    common = [c for c in latest.index if c in tax.columns]
    t_last = pre.dropna(how="all").index[-1]
    ratio = (tax.loc[t_last, common] / pre.loc[t_last, common]).dropna()
    print(f"\ntax wedge on industrial gas ({t_last}): median "
          f"{ratio.median():.2f}x, max {ratio.max():.2f}x "
          f"({ratio.idxmax()})")

    # contract-weighted vs spot: how much of the shock did industry actually see?
    from . import prices as PR
    spot = PR.load(verified=False)["gas_eu"]
    print("\ncontract-weighted (Eurostat, what industry paid) vs TTF spot, "
          "USD/GJ LHV:")
    for t in ("2020-S1", "2021-S2", "2022-S1", "2022-S2", "2023-S1"):
        y, s = t.split("-S")
        m = (1, 6) if s == "1" else (7, 12)
        sp = spot[(spot.index.year == int(y)) & (spot.index.month >= m[0]) &
                  (spot.index.month <= m[1])].mean()
        de = pre.loc[t, "Germany"] if t in pre.index else np.nan
        print(f"  {t}: Germany industrial {de:6.2f} | TTF spot {sp:6.2f} "
              f"| pass-through {de/sp*100:4.0f} %")


if __name__ == "__main__":
    main()
