"""
security.py — Phase-1 of the unified security ledger (SECURITY_METHOD.md).

Per country:
  CoDF   value of lost fuel service, $/GJ — ACER-calibrated GDP intensity
  SaR    expected unserved fuel energy, GJ/yr — two scenario families
  ESD    expected security damage, $/yr, and ESD/GDP
  ICS    implied cost of security of the domestic hydrogen backstop, $/GJ
         of expected shortfall avoided  ( = Pi / q_eff )
  BCR    CoDF / ICS — >= 1 means the security case alone carries the premium

Scenario set, estimated from the event catalogue (security_events.csv,
2000-2026 window; rate band x/2 to x2, central = geometric mean):
  s1  top-supplier interruption: lose each commodity's top-supplier share,
      median 8 months, about 0.26 events/yr
  s2  systemic import interruption (blockade / chokepoint): all fuel
      imports, median 3.5 months, about 0.15 events/yr
Mitigation v1: IEA strategic stocks — 90 days of the OIL share for members
(the obligation's actual scope); other channels are Phase 2 and their
omission makes ESD an upper bound on the import side.

From scripts/:  conda run -n synfuel python -u -m lcof.security
Writes data/cost/security_index.csv and prints the audit block.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import inputs
from .gap import country_gas_monthly, country_lcof
from .policy import grey_h2_price

# IEA members holding the 90-day net-import oil obligation (the 32 members;
# checked 2026-10-05 against iea.org/about/membership: Brazil, Chile,
# Colombia, Costa Rica, Israel and Romania are accession countries, no credit)
IEA = {"United States of America", "Japan", "Germany", "France", "Italy",
       "United Kingdom", "South Korea", "Spain", "Netherlands", "Belgium",
       "Poland", "Czechia", "Austria", "Switzerland", "Sweden", "Norway",
       "Denmark", "Finland", "Ireland", "Portugal", "Greece", "Hungary",
       "Slovakia", "Turkey", "Australia", "New Zealand", "Canada", "Mexico",
       "Estonia", "Latvia", "Lithuania", "Luxembourg"}

# Scenario families are ESTIMATED from the curated event catalogue
# (data/cost/security_events.csv, 1956-2026, sourced per row), not elicited:
#   s1  supplier-side interruption  = classes {supplier_outage, export_ban}
#   s2  systemic/chokepoint         = class {chokepoint}
# Rate = events/observation-window; duration = catalogue median per family.
# The low/high band spans a factor 2 around the estimated rate, carrying
# the elicitation uncertainty the point estimate cannot.
# Window (2026-09-25, author's choice B): rate AND duration are both
# estimated from the events of 2000-2026, the current risk regime (the 2021
# gas squeeze, the 2022 war, the Red Sea and 2026 chokepoint events), so the
# two parameters come from one sample. The full 1956-2026 catalogue is kept
# as the lower-bound sensitivity (CAT_START = 1956).
CAT_START, CAT_END = 2000, 2026
# the catalogue runs to the end of August 2026 (the Hormuz closure is
# recorded as ongoing then), so the exposure window is 1 Jan CAT_START to
# 31 Aug 2026: 26.67 years for 2000-2026, 70.67 for the full record
CAT_OBS_END = 2026 + 8 / 12
CAT_WINDOW_YEARS = CAT_OBS_END - CAT_START
BAND = 2.0


def _scenario_rates(start: int = CAT_START):
    """{s1, s2: ((rate/BAND, rate*BAND), median duration in months)} from
    the catalogue events of start-2026, and the event count."""
    ev = pd.read_csv(inputs.MAPS / "security_events.csv")
    ev = ev[(ev.year >= start) & (ev.year <= CAT_END)]
    window = CAT_OBS_END - start
    s1 = ev[ev["class"].isin(["supplier_outage", "export_ban"])]
    s2 = ev[ev["class"] == "chokepoint"]
    out = {}
    for tag, d in (("s1", s1), ("s2", s2)):
        rate = len(d) / window
        out[tag] = ((rate / BAND, rate * BAND),
                    float(d.duration_months.clip(upper=24).median()))
    return out, len(ev)

# 2026-10-19: both anchors converted at the 2025 average rate used for carbon prices (policy.py, US$1.13/EUR)
EUR_USD_2025 = 1.13
ACER_MID_USD_GJ = 69.0 / 3.6 * EUR_USD_2025    # ACER (2018) Table 50: EU-26 median national CoDG, 69 EUR/MWh -> 21.7
ENTSOG_USD_GJ = 600.0 / 3.6 * EUR_USD_2025     # ENTSOG TYNDP 2018 planning value, 600 EUR/MWh -> 188.3 (upper anchor)


def _panel_prices():
    """20-yr median world prices per imported commodity, $/GJ."""
    _, g = country_gas_monthly()
    return {"crude": float(g["brent"].median()),
            "refined": float(g["diesel"].median()),
            "gas": float(g["gas_eu"].median())}


def build() -> pd.DataFrame:
    vi = pd.read_csv(inputs.MAPS / "vulnerability_inputs.csv").set_index("country")
    px = _panel_prices()
    rates, n_events = _scenario_rates()
    global S1_P, S1_D, S2_P, S2_D
    S1_P, S1_D = rates["s1"]
    S2_P, S2_D = rates["s2"]
    print(f"scenario rates from the {n_events}-event catalogue "
          f"({CAT_START}-{CAT_END}): s1 supplier {S1_P[0]:.3f}-{S1_P[1]:.3f}/yr, "
          f"median {S1_D:.1f} mo | s2 chokepoint "
          f"{S2_P[0]:.3f}-{S2_P[1]:.3f}/yr, median {S2_D:.1f} mo")

    # ---- imported energy by commodity, GJ/yr --------------------------------
    vol = pd.DataFrame({
        "crude": vi.val_crude / px["crude"],
        "refined": vi.val_refined / px["refined"],
        "gas": vi.val_gas / px["gas"]}).clip(lower=0)

    # ---- MEASURED demand by fuel (OWID/EI): the demand layer ----------------
    # Replaces the v1 inference of energy use from the net-import share, and
    # caps every at-risk quantity by what the country actually consumes.
    dem = pd.read_csv(inputs.MAPS / "demand_by_fuel.csv",
                      index_col="country").reindex(vi.index)
    oil_dem = dem.oil_gj
    gas_dem = dem.gas_gj
    vol["crude"] = np.minimum(vol.crude, oil_dem.fillna(np.inf))
    vol["refined"] = np.minimum(vol.refined,
                                (oil_dem - vol.crude).clip(lower=0)
                                .fillna(np.inf))
    vol["gas"] = np.minimum(vol.gas, gas_dem.fillna(np.inf))
    e_imp = vol.sum(axis=1)                                   # GJ/yr, capped
    oil_share = (vol.crude + vol.refined).div(e_imp).fillna(0)

    # import dependence per fuel service (diagnostic + demand statistics)
    dep_oil = ((vol.crude + vol.refined) / oil_dem).clip(upper=1)
    dep_gas = (vol.gas / gas_dem).clip(upper=1)

    # energy use: measured primary energy where OWID has it; the v1
    # net-import-share inference only as fallback
    pct = vi.energy_import_pct / 100.0
    e_use_inf = e_imp.where(pct <= 0, e_imp / pct.clip(lower=0.02))
    e_use_inf = e_use_inf.where(pct > 0, np.nan)
    e_use = dem.primary_gj.where(dem.primary_gj.notna(), e_use_inf)

    # ---- CoDF: ACER-calibrated GDP intensity --------------------------------
    gdp_int = vi.gdp_usd / e_use                              # $/GJ of use
    eu = [c for c in ("Germany", "France", "Italy", "Spain", "Netherlands",
                      "Belgium", "Poland", "Austria", "Portugal", "Greece",
                      "Hungary", "Czechia", "Slovakia", "Lithuania", "Latvia",
                      "Estonia", "Croatia", "Slovenia", "Ireland", "Finland",
                      "Sweden", "Denmark", "Romania", "Bulgaria")
          if c in gdp_int.index and np.isfinite(gdp_int.get(c, np.nan))]
    lam = ACER_MID_USD_GJ / float(gdp_int.loc[eu].median())
    codf = lam * gdp_int
    # upper anchor: the ENTSOG planning value as a uniform multiple of
    # the central ACER anchor (a per-country correction was tried and
    # abandoned — the dead expression that used to sit here made it a
    # no-op either way)
    codf_hi = codf * (ENTSOG_USD_GJ / ACER_MID_USD_GJ)

    # ---- scenario losses, GJ/yr expected ------------------------------------
    top = pd.DataFrame({
        "crude": vi.top_crude, "refined": vi.top_refined, "gas": vi.top_gas})
    l1 = (vol * top.fillna(0)).sum(axis=1)                    # s1 energy at risk
    l2 = e_imp                                                # s2: everything

    def q_of(p_lo, p_hi, d, mit):
        p_c = np.sqrt(p_lo * p_hi)
        return p_lo * d / 12 * (1 - mit), p_c * d / 12 * (1 - mit), \
            p_hi * d / 12 * (1 - mit)

    mit = pd.Series(0.0, index=vi.index)
    mem = mit.index.isin(IEA)
    # 90-day stocks cover the oil share fully for s2 (3 mo) and half of s1
    mit_s1 = pd.Series(np.where(mem, 0.5 * oil_share, 0.0), index=vi.index)
    mit_s2 = pd.Series(np.where(mem, 1.0 * oil_share, 0.0), index=vi.index)

    rows = {}
    for tag, pr, d, loss, m in (("s1", S1_P, S1_D, l1, mit_s1),
                                ("s2", S2_P, S2_D, l2, mit_s2)):
        for lbl, p in zip(("lo", "c", "hi"),
                          (pr[0], np.sqrt(pr[0] * pr[1]), pr[1])):
            rows[f"sar_{tag}_{lbl}"] = p * d / 12 * loss * (1 - m)
    sar = pd.DataFrame(rows)
    for lbl in ("lo", "c", "hi"):
        sar[f"sar_{lbl}"] = sar[f"sar_s1_{lbl}"] + sar[f"sar_s2_{lbl}"]

    # q_eff: expected disrupted-time exposure of the MARGINAL displaced
    # import. The marginal domestic gigajoule displaces an imported
    # one; under pro-rata rationing across imports a supplier cut-off
    # (s1) strands it with probability = the top-supplier share of
    # imports, while a systemic interruption (s2) strands every
    # imported gigajoule. Economies with no net imports carry ZERO —
    # a domestic gigajoule there displaces nothing a disruption could
    # strand (the old version applied the global time fraction to
    # every country, handing net exporters a positive security value).
    # q_eff_plan keeps the planning view: targeted displacement of the
    # most-at-risk import, full time fraction while any exposure
    # exists — the upper band, in the spirit of the ENTSOG anchor.
    top_sh = (l1 / e_imp).replace([np.inf, -np.inf], np.nan) \
        .clip(0, 1).fillna(0.0)
    # the gate is the NET position (OWID/EI, the same layer as the
    # budget figure): a gross importer that net-exports (the US
    # imports heavy crude while exporting light) can redirect its own
    # exports and has nothing a disruption strands. Gross imports are
    # the fallback only where OWID has no row.
    from .security_budget import _net_dep
    dep_o_net, dep_g_net = _net_dep()
    o_n = dep_o_net.reindex(vi.index)
    g_n = dep_g_net.reindex(vi.index)
    net_any = (o_n.fillna(0) > 0) | (g_n.fillna(0) > 0)
    no_owid = o_n.isna() & g_n.isna()
    has_imp = (net_any | (no_owid & (e_imp > 0))).astype(float)
    q1 = np.sqrt(S1_P[0] * S1_P[1]) * S1_D / 12
    q2 = np.sqrt(S2_P[0] * S2_P[1]) * S2_D / 12
    q_eff = (q1 * top_sh * (1 - mit_s1)
             + q2 * (1 - mit_s2)) * has_imp
    q_eff_plan = (q1 * (1 - mit_s1) + q2 * (1 - mit_s2)) * has_imp

    # ---- supply side: premium of the domestic hydrogen backstop -------------
    lcof_h2 = country_lcof()["hydrogen"]                      # $/GJ median yr
    p_mkt = pd.Series({c: grey_h2_price(c) for c in lcof_h2.index})
    pi_h2 = (lcof_h2 - p_mkt).clip(lower=0)

    out = pd.DataFrame({
        "gdp_usd": vi.gdp_usd, "e_imp_gj": e_imp, "e_use_gj": e_use,
        "oil_demand_gj": oil_dem, "gas_demand_gj": gas_dem,
        "fossil_demand_gj": dem.fossil_gj,
        "dep_oil": dep_oil, "dep_gas": dep_gas,
        "oil_share": oil_share, "codf_usd_gj": codf,
        "codf_hi_usd_gj": codf_hi,
        "codf_drift": dem.codf_drift,
        "sar_lo_gj": sar.sar_lo, "sar_c_gj": sar.sar_c,
        "sar_hi_gj": sar.sar_hi,
        "esd_c_usd": sar.sar_c * codf,
        "esd_gdp_pct": sar.sar_c * codf / vi.gdp_usd * 100,
        "esd_gdp_hi_pct": sar.sar_hi * codf_hi / vi.gdp_usd * 100,
        "pi_h2_usd_gj": pi_h2.reindex(vi.index),
        "q_eff": q_eff,
        "q_eff_plan": q_eff_plan,
    })
    out["ics_usd_gj"] = out.pi_h2_usd_gj / out.q_eff
    out["bcr_c"] = out.codf_usd_gj / out.ics_usd_gj
    out["bcr_hi"] = out.codf_hi_usd_gj / out.ics_usd_gj

    # ---- FUEL-RESOLVED ledger --------------------------------------------
    # CoDF differs by fuel service (Fan: "across fuels, sectors"; the ACER
    # anchor is GAS-specific; the boundary appendix adds that material uses
    # are not even in GJ). v1.5 structure: CoDF_{c,f} = CoDF_c x m_f with
    # DECLARED service multipliers pending the sectoral Phase-2 build —
    # gas = 1.0 (the anchor's own service), oil-transport = 1.3 (fewer
    # short-run substitutes at the device), coal = 0.5 (stockpiled, most
    # switchable). Supply side pairs each service with its DROP-IN escape:
    # gas <- e-methane, oil <- e-diesel; hydrogen covers its own service.
    M_F = {"gas": 1.0, "oil": 1.3}
    lcof_all = country_lcof()
    _, g = country_gas_monthly()
    from .gap import fossil_for_fuel, country_gas_monthly as _cgm
    gasdf, gpan = _cgm()
    rows_f = []
    for c in vi.index:
        if c not in lcof_all.index or c not in gasdf.columns:
            continue
        # per-service exposure fraction of time (top-supplier + systemic)
        for svc, com_cols, fuel in (("gas", ["gas"], "e-methane"),
                                    ("oil", ["crude", "refined"],
                                     "e-diesel")):
            v_com = float(vol.loc[c, com_cols].sum())
            if not np.isfinite(v_com) or v_com <= 0:
                continue
            tshare = float((vol.loc[c, com_cols] *
                            top.loc[c, com_cols].fillna(0)).sum()) / v_com
            q_svc = (np.sqrt(S1_P[0] * S1_P[1]) * S1_D / 12 * tshare
                     + np.sqrt(S2_P[0] * S2_P[1]) * S2_D / 12)
            pfos = float(fossil_for_fuel(fuel, gasdf[c], gpan, c).median())
            pi_f = max(0.0, float(lcof_all.loc[c, fuel]) - pfos)
            codf_f = out.loc[c, "codf_usd_gj"] * M_F[svc]
            ics_f = pi_f / q_svc if q_svc > 0 else np.inf
            rows_f.append(dict(
                country=c, service=svc, backstop=fuel,
                codf_f_usd_gj=codf_f, pi_f_usd_gj=pi_f, q_svc=q_svc,
                ics_f_usd_gj=ics_f,
                bcr_f_c=codf_f / ics_f if ics_f > 0 else np.inf,
                bcr_f_hi=codf_f * (ENTSOG_USD_GJ / ACER_MID_USD_GJ)
                / ics_f if ics_f > 0 else np.inf))
    fuel_ledger = pd.DataFrame(rows_f)
    fuel_ledger.to_csv(inputs.MAPS / "security_by_fuel.csv", index=False)

    # ---- demand-side Herfindahl (claim 4 of the boundary framework) --------
    sh = dem[["oil_gj", "gas_gj", "coal_gj"]].div(dem.fossil_gj, axis=0)
    out["hhi_demand"] = (sh ** 2).sum(axis=1).where(dem.fossil_gj > 0)

    # ---- the HANDOFF OBJECT (methodology_handoff §5): the per-scenario ----
    # distribution, WITH explicit durations, so the valuation side can apply
    # a duration-dependent VoLL instead of a scalar to the expectation.
    sc_rows = []
    for c in vi.index:
        for svc, com_cols in (("gas", ["gas"]), ("oil", ["crude",
                                                         "refined"])):
            v_com = float(vol.loc[c, com_cols].sum())
            if not np.isfinite(v_com) or v_com <= 0:
                continue
            tsh = float((vol.loc[c, com_cols] *
                         top.loc[c, com_cols].fillna(0)).sum()) / v_com
            for sid, p, d_mo, loss in (
                    ("s1_top_supplier", np.sqrt(S1_P[0] * S1_P[1]),
                     S1_D, v_com * tsh),
                    ("s2_systemic", np.sqrt(S2_P[0] * S2_P[1]),
                     S2_D, v_com)):
                sc_rows.append(dict(
                    country=c, scenario_id=sid, probability=round(p, 4),
                    unserved_quantity=loss * d_mo / 12,
                    unit="GJ", duration_days=round(d_mo * 30.4),
                    end_use=svc, end_use_class="energetic"))
    pd.DataFrame(sc_rows).to_csv(inputs.MAPS / "security_scenarios.csv",
                                 index=False)
    return out, lam, fuel_ledger


def main():
    out, lam, fl = build()
    out.to_csv(inputs.MAPS / "security_index.csv")
    v = out.dropna(subset=["esd_gdp_pct"])
    print(f"security ledger v1.1: {len(out)} countries, "
          f"{len(v)} with import-side exposure")
    dm = out.dropna(subset=["fossil_demand_gj"])
    print(f"demand layer joined: {len(dm)} countries with measured "
          f"fossil demand; median import dependence oil "
          f"{out.dep_oil.median():.0%}, gas {out.dep_gas.median():.0%}")
    print(f"CoDF calibration: lambda={lam:.3f} on the EU cross-section "
          f"(mid ${ACER_MID_USD_GJ}/GJ); upper anchor ENTSOG "
          f"${ENTSOG_USD_GJ}/GJ")
    print(f"CoDF central: median ${v.codf_usd_gj.median():.0f}/GJ, "
          f"p10-p90 {v.codf_usd_gj.quantile(.1):.0f}-"
          f"{v.codf_usd_gj.quantile(.9):.0f}")
    print(f"ESD/GDP central: median {v.esd_gdp_pct.median():.2f}%  "
          f"max {v.esd_gdp_pct.max():.2f}% ({v.esd_gdp_pct.idxmax()})")
    b = v.dropna(subset=["bcr_c"])
    print(f"BCR central: median {b.bcr_c.median():.2f}; countries with "
          f"BCR>=1: {(b.bcr_c >= 1).sum()} central, "
          f"{(b.bcr_hi >= 1).sum()} at the ENTSOG anchor")
    print("top BCR:", ", ".join(f"{c} {x:.1f}" for c, x in
          b.bcr_c.sort_values(ascending=False).head(6).items()))
    print("\nfuel-resolved ledger (drop-in backstops):")
    for svc, d in fl.groupby("service"):
        d = d[np.isfinite(d.bcr_f_hi)]
        print(f"  {svc:4s} via {d.backstop.iloc[0]:10s} "
              f"median Pi {d.pi_f_usd_gj.median():5.1f} $/GJ | "
              f"median ICS {d.ics_f_usd_gj.median():7.0f} | "
              f"BCR>=1 at ENTSOG: {(d.bcr_f_hi >= 1).sum()}/{len(d)}")
    h = out.dropna(subset=["ics_usd_gj"])
    print(f"  own  via hydrogen    median Pi "
          f"{h.pi_h2_usd_gj.median():5.1f} $/GJ | median ICS "
          f"{h.ics_usd_gj.median():7.0f} | BCR>=1 at ENTSOG: "
          f"{(h.bcr_hi >= 1).sum()}/{len(h)}")
    # audit
    assert (v.sar_lo_gj <= v.sar_c_gj + 1e-9).all() and \
           (v.sar_c_gj <= v.sar_hi_gj + 1e-9).all(), "SaR ordering"
    assert (v.esd_gdp_pct.dropna() >= 0).all()
    assert np.isfinite(lam) and 0 < lam < 10
    print("SECURITY LEDGER CHECKS PASSED")


if __name__ == "__main__":
    main()
