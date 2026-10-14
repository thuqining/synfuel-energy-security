"""
gap.py — the single quantity behind the policy, crisis and vulnerability
readings:

        G(c, t) = LCOF(c) - P_fossil(c, t)          [$/GJ, LHV]

    tau*(t) = G / (EF_fossil - EF_syn)   the carbon price that closes it
    Pi(t)   = max(0, G)                  the escape cost of independence
    G < 0                                synthetic fuel wins outright

COUNTRY FOSSIL PRICE = monthly SHAPE from a market marker x country LEVEL from
real country data where it exists:
  Europe        TTF monthly shape, level scaled to the country's Eurostat
                industrial gas price (36 countries, real data)
  US / Canada / Mexico   Henry Hub
  Asian + other importers   Japan LNG cif (contract-weighted; conservative)
  gas producers  administered domestic price, weakly linked (see regional_prices)

Two gas conventions are carried side by side and never mixed:
  SPOT      what a new buyer faces at the margin  (TTF / HH / JKM-proxy)
  CONTRACT  what industry actually paid           (Eurostat, where available)

From scripts/:  conda run -n synfuel python -m lcof.gap
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import inputs, params as P, prices as PR
from .regional_prices import gas_regime, PRODUCER

WINDOW = ("2006", "2026")      # product benchmarks run through 2026-08
MMBTU = PR.MMBTU_PER_GJ

# ---- fossil comparator per fuel ---------------------------------------------
# grey hydrogen: gas / 0.72 efficiency + a non-fuel adder (capex, O&M, CO2 handling)
GREY_H2_NONFUEL = 4.0        # $/GJ H2
GREY_H2_ETA = 0.72
# COAL gasification is the incumbent hydrogen route in a few countries — using
# an SMR benchmark there would overstate the cost the green route must beat.
# China makes roughly 60 % of its hydrogen from coal; it is also the dominant
# route in South Africa and a large share in India.
# 2026-10-07: China ~85% of ammonia via coal gasification (IEA Ammonia Technology Roadmap
# 2021); India has no operating coal-based ammonia (Talcher, first plant, due FY2027-28)
COAL_H2_SHARE = {"China": 0.85, "South Africa": 0.55, "India": 0.0}
COAL_H2_ETA = 0.57           # GJ H2 per GJ coal
COAL_H2_NONFUEL = 6.0        # $/GJ H2 — gasifier is more capital-intensive
# large countries with substantial domestic gas: a blend of the international
# marker and a regulated domestic price (share = weight on the marker)
MIXED_GAS = {"China": (0.35, 9.0), "India": (0.45, 7.0), "Brazil": (0.50, 8.0),
             "Argentina": (0.25, 4.5), "Pakistan": (0.35, 5.0),
             "Thailand": (0.55, 8.0), "Vietnam": (0.40, 6.5),
             "Bangladesh": (0.30, 4.0), "Ukraine": (0.55, 9.0),
             "Romania": (0.55, 9.0), "Netherlands": (0.75, 9.0),
             "Norway": (0.60, 6.0), "United Kingdom": (0.80, 9.5)}
# Symmetry with the green route (2026-08-12): the H2-to-NH3 conversion is the
# same chemistry on both sides — 180 kg H2/t NH3 => 1/0.86 = 1.16, not the
# electricity-inclusive 1.43. Implied integrated gas intensity becomes
# 1.16/0.72 = 1.61 GJ gas/GJ NH3 = 30 GJ/t, inside the actual SMR-HB plant
# band (28-33 GJ/t); the old 1.43 implied 37 GJ/t and overstated the fossil
# side. Loop compression in an integrated plant is steam-driven from process
# heat, i.e. already inside the gas intensity; NONFUEL covers capex/O&M.
NH3_H2_INTENSITY = 1.16      # GJ H2 per GJ NH3
NH3_NONFUEL = 3.5            # $/GJ NH3
MEOH_GAS_INTENSITY = 1.55    # GJ gas per GJ methanol
MEOH_NONFUEL = 4.0           # $/GJ

# emission factors, t CO2 per GJ (IPCC combustion; SMR chains for H2/NH3)
EF = {"hydrogen": 0.080, "ammonia": 0.129, "methanol": 0.0741,
      "e-methane": 0.0561, "e-diesel": 0.0741, "e-kerosene": 0.0715,
      "ethanol": 0.0741, "marine": 0.0774}

# 2026-10-07: marine fuel oil, Singapore high-sulphur fuel oil 380 cst (the largest
# bunker hub; KNOC Petronet/Opinet daily MOPS-type assessments, data/prices/sg_mops),
# US$/bbl -> US$/t at 6.35 bbl/t (0.991 t/m3) -> US$/GJ at 40.2 GJ/t (IMO MEPC.308(73)
# lower calorific value of heavy fuel oil). Monthly means, nominal.
HSFO_BBL_PER_T, HSFO_GJ_PER_T = 6.35, 40.2


def hsfo_monthly() -> pd.Series:
    f = inputs.PROJECT / "data" / "prices" / "sg_mops" / "sg_mops_all_products_wide.csv"
    d = pd.read_csv(f, usecols=["date", "hsfo_380cst_3.5pctS"], parse_dates=["date"])
    s = d.set_index("date")["hsfo_380cst_3.5pctS"].dropna().resample("MS").mean()
    return s * HSFO_BBL_PER_T / HSFO_GJ_PER_T

# crisis windows defined by EVENT, never by price (no circular reasoning).
# Dates come from the event record, not from the price series; the 2026 Hormuz
# window is set from the reported military and shipping timeline:
#   2026-02-28  US/Israeli strikes on Iran begin; Iran declares the Strait of
#               Hormuz closed and cross-strait traffic largely halts
#   2026-04-07  two-week ceasefire agreed, conditional on reopening
#   2026-04-13  US blockade of Iranian ports ordered after talks fail
#   2026-04-17  Iran declares the strait open; traffic does not resume
#   2026-06-17  MOU reopens the strait toll-free, traffic still below normal
#   2026-07     attacks on commercial shipping resume
# February is excluded because the war began on its final day, so the monthly
# average is essentially pre-crisis. The window runs to the end of the data.
# 2026-09-14 (revised the same day): every window starts at the
# documented trigger (the trigger month if the event falls on or before the
# 15th, otherwise the next month) and ends at the event's documented end: the
# duration in data/cost/security_events.csv where the event is catalogued as a
# supply disruption, at least six months so each window carries enough monthly
# prices; six months where it is not catalogued; the ongoing Hormuz disruption
# runs to the end of the price series. The Qatar blockade kept LNG flowing
# (catalogue: mitigation case) and takes six months. Every candidate
# geopolitical supply event of 2006-2026 is kept whether or not prices moved;
# the 2007-08 price spike is dropped as a demand-led peak, not a dated supply
# event. Trigger dates:
#   2011-02-15 Libyan uprising          2012-01-23 EU embargo on Iranian oil
#   2017-06-05 Qatar blockade           2018-05-08 US exit from the Iran deal
#   2019-09-14 Abqaiq-Khurais attack    2020-03-11 WHO pandemic declaration
#   2022-02-24 Russian invasion         2023-11-19 Houthi seizure of Galaxy Leader
#   2025-06-13 Israel-Iran war          2026-02-28 strikes on Iran / Hormuz disruption
#   2021-09-21 IEA statement: Russia meeting only long-term contracts, exports
#              below 2019, "could do more" for European supply; Gazprom halted
#              spot sales and left its EU storage unfilled, Russian pipeline flows
#              to Europe -25% y/y in Q4 2021 (IEA, Gas Market Lessons from the
#              2022-2023 Energy Crisis). Gas only; it runs until Russia-Ukraine
#              opens, so it is shorter than the six-month minimum.
CRISES = {
    "Arab Spring / Libya": ("2011-02", "2011-09"),      # catalogue 8 months
    "EU Iran oil embargo": ("2012-02", "2012-07"),      # not catalogued: 6
    "Qatar blockade": ("2017-06", "2017-11"),           # flows held: 6
    "US Iran sanctions": ("2018-05", "2018-10"),        # not catalogued: 6
    "Abqaiq attack": ("2019-09", "2020-02"),            # catalogue 1 month -> 6
    "COVID collapse": ("2020-03", "2020-08"),           # not catalogued: 6
    "2021 Russian gas squeeze": ("2021-10", "2022-02"), # IEA 21 Sep 2021; ends as Russia-Ukraine opens
    "Russia–Ukraine": ("2022-03", "2023-08"),           # catalogue 18 months (gas curtailment)
    "Red Sea / Houthi": ("2023-12", "2025-02"),         # catalogue 15 months
    "Israel–Iran war": ("2025-06", "2025-11"),          # not catalogued: 6
    "2026 Hormuz disruption": ("2026-03", "2026-08"),   # ongoing: to data end
}

# Figure 3 disruption events: one physical rule for both fuels (2026-09-14).
# An event enters a fuel's comparison when it physically disrupted the supply
# of that fuel's fossil feedstock -- oil for diesel and jet, natural gas for
# ammonia. The channel is the commodity field of data/cost/security_events.csv
# where the event is catalogued (test_figure3 checks the match); the four
# uncatalogued events carry their documented channel. Demand shocks enter
# neither. The rule is fixed before prices are read, so no event is kept or
# dropped for how prices moved.
EVENT_CHANNELS = {
    "Arab Spring / Libya": ("oil",),        # catalogue: crude
    "EU Iran oil embargo": ("oil",),        # EU ban on Iranian crude imports, 2012
    "Qatar blockade": ("gas",),             # catalogue: gas
    "US Iran sanctions": ("oil",),          # US exit from the Iran deal; oil sanctions
    "Abqaiq attack": ("oil",),              # catalogue: crude
    "COVID collapse": (),                   # demand shock, not a supply disruption
    "2021 Russian gas squeeze": ("gas",),   # Gazprom withheld spot gas and storage (IEA)
    "Russia–Ukraine": ("oil", "gas"),       # catalogue: gas curtailment; crude and refined embargo
    "Red Sea / Houthi": ("oil", "gas"),     # catalogue: crude;refined;gas
    "Israel–Iran war": ("gas",),            # Israeli offshore gas fields shut, exports to Egypt and Jordan halted
    "2026 Hormuz disruption": ("oil", "gas"),  # catalogue: crude;refined;gas
}
FUEL_CHANNEL = {"ft": "oil", "ammonia": "gas"}
FIG3_SUPPLY_EVENTS = {
    key: tuple(e for e, ch in EVENT_CHANNELS.items() if channel in ch)
    for key, channel in FUEL_CHANNEL.items()
}
FIG3_PRIMARY_WASHOUT = 6
FIG3_WASHOUT_SENSITIVITY = (3, 6, 12)
FIG3_BASELINE_MONTHS = 12
FIG3_BASELINE_LOOKBACK = 60
# The crisis-cost column compares a regime's local real price with its
# baseline. A baseline that ended long before the regime carries the level
# and exchange-rate drift of the years between (Egypt's pound lost a quarter
# of its real value between 2021 and 2026), which would be booked to the
# event. A regime whose baseline ends more than this many months before it
# starts is drawn in the boxes but carries no crisis cost.
FIG3_CRISIS_COST_MAX_LAG = 24
# How the regimes are pooled into one normal and one disruption distribution
# per economy. "months": every rebased month of every regime (the price an
# importer faced across all disruption months; a 59-month regime weighs 59
# months). "regimes": twelve quantiles per regime, so every regime weighs
# the same -- kept as a sensitivity; with two ammonia regimes it let the
# Qatar blockade, which did not raise prices, halve the disruption median.
FIG3_WEIGHTING = "months"
# A demand shock is not drawn as an orange supply event, but neither its
# months nor its recovery tail can be called a normal fossil-price baseline.
FIG3_EXCLUSION_EVENTS = {
    key: tuple(events) + ("COVID collapse",)
    for key, events in FIG3_SUPPLY_EVENTS.items()
}
# catalogue rows behind each catalogued event, for the consistency check
EVENT_CATALOGUE_ROWS = {
    "Arab Spring / Libya": ("Libya civil war",),
    "Qatar blockade": ("Qatar blockade",),
    "Abqaiq attack": ("Abqaiq-Khurais attack",),
    "Russia–Ukraine": ("Russia-Europe gas curtailment", "Russian crude embargo-sanctions"),
    "Red Sea / Houthi": ("Red Sea Houthi attacks",),
    "2026 Hormuz disruption": ("Hormuz closure",),
}


def normal_mask(index) -> "pd.Series":
    """Figure 3 normal months: the 12 months before each window, window
    months excluded -- the baseline the crisis-cost column also uses"""
    idx = pd.PeriodIndex(index, freq="M")
    inside = pd.Series(False, index=idx)
    pre = pd.Series(False, index=idx)
    for a_, b_ in CRISES.values():
        p0, p1 = pd.Period(a_, "M"), pd.Period(b_, "M")
        inside |= (idx >= p0) & (idx <= p1)
        pre |= (idx >= p0 - 12) & (idx < p0)
    return pre & ~inside


def figure3_regimes(version: str, washout_months: int = FIG3_PRIMARY_WASHOUT):
    """Return pre-specified supply events grouped into independent regimes.

    If the next event starts before the preceding event's fixed recovery
    buffer has elapsed, the events and the intervening months form one
    compound regime.  The grouping depends only on dated events and the
    pre-specified buffer, never on the observed price response.
    """
    if version not in FIG3_SUPPLY_EVENTS:
        raise KeyError(f"unknown Figure 3 version: {version}")
    if washout_months < 0:
        raise ValueError("washout_months must be non-negative")
    out = []
    for event in FIG3_SUPPLY_EVENTS[version]:
        start, end = (pd.Period(x, "M") for x in CRISES[event])
        gap = start.ordinal - out[-1][2].ordinal - 1 if out else None
        if out and gap < washout_months:
            out[-1][0].append(event)
            out[-1][2] = max(out[-1][2], end)
        else:
            out.append([[event], start, end])
    return tuple((" + ".join(events), start, end, tuple(events))
                 for events, start, end in out)


def _figure3_excluded(index, version: str,
                      washout_months: int = FIG3_PRIMARY_WASHOUT):
    """Event and post-event recovery months excluded from normal prices."""
    if version not in FIG3_EXCLUSION_EVENTS:
        raise KeyError(f"unknown Figure 3 version: {version}")
    idx = pd.PeriodIndex(index, freq="M")
    excluded = np.zeros(len(idx), dtype=bool)
    for event in FIG3_EXCLUSION_EVENTS[version]:
        a_, b_ = CRISES[event]
        start, end = pd.Period(a_, "M"), pd.Period(b_, "M")
        excluded |= (idx >= start) & (idx <= end + washout_months)
    return excluded


def non_event_mask(index, version: str | None = None,
                   washout_months: int = FIG3_PRIMARY_WASHOUT) -> "pd.Series":
    """Figure 3 quiet months after removing events and their recovery tails.

    ``version`` makes the exclusion fuel-specific.  The deprecated ``None``
    form retains the old all-event/no-washout behaviour for calculations
    outside Figure 3.
    """
    idx = pd.PeriodIndex(index, freq="M")
    if version is None:
        inside = np.zeros(len(idx), dtype=bool)
        for a_, b_ in CRISES.values():
            inside |= ((idx >= pd.Period(a_, "M")) &
                       (idx <= pd.Period(b_, "M")))
        return pd.Series(~inside, index=idx)
    return pd.Series(~_figure3_excluded(idx, version, washout_months),
                     index=idx)


def event_median_move(series: pd.Series, start: str, end: str,
                      min_event: int = 3, min_pre: int = 9) -> float:
    """Paired event effect: event median / preceding-12-month median - 1."""
    s = series.dropna()
    p0 = pd.Period(start, "M")
    event = s[(s.index >= p0) & (s.index <= pd.Period(end, "M"))]
    pre = s[(s.index >= p0 - 12) & (s.index < p0)]
    if len(event) < min_event or len(pre) < min_pre:
        return float("nan")
    base = float(np.median(pre))
    if not np.isfinite(base) or base <= 0:
        return float("nan")
    return float(np.median(event) / base - 1.0)


def event_equivalent_prices(series: pd.Series, version: str) -> pd.Series:
    """Event effects expressed at one country's normal price level.

    Pooling raw event levels across 2006--2026 confounds shocks with the price
    regime in which each event happened (a Simpson/composition effect).  This
    function pairs each event with its own preceding 12 months, then applies
    that multiplier to the country's median non-event price.  One value per
    pre-specified supply event is returned; no negative move is clipped.
    """
    if version not in FIG3_SUPPLY_EVENTS:
        raise KeyError(f"unknown Figure 3 version: {version}")
    s = series.dropna()
    reference = float(s[non_event_mask(s.index).to_numpy()].median())
    out = {}
    for name in FIG3_SUPPLY_EVENTS[version]:
        move = event_median_move(s, *CRISES[name])
        if np.isfinite(move) and np.isfinite(reference):
            out[name] = reference * (1.0 + move)
    return pd.Series(out, dtype=float)


def pre_event_mask(index, start, n: int = FIG3_BASELINE_MONTHS,
                   lookback: int = FIG3_BASELINE_LOOKBACK,
                   version: str | None = None,
                   washout_months: int = FIG3_PRIMARY_WASHOUT,
                   contiguous: bool = False) -> "np.ndarray":
    """Select an event baseline without event or recovery-tail months.

    Figure 3 calls this with a fuel ``version`` and ``contiguous=True``: the
    most recent complete run of ``n`` quiet calendar months within the
    lookback is used.  A missing run makes the regime unmeasurable rather
    than silently stitching together different price regimes.  The legacy
    version-less form keeps the previous event-only exclusion for callers
    outside Figure 3.
    """
    idx = pd.PeriodIndex(index, freq="M")
    p0 = pd.Period(start, "M")
    if version is None:
        excluded = np.zeros(len(idx), dtype=bool)
        for a_, b_ in CRISES.values():
            excluded |= ((idx >= pd.Period(a_, "M")) &
                         (idx <= pd.Period(b_, "M")))
    else:
        excluded = _figure3_excluded(idx, version, washout_months)
    cand = np.where((idx < p0) & (idx >= p0 - lookback) & ~excluded)[0]
    if contiguous:
        groups = []
        for pos in cand:
            if not groups or idx[pos].ordinal != idx[groups[-1][-1]].ordinal + 1:
                groups.append([pos])
            else:
                groups[-1].append(pos)
        complete = [group for group in groups if len(group) >= n]
        keep = np.asarray(complete[-1][-n:], dtype=int) if complete else np.asarray([], dtype=int)
    else:
        keep = cand[np.argsort(idx[cand].asi8)[::-1][:n]] if len(cand) else cand
    out = np.zeros(len(idx), dtype=bool)
    out[keep] = True
    return out


def baseline_lag_months(index, start, version: str,
                        washout_months: int = FIG3_PRIMARY_WASHOUT):
    """Months between the end of a regime's contiguous clean baseline and the
    regime's first month (1 = adjacent); None when there is no baseline."""
    idx = pd.PeriodIndex(index, freq="M")
    m = pre_event_mask(idx, start, version=version,
                       washout_months=washout_months, contiguous=True)
    if not m.any():
        return None
    return int(pd.Period(start, "M").ordinal - idx[m].max().ordinal)


