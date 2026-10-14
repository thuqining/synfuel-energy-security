"""Audit the evidence and calculations behind the two Figure 3 candidates.

Writes country-level coverage, event-level price moves, and fuel-specific risk
inputs for the ammonia and FT (diesel + jet) versions.  It deliberately keeps
observed, benchmark-filled and constructed months separate.

Run from scripts/:  python -u -m lcof.audit_figure3
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from math import sqrt

from . import inputs, params as P
from .coreset import CORE30_LIST
from .fig_main_cost import FUELS
from .gap import (CRISES, COAL_H2_SHARE, country_gas_monthly, fossil_for_fuel,
                  FIG3_BASELINE_MONTHS, FIG3_PRIMARY_WASHOUT,
                  FIG3_WASHOUT_SENSITIVITY, figure3_regimes,
                  paired_event_price_distributions, pre_event_mask)
from . import prices as PR
from .import_prices import NH3_GAS_ROUTE, nh3_regional_urea_ratio
from .import_prices import (W0, W1, ammonia_status, country_ammonia_monthly,
                            country_buy_monthly, country_buy_monthly_filled,
                            load as load_import_prices)
from .security_budget import family_dependence


OUT_COUNTRY = inputs.MAPS / "figure3_country_audit.csv"
OUT_EVENT = inputs.MAPS / "figure3_event_audit.csv"
OUT_MEMBER = inputs.MAPS / "figure3_member_event_audit.csv"
OUT_WASHOUT = inputs.MAPS / "figure3_washout_sensitivity.csv"
MMB = P.MMBTU_PER_GJ
NH3_GJ_PER_T = 18.6
FT_GJ_PER_T = 42.9      # diesel 42.8, jet 43.0 MJ/kg (LHV)


def _mask(index: pd.PeriodIndex) -> pd.Series:
    out = pd.Series(False, index=index)
    for start, end in CRISES.values():
        out.loc[start:end] = True
    return out


def _cpi() -> tuple[pd.Series, float]:
    path = inputs.PROJECT / "data" / "prices" / "fx" / "us_cpi_monthly.csv"
    d = pd.read_csv(path)
    s = pd.Series(d.cpi_u.to_numpy(float),
                  index=pd.PeriodIndex(d.month, freq="M")).sort_index()
    # BLS marks 2025-10 unavailable.  Interpolate that one documented gap only
    # for the sensitivity calculation; the raw table retains the missing flag.
    s = s.interpolate(limit=1, limit_area="inside")
    return s, float(s[s.index.year == 2025].mean())


def _real(series: pd.Series, cpi: pd.Series, reference: float) -> pd.Series:
    factor = (reference / cpi.reindex(series.index)).astype(float)
    return series * factor


def _corr(a: pd.Series, b: pd.Series) -> float:
    """Pearson correlation without BLAS (the current Windows env has a
    broken NumPy/BLAS DLL; keeping the audit arithmetic independently usable)."""
    pairs = [(float(x), float(y)) for x, y in zip(a, b)
             if np.isfinite(x) and np.isfinite(y)]
    if len(pairs) < 2:
        return float("nan")
    ax = sum(x for x, _ in pairs) / len(pairs)
    by = sum(y for _, y in pairs) / len(pairs)
    num = sum((x - ax) * (y - by) for x, y in pairs)
    den = sqrt(sum((x - ax) ** 2 for x, _ in pairs) *
               sum((y - by) ** 2 for _, y in pairs))
    return num / den if den else float("nan")


def _demand() -> pd.DataFrame:
    meta = inputs.load_meta(2025)
    dg = pd.read_csv(inputs.MAPS / "demand_fuel_grid.csv", index_col=0)
    cols = [fuel + "_gj" for fuel in FUELS]
    return dg[cols].join(meta[["country"]]).groupby("country").sum()


_UREA_NH3 = None


def _urea_nh3() -> pd.Series:
    """urea-implied ammonia price, $/GJ LHV nominal: World Bank urea net of
    the conversion cost, per tonne of contained ammonia (prices.py)"""
    global _UREA_NH3
    if _UREA_NH3 is None:
        _UREA_NH3 = PR.load(verified=True).ammonia_implied.dropna()
    return _UREA_NH3


def _coal_dependence() -> pd.Series:
    """net coal import dependence, max(0, 1 - production / consumption),
    latest OWID year since 2015 -- the construction security_budget._net_dep
    uses for oil and gas"""
    d = pd.read_csv(inputs.MAPS / "owid_energy.csv",
                    usecols=["country", "year", "coal_consumption",
                             "coal_production"])
    d = d.replace({"country": {"United States": "United States of America"}})
    out = {}
    for c, g in d[d.year >= 2015].groupby("country"):
        gc = g.dropna(subset=["coal_consumption"]).sort_values("year")
        if not len(gc) or gc.iloc[-1].coal_consumption <= 0:
            continue
        gp = g.dropna(subset=["coal_production"]).sort_values("year")
        prod = gp.iloc[-1].coal_production if len(gp) else 0.0
        out[c] = max(0.0, 1.0 - prod / gc.iloc[-1].coal_consumption)
    return pd.Series(out)


def _series(country: str, version: str, demand: pd.DataFrame,
            prices: pd.DataFrame, gasdf: pd.DataFrame, gas) -> tuple:
    if version == "ft":
        d = float(demand.at[country, "e-diesel_gj"])
        j = float(demand.at[country, "e-kerosene_gj"])
        jet_share = j / (d + j) if d + j else 0.0
        own, own_basis = country_buy_monthly(country, 1 - jet_share,
                                              jet_share, prices)
        full, fill_basis = country_buy_monthly_filled(
            country, 1 - jet_share, jet_share, prices)
        return full, own, "observed import/export/parity + regional fill", \
            fill_basis, d + j

    # 2026-09-14: the traded urea-implied ammonia price replaces the
    # gas-constructed grey-ammonia cost as the proxy (see prices.py)
    proxy = _urea_nh3().reindex(gasdf.index)
    own, reason = country_ammonia_monthly(country, prices)
    if len(own):
        overlap = pd.concat([own, proxy], axis=1,
                            keys=["own", "proxy"]).dropna()
        ratio = float((overlap.own / overlap.proxy).median()) \
            if len(overlap) >= 12 else 1.0
        full = own.combine_first(proxy * ratio).dropna()
        mode = "observed ammonia import + urea-implied fill"
        basis = (f"{reason}; urea-fill ratio={ratio:.3f}; "
                 f"overlap={len(overlap)}")
    elif country in NH3_GAS_ROUTE:
        full = fossil_for_fuel("ammonia", gasdf[country], gas, country).dropna()
        mode = "grey ammonia from the administered national gas price"
        basis = reason
    else:
        k, n_obs = nh3_regional_urea_ratio(country, prices)
        full = (proxy * k).dropna()
        mode = "urea-implied ammonia x regional ratio"
        basis = f"{reason}; regional own/urea ratio {k:.3f} from {n_obs} observed importers"
    return full, own, mode, basis, float(demand.at[country, "ammonia_gj"])


def main() -> None:
    idx = pd.period_range(W0, W1, freq="M")
    crisis = _mask(idx)
    cpi, cpi_2025 = _cpi()
    demand = _demand()
    prices = load_import_prices()
    gasdf, gas = country_gas_monthly()
    dep_gas, dep_oil = family_dependence(CORE30_LIST)
    dep_coal = _coal_dependence()
    generic_v = pd.read_csv(inputs.MAPS / "vulnerability_index.csv",
                            index_col=0)
    ft_hhi = pd.read_csv(inputs.PROJECT / "data" / "prices" /
                         "figure3_risk" / "ft_supplier_hhi_2023.csv",
                         index_col=0)
    # product-matched exposure for diesel + jet: HS 271019 trade, 2015-2025
    ft_trade = pd.read_csv(inputs.PROJECT / "data" / "prices" /
                           "figure3_risk" / "ft_trade_balance_annual.csv")
    ft_trade = ft_trade.groupby("country").agg(
        imports_t=("imports_t", "sum"), exports_t=("exports_t", "sum"),
        n_years=("year", "nunique"))
    vuln_inputs = pd.read_csv(inputs.MAPS / "vulnerability_inputs.csv",
                              index_col=0)
    coal_hhi = pd.read_csv(inputs.PROJECT / "data" / "prices" /
                           "figure3_risk" / "coal_supplier_hhi_2023.csv",
                           index_col=0)
    # natural gas only (HS 271111 + 271121); HS 2711 also carries LPG and
    # Germany's partners are confidential (see dl_gas_supplier_hhi.py)
    gas_hhi = pd.read_csv(inputs.PROJECT / "data" / "prices" /
                          "figure3_risk" / "gas_supplier_hhi_2023.csv",
                          index_col=0)
    nh3_hhi = pd.read_csv(inputs.PROJECT / "data" / "prices" /
                          "imports_ammonia" / "ammonia_supplier_hhi_2023.csv",
                          index_col=0)
    nh3_hhi = nh3_hhi.rename(index={"United States":
                                     "United States of America"})
    nh3_trade = ammonia_status()
    # 2026-10-07: the ammonia chain is measured in nitrogen (ammonia, urea, nitrates,
    # ammonium phosphates; nitrogen_consumption.py), 2025: the direct import share is
    # the net-imported share of the nitrogen an economy uses and the product
    # concentration is that of its nitrogen suppliers
    from .nitrogen_consumption import nitrogen_hhi
    n_bal = pd.read_csv(inputs.MAPS / "ammonia_consumption.csv", index_col=0)
    n_hhi = nitrogen_hhi()

    country_rows, event_rows, washout_rows, member_rows = [], [], [], []
    cache = {}
    for version in ("ft", "ammonia"):
        site = pd.read_csv(inputs.MAPS / f"core30_sites_{version}.csv",
                           index_col=0)
        for country in CORE30_LIST:
            full, own, mode, basis, dem_gj = _series(
                country, version, demand, prices, gasdf, gas)
            full = full.reindex(idx).dropna()
            own = own.reindex(idx).dropna()
            own_months = set(own.index)
            cm = crisis.reindex(full.index).fillna(False)
            nominal_pooled_event = full[cm]
            nominal_quiet, nominal_crisis, supply_events = \
                paired_event_price_distributions(full, version)
            nominal_quiet = pd.Series(nominal_quiet, dtype=float)
            nominal_crisis = pd.Series(nominal_crisis, dtype=float)
            real = _real(full, cpi, cpi_2025).dropna()
            rcm = crisis.reindex(real.index).fillna(False)
            real_pooled_event = real[rcm]
            real_quiet, real_crisis, real_supply_events = \
                paired_event_price_distributions(real, version)
            real_quiet = pd.Series(real_quiet, dtype=float)
            real_crisis = pd.Series(real_crisis, dtype=float)
            if supply_events != real_supply_events:
                raise AssertionError(f"{version}/{country}: nominal-real event mismatch")

            for washout in FIG3_WASHOUT_SENSITIVITY:
                wq, wc, wr = paired_event_price_distributions(
                    real, version, washout_months=washout)
                washout_rows.append({
                    "version": version, "country": country,
                    "washout_months": washout,
                    "normal_median_2025usd_mmbtu":
                        float(np.median(wq) * MMB) if len(wq) else np.nan,
                    "disruption_median_2025usd_mmbtu":
                        float(np.median(wc) * MMB) if len(wc) else np.nan,
                    "disruption_uplift_2025usd_pct":
                        float((np.median(wc) / np.median(wq) - 1) * 100)
                        if len(wq) and len(wc) else np.nan,
                    "n_regimes": len(wr),
                    "regimes": " | ".join(wr),
                })

            direct = feed = np.nan
            w_direct = w_gas = w_coal = 0.0
            gas_hhi_source = ""
            if version == "ft":
                # the same chain rule as ammonia (2026-09-16): the share of
                # the fuel's own supply that is imported, as product (net
                # imports of HS 271019, 2015-2025, over diesel + jet demand)
                # or as the crude oil it is refined from at home; nothing
                # else of the energy mix enters
                tr = ft_trade.reindex([country]).iloc[0]
                avg_net_t = max(float(tr.imports_t - tr.exports_t), 0.0) / float(tr.n_years) \
                    if np.isfinite(tr.imports_t) else np.nan
                direct = min(avg_net_t * FT_GJ_PER_T / dem_gj, 1.0) \
                    if dem_gj > 0 and np.isfinite(avg_net_t) else np.nan
                crude_dep = float(dep_oil.get(country, 0.0))
                feed = crude_dep
                if np.isfinite(direct):
                    w_direct = direct
                    w_gas = (1.0 - direct) * crude_dep      # crude term (kept in the gas slot)
                    exposure = min(w_direct + w_gas, 1.0)
                else:
                    exposure = np.nan
                hhi_product = float(ft_hhi.hhi_ft.get(country, np.nan))
                hhi_crude = float(vuln_inputs.hhi_crude.get(country, np.nan))
                if not np.isfinite(hhi_crude):
                    # no crude imports reported (Saudi Arabia produces; Kenya,
                    # Morocco, Madagascar have no refinery of their own): the
                    # product concentration stands in
                    hhi_crude = hhi_product
                hhi_feedstock = hhi_crude if w_gas > 0 else np.nan
                hhi_effective = ((w_direct * hhi_product + w_gas * hhi_crude) / exposure) \
                    if exposure > 0 else 0.0
                gas_hhi_source = "crude HS 2709 HHI (2023)"
                trade_status = "net importer" if exposure > 0 else "net exporter"
            else:
                direct = float(n_bal.n_import_share.get(country, np.nan))
                # ammonia made at home from imported gas (or coal) is as
                # exposed as imported ammonia: the direct import share plus
                # the domestic share times the import dependence of its
                # feedstock, gas and coal weighted by the national coal
                # share of hydrogen (gap.COAL_H2_SHARE)
                sig = COAL_H2_SHARE.get(country, 0.0)
                gas_dep = float(dep_gas.get(country, 0.0))
                coal_dep = float(dep_coal.get(country, 0.0))
                feed = (1.0 - sig) * gas_dep + sig * coal_dep
                if np.isfinite(direct):
                    w_direct = direct
                    w_gas = (1.0 - direct) * (1.0 - sig) * gas_dep
                    w_coal = (1.0 - direct) * sig * coal_dep
                    exposure = min(w_direct + w_gas + w_coal, 1.0)
                else:
                    exposure = np.nan
                hhi_product = float(n_hhi.hhi_nitrogen.get(country, np.nan))
                if not np.isfinite(hhi_product):
                    hhi_product = float(nh3_hhi.hhi_ammonia.get(country, np.nan))
                hhi_gas = float(gas_hhi.hhi_gas_used.get(country, np.nan))
                gas_hhi_source = str(gas_hhi.hhi_gas_source.get(country, "missing"))
                if not np.isfinite(hhi_gas):
                    # no natural-gas market, or suppliers not identified: the
                    # nitrogen such an economy uses arrives as imported
                    # ammonia, so the ammonia import concentration stands in
                    hhi_gas = hhi_product
                    gas_hhi_source += "; ammonia import HHI used"
                hhi_coal = float(coal_hhi.hhi_coal.get(country, np.nan)) \
                    if sig > 0 else 0.0
                feed_weight = w_gas + w_coal
                hhi_feedstock = ((w_gas * hhi_gas + w_coal * hhi_coal) /
                                 feed_weight) if feed_weight > 0 else np.nan
                hhi_effective = ((w_direct * hhi_product +
                                  w_gas * hhi_gas + w_coal * hhi_coal) /
                                 exposure) if exposure > 0 else 0.0
                # the same rule as the FT branch and the figure: a net
                # exporter of the chain imports neither the product nor its
                # feedstock (exposure exactly zero); the product-only trade
                # status called Poland, which exports ammonia but imports the
                # gas it is made from, an exporter (found 2026-09-16)
                trade_status = (("net importer" if exposure > 0 else "net exporter")
                                if np.isfinite(exposure) else "unclassified")

            build = float(site.best_med_mmbtu.get(country, np.nan))
            quiet_mmbtu = float(nominal_quiet.median() * MMB)
            crisis_mmbtu = float(nominal_crisis.median() * MMB)
            # Synthetic costs are expressed in real USD.  Risk must therefore
            # use the real-2025-USD fossil comparator, not the nominal pooled
            # 2006-2026 median.
            quiet_real_mmbtu = float(real_quiet.median() * MMB)
            premium = max(build - quiet_real_mmbtu, 0.0)
            own_crisis = sum(month in own_months for month in full.index[cm])
            country_rows.append({
                "version": version, "country": country,
                "comparator_mode": mode, "trade_status": trade_status,
                "basis": basis, "first": str(full.index.min()),
                "last": str(full.index.max()), "months_total": len(full),
                "months_observed": len(own),
                "months_filled_or_constructed": len(full) - len(own),
                "observed_share": len(own) / len(full) if len(full) else np.nan,
                "crisis_months_total": int(cm.sum()),
                "crisis_months_observed": int(own_crisis),
                "crisis_observed_share": own_crisis / cm.sum() if cm.sum() else np.nan,
                "annual_demand_ej": dem_gj / 1e9,
                "annual_demand_bn_mmbtu": dem_gj / MMB / 1e9,
                "estimated_quiet_bill_bn_usd": dem_gj * quiet_real_mmbtu / MMB / 1e9,
                "quiet_median_nominal_mmbtu": quiet_mmbtu,
                "crisis_median_nominal_mmbtu": crisis_mmbtu,
                "crisis_uplift_nominal_pct":
                    (crisis_mmbtu / quiet_mmbtu - 1) * 100,
                "quiet_median_2025usd_mmbtu": quiet_real_mmbtu,
                "crisis_median_2025usd_mmbtu": float(real_crisis.median() * MMB),
                "crisis_uplift_2025usd_pct":
                    (real_crisis.median() / real_quiet.median() - 1) * 100,
                "quiet_iqr_over_median":
                    float((nominal_quiet.quantile(.75) - nominal_quiet.quantile(.25)) /
                          nominal_quiet.median()),
                "build_median_mmbtu": build,
                "escape_premium_mmbtu": premium,
                "import_exposure": exposure,
                "supplier_hhi": hhi_effective,
                "supplier_hhi_product": hhi_product,
                "supplier_hhi_feedstock": hhi_feedstock,
                "supplier_hhi_effective": hhi_effective,
                "supplier_hhi_gas_source": gas_hhi_source,
                "import_exposure_direct": direct,
                "direct_import_share_basis":
                    ("2025 net nitrogen imports (ammonia and nitrogen fertilizers) over national nitrogen use"
                     if version == "ammonia" else
                     "mean annual 2015-2025 net HS271019 imports divided by modelled diesel + jet demand"),
                "feedstock_import_dependence": feed,
                "exposure_weight_direct_ammonia": w_direct,
                "exposure_weight_gas_feedstock": w_gas,
                "exposure_weight_coal_feedstock": w_coal,
                "normal_price_definition":
                    "month-weighted contiguous clean pre12 distribution; event and recovery months excluded; rebased to national quiet median",
                "disruption_price_definition":
                    "month-weighted supply-disruption regime months paired to contiguous pre12 and rebased",
                "washout_months": FIG3_PRIMARY_WASHOUT,
                "n_supply_events": len(supply_events),
                "normal_distribution_n": len(nominal_quiet),
                "disruption_distribution_n": len(nominal_crisis),
                "supply_events": " | ".join(supply_events),
                "supplier_hhi_method":
                    ("exposure-weighted HS271019 product and HS2709 crude HHI" if version == "ft" else
                     "exposure-weighted 2025 nitrogen-supplier, HS271111+271121 natural gas and HS2701 coal HHI"),
                "pooled_event_median_nominal_mmbtu":
                    float(nominal_pooled_event.median() * MMB),
                "pooled_event_median_2025usd_mmbtu":
                    float(real_pooled_event.median() * MMB),
                "generic_oil_gas_V_current": float(generic_v.V.get(country, np.nan)),
            })
            cache[(version, country)] = (full, own_months)

            for event, p0, p1, members in figure3_regimes(
                    version, FIG3_PRIMARY_WASHOUT):
                start, end = str(p0), str(p1)
                ev = full[(full.index >= p0) & (full.index <= p1)]
                pre = full[pre_event_mask(
                    full.index, start, version=version,
                    washout_months=FIG3_PRIMARY_WASHOUT,
                    contiguous=True)]
                ev_real = _real(ev, cpi, cpi_2025).dropna()
                pre_real = _real(pre, cpi, cpi_2025).dropna()
                event_rows.append({
                    "version": version, "country": country, "event": event,
                    "start": start, "end": end, "n_event": len(ev),
                    "n_pre": len(pre),
                    "member_events": " | ".join(members),
                    "washout_months": FIG3_PRIMARY_WASHOUT,
                    "pre_first": str(pre.index.min()) if len(pre) else "",
                    "pre_last": str(pre.index.max()) if len(pre) else "",
                    "event_observed_share":
                        sum(m in own_months for m in ev.index) / len(ev)
                        if len(ev) else np.nan,
                    # the 12-month baseline must be observed too, or the
                    # move compares an event with a filled baseline
                    "pre_observed_share":
                        sum(m in own_months for m in pre.index) / len(pre)
                        if len(pre) else np.nan,
                    "event_move_nominal_pct":
                        (ev.median() / pre.median() - 1) * 100
                        if len(ev) >= 3 and len(pre) >= FIG3_BASELINE_MONTHS else np.nan,
                    "event_move_2025usd_pct":
                        (ev_real.median() / pre_real.median() - 1) * 100
                        if len(ev_real) >= 3 and len(pre_real) >= FIG3_BASELINE_MONTHS else np.nan,
                })
                # the same regime, one dated event at a time, against the
                # regime's baseline: what Extended Data Fig. 4 draws
                for member in members:
                    a_, b_ = CRISES[member]
                    m0, m1 = pd.Period(a_, "M"), pd.Period(b_, "M")
                    evm = full[(full.index >= m0) & (full.index <= m1)]
                    evm_real = _real(evm, cpi, cpi_2025).dropna()
                    member_rows.append({
                        "version": version, "country": country, "regime": event,
                        "event": member, "start": a_, "end": b_,
                        "n_event": len(evm), "n_pre": len(pre),
                        "baseline_first": str(pre.index.min()) if len(pre) else "",
                        "baseline_last": str(pre.index.max()) if len(pre) else "",
                        "event_observed_share":
                            sum(m in own_months for m in evm.index) / len(evm)
                            if len(evm) else np.nan,
                        "pre_observed_share":
                            sum(m in own_months for m in pre.index) / len(pre)
                            if len(pre) else np.nan,
                        "event_move_nominal_pct":
                            (evm.median() / pre.median() - 1) * 100
                            if len(evm) >= 3 and len(pre) >= FIG3_BASELINE_MONTHS else np.nan,
                        "event_move_2025usd_pct":
                            (evm_real.median() / pre_real.median() - 1) * 100
                            if len(evm_real) >= 3 and len(pre_real) >= FIG3_BASELINE_MONTHS else np.nan,
                    })

    countries = pd.DataFrame(country_rows)
    # Supply risk is a pure security metric.  The old cube-root index is kept
    # separately as V_strategic because it also includes competitiveness.
    countries["escape_premium_normalized"] = countries.groupby("version")[
        "escape_premium_mmbtu"].transform(
            lambda s: s / s.max() if s.max() > 0 else 0.0)
    countries["supply_risk"] = (
        countries.import_exposure.clip(0, 1) *
        countries.supplier_hhi_effective.clip(0, 1)) ** (1 / 2)
    countries["V_strategic"] = (
        countries.import_exposure.clip(0, 1) *
        countries.supplier_hhi_effective.clip(0, 1) *
        countries.escape_premium_normalized.clip(0, 1)) ** (1 / 3)
    # Preserve the old downstream column while separating supply security
    # from cost competitiveness in the main figure.
    countries["V_product"] = countries["V_strategic"]

    events = pd.DataFrame(event_rows)
    ev_country = events.groupby(["version", "country"])[
        ["event_move_nominal_pct", "event_move_2025usd_pct"]].median()
    ev_country.columns = ["median_event_move_nominal_pct",
                          "median_event_move_2025usd_pct"]
    countries = countries.join(ev_country, on=["version", "country"])
    countries.to_csv(OUT_COUNTRY, index=False)
    events.to_csv(OUT_EVENT, index=False)
    pd.DataFrame(member_rows).to_csv(OUT_MEMBER, index=False)
    pd.DataFrame(washout_rows).to_csv(OUT_WASHOUT, index=False)

    for version, group in countries.groupby("version"):
        print(f"\n{version.upper()}: observed share median "
              f"{group.observed_share.median():.0%}, range "
              f"{group.observed_share.min():.0%}-{group.observed_share.max():.0%}; "
              f"crisis observed median {group.crisis_observed_share.median():.0%}")
        print("  comparator modes:", group.comparator_mode.value_counts().to_dict())
        print(f"  paired supply-event uplift: nominal median "
              f"{group.crisis_uplift_nominal_pct.median():+.1f}%, "
              f"real-2025USD {group.crisis_uplift_2025usd_pct.median():+.1f}%")
        print(f"  strategic V vs current generic V correlation: "
              f"{_corr(group.V_strategic, group.generic_oil_gas_V_current):.2f}")
    print(f"\nwrote {OUT_COUNTRY}\nwrote {OUT_EVENT}\nwrote {OUT_WASHOUT}")


if __name__ == "__main__":
    main()
