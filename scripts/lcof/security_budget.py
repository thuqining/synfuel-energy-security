"""
security_budget.py — how much security does 1%, 2%, 3% of GDP buy?

The "cost of full independence" framing asks the wrong question: no
government will spend 10-20% of GDP a year, so a number that large reads
as a refutation rather than as a plan. The same object
inverted is a policy instrument: fix the annual budget, and ask how much
of the fuel bill it domesticates.

Per country we build the marginal abatement-style curve of independence.
Every (land cell, fuel) pair is a way to replace one GJ of imported fuel
with a domestic synthetic one, at a premium

    p(cell, f) = max( LCOF_f(cell) - grey_f(country), 0 )   $/GJ_fuel

with LCOF_f(cell) the Stage-2 cascade evaluated on THAT cell's Stage-1
hydrogen and electricity cost (the same grid every map in the paper
uses), and grey_f the national fossil comparator. Pairs are filled
cheapest-premium first, subject to

    the cell's land-limited firm-hydrogen output (shared across fuels)
    the country's addressable demand for each fuel

which yields a rising cost curve C(x) for domesticating a share x of the
addressable fuel bill. Inverting C at x-budget b gives x*(b), and the
security bought follows from the ledger: domestic output displaces
imports first, so the share of import exposure retired is min(x/q, 1)
with q the imported share of the bill (dep_oil/dep_gas weighted), and
ESD x min(x/q, 1).

Outputs data/cost/security_budget.csv, tab_budget.tex and
fig_security_budget.(pdf|png).

From scripts/:  conda run -n synfuel python -u -m lcof.security_budget
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

mpl.use("Agg")

from . import inputs, params as P
from .fig_main_cost import MM, NAT_RC, FUELS
from .fig_pptx_pairs import OUT, SUFFIX
from .coreset import core_countries
from .policy import EF, FOSSIL, CARBON_PRICE
from .supply_demand import firm_h2_potential_gj, lcof_cells, \
    LAND_AVAIL, MU_H2, SHORT, UMM

mpl.rcParams.update(NAT_RC)

BUDGETS = (1.0, 2.0, 3.0)        # % of GDP per year
# ---- greenhouse gases beyond combustion CO2 ------------------------------
# policy.EF is IPCC 2006 COMBUSTION CO2 only. That is a floor for the
# abatement: it omits upstream methane from the oil and gas supply chains
# and combustion N2O, both of which the synthetic route also avoids.
# GHG_UPLIFT rescales each fossil comparator to a life-cycle CO2e basis at
# GWP100, and is applied only when ghg="co2e".
#   liquids     RED III fixes the fossil transport comparator at
#               94 gCO2e/MJ against an IPCC combustion factor of
#               74.1 gCO2/MJ -> 1.27 (the same comparator policy_rules.py
#               already uses for the RFNBO threshold)
#   natural gas combustion 56.1 gCO2/MJ; a supply-chain methane intensity
#               of ~1.7% of throughput at GWP100 = 29.8 adds ~14 gCO2e/MJ
#               -> 1.25. THE LEAKAGE RATE IS AN ASSUMPTION, not a result:
#               it needs a chosen source (e.g. the IEA Global Methane
#               Tracker) before it goes in the paper.
#   grey H2/NH3 already production-chain; the same gas uplift reaches them
#               through the SMR feedstock -> 1.20
#   coal        mine methane, ~1.05
GHG_UPLIFT = {"diesel": 1.27, "kerosene": 1.27, "natgas": 1.25,
              "coal": 1.05, "grey_h2": 1.20, "grey_nh3": 1.20}
BCOL = {1.0: "#0B4F9E", 2.0: "#4A90D9", 3.0: "#A8CCEC"}
GREY, ACCENT = "#9AA5AF", "#D55E00"
BS, NL = chr(92), chr(10)
EOL = BS + BS
XMAX = 4.0                       # % GDP shown on the curve panel


def _grey(dgc: pd.DataFrame, domestic: bool = False) -> pd.DataFrame:
    """National fossil comparator per fuel, $/GJ_fuel (same route as the
    ledger and the supply-demand balance). domestic=True returns the national
    production route for every economy, without the core-30 import prices
    (2026-10-07: the comparator for the part of demand supplied at home)."""
    from .policy import FOSSIL
    from .gap import country_gas_monthly, fossil_for_fuel
    # 2025 US$ throughout, as in Figure 3 (the LCOF layer is at 2025 costs)
    from .audit_figure3 import _cpi, _real
    cpi, cpi_2025 = _cpi()
    gasdf, gg = country_gas_monthly()
    rows = {}
    for c in dgc.index:
        r = {}
        for f in FUELS:
            spec = FOSSIL[f]
            if isinstance(spec["price"], (int, float)):
                r[f] = float(spec["price"])
                continue
            ref = f if f in ("ammonia", "marine") else "e-methane"
            s = (fossil_for_fuel(ref, gasdf[c], gg, c).dropna()
                 if c in gasdf.columns else pd.Series(dtype=float))
            s = _real(s, cpi, cpi_2025).dropna() if len(s) else s
            r[f] = float(s.median()) if len(s) else np.nan
        rows[c] = r
    g = pd.DataFrame(rows).T
    # Figure 3's comparator for the fuels it observes (2026-09-17): each core
    # economy's own import price in normal months (event and recovery months
    # excluded), 2025 US$ -- the same buy side the boxes of Fig. 3 use, so the
    # premium a budget pays is the gap the main figure draws. Ammonia from the
    # ammonia series; diesel, jet and ethanol (which competes with the same
    # road fuel) from the demand-weighted diesel + jet series.
    for key, fuels in (() if domestic else
                       (("ammonia", ["ammonia"]),
                        ("ft", ["e-diesel", "e-kerosene", "ethanol"]))):
        path = inputs.MAPS / f"core30_sites_{key}.csv"
        if not path.exists():
            continue
        q = pd.read_csv(path).set_index("country").quiet_med_mmbtu / P.MMBTU_PER_GJ
        for c in q.index.intersection(g.index):
            if np.isfinite(q[c]):
                for f in fuels:
                    g.loc[c, f] = float(q[c])
    return g


def _curve(prem, cell, fuel, pot, dem, mu, ef, isgas, dep=None,
           fam_cap=None):
    """Merit order over (cell, fuel) pairs.

    Default: cheapest premium first — every dollar buys the most
    domestic fuel. With `dep` (import dependence of each fuel's family,
    per pair) the order becomes SECURITY-FIRST: premium per gigajoule
    of import retired (prem / dep), pairs whose family imports are
    already exhausted (cumulative family coverage >= fam_cap[family],
    GJ) drop to the back of the queue and are then filled cheapest
    first — they still buy coverage, but no security.

    Each cell's firm-hydrogen output is a resource shared by every fuel
    it could make (1 GJ of fuel f consumes mu_f GJ of hydrogen); each
    fuel is needed only up to the country's demand for it. Returns
    cumulative coverage (GJ_fuel), cumulative annual spend ($/yr),
    cumulative CO2 abated (t/yr) and cumulative gas-family coverage
    (GJ_fuel) — the last so that import retirement can be capped by
    each fuel family's actual imports.
    """
    rem_h2, rem_d = pot.astype(float).copy(), dem.astype(float).copy()
    cov, spend, co2, covg = [0.0], [0.0], [0.0], [0.0]
    fam_cov = [0.0, 0.0]                       # oil family, gas family

    def take(k):
        ci, fi = cell[k], fuel[k]
        if rem_d[fi] <= 0.0 or rem_h2[ci] <= 0.0:
            return
        q = min(rem_d[fi], rem_h2[ci] / mu[fi])
        if q <= 0.0:
            return
        rem_d[fi] -= q
        rem_h2[ci] -= q * mu[fi]
        cov.append(cov[-1] + q)
        spend.append(spend[-1] + q * prem[k])
        co2.append(co2[-1] + q * ef[fi])
        covg.append(covg[-1] + (q if isgas[fi] else 0.0))
        fam_cov[int(isgas[fi])] += q

    if dep is None:
        for k in np.argsort(prem, kind="stable"):
            take(k)
    else:
        key = np.where(dep > 0, prem / np.maximum(dep, 1e-12), np.inf)
        deferred = []
        for k in np.lexsort((prem, key)):
            g = int(isgas[fuel[k]])
            if not np.isfinite(key[k]) or fam_cov[g] >= fam_cap[g]:
                deferred.append(k)
                continue
            take(k)
        for k in sorted(deferred, key=lambda i: prem[i]):
            take(k)
    return np.array(cov), np.array(spend), np.array(co2), np.array(covg)


def _sec_opt(prem, cell, fuel, pot, dem, mu, isgas, cap_g, cap_o,
             budget):
    """Security-OPTIMAL allocation of one budget: the LP that maximises
    import exposure retired (GJ) subject to the budget, each cell's
    firm-hydrogen output, each fuel's demand and the two family import
    caps — under the paper's displacement rule (a domestic gigajoule
    displaces an imported one of its own family until that family's
    imports are exhausted). Unlike a greedy order it is an optimum, so
    it never retires less than the cheapest-first fill. Returns
    (GJ covered, GJ retired).
    """
    from scipy.optimize import linprog
    from scipy.sparse import coo_matrix
    n = len(prem)
    ncell, nfuel = int(pot.size), int(dem.size)
    # variables: x_k (n pairs), r_o, r_g
    nv = n + 2
    rows, cols, vals, b = [], [], [], []
    r = 0
    rows += [r] * n; cols += list(range(n)); vals += list(prem); b.append(budget); r += 1
    for k in range(n):                     # hydrogen per cell
        rows.append(r + cell[k]); cols.append(k); vals.append(mu[fuel[k]])
    b += list(pot); r += ncell
    for k in range(n):                     # demand per fuel
        rows.append(r + fuel[k]); cols.append(k); vals.append(1.0)
    b += list(dem); r += nfuel
    # r_o <= sum(oil x);  r_g <= sum(gas x)   (and r <= family cap via
    # the variable bounds below): one domestic GJ retires one imported
    # GJ of its family until the family's imports are exhausted
    for k in range(n):
        g = bool(isgas[fuel[k]])
        rows.append(r + int(g)); cols.append(k)
        vals.append(-1.0)
    rows += [r, r + 1]; cols += [n, n + 1]; vals += [1.0, 1.0]
    b += [0.0, 0.0]; r += 2
    A = coo_matrix((vals, (rows, cols)), shape=(r, nv)).tocsr()
    c = np.zeros(nv); c[n:] = -1.0        # maximise r_o + r_g
    bounds = [(0, None)] * n + [(0, cap_o), (0, cap_g)]
    res = linprog(c, A_ub=A, b_ub=np.array(b), bounds=bounds,
                  method="highs")
    if not res.success:
        return np.nan, np.nan
    x = res.x[:n]
    return float(x.sum()), float(-res.fun)


JODI_DIR = inputs.MAPS.parent / "jodi"
STALE_YEARS = 3
MATERIAL = 0.10      # stale domestic output must be >= 10% of use to matter
# ISO3 (OWID) -> ISO2 (JODI) for the economies whose OWID production series
# stop years before their consumption series
_ISO2 = {"AUT": "AT", "BGR": "BG", "CHL": "CL", "HRV": "HR", "CZE": "CZ",
         "ECU": "EC", "HUN": "HU", "IRL": "IE", "JPN": "JP", "MAR": "MA",
         "NZL": "NZ", "PHL": "PH", "SVK": "SK", "ZAF": "ZA", "BLR": "BY",
         "DEU": "DE", "LTU": "LT", "NLD": "NL", "PAK": "PK", "POL": "PL",
         "TUR": "TR", "UKR": "UA"}
# economies with no OWID oil or gas row (the EI review groups them into
# regional totals): their dependence is taken from JODI where JODI has a
# complete year, instead of the all-energy import ratio, which counted oil
# and gas exporters such as Nigeria and Libya as importers
_MISSING_ISO2 = {
    "Afghanistan": "AF", "Albania": "AL", "Angola": "AO", "Armenia": "AM", "Belize": "BZ",
    "Benin": "BJ", "Bhutan": "BT", "Bolivia": "BO", "Bosnia and Herzegovina": "BA",
    "Botswana": "BW", "Burkina Faso": "BF", "Cambodia": "KH", "Cameroon": "CM",
    "Central African Republic": "CF", "Chad": "TD", "Costa Rica": "CR", "Cuba": "CU",
    "Democratic Republic of the Congo": "CD", "Dominican Republic": "DO", "Eritrea": "ER",
    "Ethiopia": "ET", "Fiji": "FJ", "Gabon": "GA", "Georgia": "GE", "Ghana": "GH",
    "Guatemala": "GT", "Guinea": "GN", "Guinea-Bissau": "GW", "Guyana": "GY", "Haiti": "HT",
    "Honduras": "HN", "Ivory Coast": "CI", "Jordan": "JO", "Kenya": "KE", "Kyrgyzstan": "KG",
    "Laos": "LA", "Liberia": "LR", "Libya": "LY", "Madagascar": "MG", "Malawi": "MW",
    "Mali": "ML", "Mauritania": "MR", "Mongolia": "MN", "Mozambique": "MZ", "Myanmar": "MM",
    "Namibia": "NA", "Nepal": "NP", "Nicaragua": "NI", "Niger": "NE", "Nigeria": "NG",
    "North Korea": "KP", "Panama": "PA", "Papua New Guinea": "PG", "Paraguay": "PY",
    "Republic of the Congo": "CG", "Rwanda": "RW", "Senegal": "SN", "Sierra Leone": "SL",
    "Somalia": "SO", "South Sudan": "SS", "Sudan": "SD", "Suriname": "SR", "Syria": "SY",
    "Tajikistan": "TJ", "Tunisia": "TN", "Uganda": "UG", "Uruguay": "UY", "Yemen": "YE",
    "Zambia": "ZM", "Zimbabwe": "ZW",
    # 2026-10-06: no OWID consumption row either; without these entries they fell through to
    # the last-resort energy-import ratio (data audit)
    "Republic of Serbia": "RS", "United Republic of Tanzania": "TZ", "The Bahamas": "BS"}


def _jodi_dep(fuel: str, iso2: str):
    """(year, net import dependence) from JODI for the latest year with all
    twelve months reported: (total imports - total exports) / demand, the
    Eurostat definition of import dependency, clipped to [0, 1]. None when
    JODI has no complete year."""
    f = JODI_DIR / ("STAGING_world_NewFormat.csv" if fuel == "gas" else "jodi_oil_net.csv")
    if not f.exists():
        return None
    key = ("_jodi_" + fuel)
    if key not in _JODI_CACHE:
        # keep_default_na=False: Namibia's code "NA" must not become NaN
        j = pd.read_csv(f, keep_default_na=False, na_values=[""])
        j["OBS_VALUE"] = pd.to_numeric(j.OBS_VALUE, errors="coerce")
        if fuel == "gas":
            j = j[j.UNIT_MEASURE == "TJ"]
            flows = {"imp": "TOTIMPSB", "exp": "TOTEXPSB", "dem": "TOTDEMC"}
        else:
            # crude + products in kt (built from the JODI primary and
            # secondary annual files): imports, exports and product demand
            j = j[j.UNIT_MEASURE == "KTONS"]
            flows = {"imp": "TOTIMPSB", "exp": "TOTEXPSB", "dem": "TOTDEMC"}
        j = j[j.FLOW_BREAKDOWN.isin(flows.values())].copy()
        j["year"] = j.TIME_PERIOD.str[:4].astype(int)
        _JODI_CACHE[key] = (j, flows)
    j, flows = _JODI_CACHE[key]
    s = j[j.REF_AREA == iso2]
    for y in sorted(s.year.unique(), reverse=True):
        p = s[s.year == y].pivot_table(index="TIME_PERIOD", columns="FLOW_BREAKDOWN",
                                       values="OBS_VALUE", aggfunc="sum")
        if all(v in p for v in flows.values()) and \
                p[list(flows.values())].notna().all(axis=1).sum() == 12 and p[flows["dem"]].sum() > 0:
            dep = (p[flows["imp"]].sum() - p[flows["exp"]].sum()) / p[flows["dem"]].sum()
            return int(y), float(min(max(dep, 0.0), 1.0))
    return None


_JODI_CACHE: dict = {}

# OWID names -> the model's (Natural Earth) names; the last three used to
# drop out of every join (2026-09-26)
OWID_RENAME = {"United States": "United States of America",
               "Serbia": "Republic of Serbia",
               "Tanzania": "United Republic of Tanzania",
               "Bahamas": "The Bahamas"}


def _un_use_gj() -> dict:
    """{(country, 'oil'|'gas'): GJ/yr} from the UN Energy Statistics file
    un_energy already parsed: every transaction in it except 1213 (a part
    of 121), latest of 2023/2022 per series."""
    from . import un_energy
    f = un_energy.UND / "un_sector_fuel_tj.csv"
    if not f.exists():
        return {}
    u = pd.read_csv(f, dtype={"area": str, "transaction": str})
    u = u[(u.transaction != "1213") & u.group.isin(["OIL", "GAS"])]
    u = u.assign(area=u.area.str.zfill(3)).sort_values("year")
    tot = u.groupby(["group", "area", "transaction"]).tj.last() \
           .groupby(["group", "area"]).sum()
    nm = un_energy._name_map(list(_MISSING_ISO2))
    return {(c, grp.lower()): float(tot.get((grp, a), 0.0)) * 1e3
            for c, a in nm.items() for grp in ("OIL", "GAS")}


def _net_dep(log: bool = False):
    """net import dependence per fuel, max(0, 1 - production /
    consumption), latest observed year per country from OWID (EI
    Statistical Review lineage).

    2026-09-25: several OWID production series stop in 2016 while
    consumption runs to 2024, and pairing the two years overstated
    self-sufficiency where domestic fields are declining (Philippines,
    Ireland). Where the production year lags the consumption year by more
    than STALE_YEARS, the dependence is taken from JODI instead (latest
    complete year, (imports - exports) / demand)."""
    d = pd.read_csv(inputs.MAPS / "owid_energy.csv",
                    usecols=["country", "iso_code", "year", "oil_consumption",
                             "oil_production", "gas_consumption",
                             "gas_production"])
    d = d.replace({"country": OWID_RENAME})
    oil, gas, rec = {}, {}, []
    for c, g in d[d.year >= 2015].groupby("country"):
        g = g.sort_values("year")
        iso3 = g.iso_code.dropna().iloc[0] if g.iso_code.notna().any() else None
        for fuel, cons_c, prod_c, out in (("oil", "oil_consumption",
                                           "oil_production", oil),
                                          ("gas", "gas_consumption",
                                           "gas_production", gas)):
            gc = g.dropna(subset=[cons_c])
            if not len(gc) or gc.iloc[-1][cons_c] <= 0:
                continue
            gp = g.dropna(subset=[prod_c])
            prod = gp.iloc[-1][prod_c] if len(gp) else 0.0
            out[c] = max(0.0, 1.0 - prod / gc.iloc[-1][cons_c])
            yc = int(gc.iloc[-1].year)
            yp = int(gp.iloc[-1].year) if len(gp) else None
            stale_share = prod / gc.iloc[-1][cons_c]
            if (yp is not None and yp < yc - STALE_YEARS and stale_share >= MATERIAL
                    and iso3 in _ISO2):
                jd = _jodi_dep(fuel, _ISO2[iso3])
                if jd is not None and jd[0] > yp:      # only a newer year replaces
                    rec.append(dict(country=c, fuel=fuel, owid_prod_year=yp, owid_cons_year=yc,
                                    owid_dep=out[c], jodi_year=jd[0], jodi_dep=jd[1]))
                    out[c] = jd[1]
    # economies the EI review names only inside regional totals (no OWID
    # consumption row): net import dependence from UN Energy Statistics
    # trade, (imports - exports) / (production + imports - exports), crude,
    # NGL and oil products for oil, natural gas for gas (lcof.un_trade;
    # checked against OWID where both exist: oil r = 0.994 with no class
    # disagreement, gas r = 0.988). Gas supply below 1 PJ a year counts as no
    # gas market, so the family falls back to oil. Only where the UN has no
    # row does the older rule apply: OWID production against UN final use,
    # guarded by World Bank net energy imports (oil) and JODI (gas). JODI oil
    # is never used for these economies: Nigeria reports 7-11 Mt of exports
    # against a crude export trade of about 70 Mt.
    from . import un_energy
    ut_f = un_energy.UND / "un_net_dependence.csv"
    ut = (pd.read_csv(ut_f, dtype={"area": str}).assign(area=lambda x: x.area.str.zfill(3))
          .set_index(["area", "group"]) if ut_f.exists() else None)
    area = un_energy._name_map(list(_MISSING_ISO2))
    un = _un_use_gj()
    wdi = pd.read_csv(inputs.MAPS / "vulnerability_inputs.csv",
                      index_col="country").energy_import_pct / 100.0
    owid_name = {"Republic of the Congo": "Congo", "Ivory Coast": "Cote d'Ivoire",
                 "Democratic Republic of the Congo": "Democratic Republic of Congo"}
    for c, iso2 in _MISSING_ISO2.items():
        g = d[d.country == owid_name.get(c, c)].sort_values("year")
        for fuel, prod_c, out in (("oil", "oil_production", oil), ("gas", "gas_production", gas)):
            if c in out:
                continue
            key = (area.get(c), fuel.upper())
            if ut is not None and key in ut.index:
                r = ut.loc[key]
                if fuel == "gas" and (r["prod"] + r.imp - r.exp) < 1e3:    # < 1 PJ
                    continue
                out[c] = float(r.dep)
                rec.append(dict(country=c, fuel=fuel, owid_prod_year=None,
                                owid_cons_year=None, owid_dep=None, jodi_year=int(r.year),
                                jodi_dep=round(float(r.dep), 4), source="UN energy trade"))
                continue
            use = un.get((c, fuel), 0.0)
            if use <= 0:
                continue
            gp = g.dropna(subset=[prod_c])
            prod = float(gp.iloc[-1][prod_c]) * 3.6e6 if len(gp) else 0.0   # TWh -> GJ
            dep0 = max(0.0, 1.0 - prod / use)
            dep, src = dep0, "OWID production / UN use"
            if fuel == "oil" and dep0 == 0.0 and wdi.get(c, np.nan) > 0:
                dep, src = min(float(wdi[c]), 1.0), "WDI net energy imports"
            if fuel == "gas":
                jd = _jodi_dep("gas", iso2)
                if jd is not None and jd[1] > dep0:
                    dep, src = jd[1], f"JODI {jd[0]}"
            out[c] = dep
            rec.append(dict(country=c, fuel=fuel,
                            owid_prod_year=int(gp.iloc[-1].year) if len(gp) else None,
                            owid_cons_year=None, owid_dep=round(dep0, 4), jodi_year=None,
                            jodi_dep=round(dep, 4), source=src))
    if log and rec:
        pd.DataFrame(rec).round(4).to_csv(inputs.MAPS / "net_dep_jodi_overrides.csv", index=False)
    return pd.Series(oil), pd.Series(gas)


def family_dependence(index=None):
    """Per-family net import dependence on the layer the budget figure
    uses: OWID net dependence, the gas family falling back to oil where
    a country has no gas market, and the ledger's e_imp/e_use ratio as
    the last resort. Returns (dep_gas, dep_oil)."""
    dep_o, dep_g = _net_dep()
    si = pd.read_csv(inputs.MAPS / "security_index.csv", index_col=0)
    e_ratio = (si.e_imp_gj / si.e_use_gj).clip(0, 1)
    if index is None:
        index = dep_o.index.union(dep_g.index).union(e_ratio.index)
    index = pd.Index(index)
    o = dep_o.reindex(index)
    g = dep_g.reindex(index).fillna(o)
    e = e_ratio.reindex(index)
    return g.fillna(e).clip(0, 1), o.fillna(e).clip(0, 1)


def compute(scale: float = 1.0, write: bool = True,
            ghg: str = "co2", cost_layer: str = "median",
            carbon: str = "cheapest"):
    """cost_layer: 'median' = the per-year 2025 sweep (optimistic
    bound); 'fixed' = the fixed-design layer (worst-year LCOH/LCOE
    per cell from lcoh_global_fixed.csv, validated within ~0.5%
    median of the joint 20-year optimum). carbon: 'cheapest' = each
    cell's cheapest CO2 source (Figs 2-3 layer); 'dac' = direct air
    capture everywhere (sensitivity, written to security_budget_dac.csv)."""
    meta = inputs.load_meta(2025)
    land = meta[meta.cell_type == "land"].copy()
    lc = pd.read_csv(inputs.MAPS / f"lcoh_global_2025{SUFFIX}.csv") \
           .set_index("cell_id")
    if cost_layer == "fixed":
        fx = pd.read_csv(inputs.MAPS / "lcoh_global_fixed.csv",
                         index_col=0)
        lc = lc.join(fx[["lcoh_usd_gj", "lcoe_usd_mwh"]],
                     rsuffix="_fx", how="inner")
        lc["lcoh_usd_gj"] = lc.pop("lcoh_usd_gj_fx")
        lc["lcoe_usd_mwh"] = lc.pop("lcoe_usd_mwh_fx")
    land = land.join(lc[["cap_pv", "cap_wind", "lcoh_usd_gj",
                         "lcoe_usd_mwh"]], how="inner")
    land = land[np.isfinite(land.cap_pv) & np.isfinite(land.cap_wind)
                & np.isfinite(land.lcoh_usd_gj)]

    # ---- land-limited firm hydrogen per cell (as in supply_demand) -------
    land["pot_h2_gj"] = firm_h2_potential_gj(land, scale=scale)

    # ---- demand and comparators ------------------------------------------
    dg = pd.read_csv(inputs.MAPS / "demand_fuel_grid.csv", index_col=0)
    cols = [f + "_gj" for f in FUELS]
    dgc = dg.join(meta[["country"]]).groupby("country")[cols].sum()
    dgc.columns = FUELS
    dgc = dgc[dgc.sum(axis=1) > 0]
    grey = _grey(dgc)
    # CO2 at the cheapest source within reach of each cell (industrial,
    # biogenic or DAC), the same carbon layer as Figs 2 and 3; carbon="dac"
    # prices every carbon fuel at direct air capture as a sensitivity
    if carbon == "dac":
        co2_cost = P.C_CO2_DAC
    else:
        co2df = pd.read_csv(inputs.MAPS / "co2_cost_by_cell.csv").set_index("cell_id")
        co2_cost = co2df.co2_cost.reindex(land.index).fillna(P.C_CO2_DAC)
    lcof = lcof_cells(land, co2_cost)

    # 2026-10-21: GDP projected to the cost year (IMF WEO to 2030, SSP2 after); value of lost fuel at 2025
    from .gdp_projection import projected
    si = projected(pd.read_csv(inputs.MAPS / "security_index.csv", index_col=0))
    # the import share of THE BILL, not of total energy: NET per-fuel
    # dependence max(0, 1 - production/consumption) from OWID (EI
    # Statistical Review), weighted by each country's oil-/gas-family
    # composition of its addressable demand. Two wrong layers rejected
    # on the way here: the WDI whole-energy share lets domestic coal
    # dilute the denominator (China read 24% when its oil-and-gas bill
    # is half imported), and the ledger's Comtrade-based dep_oil/dep_gas
    # are GROSS flows capped at 1, which read refining-and-trading hubs
    # (UK, Netherlands) as 100%-dependent when their net dependence is
    # ~50%. Where a country has no gas market the gas-family fuels
    # displace imported oil products, so dep_gas falls back to dep_oil;
    # the ledger's e_imp/e_use ratio is the last resort (3 economies).
    dep_o, dep_g = _net_dep()
    GASF = ["e-methane", "ammonia", "methanol"]
    w_gas = dgc[GASF].sum(axis=1) / dgc.sum(axis=1)
    dep_gas = dep_g.reindex(w_gas.index).fillna(
        dep_o.reindex(w_gas.index))
    imp = (w_gas * dep_gas
           + (1 - w_gas) * dep_o.reindex(w_gas.index)).clip(0, 1)
    e_ratio = (si.e_imp_gj / si.e_use_gj).clip(0, 1)
    imp = imp.fillna(e_ratio.reindex(imp.index))

    rec, curves = [], {}
    for c in dgc.index:
        if c not in si.index or not np.isfinite(si.gdp_usd.get(c, np.nan)):
            continue
        cc = land.index[land.country == c]
        if len(cc) == 0 or not grey.loc[c].notna().any():
            continue
        dem = dgc.loc[c]
        tot = float(dem.sum())
        if tot <= 0:
            continue
        # every (cell, fuel) way to replace a GJ of the fuel bill
        pot = land.pot_h2_gj.reindex(cc).to_numpy()
        nc = len(cc)
        prem, prem_c, cell_ix, fuel_ix, dvec, muvec, efvec = (
            [], [], [], [], [], [], [])
        p_co2 = float(CARBON_PRICE.get(c, 0.0))
        for j, f in enumerate(FUELS):
            d_f = float(dem[f])
            dvec.append(d_f)
            muvec.append(MU_H2[f])
            k = FOSSIL[f]["ef"]                   # t CO2(e) per GJ displaced
            efvec.append(EF[k] * (GHG_UPLIFT[k] if ghg == "co2e" else 1.0))
            if d_f <= 0 or not np.isfinite(grey.loc[c, f]):
                dvec[-1] = 0.0
                continue
            p = np.maximum(lcof.loc[cc, f].to_numpy() - grey.loc[c, f], 0.0)
            prem.append(p)
            # what the state still pays once the country's own carbon
            # price is credited against the displaced emissions
            prem_c.append(np.maximum(p - p_co2 * efvec[j], 0.0))
            cell_ix.append(np.arange(nc))
            fuel_ix.append(np.full(nc, j))
        if not prem:
            continue
        ci_, fi_ = np.concatenate(cell_ix), np.concatenate(fuel_ix)
        dv, mv, ev = np.array(dvec), np.array(muvec), np.array(efvec)
        isg = np.array([f in GASF for f in FUELS])
        pr_ = np.concatenate(prem)

        q_imp = float(imp.get(c, np.nan))
        # per-family import shares of the bill, for the retirement cap:
        # a domestic GJ of a gas-family fuel can only retire gas-family
        # imports, and likewise for the oil family
        wg = float(w_gas.get(c, np.nan))
        dg_c = float(dep_gas.get(c, np.nan))
        do_c = float(dep_o.get(c, np.nan)) if c in dep_o.index else np.nan
        qg = wg * dg_c
        qo = (1 - wg) * do_c
        fam_ok = (np.isfinite(qg) and np.isfinite(qo) and q_imp > 0
                  and abs(qg + qo - q_imp) < 1e-6)

        cov, spend, co2, covg = _curve(pr_, ci_, fi_, pot, dv, mv, ev,
                                       isg)
        cov_c, spend_c, co2_c, _ = _curve(np.concatenate(prem_c), ci_,
                                          fi_, pot, dv, mv, ev, isg)
        cov = cov / tot                                   # share of demand
        covg = covg / tot
        cov_c = cov_c / tot
        gdp = float(si.gdp_usd[c])
        bud = spend / gdp * 100.0                         # % of GDP per year
        bud_c = spend_c / gdp * 100.0
        curves[c] = (bud, cov, co2, bud_c, cov_c, co2_c)
        esd = float(si.esd_c_usd.get(c, np.nan))
        esd_hi = float(si.esd_gdp_hi_pct.get(c, np.nan)) / 100.0 * gdp
        row = dict(country=c, dem_fuel_gj=tot, gdp_usd=gdp,
                   import_pct=q_imp,
                   cost_full_gdp_pct=float(bud[-1]) if cov[-1] > 0.999
                   else np.nan,
                   max_cov=float(cov[-1]))
        row["p_co2_usd_t"] = p_co2
        row["co2_full_mt"] = float(co2[-1]) / 1e6
        for b in BUDGETS:
            x = float(np.interp(b, bud, cov))
            row[f"cov_{b:.0f}"] = x
            row[f"cov_ccp_{b:.0f}"] = float(np.interp(b, bud_c, cov_c))
            e = float(np.interp(b, bud, co2))
            row[f"co2_{b:.0f}_mt"] = e / 1e6
            sp = min(b, float(bud[-1])) / 100.0 * gdp
            # gross: the whole premium charged to carbon. net: the premium
            # left after the security loss the same build retires — the
            # honest split when the build is made for security anyway
            row[f"abate_cost_{b:.0f}"] = sp / e if e > 0 else np.nan
            if fam_ok:
                xg = float(np.interp(b, bud, covg))
                ret = (min(xg, qg) + min(x - xg, qo)) / q_imp
                # the same budget allocated security-OPTIMALLY (LP):
                # the most exposure the money could retire
                cs, rs = _sec_opt(pr_, ci_, fi_, pot, dv, mv, isg,
                                  qg * tot, qo * tot, b / 100.0 * gdp)
                row[f"cov_sf_{b:.0f}"] = cs / tot
                row[f"ret_sf_{b:.0f}"] = rs / (q_imp * tot)
            elif np.isfinite(q_imp) and q_imp > 0:
                ret = min(x / q_imp, 1.0)
                row[f"cov_sf_{b:.0f}"] = x
                row[f"ret_sf_{b:.0f}"] = ret
            else:
                ret = np.nan
                row[f"cov_sf_{b:.0f}"] = x
                row[f"ret_sf_{b:.0f}"] = np.nan
            row[f"ret_{b:.0f}"] = ret
            for tag, esd_v in (("", esd), ("_hi", esd_hi)):
                av = (esd_v * ret if np.isfinite(esd_v)
                      and np.isfinite(ret) else np.nan)
                row[f"abate_net{tag}_{b:.0f}"] = ((sp - av) / e
                                                  if e > 0 else np.nan)
            spend_b = min(b, float(bud[-1])) / 100.0 * gdp   # unspent if capped
            row[f"spend_{b:.0f}_bn"] = spend_b / 1e9
            row[f"esd_avoid_{b:.0f}_bn"] = esd * ret / 1e9 \
                if np.isfinite(esd) and np.isfinite(ret) else np.nan
            for tag, e in (("", esd), ("_hi", esd_hi)):
                row[f"bcr{tag}_{b:.0f}"] = (
                    e * ret / spend_b if np.isfinite(e) and np.isfinite(ret)
                    and spend_b > 0 else np.nan)
        # what it costs to domesticate exactly the imported part — only
        # meaningful where the domestic resource can reach that far at
        # all; capping at the ceiling would price hitting the ceiling,
        # not covering the imports
        feasible = (np.isfinite(q_imp) and q_imp > 0
                    and cov[-1] >= q_imp - 1e-9)
        row["imports_reachable"] = bool(feasible)
        row["cost_imports_gdp_pct"] = (float(np.interp(q_imp, cov, bud))
                                       if feasible else np.nan)
        rec.append(row)

    df = pd.DataFrame(rec).set_index("country")
    if write:
        df.to_csv(inputs.MAPS / ("security_budget.csv" if carbon != "dac"
                                 else "security_budget_dac.csv"))
    return df, curves


def sensitivity_ghg():
    """Combustion CO2 only is the floor; what does a life-cycle CO2e
    basis do to the same build?"""
    for g in ("co2", "co2e"):
        df, _ = compute(write=False, ghg=g)
        d = df.loc[[c for c in core_countries(df.index) if c in df.index]]
        print(f"  {g:5s}: 1% of GDP abates "
              f"{d.co2_1_mt.sum() / 1e3:.2f} Gt per year at a median "
              f"${d.abate_cost_1.median():.0f} per tonne; 3% abates "
              f"{d.co2_3_mt.sum() / 1e3:.2f} Gt at "
              f"${d.abate_cost_3.median():.0f}")
    print("  (the CO2e uplift for natural gas rests on an assumed "
          "supply-chain methane intensity — pick a source before "
          "publishing it)")


def sensitivity():
    """The ceilings are set by the screened-land assumption: baseline =
    5% of each country's eligible land, high = 10% (scale 2)."""
    print("screened-land sensitivity (share of ELIGIBLE land developed):")
    for scale, lab in ((1.0, "5% of eligible (baseline)"),
                       (2.0, "10% of eligible (high)")):
        df, _ = compute(scale=scale, write=False)
        d = df.loc[[c for c in core_countries(df.index) if c in df.index]]
        print(f"  {lab}: 1% of GDP buys a median "
              f"{d.cov_1.median():.0%} of the fuel bill; land binds before "
              f"the budget in {(d.max_cov <= d.cov_1 + 1e-6).sum()} of "
              f"{len(d)} core economies; median ceiling "
              f"{d.max_cov.median():.0%}")


