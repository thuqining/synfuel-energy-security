"""global_trajectory.py — the globally aggregated result
plus the demand-concentration numbers.

For every assessed economy we compute the security-parity and
cost-parity build years (same machinery as fig_main_parity, no core
filter), attach the reconciled addressable demand and the displaced
fossil emissions, and aggregate:

  R_sec(t) = sum of addressable demand of economies security-rational
             by build year t     [billion MMBtu/yr and EJ/yr]
  A_sec(t) = displaced fossil CO2 of the same set  [GtCO2/yr]

and the same for cost parity. Also writes the per-fuel demand
concentration table (tab_demand.tex) and the trajectory figure.

From scripts/:  conda run -n synfuel python -u -m lcof.global_trajectory
Output: data/cost/global_trajectory.csv,
        synthetic_fuel_nature/tab_demand.tex,
        cf_global_final/figures/pptx/fig_global_traj.(pdf|png)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

mpl.use("Agg")

from . import inputs
from .fig_main_cost import MM, NAT_RC, FUELS, _nat_map
from .fig_pptx_pairs import OUT, SUFFIX, YEARS
from .demand_grid import _decline
from .policy import grey_h2_price

mpl.rcParams.update(NAT_RC)

ORANGE, BLUE, GREEN = "#D55E00", "#0072B2", "#009E73"
UMM = 1.0551                       # $/MMBtu = $/GJ * UMM;  GJ = 1/UMM MMBtu
# displaced fossil combustion/production EF, t CO2 per GJ of service
EFD = {"e-methane": 0.0561, "e-diesel": 0.0741, "ethanol": 0.0741,
       "e-kerosene": 0.0715, "methanol": 0.0741, "ammonia": 0.129, "marine": 0.0774}
# regions for the stacked trajectory (Natural Earth continents, with
# the two energy-defined splits the paper uses elsewhere)
# 2026-10-05: Paul Tol "muted" (colour-blind safe) without its green, so that
# regions never share a colour with the fuels of Fig. 1 or with the paper's
# roles (blue synthetic, orange imports, green security, magenta carbon)
REGION_COL = {"China": "#332288", "Rest of Asia and Oceania": "#88CCEE",
              "Europe": "#44AA99", "Americas": "#CC6677",
              "Africa": "#999933", "Middle East": "#882255"}
MIDEAST = {"Saudi Arabia", "Iran", "Iraq", "Qatar", "Kuwait", "Oman",
           "United Arab Emirates", "Yemen", "Jordan", "Lebanon",
           "Syria", "Israel", "Bahrain"}


def region_of(country: str, lon: float, lat: float) -> str:
    """region from the country's representative point; the Middle East
    and China are named explicitly because the paper treats them as
    their own markets."""
    if country == "China":
        return "China"
    if country in MIDEAST:
        return "Middle East"
    if country in ("Russia", "Russian Federation", "Cyprus"):
        return "Europe"          # Russia: point east of 45E; Cyprus: point south of 35N
    if not np.isfinite(lon):
        return "Rest of Asia and Oceania"
    if lon < -25:
        return "Americas"
    if lat >= 35 and -25 <= lon <= 45:
        return "Europe"
    if -20 <= lon <= 55 and lat < 35:
        return "Africa"
    return "Rest of Asia and Oceania"


BS = chr(92)
NL = chr(10)
EOL = BS + BS


def main():
    # ---- addressable demand + displaced emissions per country -------------
    meta = inputs.load_meta(2025)
    dg = pd.read_csv(inputs.MAPS / "demand_fuel_grid.csv", index_col=0)
    cols = [f + "_gj" for f in FUELS]
    dgc = dg.join(meta[["country"]]).groupby("country")[cols].sum()
    dem_gj = dgc.sum(axis=1)
    emis_t = sum(dgc[f + "_gj"] * EFD[f] for f in FUELS)

    # ---- parity years, all assessed economies, PER FUEL -------------------
    # A country reaching hydrogen parity used to book its whole
    # six-fuel demand at once; that equated hydrogen parity with
    # all-fuel parity and inflated the global trajectory. Each
    # (country, fuel) now clears on its own premium against its own
    # comparator, with its own decline path and service multiplier.
    si = pd.read_csv(inputs.MAPS / "security_index.csv", index_col=0)
    si = si.dropna(subset=["codf_hi_usd_gj", "q_eff"])
    g = _decline(["hydrogen"])["hydrogen"]        # cell map, panel a
    decl = _decline(FUELS)
    from .gap import country_gas_monthly, country_lcof
    from .security_budget import _grey
    lcof_all = country_lcof()
    gasdf, gpan = country_gas_monthly()
    # the same comparators as Figs 3-5 (2026-09-17): each core economy's own
    # import price in normal months for ammonia, diesel, jet and ethanol; the
    # national gas route or world benchmark elsewhere; all in 2025 US$
    grey_tab = _grey(dgc.rename(columns=lambda k: k.replace("_gj", "")))
    GASF = {"e-methane", "ammonia", "methanol"}
    M_F = {"gas": 1.0, "oil": 1.3}                # service multipliers
    vy = np.arange(2025, 2051)
    rows, n_skip = [], 0
    for c in dgc.index:
        if (c not in si.index or c not in lcof_all.index
                or c not in gasdf.columns):
            n_skip += 1
            continue
        r = si.loc[c]
        for f in FUELS:
            d_f = float(dgc.loc[c, f + "_gj"])
            if d_f <= 0 or f not in lcof_all.columns:
                continue
            lcof_f = float(lcof_all.loc[c, f])
            grey_f = float(grey_tab.loc[c, f]) if (c in grey_tab.index
                                                   and f in grey_tab.columns) else np.nan
            if (not np.isfinite(lcof_f) or not np.isfinite(grey_f)
                    or grey_f <= 0):
                continue
            pi_t = lcof_f * decl[f] - grey_f
            m_f = M_F["gas" if f in GASF else "oil"]
            # ENTSOG planning anchor: codf_hi = codf x (ENTSOG/ACER)
            thr = r.codf_hi_usd_gj * r.q_eff * m_f
            ks = np.nonzero(pi_t <= thr)[0]
            kc = np.nonzero(pi_t <= 0)[0]
            rows.append((c, f,
                         float(vy[ks[0]]) if len(ks) else 2099.0,
                         float(vy[kc[0]]) if len(kc) else 2099.0,
                         d_f, d_f * EFD[f]))
    dfp = pd.DataFrame(rows, columns=["country", "fuel", "sec", "cost",
                                      "dem_gj", "emis_t"])
    print(f"fuel-resolved parity: {len(dfp)} (country, fuel) pairs, "
          f"{dfp.country.nunique()} economies ({n_skip} skipped for "
          f"missing layers)")
    tot_gj = dfp.dem_gj.sum()
    tot_ej = tot_gj / 1e9

    traj = []
    for t in vy:
        s = dfp[dfp.sec <= t]
        k = dfp[dfp.cost <= t]
        traj.append((int(t),
                     s.dem_gj.sum() / 1e9, s.dem_gj.sum() / tot_gj,
                     s.emis_t.sum() / 1e9,
                     k.dem_gj.sum() / 1e9, k.dem_gj.sum() / tot_gj,
                     k.emis_t.sum() / 1e9))
    tj = pd.DataFrame(traj, columns=["year", "sec_ej", "sec_share",
                                     "sec_gt", "cost_ej", "cost_share",
                                     "cost_gt"])
    # chain basis (2026-09-25): each (country, fuel) pair is tested against
    # its own chain's disruption probability, and only the chain's net
    # imports can clear for security (fig5_chain.panel_b_data); the
    # country-level block above is kept for reference only
    from .fig5_chain import panel_b_data
    dfp, tjc, q_at = panel_b_data(write=False)
    dfp["emis_t"] = dfp.dem_gj * dfp.ef
    tot_gj = dfp.dem_gj.sum()
    tot_ej = tot_gj / 1e9
    tj = pd.DataFrame({"year": tjc.year,
                       "sec_ej": tjc.sec_bn_mmbtu * UMM, "sec_share": tjc.sec_share,
                       "sec_gt": tjc.sec_gt,
                       "cost_ej": tjc.cost_bn_mmbtu * UMM, "cost_share": tjc.cost_share,
                       "cost_gt": tjc.cost_gt})
    tj.to_csv(inputs.MAPS / "global_trajectory.csv", index=False)

    for t in (2030, 2040, 2050):
        r = tj[tj.year == t].iloc[0]
        print(f"{t}: security-rational {r.sec_ej:5.1f} EJ/yr "
              f"({r.sec_share:4.0%} of addressable, {r.sec_gt:.1f} Gt/yr "
              f"avoided) | cost-rational {r.cost_ej:5.1f} EJ/yr "
              f"({r.cost_share:4.0%}, {r.cost_gt:.1f} Gt/yr)")
    print(f"assessed economies: {dfp.country.nunique()}; addressable total "
          f"{tot_ej:.1f} EJ/yr = {tot_gj / UMM / 1e9:.1f} bn MMBtu/yr; "
          f"emissions pool {dfp.emis_t.sum() / 1e9:.1f} Gt/yr")

    # ---- demand concentration per fuel ----------------------
    conc_rows = []
    for f in FUELS:
        col = f + "_gj"
        by_c = dgc[col].sort_values(ascending=False)
        cell = dg[col].sort_values(ascending=False)
        n5 = max(1, int(0.05 * (cell > 0).sum()))
        top10 = by_c.head(10).sum() / max(by_c.sum(), 1e-9)
        top5c = cell.head(n5).sum() / max(cell.sum(), 1e-9)
        conc_rows.append(
            f"{f} & {by_c.sum() / UMM / 1e9:.2f} & "
            f"{by_c.sum() / 1e9:.1f} & {top10:.0%} & {top5c:.0%}"
            .replace("%", BS + "%"))
        print(f"  {f:11s} {by_c.sum()/1e9:6.1f} EJ/yr  top-10 countries "
              f"{top10:4.0%}  top-5% cells {top5c:4.0%}")
    header = ("Fuel & (bn MMBtu" + BS + ",yr$^{-1}$) & (EJ" + BS
              + ",yr$^{-1}$) & top-10 countries & top-5" + BS
              + "% of cells " + EOL)
    body = (BS + "begin{tabular}{@{}l r r r r@{}}" + NL + BS + "toprule"
            + NL + " & " + BS + "multicolumn{2}{c}{addressable demand} & "
            + BS + "multicolumn{2}{c}{share held by} " + EOL + NL
            + BS + "cmidrule(lr){2-3}" + BS + "cmidrule(l){4-5}" + NL
            + header + NL + BS + "midrule" + NL
            + (" " + EOL + NL).join(conc_rows) + " " + EOL + NL
            + BS + "bottomrule" + NL + BS + "end{tabular}" + NL)
    texdir = inputs.MAPS.parent.parent / "synthetic_fuel_nature"
    (texdir / "tab_demand.tex").write_text(body, encoding="utf-8")

    # ---- regions ----------------------------------------------------------
    from .fig_pptx_pairs import _COUNTRIES
    pts = _COUNTRIES.copy()
    rp = pts.geometry.representative_point()
    pts["lon"], pts["lat"] = rp.x.to_numpy(), rp.y.to_numpy()
    pts = pts.drop_duplicates("country").set_index("country")
    dfp["region"] = [region_of(c, float(pts.lon.get(c, np.nan)),
                               float(pts.lat.get(c, np.nan)))
                     for c in dfp.country]
    dfp["gt_2030"] = q_at(2030, dfp) * dfp.ef / 1e9
    dfp.to_csv(inputs.MAPS / "global_trajectory_countries.csv", index=False)
    reg_sum = dfp.groupby("region").gt_2030.sum().sort_values(
        ascending=False)
    print("CO2 displaced by 2030 (Gt/yr) by region:")
    for r, v in reg_sum.items():
        print(f"  {r:22s} {v:5.2f}")

    # ---- figure -----------------------------------------------------------
    meta_land = meta[meta.cell_type == "land"]
    fig = plt.figure(figsize=(183 * MM, 152 * MM))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.0, 0.92], hspace=0.30,
                          left=0.085, right=0.97, top=0.965,
                          bottom=0.075)
    a = fig.add_subplot(gs[0])
    c = fig.add_subplot(gs[1])

    # a: WHEN each SITE turns — a date, not a magnitude, computed cell by
    # cell (the cell's own firm-hydrogen cost against its host economy's
    # security threshold), so within-country variation is visible
    frames = {y: pd.read_csv(inputs.MAPS / f"lcoh_global_{y}{SUFFIX}.csv")
              .set_index("cell_id") for y in YEARS}
    cells = frames[YEARS[0]].index
    med = pd.Series(np.median(np.column_stack(
        [frames[y].loc[cells, "lcoh_usd_gj"] for y in YEARS]), axis=1),
        index=cells)
    from .fig5a_chain import q_h2
    QH = q_h2()                        # hydrogen feedstock chain (2026-09-25)
    thr_c, grey_c = {}, {}
    for cy, r in si.iterrows():
        gp = grey_h2_price(cy)
        if np.isfinite(gp) and gp > 0:
            grey_c[cy] = gp
            thr_c[cy] = r.codf_hi_usd_gj * float(QH.get(cy, 0.0))
    cell_yr = {}
    for cid in med.index:
        host = meta_land.country.get(cid)
        if host is None or host not in thr_c:
            continue
        pi_t = med[cid] * g - grey_c[host]
        k = np.nonzero(pi_t <= thr_c[host])[0]
        if len(k):
            cell_yr[int(cid)] = float(vy[k[0]])
    print(f"cell-level security parity: {len(cell_yr)} of {len(med)} "
          f"cells clear by 2050 "
          f"(median {np.median(list(cell_yr.values())):.0f})")
    # kept for the slides' regional zooms (fig_slides2026)
    pd.Series(cell_yr, name="security_year").rename_axis("cell_id") \
        .to_csv(inputs.MAPS / "cell_security_year.csv")
    _nat_map(fig, a, cell_yr, "viridis_r", 2025, 2050,
             "build year in which a site first becomes security-rational, "
             "cell by cell (uncoloured: not before 2050, or no data)", "")
    a.text(-0.075, 1.05, "a", transform=a.transAxes, fontsize=9,
           fontweight="bold", va="top")

    # c: the trajectory, stacked by region, with the CO2 lines
    order = [r for r in REGION_COL if r in set(dfp.region)]
    stack = []
    for r in order:
        d = dfp[dfp.region == r]
        stack.append([q_at(tt, d).sum() / 1e9 / UMM
                      for tt in vy])
    c.stackplot(vy, stack, colors=[REGION_COL[r] for r in order],
                labels=order, lw=0.3, edgecolor="white")
    c.set_xlim(2025, 2050)
    ymax = float(tj.sec_ej.max()) / UMM * 1.22
    c.set_ylim(0, ymax)
    c.set_xlabel("Build year")
    c.set_ylabel("Eligible fuel demand (billion MMBtu yr$^{-1}$)")
    c.set_title(f"All {dfp.country.nunique()} assessed economies", loc="left",
                fontsize=8, color="#3A4550", pad=3)
    for sp in ("top", "right"):
        c.spines[sp].set_visible(False)
    c.legend(fontsize=8, frameon=False, ncol=2, loc="upper left",
             bbox_to_anchor=(0.01, 1.0), handlelength=1.2, columnspacing=1.2,
             labelspacing=0.35, borderaxespad=0.2)
    c.text(-0.075, 1.10, "b", transform=c.transAxes, fontsize=9,
           fontweight="bold", va="top")

    fig.savefig(OUT / "fig_global_traj.pdf", bbox_inches="tight")
    fig.savefig(OUT / "fig_global_traj.png", dpi=600,
                bbox_inches="tight")
    plt.close(fig)
    # the map alone, for Extended Data: the trajectory panel moved into the
    # main Figure 5 (fig_main_carbon.py, 2026-09-17)
    fig2 = plt.figure(figsize=(183 * MM, 92 * MM))
    a2 = fig2.add_axes([0.02, 0.05, 0.96, 0.92])
    _nat_map(fig2, a2, cell_yr, "viridis_r", 2025, 2050,
             "build year in which a site first becomes security-rational, "
             "cell by cell (uncoloured: not before 2050, or no data)", "")
    fig2.savefig(OUT / "fig_global_traj_map.pdf", bbox_inches="tight")
    fig2.savefig(OUT / "fig_global_traj_map.png", dpi=600,
                 bbox_inches="tight")
    plt.close(fig2)
    print("saved fig_global_traj.(pdf|png), fig_global_traj_map.(pdf|png), "
          "global_trajectory.csv, tab_demand.tex")


if __name__ == "__main__":
    main()