def paired_event_price_distributions(series: pd.Series, version: str,
                                     points_per_event: int = 12,
                                     washout_months: int = FIG3_PRIMARY_WASHOUT,
                                     weighting: str = FIG3_WEIGHTING):
    """Matched quiet/disruption-regime distributions for Figure 3.

    Events separated by less than the fixed washout are treated as one
    compound regime.  Every regime is divided by the median of its most
    recent contiguous 12-month quiet baseline and rebased to the country's
    quiet-month median.  Event windows, the post-event washout and the COVID
    demand shock are excluded from quiet prices.  With ``weighting="months"``
    (default, FIG3_WEIGHTING) every rebased month enters; with ``"regimes"``
    a fixed quantile grid gives every regime equal weight.  Returns
    ``(normal, disruption, regime_names)``.
    """
    if version not in FIG3_SUPPLY_EVENTS:
        raise KeyError(f"unknown Figure 3 version: {version}")
    s = series.dropna()
    reference = float(s[non_event_mask(s.index, version,
                                      washout_months).to_numpy()].median())
    q = (np.arange(points_per_event, dtype=float) + 0.5) / points_per_event
    normal, disruption, used = [], [], []
    for name, p0, p1, _events in figure3_regimes(version, washout_months):
        pre = s[pre_event_mask(s.index, p0, version=version,
                               washout_months=washout_months,
                               contiguous=True)]
        event = s[(s.index >= p0) & (s.index <= p1)]
        if len(pre) < FIG3_BASELINE_MONTHS or len(event) < 3:
            continue
        base = float(pre.median())
        if not np.isfinite(base) or base <= 0:
            continue
        if weighting == "months":
            normal.extend((pre / base * reference).tolist())
            disruption.extend((event / base * reference).tolist())
        elif weighting == "regimes":
            normal.extend((pre.quantile(q) / base * reference).tolist())
            disruption.extend((event.quantile(q) / base * reference).tolist())
        else:
            raise ValueError(f"unknown weighting {weighting!r}")
        used.append(name)
    # 2026-10-07: a rebased disruption month never exceeds the highest price
    # the economy has actually paid (2006-2026, real): rebasing carries an
    # event's proportional rise onto today's normal price, and from a low
    # pre-event base (2020-21) it can otherwise imply prices above any record
    cap = float(s.max())
    return (np.asarray(normal, dtype=float),
            np.minimum(np.asarray(disruption, dtype=float), cap), tuple(used))


