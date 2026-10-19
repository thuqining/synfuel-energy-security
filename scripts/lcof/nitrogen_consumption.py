"""
nitrogen_consumption.py -- national nitrogen use in ammonia equivalent, 2025 (2026-10-07).

Ammonia is the precursor of practically all mineral nitrogen, and most nitrogen
crosses borders as urea, nitrates and ammonium phosphates rather than as ammonia.
Counting only ammonia itself places the nitrogen where it is synthesised (exporters
of urea look like large ammonia users, importers of fertilizer like none). Following
the fertilizer-security literature (Rosa & Gabrielli 2023, ERL 18 014008; Mingolla &
Rosa 2025, Nature Food), demand is the nitrogen a country uses, in ammonia
equivalent:

    N use = N production + N imports - N exports           (t N, 2025)
    ammonia equivalent = N use x 17/14

  production  ammonia production, USGS Mineral Commodity Summaries 2026 (2025e) for
              the 22 listed countries, the 'Other countries' total shared by 2023
              Minerals Yearbook production (ammonia_consumption.production_2025_t)
  trade       UN Comtrade, ammonia (HS 281410, 281420) and nitrogen fertilizers
              (HS 3102, 3105 with nitrogen), times the nitrogen content of each
              product (fetch_nitrogen_trade.N_CONTENT); each reporter's latest
              reported year (2025, else 2024, else 2023) for each flow; for producers
              that report no exports, the mirror flow (partners' imports from them)

Uses of the result: the national ammonia demand of the demand grid (rescaled to the
2025 world production of 194.3 Mt NH3) and the direct import share of nitrogen,
m = max(net N imports, 0) / N use, of the ammonia supply chain.

Writes data/cost/ammonia_consumption.csv (the previous ammonia-only balance is kept
as ammonia_consumption_nh3only.csv).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import inputs
from .ammonia_consumption import production_2025_t, _name, NH3_PER_N
from .fetch_nitrogen_trade import N_CONTENT, YEARS, MIRROR_GROUPS

ND = inputs.PROJECT / "data" / "demand" / "usgs" / "nitrogen"


def _kg(d: pd.DataFrame) -> pd.Series:
    return d.netWgt.where(d.netWgt > 0, d.qty.where(d.qty > 0, d.altQty)).fillna(0.0)


def _load(flow: str) -> pd.DataFrame:
    """rows: reporter, year, code, t_N"""
    rows = []
    for y in YEARS:
        for c, frac in N_CONTENT.items():
            f = ND / f"tot_{c}_{y}_{flow}.json"
            if not f.exists():
                continue
            d = pd.DataFrame(json.load(open(f, encoding="utf-8"))["data"])
            if d.empty:
                continue
            d = d[d.partnerCode == 0]
            rows.append(pd.DataFrame({"reporter": d.reporterDesc.map(_name).to_numpy(), "year": y,
                                      "code": c, "t_N": _kg(d).to_numpy() / 1e3 * frac}))
    return pd.concat(rows, ignore_index=True)


def latest(flow: str) -> tuple[pd.Series, pd.Series]:
    """t N per reporter in its latest reported year (any nitrogen code counts as
    reporting; codes it does not report in that year are zero), and that year"""
    d = _load(flow)
    yr = d.groupby("reporter").year.max()
    d = d[d.year == d.reporter.map(yr)]
    return d.groupby("reporter").t_N.sum(), yr


def _mirror_t_n(name: str) -> tuple[float, int]:
    """partners' reported imports from `name`, t N, each partner at its latest year"""
    got, total = set(), 0.0
    for y in YEARS:
        part = []
        for k in range(len(MIRROR_GROUPS)):
            f = ND / f"mir_{name}_{y}_{k}.json"
            if f.exists():
                d = pd.DataFrame(json.load(open(f, encoding="utf-8"))["data"])
                if not d.empty:
                    part.append(d)
        if not part:
            continue
        d = pd.concat(part)
        d["t_N"] = _kg(d) / 1e3 * d.cmdCode.astype(str).map(N_CONTENT).fillna(0.0)
        by = d.groupby("reporterCode").t_N.sum()
        new = by.index.difference(list(got))
        total += float(by[new].sum())
        got |= set(new)
    return total, len(got)


# producers whose nitrogen exports reach Comtrade only through their partners
MIRROR = {"Russia": 643, "Qatar": 634, "Algeria": 12, "Iran": 364, "Turkmenistan": 795,
          "Libya": 434, "Nigeria": 566, "Bahrain": 48, "Venezuela": 862, "Oman": 512,
          "Egypt": 818, "Saudi Arabia": 682, "Trinidad and Tobago": 780, "Belarus": 112,
          "Uzbekistan": 860, "Ukraine": 804, "Kuwait": 414, "United Arab Emirates": 784,
          "Iraq": 368, "Brunei": 96, "Indonesia": 360, "Malaysia": 458,
          # 2026-10-19: Norway reports almost no nitrogen exports (3 kt N), but its partners report 0.6 Mt N
          # of imports from Norway (calcium nitrate and NPK from Yara Porsgrunn)
          "Norway": 579}


