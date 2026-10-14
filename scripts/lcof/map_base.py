"""
map_base.py -background graphics for the 2026 slide, built to
follow the Introduction of the manuscript (main_V1.1, 2026-09-28):

  jt26_i_sankey        world primary energy 2025 -> hard-to-electrify fuel
                       demand (76 billion MMBtu) -> the synthetic routes
  jt26_i_cost          the cost barrier: share of electricity that reaches the
                       fuel, and synthetic / fossil cost ratio by fuel
  jt26_i_headlines     recent conflicts that struck fuel supply
  jt26_i_px_base       Brent crude and European gas, 2006-2026 ($/MMBtu)
  jt26_i_px_ev<k>      one transparent overlay per conflict, same canvas as
                       the base, so build_slides2026_pptx.py can stack them and
                       reveal one per click

Units: billion MMBtu (LHV) for energy, $/MMBtu (LHV) for prices.
From scripts/:  python -m lcof.map_base   (synfuel env)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

mpl.use("Agg")

from . import inputs, params as P

OUT = inputs.PROJECT / "cf_global_final" / "figures" / "slides2026"
OUT.mkdir(parents=True, exist_ok=True)
INK, GREY, LIGHT = "#142B45", "#444444", "#8C96A3"
ACC = "#C0502D"
UMM = 1.0551                       # GJ per MMBtu
STYLE = {"font.family": "Arial", "font.size": 17, "axes.edgecolor": INK,
         "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
         "axes.labelsize": 17, "xtick.labelsize": 16, "ytick.labelsize": 16,
         "axes.spines.top": False, "axes.spines.right": False}
ROUTE_COL = {"e-diesel": "#56B4E9", "e-methane": "#009E73", "e-kerosene": "#2B7BB9",
             "methanol": "#E69F00", "ammonia": "#0072B2", "ethanol": "#CC79A7"}
ROUTE_USE = {"e-diesel": "trucks, industry, other oil uses",
             "e-methane": "industry, other gas uses",
             "e-kerosene": "aviation",
             "methanol": "shipping",
             "ammonia": "fertilizer, shipping",
             "ethanol": "road"}
ORIGIN = {"e-diesel": "oil", "e-kerosene": "oil", "ethanol": "oil", "methanol": "oil",
          "e-methane": "gas", "ammonia": "gas"}


def _save(fig, name, **kw):
    fig.savefig(OUT / f"{name}.png", dpi=200, facecolor=kw.pop("facecolor", "white"), **kw)
    plt.close(fig)
    print(f"  saved {name}")


# ============================================================ energy flow
def world_energy():
    """Energy Institute Statistical Review 2026, world total energy supply
    2025, EJ -> billion MMBtu"""
    d = pd.read_csv(inputs.PROJECT / "data" / "demand" / "ei_2026" /
                    "Statistical Review of World Energy Narrow format.csv", low_memory=False)
    w = d[(d.Country == "Total World") & (d.Year == 2025)].set_index("Var").Value
    src = {"Oil": w["oil_tes_ej"], "Natural gas": w["gas_tes_ej"], "Coal": w["coal_tes_ej"],
           "Nuclear": w["nuclear_tes_ej"], "Hydro": w["hydro_tes_ej"],
           "Wind, solar, other renewables": w["renewables_tes_ej"]}
    tot = w["tes_ej"]
    return {k: v / UMM for k, v in src.items()}, tot / UMM


def addressable():
    """the paper's addressable market, 139 economies, EJ -> billion MMBtu"""
    gt = pd.read_csv(inputs.MAPS / "global_trajectory_countries.csv")
    return (gt.groupby("fuel").dem_gj.sum() / 1e9 / UMM).sort_values(ascending=False), \
        gt.country.nunique()


def _ribbon(ax, x0, x1, a0, b0, a1, b1, color, alpha=0.55):
    t = np.linspace(0, 1, 80)
    s = 3 * t ** 2 - 2 * t ** 3
    x = x0 + (x1 - x0) * t
    lo = a0 + (a1 - a0) * s
    hi = b0 + (b1 - b0) * s
    ax.fill_between(x, lo, hi, color=color, alpha=alpha, lw=0, zorder=1)


