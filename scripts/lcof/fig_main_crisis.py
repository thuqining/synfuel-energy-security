"""
fig_main_crisis.py — Extended Data: each dated disruption, economy by
economy, on Figure 3's comparator and rules.

  a  Ammonia, the Figure 3 fuel: the six natural-gas events one by one
     (rows) against the 30 core economies (columns, Figure 3 order): the
     real (2025 US$) move of the event-window median over the regime's
     matched contiguous twelve-month clean baseline, each economy's own
     import price. Events inside one compound regime share that regime's
     baseline, so the rows are comparable with the orange line of Fig. 3.
  b  Diesel and jet fuel: the seven oil events, same construction.
  Beside each heatmap (2026-10-05): one violin per event, the spread of
  its price change across the 30 economies, with the median economy. Hatched cells rest mainly on the
  validated urea proxy or constructed months (fewer than half of the event
  or baseline months are observed customs prices).

Data: data/cost/figure3_member_event_audit.csv (audit_figure3). The script
also writes the all-country world-pool tables kept as Supplementary data
(ed_crisis_by_country_regime.csv, ed_crisis_pooled_by_fuel.csv): every
modelled country's grey rival for the seven synthetic fuels on the same
rules, marker-based national gas prices outside the core 30.

From scripts/:  conda run -n synfuel python -u -m lcof.fig_main_crisis
Output: cf_global_final/figures/pptx/fig_main_crisis.(pdf|png)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

mpl.use("Agg")

from . import inputs
from .fig_main_cost import MM, NAT_RC
from .fig_pptx_pairs import OUT
from .gap import (CRISES, FUEL_CHANNEL, FIG3_SUPPLY_EVENTS, FIG3_PRIMARY_WASHOUT,
                  FIG3_BASELINE_MONTHS, figure3_regimes, pre_event_mask,
                  non_event_mask, country_gas_monthly, fossil_for_fuel)
from .audit_figure3 import _cpi, _real
from .coreset import CORE30_LIST

mpl.rcParams.update(NAT_RC)

FUELS7 = ["hydrogen", "ammonia", "methanol", "e-methane", "e-diesel",
          "e-kerosene", "ethanol"]
FUEL_VERSION = {"hydrogen": "ammonia", "ammonia": "ammonia",
                "methanol": "ammonia", "e-methane": "ammonia",
                "e-diesel": "ft", "e-kerosene": "ft", "ethanol": "ft"}
GREY_NAME = {"hydrogen": "grey hydrogen (from gas)",
             "ammonia": "grey ammonia (from gas)",
             "methanol": "grey methanol (from gas)",
             "e-methane": "natural gas (vs e-methane)",
             "e-diesel": "fossil diesel (vs e-diesel)",
             "e-kerosene": "jet fuel (vs e-kerosene)",
             "ethanol": "gasoline (vs ethanol)"}
GLOBAL_SERIES = {"e-diesel", "e-kerosene", "ethanol"}

SHORT_EVENT = {"Arab Spring / Libya": "Libya",
               "EU Iran oil embargo": "EU Iran embargo",
               "Qatar blockade": "Qatar blockade",
               "US Iran sanctions": "US Iran sanctions",
               "Abqaiq attack": "Abqaiq attack",
               "2021 Russian gas squeeze": "Russian gas squeeze",
               "Russia–Ukraine": "Russia–Ukraine",
               "Red Sea / Houthi": "Red Sea",
               "Israel–Iran war": "Israel–Iran war",
               "2026 Hormuz disruption": "Hormuz"}
SHORT_COUNTRY = {"United States of America": "United States",
                 "Dominican Republic": "Dominican Rep."}   # full names, as in Figs 3-5


def event_label(event: str) -> str:
    a, b = CRISES[event]
    y0, y1 = a[:4], b[:4]
    span = y0 if y0 == y1 else f"{y0}–{y1[2:]}"
    return f"{SHORT_EVENT.get(event, event)} ({span})"


# ---------------------------------------------------------------------------
# Supplementary world-pool tables (every modelled country, seven fuels)
# ---------------------------------------------------------------------------
def _regime_moves(series: pd.Series, version: str, cpi, cpi_ref):
    """Figure 3 rule on one monthly series ($/GJ): per regime the real
    (2025 US$) move of the regime median over its matched contiguous
    baseline, plus the pooled normal and disruption deviations (%) from
    the country's quiet-month median. Returns (rows, normal, disruption)."""
    s = series.dropna()
    s = s[s > 0]
    if len(s) < 24:
        return [], np.array([]), np.array([])
    real = _real(s, cpi, cpi_ref).dropna()
    quiet = real[non_event_mask(real.index, version,
                                FIG3_PRIMARY_WASHOUT).to_numpy()]
    ref = float(quiet.median())
    rows, normal, disruption = [], [], []
    for name, p0, p1, members in figure3_regimes(version, FIG3_PRIMARY_WASHOUT):
        pre = real[pre_event_mask(real.index, p0, version=version,
                                  washout_months=FIG3_PRIMARY_WASHOUT,
                                  contiguous=True)]
        ev = real[(real.index >= p0) & (real.index <= p1)]
        ok = len(pre) >= FIG3_BASELINE_MONTHS and len(ev) >= 3
        base = float(pre.median()) if ok else np.nan
        nom_ev = s[(s.index >= p0) & (s.index <= p1)]
        nom_pre = s.reindex(pre.index).dropna()
        rows.append({
            "regime": name, "start": str(p0), "end": str(p1),
            "member_events": " | ".join(members),
            "n_event": int(len(ev)), "n_pre": int(len(pre)),
            "baseline_first": str(pre.index.min()) if len(pre) else "",
            "baseline_last": str(pre.index.max()) if len(pre) else "",
            "event_move_2025usd_pct":
                (float(ev.median()) / base - 1) * 100 if ok and base > 0 else np.nan,
            "event_move_nominal_pct":
                (float(nom_ev.median()) / float(nom_pre.median()) - 1) * 100
                if ok and len(nom_pre) >= FIG3_BASELINE_MONTHS else np.nan,
        })
        if ok and base > 0 and ref > 0:
            normal.extend(((pre / base * ref) / ref - 1).mul(100).tolist())
            disruption.extend(((ev / base * ref) / ref - 1).mul(100).tolist())
    return rows, np.asarray(normal, float), np.asarray(disruption, float)


