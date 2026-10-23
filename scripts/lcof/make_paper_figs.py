"""
make_paper_figs.py — redraw the figures of the paper and its SI as uploaded on 2026-10-22: 183 mm wide
(lcof.fixwidth for the figures saved to a tight box), rasters at 600 dpi, each in its own process so that every
figure reads the sandbox and cost tier it was drawn from.

From scripts/:  python -m lcof.make_paper_figs <out dir> [name ...]        (no names: all of FIGS)
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
W = R / "work" / "caselow"
FUELS3 = ("ammonia", "e-diesel", "e-methane", "methanol", "ethanol", "hydrogen")
# name -> the sandbox whose data/ the figure reads (None: it names its inputs itself)
# 2026-10-22: Fig. 4c became its own figure, Fig. 5 (fig5_core, lcof.fig_macc); the budget figure is
# now Fig. 6 (fig6_core), 2030 only
FIGS = {"fig3_core": None, "fig4_core": None, "fig5_core": None, "fig6_core": None,
        "fig_main_framework": "2025mid", "fig_sd_map_full": "2025mid", "fig_main_demand_struct": "2025mid",
        "fig_main_crisis": "2025mid", "fig_si_feedstocks": "2025mid", "fig_si_weather_spread": "2025mid",
        "fig_si_corridors": "2025mid", "fig_si_lcoh_map_kg": "2025mid", "fig_si_voll_map": None,
        "fig_si_capacity": "2030", "fig_si_tiers": None, "fig_si_workflow": "2025mid",
        **{f"si_fig3_{f}_139": None for f in FUELS3},
        **{f"si_fig5_{y}_139": None for y in ("2030", "2040", "2050")}, "si_fig4a_139": None}
# the older figures drawn by a module's main() into fig_pptx_pairs.OUT
OLDER = {"fig_main_framework": "fig_main_framework", "fig_sd_map_full": "fig_sd_map_zoom",
         "fig_si_feedstocks": "fig_si_feedstocks", "fig_si_weather_spread": "fig_si_weather_spread",
         "fig_si_corridors": "fig_si_corridors", "fig_si_voll_map": "fig_si_voll_map",
         "fig_si_lcoh_map_kg": "fig_si_lcoh_map_kg", "fig_si_workflow": "fig_si_workflow"}


def _one(name: str, out: Path):
    case = FIGS[name]
    if case and case.endswith("mid"):
        os.environ["LCOF_TIER"] = "mid"
    from lcof import inputs, case_low as C
    if case:
        inputs.MAPS = W / case / "data"
        C.apply_params(int(case[:4]))
    from lcof import fixwidth, fig_pptx_pairs as FPP
    # 2026-10-22: 7 pt throughout, except the dense 139-economy figures, whose economy names stay smaller
    dense = name in ("fig_main_demand_struct", "fig_main_crisis", "fig_si_capacity") or name.endswith("_139")
    fixwidth.install(min_pt=None if dense else 7.0)
    FPP.OUT = out
    if name == "fig3_core":
        from lcof import fig35_core
        fig35_core.main("fig3", str(out / name), 104.0, 72.0)     # 2026-10-22: a shorter, more space before b
    elif name == "fig6_core":
        from lcof import fig35_core
        fig35_core.main("fig6", str(out / name), 85.0)
    elif name == "fig4_core":
        from lcof import fig4_core
        fig4_core.main(str(out / name), [f"{y}={W / str(y)}" for y in (2030, 2040, 2050)], 80.0, 72.0, 0.0)
    elif name == "fig5_core":
        from lcof import fig_macc
        fig_macc.main(str(out / name), *(f"{y}={W / str(y)}" for y in (2030, 2040, 2050)))
    elif name.startswith("si_fig3_"):          # 2026-10-22: one economy per row, names level
        from lcof import fig_rows139
        fig_rows139.fig3(str(out / name), name[len("si_fig3_"):-len("_139")])
    elif name == "si_fig4a_139":
        from lcof import fig_rows139
        fig_rows139.fig4a(str(out / name))
    elif name.startswith("si_fig5_"):
        from lcof import fig_rows139            # Fig. 6 at one cost year, one economy per row
        fig_rows139.fig6(str(out / name), name.split("_")[2])
    elif name == "fig_main_crisis":
        from lcof import crisis139
        crisis139.main(str(out))
    elif name == "fig_main_demand_struct":
        from lcof import fig_main_demand_struct as M
        M.main139(out)
    elif name == "fig_si_capacity":
        import pandas as pd
        from lcof import security_budget as M
        from lcof.coreset import core_countries
        M.OUT = out
        d = pd.read_csv(inputs.MAPS / "security_budget.csv", index_col=0)
        M._figure_capacity(d, bold=set(core_countries(d.index)))
    elif name == "fig_si_tiers":
        from lcof import fig_si_tiers
        fig_si_tiers.main(str(W), str(out))
    else:
        import importlib
        M = importlib.import_module("lcof." + OLDER[name])
        if hasattr(M, "OUT"):
            M.OUT = out
        M.main()


def main(out, *names):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for n in names or FIGS:
        r = subprocess.run([sys.executable, "-m", "lcof.make_paper_figs", "--one", n, str(out)],
                           cwd=Path(__file__).resolve().parents[1])
        print(("ok  " if r.returncode == 0 else "FAIL"), n)


if __name__ == "__main__":
    if sys.argv[1] == "--one":
        _one(sys.argv[2], Path(sys.argv[3]))
    else:
        main(*sys.argv[1:])
