"""
make_tab_budget_si.py -- SI Table tab:budget from security_budget.csv (2026-10-07),
in the SI layout, with the groups of Fig. 5 (security_budget._figure): imports
covered (3% of GDP, spent on imported fuels first, retires all net imports), budget
binds, land binds (ceiling below full demand and reached within 3%), net exporters.

usage: python -m lcof.make_tab_budget_si <supplementary.tex>
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from . import inputs
from .coreset import core_countries

SHORT = {"United States of America": "United States", "Dominican Republic": "Dominican Rep."}
GROSS = {"Kenya", "Dominican Republic", "Madagascar"}


def main(si: str):
    sb = pd.read_csv(inputs.MAPS / "security_budget.csv", index_col=0)
    d = sb.loc[[c for c in core_countries(sb.index) if c in sb.index]].copy()
    is_x = d.import_pct <= 0.0
    covered = ~is_x & (d.ret_sf_3 >= 0.995)
    land = ~is_x & ~covered & (d.cov_3 >= d.max_cov - 1e-6) & (d.max_cov < 1 - 1e-6)
    budget = ~is_x & ~covered & ~land
    rows = []
    for g, lab in ((covered, "imports covered"), (budget, "budget binds"), (land, "land binds"),
                   (is_x, "net exporter")):
        for c in d[g].sort_values("cov_1", ascending=False).index:
            r = d.loc[c]
            name = SHORT.get(c, c) + ("$^{*}$" if c in GROSS else "")
            imp = f"{100 * r.import_pct:.0f}" if r.import_pct > 0 else "0"
            ret = (lambda v: "--" if r.import_pct <= 0 else f"{100 * min(v, 1):.0f}")
            rows.append(f"{name} & {r.dem_fuel_gj / 1.0551e9:.2f} & {imp} & {100 * r.max_cov:.0f} & "
                        f"{100 * r.cov_1:.0f} & {100 * r.cov_2:.0f} & {100 * r.cov_3:.0f} & "
                        f"{ret(r.ret_1)} & {ret(r.ret_sf_1)} & {lab} \\\\")
    p = Path(si)
    t = p.read_text(encoding="utf-8")
    a = t.index(r"\label{tab:budget}")
    e = t.index(r"\bottomrule", a)
    m = t.index(r"\midrule", a) + len(r"\midrule")
    t = t[:m] + "\n" + "\n".join(rows) + "\n" + t[e:]
    p.write_text(t, encoding="utf-8")
    print("\n".join(rows))
    for k in (1, 2, 3):
        print(f"retire all net imports with {k}% (security order):",
              list(d.index[~is_x & (d[f'ret_sf_{k}'] >= 0.995)]))


if __name__ == "__main__":
    main(sys.argv[1])
