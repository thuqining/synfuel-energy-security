"""make_fig3_tables.py — appendix tables behind Figure 3 and Extended Data Fig. 4.

Writes into synthetic_fuel_nature/ (the .tex wraps the first two in table
environments; the third is a self-contained longtable):

  tab_fig3_ammonia.tex   the 30 core economies, ammonia: fuel-chain exposure,
                         supplier concentration, risk, normal and disruption
                         import price (2025 US$/MMBtu), disruption premium at
                         the median and the 99th percentile, bill, worst bill
                         shock, share of observed customs months
  tab_fig3_ft.tex        the same for diesel and jet fuel
  tab_crisis_world.tex   every modelled country, the natural-gas channel: the
                         gas-price marker the country is priced off, the
                         grey-ammonia route's real move in the 2017 Qatar
                         blockade and in the 2021-2026 compound regime against
                         the matched baseline, and the whole-economy
                         vulnerability inputs (oil-and-gas bill import share,
                         supplier HHI, V) where they exist

Sources: data/cost/figure3_country_audit.csv, core30_sites_{ammonia,ft}.csv,
ed_crisis_by_country_regime.csv, vulnerability_index.csv.

From scripts/:  conda run -n synfuel python -u -m lcof.make_fig3_tables
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import inputs
from .coreset import CORE30_LIST
from .gap import gas_regime
from .make_paper_tables import BS, EOL, NL, SHORT, TEXDIR, wrap

MARKER = {"ttf": "TTF", "lng_import": "Japan LNG contract",
          "henry_hub": "Henry Hub", "producer": "administered"}
# long names that would push the 143-row table past the text width
SHORT_WORLD = {"United Republic of Tanzania": "Tanzania",
               "Bosnia and Herzegovina": "Bosnia-Herzegovina",
               "Democratic Republic of the Congo": "DR Congo",
               "Republic of Serbia": "Serbia",
               "Central African Republic": "Central African Rep.",
               "Republic of the Congo": "Congo (Rep.)",
               "Falkland Islands": "Falkland Is.",
               "Trinidad and Tobago": "Trinidad \\& Tobago",
               "Equatorial Guinea": "Equat. Guinea"}
FUEL_TITLE = {"ammonia": "ammonia", "ft": "diesel and jet fuel"}


def _name(c: str) -> str:
    return SHORT.get(c, c).replace("&", BS + "&")


def _f(v, fmt="{:.2f}", dash="--") -> str:
    return dash if v is None or not np.isfinite(v) else fmt.format(v)


def _pct(v) -> str:
    if v is not None and np.isfinite(v) and abs(v) < 0.5:
        return "0"                    # never "-0"
    return _f(v, "{:+.0f}")


def core_table(version: str) -> tuple[str, pd.DataFrame]:
    ca = pd.read_csv(inputs.MAPS / "figure3_country_audit.csv")
    ca = ca[ca.version == version].set_index("country")
    # 2026-10-13: Fig. 3 tables written before the 1st-99th switch name the column crisis_p98_mmbtu
    site = pd.read_csv(inputs.MAPS / f"core30_sites_{version}.csv").rename(columns={"crisis_p98_mmbtu": "crisis_p99_mmbtu"}).set_index("country")
    d = ca.join(site[["crisis_p99_mmbtu", "crisis_cost_max_gdp_pct",
                      "crisis_cost_max_event"]], how="left")
    d = d.loc[[c for c in CORE30_LIST if c in d.index]]
    # the figure's own rule: net importers of the chain by risk, then the
    # net exporters (exposure exactly zero) by risk
    d["exporter"] = d.import_exposure <= 0
    d = d.sort_values(["exporter", "supply_risk"], ascending=[True, False])
    # the risk printed in the figure is sqrt(E x H_effective); recompute so the
    # table can never drift from the figure
    chk = np.sqrt(d.import_exposure * d.supplier_hhi_effective)
    assert float((chk - d.supply_risk).abs().max()) < 1e-6, "risk != sqrt(E*H)"
    d["p99_uplift_pct"] = (d.crisis_p99_mmbtu / d.quiet_median_2025usd_mmbtu - 1) * 100
    rows = []
    n_imp = int((~d.exporter).sum())
    for i, (c, r) in enumerate(d.iterrows()):
        if i == n_imp:
            rows.append(BS + "midrule" + NL + BS + "multicolumn{11}{@{}l}{"
                        + BS + "emph{Net exporters of the chain}}")
        rows.append(" & ".join([
            _name(c),
            _f(r.import_exposure, "{:.2f}"),
            _f(r.supplier_hhi_effective, "{:.2f}") if r.import_exposure > 0 else "--",
            _f(r.supply_risk, "{:.2f}"),
            _f(r.quiet_median_2025usd_mmbtu, "{:.0f}"),
            _f(r.crisis_median_2025usd_mmbtu, "{:.0f}"),
            _pct(r.crisis_uplift_2025usd_pct),
            _pct(r.p99_uplift_pct),
            _f(r.estimated_quiet_bill_bn_usd,
               "{:.2g}" if r.estimated_quiet_bill_bn_usd < 1 else "{:.1f}"
               if r.estimated_quiet_bill_bn_usd < 10 else "{:.0f}"),
            _f(r.crisis_cost_max_gdp_pct, "{:.2f}") if r.import_exposure > 0 else "--",
            _f(r.observed_share * 100, "{:.0f}"),
        ]))
    header = (" & " + BS + "multicolumn{3}{c}{Supply risk} & "
              + BS + "multicolumn{4}{c}{Import price, 2025 US" + BS + "$ per MMBtu} & "
              + " & & " + EOL + NL
              + BS + "cmidrule(lr){2-4}" + BS + "cmidrule(lr){5-8}" + NL
              + "Economy & $E$ & $H$ & $" + BS + "sqrt{EH}$ & normal & disruption & "
              + BS + "multicolumn{1}{c}{$" + BS + "Delta$ (\\%)} & "
              + BS + "multicolumn{1}{c}{p99 $" + BS + "Delta$ (\\%)} & "
              + "Bill & Shock & Obs." + EOL)
    tab = wrap("@{}l r r r r r r r r r r@{}", header, rows)
    return tab, d


def world_table() -> tuple[str, pd.DataFrame]:
    t = pd.read_csv(inputs.MAPS / "ed_crisis_by_country_regime.csv")
    t = t[t.fuel == "ammonia"]
    qat = t[t.regime == "Qatar blockade"].set_index("country").event_move_2025usd_pct
    comp = t[t.regime.str.contains("Hormuz")].set_index("country")
    vi = pd.read_csv(inputs.MAPS / "vulnerability_index.csv").set_index("country")
    N_BILL = int(vi.V.notna().sum())          # economies with a bill layer
    d = pd.DataFrame({"compound": comp.event_move_2025usd_pct,
                      "baseline": comp.baseline_first.str[:4] + "--" + comp.baseline_last.str[2:4]})
    d["qatar"] = qat
    d["marker"] = [MARKER[gas_regime(c)] for c in d.index]
    d = d.join(vi[["import_pct", "hhi", "V"]], how="left")
    d["core"] = d.index.isin(CORE30_LIST)
    d = d.sort_values("compound", ascending=False)
    rows = []
    for c, r in d.iterrows():
        rows.append(" & ".join([
            SHORT_WORLD.get(c, _name(c)) + ("$^{" + BS + "dagger}$" if r.core else ""),
            r.marker, _pct(r.qatar), _pct(r.compound),
            _f(r.import_pct, "{:.0f}"), _f(r.hhi, "{:.2f}"), _f(r.V, "{:.2f}")]))
    head = ("Country & Gas-price marker & " + BS + "multicolumn{2}{c}{Grey-ammonia move (\\%)} & "
            + BS + "multicolumn{3}{c}{Oil-and-gas bill}" + EOL + NL
            + BS + "cmidrule(lr){3-4}" + BS + "cmidrule(lr){5-7}" + NL
            + " & & Qatar 2017 & 2021--26 & import (\\%) & HHI & $V$" + EOL)
    body = (BS + "begingroup" + BS + "footnotesize" + BS + "setlength{" + BS
            + "tabcolsep}{3pt}" + NL
            + BS + "begin{longtable}{@{}l l r r r r r@{}}" + NL
            + BS + "caption{" + BS + "textbf{Price moves on the natural-gas channel for every "
            "modelled country.} Change of the event median over the matched twelve clean "
            "months before the regime, in 2025 US" + BS + "$, for the grey-ammonia route on "
            "each country's gas price (equation~" + BS + "ref{eq:greynh3}): the 2017 Qatar "
            "blockade and the 2021--2026 compound regime (Russian gas squeeze through the "
            "Hormuz disruption; baseline 2019--20). The marker column gives the gas price "
            "each country is priced from (Section~" + BS + "ref{sec:worldtables}). The "
            "contract-indexed Japan LNG import price moves little in real terms and "
            "administered producer prices do not move, so these rows understate what a spot "
            "buyer paid. $" + BS + "dagger$ marks the 30 core economies, whose own customs "
            "import prices are in Supplementary Tables~" + BS + "ref{tab:fig3ammonia} and "
            + BS + "ref{tab:fig3ft}. Oil-linked fuels are not tabulated by country, because "
            "their world benchmark moves identically everywhere (Extended Data Fig.~" + BS
            + "ref{fig:crisis}b). The right-hand columns give the whole-economy vulnerability "
            "inputs for the " + str(N_BILL) + " countries with a bill layer: the net import share of the "
            "oil-and-gas bill, the supplier HHI over HS 2709, 2710 and 2711, and the "
            "descriptive index $V$ (Extended Data Table~" + BS + "ref{tab:cases}).}" + NL
            + BS + "label{tab:crisisworld}" + EOL + NL
            + BS + "toprule" + NL + head + NL + BS + "midrule" + NL + BS + "endfirsthead" + NL
            + BS + "multicolumn{7}{@{}l}{" + BS + "small" + BS + "emph{Table~" + BS
            + "ref{tab:crisisworld} continued}}" + EOL + NL
            + BS + "toprule" + NL + head + NL + BS + "midrule" + NL + BS + "endhead" + NL
            + BS + "midrule" + NL + BS + "multicolumn{7}{r@{}}{" + BS + "small" + BS
            + "emph{continued on next page}}" + EOL + NL + BS + "endfoot" + NL
            + BS + "bottomrule" + NL + BS + "endlastfoot" + NL
            + (" " + EOL + NL).join(rows) + " " + EOL + NL
            + BS + "end{longtable}" + NL + BS + "endgroup" + NL)
    return body, d


def main() -> None:
    out = {}
    for version in ("ammonia", "ft"):
        tab, d = core_table(version)
        (TEXDIR / f"tab_fig3_{version}.tex").write_text(tab, encoding="utf-8")
        out[version] = d
        imp = d[~d.exporter]
        print(f"{version}: {len(imp)} importers / {int(d.exporter.sum())} exporters; "
              f"risk max {imp.supply_risk.idxmax()} {imp.supply_risk.max():.2f}, "
              f"min importer {imp.supply_risk.idxmin()} {imp.supply_risk.min():.2f}; "
              f"disruption premium max {d.crisis_uplift_2025usd_pct.idxmax()} "
              f"{d.crisis_uplift_2025usd_pct.max():+.0f}%, min {d.crisis_uplift_2025usd_pct.idxmin()} "
              f"{d.crisis_uplift_2025usd_pct.min():+.0f}%; p99 premium max "
              f"{d.p99_uplift_pct.idxmax()} {d.p99_uplift_pct.max():+.0f}%; "
              f"bill shock max {d.crisis_cost_max_gdp_pct.idxmax()} "
              f"{d.crisis_cost_max_gdp_pct.max():.2f}% GDP")
    body, w = world_table()
    (TEXDIR / "tab_crisis_world.tex").write_text(body, encoding="utf-8")
    print(f"world: {len(w)} countries; 2021-26 grey-ammonia move max "
          f"{w.compound.idxmax()} {w.compound.max():+.0f}%, min {w.compound.idxmin()} "
          f"{w.compound.min():+.0f}%; by marker: "
          + "; ".join(f"{m} n={g.shape[0]} median {g.compound.median():+.0f}%"
                      for m, g in w.groupby('marker')))
    print("wrote tab_fig3_ammonia.tex, tab_fig3_ft.tex, tab_crisis_world.tex")


if __name__ == "__main__":
    main()
