"""
demand_grid.py — gridded fuel-demand proxy and the plant recommendation.

No global gridded FINAL-ENERGY-demand product exists at 2.5 deg, so we use
the standard proxy: sectoral CO2 emissions (EDGAR 2026 release, 0.1 deg,
year 2025, tonne / cell / yr) aggregated onto the LCOS grid. For industry,
buildings, road and aviation that proxy sets only WHERE demand sits inside a
country; HOW MUCH each country burns is its reported fossil fuel use: the UN
Energy Statistics Database gives the 2023 level split into gas, oil and coal
(un_energy.py), and each part is grown to 2025 with the country's Energy
Institute growth for that fuel (ei_energy.py). Dividing mixed-fuel CO2 by
one emission factor overstated industrial fuel use by about a third.  Where fossil CO2 is
emitted today is where a drop-in synthetic fuel would be burned tomorrow —
the same logic Climate TRACE uses for its asset inventory (their gridded
product is request-only; EDGAR is the open equivalent).

Sector -> fuel mapping (demand shares, not volumes), applied AFTER the
ADDRESSABLE electrification discount below:
  e-kerosene   aviation, anchored at airports (LTO + climb/descent, scaled
               up by the global cruise multiplier — fuel is uplifted at
               airports, not over flyover corridors)
  e-diesel     road transport x 0.8 (of the addressable road fuel) + the OIL
               part of buildings and industrial combustion (heating oil,
               LPG, fuel oil: drop-in for Fischer-Tropsch liquids)
  ethanol      road transport x 0.2       (of the addressable road fuel)
  e-methane    the GAS part of buildings (RCO) + industrial combustion
               (IND); power excluded — the gas-substitution market.
               Coal in those sectors is not mapped: the paper's addressable
               bill is oil and gas, not coal. Each country's gas/oil/coal
               composition is its UN 2023 sector fuel use grown to 2025 with
               the anchor's own arithmetic, so e-methane is a share of gas
               use by construction and needs no cap (the former 50%-of-gas
               cap, which removed coal after the fact, went on 2026-09-13)
  methanol     chemicals (methanol's share of chemical usage) + shipping x 0.7
  ammonia      chemicals (ammonia's share, fertiliser ammonia included)
               + shipping x 0.3
Shipping is split 70/30 methanol/ammonia (current dual-fuel orderbook, DNV
Maritime Forecast); the chemicals slice is divided between the two big
H2-consuming chemicals in proportion to their world usage.  Hydrogen itself is the base fuel everywhere and is scored
separately in the paper — the recommendation map is the NON-H2 layer.

Recommendation score per cell c and fuel f:
  S_f(c) = demand_share_f(c) * competitiveness_f(c),
  competitiveness_f = min_g medLCOF_g(c) / medLCOF_f(c)  in (0, 1],
median over the 20 weather years.  top1/top2 = argmax S.  Cells whose total
proxy demand is < SPARSE_KT are flagged sparse (export-oriented site — the
local-demand recommendation is not meaningful there).

From scripts/:  conda run -n synfuel python -u -m lcof.demand_grid
Outputs: data/cost/demand_fuel_grid.csv, data/cost/fuel_recommendation.csv
"""
from __future__ import annotations

import zipfile
import numpy as np
import pandas as pd
import xarray as xr

from . import inputs

EDGAR = inputs.PROJECT / "data" / "demand" / "edgar_2026"
EDGAR_RELEASE = "EDGAR_2026_GHG"
# the latest year of the release, and the UN base year its growth is taken
# from; EDGAR's latest year is a fast-track extension of the base-year map
EDGAR_YEAR, EDGAR_BASE_YEAR = 2025, 2023
OUTD = inputs.MAPS

SECTORS = ["ENE", "IND", "TRO", "TNR_Ship", "TNR_Aviation_CDS",
           "TNR_Aviation_CRS", "TNR_Aviation_LTO", "RCO", "CHE", "AGS"]

