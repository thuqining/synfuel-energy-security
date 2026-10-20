"""
fig_main_sites.py — MAIN-TEXT Fig 3: where to build, per core economy, in
two versions drawn by the same code with the same indicators:

  ammonia  gas family — the first tranche of the recommendation map; its
           rival, grey ammonia from natural gas, is priced off each
           country's regional gas marker
  ft       oil family — the Fischer-Tropsch liquids (e-diesel and e-jet),
           the largest bill; their rivals, diesel and jet fuel, are priced
           at each economy's OWN import-side price (customs CIF > official
           import parity > landed cost > export FOB for net exporters),
           weighted by its own diesel/jet demand, months without one filled
           from its regional market at its own median ratio (import_prices)

Rows are the 30 core economies, one currency ($ per MMBtu, LHV, real 2025
US$ -- fossil prices deflated with the BLS CPI-U):

  dark blue   BUILD at the country's cheapest 2.5-degree cell for that
              fuel (median over 20 weather years; CO2 at the cell's
              cheapest source), drawn over the 20 weather years, + $1/GJ
              to ship the fuel to demand
  grey        BUY in a contiguous clean baseline before each independent
              supply-disruption regime
  orange      BUY during those regimes; both monthly distributions are paired,
              month-weighted (gap.FIG3_WEIGHTING) and rebased to the country's
              quiet median

The primary specification removes a six-month post-event recovery period;
3- and 12-month versions are generated as sensitivity checks.  Events that
arrive before the recovery buffer expires form one compound regime.

Columns: import exposure, supply risk sqrt(exposure x route-matched supplier
HHI) and Bill (normal-month bill, US$bn/yr); the crisis cost (% GDP), the largest
and smallest over the fuel's own supply events (gap.FIG3_SUPPLY_EVENTS).
The share of economies whose synthetic build is at or below the fossil
disruption 99th percentile is quoted in the text, not marked on the rows.

From scripts/:  conda run -n synfuel python -u -m lcof.fig_main_sites
Output: cf_global_final/figures/pptx/fig_main_sites_{ammonia,ft}.(pdf|png)
        data/cost/core30_sites_{ammonia,ft}.csv
        and, for MAIN_FUEL, fig_main_sites.(pdf|png) + core30_sites.csv
"""
from __future__ import annotations

import sys

# The fossil side is ONE element per row: the normal-month box with the
# disruption months attached as an orange 1-99% range and median.
# --split restores the older three-box layout as fig_main_sites_split.*
MERGED = "--split" not in sys.argv     # merged buy side is the default
VIOLIN = "--violin" in sys.argv    # density outlines instead of boxes
# --city: the build box at the demand-centre cell (backup slide; writes
# fig_main_sites_city_* only and never the core30_sites tables)
CITY = "--city" in sys.argv
                                    # (comparison variant, 2026-09-16)

import os
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

mpl.use("Agg")

from . import inputs, params as P
from . import prices as PR
from .import_prices import NH3_GAS_ROUTE, nh3_regional_urea_ratio
from .fig_pptx_pairs import OUT, SUFFIX, YEARS
from .gap import (country_gas_monthly, fossil_for_fuel, CRISES,
                  FIG3_PRIMARY_WASHOUT, FIG3_WASHOUT_SENSITIVITY,
                  FIG3_CRISIS_COST_MAX_LAG, baseline_lag_months,
                  figure3_regimes, paired_event_price_distributions,
                  pre_event_mask)
from .import_prices import (country_buy_monthly, country_ammonia_monthly,
                            country_buy_monthly_filled,
                            load as load_import_prices)
from .coreset import CORE30_LIST, CORE30_TYPE
from .fig_main_cost import FUELS
from .fig_main_cities import CITIES, _nearest_cell

MMB = P.MMBTU_PER_GJ
# GDP for the crisis-cost column: the same GDP layer as the budget figure
_GDP = pd.read_csv(inputs.MAPS / "security_budget.csv", index_col=0).gdp_usd

# local-currency real prices for the crisis-cost columns: US$ times national
# currency per US$ (BIS monthly averages) over the national CPI (BIS; IMF for
# the eight economies BIS does not cover)
_FXDIR = inputs.PROJECT / "data" / "prices" / "fx"


def _load_local():
    fx = pd.read_csv(_FXDIR / "bis_xru_core30_monthly.csv")
    cpi = pd.concat([pd.read_csv(_FXDIR / "bis_cpi_core30_monthly.csv"),
                     pd.read_csv(_FXDIR / "imf_cpi_core8_monthly.csv")])
    f = {c: pd.Series(e.per_usd.to_numpy(float),
                      index=pd.PeriodIndex(e.month.astype(str).str[:7], freq="M")).groupby(level=0).mean()
         for c, e in fx.groupby("country")}
    k = {c: pd.Series(e.cpi.to_numpy(float),
                      index=pd.PeriodIndex(e.month.astype(str).str[:7], freq="M")).groupby(level=0).mean()
         for c, e in cpi.groupby("country")}
    return f, k


_FX, _CPI = _load_local()
# the two shocks every economy faced, reported side by side instead of each
# economy's own maximum (a maximum over many events is biased upward and
# picks different events for different economies)
KEY_EVENTS = ("Russia–Ukraine", "2026 Hormuz disruption")


def _event_move(s, a, b, version, washout_months):
    """signed price move an event made: window median over the median of
    its clean baseline (the 12 most recent months before it outside every
    event window), minus one"""
    ev = s.loc[a:b].dropna()
    pre = s[pre_event_mask(s.index, a, version=version,
                           washout_months=washout_months,
                           contiguous=True)].dropna()
    if len(ev) >= 3 and len(pre) >= 12 and np.median(pre) > 0:
        return float(np.median(ev) / np.median(pre) - 1.0)
    return np.nan