NES = 899          # 'Areas, nes': partners not stated


def nitrogen_hhi() -> pd.DataFrame:
    """supplier concentration of each reporter's nitrogen imports (ammonia and
    nitrogen fertilizers, by nitrogen content) in its latest reported year:
    HHI over named partners, the share of tonnage from undisclosed partners
    ('areas nes'), and the top supplier's share"""
    rows = []
    files = sorted(ND.glob("par_*.json"))
    seen = {}
    for f in files:
        d = pd.DataFrame(json.load(open(f, encoding="utf-8"))["data"])
        if d.empty:
            continue
        rep = _name(d.reporterDesc.iloc[0])
        seen.setdefault(rep, []).append(d)
    for rep, parts in seen.items():
        d = pd.concat(parts, ignore_index=True)
        d = d[(d.partnerCode != 0) & (d.flowCode == "M")]
        d = d.drop_duplicates(["cmdCode", "partnerCode", "period"])
        d["t_N"] = _kg(d) / 1e3 * d.cmdCode.astype(str).map(N_CONTENT).fillna(0.0)
        by = d.groupby("partnerCode").t_N.sum()
        tot = float(by.sum())
        if tot <= 0:
            continue
        nes = float(by.get(NES, 0.0))
        named = by.drop(NES, errors="ignore")
        s = named / named.sum() if named.sum() > 0 else named
        rows.append(dict(country=rep, year=int(d.period.astype(int).max()), n_imports_partner_t=tot,
                         hhi_nitrogen=float((s ** 2).sum()), top_share_nitrogen=float(s.max()) if len(s) else np.nan,
                         nes_share=nes / tot, n_partners=int((named > 0).sum())))
    return pd.DataFrame(rows).set_index("country")


def build(world_nh3_t: float = 160.0e6 * NH3_PER_N, write: bool = True) -> pd.DataFrame:
    prod_n = production_2025_t() / NH3_PER_N
    imp, yi = latest("M")
    exp, yx = latest("X")
    idx = prod_n.index.union(imp.index).union(exp.index)
    df = pd.DataFrame({"n_production_t": prod_n.reindex(idx).fillna(0.0),
                       "n_imports_t": imp.reindex(idx).fillna(0.0),
                       "n_exports_t": exp.reindex(idx),
                       "imports_year": yi.reindex(idx), "exports_year": yx.reindex(idx)})
    df["exports_source"] = np.where(df.n_exports_t.notna(), "reported", "none reported")
    for c in MIRROR:
        if c not in df.index:
            continue
        if np.isfinite(df.at[c, "n_exports_t"]) and df.at[c, "exports_year"] == 2025:
            continue
        m, n = _mirror_t_n(c)
        if n and (not np.isfinite(df.at[c, "n_exports_t"]) or m > df.at[c, "n_exports_t"]):
            df.at[c, "n_exports_t"] = m
            df.at[c, "exports_source"] = f"mirror ({n} partners)"
    df["n_exports_t"] = df.n_exports_t.fillna(0.0)
    df["n_use_raw_t"] = (df.n_production_t + df.n_imports_t - df.n_exports_t).clip(lower=0.0)
    net = (df.n_imports_t - df.n_exports_t).clip(lower=0.0)
    df["n_import_share"] = np.where(df.n_use_raw_t > 0, (net / df.n_use_raw_t).clip(upper=1.0), np.nan)
    scale = world_nh3_t / (df.n_use_raw_t.sum() * NH3_PER_N)
    df["consumption_t"] = df.n_use_raw_t * NH3_PER_N * scale       # ammonia equivalent, t NH3
    print(f"nitrogen use {df.n_use_raw_t.sum() / 1e6:.1f} Mt N (production {df.n_production_t.sum() / 1e6:.1f}); "
          f"ammonia equivalent scaled x{scale:.3f} to {world_nh3_t / 1e6:.1f} Mt NH3")
    if write:
        df.round(3).to_csv(inputs.MAPS / "ammonia_consumption.csv", index_label="country")
    return df


if __name__ == "__main__":
    d = build()
    core = ["China", "United States of America", "India", "Japan", "Germany", "South Korea", "Brazil",
            "Indonesia", "Italy", "Spain", "Israel", "Netherlands", "Poland", "United Kingdom", "Vietnam",
            "Egypt", "Pakistan", "Kenya", "Philippines", "Sri Lanka", "Dominican Republic", "Madagascar",
            "Ireland", "Chile", "Morocco", "Australia", "Saudi Arabia", "South Africa", "Norway", "Oman"]
    t = d.reindex(core)[["n_production_t", "n_imports_t", "n_exports_t", "exports_source",
                         "imports_year", "exports_year", "n_import_share", "consumption_t"]].copy()
    for k in ("n_production_t", "n_imports_t", "n_exports_t"):
        t[k] = (t[k] / 1e3).round(0)
    t["consumption_t"] = (t.consumption_t / 1e6).round(2)
    print(t.to_string())