# world usage of the two H2-consuming chemicals, which sizes the chemicals
# slice (production equals use for a traded commodity over a year):
#   ammonia  USGS Mineral Commodity Summaries 2026: 160,000 kt N in 2025
#            (estimated) x 17/14 = 194.3 Mt NH3, at 18.6 GJ/t LHV
#   methanol about 110 Mt, industry estimate (Methanol Institute /
#            MMSA), at 20 GJ/t LHV
NH3_MT, NH3_GJ_PER_T = 160.0 * 17.0 / 14.0, 18.6
MEOH_MT, MEOH_GJ_PER_T = 110.0, 20.0
CHE_TARGET_GJ = (NH3_MT * NH3_GJ_PER_T + MEOH_MT * MEOH_GJ_PER_T) * 1e6
NH3_SHARE = NH3_MT * NH3_GJ_PER_T * 1e6 / CHE_TARGET_GJ
MEOH_SHARE = 1.0 - NH3_SHARE

# the stationary sectors are mapped fuel by fuel: a weight given as a fuel
# group name below means that group's share of the sector in each country
# (its anchored 2025 composition, see _anchor_to_reported)
FUEL_GROUPS = ("GAS", "OIL", "COAL")
STATIONARY = ("IND", "RCO")

FUEL_MAP = {
    # aviation anchored at AIRPORTS (LTO + climb/descent); cruise fuel is
    # uplifted there too, so build() scales these two up by the global
    # cruise multiplier instead of crediting flyover corridors
    "e-kerosene": {"TNR_Aviation_LTO": 1.0, "TNR_Aviation_CDS": 1.0},
    # heavy / long-haul road, plus the oil burned in buildings and industry
    # (heating oil, LPG, fuel oil), which Fischer-Tropsch liquids replace
    # drop-in
    "e-diesel":   {"TRO": 0.8, "IND": "OIL", "RCO": "OIL"},
    "ethanol":    {"TRO": 0.2},
    # power (ENE) is NOT in this map. Making a fuel from electricity and
    # burning it back for electricity is a round trip at about 28% (65%
    # electrolysis x 78% methanation x 55% turbine), against 36% for the
    # same round trip through hydrogen, and e-methane alone also pays
    # for the carbon feed. The one case that survives is long-duration
    # storage, where the alternative is not a battery; that case needs a
    # grid and dispatch model, which this paper does not build, so the
    # power sector is left out of the addressable market rather than
    # carried on an assumption we cannot support.
    # Coal burned in buildings and industry is in no fuel's map: the
    # addressable bill is oil and gas.
    "e-methane":  {"RCO": "GAS", "IND": "GAS"},
    # chemicals split by the two big H2-consuming chemicals' world usage
    "methanol":   {"CHE": MEOH_SHARE},
    # ammonia is counted once, in the chemicals slice: world ammonia
    # usage already includes the ~70-90% that becomes fertiliser, so the
    # agricultural-soils (urea application) field is no longer added.
    # 2026-10-07: placed by national apparent consumption in build(), not by
    # the chemical-sector CO2 field (see ammonia_consumption.py)
    "ammonia":    {"CHE": NH3_SHARE},
    # 2026-10-07: shipping is its own market. Its synthetic fuel is e-methanol
    # and e-ammonia, 70/30 (current dual-fuel orderbook, DNV), but what it
    # replaces is marine fuel oil, so it is priced and credited against fuel oil
    # (params.FUELS["marine"], policy.FOSSIL["marine"])
    "marine":     {"TNR_Ship": 1.0},
}
SPARSE_KT = 100.0               # kt CO2/yr addressable — below this the cell is an export site, not a local market

# fraction of each sector's demand that is realistically addressable by a
# SYNTHETIC fuel rather than by direct electrification (IEA/IRENA
# hard-to-abate logic): buildings only hard-to-retrofit gas heat, industry
# only high-temperature heat, road the part of its fuel not electrified in
# the near term, across all vehicle classes (FUEL_MAP then gives 80% of it
# to e-diesel and 20% to ethanol); aviation,
# shipping, chemicals and fertiliser in full. Power is zero, for the
# round-trip reason given at the fuel map above.
ADDRESSABLE = {"ENE": 0.00, "RCO": 0.20, "IND": 0.40, "TRO": 0.30,
               "TNR_Ship": 1.0, "TNR_Aviation_LTO": 1.0,
               "TNR_Aviation_CDS": 1.0, "TNR_Aviation_CRS": 1.0,
               "CHE": 1.0, "AGS": 1.0}


