"""
map_layers.py — talk graphics for the job-talk deck rebuilt on the
V1.3 manuscript (2026-10-02). Everything shown is in the paper or its
Supplementary Information; the deck adds no analysis of its own.

  methods   jt13_m_framework, jt13_m_stage1, jt13_m_cascade, jt13_m_demand,
            jt13_m_buyside, jt13_m_security, jt13_m_budget, and the three
            decision rules jt13_eq_parity, jt13_eq_fig4a, jt13_eq_fig4b
  results   jt13_trade (transport between cells and the trade corridors,
            Supplementary Note 6), jt13_fig3 and jt13_fig3_ft (Fig. 3 and
            Supplementary Fig. 5), jt13_fig4a and jt13_fig4b (the two panels
            of Fig. 4, each on its own canvas), jt13_fig5 (Fig. 5)
  intro     jt13_i_cost (the cost barrier, without the break-even carbon
            prices that the paper no longer reports)

The method pictures are drawn on a canvas the size of a slide's figure area
(12.9 x 6.3 in), so they show at their own type size; every box label is
shrunk until it fits its box (_fit_text), never the other way round.
The paper figures are drawn by their own code (fig_main_sites,
fig5a_chain.draw_a_circles, the panel-b code of fig5_chain,
security_budget._figure); only the canvas is smaller, so on a slide the
lettering is about 1.3-1.8 times the paper's. Nothing here writes to
data/cost or to the paper's figure folder.

From scripts/:  conda run -n synfuel python -u -m lcof.map_layers [jobs]
                jobs: methods trade fig3 fig4 fig5 cost  (default: all)
Outputs:        cf_global_final/figures/slides2026/v13/*.png
"""
from __future__ import annotations

import shutil

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

mpl.use("Agg")

from . import inputs, params as P

OUT = inputs.PROJECT / "cf_global_final" / "figures" / "slides2026" / "v13"
OUT.mkdir(parents=True, exist_ok=True)

INK, GREY, LIGHT = "#142B45", "#444444", "#8C96A3"
BLUE, ORANGE, GREEN, RED, PURPLE = "#2E5E8E", "#E69F00", "#1F7A4D", "#C0502D", "#6A4C93"
PALE = "#EEF2F6"
UMM = 1.0551                      # GJ per MMBtu
W, H = 12.9, 6.3                  # a slide's figure area, inches
STYLE = {"font.family": "Arial", "font.size": 16, "axes.edgecolor": INK,
         "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
         "axes.labelsize": 16, "xtick.labelsize": 15, "ytick.labelsize": 15,
         "axes.spines.top": False, "axes.spines.right": False}
FITTED = []                       # (picture, final font size) of every fitted label


def _style():
    mpl.rcParams.update(mpl.rcParamsDefault)
    mpl.rcParams.update(STYLE)


def _save(fig, name, dpi=220, **kw):
    fig.savefig(OUT / f"{name}.png", dpi=dpi, bbox_inches="tight",
                facecolor=kw.pop("facecolor", "white"), **kw)
    plt.close(fig)
    print(f"  saved {name}")


def _blank(w=W, h=H):
    fig = plt.figure(figsize=(w, h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    return fig, ax


def _fit_text(ax, x, y, w, h, text, fs, color, bold=True, lsp=1.22, pad=0.12, ha="center",
              tag=""):
    """text centred in the box (x, y, w, h) in inches; the font shrinks in
    0.5 pt steps until the text fits inside the box less its padding"""
    fig = ax.figure
    r = fig.canvas.get_renderer()
    tx = x + w / 2 if ha == "center" else x + pad
    t = ax.text(tx, y + h / 2, text, ha=ha, va="center", fontsize=fs, color=color,
                fontweight="bold" if bold else "normal", linespacing=lsp, zorder=3, clip_on=False)
    while fs > 9:
        bb = t.get_window_extent(renderer=r)
        if bb.width <= (w - 2 * pad) * fig.dpi and bb.height <= (h - 2 * pad) * fig.dpi:
            break
        fs -= 0.5
        t.set_fontsize(fs)
    FITTED.append((tag, fs))
    return t


def _box(ax, x, y, w, h, text, fc, tc="white", fs=17, bold=True, lsp=1.22, tag=""):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.10",
                                fc=fc, ec="none", zorder=2, clip_on=False))
    return _fit_text(ax, x, y, w, h, text, fs, tc, bold=bold, lsp=lsp, tag=tag)


def _arrow(ax, xy1, xy2, color=INK, lw=2.6, ms=18):
    ax.add_patch(FancyArrowPatch(xy1, xy2, arrowstyle="-|>", color=color, lw=lw,
                                 mutation_scale=ms, zorder=1, clip_on=False))