def main():
    df, curves = compute()
    core = [c for c in core_countries(df.index) if c in df.index]
    d = df.loc[core]
    print(f"{len(df)} economies priced; core-30 present: {len(d)}")
    # DAC-carbon sensitivity (the pre-2026-09-17 convention), for the text
    ddac, _ = compute(write=True, carbon="dac")
    dd = ddac.loc[core]
    print(f"  carbon at DAC everywhere instead of the cheapest source: 1% of "
          f"GDP buys a median {dd.cov_1.median():.1%} of the bill (cheapest "
          f"source {d.cov_1.median():.1%}), abating at a median "
          f"${dd.abate_cost_1.median():.0f} per tonne (${d.abate_cost_1.median():.0f})")
    for b in BUDGETS:
        print(f"  {b:.0f}% of GDP per year buys a median "
              f"{d[f'cov_{b:.0f}'].median():.0%} of the addressable fuel "
              f"bill ({d[f'cov_{b:.0f}'].quantile(.25):.0%}-"
              f"{d[f'cov_{b:.0f}'].quantile(.75):.0%} IQR), retiring a "
              f"median {d[f'ret_{b:.0f}'].median():.0%} of import exposure; "
              f"benefit/cost {d[f'bcr_{b:.0f}'].median():.2f} central, "
              f"{d[f'bcr_hi_{b:.0f}'].median():.2f} at the ENTSOG anchor")
    bind = (d.max_cov <= d.cov_1 + 1e-6).sum()
    print(f"  land, not money, is the binding constraint in {bind} of "
          f"{len(d)} core economies (1% of GDP already exhausts the "
          f"domestic resource): median ceiling {d.max_cov.median():.0%}")
    full = d.cost_full_gdp_pct.dropna()
    print(f"  by contrast, full independence where it is physically "
          f"possible at all ({len(full)} of {len(d)}): median "
          f"{full.median():.1f}% of GDP per year (max {full.max():.0f}%) "
          f"— the number that reads as a refutation")
    ci = d.cost_imports_gdp_pct.dropna()
    exposed = int((d.import_pct > 0).sum())
    print(f"  domesticating exactly the IMPORTED part: possible on "
          f"screened land in {len(ci)} of the {exposed} core "
          f"economies with net imports, at a median "
          f"{ci.median():.1f}% of GDP per year (IQR "
          f"{ci.quantile(.25):.1f}-{ci.quantile(.75):.1f}); for the other "
          f"{exposed - len(ci)} no budget reaches it domestically")
    for c in ["China", "Japan", "Germany", "India", "South Korea",
              "United States of America", "Chile", "Morocco"]:
        if c in d.index:
            r = d.loc[c]
            print(f"    {SHORT.get(c, c):15s} 1% -> {r.cov_1:5.0%}  "
                  f"2% -> {r.cov_2:5.0%}  3% -> {r.cov_3:5.0%}  "
                  f"(imports {r.import_pct:.0%}, full "
                  f"{r.cost_full_gdp_pct:.0f}% GDP)")

    print("  the carbon dividend of the same spend:")
    for b in BUDGETS:
        tot = d[f"co2_{b:.0f}_mt"].sum()
        ac = d[f"abate_cost_{b:.0f}"]
        print(f"    {b:.0f}% of GDP abates {tot / 1e3:.2f} GtCO2 per year "
              f"across the core 30 ({tot / d.co2_full_mt.sum():.0%} of what "
              f"full substitution of their fuel bill would abate), at an "
              f"implied median ${ac.median():.0f} per tCO2 "
              f"(IQR ${ac.quantile(.25):.0f}-{ac.quantile(.75):.0f})")
    below = (d.abate_cost_1 <= d.p_co2_usd_t).sum()
    priced = int((d.p_co2_usd_t > 0).sum())
    print(f"    charged entirely to carbon, the first per cent costs less "
          f"per tonne than the country's own carbon price in {below} of "
          f"the {priced} core economies that price carbon at all")
    for b in BUDGETS:
        net = d[f"abate_net_hi_{b:.0f}"].dropna()
        print(f"    net of the security loss it retires (ENTSOG anchor), "
              f"the {b:.0f}% budget abates at a median "
              f"${net.median():.0f} per tCO2, negative in "
              f"{(net < 0).sum()} of {len(net)} economies")
    for b in BUDGETS:
        gain = (d[f"cov_ccp_{b:.0f}"] - d[f"cov_{b:.0f}"])
        print(f"    crediting the observed carbon price stretches the "
              f"{b:.0f}% budget by a median "
              f"{gain.median() * 100:+.1f} points of the fuel bill "
              f"(max {gain.max() * 100:+.0f})")

    _table(d)
    _figure(d, curves)
    _figure_capacity(df, bold=set(core))     # 2026-10-22: all 139 economies, the core 30 in bold
    _figure_co2(d, curves)