def _sector_to_grid(sector: str, meta: pd.DataFrame,
                    year: int = EDGAR_YEAR) -> pd.Series:
    """EDGAR 0.1-deg field summed into the 2.5-deg LCOS cells (t CO2/yr)."""
    nc = EDGAR / f"{EDGAR_RELEASE}_CO2_{year}_{sector}_emi.nc"
    if not nc.exists():
        zp = EDGAR / f"{EDGAR_RELEASE}_CO2_{year}_{sector}_emi_nc.zip"
        with zipfile.ZipFile(zp) as z:
            for n in z.namelist():
                if n.endswith(".nc"):
                    z.extract(n, EDGAR)
                    if EDGAR / n != nc:
                        (EDGAR / n).replace(nc)
    ds = xr.open_dataset(nc)
    e = ds["emissions"].values          # (1800, 3600), t / 0.1deg cell / yr
    lat = ds["lat"].values
    lon = ds["lon"].values
    ds.close()

    ilat = np.floor((lat + 63.75) / 2.5).astype(int)      # 60 rows of cells
    ilon = np.floor((lon + 181.25) / 2.5).astype(int) % 144
    ok = (ilat >= 0) & (ilat < 60)

    acc = np.zeros((60, 144))
    np.add.at(acc, (ilat[ok][:, None].repeat(3600, 1),
                    np.broadcast_to(ilon, (ok.sum(), 3600))),
              e[ok, :])

    ci = np.floor((meta.lat.values + 63.75) / 2.5).astype(int)
    cj = np.floor((meta.lon.values + 181.25) / 2.5).astype(int) % 144
    out = pd.Series(acc[ci, cj], index=meta.index, name=sector)
    # a 2.5-deg box maps to exactly one cell_id, so this is a partition
    return out


# sectors whose national LEVEL is taken from UN statistics; the value is
# the EDGAR fields that carry each one on the grid
UN_ANCHOR = {"IND": ["IND"], "RCO": ["RCO"], "TRO": ["TRO"],
             "AVIATION": ["TNR_Aviation_LTO", "TNR_Aviation_CDS"]}


def _anchor_to_reported(sec: pd.DataFrame, base: pd.DataFrame,
                        meta: pd.DataFrame) -> pd.DataFrame:
    """Rescale each anchored sector, country by country, so its energy
    (CO2 / emission factor) equals the country's reported fossil fuel use in
    EDGAR_YEAR. The UN base year gives that use split into gas, oil and coal;
    each part grows to EDGAR_YEAR with the country's Energy Institute growth
    for the same fuel, or with EDGAR's own growth of the sector between
    EDGAR_BASE_YEAR and EDGAR_YEAR (same release) where the Energy Institute
    names no figure. Cells keep their share of the national total. A country
    with no UN figure, or no EDGAR emissions to spread it over, keeps its
    EDGAR level. Aviation is anchored after the cruise uplift, against
    domestic plus international bunkers, both uplifted at its airports.

    Returns the rescaled sectors and, for the STATIONARY sectors, each
    anchored country's 2025 fuel composition (shares of gas, oil and coal in
    that level), which build() uses to map those sectors fuel by fuel."""
    from .un_energy import sector_fuel_levels
    from .ei_energy import growth
    lev = sector_fuel_levels()
    names = sorted(meta.country.dropna().unique())
    gro = growth(names)
    country = meta.country.reindex(sec.index)
    comp = {}
    for g, cols in UN_ANCHOR.items():
        e_now = sum(sec[c] / EF[c] for c in cols).groupby(country).sum()
        e_base = sum(base[c] / EF[c] for c in cols).groupby(country).sum()
        target, shares, base_gj, ei_gj = {}, {}, 0.0, 0.0
        for c in names:
            if c not in lev.index or not e_now.get(c, 0) > 0:
                continue
            parts = lev.loc[c, g]
            if not np.isfinite(parts.to_numpy(float)).any():
                continue
            edg = e_now[c] / e_base[c] if e_base.get(c, 0) > 0 else 1.0
            lv = {}
            for grp, v in parts.items():
                if not np.isfinite(v) or v <= 0:
                    continue
                r = gro.at[c, grp] if c in gro.index else np.nan
                if np.isfinite(r):
                    ei_gj += v
                else:
                    r = edg
                lv[grp] = v * r
            t_c = sum(lv.values())
            if t_c > 0:
                target[c] = t_c
                shares[c] = {k: lv.get(k, 0.0) / t_c for k in FUEL_GROUPS}
                base_gj += float(np.nansum(parts.to_numpy(float)))
        k = pd.Series(target) / e_now.reindex(list(target))
        kc = country.map(k).fillna(1.0)
        before = e_now.sum() / 1e9
        for c in cols:
            sec[c] = sec[c] * kc
        after = sum(sec[c] / EF[c] for c in cols).sum() / 1e9
        print(f"reported level for {g:8s}: EDGAR {before:6.1f} -> {after:6.1f} EJ "
              f"({len(k)} countries; UN base {base_gj / 1e9:.1f} EJ, "
              f"Energy Institute growth on {100 * ei_gj / max(base_gj, 1):.0f}%)")
        if g in STATIONARY:
            comp[g] = pd.DataFrame(shares).T.reindex(columns=list(FUEL_GROUPS))
    return sec, comp


