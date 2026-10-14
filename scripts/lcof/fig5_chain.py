"""
fig5_chain.py — Figure 5 on the fuel-chain basis (2026-09-25 audit).

  a  fig5a_chain: the 1%-of-GDP security portfolio, per tonne, security
     value valued chain by chain (read from data/cost/fig5a_chain.csv)
  b  (2026-10-03) abatement-cost curves of all addressable demand in the
     assessed economies, build year 2025 above 2050, cut at zero cost and
     coloured by region; hatched tranches pay off only with the security
     value. Since 2026-10-04 the bars run in three groups (cheaper on cost
     alone, cheaper only with security, still dearer), each from low to high
     cost; the separately sorted black cost-only line was dropped because
     its x positions did not match the bars. The dotted and dashed lines
     are the trajectory below (written to fig5b_chain_trajectory.csv).

Panel b previously let a whole (country, fuel) demand clear once the
premium fell below a country-level threshold codf_hi x q_eff x m_f. Now
each fuel is tested against its own chain, and only the part the chain
imports can clear for security:

  w_{c,f}   = CoDF_hi,c x q_{c,f} x m_f          $ per imported GJ retired
  pi_{c,f}(t) = LCOF_{c,f} x g_f(t) - p_{c,f}     production premium
  Q_{c,f}(t) = I_{c,f} x 1[pi <= w]  +  (D_{c,f} - I_{c,f}) x 1[pi <= 0]

with I_{c,f} = e_{c,f} D_{c,f} the chain's net imports (Fig. 3 chain
exposure in the 30 core economies, the fuel family's net dependence
elsewhere). Cost parity alone is D_{c,f} x 1[pi <= 0]. Demand is held at
2025, fossil comparators at their observed level; only g_f(t), the
technology-cost path of the synthetic fuel, moves.

From scripts/:  conda run -n synfuel python -u -m lcof.fig5_chain
Writes data/cost/fig5b_chain_pairs.csv, data/cost/fig5b_chain_trajectory.csv
and cf_global_final/figures/pptx/fig5_chain.(pdf|png).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.ticker import FuncFormatter

mpl.use("Agg")

from . import inputs
from .fig_main_cost import MM, NAT_RC, FUELS
from .fig_pptx_pairs import OUT
from .demand_grid import _decline
from .global_trajectory import EFD, REGION_COL, region_of
from .fig5a_chain import chain_inputs, draw_a, draw_a_simple, draw_a_bars, draw_a_hurdle, draw_a_circles, GASF, M_F

mpl.rcParams.update(NAT_RC)
VY = np.arange(2025, 2051)


def panel_b_data(rate=1.0, write=True):
    from .gap import country_gas_monthly, country_lcof
    from .security_budget import _grey
    meta = inputs.load_meta(2025)
    dg = pd.read_csv(inputs.MAPS / "demand_fuel_grid.csv", index_col=0)
    cols = [f + "_gj" for f in FUELS]
    dgc = dg.join(meta[["country"]]).groupby("country")[cols].sum()
    si = pd.read_csv(inputs.MAPS / "security_index.csv", index_col=0)
    si = si.dropna(subset=["codf_hi_usd_gj", "q_eff"])
    decl = _decline(FUELS)
    lcof_all = country_lcof()
    gasdf, _ = country_gas_monthly()
    grey_tab = _grey(dgc.rename(columns=lambda k: k.replace("_gj", "")))
    # 2026-10-07 (review): the part of demand supplied at home competes with the
    # cheaper of the import price and the economy's own production route (China's coal-based
    # and the United States' gas-based ammonia undercut imports); net imports keep the import
    # price. Ammonia only: refined oil products are priced at import parity everywhere.
    grey_dom = _grey(dgc.rename(columns=lambda k: k.replace("_gj", "")), domestic=True)
    keep = [c for c in dgc.index if c in si.index and c in lcof_all.index
            and c in gasdf.columns]
    ch = chain_inputs(keep)
    rows = []
    for c in keep:
        codf = float(si.codf_hi_usd_gj[c])
        for f in FUELS:
            d_f = float(dgc.loc[c, f + "_gj"])
            if d_f <= 0 or f not in lcof_all.columns:
                continue
            lc = float(lcof_all.loc[c, f])
            gr = float(grey_tab.loc[c, f]) if (c in grey_tab.index and f in grey_tab.columns) else np.nan
            if not np.isfinite(lc) or not np.isfinite(gr) or gr <= 0:
                continue
            pi = lc * decl[f] - gr
            gd = float(grey_dom.loc[c, f]) if f == "ammonia" else np.nan
            pi_r = lc * decl[f] - (min(gr, gd) if np.isfinite(gd) and gd > 0 else gr)
            kr = np.nonzero(pi_r <= 0)[0]
            r1, r2 = (rate, rate) if np.isscalar(rate) else rate
            e = float(ch.loc[(c, f), "e"])
            q = r1 * float(ch.loc[(c, f), "q_s1"]) + r2 * float(ch.loc[(c, f), "q_s2"])
            w = codf * q * M_F["gas" if f in GASF else "oil"]
            ks = np.nonzero(pi <= w)[0] if (e > 0 and w > 0) else []
            kc = np.nonzero(pi <= 0)[0]
            rows.append(dict(country=c, fuel=f, dem_gj=d_f, imp_gj=e * d_f,
                             w_usd_gj=w, sec_imp=float(VY[ks[0]]) if len(ks) else 2099.0,
                             cost=float(VY[kc[0]]) if len(kc) else 2099.0, ef=EFD[f],
                             # premium over the fossil comparator, US$/GJ, for the
                             # abatement-cost curves of panel b (2026-10-03)
                             pi_2025=float(pi[0]), pi_2050=float(pi[-1]),
                             # the domestically supplied rest of demand (least-cost comparator)
                             cost_rest=float(VY[kr[0]]) if len(kr) else 2099.0,
                             pi_rest_2025=float(pi_r[0]), pi_rest_2050=float(pi_r[-1])))
    p = pd.DataFrame(rows)
    from .fig_pptx_pairs import _COUNTRIES
    pts = _COUNTRIES.copy()
    rp = pts.geometry.representative_point()
    pts["lon"], pts["lat"] = rp.x.to_numpy(), rp.y.to_numpy()
    pts = pts.drop_duplicates("country").set_index("country")
    p["region"] = [region_of(c, float(pts.lon.get(c, np.nan)), float(pts.lat.get(c, np.nan)))
                   for c in p.country]
    if write:
        p.to_csv(inputs.MAPS / "fig5b_chain_pairs.csv", index=False)

    def q_at(t, pp):
        return pp.imp_gj * (pp.sec_imp <= t) + (pp.dem_gj - pp.imp_gj) * (pp.cost_rest <= t)

    def q_cost(t, pp):
        return pp.imp_gj * (pp.cost <= t) + (pp.dem_gj - pp.imp_gj) * (pp.cost_rest <= t)
    tj = pd.DataFrame({
        "year": VY,
        "sec_gt": [float((q_at(t, p) * p.ef).sum() / 1e9) for t in VY],
        "cost_gt": [float((q_cost(t, p) * p.ef).sum() / 1e9) for t in VY],
        "sec_bn_mmbtu": [float(q_at(t, p).sum() / 1e9 / 1.0551) for t in VY],
        "cost_bn_mmbtu": [float(q_cost(t, p).sum() / 1e9 / 1.0551) for t in VY]})
    tot = p.dem_gj.sum()
    tj["sec_share"] = tj.sec_bn_mmbtu * 1.0551 * 1e9 / tot
    tj["cost_share"] = tj.cost_bn_mmbtu * 1.0551 * 1e9 / tot
    if write:
        tj.to_csv(inputs.MAPS / "fig5b_chain_trajectory.csv", index=False)
    old = pd.read_csv(inputs.MAPS / "global_trajectory.csv").set_index("year")
    for t in (2030, 2040, 2050):
        r = tj.set_index("year").loc[t]
        ch_t = float((q_at(t, p[p.country == "China"]) * p[p.country == "China"].ef).sum() / 1e9)
        print(f"{t}: security {r.sec_gt:.2f} Gt ({r.sec_bn_mmbtu:.1f} bn MMBtu, {r.sec_share:.0%}) "
              f"| cost parity {r.cost_gt:.2f} Gt ({r.cost_bn_mmbtu:.1f} bn MMBtu, {r.cost_share:.0%}) "
              f"| China {ch_t:.2f} Gt | old security {old.sec_gt[t]:.2f} Gt, old cost {old.cost_gt[t]:.2f} Gt")
    print(f"{p.country.nunique()} economies, {len(p)} (country, fuel) pairs; "
          f"chain imports {p.imp_gj.sum() / tot:.0%} of addressable demand")
    return p, tj, q_at


_INK, _GREEN = "#1A1A1A", "#1B7A4B"
_DEAR = "#CDD2D7"     # 2026-10-05: costlier-even-with-security bars in plain light grey
_YLO = {2025: -300.0, 2050: -800.0}      # only thin slivers lie lower (2025: 3.0 Mt; 2050: 1.8 Mt)
_CAP = 300.0                              # panel b shows the dearer demand up to US$300 per tonne
# 2026-10-05: right of the dashed line (cost above zero) the x axis is
# compressed by these factors, so the demand below zero gets about 55% of the width
_SQZ = {2025: 5.0, 2050: 2.0}
_XT = {2025: [0, 0.05, 0.5, 1.0, 1.5], 2050: [0, 0.5, 1.0, 2, 3, 4, 5]}   # 2026-10-07: ticks for the IEA-cost curves


def _curve_to_zero(ax, p, yr, rcol, tj, xmax=None, ylo=None, inside=False):
    """Abatement-cost curve of all addressable demand, cut at zero cost, in two
    groups (author, 2026-10-04): first the tranches that are cheaper than the
    fossil fuel on cost alone (premium at or below zero), then those that are
    cheaper only once the security value of net imports is credited (hatched:
    premium above zero, premium minus security margin at or below zero); each
    group runs from low to high cost per tonne. Each country-fuel pair splits
    into its net imports, at the premium minus the security margin, and the
    rest of its demand, at the premium, in US$ per tonne of CO2 displaced.
    The first group's width is the CO2 displaced on cost only and both groups
    together the CO2 displaced with the security value, i.e. the trajectory
    of fig5b_chain_trajectory.csv for that build year (asserted)."""
    mpl.rcParams["hatch.linewidth"] = 0.5
    pi = p[f"pi_{yr}"].to_numpy()
    pi_r = p[f"pi_rest_{yr}"].to_numpy()
    w = np.clip(p.w_usd_gj.to_numpy(), 0, None)
    ef = p.ef.to_numpy()
    imp = p.imp_gj.to_numpy()
    reg = p.region.to_numpy()
    cty = p.country.to_numpy()
    sec = pd.concat([
        pd.DataFrame({"wd": imp * ef / 1e9, "c": (pi - w) / ef, "prem": pi / ef, "region": reg,
                      "country": cty}),
        pd.DataFrame({"wd": (p.dem_gj.to_numpy() - imp) * ef / 1e9, "c": pi_r / ef, "prem": pi_r / ef,
                      "region": reg, "country": cty})])
    sec = sec[sec.wd > 0].copy()
    sec["sec_only"] = (sec.prem > 0) & (sec.c <= 0)
    # third group (author, 2026-10-04: "negative and positive both in the main figure"):
    # the demand still dearer than fossil fuel, light, up to _CAP per tonne
    pos = sec[(sec.c > 0) & (sec.c <= _CAP)].sort_values("c", kind="stable")
    above = float(sec.wd[sec.c > _CAP].sum())
    sec = sec[sec.c <= 0]
    neg = pd.concat([sec[~sec.sec_only].sort_values("c", kind="stable"),
                     sec[sec.sec_only].sort_values("c", kind="stable")]).reset_index(drop=True)
    bars = pd.concat([neg.assign(dear=False), pos.assign(dear=True)]).reset_index(drop=True)
    bars["x0"] = bars.wd.cumsum() - bars.wd
    zs, zc = float(neg.wd.sum()), float(neg.wd[~neg.sec_only].sum())
    t = tj.set_index("year")
    assert abs(zs - float(t.sec_gt[yr])) < 1e-6 and abs(zc - float(t.cost_gt[yr])) < 1e-6, (yr, zs, zc)
    # 2026-10-08: a figure with several build years passes one shared range
    ylo = _YLO[yr] if ylo is None else float(ylo)
    yhi = _CAP
    xmax = float(bars.wd.sum()) if xmax is None else float(xmax)
    for r in bars.itertuples():
        ax.add_patch(Rectangle((r.x0, 0), r.wd, max(r.c, ylo), fc=_DEAR if r.dear else rcol[r.region],
                               lw=0, zorder=2,
                               hatch="////" if r.sec_only else None, ec="white" if r.sec_only else "none"))
    # 2026-10-06: when one economy fills the cost-only group (2025: China), name it and
    # point to the slivers of the others, which are too thin to see
    cg = bars[~bars.dear & ~bars.sec_only]
    share = cg.groupby("country").wd.sum()
    if len(share) > 1 and share.max() >= 0.8 * zc:
        top = share.idxmax()
        tb = cg[cg.country == top]
        fuels = sorted(set(p.fuel[(p.country == top) & ((p[f"pi_{yr}"] <= 0) | (p[f"pi_rest_{yr}"] <= 0))]))
        x_mid = float((tb.x0 + tb.wd / 2).mean()) if len(tb) == 1 else float(tb.x0.min() + tb.wd.sum() / 2)
        lines, targets = [], []
        # 2026-10-08: the name goes inside the block only when the block is wide enough;
        # otherwise every name sits in the empty area right of the dashed line, with leaders
        if tb.wd.sum() >= 0.12 * xmax:
            ax.text(x_mid, 0.45 * float(tb.c.max()), f"{top}, {', '.join(fuels)}", ha="center", va="center",
                    fontsize=6, color="white", fontweight="bold", zorder=7)
        else:
            lines.append(f"{top}, {', '.join(fuels)}: {tb.wd.sum():.2f} Gt")
            targets.append((x_mid, 0.5 * float(tb.c.max())))
        rest = cg[cg.country != top]
        names = list(dict.fromkeys(rest.country))
        short = {"United States of America": "US" if inside else "United States"}
        names_s = [short.get(n, n) for n in names]
        lab_txt = (" and ".join(names_s) if len(names_s) <= 2 else ", ".join(names_s[:-1]) + " and " + names_s[-1])
        fuel_r = sorted(set(p.fuel[p.country.isin(names) & ((p[f"pi_{yr}"] <= 0) | (p[f"pi_rest_{yr}"] <= 0))]))
        if inside:                   # 2026-10-08: narrow, short lines; the fuel once at the end
            import textwrap
            lines = ([] if tb.wd.sum() >= 0.12 * xmax else [f"{top}:", f"{tb.wd.sum():.2f} Gt"])
            lines += textwrap.wrap(f"{lab_txt}:", 11) + [f"{rest.wd.sum():.3f} Gt"]
            allf = sorted(set(fuels) | set(fuel_r))
            lines.append(f"all {allf[0]}" if len(allf) == 1 else f"({', '.join(allf)})")
        else:
            lines.append(f"{lab_txt},")
            lines.append(f"{', '.join(fuel_r)}: {rest.wd.sum():.3f} Gt")
        targets += [(r.x0 + r.wd / 2, max(r.c, ylo)) for r in rest.itertuples()]
        # 2026-10-08: with the paying demand given 75 % of the width (Fig. 4 by build year) the
        # note sits in the empty lower left of the cost-only group, under the dominant block
        if inside:
            # 2026-10-08: right of the last bar of the paying groups that reaches below 0.55*ylo,
            # so the note sits in empty space under the shallow part of the curve
            deep = bars[~bars.dear & (bars.c < 0.42 * ylo)]
            tx = float((deep.x0 + deep.wd).max()) if len(deep) else 0.0
            ty = 0.66 * ylo
        else:
            tx, ty = zs, 0.55 * ylo
        ax.annotate(chr(10).join(lines), (tx, ty), xytext=(4 if inside else 5, 0), textcoords="offset points",
                    ha="left", va="center", fontsize=5.5, color=_INK, linespacing=1.1, zorder=7,
                    bbox=dict(fc="white", ec="none", pad=0.5) if inside else None)
        # thin leaders from each block to the note
        for x, y in targets:
            ax.annotate("", xy=(x, y), xytext=(tx, ty),
                        arrowprops=dict(arrowstyle="-", color="#555555", lw=0.4, shrinkA=0, shrinkB=0),
                        zorder=7)
    # piecewise-linear x axis: true scale up to the dashed line, compressed after it
    k = _SQZ[yr]
    ax.set_xscale("function", functions=(
        lambda x: np.where(np.asarray(x) <= zs, x, zs + (np.asarray(x) - zs) / k),
        lambda u: np.where(np.asarray(u) <= zs, u, zs + (np.asarray(u) - zs) * k)))
    ax.axhline(0, color="#555555", lw=0.6, zorder=4)
    if inside:
        # 2026-10-13: the lines stop at mid height and carry the totals at their tops
        y_top = 0.55 * yhi                # below the two-line group names
        ax.plot([zc, zc], [ylo, y_top], color=_INK, lw=0.7, ls=(0, (1, 1.5)), zorder=5)
        ax.plot([zs, zs], [ylo, y_top], color=_GREEN, lw=0.9, ls=(0, (3, 2)), zorder=5)
    else:
        ax.axvline(zc, color=_INK, lw=0.7, ls=(0, (1, 1.5)), zorder=5)
        ax.axvline(zs, color=_GREEN, lw=0.9, ls=(0, (3, 2)), zorder=5)
    # 2026-10-05: group names written on the panel above each group
    yt = 0.97 * _CAP
    lab = dict(fontsize=6, va="top", linespacing=1.05, zorder=6)
    # 2026-10-07: no name for an empty group (2025: nothing pays off on cost alone), and a
    # name that would touch its neighbour moves down a line
    t_cost = (ax.text(zc / 2, yt, "Pays off without\nsecurity value" if inside else "Pays off on\ncost alone",
                      ha="center", color=_INK, **lab)
              if zc > 1e-9 else None)
    # 2026-10-06: parallel to "Pays off on cost alone"; the group counts the cost and the
    # security value together, not security alone
    # regular weight like the other two names: in bold it overran the narrower 2050 group
    t_sec = ax.text((zc + zs) / 2, yt, "Pays off with\nsecurity value" if inside else "Pays off with\nsecurity",
                    ha="center", color=_GREEN, **lab)
    if inside:
        # a name wider than its group starts at the dotted line and runs right, over the low
        # first bars of the dearer group, instead of spilling left over the cost-only name
        t_sec.set_ha("left")
        t_sec.set_x(zc)
        t_sec.set_text(" Pays off with\n security value")
    if inside:
        # 2026-10-08: right-aligned at the panel's right edge so it never reaches the next panel
        t_dear = ax.annotate("Costlier with" + chr(10) + "security value",
                             (1.0, -0.04 * (yhi - ylo)), xycoords=("axes fraction", "data"), xytext=(-1, 0),
                             textcoords="offset points", ha="right", va="top", fontsize=5.2, linespacing=1.05,
                             color="#6A7480", zorder=6)
    else:
        t_dear = ax.annotate("Costlier even\nwith security", (zs, yt), xytext=(4, 0), textcoords="offset points",
                             ha="left", color="#6A7480", **lab)
    # both values to the right of the dashed line, below zero where there are no bars
    yl, dy = -0.03 * (yhi - ylo), 0.06 * (yhi - ylo)   # empty area below zero, right of the dashed line
    if inside:
        # 2026-10-08: above zero, each total right-aligned inside its own group (the cost-only total
        # left of the dotted line, the total with security left of the dashed line), two lines
        ax.annotate(f"{zc:.2f} Gt", (zc, y_top), xytext=(0, 1.5), textcoords="offset points",
                    ha="center", va="bottom", fontsize=5.8, color=_INK, zorder=8,
                    bbox=dict(fc="white", ec="none", pad=0.3))
        ax.annotate(f"{zs:.2f} Gt", (zs, y_top), xytext=(0, 1.5), textcoords="offset points",
                    ha="center", va="bottom", fontsize=5.8, color=_GREEN, fontweight="bold", zorder=8,
                    bbox=dict(fc="white", ec="none", pad=0.3))
    else:
        ax.annotate(f"{zs:.2f} Gt with security", (zs, yl), xytext=(3, 0), textcoords="offset points",
                    ha="left", va="top", fontsize=6, color=_GREEN, fontweight="bold")
        ax.annotate(f"{zc:.2f} Gt without security", (zs, yl - dy), xytext=(3, 0), textcoords="offset points",
                    ha="left", va="top", fontsize=6, color=_INK)
    # mark where the scale changes: a break on the x axis and a short note
    ax.annotate("//", (zs, ylo), xytext=(0, -1), textcoords="offset points", ha="center", va="center",
                fontsize=7, color="#555555", annotation_clip=False, zorder=6,
                bbox=dict(fc="white", ec="none", pad=0.2))
    ax.annotate(f"{k:.0f}\u00d7" if inside else f"axis compressed {k:.0f}\u00d7", (zs, ylo),
                xytext=(4, 4), textcoords="offset points",
                ha="left", va="bottom", fontsize=5.5, color="#555555")
    # the build year sits in the empty lower right (below zero, right of the dashed line)
    if not inside:                   # Fig. 4 by build year names the year in the column title
        ax.text(0.98, 0.04, str(yr), transform=ax.transAxes, ha="right", va="bottom", fontsize=7,
                fontweight="bold", color="#333333")
    ax.set_xlim(0, xmax)
    ax.set_xticks(_XT[yr])
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax.set_ylim(ylo, yhi)
    ax.tick_params(axis="both", labelsize=6.5)
    # overlap test on the finished axes (scale and limits set)
    ax.figure.canvas.draw()
    rr = ax.figure.canvas.get_renderer()
    # 2026-10-07: a group name must sit inside its group. If it is wider than the group,
    # try three lines; if still too wide, move it into the empty area below zero, right of the
    # dashed line, with a thin leader to the group (2025: both paying groups are slivers)
    px = lambda x: ax.transData.transform((x, 0))[0]
    groups = [(t_cost, 0.0, zc, *(("Pays off\nwithout\nsecurity value", "Pays off\nwithout\nsecurity\nvalue")
                                  if inside else ("Pays off\non cost\nalone", "Pays\noff on\ncost\nalone"))),
              (t_sec, zc, zs, *(("Pays off\nwith\nsecurity value", "Pays off\nwith\nsecurity\nvalue")
                                if inside else ("Pays off\nwith\nsecurity", "Pays\noff\nwith\nsecurity")))]
    slot = 0
    for txt, x0, x1, three, four in groups:
        if txt is None or inside:        # 2026-10-13: Fig. 4 keeps both names on two lines
            continue
        room = px(x1) - px(x0) - 3
        if txt.get_window_extent(rr).width <= room:
            continue
        txt.set_text(three)
        ax.figure.canvas.draw()
        if txt.get_window_extent(rr).width <= room:
            continue
        # three, then four lines, flush left in the group
        txt.set_ha("left")
        txt.set_x(ax.transData.inverted().transform((px(x0) + 1.5, 0))[0])
        ax.figure.canvas.draw()
        if txt.get_window_extent(rr).width <= room:
            continue
        txt.set_text(four)
        ax.figure.canvas.draw()
        if txt.get_window_extent(rr).width <= room:
            continue
        txt.set_text(txt.get_text().replace("\n", " ", 1).replace("\n", " "))
        # above zero, over the low first bars of the dearer group and clear of every label
        fx = ax.transAxes.inverted().transform((px(zs), 0))[0] + 0.10
        fy = 0.80 - 0.09 * slot
        txt.set_position(ax.transData.inverted().transform(ax.transAxes.transform((fx, fy))))
        txt.set_ha("left")
        txt.set_va("center")
        ax.annotate("", xy=((x0 + x1) / 2, 0.04 * ylo), xytext=(fx - 0.01, fy), textcoords="axes fraction",
                    arrowprops=dict(arrowstyle="-", color=txt.get_color(), lw=0.5, shrinkA=0, shrinkB=1),
                    zorder=6)
        slot += 1
    ax.figure.canvas.draw()
    bb = lambda o: o.get_window_extent(rr).expanded(1.1, 1.0)
    if not inside and bb(t_sec).overlaps(bb(t_dear)):
        t_sec.set_y(t_sec.get_position()[1] - 0.17 * _CAP)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}".replace("-", "−")))
    ax.set_ylabel("Abatement cost (US\\$ tCO$_2^{-1}$)", fontsize=7)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    cut = neg[neg.c < ylo]
    print(f"  b {yr}: {zs:.3f} Gt with security, {zc:.3f} on cost only (+{zs - zc:.3f}); axis cut at {ylo:.0f}, "
          f"{cut.wd.sum() * 1e3:.1f} Mt lower (min {neg.c.min():.0f}); shown to US${_CAP:.0f}/t = {xmax:.2f} Gt, "
          f"{above:.2f} Gt costs more")
    return set(bars.region)


def main():
    d = pd.read_csv(inputs.MAPS / "fig5a_chain.csv", index_col=0)
    p, tj, q_at = panel_b_data()

    # Nature style: 183 mm wide, Arial 5-7 pt, bold lowercase 8 pt panel letters,
    # no titles inside the figure (the message lives in the legend title)
    # 2026-10-05: 170 -> 150 mm tall, India merged, the bar-type key moved into panel b (2050)
    fig = plt.figure(figsize=(183 * MM, 150 * MM))
    gs = fig.add_gridspec(1, 2, width_ratios=[0.50, 0.50], wspace=0.34,
                          left=0.12, right=0.985, top=0.90, bottom=0.075)
    a = fig.add_subplot(gs[0])
    # 2026-10-03 (author): panel b is the abatement-cost curve cut at zero cost,
    # build year 2025 above 2050, replacing the stacked regional trajectory
    gb = gs[1].subgridspec(2, 1, hspace=0.22)
    b1, b2 = fig.add_subplot(gb[0]), fig.add_subplot(gb[1])
    # 2026-10-02: back to the circle version (review), all 30
    # economies with the net exporters below the importers
    # security margins in an aligned column at the right (2026-10-02)
    draw_a_circles(a, d, legend_anchor=(-0.02, 1.02), margin="column")
    a.set_xlabel("Abatement cost (US\$ per tonne of CO$_2$ displaced)", fontsize=7)

    # 2026-10-05: India is no longer split out (0.16 of 1.95 Gt in 2050)
    RCOL = dict(REGION_COL)
    present = set()
    for ax, yr in ((b1, 2025), (b2, 2050)):
        present |= _curve_to_zero(ax, p, yr, RCOL, tj)
    b2.set_xlabel("Cumulative CO$_2$ displaced (Gt yr$^{-1}$)", fontsize=7)
    # two keys (author, 2026-10-04): colour = region; solid / hatched = cheaper
    # than fossil fuel on cost alone / only with the security value
    names = [k for k in RCOL if k in present]
    short = {"Rest of Asia and Oceania": "Rest of Asia & Oceania"}
    b1.legend([Rectangle((0, 0), 1, 1, fc=RCOL[k]) for k in names], [short.get(k, k) for k in names],
              fontsize=6, frameon=False, ncol=3, loc="lower left",
              bbox_to_anchor=(-0.02, 1.03), handlelength=1.1, columnspacing=0.8, labelspacing=0.3,
              borderaxespad=0.0)
    # 2026-10-05: the bar-type key is replaced by group names on the panels
    # panel b's letter sits just left of its y-axis label, wherever the gap puts it
    fig.canvas.draw()
    bx = b1.get_tightbbox(fig.canvas.get_renderer()).transformed(fig.transFigure.inverted()).x0
    for letter, x in (("a", 0.005), ("b", bx - 0.01)):
        fig.text(x, 0.985, letter, fontsize=8, fontweight="bold", ha="left", va="top")
    for name in ("fig5_chain", "fig_main_carbon"):     # the paper's Figure 5
        fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
        fig.savefig(OUT / f"{name}.png", dpi=600, bbox_inches="tight")
    plt.close(fig)
    print("saved fig5_chain.(pdf|png) = fig_main_carbon.(pdf|png)")


if __name__ == "__main__":
    main()
