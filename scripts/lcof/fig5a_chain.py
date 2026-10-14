"""
fig5a_chain.py — Figure 5a on the fuel-chain basis (2026-09-25 audit).

The published panel credited each economy's whole expected security
damage (ESD, built on ALL gross oil and gas imports) against the share of
NET imports of the addressable bill that a cheapest-first 1%-of-GDP
portfolio retires. That overstated the security value 1.7-19x, left
economies whose cheapest fuel is gas-family but whose imports are oil
with no security value, and gave net exporters none at all.

Here every fuel is valued on its own supply chain, as in Fig. 3:

  I_f   net imports along the chain of fuel f, GJ/yr
          ammonia                 Fig. 3 ammonia chain exposure x demand
                                  (product net imports + gas/coal feedstock)
          e-diesel, e-kerosene,   Fig. 3 diesel-and-jet chain exposure x
          ethanol                 demand (product net imports + crude)
          e-methane, methanol     net gas dependence x demand
  q_f   expected fraction of the year a marginal imported GJ of the chain
        is lost: the q_eff construction of security.py (supplier cut-off
        s1 strands it with the top-supplier share, a chokepoint s2 strands
        all of it; IEA stocks cover oil chains) applied per chain; zero
        where the chain has no net imports
  w_f   = CoDF_hi x q_f x m_f, $ per imported GJ retired (the valuation of
        the security-parity equation: higher value, central event rate)

Portfolio (1% of GDP, land and demand limits as in security_budget):
  main case (2026-10-02: Fig. 4a must spend the budget the way
  Fig. 5 and the Methods do) — mode "merit", Fig. 5's own merit order:
  cell-fuel pairs by rising premium until the budget is spent; imports
  retired within each chain are min(domestic f, I_f).
  sensitivity — mode "security", the earlier imports-first order:
  stage 1  maximise sum_f w_f r_f,  r_f <= sum of domestic f,  r_f <= I_f
  stage 2  keep that security value, spend what is left on coverage.

Per economy:  gross = spend / CO2,  net = (spend - sum_f w_f r_f) / CO2.

From scripts/:  conda run -n synfuel python -u -m lcof.fig5a_chain
Writes data/cost/fig5a_chain.csv and
cf_global_final/figures/pptx/fig5a_chain.(pdf|png).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

mpl.use("Agg")

from . import inputs, params as P
from .fig_main_cost import MM, NAT_RC, FUELS
from .fig_pptx_pairs import OUT, SUFFIX
from .coreset import core_countries
from .policy import EF, FOSSIL, CARBON_PRICE
from .supply_demand import firm_h2_potential_gj, lcof_cells, MU_H2
from .security_budget import _grey, family_dependence, _figure_co2
from . import security as S

mpl.rcParams.update(NAT_RC)

BUDGET_PCT = 1.0
GASF = {"e-methane", "ammonia", "methanol"}
OILF = {"e-diesel", "e-kerosene", "ethanol", "marine"}   # marine fuel oil: oil chain, IEA stocks
M_F = {"gas": 1.0, "oil": 1.3}                 # service multipliers (Eq. 1)
SCALE = 1e6                                     # LP in million GJ


def _setup():
    """the same cell layer, demand, comparators and land limit as
    security_budget.compute (median cost layer, cheapest CO2)."""
    meta = inputs.load_meta(2025)
    land = meta[meta.cell_type == "land"].copy()
    lc = pd.read_csv(inputs.MAPS / f"lcoh_global_2025{SUFFIX}.csv").set_index("cell_id")
    land = land.join(lc[["cap_pv", "cap_wind", "lcoh_usd_gj", "lcoe_usd_mwh"]], how="inner")
    land = land[np.isfinite(land.cap_pv) & np.isfinite(land.cap_wind)
                & np.isfinite(land.lcoh_usd_gj)]
    land["pot_h2_gj"] = firm_h2_potential_gj(land)
    dg = pd.read_csv(inputs.MAPS / "demand_fuel_grid.csv", index_col=0)
    cols = [f + "_gj" for f in FUELS]
    dgc = dg.join(meta[["country"]]).groupby("country")[cols].sum()
    dgc.columns = FUELS
    dgc = dgc[dgc.sum(axis=1) > 0]
    grey = _grey(dgc)
    co2df = pd.read_csv(inputs.MAPS / "co2_cost_by_cell.csv").set_index("cell_id")
    lcof = lcof_cells(land, co2df.co2_cost.reindex(land.index).fillna(P.C_CO2_DAC))
    return land, dgc, grey, lcof


def chain_inputs(countries):
    """I-share e_f (net imported share of fuel f's own chain) and q_f."""
    au = pd.read_csv(inputs.MAPS / "figure3_country_audit.csv")
    amm = au[au.version == "ammonia"].set_index("country")
    ft = au[au.version == "ft"].set_index("country")
    dep_gas, dep_oil = family_dependence(countries)
    vi = pd.read_csv(inputs.MAPS / "vulnerability_inputs.csv").set_index("country")
    rates, _ = S._scenario_rates()
    (p1, d1), (p2, d2) = rates["s1"], rates["s2"]
    q1 = np.sqrt(p1[0] * p1[1]) * d1 / 12
    q2 = np.sqrt(p2[0] * p2[1]) * d2 / 12

    med_top = {k: float(vi[k].median()) for k in ("top_crude", "top_refined", "top_gas")}
    # 2026-10-07: nitrogen balance (ammonia and nitrogen fertilizers, 2025) for the
    # ammonia chain of the economies outside the Fig. 3 set
    from .nitrogen_consumption import nitrogen_hhi
    n_bal = pd.read_csv(inputs.MAPS / "ammonia_consumption.csv", index_col=0)
    n_hhi = nitrogen_hhi()
    E, Q, TOP, QA, QB = {}, {}, {}, {}, {}
    for c in countries:
        e_gas = float(dep_gas.get(c, np.nan))
        e_h2 = float(amm.feedstock_import_dependence.get(c, np.nan)) if c in amm.index else np.nan
        e_h2 = e_h2 if np.isfinite(e_h2) else e_gas      # grey hydrogen's gas/coal feedstock
        if c in amm.index and c in ft.index:
            e_amm = float(amm.import_exposure.get(c, np.nan))
            e_ft = float(ft.import_exposure.get(c, np.nan))
            ft_dir = float(ft.import_exposure_direct.get(c, 0.0)) if np.isfinite(e_ft) else 0.0
            amm_dir = float(amm.import_exposure_direct.get(c, 0.0)) if np.isfinite(e_amm) else 0.0
        else:
            # outside the Fig. 3 set no product trade is assembled: the chain
            # falls back to its fuel family (ammonia on its gas feedstock,
            # oil-family fuels on net oil dependence)
            e_amm, e_ft = e_gas, float(dep_oil.get(c, np.nan))
            ft_dir = amm_dir = 0.0
            # ammonia: net-imported share of the nitrogen it uses, plus the domestic
            # share times the import dependence of its gas (or coal) feedstock
            m_n = float(n_bal.n_import_share.get(c, np.nan))
            if np.isfinite(m_n):
                feed = e_h2 if np.isfinite(e_h2) else 0.0
                e_amm = min(m_n + (1.0 - m_n) * feed, 1.0)
                amm_dir = m_n
        # a missing supplier share takes the cross-country median
        t_cr = float(vi.top_crude.get(c, med_top["top_crude"]))
        t_rf = float(vi.top_refined.get(c, med_top["top_refined"]))
        t_gs = float(vi.top_gas.get(c, np.nan))
        t_oil_fb = np.nanmean([t_cr, t_rf]) if np.isfinite([t_cr, t_rf]).any() else np.nan
        t_cr = t_cr if np.isfinite(t_cr) else t_oil_fb
        t_rf = t_rf if np.isfinite(t_rf) else t_oil_fb
        # a row present with both oil shares blank (Bangladesh, Belarus)
        # takes the median too, not zero
        t_cr = t_cr if np.isfinite(t_cr) else med_top["top_crude"]
        t_rf = t_rf if np.isfinite(t_rf) else med_top["top_refined"]
        # no gas market: gas-family fuels displace oil products (as in the budget)
        t_gs = t_gs if np.isfinite(t_gs) else t_rf
        hhi_nh3 = float(amm.supplier_hhi_product.get(c, np.nan))
        if not np.isfinite(hhi_nh3):
            hhi_nh3 = float(n_hhi.hhi_nitrogen.get(c, np.nan))
        hhi_nh3 = hhi_nh3 if np.isfinite(hhi_nh3) else t_gs
        # top-supplier share of each chain's imports, weighted by route
        if np.isfinite(e_ft) and e_ft > 0:
            top_oil = (ft_dir * t_rf + (e_ft - ft_dir) * t_cr) / e_ft
        else:
            top_oil = t_cr
        if np.isfinite(e_amm) and e_amm > 0:
            # ammonia product: supplier HHI stands in for the top share
            # (HHI <= top share, so this errs low); feedstock: gas
            top_amm = (amm_dir * hhi_nh3 + (e_amm - amm_dir) * t_gs) / e_amm
        else:
            top_amm = t_gs
        iea = c in S.IEA
        for f in FUELS + ["hydrogen"]:
            if f == "hydrogen":
                e, top, oil = e_h2, t_gs, False
            elif f == "ammonia":
                e, top, oil = e_amm, top_amm, False
            elif f in OILF:
                e, top, oil = e_ft, top_oil, True
            else:
                e, top, oil = e_gas, t_gs, False
            e = float(np.clip(e, 0, 1)) if np.isfinite(e) else 0.0
            top = float(np.clip(top, 0, 1)) if np.isfinite(top) else 0.0
            m1 = 0.5 if (iea and oil) else 0.0
            m2 = 1.0 if (iea and oil) else 0.0
            qa = q1 * top * (1 - m1) if e > 0 else 0.0     # supplier cut-off part
            qb = q2 * (1 - m2) if e > 0 else 0.0           # chokepoint part
            E[(c, f)], Q[(c, f)], TOP[(c, f)] = e, qa + qb, top
            QA[(c, f)], QB[(c, f)] = qa, qb
    idx = pd.MultiIndex.from_tuples(list(E), names=["country", "fuel"])
    return pd.DataFrame({"e": list(E.values()), "q": list(Q.values()),
                         "q_s1": list(QA.values()), "q_s2": list(QB.values()),
                         "top": list(TOP.values())}, index=idx)


def _portfolio(prem, cell, fuel, pot, dem, mu, ef, w, cap, budget, mode="security"):
    """x in million GJ. mode 'security': two-stage (max security value,
    then max coverage); 'justified': max (security value - premium spend),
    i.e. build only where the chain value covers the premium.
    Returns x (GJ), r (GJ per fuel)."""
    if mode == "merit":
        # Fig. 5's own merit order (security_budget._curve): cell-fuel pairs
        # by rising premium (stable sort), each taking the smaller of the
        # fuel's remaining demand and the cell's remaining land-limited
        # hydrogen, until the budget is spent; the last pair is taken in part
        rem_h2, rem_d = pot.astype(float).copy(), dem.astype(float).copy()
        x = np.zeros(len(prem))
        spent = 0.0
        for k in np.argsort(prem, kind="stable"):
            ci, fi = cell[k], fuel[k]
            if rem_d[fi] <= 0.0 or rem_h2[ci] <= 0.0:
                continue
            q = min(rem_d[fi], rem_h2[ci] / mu[fi])
            if q <= 0.0:
                continue
            last = prem[k] > 0 and spent + q * prem[k] > budget
            if last:
                q = max(budget - spent, 0.0) / prem[k]
            x[k] = q
            rem_d[fi] -= q
            rem_h2[ci] -= q * mu[fi]
            spent += q * prem[k]
            if last:
                break
        return x, None
    from scipy.optimize import linprog
    from scipy.sparse import coo_matrix
    n, nc, nf = len(prem), int(pot.size), int(dem.size)
    nv = n + nf
    rows, cols, vals, b = [], [], [], []
    r = 0
    rows += [r] * n; cols += list(range(n)); vals += list(prem); b.append(budget / SCALE); r += 1
    for k in range(n):
        rows.append(r + cell[k]); cols.append(k); vals.append(mu[fuel[k]])
    b += list(pot / SCALE); r += nc
    for k in range(n):
        rows.append(r + fuel[k]); cols.append(k); vals.append(1.0)
    b += list(dem / SCALE); r += nf
    for k in range(n):                          # r_f <= sum_k in f x_k
        rows.append(r + fuel[k]); cols.append(k); vals.append(-1.0)
    for j in range(nf):
        rows.append(r + j); cols.append(n + j); vals.append(1.0)
    b += [0.0] * nf; r += nf
    A = coo_matrix((vals, (rows, cols)), shape=(r, nv)).tocsr()
    bounds = [(0, None)] * n + [(0, cap[j] / SCALE) for j in range(nf)]
    c1 = np.zeros(nv); c1[n:] = -w
    if mode == "justified":
        c1[:n] = prem
    if mode == "cheapest":                       # the most fuel for the money
        c1[:] = 0.0; c1[:n] = -1.0
    s1 = linprog(c1, A_ub=A, b_ub=np.array(b), bounds=bounds, method="highs")
    if not s1.success:
        raise RuntimeError(s1.message)
    if mode == "cheapest":
        return s1.x[:n] * SCALE, s1.x[n:] * SCALE
    # stage 2: hold the stage-1 objective (security value; for 'justified'
    # security value net of spend), then settle the fuel quantity, which
    # stage 1 leaves undetermined wherever a cell's premium is zero or
    # equals the chain value it earns
    from scipy.sparse import vstack, csr_matrix
    hold = c1.copy()                                    # c1 . x <= s1.fun
    A2 = vstack([A, csr_matrix(hold)]).tocsr()
    b2 = np.array(b + [s1.fun + abs(s1.fun) * 1e-7])
    # security mode buys the most fuel at that value; the justified tranche
    # keeps the least, so zero-premium (cost-parity) cells, which need no
    # security case, are not counted in it
    c2 = np.zeros(nv); c2[:n] = 1.0 if mode == "justified" else -1.0
    s2 = linprog(c2, A_ub=A2, b_ub=b2, bounds=bounds, method="highs")
    if not s2.success:
        raise RuntimeError(s2.message)
    return s2.x[:n] * SCALE, s2.x[n:] * SCALE


def write_chain_table():
    """chain exposure and disruption probability for every economy in the
    security ledger, six fuels plus the hydrogen backstop — the one table
    every security-value figure reads (Fig. 5, parity, ledger, cases)."""
    si = pd.read_csv(inputs.MAPS / "security_index.csv", index_col=0)
    ch = chain_inputs(list(si.index))
    ch.to_csv(inputs.MAPS / "chain_q.csv")
    h = ch.xs("hydrogen", level="fuel")
    print(f"chain_q.csv: {len(si)} economies; hydrogen chain q median {h.q.median():.4f}, "
          f"{int((h.q > 0).sum())} with feedstock imports (country q_eff median "
          f"{si.q_eff.median():.4f})")
    return ch


def q_h2():
    """hydrogen-backstop disruption probability per economy (chain basis)."""
    return pd.read_csv(inputs.MAPS / "chain_q.csv").query("fuel == 'hydrogen'")         .set_index("country").q


def main():
    write_chain_table()
    d = compute(write=True)
    figure(d)
    return d


def compute(budget_pct=BUDGET_PCT, value="hi", rate=1.0, mode="merit", write=False,
            setup=None, verbose=True, import_only=False):
    """value 'hi' = CoDF_hi (ENTSOG anchor), 'central' = CoDF (ACER);
    rate multiplies the event rates (q is linear in them)."""
    land, dgc, grey, lcof = setup or _setup()
    si = pd.read_csv(inputs.MAPS / "security_index.csv", index_col=0)
    sb = pd.read_csv(inputs.MAPS / "security_budget.csv", index_col=0)
    core = [c for c in core_countries(sb.index) if c in sb.index]
    ch = chain_inputs(core)
    efv = np.array([EF[FOSSIL[f]["ef"]] for f in FUELS])
    muv = np.array([MU_H2[f] for f in FUELS])
    rec = []
    for c in core:
        cc = land.index[land.country == c]
        dem = dgc.loc[c, FUELS].to_numpy(float)
        gdp = float(si.gdp_usd[c])
        codf_hi = float(si.codf_hi_usd_gj[c] if value == "hi" else si.codf_usd_gj[c])
        pot = land.pot_h2_gj.reindex(cc).to_numpy()
        prem, cell, fuel = [], [], []
        dvec = dem.copy()
        for j, f in enumerate(FUELS):
            if dem[j] <= 0 or not np.isfinite(grey.loc[c, f]):
                dvec[j] = 0.0
                continue
            prem.append(np.maximum(lcof.loc[cc, f].to_numpy() - grey.loc[c, f], 0.0))
            cell.append(np.arange(len(cc)))
            fuel.append(np.full(len(cc), j))
        prem, cell, fuel = np.concatenate(prem), np.concatenate(cell), np.concatenate(fuel)
        e = np.array([ch.loc[(c, f), "e"] for f in FUELS])
        # rate: one multiplier, or (supplier cut-off, chokepoint) multipliers
        r1, r2 = (rate, rate) if np.isscalar(rate) else rate
        q = np.array([r1 * ch.loc[(c, f), "q_s1"] + r2 * ch.loc[(c, f), "q_s2"] for f in FUELS])
        mf = np.array([M_F["gas" if f in GASF else "oil"] for f in FUELS])
        w = codf_hi * q * mf
        cap = e * dvec
        budget = budget_pct / 100 * gdp
        if import_only:          # only the tranche that retires chain imports
            dvec = np.minimum(dvec, cap)
        x, rr = _portfolio(prem, cell, fuel, pot, dvec, muv, efv, w, cap, budget, mode)
        # the solution must respect every limit it was given
        byf_chk = np.bincount(fuel, weights=x, minlength=len(FUELS))
        if mode in ("cheapest", "merit"):        # imports retired within each chain
            rr = np.minimum(byf_chk, cap)
        h2 = np.bincount(cell, weights=x * muv[fuel], minlength=len(cc))
        tol = 1e-4
        assert (prem * x).sum() <= budget * (1 + tol) + 1e3, (c, "budget")
        assert (h2 <= pot * (1 + tol) + 1e3).all(), (c, "land")
        assert (byf_chk <= dvec * (1 + tol) + 1e3).all(), (c, "demand")
        assert (rr <= cap * (1 + tol) + 1e3).all() and (rr <= byf_chk * (1 + tol) + 1e3).all(), (c, "retire")
        spend = float((prem * x).sum())
        byf = np.bincount(fuel, weights=x, minlength=len(FUELS))
        co2 = float((byf * efv).sum())
        sv = float((w * rr).sum())
        row = dict(country=c, gdp_usd=gdp, spend_bn=spend / 1e9, co2_mt=co2 / 1e6,
                   cov=float(x.sum() / dem.sum()), sec_value_bn=sv / 1e9,
                   chain_import_share=float(cap.sum() / dem.sum()),
                   retired_share=float(rr.sum() / cap.sum()) if cap.sum() > 0 else np.nan,
                   gross_usd_t=spend / co2 if co2 > 0 else np.nan,
                   net_usd_t=(spend - sv) / co2 if co2 > 0 else np.nan,
                   p_co2_usd_t=float(CARBON_PRICE.get(c, 0.0)),
                   old_gross_usd_t=float(sb.abate_cost_1.get(c, np.nan)),
                   old_net_hi_usd_t=float(sb.abate_net_hi_1.get(c, np.nan)))
        for j, f in enumerate(FUELS):
            row[f"x_{f}_share"] = float(byf[j] / x.sum()) if x.sum() > 0 else 0.0
            row[f"I_{f}_share"] = float(e[j])
            row[f"q_{f}"] = float(q[j])
            row[f"ret_{f}_gj"] = float(rr[j])
        rec.append(row)
    d = pd.DataFrame(rec).set_index("country")
    if write:
        d.to_csv(inputs.MAPS / "fig5a_chain.csv")
    if not verbose:
        return d
    fin = d.net_usd_t.dropna()
    imp = d[d.chain_import_share > 0]
    print(f"{len(d)} economies ({len(imp)} with chain imports); net<=0 in "
          f"{int((imp.net_usd_t <= 0).sum())} of {len(imp)}; median gross "
          f"{d.gross_usd_t.median():.0f}, median net {imp.net_usd_t.median():.0f} $/t "
          f"(old: {int((d.old_net_hi_usd_t <= 0).sum())} of 26, median gross "
          f"{d.old_gross_usd_t.median():.0f}, net {d.old_net_hi_usd_t.median():.0f})")
    print(d[["chain_import_share", "retired_share", "cov", "co2_mt", "gross_usd_t",
             "net_usd_t", "old_gross_usd_t", "old_net_hi_usd_t"]].round(2).to_string())
    return d


def figure(d):
    fig, ax = plt.subplots(figsize=(100 * MM, 118 * MM))
    fig.subplots_adjust(left=0.27, right=0.97, top=0.97, bottom=0.10)
    draw_a(ax, d)
    fig.savefig(OUT / "fig5a_chain.pdf", bbox_inches="tight")
    fig.savefig(OUT / "fig5a_chain.png", dpi=600, bbox_inches="tight")
    plt.close(fig)
    print("saved fig5a_chain.(pdf|png)")


def draw_a(ax, d, legend_anchor=(-0.02, 1.005)):
    # rows grouped as in the published panel: net importers and net
    # exporters of the oil and gas families (security_budget.import_pct);
    # every row still carries both circles, valued chain by chain
    sb = pd.read_csv(inputs.MAPS / "security_budget.csv", index_col=0)
    dd = pd.DataFrame({"abate_cost_1": d.gross_usd_t, "abate_net_hi_1": d.net_usd_t,
                       "import_pct": sb.import_pct.reindex(d.index),
                       "p_co2_usd_t": d.p_co2_usd_t})
    info = _figure_co2(dd, {}, ax=ax, save=False, legend=False,
                       xlim=(-300.0, 1000.0), xstep=250)
    h = info["handles"]
    # the security value per tonne of every row, as a column outside the
    # axis (the grey segment's length), so no label sits on the data
    from matplotlib.transforms import blended_transform_factory
    tr = blended_transform_factory(ax.transAxes, ax.transData)
    sv = (d.gross_usd_t - d.net_usd_t)
    for i, c in enumerate(info["order"]):
        v = float(sv.get(c, np.nan))
        if np.isfinite(v):
            ax.text(1.085, i, f"{v:,.0f}", transform=tr, fontsize=7,
                    ha="right", va="center", color="#5A6570")
    ax.text(1.085, len(info["order"]) - 0.35, "Security\nmargin\n(US\\$ t$^{-1}$)",
            transform=tr, fontsize=6.5, ha="right", va="bottom",
            color="#5A6570", linespacing=1.1)
    ax.legend(handles=[h[0], h[1], h[2], h[3], h[4]], loc="lower left",
              bbox_to_anchor=legend_anchor, ncol=2, fontsize=6.8, frameon=False,
              handlelength=1.4, handletextpad=0.5, columnspacing=1.0,
              borderaxespad=0.0)
    return info


def draw_a_hurdle(ax, d, legend_anchor=(-0.02, 1.02)):
    """Panel a, circles with the carbon price as the hurdle (2026-09-30).
    Open circle = production premium at normal prices per t CO2 (what climate
    policy alone must pay); arrow = security value per t CO2 (value printed);
    filled circle = premium net of disruption value. The magenta tick is the
    carbon price in force: the open circle never reaches it, the filled circle
    clears it (green) in some importers. Nature style, no formulas."""
    from matplotlib.lines import Line2D
    from .security_budget import SHORT
    sb = pd.read_csv(inputs.MAPS / "security_budget.csv", index_col=0)
    imp = sb.import_pct.reindex(d.index) > 0
    g = d.loc[imp, "gross_usd_t"]
    n = d.loc[imp, "net_usd_t"]
    pc = d.loc[imp, "p_co2_usd_t"].fillna(0.0)
    order = list((n - pc).sort_values(ascending=False).index)   # cleared at the top
    XLO, XHI = -300.0, 1000.0
    INKC, ARROW, MAG, GREENC, BLUEC = "#1F3A5F", "#9AA3AC", "#B4116F", "#1F9E6E", "#2E5E8E"
    ax.axvline(0, color="#C9CFD6", lw=0.6, zorder=1)
    for i, c in enumerate(order):
        ok = n[c] <= pc[c]
        gg = min(float(g[c]), XHI - 25)
        vv = max(float(n[c]), XLO + 25)
        ax.annotate("", xy=(vv + 10, i), xytext=(gg - 10, i),
                    arrowprops=dict(arrowstyle="-|>", color=ARROW, lw=1.0,
                                    mutation_scale=6, shrinkA=0, shrinkB=0), zorder=3)
        ax.text(gg - 14, i + 0.36, f"{g[c] - n[c]:,.0f}", fontsize=5.5, color="#6A7480",
                ha="right", va="center", zorder=4)
        ax.plot([pc[c], pc[c]], [i - 0.38, i + 0.38], color=MAG, lw=1.3, zorder=5,
                solid_capstyle="butt")
        ax.scatter([gg], [i], s=16, facecolor="white", edgecolor=INKC, linewidths=0.8, zorder=6)
        ax.scatter([vv], [i], s=20, color=INKC, zorder=7, lw=0)
        if n[c] < XLO + 25:
            ax.text(vv + 20, i - 0.36, f"{n[c]:,.0f}", fontsize=5.5, color=INKC,
                    ha="left", va="center", zorder=8)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([SHORT.get(c, c) for c in order], fontsize=7)
    ax.tick_params(axis="y", length=0)
    ax.set_xlim(XLO, XHI)
    ax.set_ylim(-0.7, len(order) - 0.3)
    ax.set_xticks(np.arange(-250, XHI + 1, 250))
    ax.tick_params(axis="x", labelsize=7)
    ax.grid(axis="x", alpha=0.25, lw=0.4)
    ax.set_axisbelow(True)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    handles = [Line2D([], [], marker="o", ls="none", ms=4.5, mfc="white", mec=INKC,
                      label="Premium at normal prices"),
               Line2D([], [], color=ARROW, lw=1.0, marker="<", ms=3.5, markevery=[0],
                      label="Security value"),
               Line2D([], [], marker="|", ls="none", ms=8, mew=1.3, color=MAG,
                      label="Carbon price"),
               Line2D([], [], marker="o", ls="none", ms=4.8, color=INKC,
                      label="Net of disruption value")]
    # left-margin brackets: which rows clear the carbon price
    from matplotlib.transforms import blended_transform_factory
    tr = blended_transform_factory(ax.transAxes, ax.transData)
    ncl = int((n <= pc).sum())
    groups = [(len(order) - ncl, len(order) - 1, "clears the\ncarbon price", "#1F7A4D"),
              (0, len(order) - ncl - 1, "still above the carbon price", "#5A6570")]
    XB = -0.36
    for lo, hi, lab, col in groups:
        ax.plot([XB, XB], [lo - 0.35, hi + 0.35], transform=tr, color=col, lw=0.8,
                clip_on=False)
        for yy in (lo - 0.35, hi + 0.35):
            ax.plot([XB, XB + 0.012], [yy, yy], transform=tr, color=col, lw=0.8, clip_on=False)
        ax.text(XB - 0.012, (lo + hi) / 2, lab, transform=tr, rotation=90, fontsize=6.5,
                color=col, ha="right", va="center", linespacing=1.1, fontweight="bold")
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=legend_anchor, ncol=2,
              fontsize=6.5, frameon=False, handlelength=1.2, handletextpad=0.5,
              columnspacing=1.2, borderaxespad=0.0)
    return order