def _stationary_shares(comp: dict, gj: pd.DataFrame,
                       meta: pd.DataFrame) -> dict:
    """Per-cell share of each fuel group in each STATIONARY sector: the
    cell's country's anchored composition. A country the UN does not split
    (Taiwan, mostly: under 1% of either sector's demand) gets the
    demand-weighted average composition of the anchored countries."""
    country = meta.country.reindex(gj.index)
    out = {}
    for g, tab in comp.items():
        w = gj[g].groupby(country).sum().reindex(tab.index)
        avg = tab.mul(w, axis=0).sum() / w.sum()
        fb = gj[g][~country.isin(tab.index)].sum() / gj[g].sum()
        print(f"{g}: fuel composition from UN statistics for {len(tab)} countries "
              f"(demand-weighted gas {avg.GAS:.2f}, oil {avg.OIL:.2f}, coal "
              f"{avg.COAL:.2f}); world average used for {100 * fb:.1f}% of "
              f"the sector's demand")
        out[g] = {k: country.map(tab[k]).fillna(avg[k]) for k in FUEL_GROUPS}
    return out


def build() -> pd.DataFrame:
    meta = inputs.load_meta(2025)
    sec = pd.DataFrame({s: _sector_to_grid(s, meta, EDGAR_YEAR)
                        for s in SECTORS})
    base = pd.DataFrame({s: _sector_to_grid(s, meta, EDGAR_BASE_YEAR)
                         for s in SECTORS})

    # cruise fuel is uplifted at airports: scale airport-anchored aviation
    # up so total aviation demand is conserved
    apt = sec.TNR_Aviation_LTO.sum() + sec.TNR_Aviation_CDS.sum()
    av_scale = (apt + sec.TNR_Aviation_CRS.sum()) / apt
    sec = sec.assign(TNR_Aviation_LTO=sec.TNR_Aviation_LTO * av_scale,
                     TNR_Aviation_CDS=sec.TNR_Aviation_CDS * av_scale)
    print(f"aviation cruise multiplier applied at airports: {av_scale:.2f}")
    apt0 = base.TNR_Aviation_LTO.sum() + base.TNR_Aviation_CDS.sum()
    k0 = (apt0 + base.TNR_Aviation_CRS.sum()) / apt0
    base = base.assign(TNR_Aviation_LTO=base.TNR_Aviation_LTO * k0,
                       TNR_Aviation_CDS=base.TNR_Aviation_CDS * k0)
    sec, comp = _anchor_to_reported(sec, base, meta)

    adr = sec * pd.Series(ADDRESSABLE)
    gj = adr / pd.Series(EF)          # displaced service energy, GJ/yr
    share = _stationary_shares(comp, gj, meta)

    def wt(s, w):
        # a fuel-group name means that group's share of the sector, per cell
        return share[s][w] if isinstance(w, str) else w

    # -- reconciliation with observed consumption (verified 2026-08) --
    # 1. CHE covers ALL chemicals; NH3+MeOH are the H2-relevant slice.
    #    Global calibration so CHE-derived NH3+MeOH energy matches
    #    world usage (NH3_MT x NH3_GJ_PER_T + MEOH_MT x MEOH_GJ_PER_T,
    #    see the constants above FUEL_MAP):
    che_derived = gj.CHE.sum()        # the whole chemicals field
    CHE_SCALE = CHE_TARGET_GJ / che_derived if che_derived > 0 else 1.0
    gj = gj.assign(CHE=gj.CHE * CHE_SCALE)
    print(f"CHE calibrated to NH3+MeOH production stats: x{CHE_SCALE:.2f}")

    fuel = pd.DataFrame({f: sum(adr[s] * wt(s, w) for s, w in m.items())
                         for f, m in FUEL_MAP.items()})
    fuel["total_tco2"] = fuel.sum(axis=1)
    for f, m in FUEL_MAP.items():
        fuel[f + "_gj"] = sum(gj[s] * wt(s, w) for s, w in m.items())
    # 2026-10-07: ammonia by national apparent consumption (USGS production +
    # UN Comtrade net imports, ammonia_consumption.py), spread over each
    # country's cells by its chemical-sector field, else its industry field,
    # else its total addressable demand
    nh3 = pd.read_csv(OUTD / "ammonia_consumption.csv", index_col=0).consumption_t * NH3_GJ_PER_T
    ctry = meta.country.reindex(fuel.index)
    w = pd.DataFrame({"che": gj.CHE.reindex(fuel.index).fillna(0.0),
                      "ind": gj.IND.reindex(fuel.index).fillna(0.0),
                      "tot": fuel[[f + "_gj" for f in FUEL_MAP]].sum(axis=1)})
    new = pd.Series(0.0, index=fuel.index)
    lost = 0.0
    for c, q in nh3.items():
        if q <= 0:
            continue
        cells = ctry.index[ctry == c]
        if not len(cells):
            lost += q
            continue
        for k in ("che", "ind", "tot"):
            wc = w.loc[cells, k]
            if wc.sum() > 0:
                new.loc[cells] = q * wc / wc.sum()
                break
    fuel["ammonia_gj"] = new
    fuel["ammonia"] = new * EF["CHE"]
    fuel["total_tco2"] = fuel[list(FUEL_MAP)].sum(axis=1)
    print(f"ammonia by apparent consumption: {new.sum() / NH3_GJ_PER_T / 1e6:.1f} Mt on the grid, "
          f"{lost / NH3_GJ_PER_T / 1e6:.2f} Mt in economies without land cells")
    stat = {k: sum(gj[g] * share[g][k] for g in STATIONARY).sum() / 1e9
            for k in FUEL_GROUPS}
    print(f"stationary addressable demand: gas {stat['GAS']:.1f} EJ -> e-methane, "
          f"oil {stat['OIL']:.1f} EJ -> e-diesel, coal {stat['COAL']:.1f} EJ "
          f"not mapped (the addressable bill is oil and gas)")

    # 2. Gas substitution is a share of gas use by construction (0.40 of
    #    industry's and 0.20 of buildings' gas at the UN level), so check it
    #    against the independent national gas total: Energy Institute 2025
    #    where it names the country, the latest OWID year otherwise. The
    #    former 50%-of-gas cap on e-methane, which removed the coal that the
    #    all-fuel mapping had let in, is not needed and was dropped
    #    (2026-09-13); the ratio it capped is now an audit.
    from .ei_energy import by_country, LATEST_YEAR
    owid = pd.read_csv(inputs.MAPS / "demand_by_fuel.csv")
    gas_c = owid.sort_values("year").groupby("country").last().gas_gj
    ei_gas = by_country(sorted(meta.country.dropna().unique()))[
        f"GAS_{LATEST_YEAR}"]
    gas_c = ei_gas.dropna().combine_first(gas_c)
    em_c = fuel.join(meta[["country"]]).groupby("country")[
        "e-methane_gj"].sum()
    ratio = (em_c / gas_c).dropna()
    print(f"e-methane / national gas use: median {ratio.median():.2f}, "
          f"max {ratio.max():.2f} ({ratio.idxmax()}); "
          f"global e-methane {fuel['e-methane_gj'].sum() / 1e9:.1f} EJ")
    assert ratio.max() < 0.5, "e-methane exceeds the gas it can address"

    # ---- audit ------------------------------------------------------------
    glob = sec.sum() / 1e9        # Gt
    print(f"captured on the cell grid, Gt CO2 ({EDGAR_YEAR}):")
    for s in SECTORS:
        print(f"  {s:18s} {glob[s]:7.2f}")
    assert 12.0 < glob["ENE"] < 16.0, "power total implausible"
    assert 5.0 < glob["TRO"] < 7.5, "road total implausible"
    land_share = fuel.loc[meta.cell_type == "land", "total_tco2"].sum() \
        / fuel.total_tco2.sum()
    print(f"share of captured demand on land cells: {land_share:.1%}")
    assert land_share > 0.85
    # reconciliation audits: global addressable totals vs observed stats
    tot_ej = {f: fuel[f + "_gj"].sum() / 1e9 for f in FUEL_MAP}
    print("addressable demand, EJ:", {k: round(v, 1)
                                      for k, v in tot_ej.items()})
    assert 8 <= tot_ej["e-kerosene"] <= 15, "aviation vs ~11-14 EJ jet"
    assert 3.3 <= tot_ej["ammonia"] <= 3.7, "ammonia vs its world usage (3.6 EJ)"
    assert 6 <= tot_ej["marine"] <= 12, "shipping vs ~9-11 EJ of bunker fuel"
    assert tot_ej["e-methane"] <= 75, "gas substitution vs ~140 EJ gas"
    print("ALL CHECKS PASSED (demand grid)")

    fuel.round(1).to_csv(OUTD / "demand_fuel_grid.csv")
    return fuel


