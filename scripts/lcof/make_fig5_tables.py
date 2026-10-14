"""
make_fig5_tables.py — the Supplementary tables behind the fuel-chain
Figure 5a (2026-09-25):

  tab_fig5a.tex     per economy: chain import share, retired share, fuel mix
                    of the security portfolio, CO2, gross and net cost per
                    tonne, security value per tonne, carbon price
  tab_chainq.tex    per economy: chain exposure e and disruption probability
                    q for the ammonia, gas, oil and hydrogen chains, and the
                    higher value of disrupted fuel
  tab_fig5sens.tex  the sensitivity scenarios of fig5a_sens

From scripts/:  conda run -n synfuel python -u -m lcof.make_fig5_tables
"""
from __future__ import annotations

import pandas as pd

from . import inputs

TEX = inputs.MAPS.parent.parent / "synthetic_fuel_nature"
BS = chr(92)
EOL = " " + BS + BS
SHORT = {"United States of America": "United States", "Dominican Republic": "Dominican Rep.",
         "United Kingdom": "United Kingdom"}
MIX = {"ammonia": "A", "methanol": "M", "e-methane": "G", "e-diesel": "D",
       "e-kerosene": "K", "ethanol": "E", "marine": "S"}   # S: marine fuel (2026-10-07)


def num(x, fmt="{:.0f}"):
    """a number for LaTeX, with a proper minus sign"""
    if pd.isna(x):
        return "--"
    t = fmt.format(x)
    return "$-$" + t[1:] if t.startswith("-") else t


NAMES = {"main (2000-2026 events)": "Main case (2000--2026 events)",
         "1956-2026 catalogue": "Full 1956--2026 event record",
         "2000-2026 rates, full-record durations": "2000--2026 rates, 1956--2026 durations",
         "event rates x2": "Event rates at top of band ($" + chr(92) + "times$2)",
         "central value (ACER)": "Central valuation (ACER)",
         "budget 0.5%": "Budget 0.5" + chr(92) + "% of GDP",
         "budget 2%": "Budget 2" + chr(92) + "% of GDP",
         "budget 3%": "Budget 3" + chr(92) + "% of GDP",
         "cheapest-first fill": "Lowest-premium fill",
         "imports-first order": "Imports-first order",
         "security-justified only": "Security-justified tranche only"}


def _tab(cols, header, rows):
    return (BS + "begin{tabular}{@{}" + cols + "@{}}" + BS + "toprule\n" + header + EOL + "\n"
            + BS + "midrule\n" + "\n".join(r + EOL for r in rows) + "\n" + BS + "bottomrule\n"
            + BS + "end{tabular}\n")


def main():
    d = pd.read_csv(inputs.MAPS / "fig5a_chain.csv", index_col=0)
    sb = pd.read_csv(inputs.MAPS / "security_budget.csv", index_col=0)
    si = pd.read_csv(inputs.MAPS / "security_index.csv", index_col=0)
    ch = pd.read_csv(inputs.MAPS / "chain_q.csv").set_index(["country", "fuel"])
    imp = sb.import_pct.reindex(d.index) > 0
    order = list(d[imp].sort_values("net_usd_t").index) + list(d[~imp].sort_values("net_usd_t").index)

    rows = []
    for c in order:
        r = d.loc[c]
        mix = ", ".join(f"{MIX[f]} {r[f'x_{f}_share'] * 100:.0f}" for f in MIX
                        if r[f"x_{f}_share"] >= 0.05)
        sv = r.gross_usd_t - r.net_usd_t
        rows.append(f"{SHORT.get(c, c)} & {num(r.chain_import_share * 100)} & "
                    f"{num(r.retired_share * 100)} & {mix} & {num(r.co2_mt, '{:.1f}')} & "
                    f"{num(r.gross_usd_t)} & {num(sv)} & {num(r.net_usd_t)} & {num(r.p_co2_usd_t)}")
    header = ("Economy & Chain imports & Retired & Portfolio mix & CO$_2$ & Gross & Security & Net & "
              "Carbon price" + EOL + "\n & (" + BS + "% of demand) & (" + BS + "%) & (" + BS
              + "% of output) & (Mt) & " + BS + "multicolumn{4}{c}{(US" + BS + "$ t$^{-1}$)}")
    (TEX / "tab_fig5a.tex").write_text(_tab("l r r l r r r r r", header, rows), encoding="utf-8")

    rows = []
    for c in order:
        g = lambda f, k: float(ch.loc[(c, f), k])
        rows.append(f"{SHORT.get(c, c)} & {si.codf_hi_usd_gj[c] * 1.0551:.0f} & "
                    f"{g('ammonia', 'e') * 100:.0f} & {g('ammonia', 'q'):.3f} & "
                    f"{g('e-methane', 'e') * 100:.0f} & {g('e-methane', 'q'):.3f} & "
                    f"{g('e-diesel', 'e') * 100:.0f} & {g('e-diesel', 'q'):.3f} & "
                    f"{g('hydrogen', 'e') * 100:.0f} & {g('hydrogen', 'q'):.3f}")
    header = (" & $v^{" + BS + "mathrm{hi}}_c$ & " + BS + "multicolumn{2}{c}{Ammonia} & "
              + BS + "multicolumn{2}{c}{Gas} & " + BS
              + "multicolumn{2}{c}{Oil} & " + BS
              + "multicolumn{2}{c}{Hydrogen}" + EOL + "\n"
              + BS + "cmidrule(lr){3-4}" + BS + "cmidrule(lr){5-6}" + BS + "cmidrule(lr){7-8}"
              + BS + "cmidrule(l){9-10}\nEconomy & (US" + BS + "$/MMBtu) & $e$ (" + BS + "%) & $q$ & $e$ ("
              + BS + "%) & $q$ & $e$ (" + BS + "%) & $q$ & $e$ (" + BS + "%) & $q$")
    (TEX / "tab_chainq.tex").write_text(_tab("l r r r r r r r r r", header, rows), encoding="utf-8")

    s = pd.read_csv(inputs.MAPS / "fig5a_chain_sensitivity.csv", index_col=0)
    rows = []
    for name, gall in s.groupby("scenario", sort=False):
        g = gall[sb.import_pct.reindex(gall.index) > 0]
        sh = ((g.gross_usd_t - g.net_usd_t) / g.gross_usd_t).median()
        n0 = int((g.net_usd_t <= 0).sum())
        nc = int((g.net_usd_t <= g.p_co2_usd_t).sum())
        rows.append(f"{NAMES.get(name, name)} & {n0} & {nc} & {num(g.gross_usd_t.median())} & "
                    f"{num(g.net_usd_t.median())} & {num(sh * 100)} & {num(gall.co2_mt.sum() / 1e3, '{:.2f}')}")
    header = ("Scenario & Net $" + BS + "le0$ & Net $" + BS + "le$ carbon price & Median gross & "
              "Median net & Security share & CO$_2$, 30 economies" + EOL + "\n & (of 26) & (of 26) & (US" + BS
              + "$ t$^{-1}$) & (US" + BS + "$ t$^{-1}$) & (" + BS + "% of premium) & (Gt yr$^{-1}$)")
    (TEX / "tab_fig5sens.tex").write_text(_tab("l r r r r r r", header, rows), encoding="utf-8")
    print(f"wrote tab_fig5a ({len(order)}), tab_chainq ({len(order)}), tab_fig5sens ({s.scenario.nunique()})")


if __name__ == "__main__":
    main()