def draw_a_bars(ax, d, legend_anchor=(-0.02, 1.005)):
    """Panel a, plain-language version (2026-09-30): per importer, the extra
    cost of synthetic fuel per tonne of CO2 (grey bar) next to the security
    value per tonne (inner bar, green where it covers the whole extra cost),
    with the carbon price as a tick. No subtraction, no negative axis."""
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    from .security_budget import SHORT
    sb = pd.read_csv(inputs.MAPS / "security_budget.csv", index_col=0)
    imp = sb.import_pct.reindex(d.index) > 0
    cost = d.loc[imp, "gross_usd_t"]
    sec = cost - d.loc[imp, "net_usd_t"]
    pc = d.loc[imp, "p_co2_usd_t"].fillna(0.0)
    order = list((sec / cost).sort_values().index)            # best covered at the top
    GREYC, BLUEC, GREENC, MAG, INKC = "#D5DAE0", "#2E5E8E", "#1F9E6E", "#B4116F", "#1F3A5F"
    XHI = 1250.0
    ARR = "#1F7A4D"
    fig = ax.figure
    pt_per_unit = ax.get_position().width * fig.get_figwidth() * 72 / XHI
    for i, c in enumerate(order):
        ax.barh(i, cost[c], height=0.72, color=GREYC, zorder=2, lw=0)
        ax.barh(i, sec[c], height=0.32, color=BLUEC, zorder=3, lw=0)
        lab = f"{sec[c]:,.0f}"
        x_end = max(cost[c], sec[c])
        ax.annotate(lab, xy=(x_end, i), xytext=(3, 0), textcoords="offset points",
                    fontsize=6, color=BLUEC, va="center", ha="left", zorder=5)
        m = sec[c] - cost[c]
        if m > 0:                                   # security margin: loss avoided beyond the cost
            yy = i - 0.25
            if m * pt_per_unit >= 7:                # arrows shorter than a head are left out
                ax.annotate("", xy=(sec[c], yy), xytext=(cost[c], yy),
                            arrowprops=dict(arrowstyle="-|>", color=ARR, lw=0.9, mutation_scale=6,
                                            shrinkA=0, shrinkB=0), zorder=6)
            ax.annotate(f"+{m:,.0f}", xy=(x_end, i), xytext=(3 + 3.4 * len(lab) + 4, 0),
                        textcoords="offset points", fontsize=6, color=ARR, va="center",
                        ha="left", zorder=6)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([SHORT.get(c, c) for c in order], fontsize=7)
    ax.tick_params(axis="y", length=0)
    ax.set_xlim(0, XHI)
    ax.set_ylim(-0.7, len(order) - 0.3)
    ax.set_xticks([0, 250, 500, 750, 1000])
    ax.tick_params(axis="x", labelsize=7)
    ax.grid(axis="x", alpha=0.25, lw=0.4)
    ax.set_axisbelow(True)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    handles = [Patch(color=GREYC, label="Extra cost over normal import price"),
               Patch(color=BLUEC, label="Avoided disruption loss"),
               Line2D([], [], color=ARR, lw=0.9, marker=">", ms=3.5, markevery=[1],
                      label="Security margin")]
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=legend_anchor, ncol=2,
              fontsize=6.5, frameon=False, handlelength=1.2, handletextpad=0.5,
              columnspacing=1.2, borderaxespad=0.0)
    ax._headline = (int((sec > pc).sum()), len(order), float(sec.median()), float(pc.median()),
                    int((sec >= cost).sum()))
    return order