# which fossil service each synthetic fuel replaces — gas-based fuels
# hedge gas imports, oil-based fuels hedge oil imports (M_F multipliers
# and CoDF from the security ledger, security.py)
SVC = {"e-methane": "gas", "methanol": "gas", "ammonia": "gas",
       "e-diesel": "oil", "e-kerosene": "oil", "ethanol": "oil", "marine": "oil"}
M_F = {"gas": 1.0, "oil": 1.3}

# displaced-service emission factors, t CO2 per GJ (IPCC 2006 defaults):
# gas 56.1 kg/GJ, diesel 74.1, jet kerosene 71.5, residual fuel oil 77.4;
# fertiliser via the SMR route: 1.9 t CO2/t NH3 over 18.6 GJ/t = 102 kg/GJ
EF = {"ENE": 0.0561, "RCO": 0.0561, "IND": 0.0561, "CHE": 0.0561,
      "TRO": 0.0741, "TNR_Aviation_LTO": 0.0715,
      "TNR_Aviation_CDS": 0.0715, "TNR_Aviation_CRS": 0.0715,
      "TNR_Ship": 0.0774, "AGS": 0.1022}

Q_MIN_GJ = 2e6          # 2 PJ/yr — one bankable first-of-a-kind plant
DISC = 0.05             # planner's real discount rate
VYEARS = np.arange(2025, 2051)