def sankey():
    mpl.rcParams.update(STYLE)
    src, tot = world_energy()
    route, n_econ = addressable()
    hard = float(route.sum())
    hard_from = {"Oil": float(sum(v for f, v in route.items() if ORIGIN[f] == "oil")),
                 "Natural gas": float(sum(v for f, v in route.items() if ORIGIN[f] == "gas"))}
    col = {"Oil": "#2E7D32", "Natural gas": "#4A90D9", "Coal": "#3A3A3A", "Nuclear": "#8E44AD",
           "Hydro": "#1F4E9A", "Wind, solar, other renewables": "#E0B000"}

    fig = plt.figure(figsize=(13.0, 6.3))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 13.0)
    ax.set_ylim(0, 6.3)
    ax.set_axis_off()
    k = 5.4 / tot                                  # inches of height per billion MMBtu
    gap = 0.07
    X0, X1, NW = 3.45, 6.55, 0.22
    # sources, top to bottom
    y = 5.95
    s_pos = {}
    for name, v in src.items():
        h = v * k
        s_pos[name] = [y - h, y]
        ax.add_patch(plt.Rectangle((X0 - NW, y - h), NW, h, color=col[name], zorder=3))
        ax.text(X0 - NW - 0.12, y - h / 2, f"{name}  {v:.0f}", ha="right", va="center",
                fontsize=15, color=INK)
        y -= h + gap
    # middle nodes: hard to electrify (top) and every other use
    h_hard = hard * k
    h_rest = (tot - hard) * k
    top = 5.95
    hard_box = [top - h_hard, top]
    rest_box = [top - h_hard - 0.35 - h_rest, top - h_hard - 0.35]
    ax.add_patch(plt.Rectangle((X1, hard_box[0]), NW, h_hard, color=ACC, zorder=3))
    ax.add_patch(plt.Rectangle((X1, rest_box[0]), NW, h_rest, color="#B8C0CA", zorder=3))
    # flows: oil and gas split into their hard-to-electrify part (to the top node)
    cur_h = hard_box[1]
    cur_r = rest_box[1]
    for name, v in src.items():
        a, b = s_pos[name]
        part = hard_from.get(name, 0.0) * k
        if part > 0:                                # top slice of the source bar
            _ribbon(ax, X0, X1, b - part, b, cur_h - part, cur_h, col[name], 0.75)
            cur_h -= part
            b -= part
        rest = b - a
        _ribbon(ax, X0, X1, a, b, cur_r - rest, cur_r, col[name], 0.35)
        cur_r -= rest
    og = src["Oil"] + src["Natural gas"]
    ax.text(X1 + NW + 0.12, rest_box[0] + 0.9,
            f"all other uses  {tot - hard:.0f}\npower, buildings,\nlight vehicles, ...",
            ha="left", va="center", fontsize=15, color=GREY)
    # oil and gas together
    ob = s_pos["Natural gas"][0]
    ax.plot([0.35, 0.35], [ob, 5.95], color=INK, lw=1.6)
    ax.text(0.25, (ob + 5.95) / 2, f"oil and gas\n{og / tot:.0%} of the world's energy", rotation=90,
            ha="right", va="center", fontsize=14, color=INK, fontweight="bold")
    # zoom: the hard-to-electrify node, magnified, split by synthetic route
    Z = 3.4 / h_hard                                # magnification
    ZX = 8.55
    zt = 5.95
    zb = zt - h_hard * Z
    ax.fill([X1 + NW, ZX, ZX, X1 + NW], [hard_box[0], zb, zt, hard_box[1]],
            color="#F6E3DB", zorder=0, lw=0)
    ax.text(X1 - 0.05, zt + 0.12, f"hard to electrify  {hard:.0f}", ha="left", va="bottom",
            fontsize=18, color=ACC, fontweight="bold")
    ax.text(ZX + 0.15, zb - 0.62,
            f"= {hard / tot:.0%} of world energy,  {hard / og:.0%} of oil and gas",
            ha="left", va="top", fontsize=16, color=ACC, fontweight="bold")
    yy = zt
    for f, v in route.items():
        h = v * k * Z
        ax.add_patch(plt.Rectangle((ZX, yy - h), NW + 0.08, h, color=ROUTE_COL[f], ec="white",
                                   lw=1.0, zorder=3))
        ax.text(ZX + NW + 0.22, yy - h / 2, f"{f}  {v:.0f}", ha="left", va="center",
                fontsize=15, color=INK, fontweight="bold")
        ax.text(ZX + NW + 2.25, yy - h / 2, ROUTE_USE[f], ha="left", va="center",
                fontsize=14, color=GREY)
        yy -= h
    ax.text(ZX + 0.15, zb - 0.2, f"magnified x{Z:.0f}", ha="center", va="top",
            fontsize=13, color=LIGHT)
    ax.text(X0 - NW - 0.12, 6.2, f"world primary energy 2025:  {tot:.0f}", ha="right",
            va="center", fontsize=15, color=GREY, fontweight="bold")
    _save(fig, "jt26_i_sankey", bbox_inches="tight")
    print(f"    world {tot:.0f}; oil+gas {og:.0f} ({og / tot:.0%}); hard {hard:.1f} = "
          f"{hard / tot:.1%} of primary, {hard / og:.0%} of oil+gas; from oil {hard_from['Oil']:.1f}, "
          f"gas {hard_from['Natural gas']:.1f}")


