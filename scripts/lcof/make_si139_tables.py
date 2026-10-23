"""
make_si139_tables.py — Supplementary tables for all 139 economies (2026-10-22). The main Figs 3-5 show the 30
core economies and a map; the SI gives every economy's values, one longtable per figure, rows in alphabetical
order with each figure's group in a column.

  tab_fig3all.tex     Fig. 3: ammonia import share, bill, normal and disruption prices, domestic green ammonia
  tab_fig4all.tex     Fig. 4a: 1%-of-GDP portfolio at 2030 costs (mix, CO2, premium, margin, net) and the net
                      premium at 2040 and 2050 costs, first justified cost year
  tab_chainall.tex    chain inputs (value of lost fuel, e and q of the ammonia, gas and oil chains)
  tab_breakall.tex    break-even value of lost fuel for the 118 net importers at 2030 costs
  tab_budgetall.tex   Fig. 5 at 2030 costs: demand, imported share, land ceiling, made at home with 1-3% of GDP,
                      imports replaced at 1% under both spending orders, group
  tab_budgetyrs.tex   Fig. 5 at 2040 and 2050 costs: land ceiling, made at home with 1-3% of GDP, group

From scripts/:  python -m lcof.make_si139_tables <out dir>
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from lcof.fig4a_all import SHORT

R = Path(__file__).resolve().parents[2]
W = R / "work" / "caselow"
B = R / "console" / "build"
BS, EOL = chr(92), " " + chr(92) * 2
MIX = {"ammonia": "A", "methanol": "M", "e-methane": "G", "e-diesel": "D", "e-kerosene": "J", "ethanol": "E",
       "marine": "S"}
UMM = 1.055056
V_REF = 199.0                       # US$/MMBtu, the ENTSOG value the security margin is computed at
V_CEN = 23.0


CORE = set(pd.read_csv(W / "2030" / "data" / "fig5a_chain.csv", index_col=0).index)
# 2026-10-22 (user): the 30 core economies of the main figures come first, in bold
CORE_NOTE = " The 30 core economies of the main figures come first, in bold; the others follow in alphabetical order."


def nm(c):
    s = SHORT.get(c, c).replace("&", BS + "&")
    return BS + "textbf{" + s + "}" if c in CORE else s


def order(cs):
    """core economies first, then the rest, each alphabetical"""
    key = lambda c: SHORT.get(c, c).lower()
    return sorted([c for c in cs if c in CORE], key=key) + sorted([c for c in cs if c not in CORE], key=key)


def num(x, f="{:.0f}"):
    if x is None or not np.isfinite(x):
        return "--"
    s = f.format(x)
    if s.lstrip("-").strip("0.") == "":
        s = s.lstrip("-")
    return s.replace("-", "$-$", 1) if s.startswith("-") else s


def longtable(cols, head, rows, caption, label, short, ncol=None, note=CORE_NOTE):
    """caption on the first page, the header repeated on every page"""
    caption += note
    ncol = ncol or cols.count("l") + cols.count("r") + cols.count("c")
    out = [BS + "begin{longtable}{@{}" + cols + "@{}}",
           BS + "caption[" + short + "]{" + caption + "}" + BS + "label{" + label + "}" + EOL,
           BS + "toprule", head + EOL, BS + "midrule", BS + "endfirsthead",
           BS + "multicolumn{" + str(ncol) + "}{@{}l}{" + BS
           + "footnotesize" + BS + "textit{(continued)}}" + EOL, BS + "toprule", head + EOL, BS + "midrule",
           BS + "endhead", BS + "bottomrule", BS + "endlastfoot"]
    out += [r + EOL for r in rows]
    out.append(BS + "end{longtable}")
    return "\n".join(out) + "\n"


def console():
    t = (R / "console" / "index.html").read_text(encoding="utf-8")
    return json.JSONDecoder().raw_decode(t[t.index("const DATA=") + 11:])[0]["countries"]


def f5_group(s):
    """Fig. 5 groups (console/build_console.py): exporter, imports covered by the security-optimal program at
    3% of GDP, land binds, budget binds"""
    g = pd.Series("B", index=s.index)
    land = (s.cov_3 >= s.max_cov - 1e-6) & (s.max_cov < 1 - 1e-6)
    g[land] = "L"
    g[s.ret_sf_3 >= 0.995] = "C"
    g[s.import_pct <= 0] = "X"
    return g


def main(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    sb = {y: pd.read_csv(W / str(y) / "data" / "security_budget.csv", index_col=0) for y in (2030, 2040, 2050)}
    econ = order(sb[2030].index)
    si = pd.read_csv(W / "2030" / "data" / "security_index.csv", index_col=0)
    a = {y: pd.read_csv(B / f"fig4a_all_{y}.csv", index_col=0) for y in (2030, 2040, 2050)}
    C = console()

    # ---- country inputs and hydrogen costs (tab:country) -----------------------------------------------------
    from lcof import inputs
    meta = inputs.load_meta(2025)
    land = meta[meta.cell_type == "land"][["country"]]

    def h2(case):
        fr = [pd.read_csv(W / case / "data" / f"lcoh_global_{y}_reg.csv").set_index("cell_id")[
            ["lcoh_usd_gj", "lcoh_usd_kg"]] for y in range(2006, 2026)]
        return pd.concat(fr).groupby(level=0).median().join(land, how="inner")
    h25, h30 = h2("2025mid"), h2("2030")
    wacc = pd.read_csv(W / "2025mid" / "data" / "wacc_by_country.csv").set_index("country")
    capx = pd.read_csv(W / "2025mid" / "data" / "capex_by_country_2025mid.csv").set_index("country")
    hh = lambda g, kg: f"{g * UMM:.0f} ({kg:.1f})"
    rows = []
    for c in econ:
        a25, a30 = h25[h25.country == c], h30[h30.country == c]
        star = "" if str(wacc.wacc_source.get(c, "")) == "damodaran" else "$^{*}$"
        k = capx.loc[c]
        rows.append(f"{nm(c)} & {wacc.wacc_pct[c]:.1f}{star} & {k.pv_capex_usd_kw:,.0f} & {k.wind_capex_usd_kw:,.0f} & "
                    f"{k.electrolyser_capex_usd_kw:,.0f} & {k.syn_location_factor:.2f} & "
                    f"{hh(a25.lcoh_usd_gj.min(), a25.lcoh_usd_kg.min())} & "
                    f"{hh(a25.lcoh_usd_gj.median(), a25.lcoh_usd_kg.median())} & "
                    f"{hh(a30.lcoh_usd_gj.min(), a30.lcoh_usd_kg.min())}")
    head = (" & Cost of & " + BS + "multicolumn{3}{c}{Capital cost (US" + BS + "$" + BS + ",kW$^{-1}$)} & Location & "
            + BS + "multicolumn{3}{c}{Hydrogen, US" + BS + "$" + BS + ",MMBtu$^{-1}$ (US" + BS + "$" + BS
            + ",kg$^{-1}$)}" + EOL + "\n" + BS + "cmidrule(lr){3-5}" + BS + "cmidrule(l){7-9}\n"
            + " & capital & & & & & " + BS + "multicolumn{2}{c}{2025} & 2030" + EOL + "\n"
            + "Economy & (" + BS + "%) & Solar & Wind & Electrolyzer & factor & Cheapest & Median & Cheapest")
    capt = ("Country inputs and hydrogen costs for all 139 economies. Cost of capital: 4.0" + BS + "% plus the "
            "Damodaran country risk premium, and $^{*}$ marks a value assigned by sovereign rating tier. Capital "
            "costs are the 2025 central layer. The location factor is our assumption of construction costs relative "
            "to the United States (1.00); it scales the synthesis plant cost and the installation share of the "
            "hydrogen tank cost. Hydrogen costs are the medians over the 20 weather years of the economy's cheapest "
            "and median land cells at 2025 central costs, and of the cheapest cell at the lowest 2030 costs.")
    (out / "tab_country.tex").write_text(
        BS + "begingroup" + BS + "footnotesize" + BS + "setlength{" + BS + "tabcolsep}{1.8pt}\n"
        + longtable("lrrrrrrrr", head, rows, capt, "tab:country", "Country inputs and hydrogen costs, all economies")
        + BS + "endgroup\n", encoding="utf-8")
    print("tab_country", len(rows), "tier-assigned:", sum("$^{*}$" in r.split("&")[1] for r in rows))

    # ---- Fig. 3 -------------------------------------------------------------------------------------------
    pr = pd.read_csv(B / "fig3_prices_ammonia.csv").set_index("country")
    box = pd.read_csv(B / "fuel_box_2025.csv")
    box = box[box.fuel == "ammonia"].set_index("country")
    gdp25 = si.gdp_usd                                       # 2025 GDP (Fig. 3 describes today)
    rows, cls = [], {}
    for c in econ:
        e = C.get(c, {}).get("E_amm")
        p = pr.loc[c] if c in pr.index else None
        b = box.loc[c] if c in box.index else None
        if p is None or b is None:
            continue
        k = "X" if (e is None or e <= 0) else ("M" if b.p50 <= p.disruption_p50 else ("P" if b.p50 <= p.disruption_p90 else "A"))
        cls[k] = cls.get(k, 0) + 1
        own = "" if p.own_share > 0 else "$^{*}$"
        rows.append(f"{nm(c)}{own} & {num((e or 0) * 100)} & {num(p.bill_bn_usd * 1e9 / gdp25[c] * 1e3, '{:.1f}')} & "
                    f"{num(p.normal_p50, '{:.1f}')} & {num(p.disruption_p50, '{:.1f}')} & {num(p.disruption_p90, '{:.1f}')} & "
                    f"{num(b.p50, '{:.1f}')} & {num(b.p25, '{:.1f}')}--{num(b.p75, '{:.1f}')} & {k}")
    head = (" & Import & Bill & " + BS + "multicolumn{3}{c}{Fossil ammonia} & " + BS
            + "multicolumn{2}{c}{Green ammonia} & " + EOL + "\n" + BS + "cmidrule(lr){4-6}" + BS + "cmidrule(lr){7-8}\n"
            + "Economy & share (" + BS + "%) & (" + BS + "textperthousand{} GDP) & Normal & Disruption & "
            + "90th pct. & Median & IQR & Class")
    cap = ("Values behind Fig.~" + BS + "ref{fig:cities} for all 139 economies, in 2025 US" + BS + "$ per MMBtu "
           "(lower heating value). Import share: import share of the ammonia supply chain, $E_c$. Bill: annual "
           "ammonia expenditure at normal prices as a share of 2025 GDP. Fossil ammonia: medians of the matched "
           "national price in normal months and in disruption months, and the 90th percentile in disruption months. "
           "Green ammonia: production cost in the economy's lowest-cost cell at 2025 central equipment costs, "
           "including delivery, median and interquartile range across 20 weather years. Class (map of Fig.~" + BS
           + "ref{fig:cities}b): M, below the median disruption price; P, between the median and the 90th percentile; A, "
           "above the 90th percentile; X, net exporter of the ammonia chain ($E_c=0$: no net imports of nitrogen "
           "products or of the gas or coal they are made from). $^{*}$No own import price series (regional urea-implied price or administered "
           "gas-based cost).")
    (out / "tab_fig3all.tex").write_text(
        BS + "begingroup" + BS + "footnotesize" + BS + "setlength{" + BS + "tabcolsep}{3pt}\n"
        + longtable("lrrrrrrrc", head, rows, cap, "tab:fig3all", "Ammonia prices and costs, all economies")
        + BS + "endgroup\n", encoding="utf-8")
    print("tab_fig3all", len(rows), cls)

    # ---- Fig. 4a ------------------------------------------------------------------------------------------
    imp = sb[2030].import_pct > 0
    first = {}
    for c in econ:
        if not imp.get(c, False):
            first[c] = "X"
            continue
        yrs = [y for y in (2030, 2040, 2050) if a[y].net_usd_t.get(c, np.inf) <= a[y].p_co2_usd_t.get(c, 0)]
        first[c] = str(yrs[0]) if yrs else "--"
    rows = []
    for c in econ:
        r = a[2030].loc[c]
        mix = " ".join(f"{MIX[f]}{r[f'x_{f}_share'] * 100:.0f}" for f in MIX if r.get(f"x_{f}_share", 0) >= 0.05)
        ret = num(r.retired_share * 100) if np.isfinite(r.retired_share) else "--"
        # 2026-10-22: a share below 0.5% prints as <1, not as a 0 beside a retired share
        ci = "$<$1" if 0 < r.chain_import_share * 100 < 0.5 else num(r.chain_import_share * 100)
        rows.append(f"{nm(c)} & {ci} & {ret} & {mix} & {num(r.co2_mt, '{:.1f}')} & "
                    f"{num(r.gross_usd_t)} & {num(r.gross_usd_t - r.net_usd_t)} & {num(r.net_usd_t)} & "
                    f"{num(a[2040].net_usd_t[c])} & {num(a[2050].net_usd_t[c])} & {num(r.p_co2_usd_t)} & {first[c]}")
    head = (" & Chain & & Portfolio mix & CO$_2$ & " + BS + "multicolumn{3}{c}{2030 costs} & " + BS
            + "multicolumn{2}{c}{Net premium} & Carbon & First" + EOL + "\n" + BS + "cmidrule(lr){6-8}" + BS
            + "cmidrule(lr){9-10}\n"
            + "Economy & imports (" + BS + "%) & Ret. (" + BS + "%) & (" + BS + "% of output) & (Mt) & Cost & "
            + "Margin & Net & 2040 & 2050 & price & year")
    cap = ("Values behind Fig.~" + BS + "ref{fig:co2}a for all 139 economies: the 1" + BS + "%-of-GDP merit order "
           "portfolio at 2030 costs in the lowest tier and its net premium at 2040 and 2050 costs, in US" + BS
           + "$ per tonne of CO$_2$ displaced. Chain imports are the chain-weighted net imports as a share of "
           "addressable demand, and retired is the share of them the portfolio replaces. The portfolio mix gives "
           "the output share of ammonia (A), methanol (M), e-methane (G), e-diesel (D), e-jet fuel (J), ethanol "
           "(E) and the marine fuel (S) of 5" + BS + "% or more. Cost: cost premium (support spent divided by the "
           "CO$_2$ displaced); margin: security margin; net: their difference. The portfolio is justified when the "
           "net premium does not exceed the carbon price in force; first year gives the earliest cost year "
           "at which it is (X, net exporter; --, not justified by 2050).")
    (out / "tab_fig4all.tex").write_text(
        BS + "begingroup" + BS + "scriptsize" + BS + "setlength{" + BS + "tabcolsep}{1.6pt}\n"
        + longtable("lrrlrrrrrrrc", head, rows, cap,
                    "tab:fig4all", "Portfolios behind Fig.~4a, all economies", ncol=12)
        + BS + "endgroup\n", encoding="utf-8")
    print("tab_fig4all", len(rows), pd.Series(first).value_counts().to_dict())

    # ---- chain inputs ------------------------------------------------------------------------------------
    ch = pd.read_csv(W / "2030" / "data" / "chain_q.csv").set_index(["country", "fuel"])
    rows = []
    for c in econ:
        g = lambda f, k: float(ch.loc[(c, f), k]) if (c, f) in ch.index else np.nan
        rows.append(f"{nm(c)} & {num(si.codf_hi_usd_gj[c] * UMM)} & "
                    f"{num(g('ammonia', 'e') * 100)} & {num(g('ammonia', 'q'), '{:.3f}')} & "
                    f"{num(g('e-methane', 'e') * 100)} & {num(g('e-methane', 'q'), '{:.3f}')} & "
                    f"{num(g('e-diesel', 'e') * 100)} & {num(g('e-diesel', 'q'), '{:.3f}')}")
    head = (" & $v^{" + BS + "mathrm{hi}}_c$ & " + BS + "multicolumn{2}{c}{Ammonia} & " + BS
            + "multicolumn{2}{c}{Gas} & " + BS + "multicolumn{2}{c}{Oil}" + EOL + "\n" + BS + "cmidrule(lr){3-4}"
            + BS + "cmidrule(lr){5-6}" + BS + "cmidrule(l){7-8}\nEconomy & (US" + BS + "$" + BS
            + ",MMBtu$^{-1}$) & $e$ (" + BS + "%) & $q$ & $e$ (" + BS + "%) & $q$ & $e$ (" + BS + "%) & $q$")
    cap = ("Fuel chain inputs for all 139 economies at 2000--2026 event rates: the higher value of lost fuel "
           "$v^{" + BS + "mathrm{hi}}_c$ and, for each chain, the net-imported share $e$ and the expected share of "
           "a marginal import lost each year $q$. Gas covers e-methane and methanol, and oil covers e-diesel, "
           "e-jet fuel, ethanol and the marine fuel. The inputs do not depend on the cost year or tier.")
    (out / "tab_chainall.tex").write_text(
        BS + "begingroup" + BS + "footnotesize\n" + longtable("lrrrrrrr", head, rows, cap, "tab:chainall",
                                                              "Fuel chain inputs, all economies")
        + BS + "endgroup\n", encoding="utf-8")
    print("tab_chainall", len(rows))

    # ---- break-even value of lost fuel (importers) -----------------------------------------------------
    d = a[2030][a[2030].index.isin(sb[2030].index[imp])].copy()
    d["m"] = d.gross_usd_t - d.net_usd_t
    d["be"] = np.where(d.m > 0, (d.gross_usd_t - d.p_co2_usd_t) / d.m * V_REF, np.inf)
    d["core"] = ~d.index.isin(CORE)
    d = d.sort_values(["core", "be"])
    rows = [f"{nm(c)} & {num(r.gross_usd_t)} & {num(r.m)} & {num(r.p_co2_usd_t)} & "
            + (f"{max(r.be, 0):,.0f} & {max(r.be, 0) / V_CEN:,.1f}" if np.isfinite(r.be) else "-- & --")
            for c, r in d.iterrows()]
    n23, n85, n199 = int((d.be <= V_CEN).sum()), int((d.be <= 85).sum()), int((d.be <= V_REF).sum())
    head = (" & Cost & Security margin & Carbon & " + BS + "multicolumn{2}{c}{Break-even value of lost fuel}" + EOL
            + "\n" + BS + "cmidrule(l){5-6}\nEconomy & premium & at reference & price & US" + BS + "$" + BS
            + ",MMBtu$^{-1}$ & $" + BS + "times$ central value")
    cap = (f"Break-even value of lost fuel for the {len(d)} net importers among the 139 economies at 2030 costs "
           "in the lowest tier: the European reference value at which the security margin and the carbon price "
           "together cover the cost premium of the 1" + BS + "%-of-GDP portfolio (Supplementary Table~" + BS
           + "ref{tab:fig4all}): the cost premium less the carbon price, divided by the security margin at the reference "
           "value and multiplied by US" + BS + "$199" + BS + ",MMBtu$^{-1}$. Costs per tonne "
           "are in US" + BS + "$" + BS + f",tCO$_2^{{-1}}$. At the central value of US" + BS + "$23" + BS
           + f",MMBtu$^{{-1}}$ {n23} portfolios are justified, at US" + BS + "$85" + BS + f",MMBtu$^{{-1}}$ {n85} "
           f"and at the reference value {n199}. "
           + ("Economies whose portfolio retires no imports have no break-even value (--). "
              if not np.isfinite(d.be).all() else "")
           + "Within each block, rows are ordered by the break-even value.")
    (out / "tab_breakall.tex").write_text(
        BS + "begingroup" + BS + "footnotesize\n" + longtable("lrrrrr", head, rows, cap, "tab:breakall",
                                                              "Break-even value of lost fuel, all importers",
                                                              note=" The core economies come first, in bold.")
        + BS + "endgroup\n", encoding="utf-8")
    print("tab_breakall", len(rows), "counts at 23/85/199:", n23, n85, n199)

    # ---- Fig. 5 -------------------------------------------------------------------------------------------
    grp = {y: f5_group(sb[y]) for y in sb}
    s = sb[2030]
    rows = []
    for c in econ:
        r = s.loc[c]
        ex = r.import_pct <= 0
        p = lambda x: num(x * 100)
        rows.append(f"{nm(c)} & {r.dem_fuel_gj / UMM / 1e9:.2f} & {p(max(r.import_pct, 0))} & {p(r.max_cov)} & "
                    f"{p(r.cov_1)} & {p(r.cov_2)} & {p(r.cov_3)} & {'--' if ex else p(r.ret_1)} & "
                    f"{'--' if ex else p(r.ret_sf_1)} & {grp[2030][c]}")
    head = (" & Demand & Imported & Land & " + BS + "multicolumn{3}{c}{Made at home (" + BS + "%)} & " + BS
            + "multicolumn{2}{c}{Replaced at 1" + BS + "% (" + BS + "%)} & " + EOL + "\n" + BS + "cmidrule(lr){5-7}"
            + BS + "cmidrule(lr){8-9}\nEconomy & (bn MMBtu) & (" + BS + "%) & ceiling (" + BS + "%) & 1" + BS
            + "% & 2" + BS + "% & 3" + BS + "% & cost-first & security-optimal & Group")
    cap = ("Values behind Fig.~" + BS + "ref{fig:budget}a for all 139 economies at the lowest 2030 costs, with GDP "
           "projected to 2030. Demand: annual addressable demand. Imported: net-imported share of the oil and gas "
           "families. Land ceiling: the largest share of demand that the screened land can supply. Made at home: "
           "share of demand supplied domestically with 1" + BS + "%, 2" + BS + "% and 3" + BS + "% of GDP, filled "
           "in order of rising premium. Replaced at 1" + BS + "%: share of net imports replaced with 1" + BS + "% of "
           "GDP under the cost-first order and under the security-optimal program of equation~(" + BS
           + "ref{s:lp}). Group: C, imports covered; B, budget binds; L, land binds; X, net exporter.")
    (out / "tab_budgetall.tex").write_text(
        BS + "begingroup" + BS + "footnotesize" + BS + "setlength{" + BS + "tabcolsep}{2.6pt}\n"
        + longtable("lrrrrrrrrc", head, rows, cap, "tab:budgetall", "Budget and land limits at 2030 costs, all economies")
        + BS + "endgroup\n", encoding="utf-8")
    print("tab_budgetall", len(rows), grp[2030].value_counts().to_dict())

    rows = []
    for c in econ:
        cells = []
        for y in (2040, 2050):
            r = sb[y].loc[c]
            cells += [num(r.max_cov * 100), num(r.cov_1 * 100), num(r.cov_2 * 100), num(r.cov_3 * 100), grp[y][c]]
        rows.append(nm(c) + " & " + " & ".join(cells))
    head = (" & " + BS + "multicolumn{5}{c}{2040 costs} & " + BS + "multicolumn{5}{c}{2050 costs}" + EOL + "\n" + BS
            + "cmidrule(lr){2-6}" + BS + "cmidrule(l){7-11}\nEconomy & Land & 1" + BS + "% & 2" + BS + "% & 3" + BS
            + "% & Group & Land & 1" + BS + "% & 2" + BS + "% & 3" + BS + "% & Group")
    cap = ("Values behind Fig.~" + BS + "ref{fig:budget}b,c for all 139 economies at the lowest 2040 and 2050 "
           "costs, with GDP projected to each cost year: land ceiling and share of demand made at home with 1" + BS
           + "%, 2" + BS + "% and 3" + BS + "% of GDP (" + BS + "% of addressable demand), and the group as in "
           "Supplementary Table~" + BS + "ref{tab:budgetall}. Demand and imported shares are those of Supplementary "
           "Table~" + BS + "ref{tab:budgetall}.")
    (out / "tab_budgetyrs.tex").write_text(
        BS + "begingroup" + BS + "footnotesize\n" + longtable("lrrrrcrrrrc", head, rows, cap, "tab:budgetyrs",
                                                              "Budget and land limits at 2040 and 2050 costs, all economies")
        + BS + "endgroup\n", encoding="utf-8")
    print("tab_budgetyrs", len(rows), {y: grp[y].value_counts().to_dict() for y in (2040, 2050)})

    # 2026-10-22: the 139-economy tables replace the core-30 tables of the SI and keep their labels, so the
    # cross-references of the main text and the SI stay valid
    keep = {"tab:fig4all": "tab:fig5a", "tab:chainall": "tab:chainq", "tab:breakall": "tab:breakeven",
            "tab:budgetall": "tab:budget"}
    for f in out.glob("tab_*.tex"):
        t = f.read_text(encoding="utf-8")
        for a, b in keep.items():
            t = t.replace(a, b)
        f.write_text(t, encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1])