def draw_a_simple(ax, d, legend_anchor=(-0.02, 1.005)):
    """Panel a, reader version (2026-09-30): importers only; hollow = normal
    benchmark (premium at normal import prices per tonne of CO2), arrow to
    the filled dot = after the security margin; shaded band left of zero =
    security alone pays; magenta tick = carbon price in force. No formulas,
    no side column, no colour code."""
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    from .security_budget import SHORT
    sb = pd.read_csv(inputs.MAPS / "security_budget.csv", index_col=0)
    imp = sb.import_pct.reindex(d.index) > 0
    g = d.loc[imp, "gross_usd_t"]
    n = d.loc[imp, "net_usd_t"]
    pc = d.loc[imp, "p_co2_usd_t"].fillna(0.0)
    order = list(n.sort_values(ascending=False).index)       # most negative at the top
    XLO, XHI = -600.0, 1000.0                               # wide enough for Ireland (-442)
    INKC, GREYC, MAG, SHADE = "#1F3A5F", "#8A94A0", "#B4116F", "#E3F2EA"
    ax.axvspan(XLO, 0, color=SHADE, zorder=0, lw=0)
    ax.axvline(0, color="#9AA3AC", lw=1.0, zorder=1)
    ax.text((XLO + 0) / 2, 1.5, "security\nalone\npays", fontsize=7,
            color="#3A4550", va="center", ha="center", linespacing=1.1)
    # arrow ends are trimmed in points by each circle's radius plus a gap, so no
    # arrow touches a circle; arrows too short for a head are left out
    S_OPEN, S_FILL, GAP, HEAD = 20, 24, 1.6, 5.0
    r_open = np.sqrt(S_OPEN) / 2 + 0.5          # marker radius in points (+ half edge)
    r_fill = np.sqrt(S_FILL) / 2
    fig = ax.figure
    pos = ax.get_position()
    pt_per_unit = pos.width * fig.get_figwidth() * 72 / (XHI - XLO)
    for i, c in enumerate(order):
        gg = min(float(g[c]), XHI - 30)
        vv = max(float(n[c]), XLO + 30)
        length_pt = abs(gg - vv) * pt_per_unit
        if length_pt > r_open + r_fill + 2 * GAP + HEAD:
            ax.annotate("", xy=(vv, i), xytext=(gg, i),
                        arrowprops=dict(arrowstyle="-|>", color=GREYC, lw=1.1,
                                        mutation_scale=7, shrinkA=r_open + GAP,
                                        shrinkB=r_fill + GAP), zorder=3)
        ax.scatter([gg], [i], s=S_OPEN, facecolor="white", edgecolor=INKC, linewidths=1.0, zorder=5)
        ax.scatter([vv], [i], s=S_FILL, color=INKC, zorder=6)
        m = float(g[c]) - float(n[c])                       # the security margin, US$ per tonne
        ax.annotate(f"{m:,.0f}", xy=(gg, i), xytext=(r_open + 2.0, 0),
                    textcoords="offset points", fontsize=5.8, color="#5A6570",
                    ha="left", va="center", zorder=7, annotation_clip=False)
        if float(n[c]) <= 0:                         # every negative result, printed
            ax.annotate(f"{float(n[c]):,.0f}", xy=(vv, i), xytext=(-(r_fill + 2.0), 0),
                        textcoords="offset points", fontsize=5.8, color=INKC,
                        ha="right", va="center", zorder=7, annotation_clip=False)
        if float(g[c]) > XHI - 30:
            ax.text(gg - 28, i + 0.42, f"{float(g[c]):,.0f}", fontsize=6.2, color=INKC,
                    ha="right", va="center", zorder=7)
        ax.plot([pc[c], pc[c]], [i - 0.34, i + 0.34], color=MAG, lw=1.2, zorder=4)
    # the message: security value, in carbon-price units, dwarfs the carbon price
    marg = (g - n)
    nn = int((marg > pc).sum())
    ax._headline = (nn, len(order), float(marg.median()), float(pc.median()))
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([SHORT.get(c, c) for c in order], fontsize=7.4)
    ax.tick_params(axis="y", length=0)
    ax.set_xlim(XLO, XHI)
    ax.set_ylim(-0.7, len(order) - 0.3)
    ax.set_xticks(np.arange(-500, XHI + 1, 250))
    ax.tick_params(axis="x", labelsize=7)
    ax.grid(axis="x", alpha=0.2, lw=0.4)
    ax.set_axisbelow(True)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    handles = [Line2D([], [], marker="o", ls="none", ms=5.5, mfc="white", mec=INKC,
                      label="Premium at normal prices"),
               Line2D([], [], marker="o", ls="none", ms=5.5, color=INKC,
                      label="Net of disruption value"),
               Line2D([], [], color=GREYC, lw=1.3, marker="<", ms=4, markevery=[0],
                      label="Security margin"),
               Line2D([], [], marker="|", ls="none", ms=9, mew=1.2, color=MAG,
                      label="Carbon price")]
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=legend_anchor, ncol=2,
              fontsize=7.0, frameon=False, handlelength=1.2, handletextpad=0.4,
              columnspacing=1.0, borderaxespad=0.0)
    return order


