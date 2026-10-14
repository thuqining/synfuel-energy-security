"""
case_low.py — the lowest-cost main case (2026-10-07) for one
cost year: collect the 20-weather-year flexible-synthesis LP, build a sandbox copy
of data/cost on it, set the year's cost scalars, and run the main-figure modules.

  layer   lcoh_global_<wy>_reg.csv for wy = 2006..2025 from the flexible LP
          (ammonia window 60-100 %, 5 %/h; the fuel-specific LPs agree to 0.003
          percentage points, flex_prepare_lowest), in the columns of the
          constant-load layer
  capex   capex_by_country_<year>low.csv; the synthesis location factor is
          multiplied by the economy's median reactor oversizing C_S of the LP
  params  synthesis capex at the IEA GHR 2026 low end, x the DEA path after 2030
          (lowest_case_scalars.csv), electrolyser efficiency, DAC cost

From scripts/:  python -m lcof.case_low <year> <parts_dir> <workdir> [stage ...]
Central / highest cost tiers (SI; 2026-10-08): set LCOF_TIER=mid or LCOF_TIER=high. The sandbox
then takes capex_by_country_<year><tier>.csv and the tier row of tier_scalars.csv (lcof.capex_tiers);
the figure scripts that call apply_params read the same variable.
stages: build (default first), figs (Figs 1-3), fig4 (4a/4b data), fig5
"""
from __future__ import annotations

import glob
import runpy
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
COST = ROOT / "data" / "cost"
WY = list(range(2006, 2026))
TAG = "flex60_ammonia"
KEEP = ["lcoh_usd_gj", "lcoh_usd_kg", "lcoe_usd_mwh", "cap_pv", "cap_wind", "cap_ez", "h2sto_h",
        "cap_bat_MW", "cap_bat_MWh", "solar_share", "curtail_share"]
SYN_BASE = {"ammonia": 950e3, "methanol": 349e3, "ethanol": 349e3, "e-methane": 700e3,
            "e-diesel": 2032e3, "e-kerosene": 2032e3}


def collect(parts_dir: str) -> pd.DataFrame:
    fs = sorted(glob.glob(f"{parts_dir}/part_*_*.csv"))
    r = pd.concat([pd.read_csv(f) for f in fs]).drop_duplicates(["cell_id", "year"])
    bad = r.filter(like="status_").eq("fail").any(axis=1).sum() if r.filter(like="status_").shape[1] else 0
    n = r.groupby("year").cell_id.nunique()
    print(f"{len(fs)} parts, {len(r)} cell-years, cells per weather year {n.min()}-{n.max()}, "
          f"{len(n)} weather years, {bad} failed", flush=True)
    assert len(n) == len(WY) and n.min() == n.max(), "incomplete run"
    out = pd.DataFrame({"cell_id": r.cell_id, "year": r.year, "status": "ok",
                        "lcoh_usd_gj": r[f"lcoh_{TAG}"], "lcoe_usd_mwh": r[f"lcoe_mwh_{TAG}"],
                        "cap_pv": r[f"cap_pv_{TAG}"], "cap_wind": r[f"cap_wind_{TAG}"],
                        "cap_ez": r[f"cap_ez_{TAG}"], "h2sto_h": r[f"sto_h_{TAG}"],
                        "cap_bat_MW": r[f"cap_bat_MW_{TAG}"], "cap_bat_MWh": r[f"cap_bat_MWh_{TAG}"],
                        "solar_share": r[f"solar_share_{TAG}"], "curtail_share": r[f"curtail_share_{TAG}"],
                        "cs": r[f"cs_{TAG}"]})
    out["lcoh_usd_kg"] = out.lcoh_usd_gj * 0.12
    return out


def build(year: int, parts_dir: str, work: str):
    W = Path(work)
    SB = W / "data"
    if SB.exists():
        shutil.rmtree(SB)
    shutil.copytree(COST, SB, ignore=shutil.ignore_patterns(
        "sens_*", "_iea_logs", "sources", "flexlow", "flex60_20yr_raw", "pass1_*", "lcoh_global_*_reg_*.csv"))
    (W / "figs").mkdir(parents=True, exist_ok=True)
    (W.parent / "synthetic_fuel_nature").mkdir(parents=True, exist_ok=True)
    r = collect(parts_dir)
    for wy in WY:
        g = r[r.year == wy].drop(columns=["year", "cs"])
        g[["cell_id", "status"] + KEEP].to_csv(SB / f"lcoh_global_{wy}_reg.csv", index=False)
    # synthesis oversizing of the flexible plant, economy median over cells and weather years
    from . import inputs
    meta = inputs.load_meta(2025)
    cs = r.groupby("cell_id").cs.median()
    cs_c = cs.groupby(meta.country.reindex(cs.index)).median()
    import os
    cap = pd.read_csv(COST / f"capex_by_country_{year}{os.environ.get('LCOF_TIER') or 'low'}.csv"
                      ).set_index("country")
    cap["flex_cs"] = cs_c.reindex(cap.index).fillna(float(cs.median()))
    cap["syn_location_factor"] = cap.syn_location_factor * cap.flex_cs
    cap.reset_index().to_csv(SB / "capex_by_country.csv", index=False)
    h = r.groupby("cell_id").lcoh_usd_gj.median()
    print(f"{year}: median over cells of the 20-yr median LCOH {h.median() * 0.12:.2f} US$/kg, "
          f"C_S median {cs.median():.3f}", flush=True)