def _event_rise(s, a, b, version, washout_months):
    """price rise an event made: window median over the median of the 12
    months before it; only rises count"""
    ev = s.loc[a:b].dropna()
    pre = s[pre_event_mask(s.index, a, version=version,
                           washout_months=washout_months,
                           contiguous=True)].dropna()
    if len(ev) >= 3 and len(pre) >= 12 and np.median(pre) > 0:
        return max(float(np.median(ev) / np.median(pre) - 1.0), 0.0)
    return np.nan

SPEC = {"ammonia": dict(fuels=("ammonia",), label="ammonia",
                        bill="(ammonia)", syn="Green ammonia", fos="Fossil ammonia"),
        "ft": dict(fuels=("e-diesel", "e-kerosene"),
                   label="diesel and jet fuel", bill="(diesel + jet)",
                   syn="E-diesel/e-jet fuel", fos="Fossil diesel/jet fuel")}   # 2026-10-19: e- prefix as in Fig. 1
# the version written to fig_main_sites.* / core30_sites.csv; None keeps the
# paper's current constructed-ammonia render until the Fig 3 decision
# 2026-09-14 (after review): ammonia is the main
# Figure 3 -- its comparator now rests on observed import prices and the
# validated urea-implied price, and its break-even is nearest; diesel + jet
# goes to Extended Data
MAIN_FUEL = "ammonia"
_K = ("eta_syn", "mu_co2", "mu_n2", "mu_el", "syn_capex", "syn_life",
      "syn_opex")
assert all(P.FUELS["e-diesel"][k] == P.FUELS["e-kerosene"][k] for k in _K), \
    "e-diesel and e-kerosene no longer share one train"
# moving the fuel from the best site to the demand centre: $1/GJ for both
# versions. Maritime ammonia runs $0.7-1.5/GJ intercontinental and
# domestic distances sit at the low end; liquid fuels move in ordinary
# product tankers and pipelines, so the same allowance is not tight.
# Best-site option only — the demand-centre build consumes on site.
TRANSPORT_USD_GJ = 1.0
TYPE_MARK = {"large consumer": "s", "industrial importer": "o",
             "emerging importer": "^", "island state": "D",
             "resource-rich builder": "P"}
TYPE_COL = {"large consumer": "#000000",
            "industrial importer": "#D55E00",
            "emerging importer": "#E69F00",
            "island state": "#56B4E9",
            "resource-rich builder": "#009E73"}
MM = 1 / 25.4
mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "DejaVu Sans"],
    "font.size": 7, "axes.titlesize": 7, "axes.labelsize": 7,
    "xtick.labelsize": 7, "ytick.labelsize": 7,
    "axes.linewidth": 0.5, "xtick.major.width": 0.5,
    "ytick.major.width": 0.5,
})
GREY_P = "#7A7F85"     # 2026-10-05: normal-price line, a shade darker than the box grey
NORM_LW = 4.2          # 2026-10-06: the normal-price band (points), wide enough to read as a band
BEST, LOAD, GREY, CRIS, PURPLE = ("#0B4F9E", "#7FB2E0", "#8C8C8C",
                                  "#D55E00", "#CB181D")   # 2026-10-05: risk = import exposure red (as in Fig. 5), not the disruption orange
# 2026-10-05: the risk column as shaded cells, 0 white to 1 dark red
RISK_CELLS = True
SHORT = {"United States of America": "United States",
         "United Kingdom of Great Britain and Northern Ireland": "UK",
         "Dominican Republic": "Dominican Rep."}


def _box(ax, y, data, color, h=0.17, alpha=0.85, wmin=0.05):
    """wmin is a floor on the DRAWN width, in data units. An
    administratively priced economy has an interquartile range of a few
    tenths of a dollar; at the width of the whole panel that is thinner
    than the white median line, so the box disappears and the row reads
    as a lone dot. Drawn at the floor it still reads as a box, and the
    median line is dropped rather than bisecting it."""
    lo, q1, med, q3, hi = np.percentile(data, [1, 25, 50, 75, 99])
    ax.plot([lo, hi], [y, y], color=color, lw=0.8, zorder=2)
    w = q3 - q1
    ax.add_patch(plt.Rectangle((q1 if w >= wmin else med - wmin / 2,
                                y - h / 2), max(w, wmin), h,
                               fc=color, alpha=alpha, zorder=3,
                               ec="none" if w >= wmin else "#3D4650",
                               lw=0.0 if w >= wmin else 0.45))
    if w >= wmin:
        ax.plot([med, med], [y - h / 2, y + h / 2], color="white",
                lw=0.9, zorder=4)


def _kde(data, grid):
    """Gaussian kernel density with Silverman's bandwidth (numpy only)."""
    x = np.asarray(data, float)
    n = len(x)
    sd = x.std(ddof=1) if n > 1 else 0.0
    iqr = np.subtract(*np.percentile(x, [75, 25]))
    a = min(sd, iqr / 1.349) if iqr > 0 else sd
    bw = 0.9 * a * n ** (-0.2)
    if not np.isfinite(bw) or bw <= 0:
        return None
    z = (grid[:, None] - x[None, :]) / bw
    return np.exp(-0.5 * z * z).sum(axis=1) / (n * bw * np.sqrt(2 * np.pi))