def _row(ax, items, y, h, fs, gap=0.4, x0=0.1, x1=W - 0.1, arrows=True, tag=""):
    """boxes of equal width between x0 and x1, joined by arrows"""
    n = len(items)
    w = (x1 - x0 - gap * (n - 1)) / n
    xs = []
    for k, (txt, col) in enumerate(items):
        x = x0 + k * (w + gap)
        _box(ax, x, y, w, h, txt, col, fs=fs, tag=tag)
        xs.append(x)
        if arrows and k < n - 1:
            _arrow(ax, (x + w + 0.04, y + h / 2), (x + w + gap - 0.04, y + h / 2))
    return xs, w


# ====================================================================== methods
def m_framework():
    """the six steps, the data behind each and the figure each one feeds"""
    _style()
    fig, ax = _blank()
    data = ["ERA5 hourly wind\nand solar,\n2006-2025",
            "equipment costs;\ncost of capital\nby country",
            "EDGAR emissions;\nUN and Energy\nInstitute data",
            "monthly import\nprices, 30\neconomies",
            "20 disruptions,\n1956-2026; value\nof lost gas",
            "GDP; land use;\ncarbon prices\nin force"]
    steps = [("1  Hydrogen\nhourly LP,\n2,740 cells x\n20 years", BLUE),
             ("2  Six fuels\nfrom hydrogen,\nCO2 and\nelectricity", BLUE),
             ("3  Demand\nfuel use that\nelectricity\ncannot reach", GREEN),
             ("4  Import prices\nnormal and\ndisruption\nmonths", RED),
             ("5  Security\nvalue of a\ndomestic\ngigajoule", RED),
             ("6  Budget\nand land\n1-3% of GDP;\nCO2 displaced", PURPLE)]
    x0, gap = 0.1, 0.22
    n = len(steps)
    w = (W - 0.2 - gap * (n - 1)) / n
    ax.text(x0, 6.12, "DATA", fontsize=16, color=LIGHT, fontweight="bold", va="center")
    ax.text(x0, 4.12, "STEPS", fontsize=16, color=LIGHT, fontweight="bold", va="center")
    for k, (d, (st, col)) in enumerate(zip(data, steps)):
        x = x0 + k * (w + gap)
        _box(ax, x, 4.45, w, 1.45, d, PALE, tc=INK, fs=16, bold=False, tag="fw data")
        _arrow(ax, (x + w / 2, 4.42), (x + w / 2, 4.02), color=LIGHT, lw=2.2, ms=16)
        _box(ax, x, 1.85, w, 2.12, st, col, fs=17.5, tag="fw step")
        if k < n - 1:
            _arrow(ax, (x + w + 0.03, 2.91), (x + w + gap - 0.03, 2.91))

    def bracket(k0, k1, label):
        xa = x0 + k0 * (w + gap) + 0.08
        xb = x0 + k1 * (w + gap) + w - 0.08
        ax.plot([xa, xa, xb, xb], [1.74, 1.62, 1.62, 1.74], color=INK, lw=1.5, clip_on=False)
        ax.text((xa + xb) / 2, 1.5, label, ha="center", va="top", fontsize=16, color=INK,
                fontweight="bold", linespacing=1.15)
    bracket(0, 2, "Figs 1 and 2: cost, demand, mismatch")
    bracket(3, 3, "Fig. 3\nhedge")
    bracket(4, 4, "Fig. 4\ntipping, CO2")
    bracket(5, 5, "Figs 4a and 5\nlimits")
    ax.text(W / 2, 0.28, "Fossil prices, demand and carbon prices are held at observed values; "
            "only the synthetic plant's cost is projected forward.",
            ha="center", va="center", fontsize=16, color=INK)
    _save(fig, "jt13_m_framework")


def m_stage1():
    _style()
    fig, ax = _blank()
    cols = [("CHOOSE\n(decision variables)\n\nsolar MW, wind MW,\nelectrolyser MW,\n"
             "battery MW and MWh,\nhydrogen store MWh,\nhourly dispatch", BLUE),
            ("SUBJECT TO\n(constraints)\n\npower balance every hour,\nwith battery and curtailment;\n"
             "both stores end the year\nwhere they began;\nconstant hydrogen output\nin all 8,760 hours",
             "#4A4A4A"),
            ("MINIMISE\n(objective)\n\nannualised capital at the\ncountry's cost of capital\n"
             "+ fixed O&M + water\n\nLCOH = minimum cost /\nhydrogen delivered", GREEN)]
    _row(ax, cols, 2.6, 3.6, 18, gap=0.45, tag="stage1 box")
    props = [("SCALE-FREE", "every term is linear in the output F, so no plant size is assumed"),
             ("CONSTANT OUTPUT", "the hydrogen store rides through multi-day lulls; a battery is built in "
                                 "9% of cell-years (cost effect < 0.1%)"),
             ("54,800 LINEAR PROGRAMMES", "2,740 cells x 20 weather years; each cell at its median year")]
    for j, (h, b) in enumerate(props):
        y = 2.2 - j * 0.78
        ax.text(0.12, y, h, fontsize=17, color=RED, fontweight="bold", va="center")
        ax.text(0.12, y - 0.36, b, fontsize=16.5, color=GREY, va="center")
    _save(fig, "jt13_m_stage1")