def draw_a_circles(ax, d, legend_anchor=(-0.02, 1.005), margin="arrow", order=None, ylabels=True,
                   legend=True, group_labels=True, band_label=True, xlim=None, mark_justified=False,
                   net_column=True):
    """Panel a, 2026-10-02 (review): the circle version
    with all 30 economies, net importers above a dashed divider and net
    exporters below, labelled at the right as in Fig. 3.

    Reading, per tonne of CO2 displaced: open circle = extra cost over the
    normal import price (support spent / CO2 displaced); grey arrow, with
    its value printed on it = security margin (expected disruption loss
    avoided); filled circle = net cost after the avoided loss; magenta tick =
    carbon price in force. The portfolio is justified when security margin +
    carbon price >= extra cost, i.e. when the filled circle lies left of the
    tick; left of zero the avoided loss alone exceeds the extra cost.

    The empty stretch of the axis below -200 (only Ireland lies there) is
    compressed fourfold and marked with a break, so that the crowded positive
    side gets the width. Where the two circles nearly coincide (net
    exporters) the open circle is drawn as a ring around a smaller dot."""
    from matplotlib.lines import Line2D
    from .security_budget import SHORT
    sb = pd.read_csv(inputs.MAPS / "security_budget.csv", index_col=0)
    is_imp = sb.import_pct.reindex(d.index) > 0
    g, n = d["gross_usd_t"], d["net_usd_t"]
    pc = d["p_co2_usd_t"].fillna(0.0)
    exps = list(n[~is_imp].sort_values(ascending=False).index)   # bottom block
    imps = list(n[is_imp].sort_values(ascending=False).index)    # most negative at the top
    if order is not None:            # 2026-10-07: one row order across the build-year columns of Fig. 4
        exps = [c for c in order["exps"] if c in d.index]
        imps = [c for c in order["imps"] if c in d.index]
    ypos = {c: i for i, c in enumerate(exps)}
    off = len(exps) + 1                                          # one empty row between blocks
    ypos.update({c: off + i for i, c in enumerate(imps)})

    B, K = -200.0, 0.25                                          # compressed below B
    if xlim is not None:             # 2026-10-08: data-driven range
        B, K = xlim[0] - 1.0, 1.0
        # 2026-10-08: the shaded band (net cost below zero) takes at most a quarter of the
        # width; beyond -neg/2 the axis is compressed, with a break, as in the original panel
        neg = max(float(xlim[1]) / 3.0, 100.0)
        if -float(xlim[0]) > neg:
            B = -0.5 * neg
            K = 0.5 * neg / (B - float(xlim[0]))
    # 2026-10-07: installed electrolyser costs put several premia above US$1,000 per
    # tonne, so the axis is also compressed fourfold above B2, with its own break
    B2, K2 = 1000.0, 0.25
    if xlim is not None:
        B2, K2 = xlim[1] + 1.0, 1.0

    def fwd(x):
        x = np.asarray(x, dtype=float)
        return np.where(x < B, B + (x - B) * K, np.where(x > B2, B2 + (x - B2) * K2, x))

    def inv(y):
        y = np.asarray(y, dtype=float)
        return np.where(y < B, B + (y - B) / K, np.where(y > B2, B2 + (y - B2) / K2, y))
    ax.set_xscale("function", functions=(fwd, inv))
    XLO, XMAX = (-1060.0, 2000.0) if xlim is None else (float(xlim[0]), float(xlim[1]))
    SC = (float(fwd(XMAX)) - float(fwd(XLO))) / 1665.0           # offsets below were set on a 1,665-wide axis
    D_DATA = float(fwd(XMAX)) - float(fwd(XLO))
    E_COL = (0.34 / 0.66 if net_column else 0.20 / 0.80) * D_DATA                                 # build-year panels: column strip width
    XHI = float(inv(float(fwd(XMAX)) + (265.0 * SC if xlim is None else E_COL)))  # XMAX..XHI: columns, group labels
    ax.set_xlim(XLO, XHI)
    ax.set_ylim(-0.7, off + len(imps) - 0.3)

    INKC, GREYC, MAG, SHADE, LBL = "#0B4F9E", "#8A94A0", "#B4116F", "#E3F2EA", "#5A6570"
    SECC = "#1B7A4B"                     # 2026-10-05: security value green across Fig. 4 (as the dashed line in b)
    ax.axvspan(XLO, 0, color=SHADE, zorder=0, lw=0)
    ax.axvline(0, color="#9AA3AC", lw=1.0, zorder=1)
    fig = ax.figure
    fig.canvas.draw()
    PT = 72.0 / fig.dpi
    to_disp = ax.transData.transform
    to_data = ax.transData.inverted().transform
    # the band label sits in the middle of the band as drawn
    x_mid = to_data(((to_disp((XLO, 0))[0] + to_disp((0, 0))[0]) / 2, 0))[0]
    if band_label:
        # 2026-10-08: named on the band, low in the importer block where the band is empty
        if xlim is None:
            ax.text(x_mid, off + 3.0, "Avoided loss\nexceeds\nextra cost", fontsize=6.5,
                    color="#3A6B50", va="center", ha="center", linespacing=1.1)
        else:
            ax.text(x_mid, off + 4.5, "Security margin > cost premium", fontsize=6, rotation=90,
                    color="#3A6B50", va="center", ha="center")

    S_OPEN, S_FILL, GAP, HEAD = 20, 24, 1.6, 5.0
    r_open = np.sqrt(S_OPEN) / 2 + 0.5
    r_fill = np.sqrt(S_FILL) / 2
    DIG = 3.1                                                    # digit width at 5.8 pt, points
    col_labels = {}                                              # margin="column": values for the right column
    for c, i in ypos.items():
        gx, nx = float(g[c]), float(n[c])
        xg, xn = to_disp((gx, i))[0], to_disp((nx, i))[0]
        sep_pt = abs(xg - xn) * PT
        arrow = sep_pt > r_open + r_fill + 2 * GAP + HEAD
        if arrow:
            ax.annotate("", xy=(nx, i), xytext=(gx, i),
                        arrowprops=dict(arrowstyle="-|>", color=SECC, lw=1.1,
                                        mutation_scale=7, shrinkA=r_open + GAP,
                                        shrinkB=r_fill + GAP), zorder=3)
        if sep_pt < r_open + r_fill:                             # coincide: ring around a dot
            ax.scatter([nx], [i], s=12, color=INKC, zorder=5, clip_on=False)
            ax.scatter([gx], [i], s=46, facecolor="none", edgecolor=INKC, linewidths=1.0, zorder=6, clip_on=False)
            top = np.sqrt(46) / 2 + 0.5
        else:
            ax.scatter([gx], [i], s=S_OPEN, facecolor="white", edgecolor=INKC, linewidths=1.0, zorder=5, clip_on=False)
            ax.scatter([nx], [i], s=S_FILL, color=INKC, zorder=6, clip_on=False)
            top = 0.0
        if mark_justified and bool(is_imp.get(c, False)) and nx <= float(pc[c]):
            # 2026-10-08: justified = security margin + carbon price cover the extra cost;
            # a green ring around the net-cost dot
            ax.scatter([nx], [i], s=72, facecolor="none", edgecolor=SECC, linewidths=1.3, zorder=7,
                       clip_on=False)
        ax.plot([pc[c], pc[c]], [i - 0.34, i + 0.34], color=MAG, lw=1.2, zorder=4)
        # the security margin is printed on its arrow, clear of the carbon tick
        m = gx - nx
        lab = f"{m:,.0f}"
        half = len(lab) * DIG / 2 + 1.0
        xt = to_disp((float(pc[c]), i))[0]
        lo, hi = min(xg, xn), max(xg, xn)
        if margin == "column":                                   # aligned column at the right instead
            col_labels[c] = lab
        elif margin == "none":                                   # build-year columns: no numbers
            pass
        elif top > 0:                                            # ring: rows are too tight above,
            ax.annotate(lab, xy=(max(gx, nx), i), xytext=(top + 2.0, 0),   # so the margin sits at its right
                        textcoords="offset points", fontsize=5.8, color=LBL,
                        ha="left", va="center", zorder=7, annotation_clip=False)
        else:
            if arrow:
                span_lo, span_hi = lo + r_fill / PT, hi - r_open / PT
                cands = [span_lo + f * (span_hi - span_lo)
                         for f in (0.5, 0.35, 0.65, 0.22, 0.78, 0.9, 0.1, 1.0, 0.0)]
            else:
                cands = [(lo + hi) / 2]
            x0 = to_disp((0.0, i))[0]                            # keep clear of the tick and the zero line
            clear = lambda x: min(abs(x - xt), abs(x - x0)) * PT
            cx = next((x for x in cands if clear(x) > half + 1.8), max(cands, key=clear))
            # a number that sits over a circle is lifted above the circle's top
            over = (abs(cx - xg) * PT < half + r_open + 0.5) or (abs(cx - xn) * PT < half + r_fill + 0.5)
            lift = (max(r_open, r_fill) + 1.0) if (over or not arrow) else 1.4
            ax.annotate(lab, xy=(to_data((cx, 0))[0], i), xytext=(0, lift),
                        textcoords="offset points", fontsize=5.8, color=LBL,
                        ha="center", va="bottom", zorder=7, annotation_clip=False)
        if nx <= 0 and xlim is None:                             # every negative result, printed
            nlab = f"{nx:,.0f}"
            ringed = mark_justified and bool(is_imp.get(c, False)) and nx <= float(pc[c])
            r_lab = np.sqrt(72) / 2 + 0.8 if ringed else r_fill   # clear of the justified ring
            room = (xn - to_disp((XLO, i))[0]) * PT - r_lab - 2.0
            if room >= len(nlab) * DIG + 1.0:
                ax.annotate(nlab, xy=(nx, i), xytext=(-(r_lab + 2.0), 0),
                            textcoords="offset points", fontsize=5.8, color=INKC,
                            ha="right", va="center", zorder=7, annotation_clip=False)
            else:                                                # no room at the left edge
                ax.annotate(nlab, xy=(nx, i), xytext=(r_lab + 1.0, 3.5),
                            textcoords="offset points", fontsize=5.8, color=INKC,
                            ha="left", va="bottom", zorder=7, annotation_clip=False)

    # groups, as in Fig. 3: dashed divider, labels at the right of each block
    ax.plot([XLO, XHI], [len(exps), len(exps)], color=GREYC, lw=0.7, ls=(0, (5, 3)), zorder=2)
    if margin == "column":
        fx = float(fwd(XMAX))
        if xlim is None:
            XCOL, XGRP, XDIV = (float(inv(fx + d * SC)) for d in (85.0, 235.0, 28.0))
        else:                        # fractions of the strip: divider, margin, net cost, group name
            XDIV, XCOL, XGRP = (float(inv(fx + f * E_COL)) for f in
                                 ((0.04, 0.22, 0.92) if net_column else (0.06, 0.38, 0.88)))
        top_row = off + len(imps) - 1
        ax.plot([XDIV, XDIV], [-0.7, top_row + 0.5], color="#DDDDDD", lw=0.5, zorder=1)
        ax.text(XCOL, top_row + 0.75, "Security\nmargin" if xlim is None else "Margin", fontsize=6.3, color=LBL,
                ha="center", va="bottom", linespacing=1.1, zorder=7)
        if xlim is not None and net_column:   # 2026-10-08: net cost column, justified rows in bold
            XNET = float(inv(fx + 0.64 * E_COL))
            ax.text(XNET, top_row + 0.75, "Net", fontsize=6.3, color=INKC,
                    ha="center", va="bottom", linespacing=1.1, zorder=7)
            # 2026-10-13: the two columns carry their unit
            ax.text((XCOL + XNET) / 2, top_row + 1.55, "US\\$ tCO$_2^{-1}$", fontsize=5.8, color=LBL,
                    ha="center", va="bottom", zorder=7)
            for c in ypos:
                jj = mark_justified and bool(is_imp.get(c, False)) and float(n[c]) <= float(pc[c])
                ax.text(XNET, ypos[c], f"{float(n[c]):,.0f}".replace("-", "\u2212"), fontsize=6.3,
                        color=SECC if jj else INKC, fontweight="bold" if jj else "normal",
                        ha="center", va="center", zorder=7)
        for c, lab in col_labels.items():
            ax.text(XCOL, ypos[c], lab, fontsize=6.3, color=LBL, ha="center", va="center", zorder=7)
        if group_labels:
            ax.text(XGRP, off + (len(imps) - 1) / 2, "Net importers", fontsize=7, color=LBL,
                    ha="center", va="center", rotation=90, zorder=6)
            # 2026-10-14: the name is taller than the four exporter rows, so it hangs from just below
            # the dashed line instead of being centred on them (centred, it crossed into the importers)
            ax.text(XGRP, len(exps) - 0.6, "Net exporters", fontsize=7, color=LBL,
                    ha="center", va="top", rotation=90, zorder=6)
    elif group_labels:
        xg_lab = float(inv(float(fwd(XMAX)) + 35.0))
        ax.text(xg_lab, off + (len(imps) - 1) / 2, "Net\nimporters", fontsize=7, color=LBL,
                ha="left", va="center", linespacing=1.15, zorder=6)
        ax.text(xg_lab, (len(exps) - 1) / 2, "Net\nexporters", fontsize=7, color=LBL,
                ha="left", va="center", linespacing=1.15, zorder=6)

    rows = sorted(ypos, key=ypos.get)
    ax.set_yticks([ypos[c] for c in rows])
    ax.set_yticklabels([SHORT.get(c, c) for c in rows] if ylabels else [], fontsize=7.0)
    ax.tick_params(axis="y", length=0)
    if xlim is None:
        ax.set_xticks([-1000, 0, 250, 500, 750, 1000, 2000])
        ax.set_xticklabels(["−1,000", "0", "250", "500", "750", "1,000", "2,000"])
    else:
        step = next(s for s in (100, 200, 250, 500, 1000) if (XMAX - B if B > XLO else XMAX - XLO) / s <= 4)
        tk = np.arange(np.ceil(max(XLO, B) / step) * step, XMAX + 1e-9, step)
        if B > XLO:                                  # one tick in the compressed stretch
            tk = np.r_[np.ceil(XLO / 100.0) * 100.0, tk]
        ax.set_xticks(tk)
        ax.set_xticklabels([f"{v + 0.0:,.0f}".replace("-", "−") if abs(v) > 1e-9 else "0" for v in tk])
    ax.tick_params(axis="x", labelsize=7)
    ax.grid(axis="x", alpha=0.2, lw=0.4)
    ax.set_axisbelow(True)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_bounds(XLO, XMAX)
    # axis break at B: two short slashes across the bottom spine
    for xb in (ax.transAxes.inverted().transform(to_disp((bb, 0)))[0] for bb in (B, B2) if XLO < bb < XMAX):
        for dx in (-0.006, 0.006):
            ax.plot([xb + dx - 0.004, xb + dx + 0.004], [-0.012, 0.012], transform=ax.transAxes,
                    color="#333333", lw=0.8, clip_on=False, zorder=8)
        ax.plot([xb - 0.006, xb + 0.006], [0, 0], transform=ax.transAxes, color="white",
                lw=1.6, clip_on=False, zorder=7)

    handles = [Line2D([], [], marker="o", ls="none", ms=5.5, mfc="white", mec=INKC,
                      label="Premium at normal prices"),
               Line2D([], [], marker="o", ls="none", ms=5.5, color=INKC,
                      label="Net cost after avoided loss"),
               Line2D([], [], color=SECC, lw=1.3, marker="<", ms=4, markevery=[0],
                      label="Security margin"),
               Line2D([], [], marker="|", ls="none", ms=9, mew=1.2, color=MAG,
                      label="Carbon incentive")]
    if legend:
        ax.legend(handles=handles, loc="lower left", bbox_to_anchor=legend_anchor, ncol=2,
                  fontsize=7.0, frameon=False, handlelength=1.2, handletextpad=0.4,
                  columnspacing=1.0, borderaxespad=0.0)
    return rows


if __name__ == "__main__":
    main()