def world_tables() -> None:
    cpi, cpi_ref = _cpi()
    gasdf, gg = country_gas_monthly()
    table, pooled = [], []
    for f in FUELS7:
        version = FUEL_VERSION[f]
        qs, cs = [], []
        countries = ["(world benchmark)"] if f in GLOBAL_SERIES else list(gasdf.columns)
        for c in countries:
            gas = gasdf.iloc[:, 0] if f in GLOBAL_SERIES else gasdf[c]
            s = fossil_for_fuel(f, gas, gg, "" if f in GLOBAL_SERIES else c)
            rows, nq, nc = _regime_moves(s, version, cpi, cpi_ref)
            for r in rows:
                r.update({"fuel": f, "grey_rival": GREY_NAME[f],
                          "event_rule": FUEL_CHANNEL[version] + " events",
                          "country": c,
                          "price_source": ("world product benchmark"
                                           if f in GLOBAL_SERIES else
                                           "national gas price through the grey route")})
                table.append(r)
            qs.append(nq)
            cs.append(nc)
        q, c_ = np.concatenate(qs), np.concatenate(cs)
        pooled.append({
            "fuel": f, "event_rule": FUEL_CHANNEL[version] + " events",
            "n_series": len(countries), "normal_n": len(q), "disruption_n": len(c_),
            "normal_median_pct": float(np.median(q)),
            "disruption_median_pct": float(np.median(c_)),
            "normal_p98_pct": float(np.percentile(q, 98)),
            "disruption_p98_pct": float(np.percentile(c_, 98)),
            "normal_max_pct": float(q.max()), "disruption_max_pct": float(c_.max()),
        })
    tab = pd.DataFrame(table)[[
        "fuel", "grey_rival", "event_rule", "price_source", "country", "regime",
        "member_events", "start", "end", "n_event", "n_pre", "baseline_first",
        "baseline_last", "event_move_2025usd_pct", "event_move_nominal_pct"]]
    tab.round(2).to_csv(inputs.MAPS / "ed_crisis_by_country_regime.csv", index=False)
    pooled = pd.DataFrame(pooled)
    pooled.round(2).to_csv(inputs.MAPS / "ed_crisis_pooled_by_fuel.csv", index=False)
    print("world pool, matched baselines, deviation from own normal median "
          "(normal | disruption), %:")
    for r in pooled.itertuples():
        print(f"  {r.fuel:10s} median {r.normal_median_pct:+5.1f} | {r.disruption_median_pct:+5.1f}"
              f"   max {r.normal_max_pct:+5.0f} | {r.disruption_max_pct:+5.0f}  ({r.event_rule})")
    print(f"  wrote ed_crisis_by_country_regime.csv ({len(tab)} rows), ed_crisis_pooled_by_fuel.csv")


