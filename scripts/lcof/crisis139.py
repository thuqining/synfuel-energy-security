"""
crisis139.py — the disruption-event heatmap of the SI (fig_main_crisis) for all 139 economies (2026-10-22, user:
every SI figure covers the 139 economies). Same series (audit_figure3._series: the economy's own import price,
filled from the urea-implied price, the administered gas route or the regional urea ratio; diesel and jet from the
own import price filled from the import market) and the same rule: each dated event's median against its regime's
matched contiguous 12-month baseline, in 2025 US$. Economies are rows (core 30 first, in bold), the six natural gas
events (ammonia) and seven oil events (diesel and jet fuel) are columns; hatched cells rest mainly on filled months
(fewer than half of the event or baseline months observed), as in the 30-economy version.

From scripts/ (2025mid sandbox):  python ../work/caselow/run_mod.py ../work/caselow/2025mid 2025 lcof.crisis139 <out dir>
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

mpl.use("Agg")
from lcof import inputs
from lcof.fig_main_cost import MM, NAT_RC
from lcof.gap import CRISES, FIG3_SUPPLY_EVENTS, FIG3_PRIMARY_WASHOUT, FIG3_BASELINE_MONTHS, figure3_regimes, \
    pre_event_mask
from lcof.audit_figure3 import _series, _cpi, _real, _demand, W0, W1
from lcof.fig_main_sites import load_import_prices, country_gas_monthly
from lcof.fig_main_crisis import event_label
from lcof.fig4a_all import SHORT

mpl.rcParams.update(NAT_RC)
R = Path(__file__).resolve().parents[2]


def moves(countries):
    idx = pd.period_range(W0, W1, freq="M")
    cpi, cpi_2025 = _cpi()
    demand, prices = _demand(), load_import_prices()
    gasdf, gas = country_gas_monthly()
    rows = []
    for version in ("ammonia", "ft"):
        for c in countries:
            try:
                full, own, *_ = _series(c, version, demand, prices, gasdf, gas)
            except Exception as e:                       # noqa: BLE001 - an economy without a series stays empty
                print("   no series", version, c, str(e)[:60])
                continue
            full = full.reindex(idx).dropna()
            own_months = set(own.reindex(idx).dropna().index)
            for regime, p0, p1, members in figure3_regimes(version, FIG3_PRIMARY_WASHOUT):
                pre = full[pre_event_mask(full.index, str(p0), version=version,
                                          washout_months=FIG3_PRIMARY_WASHOUT, contiguous=True)]
                pre_real = _real(pre, cpi, cpi_2025).dropna()
                for member in members:
                    a_, b_ = CRISES[member]
                    evm = full[(full.index >= pd.Period(a_, "M")) & (full.index <= pd.Period(b_, "M"))]
                    evm_real = _real(evm, cpi, cpi_2025).dropna()
                    ok = len(evm_real) >= 3 and len(pre_real) >= FIG3_BASELINE_MONTHS
                    rows.append(dict(
                        version=version, country=c, event=member,
                        move=(evm_real.median() / pre_real.median() - 1) * 100 if ok else np.nan,
                        ev_obs=sum(m in own_months for m in evm.index) / len(evm) if len(evm) else np.nan,
                        pre_obs=sum(m in own_months for m in pre.index) / len(pre) if len(pre) else np.nan))
    return pd.DataFrame(rows)


def main(out):
    W = inputs.MAPS.parent.parent
    econ = list(pd.read_csv(W / "2030" / "data" / "security_budget.csv", index_col=0).index)
    core = set(pd.read_csv(W / "2030" / "data" / "fig5a_chain.csv", index_col=0).index)
    key = lambda c: SHORT.get(c, c).lower()
    order = sorted([c for c in econ if c in core], key=key) + sorted([c for c in econ if c not in core], key=key)
    m = moves(order)
    m.to_csv(Path(out) / "crisis139_moves.csv", index=False)
    # the 30-economy audit must be reproduced exactly
    au = pd.read_csv(inputs.MAPS / "figure3_member_event_audit.csv")
    chk = au.merge(m, on=["version", "country", "event"], how="inner")
    diff = (chk.event_move_2025usd_pct - chk.move).abs().max()
    print(f"check against figure3_member_event_audit: {len(chk)} cells, max |diff| {diff:.2e} pct points")
    assert len(chk) == len(au) and diff < 1e-6

    mats = {}
    for version in ("ammonia", "ft"):
        events = list(FIG3_SUPPLY_EVENTS[version])
        e = m[m.version == version]
        M = e.pivot(index="country", columns="event", values="move").reindex(index=order, columns=events)
        thin = (e.pivot(index="country", columns="event", values="ev_obs").reindex(index=order, columns=events)
                .fillna(0) < 0.5) | (e.pivot(index="country", columns="event", values="pre_obs")
                                     .reindex(index=order, columns=events).fillna(0) < 0.5)
        mats[version] = (M, thin, events)
    # two blocks of economies side by side (core 30 first, then alphabetical), each with the six gas events
    # (ammonia) and the seven oil events (diesel and jet fuel); one colour scale per fuel, keyed at the bottom
    # 2026-10-22 (user): keys and labels aligned with the panels: a two-line group title above each event
    # block, the colour bars directly under the left column's two panels and the hatching key under the right
    # column, each starting at its panel's left edge
    H = 189.0                                 # 2026-10-22: 3 mm shorter for the longer caption
    fig = plt.figure(figsize=(183 * MM, H * MM))
    half = (len(order) + 1) // 2
    blocks = [order[:half], order[half:]]
    top, bot = 1 - 42 / H, 15 / H
    cmap = mpl.colormaps["RdBu_r"].copy()
    cmap.set_bad("#E6E8EB")
    norms = {v: mpl.colors.TwoSlopeNorm(vcenter=0.0, vmin=-100.0,
                                         vmax=float(np.ceil(np.nanmax(mats[v][0].values) / 50) * 50)) for v in mats}
    # 2026-10-22: the column medians over the 30 core economies, the only ones with prices of their own; the 109
    # others share one proxy series for ammonia and three market series for diesel and jet fuel
    med = {v: np.nanmedian(mats[v][0].reindex(sorted(core)).values, axis=0) for v in mats}
    cw = 0.0215                                       # figure width per event column
    TITLE = {"ammonia": "Ammonia" + chr(10) + "natural gas events",
             "ft": "Diesel and jet fuel" + chr(10) + "oil events"}
    pos = {}
    for b, blk in enumerate(blocks):
        x = 0.115 + b * 0.5
        for version in ("ammonia", "ft"):
            M, thin, events = mats[version]
            Mb, Tb = M.reindex(blk), thin.reindex(blk)
            w = cw * len(events)
            pos[(b, version)] = (x, w)
            ax = fig.add_axes([x, bot + (top - bot) * (1 - len(blk) / half), w, (top - bot) * len(blk) / half])
            ax.imshow(np.ma.masked_invalid(Mb.values), aspect="auto", cmap=cmap, norm=norms[version],
                      interpolation="nearest")
            for (r, c), tt in np.ndenumerate(Tb.values):
                if tt and np.isfinite(Mb.values[r, c]):
                    ax.add_patch(plt.Rectangle((c - 0.5, r - 0.5), 1, 1, fill=False, hatch="////", ec="white",
                                               lw=0))
            ax.set_xticks(range(len(events)))
            ax.set_xticklabels([f"{event_label(ev)} {md:+.0f}%" for ev, md in zip(events, med[version])],
                               rotation=90, fontsize=5)
            ax.xaxis.tick_top()
            ax.set_yticks(range(len(blk)))
            if version == "ammonia":
                ax.set_yticklabels([SHORT.get(c, c) for c in blk], fontsize=5)
                for lab, c in zip(ax.get_yticklabels(), blk):
                    if c in core:
                        lab.set_fontweight("bold")
            else:
                ax.set_yticklabels([])
            ax.tick_params(length=1.2, width=0.3, pad=1)
            if b == 0:
                ax.axhline(len(core) - 0.5, color="#3D4650", lw=0.6)
            for sp in ax.spines.values():
                sp.set_linewidth(0.3)
            fig.text(x, 1 - 1.0 / H, TITLE[version], fontsize=6, fontweight="bold", ha="left", va="top",
                     linespacing=1.1)
            x += w + 0.012
    # colour bars under the left column's panels, same left edge and width
    for version, lab in (("ammonia", "Ammonia, change (%)"),
                         ("ft", "Diesel and jet fuel, change (%)")):
        x, w = pos[(0, version)]
        cax = fig.add_axes([x, 4.5 / H, w, 2.0 / H])
        cb = fig.colorbar(mpl.cm.ScalarMappable(norm=norms[version], cmap=cmap), cax=cax, orientation="horizontal")
        cb.set_ticks([-100, -50, 0, 150, 300] if version == "ammonia" else [-50, 0, 50, 100])
        cb.ax.tick_params(labelsize=5, width=0.3, length=1.5, pad=1)
        cb.outline.set_linewidth(0.3)
        cb.ax.set_title(lab, fontsize=5, pad=2, loc="left")
    from matplotlib.patches import Patch
    xr, _ = pos[(1, "ammonia")]
    keys = [Patch(fc="#E39A86", hatch="////", ec="white", lw=0,
                  label="fewer than half of months observed (proxy prices)")]
    if any(np.isnan(mats[v][0].values).any() for v in mats):      # 2026-10-22: only when a cell is empty
        keys.append(Patch(fc="#E6E8EB", ec="none", label="no price data"))
    fig.legend(handles=keys,
               loc="lower left", bbox_to_anchor=(xr - 0.004, 1.5 / H), fontsize=5, frameon=False, ncol=1,
               handlelength=1.4, handleheight=1.0, borderaxespad=0.0, labelspacing=0.4)
    from lcof.figcheck import report
    report(fig, "fig_main_crisis_139")
    fig.savefig(Path(out) / "fig_main_crisis.pdf", bbox_inches="tight")
    fig.savefig(Path(out) / "fig_main_crisis.png", dpi=300, bbox_inches="tight")
    print("core-30 medians:", {v: dict(zip(mats[v][2], np.round(med[v]))) for v in mats})


if __name__ == "__main__":
    main(sys.argv[1])