# ============================================================ cost barrier
def power_to_fuel():
    out = {"hydrogen": P.ETA_EL}
    for f in ("ammonia", "methanol", "e-methane", "ethanol", "e-diesel", "e-kerosene"):
        t = P.FUELS[f]
        out[f] = 1.0 / (1.0 / (P.ETA_EL * t["eta_syn"]) + t["mu_el"])
    return pd.Series(out)


def cost():
    mpl.rcParams.update(STYLE)
    ptf = power_to_fuel()
    b = pd.read_csv(inputs.MAPS / "breakeven_carbon_2025.csv")
    b["r"] = b.lcof_usd_gj / b.p_fossil_usd_gj
    g = b.groupby("fuel").agg(r=("r", "median"), tau=("tau_star_usd_t", "median"))
    order = ["ammonia", "hydrogen", "methanol", "ethanol", "e-diesel", "e-kerosene", "e-methane"]
    col = dict(ROUTE_COL, hydrogen="#7F7F7F")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13.0, 5.6), gridspec_kw=dict(width_ratios=[1, 1.15],
                                                                             wspace=0.55))
    ys = np.arange(len(order))[::-1]
    for y, f in zip(ys, order):
        v = ptf[f] * 100
        a1.barh(y, v, color=col[f], height=0.62)
        a1.barh(y, 100 - v, left=v, color="#E4E8EE", height=0.62)
        a1.text(v - 2, y, f"{v:.0f}%", ha="right", va="center", fontsize=15, color="white",
                fontweight="bold")
    a1.set_yticks(ys)
    a1.set_yticklabels(order)
    a1.set_xlim(0, 100)
    a1.set_xticks([0, 50, 100])
    a1.set_xlabel("share of the electricity that ends up in the fuel, %")
    a1.tick_params(axis="y", length=0)
    a1.text(0, len(order) - 0.2, "a   about half the electricity is lost", fontsize=17,
            color=INK, fontweight="bold", ha="left", va="bottom")
    for y, f in zip(ys, order):
        a2.barh(y, g.at[f, "r"], color=col[f], height=0.62)
        a2.text(g.at[f, "r"] + 0.08, y, f"{g.at[f, 'r']:.1f}x   break-even ${g.at[f, 'tau']:,.0f}/t CO2",
                ha="left", va="center", fontsize=14.5, color=GREY)
    a2.axvline(1, color=INK, lw=1.4, ls="--")
    a2.text(1.05, -0.9, "fossil price", fontsize=13, color=INK, va="center")
    a2.set_yticks(ys)
    a2.set_yticklabels(order)
    a2.set_xlim(0, 9.8)
    a2.set_ylim(-1.2, len(order) - 0.4)
    a2.set_xlabel("synthetic cost / fossil price (median of 143 economies)")
    a2.tick_params(axis="y", length=0)
    a2.text(0, len(order) - 0.2, "b   and the fuel costs 2-5 times fossil", fontsize=17,
            color=INK, fontweight="bold", ha="left", va="bottom")
    a1.set_ylim(-1.2, len(order) - 0.4)
    _save(fig, "jt26_i_cost", bbox_inches="tight")
    cp = b.groupby("country").carbon_price_now.max()
    print(f"    power-to-fuel {ptf.round(3).to_dict()}; ratios {g.r.round(2).to_dict()}; "
          f"carbon price zero in {(cp <= 0).mean():.0%} of {len(cp)} economies, max ${cp.max():.0f}")