def event_commodity_moves() -> pd.DataFrame:
    """How far each traded commodity moved inside each crisis window.

    TWO baselines, because they answer different questions and disagree:

      move_pct  against the mean of the 12 months IMMEDIATELY BEFORE the
                window. This is what the EVENT did, and it is the number to
                quote when saying "the closure moved diesel by X".
      dev_pct   against the MEDIAN of the whole 2006-2026 analysis window,
                the same baseline the deviation figures use. This mixes the
                event with any persistent regime shift — European gas reads
                high on this basis years after 2022 — so it answers "how
                unusual is this level", not "what did this event do".

    Quoted on the crisis slides; they live here rather than in prose so they
    cannot drift when the price panel is refreshed.
    """
    g = PR.load(verified=False).loc[WINDOW[0]:WINDOW[1]]
    rows = []
    for ev, (a, b) in CRISES.items():
        p0 = pd.Period(a, "M")
        m = (g.index >= p0) & (g.index <= pd.Period(b, "M"))
        pre = (g.index >= p0 - 12) & (g.index < p0)
        for c in g.columns:
            s = g[c].astype(float)
            if s.dropna().empty or not m.any():
                continue
            base = s[pre].mean()
            rows.append(dict(event=ev, series=c, window_mean=s[m].mean(),
                             window_max=s[m].max(), pre_mean=base,
                             ref_median=s.median(),
                             move_pct=(s[m].mean() / base - 1) * 100
                             if np.isfinite(base) and base > 0 else np.nan,
                             dev_pct=(s[m].mean() / s.median() - 1) * 100,
                             peak_pct=(s[m].max() / base - 1) * 100
                             if np.isfinite(base) and base > 0 else np.nan))
    return pd.DataFrame(rows)