def m_cascade():
    """the cascade equation, the route coefficients and the CO2 rule"""
    _style()
    fig, ax = _blank()
    eq = (r"$L_{f,i}\;=\;\underbrace{\mu_f^{\mathrm{H_2}}\,L_{\mathrm{H_2},i}}_{\textrm{hydrogen}}"
          r"\;+\;\underbrace{\mu_f^{\mathrm{el}}\,L_{\mathrm{el},i}}_{\textrm{auxiliary power}}"
          r"\;+\;\underbrace{\mu_f^{\mathrm{CO_2}}\,p_i^{\mathrm{CO_2}}}_{\mathrm{CO_2}}"
          r"\;+\;\underbrace{c_{f,c}^{\,\mathrm{syn}}}_{\textrm{synthesis plant}}$")
    ax.text(W / 2, 5.55, eq, usetex=True, fontsize=28, color=INK, ha="center", va="center")
    ax.text(W / 2, 4.5, "no second optimisation: the cell's own hydrogen and electricity; "
            "synthesis plant at a 90% load factor", ha="center", va="center", fontsize=16, color=GREY)
    rows = [("ammonia", "Haber-Bosch, own air separation", "ammonia"),
            ("methanol", "CO2 hydrogenation", "methanol"),
            ("e-methane", "methanation", "e-methane"),
            ("e-diesel, e-kerosene", "reverse water-gas shift + Fischer-Tropsch", "e-diesel"),
            ("ethanol", "CO2-based ethanol synthesis", "ethanol")]
    xs = [0.45, 3.6, 9.1, 11.45]
    hy = 3.92
    for x, t, ha in zip(xs, ["fuel", "route", "H2 per unit fuel", "CO2, kg/GJ"],
                        ["left", "left", "center", "center"]):
        ax.text(x, hy, t, fontsize=15.5, color=LIGHT, fontweight="bold", ha=ha, va="center")
    ax.plot([0.35, 12.55], [hy - 0.24, hy - 0.24], color="#C8CFD8", lw=1.0)
    for j, (name, route, key) in enumerate(rows):
        y = hy - 0.56 - j * 0.44
        t = P.FUELS[key]
        ax.text(xs[0], y, name, fontsize=17, color=INK, fontweight="bold", va="center")
        ax.text(xs[1], y, route, fontsize=16.5, color=GREY, va="center")
        ax.text(xs[2], y, f"{1 / t['eta_syn']:.2f}", fontsize=17, color=INK, ha="center", va="center")
        co2 = t["mu_co2"] * 1000
        ax.text(xs[3], y, "none" if co2 == 0 else f"{co2:.0f}", fontsize=17, color=INK,
                ha="center", va="center")
    _box(ax, 0.35, 0.05, 12.2, 1.0,
         "CO2 from the cheapest point source within 1,000 km: US\\$50-145/t delivered (median 72);\n"
         "153 remote cells beyond 1,000 km buy direct air capture at US\\$500/t", "#F6E3DB",
         tc=INK, fs=17, bold=False, tag="cascade co2")
    _save(fig, "jt13_m_cascade")


def m_demand():
    _style()
    fig, ax = _blank()
    steps = [("sectoral CO2\non a 0.1 degree\ngrid (EDGAR)", GREEN),
             ("convert to\nfuel energy\nby sector", GREEN),
             ("keep the share\nsynthetic fuel\ncan serve", GREEN),
             ("anchor to UN\nbalances 2023,\nupdated to 2025", GREEN),
             ("76.2 billion\nMMBtu a year,\n139 economies", INK)]
    _row(ax, steps, 4.55, 1.6, 17.5, tag="demand box")
    rows = [("aviation", "100%", "e-kerosene"),
            ("shipping", "100%", "methanol 70%, ammonia 30%"),
            ("chemical feedstock", "100%", "ammonia 62%, methanol 38%"),
            ("industry, high-temperature heat", "40%", "gas share to e-methane, oil share to e-diesel"),
            ("road transport", "30%", "e-diesel 80%, ethanol 20%"),
            ("buildings, hard-to-retrofit heat", "20%", "gas share to e-methane, oil share to e-diesel"),
            ("power generation", "0%", "not addressed")]
    hy = 3.98
    for x, t, ha in ((0.4, "sector", "left"), (5.3, "share served", "center"),
                     (6.45, "synthetic fuel  (a substitution scenario, not a forecast)", "left")):
        ax.text(x, hy, t, fontsize=15.5, color=LIGHT, fontweight="bold", ha=ha, va="center")
    ax.plot([0.3, 12.6], [hy - 0.24, hy - 0.24], color="#C8CFD8", lw=1.0)
    for j, (a, s, f) in enumerate(rows):
        y = hy - 0.55 - j * 0.48
        ax.text(0.4, y, a, fontsize=17, color=INK, va="center")
        ax.text(5.3, y, s, fontsize=17, color=GREEN, fontweight="bold", ha="center", va="center")
        ax.text(6.45, y, f, fontsize=17, color=GREY, va="center")
    _save(fig, "jt13_m_demand")