# ============================================================ headlines
HEADLINES = [
    ("Feb 2022", "Russia invades Ukraine",
     "Russian pipeline gas to OECD Europe falls by half (83 bcm) in 2022", "IEA (2025)"),
    ("Aug 2022", "European gas peaks at $78/MMBtu",
     "the summer-2022 average was four times the summer-2021 level",
     "World Bank Pink Sheet; IEA (2025)"),
    ("2021-23", "Europe shields consumers",
     "EUR 651 billion allocated by governments since September 2021", "Bruegel (2023)"),
    ("Nov 2023", "Houthi attacks in the Red Sea",
     "tankers and LNG carriers re-route around the Cape of Good Hope", "IEA chokepoint monitor"),
    ("Feb 2026", "Strait of Hormuz closed",
     "carries about a fifth of world oil consumption and of LNG trade; still near-closed in "
     "August (3 transits a day vs ~85)", "EIA (2025); IEA Oil Market Report, Aug 2026"),
]


def headlines():
    mpl.rcParams.update(STYLE)
    fig = plt.figure(figsize=(13.0, 5.9))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 5.9)
    ax.set_axis_off()
    xs = 1.55
    y0, dy = 5.35, 1.13
    ax.plot([xs, xs], [y0 + 0.15, y0 - dy * (len(HEADLINES) - 1) - 0.15], color=LIGHT, lw=2,
            zorder=1)
    for i, (d, head, fact, src) in enumerate(HEADLINES):
        y = y0 - i * dy
        c = ACC if i in (0, 4) else INK
        ax.plot(xs, y, "o", ms=13, color=c, zorder=2)
        ax.text(xs - 0.3, y, d, ha="right", va="center", fontsize=17, color=c, fontweight="bold")
        ax.text(xs + 0.35, y + 0.17, head, ha="left", va="center", fontsize=19, color=INK,
                fontweight="bold")
        ax.text(xs + 0.35, y - 0.22, fact, ha="left", va="center", fontsize=15, color=GREY)
        ax.text(12.9, y + 0.17, src, ha="right", va="center", fontsize=12, color=LIGHT)
    _save(fig, "jt26_i_headlines")


# ============================================================ animated prices
EVENTS = [  # label, window (gap.CRISES), series to measure, label x, label y, ha
    ("Russian gas squeeze 2021", ("2021-10", "2022-02"), ["gas_eu"], 2021.62, 56, "right"),
    ("Russia-Ukraine war 2022", ("2022-03", "2023-08"), ["gas_eu", "brent"], 2022.9, 80, "left"),
    ("Red Sea attacks 2023-25", ("2023-12", "2025-02"), ["brent"], 2024.55, 34, "center"),
    ("Hormuz closure 2026", ("2026-03", "2026-08"), ["brent", "gas_eu"], 2026.42, 42, "center"),
]
SER = {"brent": ("Brent crude", "#3A3A3A"), "gas_eu": ("European gas (TTF)", "#2E5E8E")}
AX_RECT = [0.075, 0.12, 0.905, 0.84]
FIGSIZE = (13.0, 5.6)
XLIM = (2019.0, 2027.05)


def _dec(p):
    return p.year + (p.month - 0.5) / 12


def _px_axes(fig, visible=True):
    ax = fig.add_axes(AX_RECT)
    ax.set_xlim(*XLIM)
    ax.set_ylim(0, 88)
    if not visible:
        ax.set_axis_off()
    return ax


