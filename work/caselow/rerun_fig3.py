"""Fig 3 (2025 central) with the synthesis factor, plus the 3- and 12-month washout files."""
import os, sys
from pathlib import Path
os.environ["LCOF_TIER"] = "mid"
W = Path(__file__).resolve().parent / "2025mid"
os.environ["LCOF_FIG_DIR"] = str(W / "figs")
from lcof import inputs, case_low as C
inputs.MAPS = W / "data"; C.apply_params(2025)
from lcof import fig_pptx_pairs as FPP; FPP.OUT = W / "figs"
import runpy
sys.argv = ["lcof.fig_main_sites"]; runpy.run_module("lcof.fig_main_sites", run_name="__main__")
from lcof import fig_main_sites as S
S.OUT = W / "figs"
for key in ("ammonia", "ft"):
    for m in (3, 12):
        S.main(key, m, sensitivity=True)
print("fig3 done")
