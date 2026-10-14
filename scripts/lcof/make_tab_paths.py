"""make_tab_paths.py - Supplementary Table tab:paths: (a) median hydrogen cost
at the 29 case systems by build year (vintage_fuels.csv, hydrogen including its
conditioning plant), (b) CO2 displaced in Fig. 4b under each pathway, the central
valuation, retiring CO2 point sources and land ceilings. Moved into the
repository from a working script on 2026-10-05 (it produced the published table).

From scripts/:  python -u -m lcof.make_tab_paths
Writes data/cost/tab_paths.tex."""
from pathlib import Path
import numpy as np
import pandas as pd

from . import demand_grid as dgm
from . import fig5_chain as f5
from . import inputs
from .fig_main_cost import FUELS

OUT = inputs.MAPS
UMM = 1.0551
V = pd.read_csv(dgm.OUTD / "vintage_fuels.csv")
V = V[V.co2_axis == "persist"]
CASES = ("Conservative", "Moderate", "Advanced")


VALL = pd.read_csv(dgm.OUTD / "vintage_fuels.csv")


def make_decline(case, axis="persist"):
    def _decline(fuels):
        c = VALL[(VALL.case == case) & (VALL.co2_axis == axis)]
        grid = sorted(c.vintage.unique())
        base = c[c.vintage == grid[0]].set_index(["site", "fuel"]).lcof_med_usd_gj
        return {f: np.interp(dgm.VYEARS, grid,
                             [float((c[c.vintage == y].set_index(["site", "fuel"]).lcof_med_usd_gj / base)
                                    .xs(f, level="fuel").median()) for y in grid])
                for f in fuels}
    return _decline


# panel A: median hydrogen cost by build year
h = V[V.fuel == "hydrogen"]
years = sorted(h.vintage.unique())
rowsA = []
for case in CASES:
    m = [h[(h.case == case) & (h.vintage == y)].lcof_med_usd_gj.median() * UMM for y in years]
    rowsA.append(f"{case} & " + " & ".join(f"{v:.1f}" for v in m) + " \\\\")
    print(case, [round(v, 1) for v in m])

# panel B: Fig. 4b
si = pd.read_csv(inputs.MAPS / "security_index.csv", index_col=0)
TY = (2025, 2030, 2040, 2050)
res = {}
for case in CASES:
    f5._decline = make_decline(case)
    p, tj, q_at = f5.panel_b_data(write=False)
    tj = tj.set_index("year")
    res[case] = ([tj.sec_gt[t] for t in TY], [tj.cost_gt[t] for t in TY])
    if case == "Moderate":
        # central valuation: scale each economy's w by codf / codf_hi, re-date security parity
        dec = f5._decline(FUELS)
        from .gap import country_lcof
        from .security_budget import _grey
        meta = inputs.load_meta(2025)
        dg = pd.read_csv(inputs.MAPS / "demand_fuel_grid.csv", index_col=0)
        dgc = dg.join(meta[["country"]]).groupby("country")[[f + "_gj" for f in FUELS]].sum()
        lc, gr = country_lcof(), _grey(dgc.rename(columns=lambda k: k.replace("_gj", "")))
        ratio = si.codf_usd_gj / si.codf_hi_usd_gj
        vy = np.asarray(dgm.VYEARS)
        sec_c = []
        for _, r in p.iterrows():
            pi = float(lc.loc[r.country, r.fuel]) * dec[r.fuel] - float(gr.loc[r.country, r.fuel])
            w = r.w_usd_gj * float(ratio[r.country])
            k = np.nonzero(pi <= w)[0] if (r.imp_gj > 0 and w > 0) else []
            sec_c.append(float(vy[k[0]]) if len(k) else 2099.0)
        p = p.assign(sec_imp=sec_c)
        res["Moderate, central valuation"] = (
            [float((q_at(t, p) * p.ef).sum() / 1e9) for t in TY], res["Moderate"][1])

