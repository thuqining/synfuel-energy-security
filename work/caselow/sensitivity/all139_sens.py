"""
all139_sens.py -- the sensitivity counts of Supplementary Tables tab:fig5sens, tab:mfsens, tab:landsens and tab:paths
for all 139 economies (2026-10-22), next to the core-30 counts the main text quotes. Same functions as fig5a_sens,
mf_sens, land_sens and tier_table, with the portfolio computed for every economy instead of the core 30.
Writes all139_sens.json next to this script; reads nothing it writes.

Run from any directory: python work/caselow/sensitivity/all139_sens.py
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np
import pandas as pd

W = ROOT / "work" / "caselow"
OUT = Path(__file__).with_name("all139_sens.json")


def setup_case(case):
    os.environ.pop("LCOF_TIER", None)
    tier = "mid" if "mid" in case else "high" if "high" in case else None
    if tier:
        os.environ["LCOF_TIER"] = tier
    from lcof import inputs, case_low as C
    inputs.MAPS = W / case / "data"
    C.apply_params(int(case[:4]), tier)
    return inputs


def compute_all(**kw):
    """fig5a_chain.compute over every economy of security_budget.csv (as lcof.console_export)"""
    from lcof import fig5a_chain as A, inputs
    orig = A.core_countries
    setup = A._setup()
    sb = pd.read_csv(inputs.MAPS / "security_budget.csv", index_col=0)
    si = pd.read_csv(inputs.MAPS / "security_index.csv", index_col=0)
    keep = [c for c in sb.index if c in setup[1].index and c in si.index]
    A.core_countries = lambda avail, n=30: [c for c in keep if c in set(avail)]
    try:
        d = A.compute(write=False, verbose=False, setup=setup, **kw)
    finally:
        A.core_countries = orig
    return d, sb


def counts(d, sb):
    imp = d[sb.import_pct.reindex(d.index) > 0]
    return dict(n_imp=int(len(imp)), net_le0=int((imp.net_usd_t <= 0).sum()),
                net_le_cp=int((imp.net_usd_t <= imp.p_co2_usd_t).sum()),
                median_gross=float(imp.gross_usd_t.median()), median_net=float(imp.net_usd_t.median()),
                median_sec_share=float(((imp.gross_usd_t - imp.net_usd_t) / imp.gross_usd_t).median()),
                median_margin=float((imp.gross_usd_t - imp.net_usd_t).median()),
                co2_gt=float(d.co2_mt.sum() / 1e3))


def groups(d):
    is_x = d.import_pct <= 0.0
    covered = ~is_x & (d.ret_sf_3 >= 0.995)
    land = ~is_x & ~covered & (d.cov_3 >= d.max_cov - 1e-6) & (d.max_cov < 1 - 1e-6)
    budget = ~is_x & ~covered & ~land
    return is_x, covered, land, budget


def main():
    res = {"fig5sens": {}, "mfsens": [], "landsens": [], "paths": []}
    # tab:fig5sens -- 2030 lowest and 2025 central
    for case in ("2030", "2025mid"):
        setup_case(case)
        from lcof import fig5a_sens as S
        res["fig5sens"][case] = {}
        for name, kw in S.SCEN:
            d, sb = compute_all(**kw)
            res["fig5sens"][case][name] = counts(d, sb)
            print(case, name, res["fig5sens"][case][name], flush=True)
    # tab:mfsens
    from lcof import fig5a_chain as A
    for year in (2030, 2040, 2050):
        setup_case(str(year))
        for mf in (1.3, 1.0):
            A.M_F["oil"] = mf
            d, sb = compute_all()
            res["mfsens"].append(dict(year=year, m_f=mf, **counts(d, sb)))
            print("mf", year, mf, res["mfsens"][-1], flush=True)
        A.M_F["oil"] = 1.3
    # tab:landsens
    from lcof import security_budget as SB, land_screen as LS
    orig_build = LS.build

    def build_farm50(refresh=False):
        df = orig_build().copy()
        a, f, p = df.agri_share, df.forest_share, df.protected_share
        s = ((1 - p) * (1 - f - 0.50 * a)).clip(lower=0)
        df["land_baseline"] = (LS.DEV_BASE * s).clip(upper=0.02).fillna(df.land_baseline)
        return df
    for year in (2030, 2040, 2050):
        setup_case(str(year))
        for case in ("main", "A", "B"):
            LS.build = build_farm50 if case == "B" else orig_build
            df, _ = SB.compute(scale=2.0 if case == "A" else 1.0, write=False)
            is_x, cov, land, bud = groups(df)
            res["landsens"].append(dict(year=year, case=case, covered=int(cov.sum()), land=int(land.sum()),
                                        budget=int(bud.sum()), exporters=int(is_x.sum()),
                                        median_cov1=float(df.cov_1.median() * 100)))
            print("land", res["landsens"][-1], flush=True)
        LS.build = orig_build
    # tab:paths -- every cost year x tier
    for y in (2025, 2030, 2040, 2050):
        for tier in ("low", "mid", "high"):
            case = f"{y}" + ("" if tier == "low" else tier)
            setup_case(case)
            d, sb = compute_all()
            imp = sb.import_pct > 0
            c = counts(d, sb)
            res["paths"].append(dict(year=y, tier=tier, justified=c["net_le_cp"], n_imp=c["n_imp"],
                                     median_cov1=float(sb.cov_1.median() * 100),
                                     cov_1=int((sb.ret_sf_1[imp] >= 0.995).sum()),
                                     cov_2=int((sb.ret_sf_2[imp] >= 0.995).sum()),
                                     cov_3=int((sb.ret_sf_3[imp] >= 0.995).sum())))
            print("paths", res["paths"][-1], flush=True)
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
