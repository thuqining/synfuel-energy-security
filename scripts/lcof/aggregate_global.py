"""
aggregate_global.py — combine the 20 per-year LCOH sweeps into the global
LCOF product: per-cell statistics for the 10 routes + heatmaps.

MAINLINE = regional CAPEX ("_reg" files), battery on, industrial CO2 map only.
Set SUFFIX = "" to aggregate the uniform-CAPEX sensitivity instead.

Statistics per cell and route:
  mean   : average over the 20 weather years
  firm   : max over years  (binding-year design cost; validated joint-LP proxy)
  cv     : std/mean of the per-year values (design-year investment risk)
  ci95_lo/hi : bootstrap 95% CI of the mean (1000 resamples)

Outputs:
  data/cost/lcof_global_stats<SUFFIX>.csv
  cf_global_final/figures/heatmap_lcof_{firm,cv}_<fuel>.png + heatmap_lcoh_firm.png

From scripts/:  conda run -n synfuel python -u -m lcof.aggregate_global
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import inputs, params as P

YEARS = list(range(2006, 2026))
RNG = np.random.default_rng(42)
NBOOT = 1000
SUFFIX = "_reg"          # regional mainline; "" = uniform-CAPEX sensitivity


def load_years():
    frames = {}
    for yr in YEARS:
        f = inputs.MAPS / f"lcoh_global_{yr}{SUFFIX}.csv"
        df = pd.read_csv(f).set_index("cell_id")
        bad = (df.status != "ok").sum()
        if bad:
            print(f"[{yr}] WARNING {bad} failed cells")
        frames[yr] = df
    return frames


def main():
    meta = inputs.load_meta(2025)
    frames = load_years()
    cells = frames[YEARS[0]].index
    lcoh = np.column_stack([frames[y].loc[cells, "lcoh_usd_gj"] for y in YEARS])
    lcoe = np.column_stack([frames[y].loc[cells, "lcoe_usd_mwh"] for y in YEARS]) / 3.6

    co2_cell = meta.loc[cells, "co2_cost"].to_numpy(float)
    wacc = meta.loc[cells, "wacc"].to_numpy(float)
    syn_loc = (meta.loc[cells, "syn_loc"].fillna(1.0).to_numpy(float)
               if "syn_loc" in meta.columns else np.ones(len(cells)))

    def syn_cost(f, w):
        a = (P.crf(w, f["syn_life"]) + f["syn_opex"]) * f["syn_capex"]
        return a / (P.CF_SYN * 8760 * 3.6)

    rows = []
    routes = dict(P.FUELS)
    routes.update(P.ALT_ROUTES)          # alternative routes: same LCOH field
    for fuel, f in routes.items():
        # synthesis CAPEX x per-country EPC location factor
        syn = np.array([syn_cost(f, w) for w in wacc]) * syn_loc
        # MAINLINE = industrial CO2 map ONLY (2026-08-08); the climate-
        # neutral map is a separate scenario, never mixed into these outputs
        for case in ("industrial",):
            c_co2 = np.where(np.isfinite(co2_cell), co2_cell, P.C_CO2_DAC)
            lcof = (lcoh / f["eta_syn"]
                    + (f["mu_co2"] * c_co2 + f["mu_n2"] * P.C_N2_DEFAULT
                       + syn)[:, None]
                    + f["mu_el"] * lcoe)                       # (cells, years)
            mean = lcof.mean(axis=1)
            firm = lcof.max(axis=1)
            cv = lcof.std(axis=1) / mean
            idx = RNG.integers(0, len(YEARS), size=(NBOOT, len(YEARS)))
            boots = lcof[:, idx].mean(axis=2)                  # (cells, NBOOT)
            lo, hi = np.percentile(boots, [2.5, 97.5], axis=1)
            rows.append(pd.DataFrame({
                "cell_id": cells, "fuel": fuel, "carbon_case": case,
                "lcof_mean_gj": mean, "lcof_firm_gj": firm, "cv": cv,
                "ci95_lo": lo, "ci95_hi": hi,
                "lcof_firm_mmbtu": firm * P.MMBTU_PER_GJ}))
        print(f"aggregated {fuel}", flush=True)
    out = pd.concat(rows, ignore_index=True)
    out.to_csv(inputs.MAPS / f"lcof_global_stats{SUFFIX}.csv", index=False)
    print(f"wrote lcof_global_stats{SUFFIX}.csv", len(out), "rows")

    # ---- heatmaps ----
    import sys
    sys.path.insert(0, str(inputs.PROJECT / "cf_global_final" / "python"))
    import plot_style as ps
    import os
    # sandbox runs (lcof.case_low) set LCOF_FIG_DIR so the project heatmaps are not overwritten
    FIGS = Path(os.environ["LCOF_FIG_DIR"]) if os.environ.get("LCOF_FIG_DIR") else inputs.PROJECT / "cf_global_final" / "figures"
    ind = out[out.carbon_case == "industrial"]
    h = pd.Series(np.max(lcoh, axis=1), index=cells)
    ps.render_map(h.to_dict(), "Firm-supply LCOH, binding weather year (2006–25)",
                  "LCOH ($/GJ)", cmap="YlGnBu_r", vmin=15, vmax=60,
                  out=FIGS / "heatmap_lcoh_firm.png")
    for fuel in P.FUELS:
        sub = ind[ind.fuel == fuel].set_index("cell_id")
        vmax = float(sub.lcof_firm_gj.quantile(0.95))
        ps.render_map(sub.lcof_firm_gj.to_dict(),
                      f"Firm-supply LCOF — {fuel} (binding year, industrial CO2)",
                      "LCOF ($/GJ)", cmap="YlGnBu_r",
                      vmin=float(sub.lcof_firm_gj.quantile(0.02)), vmax=vmax,
                      out=FIGS / f"heatmap_lcof_firm_{fuel}.png")
        ps.render_map(sub.cv.to_dict(),
                      f"Interannual variability (CV) — {fuel}",
                      "CV of annual LCOF", cmap="YlOrRd", vmin=0, vmax=0.10,
                      out=FIGS / f"heatmap_lcof_cv_{fuel}.png")
    print("heatmaps done")


if __name__ == "__main__":
    main()
