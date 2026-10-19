"""
make_tab_breakeven.py - Supplementary Table tab:breakeven (2026-10-06, question on the
EUR600/MWh valuation): for each of the 26 net importers of Fig. 4a, the European reference value of
fuel lost at which the security margin plus the carbon price covers the extra cost of the
1%-of-GDP merit-order portfolio. The security margin is linear in the value of lost fuel (every
national value is scaled by the same European factor, SI equation s:voll), so

    break-even = (extra cost - carbon price) / security margin at the reference x US$185/MMBtu.

Reads data/cost/fig5a_chain.csv and security_budget.csv (the Fig. 4a basis). Prints the LaTeX table.

From scripts/:  python -m lcof.make_tab_breakeven
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import inputs

from .params import MMBTU_PER_GJ as MMB
from .security import ACER_MID_USD_GJ, ENTSOG_USD_GJ


def _peak_2022_real() -> float:
    """August 2022 monthly peak of the European gas price (Pink Sheet, LHV), in 2025 US$ per MMBtu (BLS CPI-U)"""
    g = pd.read_csv(inputs.PROJECT / "data" / "prices" / "fossil_monthly_gj_lhv.csv", index_col=0).gas_eu
    c = pd.read_csv(inputs.PROJECT / "data" / "prices" / "fx" / "us_cpi_monthly.csv", index_col=0).cpi_u
    c = c.astype(float)
    return float(g["2022-08"] * MMB * c[c.index.str.startswith("2025")].mean() / c["2022-08"])


# 2026-10-19: US$/MMBtu, from the anchors of security.py (EUR at the 2025 average US$1.13) and the 2022 peak in
# 2025 dollars; were 185, 23 and 78 (nominal)
REF, CENTRAL, PEAK22 = ENTSOG_USD_GJ * MMB, ACER_MID_USD_GJ * MMB, _peak_2022_real()
SHORT = {"Dominican Republic": "Dominican Rep."}


def frame():
    f = pd.read_csv(inputs.MAPS / "fig5a_chain.csv", index_col=0)
    sb = pd.read_csv(inputs.MAPS / "security_budget.csv", index_col=0)
    f = f[f.index.isin(sb.index[sb.import_pct > 0])]
    m = f.gross_usd_t - f.net_usd_t
    need = (f.gross_usd_t - f.p_co2_usd_t) / m.replace(0, np.nan) * REF
    out = pd.DataFrame({"extra": f.gross_usd_t, "margin": m, "carbon": f.p_co2_usd_t, "need": need})
    return out.sort_values("need", na_position="last")


def table():
    d = frame()
    assert len(d) == 26
    counts = [int((d.need <= v).sum()) for v in (CENTRAL, PEAK22, REF)]
    # the count at the reference value must equal the justified portfolios of Fig. 4a
    f = pd.read_csv(inputs.MAPS / "fig5a_chain.csv", index_col=0).reindex(d.index)
    assert counts[2] == int((f.net_usd_t <= f.p_co2_usd_t).sum()), counts
    print("justified at central / 2022 peak / reference value:", counts)
    rows = []
    for c, r in d.iterrows():
        if np.isnan(r.need):
            be, mult = "--", "--"
        elif r.need > 5000:
            be, mult = r"$>$5,000", r"$>$200"
        else:
            be, mult = f"{r.need:,.0f}", f"{r.need / CENTRAL:.1f}"
        rows.append(f"{SHORT.get(c, c)} & {r.extra:,.0f} & {r.margin:,.0f} & {r.carbon:.0f} & {be} & {mult}\\\\")
    return "\n".join([
        r"\begin{table}[htbp]\centering\small",
        r"\caption[Break-even value of lost fuel]{Break-even value of lost fuel for the 26 net importers of",
        r"Fig.~\ref{fig:co2}a: the European reference value at which the security margin and the carbon price",
        r"together cover the extra cost of the 1\%-of-GDP portfolio (Supplementary Table~\ref{tab:fig5a}). The",
        r"security margin is linear in the value of lost fuel, because every national value is scaled by the",
        r"same European factor (equation~(\ref{s:voll})), so the break-even value is the extra cost less the",
        rf"carbon price, divided by the security margin at the reference value and multiplied by US\${REF:.0f}\,MMBtu$^{{-1}}$",
        r"(EUR600\,MWh$^{-1}$). Costs per tonne are in US\$\,tCO$_2^{-1}$. At the central value of",
        r"US\$23\,MMBtu$^{-1}$ no portfolio is justified, at about the 2022 monthly peak of the European gas",
        r"price, US\$78\,MMBtu$^{-1}$, one (Ireland), and at the reference value seven. Indonesia's",
        r"portfolio replaces no imports.}\label{tab:breakeven}",
        r"\begin{tabular}{@{}lrrrrr@{}}\toprule",
        r" & Extra & Security margin & Carbon & \multicolumn{2}{c}{Break-even value of lost fuel}\\",
        r"\cmidrule(l){5-6}",
        r"Economy & cost & at reference & price & US\$\,MMBtu$^{-1}$ & $\times$ central value\\\midrule",
        *rows,
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ])


if __name__ == "__main__":
    print(table())