def _decline(fuels):
    """global per-fuel LCOF decline path g_f(t), t = 2025..2050, from the
    build-year (vintage) runs: Moderate case, persistent CO2 axis, median
    ratio across the 29 case sites (site IQR is +-0.02-0.04)."""
    v = pd.read_csv(OUTD / "vintage_fuels.csv")
    c = v[(v.case == "Moderate") & (v.co2_axis == "persist")]
    grid = sorted(c.vintage.unique())
    base = c[c.vintage == grid[0]].set_index(["site", "fuel"]
                                             ).lcof_med_usd_gj
    g = {}
    for f in fuels:
        r = [float((c[c.vintage == y].set_index(["site", "fuel"])
                    .lcof_med_usd_gj / base).xs(f, level="fuel").median())
             for y in grid]
        g[f] = np.interp(VYEARS, grid, r)
    return g


def _comparators(countries, fuels):
    """median fossil comparator price B_f by (country, fuel), $/GJ, over
    the observed 247-month distribution; global median as fallback."""
    from .gap import country_gas_monthly, fossil_for_fuel
    gasdf, gg = country_gas_monthly()
    B = pd.DataFrame(index=pd.Index(countries, name="country"),
                     columns=fuels, dtype=float)
    for c in countries:
        if c not in gasdf.columns:
            continue
        for f in fuels:
            s = fossil_for_fuel(f, gasdf[c], gg, c).dropna()
            if len(s):
                B.loc[c, f] = float(s.median())
    return B.fillna(B.median())


