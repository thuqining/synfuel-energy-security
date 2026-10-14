"""
variants.py -- the case variants behind single Supplementary Information paragraphs.

    python variants.py gni        # Ireland at modified GNI* (55.4% of GDP) instead of GDP: 2025mid and 2030
    python variants.py offshore   # the 374 coastal cells at fixed-bottom offshore wind cost: 2025mid

Each variant copies a main case to work/caselow/<case>_<variant>, changes one input, reruns the Fig. 4a and
Fig. 5 stages and prints the numbers the SI quotes next to those of the main case. The offshore variant also
reads the cell-level sensitivity runs in work/sens_results/out/{base,offshore} (work/sens_pkg/sens_flex.py).
"""
import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
W = ROOT / "work" / "caselow"
SCRIPTS = ROOT / "scripts"
GNI_STAR = 0.554                                     # CSO Ireland, modified GNI* / GDP, 2025


def _copy(case, tag):
    dst = W / f"{case}_{tag}"
    if dst.exists():
        shutil.rmtree(dst)
    (dst / "figs").mkdir(parents=True)
    shutil.copytree(W / case / "data", dst / "data", ignore=shutil.ignore_patterns("bak_*"))
    shutil.copytree(ROOT / "data" / "jodi", dst / "jodi")
    return dst


def _run(case_dir, year, mods):
    env = dict(os.environ, PYTHONPATH=str(SCRIPTS))
    env.pop("LCOF_TIER", None)
    for m in mods:
        subprocess.run([sys.executable, str(W / "run_mod.py"), str(case_dir), str(year), m], cwd=SCRIPTS,
                       env=env, check=True, stdout=subprocess.DEVNULL)


def _summary(case_dir):
    d = pd.read_csv(case_dir / "data" / "fig5a_chain.csv", index_col=0)
    sb = pd.read_csv(case_dir / "data" / "security_budget.csv", index_col=0)
    sys.path.insert(0, str(SCRIPTS))
    from lcof.coreset import core_countries
    core = sb.reindex([c for c in core_countries(sb.index) if c in sb.index])
    return d, core


def gni():
    for case, year in (("2025mid", 2025), ("2030", 2030)):
        dst = _copy(case, "gni")
        f = dst / "data" / "vulnerability_inputs.csv"
        v = pd.read_csv(f, index_col=0)
        v.loc["Ireland", "gdp_usd"] *= GNI_STAR
        v.to_csv(f)
        _run(dst, year, ["lcof.security", "lcof.security_budget", "lcof.fig5a_chain"])
        a, _ = _summary(W / case)
        b, _ = _summary(dst)
        ma = a.gross_usd_t["Ireland"] - a.net_usd_t["Ireland"]
        mb = b.gross_usd_t["Ireland"] - b.net_usd_t["Ireland"]
        just = sorted(b.index[b.net_usd_t <= b.p_co2_usd_t])
        print(f"{case}: Ireland security margin {ma:.0f} -> {mb:.0f} US$/t ({100 * (1 - mb / ma):.0f}% lower); "
              f"net premium {b.net_usd_t['Ireland']:.0f} vs carbon price {b.p_co2_usd_t['Ireland']:.0f}; "
              f"justified with GNI*: {just}")


def offshore():
    S = ROOT / "work" / "sens_results" / "out"
    rd = lambda v: pd.concat(pd.read_csv(f) for f in glob.glob(str(S / v / "part_*.csv"))).drop_duplicates(
        "cell_id").set_index("cell_id")
    base, off = rd("base"), rd("offshore")
    ratio = off.lcoh / base.lcoh.reindex(off.index)
    mm = 1.055056                                     # US$/GJ -> US$/MMBtu
    r = 100 * (ratio - 1)
    print(f"coastal cells: {len(ratio)}; hydrogen cost +{r.median():.0f}% (IQR {r.quantile(.25):.0f}-{r.quantile(.75):.0f}%), "
          f"US${base.lcoh.reindex(off.index).median() * mm:.1f} -> {off.lcoh.median() * mm:.1f} per MMBtu; "
          f"solar share {100 * off.solar_share.median():.0f}% vs {100 * base.solar_share.reindex(off.index).median():.0f}%")
    allc = base.lcoh.copy()
    allc.loc[ratio.index] = off.lcoh
    print(f"all land cells, median hydrogen cost US${base.lcoh.median() * mm:.1f} -> {allc.median() * mm:.1f} per MMBtu")
    dst = _copy("2025mid", "offshore")
    for wy in range(2006, 2026):
        f = dst / "data" / f"lcoh_global_{wy}_reg.csv"
        d = pd.read_csv(f).set_index("cell_id")
        m = d.index.isin(ratio.index)
        d.loc[m, "lcoh_usd_gj"] = d.loc[m, "lcoh_usd_gj"] * ratio.reindex(d.index[m]).to_numpy()
        d.reset_index().to_csv(f, index=False)
    _run(dst, 2025, ["lcof.aggregate_global", "lcof.security", "lcof.security_budget", "lcof.fig5a_chain"])
    for case_dir in (W / "2025mid", dst):
        d, core = _summary(case_dir)
        imp = core.import_pct > 0
        cov3 = int((imp & (core.ret_sf_3 >= 0.995)).sum())
        print(f"{case_dir.name}: median share bought with 1% of GDP {100 * core.cov_1.median():.1f}%; "
              f"import share reached at 3% of GDP by {cov3}; net premium Ireland {d.net_usd_t['Ireland']:.0f}, "
              f"Netherlands {d.net_usd_t['Netherlands']:.0f}, Germany {d.net_usd_t['Germany']:.0f} "
              f"(carbon price Ireland {d.p_co2_usd_t['Ireland']:.0f}); justified {sorted(d.index[d.net_usd_t <= d.p_co2_usd_t])}")


if __name__ == "__main__":
    {"gni": gni, "offshore": offshore}[sys.argv[1]]()
