"""
build_case.py -- build or refresh one case (cost year x cost tier) under work/caselow/<case>.

    python build_case.py 2030 mid            # case 2030mid: build from the LP results, then Fig. 4/5 stages
    python build_case.py 2030 mid --stages   # refresh the Fig. 4/5 stages of an existing case only
    python build_case.py 2050 low            # case 2050 (lowest tier, the main case)

The case is built from data/cost/flexlow/run_<case>/out (the linear-program results per cell and weather year)
by lcof.case_low, the JODI trade files are copied next to the case's data (security_budget reads them from
<case>/jodi), and the Fig. 4b data are written by lcof.fig5_chain. Run from any directory.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]                       # repository root
SCRIPTS = ROOT / "scripts"


def main(year: str, tier: str, *flags):
    case = year + ("" if tier in ("low", "lowest", "") else tier)
    work = ROOT / "work" / "caselow" / case
    env = dict(os.environ, PYTHONPATH=str(SCRIPTS))
    env.pop("LCOF_TIER", None)
    if tier not in ("low", "lowest", ""):
        env["LCOF_TIER"] = tier
    stages = ["fig4", "fig5"] if "--stages" in flags else ["build", "fig4", "fig5"]
    parts = ROOT / "data" / "cost" / "flexlow" / f"run_{case}" / "out"
    py = sys.executable
    print(f"=== {case}: {' '.join(stages)}", flush=True)
    if "build" in stages:
        subprocess.run([py, "-m", "lcof.case_low", year, str(parts), str(work), *stages[:1]],
                       cwd=SCRIPTS, env=env, check=True)
    jodi = work / "jodi"
    if not jodi.exists():
        shutil.copytree(ROOT / "data" / "jodi", jodi)
    subprocess.run([py, "-m", "lcof.case_low", year, str(parts), str(work), "fig4", "fig5"],
                   cwd=SCRIPTS, env=env, check=True)
    subprocess.run([py, str(ROOT / "work" / "caselow" / "run_mod.py"), str(work), year, "lcof.fig5_chain"],
                   cwd=SCRIPTS, env=env, check=True)
    print(f"=== {case} done", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
