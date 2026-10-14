"""
audit_vintage.py — every check the projection has to pass, in one place.

Run after the vintage chain. Anything that fails here means a number in the
deck is wrong, so this is the gate before reporting.

From scripts/:  conda run -n synfuel python -u -m lcof.audit_vintage
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import inputs, params as P

YEARS = [2025, 2030, 2035, 2040, 2045, 2050]
CASES = ["Conservative", "Moderate", "Advanced"]
_fail = 0


def check(name, cond, detail=""):
    global _fail
    ok = bool(cond)
    _fail += (not ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def main():
    print("=" * 76)
    print("A. COVERAGE AND SOLVER")
    print("=" * 76)
    v = pd.read_csv(inputs.MAPS / "vintage_sites.csv")
    n_sites = v.cell_id.nunique()
    exp = n_sites * 20 * len(CASES) * len(YEARS)
    check("every job returned a row", len(v) == exp, f"{len(v):,} of {exp:,}")
    check("no solver failures", (v.status == "ok").all(),
          f"{int((v.status != 'ok').sum())} failures")
    check("all 20 weather years present", v.weather_year.nunique() == 20)
    check("all 6 vintages present", v.vintage.nunique() == len(YEARS))
    check("all 3 cases present", v.case.nunique() == len(CASES))

    print("\n" + "=" * 76)
    print("B. REGRESSION — the 2025 vintage must reproduce the mainline")
    print("=" * 76)
    ok = v[(v.status == "ok") & (v.vintage == 2025)]
    worst, worst_where = 0.0, ""
    for wy in sorted(ok.weather_year.unique()):
        main_df = pd.read_csv(inputs.MAPS / f"lcoh_global_{wy}_reg.csv",
                              index_col="cell_id")
        s = ok[ok.weather_year == wy]
        for cid, grp in s.groupby("cell_id"):
            if cid not in main_df.index or main_df.at[cid, "status"] != "ok":
                continue
            ref = float(main_df.at[cid, "lcoh_usd_kg"])
            e = float((grp.lcoh_usd_kg - ref).abs().max()) / ref * 100
            if e > worst:
                worst, worst_where = e, f"cell {cid}, year {wy}"
    check("2025 vintage == published mainline", worst < 1e-6,
          f"max |error| {worst:.2e} % ({worst_where or 'all match'})")

    print("\n" + "=" * 76)
    print("C. MONOTONICITY — every projected input improves")
    print("=" * 76)
    firm = (v[v.status == "ok"].groupby(["site", "case", "vintage"])
            .lcoh_usd_kg.max().unstack("vintage")[YEARS])
    rise = firm.diff(axis=1).iloc[:, 1:]
    bad = rise[(rise > 1e-9).any(axis=1)]
    check("hydrogen falls with every vintage", len(bad) == 0,
          f"{len(bad)} of {len(firm)} (site, case) pairs rise")

    f = pd.read_csv(inputs.MAPS / "vintage_fuels.csv")
    cfree = [k for k, x in P.FUELS.items() if x["mu_co2"] == 0]
    bad2 = []
    for (site, cs, ax, fuel), g in f.groupby(["site", "case", "co2_axis",
                                              "fuel"]):
        if fuel not in cfree:
            continue
        s = g.set_index("vintage").lcof_usd_mmbtu.reindex(YEARS)
        if (s.diff().dropna() > 1e-9).any():
            bad2.append((site, cs, ax, fuel))
    check(f"carbon-free fuels ({', '.join(cfree)}) never rise", not bad2,
          f"{len(bad2)} violations")

    carbon = [k for k in P.FUELS if k not in cfree]
    rises = []
    for (site, cs, ax, fuel), g in f.groupby(["site", "case", "co2_axis",
                                              "fuel"]):
        if fuel not in carbon:
            continue
        s = g.set_index("vintage").lcof_usd_mmbtu.reindex(YEARS)
        if (s.diff().dropna() > 1e-9).any():
            rises.append((site, cs, ax))
    axes = {a for _, _, a in rises}
    print(f"  [NOTE] carbon-bearing fuels rise in {len(rises)} combinations, "
          f"all on axis {axes or '—'} — this is the CO2-retirement prediction, "
          f"not an error")

    print("\n" + "=" * 76)
    print("D. INTERNAL CONSISTENCY")
    print("=" * 76)
    check("firm >= median for every site/case/vintage",
          bool((f.lcof_usd_mmbtu >= f.lcof_med_usd_mmbtu - 1e-9).all()),
          "the binding year cannot be cheaper than the typical year")
    tr = pd.read_csv(inputs.MAPS / "trajectory_index.csv")
    yc = [str(y) for y in YEARS]
    idx_only = tr[tr.tech != "eta_el"]
    check("no cost index exceeds 1", bool((idx_only[yc] <= 1 + 1e-9).all().all()))
    mono = []
    for t in idx_only.tech.unique():
        b = idx_only[idx_only.tech == t].set_index("case")
        for y in yc:
            vals = [float(b.at[c, y]) for c in CASES if c in b.index]
            if len(vals) == 3 and not (vals[0] >= vals[1] - 1e-9 >= vals[2] - 2e-9):
                mono.append((t, y))
    check("scenario ordering Conservative >= Moderate >= Advanced", not mono,
          f"{len(mono)} violations")
    eta = tr[tr.tech == "eta_el"]
    check("electrolyser efficiency below the thermodynamic ceiling",
          bool((eta[yc] <= 0.85).all().all()),
          f"max {float(eta[yc].max().max()):.3f}")

    print("\n" + "=" * 76)
    print("E. DECLARED, NOT ASSERTED")
    print("=" * 76)
    for t in ["ATB is a US dataset; the traded-component decline rate is "
              "assumed global",
              "the three cases are scenarios, not a confidence interval",
              "electrolyser 2035/2040/2045 are interpolated between sourced "
              "2030 and 2050 anchors",
              "the wind CF growth is a uniform +5.4 % scalar: it captures the "
              "mean, not the profile flattening",
              "electrolyser and battery country costs are procurement blocs, "
              "not observed per-country prices",
              "results are at the case SITES, several of which are demand "
              "centres rather than each country's best production site"]:
        print(f"  [NOTE] {t}")

    print("\n" + "=" * 76)
    print("ALL CHECKS PASSED" if _fail == 0 else f"{_fail} CHECK(S) FAILED")
    print("=" * 76)


if __name__ == "__main__":
    main()
