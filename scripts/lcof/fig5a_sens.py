"""
fig5a_sens.py — sensitivity of the chain-basis Figure 5a (for the SI).

Scenarios (all at 2025 costs, 30 core economies):
  main          1% of GDP, CoDF_hi, 2000-2026 event rates and durations,
                lowest premium first (Fig. 5's merit order; since 2026-10-02)
  imports first the same budget spent first on imported chains (the earlier
                security-first two-stage LP)
  window        the full 1956-2026 catalogue; 2000-2026 rates with
                full-record durations; rates x2
  budget        0.5%, 2%, 3% of GDP
  high rates    event rates x2 (the top of the catalogue band)
  central value CoDF (ACER) instead of CoDF_hi (ENTSOG)
  cheapest      the same budget filled cheapest-first (the Fig. 4 order)
  justified     build only where the chain security value covers the
                premium (max security value - spend, budget as cap):
                the zero-net-cost tranche

From scripts/:  conda run -n synfuel python -u -m lcof.fig5a_sens
Writes data/cost/fig5a_chain_sensitivity.csv (one row per scenario x economy)
and prints the summary.
"""
from __future__ import annotations

import pandas as pd

from . import inputs
from .fig5a_chain import compute, _setup
from .security import _scenario_rates


def _multipliers():
    """expected disrupted time (central rate x median duration) of each
    family relative to the main 2000-2026 window: the full 1956-2026
    record, and 2000-2026 rates with full-record durations"""
    main, _ = _scenario_rates()
    full, _ = _scenario_rates(1956)
    rate = {k: (v[0][0] * v[0][1]) ** 0.5 for k, v in main.items()}
    rate_f = {k: (v[0][0] * v[0][1]) ** 0.5 for k, v in full.items()}
    full_m = tuple(rate_f[k] * full[k][1] / (rate[k] * main[k][1]) for k in ("s1", "s2"))
    rate_only = tuple(full[k][1] / main[k][1] for k in ("s1", "s2"))
    return full_m, rate_only


FULL_1956, RATE_ONLY = _multipliers()
SCEN = [("main (2000-2026 events)", {}),
        ("1956-2026 catalogue", dict(rate=FULL_1956)),
        ("2000-2026 rates, full-record durations", dict(rate=RATE_ONLY)),
        ("event rates x2", dict(rate=2.0)),
        ("central value (ACER)", dict(value="central")),
        ("budget 0.5%", dict(budget_pct=0.5)), ("budget 2%", dict(budget_pct=2.0)),
        ("budget 3%", dict(budget_pct=3.0)),
        ("imports-first order", dict(mode="security")),
        ("security-justified only", dict(mode="justified"))]


def main():
    setup = _setup()
    sb = pd.read_csv(inputs.MAPS / "security_budget.csv", index_col=0)
    out, rows = [], []
    for name, kw in SCEN:
        d = compute(setup=setup, verbose=False, **kw)
        d["scenario"] = name
        out.append(d)
        imp = d[sb.import_pct.reindex(d.index) > 0]
        built = imp[imp.co2_mt > 0.01]
        rows.append(dict(
            scenario=name,
            importers_net_le0=int((imp.net_usd_t <= 0).sum()),
            importers_net_le_cprice=int((imp.net_usd_t <= imp.p_co2_usd_t).sum()),
            median_gross=float(imp.gross_usd_t.median()),
            median_net=float(imp.net_usd_t.median()),
            median_sec_share=float(((imp.gross_usd_t - imp.net_usd_t) / imp.gross_usd_t).median()),
            median_retired=float(imp.retired_share.median()),
            co2_mt=float(d.co2_mt.sum()),
            economies_building=int(len(built)),
            names_net_le0=", ".join(imp.index[imp.net_usd_t <= 0])))
    pd.concat(out).to_csv(inputs.MAPS / "fig5a_chain_sensitivity.csv")
    s = pd.DataFrame(rows).set_index("scenario")
    pd.set_option("display.width", 250)
    print(s.round(2).to_string())
    return s


if __name__ == "__main__":
    main()
