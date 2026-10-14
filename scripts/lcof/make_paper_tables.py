"""make_paper_tables.py — LaTeX summary tables for the Nature draft.

Emits three self-contained tabular environments into
synthetic_fuel_nature/ (the .tex wraps them in table envs):
  tab_reco.tex       main text: the recommendation map, per fuel
  tab_cases.tex      main text: the ledger + parity for 12 exemplars
  tab_parity50.tex   appendix: parity years for the 50 core economies

From scripts/:  conda run -n synfuel python -u -m lcof.make_paper_tables
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import inputs

TEXDIR = inputs.MAPS.parent.parent / "synthetic_fuel_nature"
UMM = 1.0551                       # $/MMBtu per $/GJ
BS = chr(92)                       # backslash
NL = chr(10)
EOL = BS + BS                      # LaTeX row terminator
SHORT = {"United States of America": "United States",
         "United Kingdom of Great Britain and Northern Ireland":
         "United Kingdom", "United Arab Emirates": "UAE",
         "Russian Federation": "Russia",
         "Dominican Republic": "Dominican Rep.",
         "Papua New Guinea": "Papua N. Guinea"}


def yr(v: float) -> str:
    return "$>$2050" if v >= 2051 else f"{v:.0f}"


def wrap(colspec: str, header: str, rows: list[str]) -> str:
    return (BS + "begin{tabular}{" + colspec + "}" + NL
            + BS + "toprule" + NL + header + NL
            + BS + "midrule" + NL
            + (" " + EOL + NL).join(rows) + " " + EOL + NL
            + BS + "bottomrule" + NL
            + BS + "end{tabular}" + NL)


def main() -> None:
    # ---- Table: recommendation map, per fuel ------------------------------
    st = pd.read_csv(inputs.MAPS / "fuel_reco_stats.csv") \
           .sort_values("cells", ascending=False)
    rows = []
    for _, r in st.iterrows():
        mkt = r.demand_pj / 1.0551 * 0.001      # PJ -> billion MMBtu
        be = yr(r.tstar_med) if np.isfinite(r.tstar_med) else "$>$2050"
        rows.append(f"{r.fuel} & {r.cells:.0f} & {r.lcof_mmbtu:.0f} & "
                    f"{r.rival_mmbtu:.0f} & {mkt:.2f} & {be}")
    header = (" & cells & median LCOF & grey rival & market won & "
              "median " + EOL + NL
              + "Fuel & won & (" + BS + "$/MMBtu) & (" + BS + "$/MMBtu) & "
              + "(bn MMBtu" + BS + ",yr$^{-1}$) & break-even " + EOL)
    (TEXDIR / "tab_reco.tex").write_text(
        wrap("@{}l r r r r c@{}", header, rows), encoding="utf-8")

    # ---- Table: ledger + parity, 12 exemplars -----------------------------
    v = pd.read_csv(inputs.MAPS / "vulnerability_index.csv", index_col=0)
    si = pd.read_csv(inputs.MAPS / "security_index.csv", index_col=0)
    be = pd.read_csv(inputs.MAPS / "breakeven_carbon_2025.csv")
    beh = be[(be.fuel == "hydrogen")
             & (be.carbon_case == "neutral")].set_index("country")
    py = pd.read_csv(inputs.MAPS / "parity_years.csv").set_index("country")

    from .coreset import core_countries, core_type
    from .fig5a_chain import q_h2
    QH = q_h2()
    EX = core_countries(py.index)                    # the core 30
    rows = []
    for c in EX:
        if c not in si.index or c not in py.index:
            continue
        q = float(QH.get(c, 0.0))            # hydrogen feedstock chain
        ics = si.loc[c, "pi_h2_usd_gj"] / q * UMM if q > 0 else np.inf
        # net exporters have no marginal import to protect: no ICS
        ics_s = f"{ics:,.0f}" if np.isfinite(ics) else "--"
        tau = max(0.0, beh.tau_star_usd_t.get(c, np.nan))
        rows.append(
            f"{SHORT.get(c, c)} & {v.V.get(c, np.nan):.2f} & "
            f"{si.loc[c, 'esd_gdp_pct']:.2f} & {ics_s} & "
            + (f"{tau:.0f}" if np.isfinite(tau) else "--") + " & "
            f"{yr(py.loc[c, 'sec'])} & {yr(py.loc[c, 'cost'])}")
    header = (" & & ESD & ICS & $" + BS + "tau^{*}$ & "
              + BS + "multicolumn{2}{c}{parity year} " + EOL + NL
              + BS + "cmidrule(l){6-7}" + NL
              + "Country & $V$ & (" + BS + "%" + BS + ",GDP) & ("
              + BS + "$/MMBtu) & (" + BS + "$/t) & security & "
              + "cost " + EOL)
    # the oil-stock column is gone: the backstop is valued on its gas/coal
    # feedstock chain, which strategic oil stocks do not cover, so it
    # repeated the security column row for row
    (TEXDIR / "tab_cases.tex").write_text(
        wrap("@{}l r r r r c c@{}", header, rows), encoding="utf-8")

    # ---- (appendix parity-50 table retired: main table now lists all 30) --
    return
    # ---- Table: parity years, all 50 core economies -----------------------
    py50 = py.sort_values(["sec", "cost"])
    rows = []
    for c, r in py50.iterrows():
        if r.cost < 2051:
            lead_s = f"{r.cost - r.sec:.0f}"
        else:
            lead_s = f"$>${2050 - r.sec:.0f}"
        nm = SHORT.get(c, c) + ("$^{" + BS + "dagger}$" if r.is_case
                                else "")
        rows.append(f"{nm} & {yr(r.sec)} & {yr(r.sec_res)} & "
                    f"{yr(r.cost)} & {lead_s}")
    half = (len(rows) + 1) // 2
    left, right = rows[:half], rows[half:]
    right += [" & & & & "] * (len(left) - len(right))
    merged = [f"{l} & {r}" for l, r in zip(left, right)]
    header = ("Country & Sec. & net stocks & Cost & Lead & "
              "Country & Sec. & net stocks & Cost & Lead " + EOL)
    (TEXDIR / "tab_parity50.tex").write_text(
        wrap("@{}l c c c c l c c c c@{}", header, merged),
        encoding="utf-8")

    print(f"wrote tab_reco ({len(st)}), tab_cases ({len(EX)}), "
          f"tab_parity50 ({len(py50)} countries) -> {TEXDIR}")


if __name__ == "__main__":
    main()