def _violin(ax, y, data, color, h=0.30, alpha=0.85, wmin=0.05, half=None,
            zorder=3):
    """A density outline in place of a box: full (half=None), or the
    upper/lower half only so two distributions can share one row.
    The density is drawn over the 1-99% range; its widest point is h/2.
    An administratively priced series (range below wmin) falls back to
    the WMIN box so the row does not read as a hairline."""
    data = np.asarray(data, float)
    lo, med, hi = np.percentile(data, [1, 50, 99])
    if hi - lo < wmin:
        _box(ax, y, data, color, h=h * 0.55, alpha=alpha, wmin=wmin)
        return
    grid = np.linspace(lo, hi, 160)
    dens = _kde(data, grid)
    if dens is None:
        _box(ax, y, data, color, h=h * 0.55, alpha=alpha, wmin=wmin)
        return
    w = dens / dens.max() * (h / 2)
    if half == "upper":
        ax.fill_between(grid, y, y + w, fc=color, alpha=alpha, lw=0, zorder=zorder)
        ax.plot([med, med], [y, y + np.interp(med, grid, w)], color="white",
                lw=0.8, zorder=zorder + 1)
    elif half == "lower":
        ax.fill_between(grid, y - w, y, fc=color, alpha=alpha, lw=0, zorder=zorder)
        ax.plot([med, med], [y - np.interp(med, grid, w), y], color="white",
                lw=0.8, zorder=zorder + 1)
    else:
        ax.fill_between(grid, y - w, y + w, fc=color, alpha=alpha, lw=0, zorder=zorder)
        wm = np.interp(med, grid, w)
        ax.plot([med, med], [y - wm, y + wm], color="white", lw=0.8,
                zorder=zorder + 1)
    ax.plot([lo, hi], [y, y], color=color, lw=0.6, zorder=zorder - 1)


def _syn(fuel, frames, meta, cid, co2):
    """one fuel built at one cell, one value per weather year, $/MMBtu
    (LHV): the Stage-2 cascade on that cell's own hydrogen and
    electricity cost, with CO2 at the cell's cheapest source (ammonia
    takes none: mu_co2 = 0)."""
    spec = P.FUELS[fuel]
    wacc = float(meta.loc[cid, "wacc"])
    syn = P.syn_cost_per_gj(fuel, wacc)
    # 2026-10-09: location factor x C_S/F, as supply_demand.lcof_cells (LCOF_SYN_LOC=0 reverts)
    if os.environ.get("LCOF_SYN_LOC") != "0" and "syn_loc" in meta.columns:
        syn *= float(meta.loc[cid, "syn_loc"]) if np.isfinite(meta.loc[cid, "syn_loc"]) else 1.0
    c = float(co2.get(cid, P.C_CO2_DAC))
    out = []
    for y in YEARS:
        lcoh = float(frames[y].loc[cid, "lcoh_usd_gj"])
        lcoe = float(frames[y].loc[cid, "lcoe_usd_mwh"]) / 3.6
        out.append((lcoh / spec["eta_syn"] + spec["mu_co2"] * c
                    + spec["mu_n2"] * P.C_N2_DEFAULT + syn
                    + spec["mu_el"] * lcoe) * MMB)
    return np.array(out)


def _cost_all(fuel, frames, meta, cells, co2):
    """the same cascade for every cell at once, median over the 20
    weather years ($/GJ), for choosing each country's cheapest site"""
    spec = P.FUELS[fuel]
    w = meta.loc[cells, "wacc"]
    syn = w.map({r: P.syn_cost_per_gj(fuel, r) for r in w.unique()})
    if os.environ.get("LCOF_SYN_LOC") != "0" and "syn_loc" in meta.columns:
        syn = syn * meta.loc[cells, "syn_loc"].fillna(1.0)
    c = co2.reindex(cells).fillna(P.C_CO2_DAC)
    yrs = []
    for y in YEARS:
        f = frames[y].loc[cells]
        yrs.append(f.lcoh_usd_gj / spec["eta_syn"] + spec["mu_co2"] * c
                   + spec["mu_n2"] * P.C_N2_DEFAULT + syn
                   + spec["mu_el"] * f.lcoe_usd_mwh / 3.6)
    return pd.concat(yrs, axis=1).median(axis=1)


def _pct(a, q):
    """percentile of a possibly empty sample (NaN when empty)"""
    a = np.asarray(a, float)
    return float(np.percentile(a, q)) if a.size else float("nan")


def _crisis_mask(idx):
    m = pd.Series(False, index=idx)
    for a, b in CRISES.values():
        m.loc[a:b] = True
    return m


def _real_2025(series):
    """Deflate nominal fossil prices to 2025 USD (BLS CPI-U)."""
    d = pd.read_csv(inputs.PROJECT / "data" / "prices" / "fx" /
                    "us_cpi_monthly.csv")
    cpi = pd.Series(d.cpi_u.to_numpy(float),
                    index=pd.PeriodIndex(d.month, freq="M")).sort_index()
    # BLS documents 2025-10 as unavailable. Interpolate this one internal
    # gap for deflation while leaving the downloaded source table unchanged.
    cpi = cpi.interpolate(limit=1, limit_area="inside")
    ref = float(cpi[cpi.index.year == 2025].mean())
    return series * (ref / cpi.reindex(series.index))