def prices():
    """base chart plus one transparent overlay per conflict on the same
    canvas: the window, the pre-event level (mean of the 12 months before,
    as in gap.CRISES) and an arrow to the peak month inside the window"""
    mpl.rcParams.update(STYLE)
    from .gap import PR
    g = PR.load(verified=False).loc["2017-01":"2026-08"] * UMM
    t = np.array([_dec(p) for p in g.index])
    m = t >= XLIM[0]
    fig = plt.figure(figsize=FIGSIZE)
    ax = _px_axes(fig)
    for s, (lab, c) in SER.items():
        ax.plot(t[m], g[s].values[m], color=c, lw=2.4, label=lab)
    ax.set_ylabel("price, $/MMBtu (LHV, nominal)")
    ax.set_xticks(range(2019, 2027))
    ax.legend(frameon=False, loc="upper left", fontsize=15)
    _save(fig, "jt26_i_px_base")
    rows = []
    for k, (lab, (a, b), ser, lx, ly, ha) in enumerate(EVENTS, 1):
        p0, p1 = pd.Period(a, "M"), pd.Period(b, "M")
        fig = plt.figure(figsize=FIGSIZE)
        ax = _px_axes(fig, visible=False)
        x0, x1 = _dec(p0) - 0.5 / 12, _dec(p1) + 0.5 / 12
        ax.axvspan(x0 + 0.01, x1 - 0.01, color=ACC, alpha=0.13, lw=0)
        parts = []
        for s in ser:
            x = g[s]
            pre = x[(x.index >= p0 - 12) & (x.index < p0)].mean()
            w = x[(x.index >= p0) & (x.index <= p1)]
            pk, pm = w.max(), _dec(w.idxmax())
            c = SER[s][1]
            ax.plot([x0, x1], [pre, pre], color=c, lw=2.2, ls=(0, (4, 2)))
            ax.annotate("", xy=(pm, pk), xytext=(pm, pre),
                        arrowprops=dict(arrowstyle="-|>", color=ACC, lw=2.6, mutation_scale=18))
            ax.plot(pm, pk, "o", ms=9, mfc="white", mec=ACC, mew=2.4)
            name = "gas" if s == "gas_eu" else "oil"
            parts.append(f"{name} +{100 * (pk / pre - 1):.0f}%")
            rows.append(dict(event=lab, series=s, pre=round(pre, 1), peak=round(pk, 1),
                             peak_month=str(w.idxmax()), pct=round(100 * (pk / pre - 1))))
        ax.text(lx, ly, lab + "\n" + ",  ".join(parts), ha=ha, va="center", fontsize=15.5,
                color=ACC, fontweight="bold", linespacing=1.3,
                bbox=dict(fc="white", ec="none", alpha=0.85, pad=2))
        _save(fig, f"jt26_i_px_ev{k}", transparent=True, facecolor="none")
    r = pd.DataFrame(rows)
    r.to_csv(OUT / "jt26_i_px_events.csv", index=False)
    print(r.to_string(index=False))