def _table(d: pd.DataFrame):
    rows = []
    for c in d.sort_values("cov_1", ascending=False).index:
        r = d.loc[c]
        rows.append(
            f"{SHORT.get(c, c)} & {r.dem_fuel_gj / UMM / 1e9:.2f} & "
            f"{r.import_pct * 100:.0f} & {r.cov_1 * 100:.0f} & "
            f"{r.cov_2 * 100:.0f} & {r.cov_3 * 100:.0f} & "
            + ("n/a" if r.import_pct <= 0
               else f"{r.cost_imports_gdp_pct:.1f}"
               if np.isfinite(r.cost_imports_gdp_pct) else "--") + " & "
            + (f"{r.bcr_1:.2f}" if np.isfinite(r.bcr_1) else "--"))
    header = (" & demand & bill & " + BS + "multicolumn{3}{c}{share of the "
              "fuel bill made at home} & to & benefit/ " + EOL + NL
              + BS + "cmidrule(lr){4-6}" + NL
              + " & (bn & imports & 1" + BS + "% & 2" + BS + "% & 3" + BS
              + "% & imports & cost " + EOL + NL
              + "Country & MMBtu/yr) & (" + BS + "%) & GDP & GDP & GDP & (" + BS
              + "% GDP) & at 1" + BS + "% " + EOL)
    body = (BS + "begin{tabular}{@{}l r r r r r r r@{}}" + NL + BS
            + "toprule" + NL + header + NL + BS + "midrule" + NL
            + (" " + EOL + NL).join(rows) + " " + EOL + NL
            + BS + "bottomrule" + NL + BS + "end{tabular}" + NL)
    texdir = inputs.MAPS.parent.parent / "synthetic_fuel_nature"
    (texdir / "tab_budget.tex").write_text(body, encoding="utf-8")


