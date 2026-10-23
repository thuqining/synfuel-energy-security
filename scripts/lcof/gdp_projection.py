"""
gdp_projection.py — Figs 4-5 with projected GDP (sensitivity, 2026-10-21).

The paper holds the economy at 2025 (GDP, demand, prices, disruption record,
carbon prices) and moves only equipment costs to 2030/2040/2050. This module
reruns Fig. 4a (fig5a_chain) and Fig. 5 (security_budget) with GDP projected
to the cost year:

  2030      2025 GDP x IMF World Economic Outlook real growth 2026-2030
            (data/gdp_projections/imf_weo_gdp_2023_2031.json, DataMapper API)
  2040/2050 the 2030 value x SSP2 real GDP growth from 2030 (SSP v3.2, OECD
            ENV-Growth 2025, GDP|PPP 2017 US$; data/gdp_projections/
            ssp2_gdp_v3.2.csv, from ssp_basic_drivers_release_3.2_full.xlsx)

Economies without a WEO growth path take SSP2 growth for 2025-2030; economies
in neither take the median factor. Two variants: 'budget' scales GDP only
(the 1-3% budgets); 'budget+voll' also scales the value of lost fuel, which
is proportional to GDP per unit of energy (energy use held at 2025).

    python ../work/caselow/run_mod.py ../work/caselow/2030 2030 lcof.gdp_projection
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from lcof import inputs

D = Path(__file__).resolve().parents[2] / "data" / "gdp_projections"
OUT = Path(__file__).resolve().parents[2] / "console" / "build"
SSP_NAME = {"United States of America": "United States", "Russia": "Russian Federation", "Iran": "Iran (Islamic Republic of)",
            "Ivory Coast": "Côte d'Ivoire", "Democratic Republic of the Congo": "Congo, Democratic Republic of the",
            "Republic of the Congo": "Congo", "United Republic of Tanzania": "Tanzania",
            "South Korea": "Korea, Republic of", "North Korea": "Korea, Democratic People's Republic of",
            "Vietnam": "Viet Nam", "Laos": "Lao People's Democratic Republic", "Syria": "Syrian Arab Republic",
            "Bolivia": "Bolivia (Plurinational State of)", "Venezuela": "Venezuela (Bolivarian Republic of)",
            "Moldova": "Moldova, Republic of", "Taiwan": "Taiwan", "Turkey": "Türkiye", "Czechia": "Czechia",
            "Republic of Serbia": "Serbia", "eSwatini": "Eswatini", "Kyrgyzstan": "Kyrgyzstan",
            "Bosnia and Herzegovina": "Bosnia and Herzegovina", "Macedonia": "North Macedonia", "Guinea-Bissau": "Guinea-Bissau"}


def factors(year: int) -> pd.Series:
    """real GDP factor, cost year over 2025, per economy (model names)."""
    import geopandas as gpd
    ne = gpd.read_file(inputs.PROJECT / "data/grid/naturalearth/ne_10m_admin_0_countries.shp")[["ADMIN", "ADM0_A3", "ISO_A3"]]
    weo = json.load(open(D / "imf_weo_gdp_2023_2031.json", encoding="utf-8"))["data"]
    ssp = pd.read_csv(D / "ssp2_gdp_v3.2.csv")
    ssp = ssp[(ssp.Variable == "GDP|PPP") & (ssp.Unit == "billion USD_2017/yr")].set_index("Region")
    ssp = ssp[[str(y) for y in (2025, 2030, 2040, 2050)]].astype(float)
    norm = lambda s: "".join(ch for ch in str(s).lower() if ch.isalnum())
    ssp_by = {norm(i): r for i, r in ssp.iterrows()}

    def ssp_row(c):
        for k in (SSP_NAME.get(c, c), c):
            r = ssp_by.get(norm(k))
            if r is not None:
                return r
        return None
    out = {}
    for _, r in ne.iterrows():
        c = r.ADMIN
        w = weo.get(r.ADM0_A3) or weo.get(r.ISO_A3) or {}
        g = [w.get(str(y), [None])[0] for y in range(2026, 2031)]
        s = ssp_row(c)
        if all(x is not None for x in g):
            f30 = float(np.prod([1 + x / 100 for x in g]))
        elif s is not None and s["2025"] > 0:
            f30 = float(s["2030"] / s["2025"])
        else:
            f30 = np.nan
        if year == 2030 or year == 2025:
            out[c] = 1.0 if year == 2025 else f30
        elif s is not None and s["2030"] > 0:
            out[c] = f30 * float(s[str(year)] / s["2030"])
        else:
            out[c] = np.nan
    f = pd.Series(out)
    return f.fillna(f.median())


_CACHE = {}


def projected(si: pd.DataFrame) -> pd.DataFrame:
    """security_index with gdp_usd at the case's cost year (params.COST_YEAR). The value of lost fuel
    (codf columns) stays at 2025. LCOF_GDP=2025 keeps 2025 GDP (the pre-2026-10-21 convention)."""
    import os
    from lcof import params as P
    year = int(getattr(P, "COST_YEAR", 2025))
    if os.environ.get("LCOF_GDP", "projected") == "2025" or year <= 2025:
        return si
    if year not in _CACHE:
        _CACHE[year] = factors(year)
    si = si.copy()
    si["gdp_usd"] = si["gdp_usd"] * _CACHE[year].reindex(si.index).fillna(1.0)
    return si


def run(year: int, variant: str):
    from lcof import fig5a_chain as A, security_budget as SB
    f = factors(year)
    orig = pd.read_csv

    def patched(path, *a, **k):
        d = orig(path, *a, **k)
        if str(path).endswith("security_index.csv"):
            m = f.reindex(d.index).fillna(1.0)
            d["gdp_usd"] = d["gdp_usd"] * m
            if variant == "budget+voll":
                for col in ("codf_usd_gj", "codf_hi_usd_gj"):
                    if col in d:
                        d[col] = d[col] * m
        return d
    import os
    pd.read_csv = patched
    old = os.environ.get("LCOF_GDP")
    os.environ["LCOF_GDP"] = "2025"          # the patch applies the factor; do not apply it twice
    try:
        sb, _ = SB.compute(write=False)
        A_core = A.core_countries
        sbi = orig(inputs.MAPS / "security_budget.csv", index_col=0)
        si = orig(inputs.MAPS / "security_index.csv", index_col=0)
        setup = A._setup()
        keep = [c for c in sbi.index if c in setup[1].index and c in si.index]
        A.core_countries = lambda avail, n=30: [c for c in keep if c in set(avail)]
        a = A.compute(write=False, verbose=False, setup=setup)
        A.core_countries = A_core
    finally:
        pd.read_csv = orig
        if old is None:
            os.environ.pop("LCOF_GDP", None)
        else:
            os.environ["LCOF_GDP"] = old
    return f, sb, a


def summary(sb, a, core):
    imp = sb.import_pct > 0
    just = (a.net_usd_t <= a.p_co2_usd_t) & (a.chain_import_share > 0)
    return {"justified_core": int(just.reindex(core).fillna(False).sum()), "justified_all": int(just.sum()),
            "median_home_1pct_core": float(sb.loc[core, "cov_1"].median() * 100),
            "median_home_1pct_all": float(sb.loc[imp | ~imp, "cov_1"].median() * 100),
            "land_binds_core": int(((sb.cov_3 >= sb.max_cov - 1e-6) & (sb.max_cov < 1 - 1e-6) & imp & (sb.ret_sf_3 < 0.995)).reindex(core).sum())}


def main():
    from lcof.coreset import core_countries
    year = int(inputs.MAPS.parent.name[:4])
    base_sb = pd.read_csv(inputs.MAPS / "security_budget.csv", index_col=0)
    base_a = pd.read_csv(OUT / f"fig4a_all_{inputs.MAPS.parent.name}.csv", index_col=0)
    core = [c for c in core_countries(base_sb.index) if c in base_sb.index]
    rows = [dict(year=year, variant="paper (2025 GDP)", gdp_factor_median=1.0, **summary(base_sb, base_a, core))]
    for variant in ("budget", "budget+voll"):
        f, sb, a = run(year, variant)
        rows.append(dict(year=year, variant=variant, gdp_factor_median=float(f.reindex(sb.index).median()),
                         **summary(sb, a, core)))
        sb[["cov_1", "cov_2", "cov_3", "max_cov", "import_pct", "ret_sf_3"]].assign(gdp_factor=f.reindex(sb.index)) \
            .to_csv(OUT / f"gdpproj_{year}_{variant.replace('+', '_')}_fig5.csv")
        a[["gross_usd_t", "net_usd_t", "p_co2_usd_t", "chain_import_share", "co2_mt"]] \
            .to_csv(OUT / f"gdpproj_{year}_{variant.replace('+', '_')}_fig4a.csv")
    d = pd.DataFrame(rows)
    d.to_csv(OUT / f"gdpproj_{year}_summary.csv", index=False)
    print(d.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