def country_gas_monthly() -> pd.DataFrame:
    """Monthly delivered gas price per country, $/GJ (LHV), spot convention."""
    g = PR.load(verified=False).loc[WINDOW[0]:WINDOW[1]]
    meta = inputs.load_meta(2025)
    land = meta[meta.cell_type == "land"]
    countries = sorted(land.country.dropna().unique())

    # country level from Eurostat (real data), shape from TTF
    euro = pd.read_csv(inputs.PROJECT / "data" / "prices" / "country_gas_prices.csv")
    euro = euro[euro.basis == "pretax"]
    # Eurostat publishes a literal 0.0 where a country-period is unavailable
    # (Albania's only four observations). Taken at face value it gives that
    # country a zero gas price for all 240 months, and hence a free grey-H2
    # benchmark. Treat non-positive as missing.
    n0 = int((euro.usd_gj_lhv <= 0).sum())
    if n0:
        print(f"  dropping {n0} non-positive Eurostat observations "
              f"({', '.join(sorted(euro.loc[euro.usd_gj_lhv <= 0, 'geo_label'].unique()))})")
        euro = euro[euro.usd_gj_lhv > 0]
    ttf_hy = {}
    for t in euro.time.unique():
        y, s = t.split("-S")
        m = (1, 6) if s == "1" else (7, 12)
        sel = g["gas_eu"][(g.index.year == int(y)) & (g.index.month >= m[0]) &
                          (g.index.month <= m[1])]
        ttf_hy[t] = sel.mean()
    euro["ttf"] = euro.time.map(ttf_hy)
    lvl = (euro.groupby("geo_label")
           .apply(lambda d: (d.usd_gj_lhv / d.ttf).median(), include_groups=False))

    out = {}
    for c in countries:
        r = gas_regime(c)
        if r == "henry_hub":
            s = g["gas_us"]
        elif r == "ttf":
            k = float(lvl.get(c, np.nan))
            if not np.isfinite(k) or k <= 0:            # 1.35 = EU median ratio
                k = 1.35
            s = g["gas_eu"] * k
        elif r == "producer":
            base, pt = PRODUCER[c]
            s = base + pt * (g["lng_jp"] - g["lng_jp"].median())
        else:
            s = g["lng_jp"]
        if c in MIXED_GAS:          # blend the marker with a regulated domestic price
            w, dom = MIXED_GAS[c]
            s = w * s + (1 - w) * dom
        out[c] = s
    return pd.DataFrame(out), g