def main(key, washout_months=FIG3_PRIMARY_WASHOUT, sensitivity=False,
         ax=None, columns=True, legend=True, save=True):
    """Standalone: draws and saves fig_main_sites_{key}. With ``ax`` the
    row panel is drawn into that axes instead (composite Figure 3):
    ``columns`` adds the Risk/Bill columns, ``legend`` the legend, ``save``
    writes the files. Returns the row order (bottom to top), NZ and XMAX."""
    sp = SPEC[key]
    fuels = sp["fuels"]
    qa = pd.read_csv(inputs.MAPS / "figure3_country_audit.csv")
    qa = qa[qa.version == key].set_index("country")
    gasdf, g = country_gas_monthly()
    frames = {y: pd.read_csv(inputs.MAPS / f"lcoh_global_{y}{SUFFIX}.csv")
              .set_index("cell_id")[["lcoh_usd_gj", "lcoe_usd_mwh"]]
              for y in YEARS}
    meta = inputs.load_meta(2025)
    land = meta[meta.cell_type == "land"]
    avail = frames[YEARS[0]].index
    co2df = pd.read_csv(inputs.MAPS / "co2_cost_by_cell.csv").set_index("cell_id")
    co2 = co2df.co2_cost
    cand = [i for i in land.index if i in avail]
    # best site by the MEDIAN FT cost over all 20 weather years (CO2
    # included), not any single year — a single-year pick is a
    # perfect-foresight choice
    med_all = _cost_all(fuels[0], frames, meta, cand, co2)
    dg = pd.read_csv(inputs.MAPS / "demand_fuel_grid.csv", index_col=0)
    dem_cell = dg[[f + "_gj" for f in FUELS]].sum(axis=1)
    by_c = dg[[f + "_gj" for f in fuels]].join(meta[["country"]])         .groupby("country").sum()
    # the diesel + jet bill, in billion MMBtu of final fuel per year: the
    # FT slice of the total the demand-structure figure prints.
    # P.MMBTU_PER_GJ is 1.0551, which is GJ per MMBtu despite the name,
    # so GJ -> MMBtu DIVIDES by it.
    bill_bn = by_c.sum(axis=1) / MMB / 1e9
    wts = by_c.div(by_c.sum(axis=1), axis=0)

    rows, rec, missing = [], [], []
    imp = load_import_prices()
    for c in CORE30_LIST:
        cc = [i for i in land[land.country == c].index if i in avail]
        if not cc:
            continue
        best_id = int(med_all.loc[cc].idxmin())
        here = dem_cell.reindex(cc).fillna(0.0)
        load_id = int(here.idxmax()) if here.max() > 0 else None
        city = CITIES.get(c, ("", 0, 0))[0]
        near = _nearest_cell(land, *CITIES[c][1:], c, avail) \
            if c in CITIES else None
        city = city if near == load_id else ""
        best = _syn(fuels[0], frames, meta, best_id, co2) + TRANSPORT_USD_GJ * MMB
        load = (_syn(fuels[0], frames, meta, load_id, co2)
                if load_id is not None else None)
        # the rival of each fuel in the set, weighted by this economy's
        # own demand for it: grey ammonia off the country's gas price, or
        # diesel and jet at the world marker
        wc = wts.loc[c]
        wj = float(wc.get("e-kerosene_gj", 0.0))
        if key == "ft":
            # the economy's OWN import-side price of diesel and jet
            # (customs CIF unit value, official import parity or landed
            # cost; own market for net exporters), weighted by its own
            # diesel/jet demand — never another economy's price
            # own months first; months without them from the economy's
            # import market, scaled by its own median ratio to that market
            own, _ = country_buy_monthly(c, 1.0 - wj, wj, imp)
            s, basis = country_buy_monthly_filled(c, 1.0 - wj, wj, imp)
            if s.empty:
                # no import price of its own: the row keeps its build box
                # and draws no fossil element
                missing.append(c)
            grey = s.dropna() * MMB
        else:
            if c not in gasdf.columns:
                raise KeyError(f"{c}: no gas price series")
            # the traded urea-implied ammonia price (World Bank urea net of
            # conversion, prices.py) is the proxy; the gas-constructed cost
            # overshot Europe's 2021-22 peak and undershot the US and Morocco
            con = PR.load(verified=True).ammonia_implied \
                .reindex(gasdf.index).dropna()
            s_nh3, why = country_ammonia_monthly(c, imp)
            own = s_nh3
            if len(s_nh3):
                # a net importer of ammonia: its own import price where it has
                # one; the urea-implied price elsewhere, at its own ratio
                ov = pd.concat([s_nh3, con], axis=1, keys=["own", "con"]).dropna()
                ratio = float((ov.own / ov.con).median()) if len(ov) >= 12 else 1.0
                filled = s_nh3.combine_first(con * ratio)
                grey = filled.dropna() * MMB
                basis = (f"{why} || own {len(s_nh3)} months, filled {len(filled) - len(s_nh3)} "
                         f"months from the urea-implied price x {ratio:.3f}")
            elif c in NH3_GAS_ROUTE:
                grey = fossil_for_fuel("ammonia", gasdf[c], g, c).dropna() * MMB
                basis = f"grey ammonia from the administered national gas price ({why})"
            else:
                k_reg, n_reg = nh3_regional_urea_ratio(c, imp)
                grey = con * k_reg * MMB
                basis = (f"urea-implied ammonia price x regional ratio {k_reg:.3f} "
                         f"({n_reg} observed importers; {why})")
        # Synthetic costs are real USD; put fossil observations on the same
        # 2025-USD basis before forming boxes, bills, or risk statistics.
        grey_nom = grey.copy()
        grey = _real_2025(grey)
        # Both boxes are matched monthly distributions: every event and its
        # preceding 12 months are rebased to the country's non-event median,
        # with equal weight per event regardless of duration.
        quiet, crisis, crisis_events = paired_event_price_distributions(
            grey, key, washout_months=washout_months)
        V = float(qa.supply_risk.get(c, np.nan))
        exposure = float(qa.import_exposure.get(c, np.nan)) * 100
        size = float(qa.estimated_quiet_bill_bn_usd.get(c, np.nan))
        # crisis cost, % of GDP: for every event window, the normal-period
        # bill times the signed price move the event made (window median over
        # the median of the 12 months before it), in the economy's own
        # currency at constant local prices (constant 2025 US$ where the
        # exchange-rate or CPI series ends before the window). The table shows
        # the largest and the smallest of the ten; a negative smallest move is
        # a saving (COVID lowered prices almost everywhere).
        gdp_bn = float(_GDP.get(c, np.nan)) / 1e9
        fx_c = _FX.get(c, pd.Series(dtype=float)).reindex(grey_nom.index)
        cpi_c = _CPI.get(c, pd.Series(dtype=float)).reindex(grey_nom.index)
        loc_real = (grey_nom * fx_c / cpi_c).dropna()
        moves, used = {}, {}
        # the same supply events as the orange box, so the columns and the
        # boxes describe one set of shocks
        event_to_regime = {}
        lags = {}
        for regime_name, p0, p1, members in figure3_regimes(
                key, washout_months):
            a, b = str(p0), str(p1)
            lag = baseline_lag_months(grey.index, a, key, washout_months)
            lags[regime_name] = lag
            if lag is None or lag > FIG3_CRISIS_COST_MAX_LAG:
                # boxes keep the regime; the crisis cost does not (the
                # baseline is too old to attribute the move to the event)
                continue
            r, u = _event_move(loc_real, a, b, key,
                               washout_months), "local real"
            if not np.isfinite(r):
                r, u = _event_move(grey, a, b, key,
                                   washout_months), "2025 US$"
            if np.isfinite(r):
                moves[regime_name], used[regime_name] = r, u
                for member in members:
                    event_to_regime[member] = regime_name

        def _cost(r):
            return 100.0 * size * r / gdp_bn if np.isfinite(size) and gdp_bn > 0 else np.nan

        if moves:
            ev_max = max(moves, key=moves.get)
            ev_min = min(moves, key=moves.get)
            cost_max, cost_min = _cost(moves[ev_max]), _cost(moves[ev_min])
        else:
            ev_max = ev_min = ""
            cost_max = cost_min = np.nan
        ru_regime = event_to_regime.get("Russia–Ukraine")
        hz_regime = event_to_regime.get("2026 Hormuz disruption")
        cost_ru = (_cost(max(moves[ru_regime], 0.0))
                   if ru_regime in moves else np.nan)
        cost_hz = (_cost(max(moves[hz_regime], 0.0))
                   if hz_regime in moves else np.nan)
        cbasis = [f"{k}: {100 * v:+.0f}% ({used[k]}; baseline lag {lags[k]} mo)"
                  for k, v in moves.items()]
        cbasis += [f"{k}: no crisis cost (baseline lag {v} mo > {FIG3_CRISIS_COST_MAX_LAG})"
                   for k, v in lags.items() if k not in moves and v is not None]
        lag_txt = " | ".join(f"{k}: {v if v is not None else 'none'}" for k, v in lags.items())
        obs_share = len(own) / len(grey) if len(grey) else np.nan
        rows.append((c, best, load, quiet, crisis, V, exposure, size,
                     obs_share, cost_max, cost_min))
        rec.append(dict(country=c, nearest_city=city, best_cell=best_id,
                        load_cell=load_id,
                        best_med_mmbtu=float(np.median(best)),
                        load_med_mmbtu=float(np.median(load))
                        if load is not None else np.nan,
                        quiet_med_mmbtu=_pct(quiet, 50),
                        crisis_med_mmbtu=_pct(crisis, 50),
                        crisis_p99_mmbtu=_pct(crisis, 99),
                        # 2026-10-14: every quantile drawn in the figure, for the source data
                        best_p01_mmbtu=_pct(best, 1), best_p25_mmbtu=_pct(best, 25),
                        best_p75_mmbtu=_pct(best, 75), best_p99_mmbtu=_pct(best, 99),
                        quiet_p01_mmbtu=_pct(quiet, 1), quiet_p25_mmbtu=_pct(quiet, 25),
                        quiet_p75_mmbtu=_pct(quiet, 75), quiet_p99_mmbtu=_pct(quiet, 99),
                        crisis_p01_mmbtu=_pct(crisis, 1), crisis_p25_mmbtu=_pct(crisis, 25),
                        crisis_p75_mmbtu=_pct(crisis, 75),
                        supply_risk=V,
                        V_strategic=float(qa.V_strategic.get(c, np.nan)),
                        import_exposure_pct=exposure,
                        jet_share=wj,
                        annual_demand_bn_mmbtu=float(bill_bn.get(c, np.nan)),
                        quiet_bill_bn_usd=size, observed_share=obs_share,
                        crisis_cost_max_gdp_pct=cost_max,
                        crisis_cost_max_event=ev_max,
                        crisis_cost_min_gdp_pct=cost_min,
                        crisis_cost_min_event=ev_min,
                        crisis_cost_ru_gdp_pct=cost_ru,
                        crisis_cost_hormuz_gdp_pct=cost_hz,
                        crisis_cost_basis=" | ".join(cbasis),
                        baseline_lag_months=lag_txt,
                        n_quiet=len(quiet), n_crisis=len(crisis),
                        disruption_events=" | ".join(crisis_events),
                        washout_months=washout_months,
                        normal_price_definition=
                            "month-weighted contiguous clean pre12 distribution; event and recovery months excluded; rebased to national quiet median",
                        disruption_price_definition=
                            "month-weighted supply-disruption regime months paired to contiguous pre12 and rebased",
                        n_weather_years=len(best), buy_basis=basis,
                        buy_first=str(grey.index.min()), buy_last=str(grey.index.max()),
                        best_co2_usd_t=float(co2.get(best_id, np.nan)),
                        best_co2_pathway=co2df.pathway.get(best_id,
                                                           "DAC (no source)"),
                        type=CORE30_TYPE[c]))
    rd = pd.DataFrame(rec)
    tag = f"_washout{washout_months}m" if sensitivity else ""
    if not CITY:
        rd.to_csv(inputs.MAPS / f"core30_sites_{key}{tag}.csv", index=False)
        if key == MAIN_FUEL and not sensitivity:
            rd.to_csv(inputs.MAPS / "core30_sites.csv", index=False)
    pen = (rd.load_med_mmbtu / rd.best_med_mmbtu).dropna()
    bq = rd.best_med_mmbtu / rd.quiet_med_mmbtu
    bc = rd.best_med_mmbtu / rd.crisis_med_mmbtu
    print(f"{sp['label']}: demand-centre vs best {(pen.median() - 1) * 100:.0f}"
          f"% median; build/buy quiet {bq.median():.1f}x median "
          f"(min {bq.min():.1f}); build/buy crisis {bc.median():.2f}x "
          f"median; build <= crisis median in {(bc <= 1).sum()} of "
          f"{len(rd)}; build <= crisis p99 in "
          f"{(rd.best_med_mmbtu <= rd.crisis_p99_mmbtu).sum()} of "
          f"{len(rd)}")
    # rows grouped, then sorted: net importers on top, ordered by supply
    # risk (highest at the top); the net exporters of the bill (imports
    # < 5%, same rule as the budget figure) sit below a divider,
    # ordered by their build cost
    def _is_exporter(r):
        # net exporter of the fuel chain: no net import of the product and
        # none of its feedstock (2026-09-16: no 5% threshold)
        return np.isfinite(r[6]) and r[6] <= 0.0
    zero = sorted([r for r in rows if _is_exporter(r)],
                  key=lambda r: (r[5] if np.isfinite(r[5]) else -1.0))
    expo = sorted([r for r in rows if not _is_exporter(r)],
                  key=lambda r: r[5])
    rows = zero + expo                       # drawn bottom -> top
    NZ = len(zero)

    n = len(rows)
    if ax is None:
        fig, ax = plt.subplots(figsize=(183 * MM, (34 + 5.4 * n) * MM))
    else:
        fig = ax.figure
    data_max = max(np.nanmax([_pct(r[1], 99), _pct(r[3], 99), _pct(r[4], 99)])
                   for r in rows)
    XMAX = np.ceil(data_max / 10) * 10
    XV = XMAX * 1.09                     # the fuel's own supply risk (the key column, first)
    XB = XMAX * 1.27                     # annual fuel bill, US$ billion per year
    # the bill shock (worst regime, % of GDP) stays in core30_sites_*.csv and
    # the text; the figure carries risk and bill only (2026-09-16)
    # exposure and the smallest crisis cost are in the data tables, not
    # drawn: exposure is inside the risk index and the smallest regime
    # effect is near zero everywhere
    WMIN = 0.010 * XMAX                  # floor on a drawn box width
    # Two facts the caption carries rather than the figure: economies
    # with no gas market of their own buy at the same imported marker
    # unadjusted, so nine fossil rows are identical, not merely alike;
    # and an administratively priced economy barely moves at all, so
    # its box is drawn at WMIN and is wider than the truth.
    for i, (c, best, load, quiet, crisis, V, exposure, size, obs_share, cost_max, cost_min) in \
            enumerate(rows):
        # three boxes per row: the demand-centre build is reported as a
        # number in the text (median +20% over the best site) rather
        # than drawn — four boxes per row were too crowded to read
        if MERGED and VIOLIN:
            # violin variant: the fossil row is one split violin, normal
            # months in the lower half and disruption months in the
            # upper half, so the two densities share a baseline; the
            # build is a full violin below it
            yf = i + 0.20
            if len(quiet):
                _violin(ax, yf, quiet, GREY, h=0.46, alpha=0.8, wmin=WMIN, half="lower")
            if len(crisis):
                _violin(ax, yf, crisis, CRIS, h=0.46, alpha=0.8, wmin=WMIN, half="upper")
            _violin(ax, i - 0.26, best, BEST, h=0.40, wmin=WMIN)
        elif MERGED:
            # Two directly comparable fossil boxes: matched pre-event months
            # and event months, both event-equal-weighted and rebased.
            # whatever months the economy's own series covers are drawn;
            # an economy without them keeps the build box alone
            # 2026-10-05: the three marks sit at three heights (disruption
            # on top, normal in the middle, build below) so the orange line no
            # longer runs through the grey box
            # 2026-10-06: normal and disruption prices overlaid on one row and
            # told apart by shape, not shade: normal = a wide translucent band with a
            # bar at its median; disruption = a thin capped line with a diamond at its
            # median, drawn on top. The build box sits on its own row below.
            yf = yc = i + 0.13
            yb = i - 0.20
            if len(quiet):
                lo, med, hi = np.percentile(quiet, [1, 50, 99])
                # 2026-10-06: a white median bar, not a dark one that read as the blue box
                ax.plot([lo, hi], [yf, yf], color=GREY_P, lw=NORM_LW, alpha=0.6, zorder=4,
                        solid_capstyle="butt")
                ax.plot([med, med], [yf - 0.10, yf + 0.10], color="white", lw=1.5, zorder=5,
                        solid_capstyle="butt")
            if len(crisis):
                lo, med, hi = np.percentile(crisis, [1, 50, 99])
                ax.plot([lo, hi], [yc, yc], color=CRIS, lw=1.0, zorder=6, solid_capstyle="butt")
                for x in (lo, hi):
                    ax.plot([x, x], [yc - 0.08, yc + 0.08], color=CRIS, lw=1.0, zorder=6,
                            solid_capstyle="butt")
                ax.plot([med], [yc], marker="D", ms=3.4, mfc=CRIS, mec="white", mew=0.5, zorder=7)
            build = load if (CITY and load is not None) else best
            _box(ax, yb, build, BEST, h=0.17, wmin=WMIN)
        else:
            _box(ax, i + 0.26, crisis, CRIS, h=0.2, alpha=0.75)
            _box(ax, i, quiet, GREY, h=0.2, alpha=0.55)
            _box(ax, i - 0.26, best, BEST, h=0.2)
        # the core-30 type is not marked on the rows: the typology is
        # described in Methods and the shapes needed a legend of
        # their own, which crowded the figure
        # 2026-10-06: the normal-month bill as a share of GDP, a fair comparison
        # across economies of very different size
        gdp_c = float(_GDP.get(c, np.nan))
        if columns and np.isfinite(size) and gdp_c > 0:
            # 2026-10-07: per mille of GDP; the whole national market
            s = f"{1000.0 * size * 1e9 / gdp_c:.1f}"
            ax.text(XB, i, s, fontsize=7, va="center", ha="center",
                    color="#3A4550")
        # every row carries its risk: a small importer's is small, an
        # exporter's is zero (2026-09-16)
        if columns and np.isfinite(V):
            lab = f"{V:.2f}" if V > 0 else "0"
            if RISK_CELLS:
                cw = 0.085 * XMAX
                fc = mpl.colormaps["Reds"](0.08 + 0.82 * min(max(V, 0.0), 1.0))
                ax.add_patch(mpl.patches.Rectangle((XV - cw / 2, i - 0.42), cw, 0.84, fc=fc,
                                                   ec="white", lw=0.6, zorder=3, clip_on=False))
                ax.text(XV, i, lab, fontsize=6.5, va="center", ha="center", zorder=4,
                        color="white" if V > 0.5 else "#3A4550")
            else:
                colv = PURPLE if V > 0.3 else "#777777"
                fw = "bold" if V > 0.3 else "normal"
                ax.text(XV, i, lab, fontsize=7, va="center", ha="center",
                        color=colv, fontweight=fw)
    # one line, level with the risk header: a second line reached left
    # far enough to cross the legend
    # two lines, bottom-aligned just above the top row: the fuel of the
    # bill on its own line keeps the header narrower than the gap to the
    # risk column
    # names on one baseline, units on a second, smaller line below them
    for x, name in (((XB, "Bill"),) if columns else ()):
        ax.text(x, n + 0.25, name, fontsize=7, ha="center", va="bottom",
                color="#3A4550")
    # the risk is the fuel's own: product imports plus the feedstock it is
    # made from, nothing else of the energy mix
    if columns:
        ax.text(XV, n + 0.25, "Import risk", fontsize=7, ha="center",   # 2026-10-13: named as in the text
                va="bottom", color=PURPLE, fontweight="bold")
        ax.text(XV, n - 0.35, "(0–1)", fontsize=7, ha="center", va="bottom", color="#3A4550")
        ax.text(XB, n - 0.35, "(‰ of GDP)", fontsize=7, ha="center",
                va="bottom", color="#3A4550")

    ax.set_yticks(range(n))
    if CITY:
        _city = {r["country"]: r["nearest_city"] for r in rec}
        ax.set_yticklabels([SHORT.get(r[0], r[0]) + (f" ({_city[r[0]]})" if _city.get(r[0]) else "")
                            for r in rows])
    else:
        ax.set_yticklabels([SHORT.get(r[0], r[0]) for r in rows])
    ax.set_xlim(0, XMAX * (1.46 if columns else 1.02))
    # the divider between the exposed importers and the zero-V group
    ax.plot([0, XMAX * (1.36 if columns else 1.02)], [NZ - 0.5, NZ - 0.5],
            color="#8A94A0", lw=0.7, ls=(0, (5, 3)), zorder=2)
    # both versions: net importers of the fuel chain (product plus the
    # feedstock it is made from) above the line; below it the economies
    # that supply the chain themselves (2026-09-16)
    # both group labels sit just right of the bill column, centred on
    # their band (2026-09-16)
    XG = XMAX * 1.35
    if columns:
      ax.text(XG, NZ + (n - NZ) / 2 - 0.5, "Net\nimporters", fontsize=7,
            color="#5A6570", ha="left", va="center", linespacing=1.15,
            zorder=6)
    # the exporter band is only two rows tall — a rotated label spills
    # across the divider, so the label sits horizontally in the blank
    # V column instead
      ax.text(XG, NZ / 2 - 0.5, "Net\nexporters", fontsize=7,
            color="#5A6570", ha="left", va="center",
            linespacing=1.15, zorder=6)
    ax.set_ylim(-0.9, n + (2.4 if legend else -0.4))
    # the separator stops at the top data row so it never crosses the
    # legend or the column headers
    if columns:
        ax.plot([XMAX * 1.03] * 2, [-0.9, n - 0.45], color="#DDDDDD", lw=0.5)
    # 2026-10-07: the trade's own unit on a second tick row under the
    # shared US$/MMBtu axis (LHV: ammonia 18.6 GJ/t; diesel 35.8 MJ/L)
    from . import params as PP
    if key == "ammonia":
        kn, stp, ulab = PP.FUELS["ammonia"]["native"]["$/t"] / PP.MMBTU_PER_GJ, 500.0, "US\\$ t$^{-1}$"
    else:
        # 2026-10-08: diesel and jet per barrel
        # one barrel conversion across the paper: jet fuel LHV, 35.1 MJ/L x 158.987 L (as Fig. 1)
        kn, stp, ulab = PP.FUELS["e-kerosene"]["native"]["$/L"] * 158.987 / PP.MMBTU_PER_GJ, 200.0, "US\\$ bbl$^{-1}$"
    # 2026-10-08: the trade's own unit is the main axis (ammonia is quoted per tonne;
    # referees check US$/t), US$/MMBtu on the second row links to Figs 1-2. The data stay in
    # US$/MMBtu; only the tick positions and labels change.
    tk = np.arange(0, XMAX * kn + 1e-9, stp)
    ax.set_xticks(tk / kn)
    ax.set_xticklabels([f"{v:,.0f}" if stp >= 1 else f"{v:g}" for v in tk])
    sec = ax.secondary_xaxis("bottom", functions=(lambda x: x, lambda y: y))
    sec.spines["bottom"].set_position(("outward", 19))
    sec.spines["bottom"].set_bounds(0, XMAX)
    sec.spines["bottom"].set_color("#8A94A0")
    sec.set_xticks([v for v in np.arange(0, XMAX + 1, 20) if v <= XMAX - 8])   # keep clear of the unit label
    sec.tick_params(direction="out", length=2.5, colors="#5A6570")
    for yo, lab in ((-9, ulab), (-28, "US\\$ MMBtu$^{-1}$")):
        ax.annotate(lab, xy=(XMAX, 0), xycoords=("data", "axes fraction"), xytext=(10, yo),
                    textcoords="offset points", ha="left", va="center", fontsize=7, color="#3A4550")
    sec.set_xlabel(sp["label"].capitalize() + " price")
    ax.tick_params(axis="y", pad=9)
    import matplotlib.patches as mp
    import matplotlib.lines as ml
    handler_map = {}
    if MERGED:
        # 2026-10-05: keys drawn exactly like the marks, fuel named
        from matplotlib.legend_handler import HandlerBase
        fuel = sp["label"]
        # 2026-10-05: the x axis already names the fuel, so the keys use
        # the paper's general terms
        # 2026-10-13: keys name the fuel compared (Green / Fossil ammonia)
        build_lab = sp["syn"]
        normal_lab = sp["fos"] + " (normal)"
        crisis_lab = sp["fos"] + " (disruption)"

        class _BoxKey(HandlerBase):
            def __init__(self, col, alpha):
                super().__init__()
                self.col, self.alpha = col, alpha

            def create_artists(self, legend, orig, x0, y0, w, h, fs, trans):
                yc = y0 + h / 2
                wl = ml.Line2D([x0, x0 + w], [yc, yc], color=self.col, lw=0.8, transform=trans)
                bx = mp.Rectangle((x0 + 0.28 * w, yc - 0.32 * h), 0.44 * w, 0.64 * h, fc=self.col,
                                  alpha=self.alpha, lw=0, transform=trans)
                md = ml.Line2D([x0 + 0.5 * w] * 2, [yc - 0.32 * h, yc + 0.32 * h], color="white",
                               lw=0.9, transform=trans)
                return [wl, bx, md]

        class _LineDiamond(HandlerBase):
            def __init__(self, col):
                super().__init__()
                self.col = col

            def create_artists(self, legend, orig, x0, y0, w, h, fs, trans):
                yc = y0 + h / 2
                ln = ml.Line2D([x0, x0 + w], [yc, yc], color=self.col, lw=1.0, transform=trans)
                dm = ml.Line2D([x0 + w / 2], [yc], marker="D", ms=3.2, mfc=self.col, mec="white",
                               mew=0.5, ls="none", transform=trans)
                return [ln, dm]

        class _BandBar(HandlerBase):
            def create_artists(self, legend, orig, x0, y0, w, h, fs, trans):
                yc = y0 + h / 2
                bd = ml.Line2D([x0, x0 + w], [yc, yc], color=GREY_P, lw=NORM_LW, alpha=0.6,
                               solid_capstyle="butt", transform=trans)
                br = ml.Line2D([x0 + w / 2] * 2, [yc - 0.30 * h, yc + 0.30 * h], color="white",
                               lw=1.5, solid_capstyle="butt", transform=trans)
                return [bd, br]

        class _CapDiamond(HandlerBase):
            def create_artists(self, legend, orig, x0, y0, w, h, fs, trans):
                yc = y0 + h / 2
                out = [ml.Line2D([x0, x0 + w], [yc, yc], color=CRIS, lw=1.0, solid_capstyle="butt",
                                 transform=trans)]
                for x in (x0, x0 + w):
                    out.append(ml.Line2D([x, x], [yc - 0.28 * h, yc + 0.28 * h], color=CRIS, lw=1.0,
                                         solid_capstyle="butt", transform=trans))
                out.append(ml.Line2D([x0 + w / 2], [yc], marker="D", ms=3.4, mfc=CRIS, mec="white",
                                     mew=0.5, ls="none", transform=trans))
                return out

        k_build, k_norm, k_cris = object(), object(), object()
        handles = [k_cris, k_norm, k_build]
        labels = [crisis_lab, normal_lab, build_lab]
        handler_map = {k_build: _BoxKey(BEST, 0.85), k_norm: _BandBar(), k_cris: _CapDiamond()}
    else:
        handles = [
            mp.Patch(color=BEST,
                     label=("Synthetic fuel at the demand centre" if CITY else "Synthetic fuel")),
            mp.Patch(color=GREY, alpha=0.55,
                     label="Fossil fuel (normal baseline)"),
            mp.Patch(color=CRIS, alpha=0.75,
                     label="Fossil fuel (disruption regime)")]
    if legend:
        ax.legend(handles=handles, labels=(labels if MERGED else None), handler_map=handler_map,
              loc="upper left", bbox_to_anchor=(XMAX * 0.02, n + 2.2),
              bbox_transform=ax.transData, fontsize=7,
              frameon=False, handlelength=2.0, ncol=3,
              columnspacing=1.6)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_bounds(-0.5, n - 0.5)   # only the rows
    ax.tick_params(direction="out", length=2.5)
    ax.set_axisbelow(True)
    ax.grid(axis="x", alpha=0.22, lw=0.4)

    info = dict(order=[r[0] for r in rows], NZ=NZ, XMAX=XMAX, n=n,
                handles=handles, label=sp["label"])
    if not save:
        return info
    base = "fig_main_sites" if MERGED else "fig_main_sites_split"
    if CITY:
        base = "fig_main_sites_city"
    if VIOLIN:
        base += "_violin"
    stems = [f"{base}_{key}{tag}"]
    if not sensitivity and key == MAIN_FUEL and not VIOLIN and not CITY:
        stems.append(base)
    for stem in stems:
        fig.savefig(OUT / f"{stem}.pdf", bbox_inches="tight")
        fig.savefig(OUT / f"{stem}.png", dpi=600, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {', '.join(stems)}.(pdf|png), {n} core economies; "
          f"core30_sites_{key}{tag}.csv")
    return info


if __name__ == "__main__":
    requested = None
    for arg in sys.argv[1:]:
        if arg.startswith("--washout="):
            requested = int(arg.split("=", 1)[1])
    if "--washout-sensitivity" in sys.argv:
        for washout in FIG3_WASHOUT_SENSITIVITY:
            for key in SPEC:
                main(key, washout, sensitivity=(washout != FIG3_PRIMARY_WASHOUT))
    else:
        washout = FIG3_PRIMARY_WASHOUT if requested is None else requested
        for key in SPEC:
            main(key, washout,
                 sensitivity=(washout != FIG3_PRIMARY_WASHOUT))
