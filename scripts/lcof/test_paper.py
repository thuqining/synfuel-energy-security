"""
test_paper.py -- regression test for the numbers the manuscript quotes (2026-10-13; expectations
updated 2026-10-22 for the value of lost fuel per unit of primary energy including biomass, GDP projected
to each cost year, the 90th-percentile tail test and the six-figure layout: Fig. 4 = security value per
tonne, Fig. 5 = abatement cost curves, Fig. 6 = budget and land at 2030 costs).

The older test_regression.py locks the 2026-10-07 headline set on the legacy data/cost basis (parity
clock, vulnerability index, fixed-design layer), which the paper no longer reports. Since the 2026-10-08
reframe the paper reads its numbers from the case sandboxes in work/caselow:
  2025mid           Figs 1-3 (2025 central costs) and the "at current costs" statements
  2030, 2040, 2050  Figs 4-6 (lowest-tier costs; Fig. 6 at 2030)
This test reads those sandboxes and checks every number the abstract and main text quote. Update an
expectation ONLY together with the text that quotes it.

From scripts/:  python -m lcof.test_paper
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .coreset import CORE30_LIST

W = Path(__file__).resolve().parents[2] / "work" / "caselow"
FAIL = []


def check(name, ok, detail=""):
    print(f"  [{'ok ' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))
    if not ok:
        FAIL.append(name)


def near(x, target, tol):
    return bool(np.isfinite(x) and abs(x - target) <= tol)


def sites(case, fuel):
    s = pd.read_csv(W / case / "data" / f"core30_sites_{fuel}.csv")
    return s.rename(columns={"crisis_p98_mmbtu": "crisis_p99_mmbtu"})


def chain(case):
    return pd.read_csv(W / case / "data" / "fig5a_chain.csv", index_col=0)


def budget(case):
    sb = pd.read_csv(W / case / "data" / "security_budget.csv", index_col=0)
    return sb.reindex([c for c in CORE30_LIST if c in sb.index])


def groups(d):
    imp = d.import_pct > 0
    cov = {b: int((imp & (d[f"ret_sf_{b}"] >= 0.995)).sum()) for b in (1, 2, 3)}
    covered = imp & (d.ret_sf_3 >= 0.995)
    land = imp & ~covered & (d.cov_3 >= d.max_cov - 1e-6) & (d.max_cov < 1 - 1e-6)
    return cov, int(land.sum()), int((imp & ~covered & ~land).sum())


def main():
    print("Fig. 2 (2025 central):")
    c = pd.read_csv(W / "2025mid" / "data" / "sd_map_classes.csv", index_col=0)
    bf = c[(c.s == 2) & (c.d == 2)]
    check("2,740 land cells", len(c) == 2740, f"{len(c)}")
    check("build-first 13% of cells, 45% of demand",
          round(100 * len(bf) / len(c)) == 13 and round(100 * bf.dem.sum() / c.dem.sum()) == 45,
          f"{len(bf) / len(c):.3f}, {bf.dem.sum() / c.dem.sum():.3f}")
    co = pd.read_csv(W / "2025mid" / "data" / "co2_cost_by_cell.csv")
    check("153 cells buy direct air capture", int((co.pathway == "DAC").sum()) == 153)

    print("Fig. 3 (2025 central):")
    a = sites("2025mid", "ammonia")
    r = a.best_med_mmbtu / a.quiet_med_mmbtu
    check("ammonia build/normal median 1.96 (IQR 1.73-2.69)",
          near(r.median(), 1.96, 0.005) and near(np.percentile(r, 25), 1.73, 0.005) and near(np.percentile(r, 75), 2.69, 0.005),
          f"{r.median():.2f} ({np.percentile(r, 25):.2f}-{np.percentile(r, 75):.2f})")
    below_med = sorted(a.country[a.best_med_mmbtu <= a.crisis_med_mmbtu])
    check("below disruption median in 6 (CN, US, DE, BR, CL, NO)",
          below_med == sorted(["China", "United States of America", "Germany", "Brazil", "Chile", "Norway"]), f"{below_med}")
    # 2026-10-22: the tail test is the 90th percentile (Fig. 3 whiskers 10th-90th), read as the figure reads it
    from .fig35_core import _data, core30, fig3_classes
    C, core = _data(), core30()
    amm = {c: C[c] for c in C if C[c].get("box", {}).get("ammonia") and C[c].get("pr", {}).get("amm")}
    p90 = {c for c, v in amm.items() if v["box"]["ammonia"][2] <= v["pr"]["amm"]["d"][4]}
    check("below disruption p90 in 26 of 30", len(p90 & core) == 26, f"{len(p90 & core)}")
    cat = fig3_classes()[0]
    imp_a = {c for c, k in cat.items() if k != "x"}
    check("139 economies: below p90 in 101, 87 of the 120 ammonia-chain importers",
          len(p90 & set(cat)) == 101 and len(p90 & imp_a) == 87 and len(imp_a) == 120,
          f"{len(p90 & set(cat))}, {len(p90 & imp_a)} of {len(imp_a)}")
    below_n = sorted(c for c, v in amm.items() if v["box"]["ammonia"][2] < v["pr"]["amm"]["n"][2])
    ratio_cn = amm["China"]["box"]["ammonia"][2] / amm["China"]["pr"]["amm"]["n"][2]
    check("China the only economy below the normal price, at 0.79", below_n == ["China"] and near(ratio_cn, 0.79, 0.005),
          f"{below_n}, {ratio_cn:.3f}")
    bills = a.set_index("country").quiet_bill_bn_usd
    check("ammonia markets China 31, India 18, US 15, median 0.6 (US$ bn)",
          round(bills["China"]) == 31 and round(bills["India"]) == 18 and round(bills["United States of America"]) == 15
          and round(bills.median(), 1) == 0.6, f"{bills['China']:.1f}, {bills['India']:.1f}, "
          f"{bills['United States of America']:.1f}, {bills.median():.2f}")
    ft = sites("2025mid", "ft")
    ft90 = [c for c in core if C.get(c, {}).get("pr", {}).get("ft") and C[c]["box"].get("e-diesel")
            and C[c]["box"]["e-diesel"][2] <= C[c]["pr"]["ft"]["d"][4]]
    check("diesel and jet build/normal 3.68, below p90 in none of the 30",
          near((ft.best_med_mmbtu / ft.quiet_med_mmbtu).median(), 3.68, 0.005) and not ft90, f"{ft90}")

    print("Fig. 4a (justified portfolios, security margin; 30 core economies):")
    for case, n_just, gt100, gt200 in (("2025mid", 2, None, None), ("2030", 8, 14, 5), ("2040", 9, 16, 5), ("2050", 13, 16, 6)):
        d = chain(case)
        sb = pd.read_csv(W / case / "data" / "security_budget.csv", index_col=0)
        imp = sb.import_pct.reindex(d.index) > 0
        just = sorted(d.index[d.net_usd_t <= d.p_co2_usd_t])
        check(f"{case}: {n_just} justified", len(just) == n_just, f"{len(just)} {just}")
        if gt100 is not None:
            m = (d.gross_usd_t - d.net_usd_t)[imp]
            check(f"{case}: margin > US$100 in {gt100}, > US$200 in {gt200}",
                  int((m > 100).sum()) == gt100 and int((m > 200).sum()) == gt200, f"{int((m > 100).sum())}, {int((m > 200).sum())}")
    d = chain("2030")
    j30 = d[d.net_usd_t <= d.p_co2_usd_t]
    check("2030: six by security alone, UK and Poland with carbon",
          int((j30.net_usd_t <= 0).sum()) == 6 and sorted(j30.index[j30.net_usd_t > 0]) == ["Poland", "United Kingdom"])
    d25 = chain("2025mid")
    gap = d25.net_usd_t - d25.p_co2_usd_t
    check("2025: Netherlands justified only with its carbon price, Germany short by ~13 US$/t",
          gap["Netherlands"] <= 0 < d25.net_usd_t["Netherlands"] and round(gap["Germany"]) == 13,
          f"{gap['Netherlands']:.1f}, {gap['Germany']:.1f}")

    print("Fig. 4b (first justified cost year; 139 economies):")
    from .fig4a_all import load
    data, imps, exps, first = load()
    yrs = pd.Series(first)
    m30 = (data[2030].gross_usd_t - data[2030].net_usd_t)[imps]
    check("118 net importers; margin > US$100 in 79, > US$200 in 38 at 2030 costs",
          len(imps) == 118 and int((m30 > 100).sum()) == 79 and int((m30 > 200).sum()) == 38,
          f"{len(imps)}, {int((m30 > 100).sum())}, {int((m30 > 200).sum())}")
    n = {y: int((yrs <= y).sum()) for y in (2030, 2040, 2050)}
    check("justified 18 / 29 / 43 at 2030 / 2040 / 2050 costs", (n[2030], n[2040], n[2050]) == (18, 29, 43), f"{n}")
    a25 = pd.read_csv(Path(__file__).resolve().parents[2] / "console" / "build" / "fig4a_all_2025mid.csv", index_col=0)
    j25 = sorted(a25.index[a25.net_usd_t <= a25.p_co2_usd_t])
    check("four at current costs (Cyprus, Ireland, Netherlands, Switzerland)",
          j25 == ["Cyprus", "Ireland", "Netherlands", "Switzerland"], f"{j25}")

    print("Fig. 5 (CO2 displaced, Gt/yr):")
    for case, sec, cost in (("2030", 0.85, 0.27), ("2040", 1.22, 0.79), ("2050", 1.86, 1.19)):
        t = pd.read_csv(W / case / "data" / "fig5b_chain_trajectory.csv").set_index("year").loc[2025]
        check(f"{case}: {sec} with security, {cost} on cost alone",
              near(t.sec_gt, sec, 0.005) and near(t.cost_gt, cost, 0.005), f"{t.sec_gt:.3f}, {t.cost_gt:.3f}")

    print("Fig. 6 (1-3% of GDP, land; 2030 costs):")
    d = budget("2030")
    cv, nl, nb = groups(d)
    check("30 economies: median 23%, covered at 1/2/3% by 3/5/6", round(100 * d.cov_1.median()) == 23
          and (cv[1], cv[2], cv[3]) == (3, 5, 6), f"{100 * d.cov_1.median():.1f}%, {cv}")
    from .fig35_core import fig5_classes
    g = pd.Series(fig5_classes("2030")[0]).value_counts().to_dict()
    check("139 economies: 32 covered, 42 budget-limited, 44 land-limited, 21 net exporters",
          (g.get("imports covered"), g.get("budget binds"), g.get("land binds"), g.get("net exporter")) == (32, 42, 44, 21),
          f"{g}")

    print()
    if FAIL:
        print(f"PAPER CHECK FAILURES ({len(FAIL)}): " + "; ".join(FAIL))
        sys.exit(1)
    print("ALL PAPER CHECKS PASSED")


if __name__ == "__main__":
    main()
