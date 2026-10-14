import os, sys, runpy
from pathlib import Path
W = Path(sys.argv[1])
os.environ["LCOF_FIG_DIR"] = str(W / "figs")
# 2026-10-13: the cost tier follows the sandbox name ("2025mid", "2025mid_offshore" -> mid; "...high..." -> high);
# lowest-case sandboxes (2030, 2040, 2050) leave it unset. An explicit LCOF_TIER still wins.
if not os.environ.get("LCOF_TIER"):
    for t in ("mid", "high"):
        if t in W.name:
            os.environ["LCOF_TIER"] = t
from lcof import inputs, case_low as C
inputs.MAPS = W / "data"; C.apply_params(int(sys.argv[2]))
from lcof import fig_pptx_pairs as FPP; FPP.OUT = W / "figs"
mod = sys.argv[3]; sys.argv = [mod]; runpy.run_module(mod, run_name="__main__")