def apply_params(year: int, tier: str | None = None):
    import os
    from . import params as P
    tier = tier or os.environ.get("LCOF_TIER") or None
    if tier:
        s = pd.read_csv(COST / "tier_scalars.csv").set_index(["tier", "year"]).loc[(tier, year)]
    else:
        s = pd.read_csv(COST / "lowest_case_scalars.csv").set_index("year").loc[year]
    for f, v in SYN_BASE.items():
        P.FUELS[f]["syn_capex"] = v * float(s[f"syn_{f}"])
    if tier:                         # the tier's own Haber-Bosch cost, already on the DEA path
        P.FUELS["ammonia"]["syn_capex"] = float(s.hb_usd_kw) * 1e3
    m, a = P.FUELS["methanol"], P.FUELS["ammonia"]
    P.FUELS["marine"]["syn_capex"] = 0.7 * m["syn_capex"] + 0.3 * a["syn_capex"]
    P.FUELS["marine"]["syn_opex"] = ((0.7 * m["syn_capex"] * m["syn_opex"] + 0.3 * a["syn_capex"] * a["syn_opex"])
                                     / P.FUELS["marine"]["syn_capex"])
    P.ETA_EL = float(s.eta_el)
    P.C_CO2_DAC = float(s.dac_usd_t)
    print(f"params {year}{' ' + tier if tier else ''}: " + ", ".join(f"{f} {P.FUELS[f]['syn_capex'] / 1e3:.0f}" for f in list(SYN_BASE) + ["marine"])
          + f" US$/kW; eta_el {P.ETA_EL:.3f}; DAC {P.C_CO2_DAC:.0f} US$/t", flush=True)


def sync_dac(data: Path):
    """2026-10-09: the CO2 layers carry the direct-air-capture price as a fixed US$500/t in the
    cells that reach no point source; set it to the case's DAC cost (P.C_CO2_DAC, set by
    apply_params for the cost year and tier) in every CO2 layer of the sandbox."""
    from . import params as P
    for f in ("co2_cost_by_cell.csv", "co2_cost_by_cell_neutral.csv", "co2_cost_by_cell_neutral_longterm.csv"):
        p = data / f
        if not p.exists():
            continue
        d = pd.read_csv(p)
        m = d.pathway == "DAC"
        if m.any() and not np.allclose(d.loc[m, "co2_cost"], P.C_CO2_DAC):
            d.loc[m, "co2_cost"] = P.C_CO2_DAC
            d.to_csv(p, index=False)
            print(f"{f}: {int(m.sum())} DAC cells set to US${P.C_CO2_DAC:.0f}/t", flush=True)


def _run(mod, *args):
    sys.argv = [mod] + list(args)
    print(f"=== {mod}", flush=True)
    runpy.run_module(mod, run_name="__main__")


STAGES = {
    "figs": ["lcof.aggregate_global", "lcof.fig_main_sites", "lcof.supply_demand", "lcof.fig_sd_map",
             "lcof.fig_main_framework"],
    "fig4": ["lcof.security_budget", "lcof.fig5a_chain"],
    "fig5": ["lcof.security_budget"],
}


def run(year: int, work: str, stages):
    W = Path(work)
    import os
    os.environ["LCOF_FIG_DIR"] = str(W / "figs")
    from . import inputs
    inputs.MAPS = W / "data"
    apply_params(year)
    sync_dac(W / "data")
    from . import fig_pptx_pairs as FPP
    FPP.OUT = W / "figs"
    if "figs" in stages or "fig4" in stages or "fig5" in stages:
        _run("lcof.aggregate_global")
    done = {"lcof.aggregate_global"}
    for st in stages:
        for mod in STAGES.get(st, []):
            if mod not in done:
                _run(mod)
                done.add(mod)


if __name__ == "__main__":
    y, parts, work, *st = sys.argv[1:]
    st = st or ["build"]
    if "build" in st:
        build(int(y), parts, work)
    rest = [s for s in st if s != "build"]
    if rest:
        run(int(y), work, rest)
