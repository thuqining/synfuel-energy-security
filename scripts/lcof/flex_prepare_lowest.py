"""
flex_prepare_lowest.py — cost inputs for the 20-weather-year flexible-synthesis
runs of the lowest-cost case (2026-10-07): one costs_<year>.npz
per cost year, in the cell order of the weather-year profiles already on the
cluster (years/cells_<y>.npz of the flex60y job), for flex_worker.py --years.

Costs: data/cost/capex_by_country_<year>low.csv (lcof.capex_2030low) and the
year scalars in lowest_case_scalars.csv (electrolyser efficiency, synthesis
scale by fuel). Synthesis at the IEA GHR 2026 low end: Haber-Bosch 560 US$/(t/yr) ->
950 US$/kW; the other plants have single published values.

The archived 20-year flexible run (flex60_20yr_raw, 2026-09-25) showed the five
fuel-specific LPs give the same hydrogen cost to 0.003 percentage points (median)
because the 60 % minimum load binds; so only ammonia is solved and its design is
used for every fuel. All five synthesis annuities are still written.

From scripts/:  python -m lcof.flex_prepare_lowest <cell_order_npz> <outdir> [years]
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from . import inputs, params as P

SOLVE_FUELS = ["ammonia", "methanol", "e-methane", "e-diesel", "ethanol"]
HB_LOW = 950e3


def syn_capex_lowest(s) -> dict:
    """lowest-case synthesis capex by fuel, US$/W fuel x 1e6, scaled by the DEA path after 2030"""
    cap = {f: P.FUELS[f]["syn_capex"] for f in SOLVE_FUELS}
    cap["ammonia"] = HB_LOW
    return {f: v * float(s[f"syn_{f}"]) for f, v in cap.items()}


def main(order_npz: str, outdir: str, years: str = "2030,2025,2040,2050"):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    cells = np.load(order_npz, allow_pickle=True)["cell_id"]
    sc = pd.read_csv(inputs.MAPS / "lowest_case_scalars.csv").set_index("year")
    for y in [int(v) for v in years.split(",")]:
        os.environ["LCOF_CAPEX_FILE"] = f"capex_by_country_{y}low.csv"
        meta = inputs.load_meta(2025).reindex(cells)
        assert meta.wacc.notna().all() and meta.ez_capex.notna().all(), y
        s = sc.loc[y]
        A = {k: np.zeros(len(cells)) for k in ("Cpv", "Cw", "Cez", "Chs", "Cbp", "Cbe", "water")}
        for i, (c, r) in enumerate(meta.iterrows()):
            A["Cpv"][i] = P.annuity("pv", r.wacc, capex_override=float(r.pv_capex))
            A["Cw"][i] = P.annuity("wind_onshore", r.wacc, capex_override=float(r.wind_capex))
            A["Cez"][i] = P.annuity("electrolyzer", r.wacc, capex_override=float(r.ez_capex))
            A["Chs"][i] = P.annuity("h2_storage", r.wacc, capex_override=float(r.tank_capex))
            A["Cbp"][i] = P.annuity("battery_power", r.wacc, capex_override=float(r.bat_p_capex))
            A["Cbe"][i] = P.annuity("battery_energy", r.wacc, capex_override=float(r.bat_e_capex))
            cw = P.C_WATER_DEFAULT if not np.isfinite(r.water_cost) else float(r.water_cost)
            A["water"][i] = cw * P.OMEGA_H2O
        syn = {}
        for f, capx in syn_capex_lowest(s).items():
            p = P.FUELS[f]
            syn[f"syn_{f}"] = np.array([(P.crf(w, p["syn_life"]) + p["syn_opex"]) * capx
                                        * p["eta_syn"] / P.CF_SYN for w in meta.wacc])
        K = dict(eta_el=float(s.eta_el), eta_ch=P.ETA_CH, eta_dh=P.ETA_DH, sigma=0.02,
                 eta_syn=P.FUELS["ammonia"]["eta_syn"],
                 eta_syn_by_fuel={f: P.FUELS[f]["eta_syn"] for f in SOLVE_FUELS})
        for k, v in {**A, **syn}.items():
            assert np.isfinite(v).all() and (v >= 0).all(), (y, k)
        np.savez_compressed(out / f"costs_{y}.npz", cell_id=cells, K=np.array(K, dtype=object), **A, **syn)
        print(f"{y}: eta_el {K['eta_el']:.3f}, median annuity Cez {np.median(A['Cez']):,.0f} $/MW/yr, "
              f"Cpv {np.median(A['Cpv']):,.0f}, syn_ammonia {np.median(syn['syn_ammonia']):,.0f}", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
