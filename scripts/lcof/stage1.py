"""
stage1.py — capacity-sizing LP for the levelized cost of hydrogen (LCOH) at one
cell, per LCOF_plan.tex Stage 1.

Minimise annualised cost of {PV, wind, electrolyser, H2 buffer, optional battery}
delivering a CONSTANT hydrogen offtake D = 1 MWh_H2/h over one weather year.
Scale-free: LCOH = Z* / 8760 [$/MWh_H2].

linopy + HiGHS, mirrors the proven lcos/model.py formulation but without the
synthesis step (that is Stage 2, deterministic algebra).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import xarray as xr
import linopy

from . import params as P


def solve_lcoh(cf_pv, cf_wind, wacc, *, water_cost=None, wind_tech="wind_onshore",
               wind_capex=None, pv_capex=None, ez_capex=None, tank_capex=None,
               bat_p_capex=None, bat_e_capex=None,
               battery=False, dt=None, solver="highs", matching="hourly"):
    """Size the RE->H2 system for one cell and weather year.

    cf_pv, cf_wind : 1-D hourly capacity factors (same length).
    wacc           : cell discount rate (fraction).
    water_cost     : $/t delivered water (cell map; default params).
    wind_tech      : TECH key selecting wind CAPEX (onshore / offshore fixed / floating).
    wind_capex     : optional $/MW override (e.g. per-cell offshore CAPEX).
    battery        : include battery variables (expected ~0; off by default).
    dt             : hours per timestep (default 8760/n, so any down-sampling
                     keeps annual energy accounting exact).
    matching       : "hourly" (default) requires a CONSTANT hourly offtake, met
                     by a cyclic H2 buffer — the firm, hourly-matched product
                     the rest of this work reports. "annual" replaces that with
                     a single annual energy balance: the plant produces
                     whenever generation is available and only the YEAR's total
                     must equal the year's demand. It is a pure relaxation of
                     the hourly case (same data, same costs, strictly larger
                     feasible set), so LCOH_annual <= LCOH_hourly always, and
                     the difference IS the cost of the temporal-matching
                     requirement — measured inside this model rather than
                     imported from another one.

    Returns dict: lcoh in $/MWh, $/GJ, $/kg; capacities per MW_H2 of steady
    output; solar share, curtailment, storage hours, generation LCOE.
    """
    cf_pv = np.asarray(cf_pv, float)
    cf_wind = np.asarray(cf_wind, float)
    n = len(cf_pv)
    dt = (8760.0 / n) if dt is None else float(dt)
    D = 1.0                                     # MWh_H2 per h (normalised)
    cw = P.C_WATER_DEFAULT if water_cost is None or not np.isfinite(water_cost) else float(water_cost)

    t = pd.Index(range(n), name="t")
    cfpv = xr.DataArray(cf_pv, coords=[t])
    cfw = xr.DataArray(cf_wind, coords=[t])

    a_pv = P.annuity("pv", wacc, capex_override=pv_capex)
    a_w = P.annuity(wind_tech, wacc, capex_override=wind_capex)
    a_ez = P.annuity("electrolyzer", wacc, capex_override=ez_capex)
    a_hs = P.annuity("h2_storage", wacc, capex_override=tank_capex)

    m = linopy.Model()

    Cpv = m.add_variables(lower=0, name="C_pv")
    Cw = m.add_variables(lower=0, name="C_wind")
    Cez = m.add_variables(lower=0, name="C_ez")
    Chs = m.add_variables(lower=0, name="C_hs")

    pel = m.add_variables(lower=0, coords=[t], name="p_ez")      # MW into electrolyser
    s = m.add_variables(lower=0, coords=[t], name="s_h2")        # MWh_H2 store level

    obj = a_pv * Cpv + a_w * Cw + a_ez * Cez + a_hs * Chs

    if battery:
        a_bp = P.annuity("battery_power", wacc, capex_override=bat_p_capex)
        a_be = P.annuity("battery_energy", wacc, capex_override=bat_e_capex)
        Cbp = m.add_variables(lower=0, name="C_bp")
        Cbe = m.add_variables(lower=0, name="C_be")
        bc = m.add_variables(lower=0, coords=[t], name="b_c")
        bd = m.add_variables(lower=0, coords=[t], name="b_d")
        e = m.add_variables(lower=0, coords=[t], name="e_bat")
        curt = m.add_variables(lower=0, coords=[t], name="curt")
        # electricity balance with explicit curtailment
        m.add_constraints(Cpv * cfpv + Cw * cfw + P.ETA_DH * bd
                          - pel - bc - curt == 0, name="balance")
        m.add_constraints(e - e.roll(t=1) - P.ETA_CH * bc * dt + bd * dt == 0,
                          name="bat_soc")            # cyclic via roll
        m.add_constraints(e - Cbe <= 0, name="bat_energy_cap")
        m.add_constraints(bc - Cbp <= 0, name="bat_charge_cap")
        m.add_constraints(bd - Cbp <= 0, name="bat_discharge_cap")
        # epsilon flow penalty ($1e-3/MWh, ~1e-5 of real costs): removes the
        # degenerate simultaneous charge+discharge (LP-safe here because
        # curtailment is free, so no binaries are needed; verified: capacity
        # identical, overlap hours 116 -> 0 at the largest-battery cell)
        obj = obj + a_bp * Cbp + a_be * Cbe + 1e-3 * (bc.sum() + bd.sum()) * dt
    else:
        # curtailment implicit: use at most the available generation
        m.add_constraints(pel - Cpv * cfpv - Cw * cfw <= 0, name="balance")

    m.add_constraints(pel - Cez <= 0, name="ez_cap")
    if matching == "annual":
        # ANNUAL matching: only the year's total must balance. No storage
        # state, no firmness. A strict relaxation of the hourly case.
        m.add_constraints(P.ETA_EL * pel.sum() * dt == D * 8760.0,
                          name="h2_annual")
        m.add_constraints(Chs == 0, name="no_buffer")
    elif matching == "hourly":
        # H2 buffer: s(t) = s(t-1) + eta*pel*dt - D*dt, cyclic
        m.add_constraints(s - s.roll(t=1) - P.ETA_EL * pel * dt == -D * dt,
                          name="h2_balance")
        m.add_constraints(s - Chs <= 0, name="h2_cap")
    else:
        raise ValueError(f"matching must be 'hourly' or 'annual', "
                         f"got {matching!r}")

    # water feedstock on produced H2
    obj = obj + cw * P.OMEGA_H2O * P.ETA_EL * pel.sum() * dt

    m.add_objective(obj, sense="min")
    if solver == "gurobi":
        # Threads=1: the global sweep runs 20 single-threaded workers in parallel
        m.solve(solver_name="gurobi", OutputFlag=0, Threads=1)
    else:
        m.solve(solver_name=solver, output_flag=False)
    if m.status != "ok":
        return {"status": m.status, "lcoh_usd_mwh": np.nan}

    Z = float(m.objective.value)
    lcoh_mwh = Z / (D * 8760.0)
    cpv, cwind = float(Cpv.solution), float(Cw.solution)
    cez, chs = float(Cez.solution), float(Chs.solution)

    gen_pv = cpv * float(cfpv.sum()) * dt        # MWh/yr
    gen_w = cwind * float(cfw.sum()) * dt
    gen = gen_pv + gen_w
    used = float(pel.solution.sum()) * dt
    lcoe_mwh = (a_pv * cpv + a_w * cwind) / gen if gen > 0 else np.nan

    out = {
        "status": "ok",
        "lcoh_usd_mwh": lcoh_mwh,
        "lcoh_usd_gj": lcoh_mwh / 3.6,
        "lcoh_usd_kg": lcoh_mwh / 1000.0 * P.LHV_H2_KWH_KG,
        "cap_pv_MW": cpv, "cap_wind_MW": cwind,
        "cap_ez_MW": cez, "cap_h2sto_MWh": chs,
        "h2sto_hours": chs / D,
        "solar_share": gen_pv / gen if gen > 0 else np.nan,
        "curtail_share": 1.0 - used / gen if gen > 0 else np.nan,
        "lcoe_usd_mwh": lcoe_mwh,
        "matching": matching,
    }
    if battery:
        out["cap_bat_MW"] = float(Cbp.solution)
        out["cap_bat_MWh"] = float(Cbe.solution)
    return out
