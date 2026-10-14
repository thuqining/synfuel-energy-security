"""
sens_summary.py -- Supplementary Tables tab:drivers, tab:minload and tab:battery from the optimization-based
sensitivity runs (work/sens_results/out/<variant>/part_*.csv, written by work/sens_pkg/sens_flex.py: every land
cell at its median weather year, 2025 central costs, the same linear program as the main runs) and the main
2025 central runs (data/cost/flexlow/run_2025mid).

Cost metric: the cost of hydrogen and synthesis plant per unit of ammonia, lcoh / eta_ammonia + syn_gj (US$/GJ).

From scripts/:  python -m lcof.sens_summary
"""
from __future__ import annotations

import glob

import numpy as np
import pandas as pd

from . import inputs

S = inputs.PROJECT / "work" / "sens_results" / "out"
ETA_NH3 = 0.86          # hydrogen-to-ammonia energy efficiency (Supplementary Table tab:stoich)


def load(variant):
    d = pd.concat(pd.read_csv(f) for f in glob.glob(str(S / variant / "part_*.csv")))
    d = d.drop_duplicates("cell_id").set_index("cell_id")
    d["cost"] = d.lcoh / ETA_NH3 + d.syn_gj
    return d


def change(var, base):
    j = base.join(var, rsuffix="_v", how="inner")
    j = j[np.isfinite(j.cost_v) & np.isfinite(j.cost) & (j.cost > 0)]
    r = 100 * (j.cost_v / j.cost - 1)
    return r.median(), r.quantile(0.1), r.quantile(0.9), len(r)


def fmt(m, lo, hi):
    return f"{m:+.1f}% ({lo:+.1f} to {hi:+.1f})"


def main():
    base = load("base")
    print(f"base: {len(base)} cells; hydrogen store median {base.sto_h.median():.0f} h; "
          f"synthesis plant x{base.cs.median():.2f}")
    print("\nTable tab:drivers (x0.7 / x1.3; efficiency x1.1 / x0.9)")
    for lab, lo, hi in (("Electrolyzer capital cost", "ez_x0.7", "ez_x1.3"),
                        ("Electrolyzer efficiency", "eta_x1.1", "eta_x0.9"),
                        ("Solar capital cost", "pv_x0.7", "pv_x1.3"),
                        ("Wind capital cost", "wind_x0.7", "wind_x1.3"),
                        ("Synthesis plant cost", "syn_x0.7", "syn_x1.3"),
                        ("Battery cost", "battery_x0.7", "battery_x1.3"),
                        ("Hydrogen storage cost", "tank_x0.7", "tank_x1.3")):
        a, b = change(load(lo), base), change(load(hi), base)
        print(f"  {lab:28s} {fmt(*a[:3]):28s} {fmt(*b[:3])}")
    m, lo, hi, _ = change(load("all_x0.6"), base)
    print(f"  all hydrogen system capital costs x0.6: {fmt(m, lo, hi)}")

    print("\nTable tab:minload (minimum load / ramp limit)")
    for v, lab in (("min100", "100% (constant load)"), ("min80", "80%"), ("base", "60% (main case)"),
                   ("min40", "40%"), ("min20", "20%"), ("min00", "0%")):
        d = load(v)
        c = change(d, base) if v != "base" else (0, 0, 0, len(d))
        print(f"  {lab:22s} {fmt(*c[:3]) if v != 'base' else '---':28s} store {d.sto_h.median():4.0f} h  "
              f"plant x{d.cs.median():.2f}  cells {c[3]}")
    ramps = [change(load(v), base)[0] for v in ("ramp01", "ramp02", "ramp10", "ramp20", "ramp100")]
    print(f"  60%, other ramp limits: largest median change {max(ramps, key=abs):+.2f}%")

    print("\nTable tab:battery (main 2025 central runs, all cell-years)")
    runs = pd.concat(pd.read_csv(f) for f in glob.glob(str(inputs.PROJECT / "data" / "cost" / "flexlow" /
                                                             "run_2025mid" / "out" / "part_*.csv")))
    runs.columns = [c.replace("_flex60_ammonia", "") for c in runs.columns]
    built = runs.cap_bat_MW > 0.01
    print(f"  cell-years with a battery: {int(built.sum()):,} of {len(runs):,} ({100 * built.mean():.0f}%)")
    print(f"  battery power where built, median {runs.cap_bat_MW[built].median():.1f} MW; energy "
          f"{runs.cap_bat_MWh[built].median():.1f} MWh; duration {(runs.cap_bat_MWh / runs.cap_bat_MW)[built].median():.1f} h")
    print(f"  hydrogen store, median over all cell-years {runs.sto_h.median():.0f} h")


if __name__ == "__main__":
    main()