def title_bg():
    """pale background for the title slide: the synthetic-fuel supply map
    (Fig. 2 classes), the three oil and gas chokepoints, and the European gas
    price with its crisis spikes. Drawn light so dark text reads on top."""
    mpl.rcParams.update(STYLE)
    from .gap import PR
    sd = pd.read_csv(inputs.MAPS / "sd_map_classes.csv", index_col=0)
    cf = pd.read_csv(inputs.MAPS / "cf_global_2020.csv", usecols=["cell_id", "lon", "lat"]).set_index("cell_id")
    sd = sd.join(cf)
    W, H = 13.333, 7.5
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_axis_off()
    # map: lon -170..190 -> x 0..W, lat -58..78 -> y 1.55..7.5
    x0, x1, y0, y1 = 0.0, W, 1.55, 7.45
    fx = lambda lon: x0 + (lon + 170) / 360 * (x1 - x0)
    fy = lambda lat: y0 + (lat + 58) / 136 * (y1 - y0)
    cw, ch = 2.5 / 360 * (x1 - x0), 2.5 / 136 * (y1 - y0)
    base = {0: "#DCE7F1", 1: "#C9DCEB", 2: "#B3D3E3"}          # cost tercile, light blue ramp
    for _, r in sd.iterrows():
        c = "#F2C9B4" if (r.s == 2 and r.d == 2) else base[int(r.s)]   # build-first cells: pale orange
        ax.add_patch(plt.Rectangle((fx(r.lon) - cw / 2, fy(r.lat) - ch / 2), cw, ch, color=c, lw=0))
    for lon, lat in ((56.3, 26.6), (43.3, 12.6), (32.5, 30.0)):     # Hormuz, Bab el-Mandeb, Suez
        for rad, a in ((0.34, 0.55), (0.22, 0.75)):
            ax.add_patch(plt.Circle((fx(lon), fy(lat)), rad, fill=False, ec="#D98B6B", lw=1.6, alpha=a))
    # European gas price 2006-2026 along the bottom
    g = PR.load(verified=False).loc["2006-01":"2026-08", "gas_eu"] * UMM
    t = np.array([p.year + (p.month - 0.5) / 12 for p in g.index])
    px = (t - 2006) / (2026.7 - 2006) * W
    py = 0.12 + g.values / g.max() * 1.35
    ax.fill_between(px, 0.12, py, color="#F4D9CC", lw=0)
    ax.plot(px, py, color="#E3A98E", lw=1.8)
    # keep the left side quiet for the title
    grad = np.linspace(1, 0, 256)[None, :] ** 1.3
    ax.imshow(np.dstack([np.ones((1, 256, 3)), grad[..., None] * 0.97]), extent=[0, W * 0.8, 0, H],
              aspect="auto", zorder=5)
    fig.savefig(OUT / "jt26_title_bg.png", dpi=150, facecolor="white")
    plt.close(fig)
    print("  saved jt26_title_bg")


def renewables():
    """world wind and solar generation 2006-2025 (Energy Institute 2026) with
    their share of electricity"""
    mpl.rcParams.update(STYLE)
    d = pd.read_csv(inputs.PROJECT / "data" / "demand" / "ei_2026" /
                    "Statistical Review of World Energy Narrow format.csv", low_memory=False)
    w = d[(d.Country == "Total World") & d.Var.isin(["wind_twh", "solar_twh", "elect_twh"])] \
        .pivot(index="Year", columns="Var", values="Value").loc[2006:2025]
    share = (w.wind_twh + w.solar_twh) / w.elect_twh * 100
    fig, ax = plt.subplots(figsize=(8.6, 5.4))
    yr = w.index.values
    ax.stackplot(yr, w.wind_twh / 1000, w.solar_twh / 1000, colors=["#2B7BB9", "#E0B000"],
                 labels=["wind", "solar"], alpha=0.9)
    ax.set_ylabel("world generation, thousand TWh")
    ax.set_xlim(2006, 2025)
    ax.set_xticks([2006, 2010, 2015, 2020, 2025])
    ax.legend(frameon=False, loc="upper left", fontsize=16)
    top = (w.wind_twh + w.solar_twh) / 1000
    for y, dx, dy in ((2006, 2.6, 1.2), (2015, -0.3, 0.9), (2025, -1.6, 0.9)):
        ax.annotate(f"{share[y]:.1f}% of\nelectricity", xy=(y, top[y]), xytext=(y + dx, top[y] + dy),
                    fontsize=15, color=INK, fontweight="bold", ha="center",
                    arrowprops=dict(arrowstyle="-", color=LIGHT, lw=1.2))
    ax.set_ylim(0, 7.2)
    _save(fig, "jt26_i_renew", bbox_inches="tight")
    print(f"    wind+solar 2025 {top[2025]:.2f} thousand TWh, {share[2025]:.1f}% (2006 {share[2006]:.1f}%)")