# referee checks (2026-10-02): CO2 point sources that retire over time, and
# each economy's qualifying demand capped at its land ceiling (Fig. 5 layer)
f5._decline = make_decline("Moderate", "retire")
p_r, tj_r, _ = f5.panel_b_data(write=False)
tj_r = tj_r.set_index("year")
res["Moderate, retiring CO$_2$ point sources"] = ([tj_r.sec_gt[t] for t in TY], [tj_r.cost_gt[t] for t in TY])
f5._decline = make_decline("Moderate")
p_m, _, q_m = f5.panel_b_data(write=False)
sb = pd.read_csv(inputs.MAPS / "security_budget.csv", index_col=0)
cap_share = sb.max_cov.clip(upper=1.0)


def capped(t, cost_only=False):
    q = (p_m.imp_gj * (p_m.cost <= t) + (p_m.dem_gj - p_m.imp_gj) * (p_m.cost_rest <= t))         if cost_only else q_m(t, p_m)
    by = pd.DataFrame({"country": p_m.country, "q": q, "co2": q * p_m.ef, "dem": p_m.dem_gj}) \
        .groupby("country").sum()
    cap = cap_share.reindex(by.index).fillna(1.0) * by.dem
    scale = np.where(by.q > 0, np.minimum(1.0, cap / by.q.where(by.q > 0, 1.0)), 1.0)
    return float((by.co2 * scale).sum() / 1e9)


res["Moderate, land ceilings applied"] = ([capped(t) for t in TY], [capped(t, True) for t in TY])
# China's share of the land-capped 2050 total (quoted in the SI)
_q = q_m(2050, p_m)
_by = pd.DataFrame({"country": p_m.country, "q": _q, "co2": _q * p_m.ef, "dem": p_m.dem_gj}).groupby("country").sum()
_cn = _by.loc["China"]
print(f"China 2050: {_cn.co2 / 1e9:.2f} Gt uncapped, "
      f"{_cn.co2 * min(1.0, cap_share.get('China', 1.0) * _cn.dem / _cn.q) / 1e9:.2f} Gt at its land ceiling")

rowsB = []
for k, (s, c) in res.items():
    lab = k + (" (main case)" if k == "Moderate" else "")
    rowsB.append(f"{lab} & " + " & ".join(f"{v:.2f}" for v in s) + " & " + " & ".join(f"{v:.2f}" for v in c) + " \\\\")
    print(lab, [round(v, 2) for v in s], [round(v, 2) for v in c])

(OUT / "tab_paths.tex").write_text(
    "\\begin{tabular}{@{}lrrrrrr@{}}\\toprule\n"
    "\\multicolumn{7}{@{}l}{\\emph{a. Median hydrogen cost at the case systems (US\\$\\,MMBtu$^{-1}$)}}\\\\\n"
    "Cost path & " + " & ".join(str(y) for y in years) + "\\\\\\midrule\n" + "\n".join(rowsA) +
    "\n\\bottomrule\\end{tabular}\n\n\\vspace{8pt}\n"
    "\\begin{tabular}{@{}lrrrrrrrr@{}}\\toprule\n"
    "\\multicolumn{9}{@{}l}{\\emph{b. CO$_2$ displaced in Fig.~\\ref{fig:co2}b (Gt\\,yr$^{-1}$)}}\\\\\n"
    " & \\multicolumn{4}{c}{With security value} & \\multicolumn{4}{c}{Cost parity alone}\\\\\n"
    "\\cmidrule(lr){2-5}\\cmidrule(l){6-9}\n"
    "Case & " + " & ".join(str(t) for t in TY) + " & " + " & ".join(str(t) for t in TY) + "\\\\\\midrule\n" +
    "\n".join(rowsB) + "\n\\bottomrule\\end{tabular}\n", encoding="utf-8")
print("wrote tab_paths.tex")