def grey_h2(country: str, gas: pd.Series, g: pd.DataFrame) -> pd.Series:
    """Incumbent hydrogen cost, blending the SMR and coal-gasification routes
    in the proportions actually used in that country."""
    smr = gas / GREY_H2_ETA + GREY_H2_NONFUEL
    share = COAL_H2_SHARE.get(country, 0.0)
    if share == 0:
        return smr
    coal = g["coal_au"] / COAL_H2_ETA + COAL_H2_NONFUEL
    return share * coal + (1 - share) * smr


def fossil_for_fuel(fuel: str, gas: pd.Series, g: pd.DataFrame,
                    country: str = "") -> pd.Series:
    """Monthly price of the incumbent this fuel must beat, $/GJ (LHV)."""
    if fuel == "e-methane":
        return gas
    if fuel == "hydrogen":
        return grey_h2(country, gas, g)
    if fuel == "ammonia":
        return NH3_H2_INTENSITY * grey_h2(country, gas, g) + NH3_NONFUEL
    if fuel == "methanol":
        return MEOH_GAS_INTENSITY * gas + MEOH_NONFUEL
    if fuel == "e-kerosene":
        return g["jet"]
    if fuel == "marine":         # shipping competes with marine fuel oil
        s = hsfo_monthly()
        if isinstance(g.index, pd.PeriodIndex):
            s.index = s.index.to_period("M")
        return s.reindex(g.index)
    return g["diesel"]           # e-diesel and ethanol compete with diesel