def m_buyside():
    _style()
    fig, ax = _blank()
    steps = [("10 dated supply\nevents, 2011-2026:\n7 oil, 6 gas\n(3 both)", RED),
             ("event months and\nthe 6 months after\nleave the normal\nmonths; so does\nCOVID", RED),
             ("events under\n6 months apart\nform one regime", RED),
             ("NORMAL: 12 clean\nmonths before\neach regime\nDISRUPTION:\nthe regime months", INK),
             ("SYNTHETIC:\ncheapest domestic\ncell, 20 weather\nyears + US\\$1/GJ", BLUE)]
    _row(ax, steps, 3.95, 2.25, 17, gap=0.36, tag="buyside box")
    ax.text(W / 2, 3.45, "each economy's OWN import price, never a neighbour's", ha="center",
            fontsize=18, color=INK, fontweight="bold", va="center")
    rows = [("14 economies", "ammonia: own customs import prices"),
            ("11 economies", "ammonia: urea-implied price, scaled to the region"),
            ("5 economies", "ammonia: production cost at the administered gas price"),
            ("all 30", "diesel and jet fuel: customs prices, median 98.6% of months observed")]
    for j, (a, b) in enumerate(rows):
        y = 2.88 - j * 0.45
        ax.text(3.2, y, a, fontsize=17, color=RED, ha="right", va="center", fontweight="bold")
        ax.text(3.5, y, b, fontsize=17, color=GREY, ha="left", va="center")
    ax.text(W / 2, 0.42, "cost ratio = synthetic cost / median normal price;   inside the disruption range: "
            "synthetic cost ≤ 98th percentile\nof disruption prices", ha="center", va="center",
            fontsize=16, color=INK, linespacing=1.3)
    _save(fig, "jt13_m_buyside")


def m_security():
    _style()
    fig, ax = _blank()
    top = [("event rate, ρ", "0.26 cut-offs and\n0.15 closures a year,\n2000-2026"),
           ("duration, T", "median 8 months\nand 3.5 months"),
           ("share stranded, φ", "cut-off: largest\nsupplier's share;\nclosure: all imports"),
           ("oil stocks, M", "IEA oil chains: half\nof a cut-off, all\nof a closure")]
    x0, gap = 0.1, 0.45
    n = len(top)
    w = (W - 0.2 - gap * (n - 1)) / n
    for k, (h, b) in enumerate(top):
        x = x0 + k * (w + gap)
        _box(ax, x, 5.25, w, 0.9, h, BLUE, fs=19, tag="security head")
        ax.text(x + w / 2, 4.5, b, ha="center", va="center", fontsize=16.5, color=GREY,
                linespacing=1.22)
        if k < n - 1:
            ax.text(x + w + gap / 2, 5.7, "×", ha="center", va="center", fontsize=24, color=INK)
    _arrow(ax, (W / 2, 3.88), (W / 2, 3.55))
    _box(ax, 1.0, 2.62, W - 2.0, 0.88,
         "q = Σ ρ · (T / 12) · φ · (1 − M):  the expected share of a marginal\n"
         "imported gigajoule that is lost each year", INK, fs=17.5, tag="security q")
    _box(ax, 0.1, 0.05, 6.05, 2.3,
         "value of a unit of fuel lost, v,\nproportional to GDP per unit of fuel use\n"
         "central: US\\$23/MMBtu (European median)\nreference: US\\$185/MMBtu\n"
         "(EUR600/MWh, European gas-security planning)", RED, fs=17, tag="security v")
    ax.text(6.45, 1.2, "×", ha="center", va="center", fontsize=24, color=INK)
    _box(ax, 6.75, 0.05, 6.05, 2.3,
         "security margin per gigajoule\nw = v · m · q\nm = 1.3 transport fuels, 1.0 gas family;\n"
         "counted only while the chain\nstill imports", GREEN, fs=17.5, tag="security w")
    _save(fig, "jt13_m_security")


