"""
si_fig3_tables.py -- refresh SI Tables tab:fig3ammonia and tab:fig3ft (2026-10-07).

Rows come from make_fig3_tables (tab_fig3_ammonia.tex, tab_fig3_ft.tex); bills below
US$0.001 bn print as 0 (economies that use no ammonia directly), and the ammonia
table gains its two green-ammonia columns from core30_sites_ammonia.csv: the cost
ratio (lowest-cost domestic cell over the normal import price) and whether that cost
lies below the 99th percentile of disruption prices.

usage: python -m lcof.si_fig3_tables <supplementary.tex>
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from . import inputs

SFN = inputs.PROJECT / "synthetic_fuel_nature"
LONG = {"Dominican Rep.": "Dominican Republic", "United States": "United States of America"}


def rows(gen: Path, green: bool):
    # 2026-10-13: Fig. 3 tables written before the 1st-99th switch name the column crisis_p98_mmbtu
    s = pd.read_csv(inputs.MAPS / "core30_sites_ammonia.csv").rename(columns={"crisis_p98_mmbtu": "crisis_p99_mmbtu"}).set_index("country")
    out = []
    started = False
    for line in gen.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("\\midrule"):
            if started:                                  # importer / exporter divider
                out.append("\\midrule")
            started = True
            continue
        if not started or "&" not in line or "\\bottomrule" in line:
            continue
        cells = [c.strip() for c in line.rstrip("\\ ").split("&")]
        try:
            b = float(cells[8])                          # Bill, US$ bn
            if b < 0.001:
                cells[8] = "0"
        except ValueError:
            pass
        if green:
            c = LONG.get(cells[0], cells[0])
            r = s.loc[c]
            cells += [f"{r.best_med_mmbtu / r.quiet_med_mmbtu:.2f}",
                      "yes" if r.best_med_mmbtu <= r.crisis_p99_mmbtu else "no"]
        out.append(" & ".join(cells) + " \\\\")
    return out


def replace_body(t: str, label: str, new):
    a = t.index("\\label{" + label + "}")
    e = t.index("\\bottomrule", a)
    m = t.index("\\midrule", a) + len("\\midrule")      # the header rule
    return t[:m] + "\n" + "\n".join(new) + "\n" + t[e:]


def main(si: str):
    p = Path(si)
    t = p.read_text(encoding="utf-8")
    ra = rows(SFN / "tab_fig3_ammonia.tex", True)
    rf = rows(SFN / "tab_fig3_ft.tex", False)
    n = lambda rr: sum(1 for x in rr if x != "\\midrule")
    assert n(ra) == 30 and n(rf) == 30, (n(ra), n(rf))
    t = replace_body(t, "tab:fig3ammonia", ra)
    t = replace_body(t, "tab:fig3ft", rf)
    p.write_text(t, encoding="utf-8")
    print("tab:fig3ammonia and tab:fig3ft refreshed;", ra[0], "|", rf[0])


if __name__ == "__main__":
    main(sys.argv[1])