def country_lcof() -> pd.DataFrame:
    """Best-domestic-site LCOF per country per fuel, $/GJ (median weather year)."""
    from .fig_pptx_pairs import load_all, cascade_years
    meta, cells, lcoh, lcoe = load_all()
    land = meta.loc[cells]
    rows = {}
    for f in P.FUELS:
        med = np.median(cascade_years(meta, cells, lcoh, lcoe, f), axis=1)
        s = pd.Series(med, index=cells)
        rows[f] = s.groupby(land.country).min()
    df = pd.DataFrame(rows)
    n = land.country.value_counts()
    return df[n.reindex(df.index).fillna(0) >= 1]


def country_lcof_table(carbon_case: str = "industrial") -> pd.DataFrame:
    """Long table country x fuel x carbon case from the SAME 20-year regional
    sweep everything else uses, in the schema policy.breakeven_table expects.

    Supersedes lcof_countries_fuels_2025.csv, which came from the earlier
    single-year run with uniform equipment costs and no battery.
      industrial  regional point-source CO2 (meta.co2_cost)
      neutral     DAC CO2 everywhere (P.C_CO2_DAC)
    """
    from .fig_pptx_pairs import load_all
    meta, cells, lcoh, lcoe = load_all()
    land = meta.loc[cells]
    wacc = land["wacc"].to_numpy(float)
    syn_loc = land["syn_loc"].fillna(1.0).to_numpy(float)
    if carbon_case == "neutral":
        co2 = np.full(len(cells), P.C_CO2_DAC)
    else:
        co2 = land["co2_cost"].to_numpy(float)
        co2 = np.where(np.isfinite(co2), co2, P.C_CO2_DAC)

    rows = []
    for name in P.FUELS:
        f = P.FUELS[name]
        syn = np.array([(P.crf(w, f["syn_life"]) + f["syn_opex"]) * f["syn_capex"]
                        / (P.CF_SYN * 8760 * 3.6) for w in wacc]) * syn_loc
        v = (lcoh / f["eta_syn"]
             + (f["mu_co2"] * co2 + f["mu_n2"] * P.C_N2_DEFAULT + syn)[:, None]
             + f["mu_el"] * lcoe)
        best = pd.Series(np.median(v, axis=1), index=cells).groupby(
            land.country).min()
        for c, val in best.items():
            rows.append(dict(country=c, fuel=name, carbon_case=carbon_case,
                             lcof_usd_gj=float(val)))
    return pd.DataFrame(rows)