def breakdown():
    """cost structure of each synthetic fuel on the paper's global grid: every
    land cell's median weather year, cheapest CO2 source, country cost of
    capital (the layer of Figs 1-2). Bars: median of each component across
    cells, $/MMBtu; label: hydrogen share of the cell's fuel cost."""
    mpl.rcParams.update(STYLE)
    from .fig_pptx_pairs import SUFFIX, YEARS
    from .supply_demand import MU_H2
    meta = inputs.load_meta(2025)
    land = meta[meta.cell_type == "land"].copy()
    frames = {y: pd.read_csv(inputs.MAPS / f"lcoh_global_{y}{SUFFIX}.csv").set_index("cell_id")
              for y in YEARS}
    cells = frames[YEARS[0]].index
    med = pd.DataFrame({k: np.median(np.column_stack([frames[y].loc[cells, k] for y in YEARS]), axis=1)
                        for k in ("lcoh_usd_gj", "lcoe_usd_mwh")}, index=cells)
    land = land.join(med, how="inner")
    land = land[np.isfinite(land.lcoh_usd_gj)]
    co2 = pd.read_csv(inputs.MAPS / "co2_cost_by_cell.csv").set_index("cell_id").co2_cost \
        .reindex(land.index).fillna(P.C_CO2_DAC)
    lcoe_gj = land.lcoe_usd_mwh / 3.6
    fuels = ["ammonia", "methanol", "e-methane", "ethanol", "e-diesel", "e-kerosene"]
    parts = [("hydrogen", "#4C78A8"), ("CO2 feed", "#E45756"), ("synthesis plant", "#F58518"),
             ("synthesis electricity", "#72B7B2")]
    rows, shares = [], {}
    for f in fuels:
        sp = P.FUELS[f]
        syn = land.wacc.map({w: P.syn_cost_per_gj(f, w) for w in land.wacc.unique()})
        comp = pd.DataFrame({"hydrogen": MU_H2[f] * land.lcoh_usd_gj,
                             "CO2 feed": sp["mu_co2"] * co2 + sp["mu_n2"] * P.C_N2_DEFAULT,
                             "synthesis plant": syn,
                             "synthesis electricity": sp["mu_el"] * lcoe_gj}) * UMM
        tot = comp.sum(axis=1)
        sh = comp["hydrogen"] / tot
        shares[f] = sh
        rows.append((f, comp.median(), tot.median(), sh.median(), sh.quantile(0.1), sh.quantile(0.9)))
    mpl.rcParams.update(STYLE)                 # the grid loaders reset rcParams on import
    fig, ax = plt.subplots(figsize=(12.5, 5.2))
    ys = np.arange(len(fuels))[::-1]
    for y, (f, cm, tot, s50, s10, s90) in zip(ys, rows):
        left = 0.0
        for name, col in parts:
            ax.barh(y, cm[name], left=left, color=col, height=0.62, label=name if y == ys[0] else None)
            left += cm[name]
        ax.text(left + 1.2, y, f"{s50:.0%} hydrogen", va="center", fontsize=17, color=INK,
                fontweight="bold")
    ax.set_yticks(ys)
    ax.set_yticklabels(fuels)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("median cost across 2,740 sites, $/MMBtu (LHV), 2025")
    ax.set_xlim(0, 105)
    ax.legend(frameon=False, ncol=4, loc="lower center", bbox_to_anchor=(0.45, 1.0), fontsize=15)
    _save(fig, "jt26_i_breakdown", bbox_inches="tight")
    allsh = pd.concat(shares.values())
    for f, cm, tot, s50, s10, s90 in rows:
        print(f"    {f:10s} median total {tot:5.1f}  parts " + ", ".join(f"{k} {v:.1f}" for k, v in cm.items())
              + f"  H2 share median {s50:.2f} p10 {s10:.2f} p90 {s90:.2f}")
    print(f"    all fuels, all cells: H2 share p5 {allsh.quantile(.05):.2f}  min {allsh.min():.2f}  max {allsh.max():.2f}")


