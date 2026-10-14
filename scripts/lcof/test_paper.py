"""
test_paper.py -- regression test for the numbers the V1.8 manuscript quotes (2026-10-13).

The older test_regression.py locks the 2026-10-07 headline set on the legacy data/cost basis (parity
clock, vulnerability index, fixed-design layer), which the paper no longer reports. Since the 2026-10-08
reframe the paper reads its numbers from the case sandboxes in work/caselow:
  2025mid           Figs 1-3 (2025 central costs) and the "at current costs" statements
  2030, 2040, 2050  Figs 4 and 5 (lowest-tier costs)
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
    k99 = int((a.best_med_mmbtu <= a.crisis_p99_mmbtu).sum())
    below_med = sorted(a.country[a.best_med_mmbtu <= a.crisis_med_mmbtu])
    check("below disruption p99 in 26 of 30", k99 == 26, f"{k99}")
    check("below disruption median in 6 (CN, US, DE, BR, CL, NO)",
          below_med == sorted(["China", "United States of America", "Germany", "Brazil", "Chile", "Norway"]), f"{below_med}")
    bills = a.set_index("country").quiet_bill_bn_usd
    check("ammonia markets China 30, India 18, US 15, median 0.6 (US$ bn)",
          round(bills["China"]) == 30 and round(bills["India"]) == 18 and round(bills["United States of America"]) == 15
          and round(bills.median(), 1) == 0.6, f"{bills['China']:.1f}, {bills['India']:.1f}, "
          f"{bills['United States of America']:.1f}, {bills.median():.2f}")
    ft = sites("2025mid", "ft")
    check("diesel and jet build/normal 3.68, below p99 only in China",
          near((ft.best_med_mmbtu / ft.quiet_med_mmbtu).median(), 3.68, 0.005)
          and sorted(ft.country[ft.best_med_mmbtu <= ft.crisis_p99_mmbtu]) == ["China"])

    print("Fig. 4a (justified portfolios, security margin):")
    for case, n_just, gt100, gt200 in (("2025mid", 1, None, None), ("2030", 8, 13, 7), ("2040", 11, 14, 7), ("2050", 15, 14, 7)):
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
    m = d.gross_usd_t - d.net_usd_t
    check("2030: Israel ~740, Ireland ~610 US$/t", near(m["Israel"], 740, 10) and near(m["Ireland"], 610, 10),
          f"{m['Israel']:.0f}, {m['Ireland']:.0f}")
    j30 = d[d.net_usd_t <= d.p_co2_usd_t]
    check("2030: six by security alone, UK and Poland with carbon",
          int((j30.net_usd_t <= 0).sum()) == 6 and sorted(j30.index[j30.net_usd_t > 0]) == ["Poland", "United Kingdom"])
    d25 = chain("2025mid")
    gap = d25.net_usd_t - d25.p_co2_usd_t
    check("2025: Netherlands and Germany short by ~22 and ~46 US$/t",
          round(gap["Netherlands"]) == 22 and round(gap["Germany"]) == 46, f"{gap['Netherlands']:.1f}, {gap['Germany']:.1f}")

    print("Fig. 4b (CO2 displaced, Gt/yr):")
    for case, sec, cost in (("2030", 0.55, 0.27), ("2040", 1.24, 0.78), ("2050", 1.88, 1.19)):
        t = pd.read_csv(W / case / "data" / "fig5b_chain_trajectory.csv").set_index("year").loc[2025]
        check(f"{case}: {sec} with security, {cost} on cost alone",
              near(t.sec_gt, sec, 0.005) and near(t.cost_gt, cost, 0.005), f"{t.sec_gt:.3f}, {t.cost_gt:.3f}")

    print("Fig. 5 (1-3% of GDP, land):")
    for case, med, cov, land, bud in (("2030", 22, (2, 5, 6), 16, 4), ("2040", 26, None, None, 1), ("2050", 43, (7, 10, 11), None, 0)):
        d = budget(case)
        cv, nl, nb = groups(d)
        ok = round(100 * d.cov_1.median()) == med and nb == bud
        ok &= cov is None or (cv[1], cv[2], cv[3]) == cov
        ok &= land is None or nl == land
        check(f"{case}: median {med}%, covered {cov}, land-limited {land}, budget-limited {bud}", ok,
              f"{100 * d.cov_1.median():.1f}%, {cv}, {nl}, {nb}")

    print()
    if FAIL:
        print(f"PAPER CHECK FAILURES ({len(FAIL)}): " + "; ".join(FAIL))
        sys.exit(1)
    print("ALL PAPER CHECKS PASSED")


if __name__ == "__main__":
    main()