def recommend(fuel: pd.DataFrame | None = None) -> pd.DataFrame:
    """the planner's problem, per cell c (see RECO_METHOD.md):

      choose f maximising the discounted net value of one plant program,
        Omega_f(c) = D_f(c) * sum_t (1+DISC)^-(t-2025)
                              * max(B_f(c) + sigma_f(c) - LCOF_f(c,t), 0)
      s.t. market depth D_f(c) >= Q_MIN_GJ,
      LCOF_f(c,t) = medLCOF_f(c) * g_f(t)  (vintage decline path),
      B_f = median observed fossil comparator (247 months, held fixed —
      no price forecast), sigma_f = the ledger's security credit
      q_eff * CoDF * m_f * dep (0 / ACER / ENTSOG variants).

    If no eligible fuel clears by 2050, rank by the smallest relative
    cost gap at 2050 (ordinal only). Cells with no eligible fuel are
    export sites. Break-even year t*_f is stored alongside."""
    from .fig_pptx_pairs import cascade_years, load_all
    if fuel is None:
        fuel = pd.read_csv(OUTD / "demand_fuel_grid.csv", index_col=0)
    meta = inputs.load_meta(2025)
    sec = pd.read_csv(OUTD / "security_index.csv", index_col=0)
    meta2, cells2, lcoh2, lcoe2 = load_all()
    fuels = list(FUEL_MAP)
    med = pd.DataFrame(
        {f: np.median(cascade_years(meta2, cells2, lcoh2, lcoe2, f), axis=1)
         for f in fuels}, index=cells2)

    idx = med.index.intersection(fuel.index)
    D = fuel.loc[idx, [f + "_gj" for f in fuels]]
    D.columns = fuels
    elig = D >= Q_MIN_GJ

    gdec = _decline(fuels)
    ctry = meta.loc[idx, "country"]
    B = _comparators(sorted(ctry.dropna().unique()), fuels)
    Bc = pd.DataFrame({f: ctry.map(B[f]) for f in fuels}, index=idx)

    qc = ctry.map(sec.q_eff).fillna(0.0)
    dep = {"gas": ctry.map(sec.dep_gas).fillna(0.0),
           "oil": ctry.map(sec.dep_oil).fillna(0.0)}
    sig = {"": 0.0,
           "_sec": pd.DataFrame({f: qc * ctry.map(sec.codf_usd_gj)
                                 .fillna(0.0) * M_F[SVC[f]] * dep[SVC[f]]
                                 for f in fuels}, index=idx),
           "_hi": pd.DataFrame({f: qc * ctry.map(sec.codf_hi_usd_gj)
                                .fillna(0.0) * M_F[SVC[f]] * dep[SVC[f]]
                                for f in fuels}, index=idx)}

    disc = (1 + DISC) ** -(VYEARS - VYEARS[0])
    rec = pd.DataFrame(index=idx)
    for tag, s in sig.items():
        Bv = Bc + (s if isinstance(s, pd.DataFrame) else 0.0)
        omega = pd.DataFrame(0.0, index=idx, columns=fuels)
        tstar = pd.DataFrame(np.inf, index=idx, columns=fuels)
        gap50 = pd.DataFrame(np.inf, index=idx, columns=fuels)
        for f in fuels:
            lc = np.outer(med.loc[idx, f], gdec[f])       # cells x years
            margin = Bv[f].values[:, None] - lc
            omega[f] = D[f].values * (np.maximum(margin, 0) * disc).sum(1)
            clears = margin > 0
            first = np.argmax(clears, axis=1).astype(float)
            first[~clears.any(axis=1)] = np.nan
            tstar[f] = VYEARS[0] + first
            gap50[f] = lc[:, -1] / Bv[f].values - 1.0
        omega[~elig] = -np.inf
        gap50[~elig] = np.inf
        # primary: largest positive NPV; fallback: smallest 2050 gap
        any_pos = (omega > 0).any(axis=1)
        key = np.where(any_pos.values[:, None], omega.values,
                       -gap50.values)
        ranked = key.argsort(axis=1)[:, ::-1]
        rec[f"top1{tag}"] = [fuels[i] for i in ranked[:, 0]]
        rec[f"top2{tag}"] = [fuels[i] for i in ranked[:, 1]]
        if tag == "":
            t1 = tstar.values[np.arange(len(idx)), ranked[:, 0]]
            rec["tstar1"] = t1
            rec["omega1"] = omega.values[np.arange(len(idx)), ranked[:, 0]]
            rec["omega2"] = omega.values[np.arange(len(idx)), ranked[:, 1]]
            rec["clears"] = any_pos
            omega0, gap0 = omega.copy(), gap50.copy()
    rec["n_eligible"] = elig.sum(axis=1)
    rec["total_pj"] = D.sum(axis=1) / 1e6
    rec["sparse"] = rec.n_eligible == 0
    sp = rec["sparse"]

    print(f"recommendation on {len(rec)} cells; export/no-market "
          f"{sp.mean():.1%}; clears by 2050: "
          f"{rec.loc[~sp, 'clears'].mean():.1%}")
    for tag in ("", "_sec", "_hi"):
        print(f"top-1 mix{tag or ' (market)':9s}:",
              rec.loc[~sp, f"top1{tag}"].value_counts().to_dict())
    flip = (rec.loc[~sp, "top1"] != rec.loc[~sp, "top1_sec"]).mean()
    flip_hi = (rec.loc[~sp, "top1"] != rec.loc[~sp, "top1_hi"]).mean()
    print(f"security flips: ACER {flip:.1%}, ENTSOG {flip_hi:.1%}")
    print("median t* of the winner (clearing cells):",
          float(rec.loc[~sp & rec.clears, "tstar1"].median()))
    # ---- robustness -------------------------------------------------------
    # winner under a doubled bankability threshold, reported as a column —
    # where it differs, the choice is the thin-premium-market vs
    # deep-bulk-market tension, a result rather than noise
    elig2 = D >= 2 * Q_MIN_GJ
    o2 = omega0.mask(~elig2, -np.inf)
    g2 = gap0.mask(~elig2, np.inf)
    anyp2 = (o2 > 0).any(axis=1)
    key2 = np.where(anyp2.values[:, None], o2.values, -g2.values)
    r2 = key2.argsort(axis=1)[:, ::-1]
    rec["top1_q2"] = [fuels[i] for i in r2[:, 0]]
    rec.loc[~elig2.any(axis=1), "top1_q2"] = "none"

    live = rec[~sp]
    alive2 = live.top1_q2 != "none"
    flip_q = (live.top1 != live.top1_q2) & alive2
    cl = live[live.clears & (live.omega2 > 0)]
    rob_d = (cl.omega1 >= cl.omega2 * 4 / 3).mean() if len(cl) else 1.0
    print(f"robustness: Q_MIN x2 sends {(~alive2).mean():.0%} of live "
          f"cells to export status and switches the fuel in "
          f"{flip_q.mean():.1%} (thin premium market -> deep bulk "
          f"market); where two fuels clear, the winner's NPV margin "
          f"exceeds a 25% demand-split perturbation in {rob_d:.0%}")
    assert rob_d > 0.6, "NPV ranking not robust to demand-split weights"
    assert flip_q.mean() < 0.5, "threshold tension dominates the map"
    assert rec.loc[~sp, "top1"].nunique() >= 3, \
        "recommendation map degenerate — one fuel everywhere"
    rec.to_csv(OUTD / "fuel_recommendation.csv")

    # per-fuel evaluation stats for the figure's value table ($/MMBtu)
    MB = 1.055
    stats = []
    for f in fuels:
        won = rec.index[(rec.top1 == f) & ~sp]
        cl = rec.loc[won]
        stats.append({
            "fuel": f, "cells": len(won),
            "lcof_mmbtu": float(med.loc[won, f].median() * MB)
            if len(won) else np.nan,
            "rival_mmbtu": float(Bc.loc[won, f].median() * MB)
            if len(won) else np.nan,
            "tstar_med": float(cl[cl.clears].tstar1.median())
            if cl.clears.any() else np.nan,
            "demand_pj": float(D.loc[won, f].sum() / 1e6)
            if len(won) else 0.0})
    pd.DataFrame(stats).to_csv(OUTD / "fuel_reco_stats.csv", index=False)
    print("saved fuel_recommendation.csv + fuel_reco_stats.csv")
    return rec


if __name__ == "__main__":
    recommend(build())