def m_budget():
    _style()
    fig, ax = _blank()
    boxes = [("BUDGET\n\n1, 2 or 3% of GDP\na year pays only\nthe premium over\nthe normal price", PURPLE),
             ("ORDER\n\nFig. 5: lowest\npremium first\n\nFig. 4a: imported\nfuel chains first", PURPLE),
             ("LAND\n\n5% of eligible land,\nat most 2% of\nterritory; hydrogen\nfrom each cell's\n"
              "solar and wind", PURPLE),
             ("IMPORTS\n\na domestic GJ\nreplaces imports\nonly in its own\nfamily: gas or oil", PURPLE)]
    _row(ax, boxes, 2.4, 3.8, 18.5, gap=0.45, tag="budget box")
    ax.text(W / 2, 1.78, "CO2 displaced = domestic fuel x emission factor of the fuel it replaces",
            ha="center", va="center", fontsize=18, color=INK, fontweight="bold")
    ax.text(W / 2, 1.12, "natural gas 0.056   ·   oil products 0.074   ·   jet fuel 0.072   ·   "
            "grey ammonia 0.129   (t CO2 per GJ)", ha="center", va="center", fontsize=16.5, color=GREY)
    ax.text(W / 2, 0.45, "synthetic fuel is credited with zero emissions; fossil CO2 feedstock counts once, "
            "through the fuel it displaces", ha="center", va="center", fontsize=16, color=GREY)
    _save(fig, "jt13_m_budget")


def equations():
    """the three decision rules, each rendered with LaTeX on a transparent canvas"""
    eqs = {
        "parity": r"$\underbrace{L_{c,f}-p_{c,f}}_{\textrm{extra cost}}\;\le\;"
                  r"\underbrace{v_c\,m_f\,q_{c,f}}_{\textrm{security margin}}$",
        "fig4a": r"$\underbrace{\frac{S_c}{\Gamma_c}}_{\textrm{extra cost}}\;-\;"
                 r"\underbrace{\frac{\sum_f w_{c,f}\,r_{c,f}}{\Gamma_c}}_{\textrm{security margin}}\;\le\;"
                 r"\underbrace{\tau_c}_{\textrm{carbon incentive}}$",
        "fig4b": r"$\mathrm{CO_2}(t)=\sum_{c,f}\epsilon_f\Big(\underbrace{I_{c,f}\,"
                 r"\mathbf{1}\big[t^{\mathrm{sec}}_{c,f}\le t\big]}_{\textrm{imports: security parity}}"
                 r"+\underbrace{\big(D_{c,f}-I_{c,f}\big)\,\mathbf{1}\big[t^{\mathrm{cost}}_{c,f}"
                 r"\le t\big]}_{\textrm{other demand: cost parity}}\Big)$",
    }
    mpl.rcParams.update({"text.usetex": True,
                         "text.latex.preamble": r"\usepackage{amsmath}\usepackage{amssymb}"})
    for k, s in eqs.items():
        fig = plt.figure(figsize=(11, 1.6))
        fig.text(0.0, 0.5, s, fontsize=26, color=INK, va="center")
        fig.savefig(OUT / f"jt13_eq_{k}.png", dpi=300, bbox_inches="tight", transparent=True)
        plt.close(fig)
    mpl.rcParams.update({"text.usetex": False})
    print("  saved jt13_eq_*")


