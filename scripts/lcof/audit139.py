"""
audit139.py — checks of the 139-economy results behind the console and the all-economy figures (2026-10-21).

Prints every failure and the outliers worth a look; writes console/build/audit139.csv (one row per economy).

    python -m lcof.audit139
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

R = Path(__file__).resolve().parents[2]
W = R / "work" / "caselow"
BUILD = R / "console" / "build"
YEARS = (2030, 2040, 2050)


def main():
    t = (R / "console/index.html").read_text(encoding="utf-8")
    D = json.JSONDecoder().raw_decode(t[t.index("const DATA=") + 11:])[0]
    C = D["countries"]
    sb = {y: pd.read_csv(W / f"{y}/data/security_budget.csv", index_col=0) for y in YEARS}
    a = {y: pd.read_csv(BUILD / f"fig4a_all_{y}.csv", index_col=0) for y in YEARS}
    si = pd.read_csv(W / "2030/data/security_index.csv", index_col=0)
    k139 = list(sb[2030].index)
    fails, notes = [], []

    def fail(msg):
        fails.append(msg)

    # 1. the same 139 economies everywhere
    for y in YEARS:
        if set(sb[y].index) != set(k139):
            fail(f"security_budget {y}: economy set differs")
        if set(a[y].index) != set(k139):
            fail(f"fig4a_all {y}: economy set differs ({len(a[y])})")
    # 2. missing values
    for y in YEARS:
        for col in ("gross_usd_t", "net_usd_t", "p_co2_usd_t", "co2_mt"):
            m = a[y][col].isna()
            if m.any():
                fail(f"fig4a {y}: {col} missing for {list(a[y].index[m])}")
        for col in ("cov_1", "cov_2", "cov_3", "max_cov", "import_pct", "gdp_usd"):
            m = sb[y][col].isna()
            if m.any():
                fail(f"security_budget {y}: {col} missing for {list(sb[y].index[m])}")
    # 3. invariants
    for y in YEARS:
        s = sb[y]
        bad = s.index[~((s.cov_1 <= s.cov_2 + 1e-9) & (s.cov_2 <= s.cov_3 + 1e-9) & (s.cov_3 <= s.max_cov + 1e-6))]
        if len(bad):
            fail(f"Fig. 5 {y}: shares not monotone or above the land ceiling: {list(bad)}")
        d = a[y]
        neg_margin = d.index[(d.gross_usd_t - d.net_usd_t) < -1e-6]
        if len(neg_margin):
            fail(f"Fig. 4a {y}: negative security margin: {list(neg_margin)}")
        exp_margin = d.index[(s.import_pct.reindex(d.index) <= 0) & ((d.gross_usd_t - d.net_usd_t) > 1)]
        if len(exp_margin):
            notes.append(f"Fig. 4a {y}: net exporters (Fig. 5 rule) with a security margin > US$1/t: {list(exp_margin)}")
        neg_gross = d.index[d.gross_usd_t < 0]
        if len(neg_gross):
            notes.append(f"Fig. 4a {y}: negative cost premium (fuel cheaper than fossil): {list(neg_gross)}")
    # 4. costs fall with the cost year; GDP factor rises
    for c in k139:
        g = [a[y].gross_usd_t.get(c, np.nan) for y in YEARS]
        if np.all(np.isfinite(g)) and not (g[0] >= g[1] - 1 and g[1] >= g[2] - 1):
            notes.append(f"cost premium not falling 2030->2050 for {c}: {np.round(g, 0)}")
        f = [sb[y].gdp_usd.get(c) / sb[2030].gdp_usd.get(c) for y in YEARS]
        if not (f[0] <= f[1] <= f[2]):
            notes.append(f"projected GDP not rising for {c}: {np.round(f, 2)}")
    # 5. outliers
    d = a[2030].copy()
    d["margin"] = d.gross_usd_t - d.net_usd_t
    d["voll_hi"] = si.codf_hi_usd_gj.reindex(d.index)
    d["gdp_bn"] = sb[2030].gdp_usd.reindex(d.index) / 1e9
    d["gdp_factor_2050"] = sb[2050].gdp_usd.reindex(d.index) / si.gdp_usd.reindex(d.index)
    d["E_amm"] = [C.get(c, {}).get("E_amm") for c in d.index]
    d["fb_amm"] = [bool(C.get(c, {}).get("fb_amm")) for c in d.index]
    d["just_2030"] = d.net_usd_t <= d.p_co2_usd_t
    d.round(3).to_csv(BUILD / "audit139.csv")
    print("== FAILURES:", len(fails))
    for m in fails:
        print("  FAIL", m)
    print("== NOTES:", len(notes))
    for m in notes[:40]:
        print("  note", m)
    print("== largest 2030 security margins (US$/t) with the value of lost fuel (US$/GJ, ENTSOG anchor):")
    print(d.sort_values("margin", ascending=False)[["margin", "gross_usd_t", "net_usd_t", "voll_hi", "gdp_bn", "co2_mt"]]
          .head(12).round(1).to_string())
    print("== value of lost fuel: median", round(d.voll_hi.median(), 1), "| top 8:")
    print(d.voll_hi.sort_values(ascending=False).head(8).round(1).to_string())
    print("== largest 2030 cost premiums:")
    print(d.sort_values("gross_usd_t", ascending=False)[["gross_usd_t", "co2_mt"]].head(6).round(1).to_string())
    print("== GDP factor 2050/2025 extremes:")
    print(d.gdp_factor_2050.sort_values().iloc[[0, 1, 2, -3, -2, -1]].round(2).to_string())
    print("== 2030 portfolios with CO2 < 0.1 Mt (premium per tonne unstable):",
          list(d.index[d.co2_mt < 0.1]))


if __name__ == "__main__":
    main()