def tea_contrast():
    """conventional TEA (fix one design, then price it) against this study
    (optimise the design at every site first), with how far the optimal design
    moves across the 2,740 sites (median weather year per cell)"""
    import glob
    from matplotlib.patches import FancyBboxPatch
    mpl.rcParams.update(STYLE)
    fs = sorted(glob.glob(str(inputs.MAPS / "lcoh_global_20??_reg.csv")))
    d = pd.concat([pd.read_csv(f) for f in fs])
    d = d[d.status == "ok"]
    g = d.groupby("cell_id")[["solar_share", "h2sto_h", "cap_ez", "cap_pv", "cap_wind"]].median()
    fig = plt.figure(figsize=(13.0, 5.4))
    ax = fig.add_axes([0, 0, 0.58, 1])
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.set_axis_off()

    def box(x, y, w, h, txt, fc, tc="white"):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.25", fc=fc, ec="none"))
        ax.text(x + w / 2, y + h / 2, txt, ha="center", va="center", fontsize=14.5, color=tc,
                fontweight="bold", linespacing=1.25)

    def arrow(x0, x1, y):
        ax.annotate("", xy=(x1, y), xytext=(x0, y), arrowprops=dict(arrowstyle="-|>", color=INK, lw=2.2))

    ax.text(0.1, 9.35, "Conventional techno-economic analysis", fontsize=17, color=GREY, fontweight="bold")
    box(0.1, 6.3, 4.3, 2.4, "one reference design\nfixed MW of solar, wind,\nelectrolyser and storage", "#9AA3AE")
    arrow(4.5, 5.6, 7.5)
    box(5.7, 6.3, 4.2, 2.4, "its cost,\nthe same design\ncopied everywhere", "#9AA3AE")
    ax.text(0.1, 4.85, "This study", fontsize=17, color=ACC, fontweight="bold")
    box(0.1, 1.2, 2.9, 3.0, "each site's\nhourly weather\nand local costs", "#2E5E8E")
    arrow(3.1, 3.7, 2.7)
    box(3.8, 1.2, 3.0, 3.0, "OPTIMISE\nthe design and\nhourly operation", ACC)
    arrow(6.9, 7.5, 2.7)
    box(7.6, 1.2, 2.3, 3.0, "least cost\nat that\nsite", "#1F7A4D")
    # right: how far the optimal design moves across sites
    bx = fig.add_axes([0.72, 0.3, 0.26, 0.5])
    items = [("solar", g.cap_pv, "#E0B000"), ("wind", g.cap_wind, "#2B7BB9"),
             ("electrolyser", g.cap_ez, "#4C78A8")]
    for k, (lab, v, c) in enumerate(items[::-1]):
        p10, p50, p90 = v.quantile([0.1, 0.5, 0.9])
        bx.plot([p10, p90], [k, k], color=c, lw=10, solid_capstyle="round", alpha=0.85)
        bx.plot(p50, k, "o", ms=11, mfc="white", mec=INK, mew=2)
    bx.set_yticks(range(len(items)))
    bx.set_yticklabels([lab for lab, *_ in items[::-1]], fontsize=16)
    bx.tick_params(axis="y", length=0)
    bx.set_xlim(0, 12.5)
    bx.set_xlabel("MW per MW of hydrogen output", fontsize=15)
    fig.text(0.62, 0.9, "The optimal design differs by site", fontsize=17, color=INK, fontweight="bold")
    fig.text(0.62, 0.84, "bar: 10th-90th percentile of 2,740 sites; circle: median", fontsize=13, color=GREY)
    h = g.h2sto_h.quantile([0.1, 0.5, 0.9])
    fig.text(0.62, 0.1, f"hydrogen store: {h.iloc[0]:.0f}-{h.iloc[2]:.0f} hours (median {h.iloc[1]:.0f})\n"
             f"{(g.solar_share > 0.6).mean():.0%} of sites solar-led, {(g.solar_share < 0.4).mean():.0%} wind-led",
             fontsize=15, color=INK, fontweight="bold", va="top", linespacing=1.4)
    _save(fig, "jt26_m_tea", bbox_inches="tight")
    for lab, v, _ in items + [("store h", g.h2sto_h, None)]:
        print(f"    {lab}: " + " / ".join(f"{x:.2f}" for x in v.quantile([0.1, 0.5, 0.9])))


def main():
    tea_contrast()
    breakdown()
    renewables()
    title_bg()
    sankey()
    cost()
    headlines()
    prices()


if __name__ == "__main__":
    main()