# ====================================================================== results
def trade():
    """Supplementary Note 6: fuel moved between cells (Supplementary Table 12)
    and ammonia along the trade corridors (Supplementary Table 13)"""
    _style()
    import matplotlib.patches as mp
    ts = pd.read_csv(inputs.MAPS / "transport_summary.csv")
    ts = ts[np.isclose(ts.t_per_1000km, 1.0)].set_index("rule")
    cor = pd.read_csv(inputs.MAPS / "corridors_discussion.csv")
    fig = plt.figure(figsize=(13.0, 5.6))
    a = fig.add_axes([0.075, 0.20, 0.20, 0.64])
    b = fig.add_axes([0.585, 0.12, 0.40, 0.72])
    # a: share of demand in build-first cells when fuel can move (spare land only)
    labels = ["own cell", "within\ncountries", "across\nborders"]
    vals = [float(ts.build_first_demand_share_fig2.iloc[0]),
            float(ts.build_first_demand_share["domestic-capped"]),
            float(ts.build_first_demand_share["open-capped"])]
    save = [None, float(ts.demand_weighted_saving_pct["domestic-capped"]),
            float(ts.demand_weighted_saving_pct["open-capped"])]
    xs = np.arange(3)
    a.bar(xs, [v * 100 for v in vals], color=["#9AA5B1", "#5B8DB8", BLUE], width=0.64)
    for x, v, s_ in zip(xs, vals, save):
        a.text(x, v * 100 + 1.5, f"{v:.0%}", ha="center", va="bottom", fontsize=19, color=INK,
               fontweight="bold")
        if s_ is not None:
            a.text(x, v * 50, f"cost\n−{s_:.0f}%", ha="center", va="center", fontsize=13.5,
                   color="white", fontweight="bold", linespacing=1.1)
    a.set_xticks(xs)
    a.set_xticklabels(labels, fontsize=14.5)
    a.set_xlim(-0.55, 2.55)
    a.set_ylim(0, 80)
    a.set_yticks([0, 20, 40, 60, 80])
    a.set_ylabel("% of demand in build-first cells")
    a.tick_params(axis="x", length=0)
    fig.text(0.012, 0.955, "a   Fuel moved between cells", fontsize=17, color=INK,
             fontweight="bold", va="center")
    # b: corridors, overland then by sea
    name = {"Iberia -> Germany": "Iberia → Germany",
            "North Africa -> Italy/central Europe": "North Africa → Italy, central Europe",
            "Inner Mongolia/NW China -> North China Plain": "Inner Mongolia → North China Plain",
            "Western Australia (Pilbara) -> Japan": "Western Australia → Japan",
            "Northern Chile -> Rotterdam (via Panama)": "Northern Chile → Rotterdam (Panama)",
            "Oman (Duqm) -> Rotterdam (via Suez)": "Oman → Rotterdam (Suez)",
            "Oman (Duqm) -> Rotterdam (via Cape, Red Sea closed)": "Oman → Rotterdam (Cape)"}
    land = cor[cor["mode"] == "overland"]
    sea = cor[cor["mode"] == "sea"]
    ys = list(np.arange(len(land))[::-1] + len(sea) + 0.6) + list(np.arange(len(sea))[::-1] * 1.0)
    rows = pd.concat([land, sea])
    for y, (_, r) in zip(ys, rows.iterrows()):
        b.barh(y + 0.19, r.local, height=0.34, color="#C9CED6")
        b.barh(y - 0.19, r.source, height=0.34, color=BLUE)
        b.barh(y - 0.19, r.transport, left=r.source, height=0.34, color=ORANGE)
        b.text(max(r.local, r.delivered) + 2.5, y, f"−{r.saving_pct:.0f}%", va="center", ha="left",
               fontsize=16, color=GREEN, fontweight="bold")
    ysep = len(sea) - 0.2
    b.axhline(ysep, color="#8A94A0", lw=0.9, ls=(0, (5, 3)))
    b.text(124, max(ys) + 0.55, "overland", ha="right", va="center", fontsize=14, color="#5A6570",
           style="italic")
    b.text(124, ysep - 0.32, "by sea", ha="right", va="center", fontsize=14, color="#5A6570",
           style="italic")
    b.set_yticks(ys)
    b.set_yticklabels([name.get(c, c) for c in rows.corridor], fontsize=14.5)
    b.tick_params(axis="y", length=0)
    b.set_xlim(0, 125)
    b.set_ylim(min(ys) - 0.6, max(ys) + 0.9)
    b.set_xlabel("ammonia, US\\$ per MMBtu")
    b.legend(handles=[mp.Patch(color="#C9CED6", label="made at the destination"),
                      mp.Patch(color=BLUE, label="made at the source"),
                      mp.Patch(color=ORANGE, label="transport")],
             loc="lower left", bbox_to_anchor=(-0.02, 1.0), ncol=3, fontsize=14, frameon=False,
             handlelength=1.0, columnspacing=1.2, borderaxespad=0.2)
    fig.text(0.315, 0.955, "b   Ammonia along trade corridors", fontsize=17, color=INK,
             fontweight="bold", va="center")
    _save(fig, "jt13_trade")
    print(f"    build-first {vals}, savings {save}; corridor transport "
          f"{cor.transport.min():.1f}-{cor.transport.max():.1f} $/MMBtu, saving "
          f"{cor.saving_pct.min():.0f}-{cor.saving_pct.max():.0f}%")


def _nat():
    from .fig_main_cost import NAT_RC
    mpl.rcParams.update(mpl.rcParamsDefault)
    mpl.rcParams.update(NAT_RC)