def _figure_capacity(d: pd.DataFrame, name: str = "fig_si_capacity", bold=()):
    """Supplementary figure (2026-10-05): why 1% of GDP buys so different
    shares in Fig. 5. Where the budget binds, the share made at home is
    1% of GDP per MMBtu of addressable demand divided by the mean premium
    of the fuel bought; where land binds first, part of the budget is left
    unspent. Rows run from the highest GDP per MMBtu (top) to the lowest."""
    mmbtu = d.dem_fuel_gj / P.MMBTU_PER_GJ
    g = (d.gdp_usd / mmbtu).rename("gdp")
    prem = (d.spend_1_bn * 1e9 / (d.cov_1 * mmbtu)).rename("prem")
    used = (d.spend_1_bn * 1e9 / d.gdp_usd * 100).rename("used")
    land = d.max_cov <= d.cov_1 + 1e-6
    # the identity the figure rests on, where the budget binds
    bb = ~land
    assert np.allclose(d.cov_1[bb], 0.01 * g[bb] / prem[bb], rtol=1e-6)
    assert (used[bb] > 0.999).all() and (used[land] < 1.0).all()
    order = list(g.sort_values(ascending=False).index)      # highest GDP per MMBtu on top
    ys = np.arange(len(order))
    names = [SHORT.get(c, c) for c in order]
    # 2026-10-22 (user: every SI figure covers the 139 economies): a full page and 5 pt type for many rows,
    # with the economies in `bold` (the core 30) in bold
    many = len(order) > 40
    if many:
        from .fig4a_all import SHORT as SH139           # the short names of the 139-economy figures
        names = [SH139.get(c, SHORT.get(c, c)) for c in order]
    # 2026-10-22 (user: names must not touch): 139 rows go in two blocks side by side, 6 pt names
    fs = 6.0 if many else 7.0
    height = 226.0 if many else 112.0
    gmax = max(4200.0, float(np.ceil(g.max() / 500.0) * 500.0))
    tk = np.arange(0, gmax + 1, 1000 if gmax <= 4200 else 2000)
    tr_ = mpl.transforms.blended_transform_factory

    # one panel, back to back (2026-10-05): GDP per MMBtu runs left
    # from the centre, the mean premium runs right, the names sit between
    # them; the shares themselves are in Fig. 5 and are not repeated here
    fig = plt.figure(figsize=(183 * MM, height * MM))
    yb, yh = (0.05, 0.92) if many else (0.10, 0.83)
    parts = [order[: (len(order) + 1) // 2], order[(len(order) + 1) // 2:]] if many else [order]
    # block geometry as figure fractions: (left, GDP axis width, name gap, premium axis width)
    geo = [(0.005, 0.15, 0.13, 0.13), (0.505, 0.15, 0.13, 0.13)] if many else [(0.02, 0.40, 0.135, 0.33)]
    for part, (x0, wa, wn, wb) in zip(parts, geo):
        n = len(part)
        ys = np.arange(n)
        a = fig.add_axes([x0, yb, wa, yh])
        b = fig.add_axes([x0 + wa + wn, yb, wb, yh])
        a.barh(ys, g[part], height=0.66, color="#9AA5AF")
        b.barh(ys, prem[part], height=0.66, color="#4A90D9")
        # 2026-10-22: the axis reaches the largest value, so no bar is cut
        a.set_xlim(gmax, 0)                               # grows to the left
        a.set_xticks(tk)
        a.set_xticklabels([f"{v / 1000:g}k" if many and v else f"{v:,.0f}" for v in tk])
        a.set_xlabel("GDP per MMBtu of addressable" + chr(10) + "fuel demand (US\\$)", fontsize=7)
        b.set_xlim(0, 90)
        b.set_xticks([0, 30, 60, 90] if many else [0, 20, 40, 60, 80])
        b.set_xlabel("Mean premium of the fuel bought" + chr(10) + "with 1% of GDP (US\\$ MMBtu$^{-1}$)",
                     fontsize=7)
        for ax in (a, b):
            ax.set_ylim(max(len(p_) for p_ in parts) - 0.4, -0.6)
            ax.set_yticks([])
            ax.tick_params(axis="x", labelsize=7)
            ax.grid(axis="x", alpha=0.20, lw=0.4)
            ax.set_axisbelow(True)
            for s in ("top", "left" if ax is a else "right"):
                ax.spines[s].set_visible(False)
        a.spines["right"].set_visible(True)
        # names centred in the gap between the two halves
        XN = x0 + wa + wn / 2
        for i, cc in enumerate(part):
            a.text(XN, i, names[order.index(cc)], transform=tr_(fig.transFigure, a.transData), fontsize=fs,
                   ha="center", va="center", color="#1A1A1A", clip_on=False,
                   fontweight="bold" if cc in bold else "normal")
        # GDP actually spent: 1% where the budget binds, less where the land
        # ceiling is reached first (bold)
        XC = 1.17
        for i, cc in enumerate(part):
            b.text(XC, i, f"{used[cc]:.2f}", transform=b.get_yaxis_transform(), fontsize=fs, ha="center",
                   va="center", color="#1A1A1A" if land[cc] else "#8A94A0",
                   fontweight="bold" if land[cc] else "normal", clip_on=False)
        b.text(XC, -1.0, "GDP spent" + chr(10) + "(%)", transform=b.get_yaxis_transform(), fontsize=7,
               ha="center", va="bottom", color="#3A4550", clip_on=False)
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.png", dpi=600, bbox_inches="tight")
    plt.close(fig)
    lo_land = g[land].min()
    below = g < lo_land
    print(f"saved {name}.(pdf|png): {int(bb.sum())} economies budget-bound at 1% of GDP "
          f"(GDP/MMBtu {g[bb].min():,.0f}-{g[bb].max():,.0f}), {int(land.sum())} reach the land ceiling first "
          f"(GDP/MMBtu {g[land].min():,.0f}-{g[land].max():,.0f}, spending {used[land].min():.2f}-"
          f"{used[land].max():.2f}% of GDP); all {int(below.sum())} below US${lo_land:,.0f}/MMBtu are "
          f"budget-bound; above it {int(land.sum())} of {int((~below).sum())} reach land")
    for cc in ("Chile", "Saudi Arabia", "Egypt", "Pakistan", "Germany", "Netherlands", "United Kingdom",
               "Israel", "China"):
        print(f"    {cc:15s} GDP/MMBtu {g[cc]:7,.0f}  premium {prem[cc]:5.1f}  share {d.cov_1[cc]:.0%}  "
              f"spent {used[cc]:.2f}% of GDP")


def _figure(d: pd.DataFrame, curves: dict, land_style: str = "hatch",
            name: str = "fig_security_budget", ax=None, legend: bool = True):
    """one panel: what 1, 2 and 3% of GDP buy, economy by economy. The
    budget-curve panel is gone — the three shades already carry the
    convexity, and the per-economy bars are the summary that matters."""
    if ax is None:
        fig, b = plt.subplots(figsize=(183 * MM, 128 * MM))
        fig.subplots_adjust(left=0.145, right=0.985, top=0.925, bottom=0.075)
    else:                            # 2026-10-08: one panel of the build-year figure (fig5_years)
        fig, b = ax.figure, ax

    # three bands, each sorted by what 1% of GDP buys: net importers
    # whose budget binds (more GDP would buy more) on top, net
    # importers whose screened land ceiling is reached within the 3%
    # budget in the middle, and the net exporters of the bill
    # (no net imports, no tick) at the bottom
    # 2026-09-25: four bands. An economy whose 3% budget
    # already covers its imported share is bound by neither money nor
    # land (Australia and Chile used to sit in the land band only because
    # they reach 100% of demand, which is not a land ceiling). Land binds
    # only where the ceiling is below full demand and is reached within
    # 3% of GDP. "Covered" means 3% of GDP, spent on imported fuels first
    # (the security-optimal allocation), retires all net imports: the
    # cheapest-first fill can reach the imported SHARE while buying the
    # wrong family (Indonesia imports oil, its cheapest cells make gas).
    is_x = d.import_pct <= 0.0
    covered = ~is_x & (d.ret_sf_3 >= 0.995)
    land = ~is_x & ~covered & (d.cov_3 >= d.max_cov - 1e-6) & (d.max_cov < 1 - 1e-6)
    budget = ~is_x & ~covered & ~land
    ex, div = [], []
    for g in (d[is_x], d[land], d[budget], d[covered]):
        ex += list(g.sort_values("cov_1").index)
        div.append(len(ex))
    NZ, NL, NB = div[0], div[1], div[2]
    ys = np.arange(len(ex))
    # land_style (2026-10-05: "land limit hard to see"):
    #   cap     - pale grey bar with a dark end-cap (until 2026-10-05)
    #   dark    - darker grey bar and a taller black end-cap (chosen 2026-10-05)
    #   outline - an open box from 0 to the ceiling around the blue bars
    #   hatch   - hatched grey bar beyond the blue bars, with the end-cap
    LAND_FC = {"cap": "#E8E8E8", "dark": "#CFD4DA", "outline": "none", "hatch": "#ECEEF0"}[land_style]
    CAP_C, CAP_H, CAP_W = {"cap": ("#5A6570", 0.36, 2.6), "dark": ("#1A1A1A", 0.46, 2.4),
                           "outline": ("#1A1A1A", 0.0, 0.0), "hatch": ("#1A1A1A", 0.46, 2.4)}[land_style]
    if land_style == "hatch":
        # 2026-10-05: categories never by shade alone -> the unused land is hatched
        mpl.rcParams["hatch.color"] = "#7F8A95"
        mpl.rcParams["hatch.linewidth"] = 0.6
    b.barh(ys, d.loc[ex, "max_cov"] * 100, height=0.66, color=LAND_FC,
           hatch="//////" if land_style == "hatch" else None, lw=0,
           zorder=1, label="domestic land ceiling")
    for k, bud in enumerate(sorted(BUDGETS, reverse=True)):
        b.barh(ys, d.loc[ex, f"cov_{bud:.0f}"] * 100, height=0.66,
               color=BCOL[bud], zorder=2 + k,
               label=f"{bud:.0f}% of GDP")
    # 2026-10-05: white seams between the 1, 2 and 3% bands, and the
    # (same day: the band names went back into the legend above)
    c1, c2, c3 = (d.loc[ex, f"cov_{k}"].to_numpy() * 100 for k in (1, 2, 3))
    for lo, hi in ((c1, c2), (c2, c3)):
        m = hi - lo > 0.4
        b.vlines(lo[m], ys[m] - 0.33, ys[m] + 0.33, color="white", lw=0.8, zorder=6)
    # a dark end-cap on every ceiling: where the coloured bar covers
    # the grey exactly (the land-limited band) the grey itself is
    # invisible, so the cap is what shows the bar has hit the wall
    if land_style == "outline":
        b.barh(ys, d.loc[ex, "max_cov"] * 100, height=0.78, fc="none",
               ec="#1A1A1A", lw=0.8, zorder=7)
    else:
        b.vlines(d.loc[ex, "max_cov"] * 100, ys - CAP_H, ys + CAP_H,
                 color=CAP_C, lw=CAP_W, zorder=7)
    # the imported share is NOT a wall like the ceiling: output past it
    # keeps replacing the country's OWN fossil production, it just buys
    # no further security. Drawn as a marker above the bar so the two
    # cannot be confused with each other.
    imp = d.loc[ex, "import_pct"] * 100
    b.vlines(imp[NZ:], ys[NZ:] - 0.46, ys[NZ:] + 0.46, color="#CB181D",
             lw=1.3, zorder=8, label="imported share of the bill")
    b.scatter(imp[NZ:], ys[NZ:] + 0.50, marker="v", s=14, color="#CB181D", lw=0, zorder=9)
    # 2026-10-08 ("the grouping is not obvious"): alternate light bands behind the groups,
    # and the group names horizontal, in bold, right of the plot with a bracket
    spans = [(0, NZ, "Net\nexporters"), (NZ, NL, "Land\nbinds"), (NL, NB, "Budget\nbinds"),
             (NB, len(ex), "Imports\ncovered")]
    for k, (lo, hi, gname) in enumerate(spans):
        if hi <= lo:
            continue
        if k % 2 == 1:
            b.axhspan(lo - 0.5, hi - 0.5, xmin=0, xmax=1, color="#EEF1F4", lw=0, zorder=0)
        b.plot([104.6, 104.6], [lo - 0.35, hi - 0.65], color="#3A4550", lw=0.9,
               clip_on=False, zorder=6, solid_capstyle="butt")
        nm = gname                      # 2026-10-14: every group name on two lines, short groups too
        b.text(105.6, (lo + hi - 1) / 2, nm, fontsize=7, fontweight="bold", color="#3A4550",
               ha="left", va="center", linespacing=1.05, clip_on=False, zorder=6)
    b.set_yticks(ys)
    # three economies have no net-trade record in the EI/OWID or UN layers;
    # their tick is one minus OWID production over UN final use (the
    # "OWID production / UN use" rows of net_dep_jodi_overrides.csv), and
    # they are starred so the reader knows the basis differs
    GROSS = {"Kenya", "Dominican Republic", "Madagascar"}
    b.set_yticklabels([SHORT.get(c, c)
                       + ("*" if c in GROSS else "") for c in ex],
                      fontsize=8)
    b.set_xlim(0, 104)
    b.set_xticks(np.arange(0, 101, 20))
    b.set_xlabel("Share of fuel demand made at home (%)")
    b.annotate("* no net-trade record: the tick is one minus domestic "
               "production over consumption",
               xy=(0.0, -0.105), xycoords="axes fraction", fontsize=6,
               color="#5A6570", ha="left", va="top", annotation_clip=False)
    import matplotlib.patches as mp
    from matplotlib.legend_handler import HandlerTuple
    from matplotlib.lines import Line2D
    from matplotlib.legend_handler import HandlerBase

    class _TickTriangle(HandlerBase):
        """legend key drawn as in the plot: a red vertical tick with a triangle on top"""
        def create_artists(self, legend, orig, x0, y0, w, h, fs, trans):
            xc = x0 + w / 2
            ln = Line2D([xc, xc], [y0 - 0.15 * h, y0 + 0.85 * h], color="#CB181D", lw=1.3, transform=trans)
            tri = Line2D([xc], [y0 + 1.05 * h], marker="v", ms=4.5, color="#CB181D", ls="none",
                         transform=trans)
            return [ln, tri]

    class _Cap(HandlerBase):
        """legend key for the land ceiling: the black end-cap only"""
        def create_artists(self, legend, orig, x0, y0, w, h, fs, trans):
            xc = x0 + w / 2
            return [Line2D([xc, xc], [y0 - 0.25 * h, y0 + 1.1 * h], color=CAP_C, lw=CAP_W,
                           solid_capstyle="butt", transform=trans)]

    imp_key, cap_key = object(), object()
    handles = [mp.Patch(color=BCOL[1.0]), mp.Patch(color=BCOL[2.0]), mp.Patch(color=BCOL[3.0])]
    labels = ["1% GDP", "2% GDP", "3% GDP"]
    if land_style == "hatch":
        handles.append(mp.Patch(fc=LAND_FC, hatch="//////", lw=0))
        labels.append("unused land")
    handles += [cap_key, imp_key]
    labels += ["land ceiling", "imported share"]
    if legend:
        b.legend(handles=handles, labels=labels,
                 handler_map={imp_key: _TickTriangle(), cap_key: _Cap()},
                 fontsize=8, frameon=False, loc="lower left",
                 bbox_to_anchor=(-0.01, 1.005), ncol=len(handles), handlelength=1.1,
                 columnspacing=1.0, borderaxespad=0.0)
    for s in ("top", "right"):
        b.spines[s].set_visible(False)
    b.grid(axis="x", alpha=0.20, lw=0.4)
    b.set_axisbelow(True)
    if ax is not None:
        return b

    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.png", dpi=600,
                bbox_inches="tight")
    plt.close(fig)
    print("saved fig_security_budget.(pdf|png), security_budget.csv, "
          "tab_budget.tex")


def _figure_co2(d: pd.DataFrame, curves: dict, ax=None, save: bool = True,
                legend: bool = True, bands=("net importers", "net\nexporters"),
                xlim=(-1500.0, 1300.0), xstep=500):
    """The climate co-benefit of a security build, on ONE number line.

    Every economy carries two numbers for the same tonne of CO2: what
    it costs when the whole premium is charged to carbon (hollow), and
    what it costs once the security loss the same build retires is
    netted off (filled). The distance between them IS the security
    dividend; the sign of the filled point is the whole verdict, so
    the reader no longer has to reconcile a bar length with a band
    colour. The carbon price in force is on the same axis, which is
    the point: it is nowhere near either number.

    With ``ax`` the panel is drawn into a caller's axes (the composite
    Figure 5, fig_main_carbon.py) and the legend handles are returned.
    """
    if ax is None:
        fig, b = plt.subplots(figsize=(183 * MM, 128 * MM))
        fig.subplots_adjust(left=0.145, right=0.985, top=0.905, bottom=0.09)
    else:
        b, fig = ax, ax.figure

    net = d.abate_net_hi_1.replace([np.inf, -np.inf], np.nan)
    is_x = d.import_pct <= 0.0                    # no dividend to net off
    imp = d[~is_x].index.to_list()
    imp.sort(key=lambda c: -net.get(c, np.nan))   # most negative on top
    exp = list(d[is_x].sort_values("abate_cost_1", ascending=False).index)
    ex = exp + imp                                # drawn bottom -> top
    NX = len(exp)
    ys = np.arange(len(ex))

    XLO, XHI = xlim
    GREEN, BLUE, GREY = "#009E73", "#0B4F9E", "#8A94A0"
    # the zero line stops at the last data row: extended to the top it
    # cut straight through the worked reading row above
    b.plot([0, 0], [-0.9, len(ex) - 0.42], color="#9AA3AC", lw=1.0,
           zorder=1, solid_capstyle="butt")
    from matplotlib import patheffects as pe
    HALO = [pe.withStroke(linewidth=2.0, foreground="white")]

    # marker positions per row, pinned like the plot, so an off-scale
    # tag can be put on the side of its row where nothing is drawn
    _pos = {}
    for _i, _c in enumerate(ex):
        _xs = [float(d.abate_cost_1.get(_c, np.nan)), float(net.get(_c, np.nan))]
        _pos[_i] = [min(max(_x, XLO + 40), XHI - 40) for _x in _xs if np.isfinite(_x)]

    def _tag(x, y, val, colour, side):
        """print an off-scale value beside the marker that stands in
        for it, so a row that runs past the axis is never blank; the
        tag goes above the row unless a marker in the row above sits
        near it, then below"""
        tx = x + (45 if side > 0 else -45)
        near = lambda r: any(abs(px - tx) < 320 for px in _pos.get(r, []))
        dy = 0.46 if not near(y + 1) else (-0.46 if not near(y - 1) else 0.46)
        b.text(tx, y + dy, f"{val:,.0f}",
               fontsize=6.2, ha="left" if side > 0 else "right",
               va="center", color=colour, zorder=9, path_effects=HALO)

    for i, c in enumerate(ex):
        g = float(d.abate_cost_1.get(c, np.nan))
        v = float(net.get(c, np.nan))
        # both ends are pinned inside the axis: a marker drawn outside
        # it is clipped away and the row reads as missing data
        gg = min(max(g, XLO + 40), XHI - 40) if np.isfinite(g) else g
        if np.isfinite(v):
            vv = min(max(v, XLO + 40), XHI - 40)
            b.plot([vv, gg], [i, i], color="#C9CFD6", lw=2.2, zorder=2,
                   solid_capstyle="round")
            b.scatter([gg], [i], s=26, facecolor="white", zorder=5,
                      edgecolor="#5A6570", linewidths=1.0)
            same = abs(g - v) < 25.0        # closer than the symbol
            b.scatter([vv], [i], s=34, zorder=6,
                      linewidths=1.0 if same else 0,
                      edgecolor="#5A6570" if same else "none",
                      color=GREEN if v <= 0 else BLUE)
            if v < XLO + 40:                      # Ireland runs off scale
                _tag(vv, i, v, GREEN, +1)
            elif v > XHI - 40:                    # Israel runs off scale
                _tag(vv, i, v, BLUE, -1)
            elif g > XHI - 40:
                _tag(gg, i, g, "#5A6570", -1)
        elif np.isfinite(g):
            b.scatter([gg], [i], s=26, facecolor="white", zorder=5,
                      edgecolor=GREY, linewidths=1.0)
            if g > XHI - 40:
                _tag(gg, i, g, "#5A6570", -1)
    pc = d.loc[ex, "p_co2_usd_t"].fillna(0.0).to_numpy()
    b.vlines(pc, ys - 0.34, ys + 0.34, color="#B4116F", lw=1.2, zorder=7)

    b.set_yticks(ys)
    b.set_yticklabels([SHORT.get(c, c)
                       for c in ex], fontsize=8)
    b.plot([XLO, XHI], [NX - 0.5, NX - 0.5], color="#8A94A0", lw=0.7,
           ls=(0, (5, 3)), zorder=3)
    b.text(XHI * 0.995, NX + (len(ex) - NX) / 2 - 0.5, bands[0],
           fontsize=7, color="#5A6570", rotation=90, ha="right",
           va="center", zorder=6)
    b.text(XHI * 0.995, NX / 2 - 0.5, bands[1], fontsize=7,
           color="#5A6570", rotation=90, ha="right", va="center",
           linespacing=1.15, zorder=6)
    # the move itself is explained in the legend (grey segment = security
    # value per tonne); no in-plot annotation, so nothing can collide
    b.set_xlim(XLO, XHI)
    b.set_ylim(-0.9, len(ex) - 0.3)
    b.set_xticks(np.arange(np.ceil(XLO / xstep) * xstep, XHI + 1, xstep))
    b.set_xlabel("US\\$ per tonne of CO$_2$ displaced")

    from matplotlib.lines import Line2D
    handles = [
        Line2D([], [], marker="o", ls="none", ms=6, mfc="white",
               mec="#5A6570", label="Normal benchmark"),
        Line2D([], [], color="#C9CFD6", lw=2.2,
               label="Security margin"),
        Line2D([], [], marker="|", ls="none", ms=10, mew=1.2,
               color="#B4116F", label="Carbon price in force"),
        Line2D([], [], marker="o", ls="none", ms=6.5, color=GREEN,
               label="Security covers the premium"),
        Line2D([], [], marker="o", ls="none", ms=6.5, color=BLUE,
               label="Gap remains")]
    if legend:
        b.legend(handles=handles,
                 fontsize=8, frameon=False, loc="lower left",
                 bbox_to_anchor=(-0.01, 1.005), ncol=2, handlelength=1.4,
                 columnspacing=1.1, borderaxespad=0.0)
    for s in ("top", "right"):
        b.spines[s].set_visible(False)
    b.grid(axis="x", alpha=0.20, lw=0.4)
    b.set_axisbelow(True)
    if not save:
        return dict(handles=handles, order=ex, NX=NX)

    fig.savefig(OUT / "fig_emission_budget.pdf", bbox_inches="tight")
    fig.savefig(OUT / "fig_emission_budget.png", dpi=600,
                bbox_inches="tight")
    plt.close(fig)
    fin = net.dropna()
    print(f"saved fig_emission_budget.(pdf|png) — gross vs net per tonne; "
          f"net<=0 in {(fin <= 0).sum()} of {len(fin)} importers, "
          f"median gross {d.abate_cost_1.median():.0f}, median net "
          f"{fin.median():.0f} $/t")


if __name__ == "__main__":
    main()