# ---------------------------------------------------------------------------
# the figure
# ---------------------------------------------------------------------------
def main():
    world_tables()

    me = pd.read_csv(inputs.MAPS / "figure3_member_event_audit.csv")
    ca = pd.read_csv(inputs.MAPS / "figure3_country_audit.csv")
    ca = ca[ca.version == "ammonia"].set_index("country")
    order = sorted(CORE30_LIST,
                   key=lambda c: (ca.trade_status.get(c, "") == "net exporter",
                                  -float(ca.supply_risk.get(c, -1))))
    nz = sum(ca.trade_status.get(c, "") != "net exporter" for c in order)

    mats = {}
    for version in ("ammonia", "ft"):
        events = list(FIG3_SUPPLY_EVENTS[version])
        e = me[me.version == version]
        M = e.pivot(index="event", columns="country", values="event_move_2025usd_pct")
        S = e.pivot(index="event", columns="country", values="event_observed_share")
        Pm = e.pivot(index="event", columns="country", values="pre_observed_share")
        M = M.reindex(index=events, columns=order)
        thin = ((S.reindex(index=events, columns=order).fillna(0) < 0.5) |
                (Pm.reindex(index=events, columns=order).fillna(0) < 0.5))
        mats[version] = (M, thin, [event_label(ev) for ev in events])
        print(f"  {version}: median economy per event (real, %): " +
              "; ".join(f"{event_label(ev)} {v:+.0f}" for ev, v in M.median(axis=1).items()))

    n_a, n_b = len(mats["ammonia"][0]), len(mats["ft"][0])
    fig = plt.figure(figsize=(183 * MM, 112 * MM))
    # 2026-10-05: a violin column beside each heatmap, one violin per row
    gs = fig.add_gridspec(2, 2, height_ratios=[n_a, n_b], width_ratios=[30, 9], hspace=0.45,
                          wspace=0.05, left=0.17, right=0.84, top=0.93, bottom=0.20)
    axes = [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[1, 0])]
    vaxes = [fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, 1])]
    cmap = mpl.colormaps["RdBu_r"].copy()
    cmap.set_bad("#E6E8EB")
    # one scale per panel: the 2021-22 gas squeeze more than tripled
    # European ammonia import prices, while no oil event moved diesel and
    # jet fuel by more than +100%; a shared scale would wash panel b out
    norms = {}
    for version in mats:
        vmax = float(np.ceil(np.nanmax(mats[version][0].values) / 50) * 50)
        norms[version] = mpl.colors.TwoSlopeNorm(vcenter=0.0, vmin=-100.0, vmax=vmax)
    DIS = "#D55E00"                              # the paper's disruption-price colour
    for ax, vax, version, letter, title in (
            (axes[0], vaxes[0], "ammonia", "a", "Ammonia: natural gas events"),
            (axes[1], vaxes[1], "ft", "b", "Diesel and jet fuel: oil events")):
        M, thin, labels = mats[version]
        norm = norms[version]
        ax.imshow(np.ma.masked_invalid(M.values), aspect="auto", cmap=cmap,
                  norm=norm, interpolation="nearest")
        for (r, c), tt in np.ndenumerate(thin.values):
            if tt and np.isfinite(M.values[r, c]):
                ax.add_patch(plt.Rectangle((c - 0.5, r - 0.5), 1, 1, fill=False,
                                           hatch="///", ec="white", lw=0))
        ax.set_yticks(range(len(M)))
        ax.set_yticklabels(labels, fontsize=7.5)
        ax.set_xticks(range(len(order)))
        ax.set_title(title, loc="left", fontsize=8, pad=4)
        ax.text(-0.24, 1.16, letter, transform=ax.transAxes, fontsize=9,
                fontweight="bold", va="bottom")
        ax.tick_params(direction="out", length=2)
        for sp in ax.spines.values():
            sp.set_linewidth(0.4)
        # the same row across the 30 economies, as a violin, median printed
        for r in range(len(M)):
            v = M.values[r][np.isfinite(M.values[r])]
            parts = vax.violinplot([v], positions=[r], vert=False, widths=0.82, showextrema=False,
                                   bw_method=0.35)
            for bd in parts["bodies"]:
                bd.set_facecolor(DIS)
                bd.set_edgecolor("none")
                bd.set_alpha(0.45)
            q1, q2, q3 = np.percentile(v, [25, 50, 75])
            vax.plot([q1, q3], [r, r], color=DIS, lw=2.0, solid_capstyle="butt", zorder=3)
            vax.scatter([q2], [r], s=8, color="white", edgecolor=DIS, lw=0.7, zorder=4)
            vax.text(1.03, r, f"{q2:+.0f}%", transform=vax.get_yaxis_transform(), ha="left",
                     va="center", fontsize=7, color="#3D4650", clip_on=False)
        vax.text(1.03, -0.75, "median", transform=vax.get_yaxis_transform(), ha="left", va="bottom",
                 fontsize=6.5, color="#5A6570", fontstyle="italic", clip_on=False)
        vax.set_ylim(len(M) - 0.5, -0.5)
        vax.set_yticks([])
        lo = min(-25.0, float(np.floor(np.nanmin(M.values) / 25) * 25))
        hi = float(np.ceil(np.nanmax(M.values) / 50) * 50)
        vax.set_xlim(lo, hi)
        vax.axvline(0, color="#5A6570", lw=0.5, zorder=1)
        vax.tick_params(axis="x", labelsize=6.5, length=2, width=0.4)
        vax.grid(axis="x", alpha=0.2, lw=0.4)
        vax.set_axisbelow(True)
        for s in ("top", "right", "left"):
            vax.spines[s].set_visible(False)
        vax.spines["bottom"].set_linewidth(0.4)
        vax.set_title("across economies", loc="left", fontsize=6.5, color="#5A6570", pad=4,
                      fontstyle="italic")
    vaxes[1].set_xlabel("move over baseline, %", fontsize=7)
    # Figure 3's divider: net exporters of the ammonia chain to the right
    axes[0].axvline(nz - 0.5, color="#3D4650", lw=0.8, ls=(0, (4, 2)))
    axes[0].tick_params(axis="x", labelbottom=False, length=0)
    axes[1].set_xticklabels([SHORT_COUNTRY.get(c, c) for c in order], rotation=65,
                            ha="right", fontsize=7.5)
    # 2026-10-05: the hatched cells get a key above panel a (and the
    # grey no-data cells, where any exist), not only a caption sentence
    from matplotlib.patches import Patch
    keys = [Patch(fc="#E39A86", hatch="///", ec="white", lw=0, label="fewer than half of months observed")]
    if any(np.isnan(mats[v][0].values).any() for v in mats):
        keys.append(Patch(fc="#E6E8EB", ec="none", label="no price data"))
    axes[0].legend(handles=keys, loc="lower right", bbox_to_anchor=(1.0, 1.01), ncol=len(keys),
                   fontsize=6.5, frameon=False, handlelength=1.4, handleheight=1.0, borderaxespad=0.0,
                   columnspacing=1.0)
    for ax, version in ((axes[0], "ammonia"), (axes[1], "ft")):
        pos = ax.get_position()
        cax = fig.add_axes([0.955, pos.y0, 0.012, pos.height])
        cb = fig.colorbar(mpl.cm.ScalarMappable(norm=norms[version], cmap=cmap), cax=cax)
        cb.set_label("move over\nbaseline, %", fontsize=7)
        cb.ax.tick_params(labelsize=7, width=0.4, length=2)
        cb.outline.set_linewidth(0.4)

    fig.savefig(OUT / "fig_main_crisis.pdf", bbox_inches="tight")
    fig.savefig(OUT / "fig_main_crisis.png", dpi=600, bbox_inches="tight")
    plt.close(fig)
    print(f"saved fig_main_crisis.(pdf|png)  {len(order)} core economies x "
          f"{n_a} gas + {n_b} oil events")


if __name__ == "__main__":
    main()
