"""risk_all_countries.py — the Figure 3 fuel-specific supply risk for every
modelled country, ammonia and diesel + jet fuel.

Same construction as audit_figure3 (the 30 core economies keep their
Figure 3 values, read from figure3_country_audit.csv): the fuel-chain
exposure E = m + (1 - m) d_feed, with m the net-imported share of the
product (HS 281410 or 271019, tonnes over the fuel's demand) and d_feed the
OWID net import dependence of the feedstock (gas and coal weighted by the
national coal share of hydrogen for ammonia; crude oil for diesel and jet);
the exposure-weighted 2023 supplier HHI H over the product and feedstock
import partners (ammonia 281410, natural gas 271111 + 271121, coal 2701;
middle distillates 271019, crude 2709 from vulnerability_inputs.csv); the
risk sqrt(E H). Differences for the 112 non-core reporters, flagged in the
table: the net-import share averages 2021-2023 (the core 30: 2015-2025) and
confidential-partner markets get no mirror-flow repair (the product
concentration or the feedstock concentration stands in, as in the audit).

Inputs: data/prices/figure3_risk/world_risk_inputs.csv (dl_world_risk_inputs.py),
        reporter_codes_world.csv, figure3_country_audit.csv, owid_energy.csv,
        vulnerability_inputs.csv, demand_fuel_grid.csv
Output: data/cost/fig3_risk_all_countries.csv
        synthetic_fuel_nature/tab_risk_world.tex (longtable)

From scripts/:  conda run -n synfuel python -u -m lcof.risk_all_countries
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import inputs
from .audit_figure3 import _coal_dependence, _demand, NH3_GJ_PER_T, FT_GJ_PER_T
from .coreset import CORE30_LIST
from .gap import COAL_H2_SHARE
from .make_paper_tables import BS, EOL, NL, SHORT, TEXDIR
from .make_fig3_tables import SHORT_WORLD, _f
from .security_budget import family_dependence

RISK_DIR = inputs.PROJECT / "data" / "prices" / "figure3_risk"
OUT = inputs.MAPS / "fig3_risk_all_countries.csv"
NES, MIN_MARKET_USD = 899, 1e6
GAS_CODES = ("271111", "271121")


def _hhi(part: pd.DataFrame) -> tuple[float, float, float, str]:
    """(hhi, total_usd, nes_share, flag) from partner-level import rows of
    one reporter and one commodity group (partner 0 = World is dropped)."""
    p = part[(part.partner != 0) & part.partner.notna() & (part.value_usd > 0)]
    total = float(p.value_usd.sum())
    if total < MIN_MARKET_USD:
        return np.nan, total, np.nan, "no import market (< US$1M)"
    nes = float(p[p.partner == NES].value_usd.sum())
    named = p[p.partner != NES].groupby("partner").value_usd.sum()
    if total and nes / total > 0.5:
        return np.nan, total, nes / total, "suppliers confidential (nes > 50%)"
    sh = named / named.sum()
    return float((sh ** 2).sum()), total, nes / total if total else np.nan, "ok"


def _net_import_t(tot: pd.DataFrame, active_years: int = 0) -> tuple[float, int, bool]:
    """average annual net imports in tonnes over the reported years; a year
    with value but no weight takes the reporter's median unit value. A
    reporter that filed customs data in the window but shows no record for
    this product traded none of it: net imports zero over its active years."""
    if tot.empty:
        return (0.0, active_years, False) if active_years else (np.nan, 0, False)
    t = tot.copy()
    t["t"] = t.net_kg / 1000.0
    ok = (t.t > 0) & (t.value_usd > 0)
    imputed = False
    if ok.any():
        uv = float((t[ok].value_usd / t[ok].t).median())
        miss = (t.t <= 0) & (t.value_usd > 0)
        t.loc[miss, "t"] = t.loc[miss, "value_usd"] / uv
        imputed = bool(miss.any())
    by = t.groupby(["year", "flow"]).t.sum().unstack("flow").reindex(columns=["M", "X"]).fillna(0.0)
    years = int(len(by))
    net = float((by.M - by.X).mean()) if years else np.nan
    return net, years, imputed


def main() -> None:
    reps = pd.read_csv(RISK_DIR / "reporter_codes_world.csv")
    # 2026-10-07: ammonia chain in nitrogen (ammonia and nitrogen fertilizers, 2025)
    from .nitrogen_consumption import nitrogen_hhi
    n_bal = pd.read_csv(inputs.MAPS / "ammonia_consumption.csv", index_col=0)
    n_hhi = nitrogen_hhi()
    raw = pd.read_csv(RISK_DIR / "world_risk_inputs.csv")
    raw["hs"] = raw.hs.astype(str)
    core = pd.read_csv(inputs.MAPS / "figure3_country_audit.csv")
    demand = _demand()
    dep_gas, dep_oil = family_dependence(list(reps.country))
    dep_coal = _coal_dependence()
    vuln = pd.read_csv(inputs.MAPS / "vulnerability_inputs.csv", index_col=0)

    rows = []
    for country in reps.country:
        if country in CORE30_LIST:
            for version in ("ammonia", "ft"):
                c = core[(core.version == version) & (core.country == country)]
                if c.empty:
                    continue
                c = c.iloc[0]
                rows.append(dict(country=country, version=version, source="core30",
                                 direct_share=c.import_exposure_direct,
                                 feed_dependence=c.feedstock_import_dependence,
                                 exposure=c.import_exposure,
                                 hhi_product=c.supplier_hhi_product,
                                 hhi_feedstock=c.supplier_hhi_feedstock,
                                 hhi_effective=c.supplier_hhi_effective,
                                 supply_risk=c.supply_risk, trade_status=c.trade_status,
                                 balance_years=("nitrogen, 2025" if version == "ammonia" else "2015-2025"), note=""))
            continue
        r = raw[raw.country == country]
        if r.empty:
            for version in ("ammonia", "ft"):
                rows.append(dict(country=country, version=version, source="none",
                                 note="no Comtrade reporter data"))
            continue
        part = r[r.kind == "partner"]
        tot = r[r.kind == "total"]
        # years in which the reporter filed any customs total in the window:
        # a product absent from those years was not traded, not unreported
        active_years = int(tot.year.nunique())
        for version in ("ammonia", "ft"):
            if version == "ammonia":
                dem = float(demand.ammonia_gj.get(country, np.nan))
                net_t, years, imputed = _net_import_t(tot[tot.hs == "281410"], active_years)
                gj_per_t = NH3_GJ_PER_T
                years = 3   # nitrogen balance in its latest year (2023-2025), not an average
                sig = COAL_H2_SHARE.get(country, 0.0)
                gas_dep = float(dep_gas.get(country, 0.0))
                coal_dep = float(dep_coal.get(country, 0.0))
                feed = (1.0 - sig) * gas_dep + sig * coal_dep
                h_prod, v_prod, nes_prod, f_prod = _hhi(part[part.hs == "281410"])
                if country in n_hhi.index:
                    h_prod = float(n_hhi.hhi_nitrogen[country])
                    nes_prod = float(n_hhi.nes_share[country])
                    f_prod = "nitrogen suppliers"
                h_gas, v_gas, nes_gas, f_gas = _hhi(part[part.hs.isin(GAS_CODES)])
                h_coal, _, _, f_coal = _hhi(part[part.hs == "2701"])
                notes = []
                if not np.isfinite(h_gas):
                    h_gas = h_prod            # the audit's stand-in
                    notes.append(f"gas HHI: {f_gas}; ammonia HHI used")
                if sig > 0 and not np.isfinite(h_coal):
                    h_coal = h_gas
                    notes.append(f"coal HHI: {f_coal}; gas HHI used")
                if sig == 0:
                    h_coal = 0.0
                m = float(n_bal.n_import_share.get(country, np.nan))
                if np.isfinite(m):
                    w_direct = m
                    w_gas = (1.0 - m) * (1.0 - sig) * gas_dep
                    w_coal = (1.0 - m) * sig * coal_dep
                    exposure = min(w_direct + w_gas + w_coal, 1.0)
                    if not np.isfinite(h_prod):
                        h_prod = h_gas if w_direct > 0 else 0.0
                        if w_direct > 0:
                            notes.append(f"ammonia HHI: {f_prod}; feedstock HHI used")
                    feedw = w_gas + w_coal
                    h_feed = ((w_gas * h_gas + w_coal * h_coal) / feedw) if feedw > 0 else np.nan
                    h_eff = ((w_direct * h_prod + w_gas * h_gas + w_coal * h_coal) / exposure) \
                        if exposure > 0 else 0.0
                else:
                    exposure = h_feed = h_eff = np.nan
            else:
                d_ = float(demand["e-diesel_gj"].get(country, np.nan))
                j_ = float(demand["e-kerosene_gj"].get(country, np.nan))
                dem = d_ + j_
                net_t, years, imputed = _net_import_t(tot[tot.hs == "271019"], active_years)
                gj_per_t = FT_GJ_PER_T
                feed = float(dep_oil.get(country, 0.0))
                h_prod, v_prod, nes_prod, f_prod = _hhi(part[part.hs == "271019"])
                h_crude = float(vuln.hhi_crude.get(country, np.nan))
                notes = []
                if not np.isfinite(h_crude):
                    h_crude = h_prod
                    notes.append("no crude HHI; product HHI used")
                m = min(max(net_t, 0.0) * gj_per_t / dem, 1.0) if dem > 0 and np.isfinite(net_t) else np.nan
                if np.isfinite(m):
                    w_direct = m
                    w_feed = (1.0 - m) * feed
                    exposure = min(w_direct + w_feed, 1.0)
                    if not np.isfinite(h_prod):
                        h_prod = h_crude if w_direct > 0 else 0.0
                        if w_direct > 0:
                            notes.append(f"product HHI: {f_prod}; crude HHI used")
                    h_feed = h_crude if w_feed > 0 else np.nan
                    h_eff = ((w_direct * h_prod + w_feed * h_crude) / exposure) if exposure > 0 else 0.0
                else:
                    exposure = h_feed = h_eff = np.nan
            risk = float(np.sqrt(exposure * h_eff)) if np.isfinite(exposure) and np.isfinite(h_eff) else np.nan
            if not np.isfinite(exposure):
                status = "unclassified"
            else:
                status = "net importer" if exposure > 0 else "net exporter"
            if years and years < 3:
                notes.append(f"balance from {years} reported year(s)")
            if imputed:
                notes.append("tonnes imputed from value")
            rows.append(dict(country=country, version=version, source="comtrade-2021-23",
                             direct_share=m, feed_dependence=feed, exposure=exposure,
                             hhi_product=h_prod, hhi_feedstock=h_feed, hhi_effective=h_eff,
                             supply_risk=risk, trade_status=status,
                             balance_years=("nitrogen, latest of 2023-2025" if version == "ammonia" else f"{years} of 2021-2023"), note="; ".join(notes),
                             product_import_usd_2023=v_prod, demand_gj=dem,
                             net_import_t_per_yr=net_t))
    d = pd.DataFrame(rows)
    d.to_csv(OUT, index=False)
    for version, g in d.groupby("version"):
        ok = g[np.isfinite(g.supply_risk)]
        print(f"{version}: {len(ok)} of {len(g)} countries with a risk; "
              f"{(ok.trade_status == 'net importer').sum()} net importers; "
              f"top: " + ", ".join(f"{r.country} {r.supply_risk:.2f}" for r in
                                   ok.sort_values('supply_risk', ascending=False).head(8).itertuples()))
        print(f"   unclassified: {sorted(g[g.trade_status == 'unclassified'].country)}")

    # ---- the appendix longtable ------------------------------------------
    w = d.pivot(index="country", columns="version",
                values=["exposure", "hhi_effective", "supply_risk", "trade_status", "source", "note"])
    order = w[("supply_risk", "ammonia")].fillna(-1).sort_values(ascending=False).index
    lines = []
    for c in order:
        def cell(v, col):
            x = w.loc[c, (v, col)]
            return _f(x, "{:.2f}") if isinstance(x, float) else "--"
        mark = ""
        if w.loc[c, ("source", "ammonia")] == "core30":
            mark = "$^{" + BS + "dagger}$"
        elif str(w.loc[c, ("note", "ammonia")]) or str(w.loc[c, ("note", "ft")]):
            if "HHI" in str(w.loc[c, ("note", "ammonia")]) + str(w.loc[c, ("note", "ft")]):
                mark = "$^{" + BS + "ddagger}$"
        name = SHORT_WORLD.get(c, SHORT.get(c, c).replace("&", BS + "&"))
        lines.append(" & ".join([
            name + mark,
            cell("exposure", "ammonia"), cell("hhi_effective", "ammonia"), cell("supply_risk", "ammonia"),
            cell("exposure", "ft"), cell("hhi_effective", "ft"), cell("supply_risk", "ft")]))
    head = ("Country & " + BS + "multicolumn{3}{c}{Ammonia} & " + BS
            + "multicolumn{3}{c}{Diesel and jet fuel}" + EOL + NL
            + BS + "cmidrule(lr){2-4}" + BS + "cmidrule(lr){5-7}" + NL
            + " & $E$ & $H$ & $" + BS + "sqrt{EH}$ & $E$ & $H$ & $" + BS + "sqrt{EH}$" + EOL)
    n_ok = {v: int(np.isfinite(d[d.version == v].supply_risk).sum()) for v in ("ammonia", "ft")}
    body = (BS + "begingroup" + BS + "footnotesize" + BS + "setlength{" + BS + "tabcolsep}{5pt}" + NL
            + BS + "begin{longtable}{@{}l r r r r r r@{}}" + NL
            + BS + "caption{" + BS + "textbf{Fuel-specific supply risk for every modelled "
            "country.} The risk index of Fig.~" + BS + "ref{fig:cities} for ammonia and for "
            "diesel and jet fuel. $E$ is the fuel-chain import exposure (net-imported share of "
            "the product plus the domestic share times the feedstock's net import dependence), "
            "$H$ the exposure-weighted 2023 supplier Herfindahl index of product and feedstock "
            "imports, and $" + BS + "sqrt{EH}$ the risk. $" + BS + "dagger$ marks the 30 core "
            "economies, which use the inputs of Fig.~" + BS + "ref{cities} (2015--2025 net "
            "imports and mirror-flow repair of confidential partners); all other reporters use "
            "2021--2023 net imports without mirror repair. $" + BS + "ddagger$ marks a supplier "
            "concentration that stands in for one the reporter does not identify (Section~"
            + BS + "ref{sec:risk}). A dash marks an economy that reports no customs data for "
            "2021--2023, has no demand for the fuel, or has no product or feedstock import "
            "market with identifiable suppliers (for ammonia, economies whose nitrogen arrives "
            "as finished fertilizer). In total " + f"{n_ok['ammonia']}" + " economies have an "
            "ammonia risk and " + f"{n_ok['ft']}" + " a diesel-and-jet risk. Rows are sorted "
            "by ammonia risk.}" + NL
            + BS + "label{tab:riskworld}" + EOL + NL
            + BS + "toprule" + NL + head + NL + BS + "midrule" + NL + BS + "endfirsthead" + NL
            + BS + "multicolumn{7}{@{}l}{" + BS + "small" + BS + "emph{Table~" + BS
            + "ref{tab:riskworld} continued}}" + EOL + NL
            + BS + "toprule" + NL + head + NL + BS + "midrule" + NL + BS + "endhead" + NL
            + BS + "midrule" + NL + BS + "multicolumn{7}{r@{}}{" + BS + "small" + BS
            + "emph{continued on next page}}" + EOL + NL + BS + "endfoot" + NL
            + BS + "bottomrule" + NL + BS + "endlastfoot" + NL
            + (" " + EOL + NL).join(lines) + " " + EOL + NL
            + BS + "end{longtable}" + NL + BS + "endgroup" + NL)
    body = body.replace(BS + "ref{cities}", BS + "ref{fig:cities}")
    (TEXDIR / "tab_risk_world.tex").write_text(body, encoding="utf-8")
    print(f"wrote {OUT} ({len(d)} rows) and tab_risk_world.tex ({len(lines)} countries)")


if __name__ == "__main__":
    main()