def build():
    gasdf, g = country_gas_monthly()
    lcof = country_lcof()
    common = [c for c in lcof.index if c in gasdf.columns]
    months = gasdf.index
    recs = []
    for c in common:
        for f in P.FUELS:
            fp = fossil_for_fuel(f, gasdf[c], g, c).reindex(months)
            gap = lcof.loc[c, f] - fp
            tau = gap / EF[f]
            recs.append(dict(country=c, fuel=f, lcof=lcof.loc[c, f],
                             fossil_med=fp.median(), fossil_min=fp.min(),
                             fossil_max=fp.max(),
                             gap_med=gap.median(), gap_min=gap.min(),
                             tau_med=tau.median(), tau_min=tau.min(),
                             win_months=int((gap < 0).sum()),
                             n_months=int(gap.notna().sum())))
    res = pd.DataFrame(recs)
    res["win_share"] = res.win_months / res.n_months * 100
    return res, gasdf, lcof, g


def main():
    res, gasdf, lcof, g = build()
    out = inputs.MAPS / "gap_country_fuel.csv"
    res.round(3).to_csv(out, index=False)
    print(f"wrote {out}  ({len(res)} country-fuel pairs, "
          f"{res.country.nunique()} countries)\n")

    print("months (of 240) in which the synthetic fuel would have been CHEAPER:")
    for f in P.FUELS:
        s = res[res.fuel == f]
        n = int((s.win_months > 0).sum())
        print(f"  {f:11s} countries with >=1 winning month: {n:3d}/{len(s)}"
              f" | best country {s.win_share.max():5.1f} % of months"
              f" ({s.loc[s.win_share.idxmax(), 'country'] if len(s) else '-'})")

    print("\ntau* (median over 2006-2026), lowest 8 countries, green hydrogen:")
    h = res[res.fuel == "hydrogen"].nsmallest(8, "tau_med")
    print(h[["country", "lcof", "fossil_med", "tau_med", "win_share"]]
          .round(1).to_string(index=False))

    print("\ncrisis windows — share of months the fuel would have won:")
    print(f"{'fuel':12s} " + " ".join(f"{k[:12]:>13s}" for k in CRISES) + "   normal")
    gasdf2 = gasdf
    for f in ("hydrogen", "ammonia", "e-methane"):
        line = f"{f:12s} "
        crisis_mask = pd.Series(False, index=gasdf2.index)
        for k, (a, b) in CRISES.items():
            m = (gasdf2.index >= pd.Period(a, "M")) & (gasdf2.index <= pd.Period(b, "M"))
            crisis_mask |= m
            wins = []
            for c in lcof.index:
                if c not in gasdf2.columns:
                    continue
                fp = fossil_for_fuel(f, gasdf2[c], g, c).reindex(gasdf2.index)
                wins.append(((lcof.loc[c, f] - fp)[m] < 0).mean() * 100)
            line += f"{np.nanmean(wins):12.1f}% "
        wins_n = []
        for c in lcof.index:
            if c not in gasdf2.columns:
                continue
            fp = fossil_for_fuel(f, gasdf2[c], g, c).reindex(gasdf2.index)
            wins_n.append(((lcof.loc[c, f] - fp)[~crisis_mask] < 0).mean() * 100)
        line += f"  {np.nanmean(wins_n):6.1f}%"
        print(line)


if __name__ == "__main__":
    main()