def fig3(key="ammonia", name="jt13_fig3", size=(7.2, 5.0)):
    """Fig. 3 (or its diesel and jet version) drawn by fig_main_sites into a
    landscape canvas; the module's own CSV writes are switched off so the
    data tables and the paper figure are left untouched"""
    from . import fig_main_sites as F3
    _nat()
    fig, ax = plt.subplots(figsize=size)
    orig = pd.DataFrame.to_csv
    pd.DataFrame.to_csv = lambda self, *a, **k: None
    try:
        info = F3.main(key, ax=ax, columns=True, legend=True, save=False)
    finally:
        pd.DataFrame.to_csv = orig
    # the rows are closer than in the paper, so the column names move up a
    # little to clear the unit line under "Bill"
    for t in ax.texts:
        if t.get_text() in ("Bill", "Risk"):
            x, y = t.get_position()
            t.set_position((x, y + 0.3))
    fig.subplots_adjust(left=0.18, right=0.97, top=0.995, bottom=0.085)
    fig.savefig(OUT / f"{name}.png", dpi=400, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  saved {name}")
    return info


def fig4a(size=(6.3, 4.6)):
    from .fig5a_chain import draw_a_circles
    _nat()
    d = pd.read_csv(inputs.MAPS / "fig5a_chain.csv", index_col=0)
    fig, ax = plt.subplots(figsize=size)
    fig.subplots_adjust(left=0.21, right=0.985, top=0.885, bottom=0.10)
    draw_a_circles(ax, d, legend_anchor=(-0.02, 1.02), margin="column")
    ax.set_xlabel("US\\$ per tonne of CO$_2$", fontsize=7)
    fig.savefig(OUT / "jt13_fig4a.png", dpi=450, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  saved jt13_fig4a")


def fig4b(size=(6.9, 3.25)):
    """panel b of Fig. 4 as drawn in fig5_chain.main, legend at the right"""
    from .fig5_chain import panel_b_data, VY
    from .global_trajectory import REGION_COL
    _nat()
    p, tj, q_at = panel_b_data(write=False)
    p = p.copy()
    p.loc[p.country == "India", "region"] = "India"
    RCOL = {"China": REGION_COL["China"], "India": "#F0E442",
            **{k: v for k, v in REGION_COL.items() if k != "China"}}
    order = [r for r in RCOL if r in set(p.region)]
    stack = [[float((q_at(t, p[p.region == r]) * p[p.region == r].ef).sum() / 1e9) for t in VY]
             for r in order]
    fig, b = plt.subplots(figsize=size)
    fig.subplots_adjust(left=0.09, right=0.70, top=0.97, bottom=0.15)
    b.stackplot(VY, stack, colors=[RCOL[r] for r in order], labels=order, lw=0.3, edgecolor="white")
    b.plot(VY, tj.cost_gt, color="white", lw=2.0, solid_capstyle="round")
    b.plot(VY, tj.cost_gt, color="#14304A", lw=0.9, ls=(0, (2.2, 1.6)), label="Cost parity alone")
    top = max(float(tj.sec_gt.max()), float(tj.cost_gt.max()))
    step = next(st for st in (0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 1.0) if st * 6 >= top * 1.15)
    b.set_xlim(2025, 2050)
    b.set_ylim(0, step * 6)
    b.set_yticks(np.arange(0, step * 6 + 1e-9, step))
    b.set_xticks([2025, 2030, 2035, 2040, 2045, 2050])
    b.tick_params(axis="both", labelsize=7)
    b.set_xlabel("Build year", fontsize=7)
    b.set_ylabel("Annual CO$_2$ displaced (Gt yr$^{-1}$)", fontsize=7)
    h, l = b.get_legend_handles_labels()
    b.legend(h[::-1], l[::-1], fontsize=7, frameon=False, loc="center left",
             bbox_to_anchor=(1.03, 0.5), handlelength=1.4, labelspacing=0.55, borderaxespad=0.0)
    for sp in ("top", "right"):
        b.spines[sp].set_visible(False)
    assert abs(sum(v[-1] for v in stack) - float(tj.sec_gt.iloc[-1])) < 1e-6
    fig.savefig(OUT / "jt13_fig4b.png", dpi=450, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    t = tj.set_index("year")
    print(f"  saved jt13_fig4b: security {t.sec_gt[2025]:.2f}/{t.sec_gt[2030]:.2f}/{t.sec_gt[2050]:.2f} Gt, "
          f"cost parity {t.cost_gt[2025]:.2f}/{t.cost_gt[2030]:.2f}/{t.cost_gt[2050]:.2f} Gt")


def fig5(shrink=0.88):
    """Fig. 5 drawn by security_budget._figure on a canvas `shrink` times the
    paper's (the lettering is then 1/shrink times larger relative to the
    bars), written to the talk folder instead of the paper's"""
    from matplotlib.axes import Axes
    from . import security_budget as SB
    from .coreset import CORE30_LIST
    _nat()
    d = pd.read_csv(inputs.MAPS / "security_budget.csv", index_col=0).loc[CORE30_LIST]
    mm0, out0, text0 = SB.MM, SB.OUT, Axes.text

    def text(self, x, y, s, *a, **k):
        # the rotated group labels sit at x = 102; with the larger relative
        # type they would touch the land-ceiling caps at 100, so move them right
        if x == 102.0 and k.get("rotation") == 90:
            x = 103.0
        return text0(self, x, y, s, *a, **k)
    SB.MM, SB.OUT, Axes.text = mm0 * shrink, OUT, text
    try:
        SB._figure(d, None)
    finally:
        SB.MM, SB.OUT, Axes.text = mm0, out0, text0
    (OUT / "fig_security_budget.png").replace(OUT / "jt13_fig5.png")
    (OUT / "fig_security_budget.pdf").unlink(missing_ok=True)
    print("  saved jt13_fig5")


# ====================================================================== intro
def cost():
    """the cost barrier: electricity that reaches the fuel, and the synthetic /
    fossil cost ratio (median of the assessed economies); no break-even
    carbon price, which the paper no longer reports"""
    from .map_base import power_to_fuel, ROUTE_COL
    _style()
    ptf = power_to_fuel()
    b = pd.read_csv(inputs.MAPS / "breakeven_carbon_2025.csv")
    b["r"] = b.lcof_usd_gj / b.p_fossil_usd_gj
    # the paper's 139 assessed economies (Fig. 4b), not the 143 of the old layer
    keep = set(pd.read_csv(inputs.MAPS / "fig5b_chain_pairs.csv").country)
    b = b[b.country.isin(keep)]
    g = b.groupby("fuel").agg(r=("r", "median"))
    n_econ = b.country.nunique()
    order = ["ammonia", "hydrogen", "methanol", "ethanol", "e-diesel", "e-kerosene", "e-methane"]
    col = dict(ROUTE_COL, hydrogen="#7F7F7F")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13.0, 5.4),
                                 gridspec_kw=dict(width_ratios=[1, 1], wspace=0.42))
    ys = np.arange(len(order))[::-1]
    for y, f in zip(ys, order):
        v = ptf[f] * 100
        a1.barh(y, v, color=col[f], height=0.62)
        a1.barh(y, 100 - v, left=v, color="#E4E8EE", height=0.62)
        a1.text(v - 2, y, f"{v:.0f}%", ha="right", va="center", fontsize=16, color="white",
                fontweight="bold")
        r = float(g.at[f, "r"])
        a2.barh(y, r, color=col[f], height=0.62)
        a2.text(r + 0.1, y, f"{r:.1f}x", ha="left", va="center", fontsize=16, color=INK,
                fontweight="bold")
    for a in (a1, a2):
        a.set_yticks(ys)
        a.set_yticklabels(order, fontsize=16)
        a.tick_params(axis="y", length=0)
        a.set_ylim(-1.0, len(order) - 0.4)
    a1.set_xlim(0, 100)
    a1.set_xticks([0, 50, 100])
    a1.set_xlabel("share of the electricity that ends up in the fuel, %")
    a1.set_title("a   about half the electricity is lost", fontsize=17, color=INK,
                 fontweight="bold", loc="left", pad=12)
    a2.axvline(1, color=INK, lw=1.4, ls="--")
    a2.text(1.1, -0.62, "fossil price", fontsize=14, color=INK, va="center", ha="left")
    a2.set_xlim(0, 6.4)
    a2.set_xticks([0, 1, 2, 3, 4, 5, 6])
    a2.set_xlabel(f"synthetic cost / fossil price\n(median of {n_econ} economies)")
    a2.set_title("b   the fuel costs 2-5 times fossil", fontsize=17, color=INK,
                 fontweight="bold", loc="left", pad=12)
    _save(fig, "jt13_i_cost")
    print(f"    ratios {g.r.round(2).to_dict()}")


# ====================================================================== SI figures
def si_figures(src):
    """the two Supplementary figures drawn for V1.3 (LCOH map, fixed design)"""
    for f in ("fig_si_lcoh_map.png", "fig_si_fixed_design.png"):
        shutil.copy2(src / f, OUT / f)
        print(f"  copied {f}")


def main():
    import sys
    from pathlib import Path
    jobs = sys.argv[1:] or ["methods", "trade", "fig3", "fig4", "fig5", "cost"]
    if "methods" in jobs:
        m_framework(); m_stage1(); m_cascade(); m_demand(); m_buyside(); m_security(); m_budget()
        equations()
        small = [(t, f) for t, f in FITTED if f < 15.5]
        print(f"  fitted {len(FITTED)} box labels; smallest {min(f for _, f in FITTED):.1f} pt"
              + (f"; below 15.5 pt: {small}" if small else ""))
    if "trade" in jobs:
        trade()
    if "fig3" in jobs:
        fig3()
        fig3("ft", "jt13_fig3_ft")
    if "fig4" in jobs:
        fig4a()
        fig4b()
    if "fig5" in jobs:
        fig5()
    if "cost" in jobs:
        cost()
    if "si" in jobs:
        si_figures(Path(sys.argv[sys.argv.index("si") + 1]))


if __name__ == "__main__":
    main()
