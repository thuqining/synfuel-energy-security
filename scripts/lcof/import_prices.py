"""
import_prices.py — each economy's own IMPORT-SIDE price of diesel, jet fuel
and ammonia, monthly, $ per GJ (LHV), for the two versions of Fig 3.

Why: a world marker is not what an importer pays. The landed price adds
freight, insurance and war-risk premia, and the importer pays in its own
currency, so the same shock lands differently (Japan's jet CIF rose +111%
in the 2026 Hormuz window against +62% for the US Gulf Coast spot).

Basis, in order of preference, per economy and product:
  1. customs import unit value, CIF (value / quantity, all partners)
  2. an official import-parity or landed-cost price set by the regulator
  3. for net exporters of oil products, the price of their own market (US
     Gulf Coast spot for the United States; the Arab Gulf export benchmark
     for Saudi Arabia and Oman) — they have no meaningful import price, and
     the basis says so
No economy silently falls back to another economy's price: a country with
no series of its own returns an empty series and is reported as missing.
Ammonia import prices are used only for net importers of ammonia
(country_ammonia_monthly); the caller keeps the constructed grey-ammonia
cost for the rest.

Conversions: every value to US$ at the month's rate (ECB reference rates,
cross via USD; other currencies from the fx files saved next to the
downloads), every quantity to GJ at LHV: diesel 42.8 MJ/kg at 0.835 kg/L and
jet 43.0 MJ/kg at 0.804 kg/L (the factors of the US marker), ammonia 18.6
MJ/kg. Months flagged thin or with estimated quantities by the source are
dropped. Unit values outside 0.4-2.5x a reference are dropped and counted
(misclassified or mis-keyed customs lines): the same month's US Gulf Coast
spot for diesel and jet; for ammonia, which has no free world marker, the
median of all economies' ammonia unit values that month.

From scripts/:  conda run -n synfuel python -u -m lcof.import_prices
Output: data/prices/country_import_prices_monthly_gj.csv (long, with basis)
        data/prices/country_import_prices_all_sources_gj.csv (incl. dropped)
        data/prices/country_import_prices_coverage.csv
"""
from __future__ import annotations

import glob
import os

import numpy as np
import pandas as pd

from . import inputs

P = inputs.PROJECT / "data" / "prices"
W0, W1 = "2006-01", "2026-08"
MJ_PER_KG = {"diesel": 42.8, "jet": 43.0, "ammonia": 18.6}
KG_PER_L = {"diesel": 0.835, "jet": 0.804}
L_PER = {"l": 1.0, "litre": 1.0, "liter": 1.0, "kl": 1000.0, "m3": 1000.0,
         "bbl": 158.987294928, "gal": 3.785411784, "usgal": 3.785411784,
         "usgallon": 3.785411784, "gallon": 3.785411784}
KG_PER = {"kg": 1.0, "100kg": 100.0, "t": 1000.0, "tonne": 1000.0,
          "mt": 1000.0, "ton": 1000.0}
RATIO_BAND = (0.4, 2.5)
# every folder a download was written to
DOWNLOAD_DIRS = ("imports_*", "exports_*", "early_*", "fill_*", "deep_*")
PRODUCTS = ("diesel", "jet", "ammonia")
ALIAS = {"united states": "United States of America", "usa": "United States of America",
         "us": "United States of America", "uk": "United Kingdom",
         "great britain": "United Kingdom", "korea": "South Korea",
         "republic of korea": "South Korea", "korea, republic of": "South Korea",
         "rep. of korea": "South Korea", "viet nam": "Vietnam",
         "dominican rep.": "Dominican Republic"}
TRUE = {"true", "1", "yes", "thin", "y"}


def _norm_country(c: str) -> str:
    return ALIAS.get(str(c).strip().lower(), str(c).strip())


def gj_per_unit(unit: str, product: str) -> float:
    u = unit.strip().lower().replace(" ", "")
    if u in KG_PER:
        return KG_PER[u] * MJ_PER_KG[product] / 1000.0
    if u in L_PER and product in KG_PER_L:
        return L_PER[u] * KG_PER_L[product] * MJ_PER_KG[product] / 1000.0
    raise ValueError(f"unknown quantity unit {unit!r} for {product}")


def _ecb(cur: str) -> pd.Series | None:
    f = P / "fx" / f"ecb_EUR{cur}_monthly.csv"
    if not f.exists():
        return None
    d = pd.read_csv(f)
    return pd.Series(d.OBS_VALUE.to_numpy(float),
                     index=pd.PeriodIndex(d.TIME_PERIOD, freq="M")).sort_index()


def fx_per_usd(cur: str) -> pd.Series:
    """local currency per US$, monthly"""
    cur = cur.upper()
    usd = _ecb("USD")
    if cur == "EUR":
        return 1.0 / usd
    e = _ecb(cur)
    if e is not None:
        return e / usd
    # currencies the ECB does not quote: files saved next to the downloads
    # (CLP: Banco Central de Chile dólar observado, fx/clp_per_usd_monthly.csv)
    for f in [str(P / "fx" / "clp_per_usd_monthly.csv")] + \
            [g for pat in DOWNLOAD_DIRS for g in glob.glob(str(P / pat / "fx_monthly.csv"))]:
        if not os.path.exists(f):
            continue
        d = pd.read_csv(f)
        d = d[d.currency.str.upper() == cur]
        if len(d):
            return pd.Series(d.per_usd.to_numpy(float),
                             index=pd.PeriodIndex(d.month, freq="M")).groupby(level=0).mean()
    raise KeyError(f"no exchange rate for {cur}")


def _to_usd_gj(value, cur, unit, product, month):
    v = pd.Series(np.asarray(value, float), index=month)
    if cur.upper() != "USD":
        v = v / fx_per_usd(cur).reindex(month).to_numpy()
    return v / gj_per_unit(unit, product)


def _long(country, product, s, basis, source):
    s = s.dropna()
    return pd.DataFrame({"country": country, "month": s.index.astype(str),
                         "product": product, "usd_gj": s.to_numpy(),
                         "basis": basis, "source": source})


# ---- series already on disk ----------------------------------------------
def _usa():
    g = pd.read_csv(P / "fossil_monthly_gj_lhv.csv", index_col=0)
    g.index = pd.PeriodIndex(g.index, freq="M")
    b = "own market: US Gulf Coast spot (net exporter)"
    return [_long("United States of America", "diesel", g.diesel, b, "EIA USGC ULSD"),
            _long("United States of America", "jet", g.jet, b, "EIA USGC jet")]


def _japan():
    d = pd.read_csv(P / "japan_trade" / "jp_import_unit_values.csv")
    d = d[d.unit_value_jpy_per_kl.notna()
          & ~d.note.astype(str).str.contains("low volume|no data|no imports", case=False)]
    out = []
    for prod, lab in (("jet", "jet"), ("gas_oil", "diesel")):
        e = d[d["product"] == prod]
        m = pd.PeriodIndex(e.month, freq="M")
        out.append(_long("Japan", lab, _to_usd_gj(e.unit_value_jpy_per_kl, "JPY", "kL", lab, m),
                         "customs import unit value, CIF", "MOF Trade Statistics of Japan"))
    return out


def _south_africa():
    d = pd.read_csv(P / "za_bfp" / "za_diesel_bfp.csv")
    d = d[d["product"].isin(["diesel_0.05S", "diesel_0.3S", "diesel"])]
    d = d.assign(rank=d["product"].map({"diesel_0.05S": 0, "diesel_0.3S": 1, "diesel": 2}))
    d = d.sort_values(["month", "rank"]).groupby("month").first()
    w = pd.read_csv(P / "za_bfp" / "za_bfp_all_products.csv").set_index("month")
    m = pd.PeriodIndex(d.index, freq="M")
    rate = w.zar_usd.reindex(d.index).astype(float).to_numpy()
    v = pd.Series(d.bfp_c_per_L.to_numpy(float) / 100.0 / rate, index=m) / gj_per_unit("L", "diesel")
    return [_long("South Africa", "diesel", v, "official import parity (Basic Fuel Price)", "DMRE/DoE BFP")]


def _chile():
    d = pd.read_csv(P / "cl_cne" / "cl_parity_prices.csv", parse_dates=["date"])
    d = d[d["product"].str.lower().str.startswith("diesel")]
    out = []
    for unit_cur in ("USD", "CLP"):
        e = d[d.unit.str.upper().str.startswith(unit_cur)].set_index("date").parity_price.sort_index()
        e = e[~e.index.duplicated(keep="last")].resample("ME").mean().dropna()
        e.index = e.index.to_period("M")
        try:
            out.append(_to_usd_gj(e.to_numpy(), unit_cur, "m3", "diesel", e.index))
        except KeyError:
            continue
    s = out[0].combine_first(out[1]) if len(out) == 2 else out[0]
    return [_long("Chile", "diesel", s, "official import parity (CNE/ENAP)", "CNE, ENAP")]


def _india():
    d = pd.read_csv(P / "in_ppac" / "in_import_unit_values.csv")
    d = d[(d.flow == "export") & d.thin_quantity_flag.isna()]
    out = []
    for prod, lab in (("HSD", "diesel"), ("ATF", "jet")):
        e = d[d["product"] == prod]
        m = pd.PeriodIndex(e.month, freq="M")
        out.append(_long("India", lab, _to_usd_gj(e.unit_value_usd_per_t, "USD", "t", lab, m),
                         "export unit value, FOB (domestic prices set at trade parity)", "PPAC"))
    return out


def _kenya():
    d = pd.read_csv(P / "ke_epra" / "ke_diesel_monthly.csv")
    d = d[d.landed_cost_usd.notna()]
    if d.empty:
        return []
    u = d.landed_cost_usd_unit.str.upper().str.replace("USD/", "", regex=False).iloc[0]
    m = pd.PeriodIndex(d.month, freq="M")
    return [_long("Kenya", "diesel", _to_usd_gj(d.landed_cost_usd, "USD", u, "diesel", m),
                  "official landed cost (EPRA)", "EPRA price notices")]


def _downloaded():
    """every import_price_monthly.csv under data/prices/imports_*"""
    out = []
    files = []
    for pat in DOWNLOAD_DIRS:
        files += glob.glob(str(P / pat / "import_price_monthly.csv"))
    for f in sorted(set(files)):
        d = pd.read_csv(f)
        if "imports_europe" in f:
            d = d[d["product"] != "diesel"]      # rebuilt in _europe_diesel
        if "imports_east_asia" in f:
            # South Korea is a net exporter: its own export unit value only
            kr = d.country.isin(["South Korea", "Korea", "Republic of Korea"])
            d = d[~(kr & ~d.basis.str.lower().str.contains("export"))]
            # Philippines diesel: the lines labelled diesel (2710.19.71+.72),
            # not the variant adding 27101979002 (tariff label 'fuel oils')
            d = d[~((d.country == "Philippines") & d.basis.str.contains("incl_79002"))]
        if "imports_mena_africa" in f:
            # South Africa: one diesel grade (0.05% S, present over the whole
            # period), not the mean of the 0.05% and 0.005% S rows
            za = (d.country == "South Africa") & (d["product"] == "diesel")
            d = d[~za | d.codes_or_series.astype(str).str.contains("0.05% S", regex=False)]
            # Morocco jet 2014-01..2015-07 is declared at a flat 8,000 MAD/t
            # in 12 months (a customs declared value, not a market price);
            # those months are dropped, the months that move are kept
            flat = ((d.country == "Morocco") & (d["product"] == "jet")
                    & d.month.between("2014-01", "2015-07")
                    & (d.unit_value.sub(8000.0).abs() <= 1.0))
            d = d[~flat]
            # Gulf diesel comes from PPAC's published historical table
            # (_gulf_ppac); the web-scraped series disagreed with it in 24
            # of 66 overlapping months (-23% to +8%), so it is not used
            d = d[~(d.country.isin(["Saudi Arabia", "Oman"]) & (d["product"] == "diesel"))]
        if "imports_pk_lk_fj" in f:
            # Strict pre-tax comparator.  OGRA's rows labelled "import
            # parity" add customs tariff/duty to C&F or landed cost.  The
            # same source files also expose C&F / Karachi landed-cost rows,
            # which are retained because they precede customs duty, fuel
            # levies, GST and retail margins.
            pk_taxed = ((d.country == "Pakistan")
                        & d.basis.astype(str).str.lower().str.startswith("regulator import parity"))
            d = d[~pk_taxed]
        # a price held by the government is not an import price
        txt = d.select_dtypes(include=["object", "string"]).astype(str)
        d = d[~txt.apply(lambda col: col.str.contains("ADMINISTERED", regex=False)).any(axis=1)]
        # a value the source itself flags as likely estimated is not observed
        txt = d.select_dtypes(include=["object", "string"]).astype(str)
        d = d[~txt.apply(lambda col: col.str.contains("likely estimated", regex=False)).any(axis=1)]
        # a multi-month average spread over month rows is not a monthly price
        txt = d.select_dtypes(include=["object", "string"]).astype(str)
        d = d[~txt.apply(lambda col: col.str.contains("SPAN-AVERAGE", regex=False)).any(axis=1)]
        if "qty_estimation_type" in d.columns:
            kind = d.qty_estimation_type.astype(str).str.lower()
            d = d[~kind.str.contains("imputed|no quantity", regex=True)]
            # month-specific estimates are kept: clear their flag for the loop below
            d = d.assign(qty_estimated=d.qty_estimated.where(~kind.str.contains("month-specific"), False))
        for flag in ("thin", "qty_estimated"):
            if flag in d.columns:
                d = d[~d[flag].astype(str).str.strip().str.lower().isin(TRUE)]
        d = d[d.unit_value.notna() & d.unit_value_unit.notna()]
        for (c, prod, basis, unit), e in d.groupby(["country", "product", "basis", "unit_value_unit"]):
            prod = str(prod).lower()
            if prod not in MJ_PER_KG:
                continue
            cur, qty = str(unit).split("/", 1)
            vals = e.unit_value.astype(float).to_numpy()
            # a value quoted in cents of the currency, e.g. "ZAR c/L"
            bits = cur.split()
            if len(bits) == 2 and bits[1].lower() in ("c", "cent", "cents"):
                cur, vals = bits[0], vals / 100.0
            m = pd.PeriodIndex(e.month, freq="M")
            try:
                s = _to_usd_gj(vals, cur, qty, prod, m).groupby(level=0).mean()
            except (KeyError, ValueError) as err:
                print(f"  ! {f}: {c} {prod} {unit}: {err}")
                continue
            src = e.source_url.iloc[0] if "source_url" in e.columns else f
            out.append(_long(_norm_country(c), prod, s, str(basis), str(src)))
    return out


def _europe_diesel():
    """European diesel from the per-code detail, WITHOUT CN 27101942: from
    2025 that code is renewable diesel (at least 80% bio-based carbon),
    priced at about three times fossil gas oil and up to 28% of Dutch
    tonnage, and the comparator is fossil diesel. Biodiesel blends
    (271020xx) are already outside the sum. Months under 1,000 t dropped."""
    f = P / "imports_europe" / "import_codes_detail_monthly.csv"
    if not f.exists():
        return []
    d = pd.read_csv(f)
    d = d[(d.in_main_sum == "diesel") & (d.code.astype(str) != "27101942")]
    out = []
    for (c, cur), e in d.groupby(["country", "value_currency"]):
        agg = e.groupby("month")[["value", "quantity_t"]].sum()
        agg = agg[agg.quantity_t >= 1000]
        m = pd.PeriodIndex(agg.index, freq="M")
        s = _to_usd_gj((agg.value / agg.quantity_t).to_numpy(), cur, "t", "diesel", m)
        out.append(_long(_norm_country(c), "diesel", s,
                         "customs import unit value, CIF (fossil gas oil)",
                         "Eurostat Comext DS-045409 / HMRC / SSB"))
    return out


def _gulf_ppac():
    """Saudi Arabia and Oman, net exporters of oil products: the Arab Gulf
    10 ppm gasoil FOB benchmark their exports price off (PPAC history,
    downloaded manually with a member login; in_ppac/manual). Not an
    import price, and the basis says so. Month-to-date months dropped."""
    f = P / "in_ppac" / "manual" / "arab_gulf_gasoil_10ppm_monthly.csv"
    if not f.exists():
        return []
    d = pd.read_csv(f)
    d = d[~d.month_to_date.astype(bool)]
    m = pd.PeriodIndex(d.month, freq="M")
    s = _to_usd_gj(d.usd_per_bbl.to_numpy(), "USD", "bbl", "diesel", m)
    b = "export benchmark: Arab Gulf FOB spot (not an import price)"
    return [_long(c, "diesel", s, b, "PPAC Diesel (FOB) international price, 10 ppm Arab Gulf gasoil")
            for c in ("Saudi Arabia", "Oman")]


PRIORITY = ("customs", "import parity", "landed", "export", "own market", "benchmark")


def _rank(basis: str) -> int:
    """lower is better: the PRIORITY order, and CIF before FOB within it"""
    b = basis.lower().replace("-", " ").replace("_", " ")
    base = next((i for i, k in enumerate(PRIORITY) if k in b), len(PRIORITY))
    if "benchmark" in b:              # an export benchmark ranks below own export values
        base = PRIORITY.index("benchmark")
    if base == PRIORITY.index("customs") and "fob" in b and "cif" not in b:
        base = PRIORITY.index("landed")   # customs FOB: freight not included
    return 2 * base + (0 if "cif" in b else 1)


def build() -> pd.DataFrame:
    parts = []
    # South Africa and Kenya come from imports_mena_africa (complete, with
    # Kenya's mislabelled months corrected); the older loaders are retired
    for fn in (_downloaded, _europe_diesel, _gulf_ppac, _japan, _chile, _india, _usa):
        parts += fn()
    d = pd.concat(parts, ignore_index=True)
    d = d[(d.month >= W0) & (d.month <= W1)]
    # plausibility: diesel and jet against the same month's US Gulf Coast
    # spot; ammonia, with no free world marker, against the median of all
    # economies' ammonia unit values that month
    g = pd.read_csv(P / "fossil_monthly_gj_lhv.csv", index_col=0)
    cross = d[d["product"] == "ammonia"].groupby("month").usd_gj.median()

    def _ref(r):
        if r["product"] == "ammonia":
            return cross.get(r.month, np.nan)
        return g.at[r.month, r["product"]] if r.month in g.index else np.nan

    ratio = d.usd_gj / d.apply(_ref, axis=1)
    d = d.assign(ratio_to_reference=ratio,
                 dropped=~ratio.between(*RATIO_BAND) & ratio.notna())
    # one value per economy, product and month: the most direct basis wins
    family = (d.basis.str.replace(r"\(reporters [^)]*\)", "(reporters)", regex=True)
               .str.replace(r"HS8 [\d+]+", "HS8", regex=True))
    n_series = d.assign(family=family).groupby(["country", "product", "family"]).month.transform("count")
    comtrade = d.source.astype(str).str.contains("comtrade", case=False)
    d = (d.assign(rank=d.basis.map(_rank), longer=-n_series, ct=comtrade.astype(int))
          .sort_values(["country", "product", "month", "rank", "ct", "longer"], kind="mergesort")
          .drop(columns=["longer", "ct"]))
    keep = d[~d.dropped].groupby(["country", "product", "month"]).head(1)
    d.to_csv(P / "country_import_prices_all_sources_gj.csv", index=False)
    keep.drop(columns=["rank", "dropped"]).to_csv(P / "country_import_prices_monthly_gj.csv", index=False)
    return keep


def load() -> pd.DataFrame:
    f = P / "country_import_prices_monthly_gj.csv"
    return pd.read_csv(f) if f.exists() else build()


def country_buy_monthly(country: str, w_diesel: float, w_jet: float,
                        table: pd.DataFrame | None = None):
    """the economy's own diesel/jet import price, $/GJ, every month it has.
    Months with both products: the mean weighted by its own diesel/jet
    demand; months with one product: that product (diesel and jet move
    together, monthly correlation 0.994 at the US Gulf Coast). Empty if the
    economy has no series of its own."""
    t = load() if table is None else table
    t = t[(t.country == country) & t["product"].isin(["diesel", "jet"])]
    if t.empty:
        return pd.Series(dtype=float), "none"
    s = {p: pd.Series(e.usd_gj.to_numpy(), index=pd.PeriodIndex(e.month, freq="M"))
         for p, e in t.groupby("product")}
    bas = {p: "; ".join(sorted(e.basis.unique())) for p, e in t.groupby("product")}
    both = pd.concat([s.get("diesel", pd.Series(dtype=float)),
                      s.get("jet", pd.Series(dtype=float))], axis=1, keys=["d", "j"])
    wd = both.d.notna() * w_diesel
    wj = both.j.notna() * w_jet
    val = (both.d.fillna(0.0) * wd + both.j.fillna(0.0) * wj) / (wd + wj)
    # a month with only a product whose weight is zero stays as that product
    only_d = both.d.notna() & both.j.isna()
    only_j = both.j.notna() & both.d.isna()
    val[only_d] = both.d[only_d]
    val[only_j] = both.j[only_j]
    n_both, n_d, n_j = int((both.d.notna() & both.j.notna()).sum()), int(only_d.sum()), int(only_j.sum())
    parts = [f"{p}: {bas[p]}" for p in ("diesel", "jet") if p in bas]
    return (val.dropna().sort_index(),
            f"{' | '.join(parts)} [months: {n_both} both, {n_d} diesel only, {n_j} jet only]")


# ---- markets that fill months without an economy's own price ------------
# the market each economy's import prices are formed in: Singapore (MOPS)
# for Asia-Pacific and the Indian Ocean, the US Gulf Coast for the
# Americas, the Mediterranean (Italy's customs CIF, the longest complete
# Mediterranean series) for the Eastern Mediterranean and North Africa
FILL_MARKET = {
    "Madagascar": "singapore", "Sri Lanka": "singapore", "Indonesia": "singapore",
    "Vietnam": "singapore", "Philippines": "singapore", "Pakistan": "singapore",
    "India": "singapore", "China": "singapore", "Australia": "singapore",
    "South Korea": "singapore", "Japan": "singapore", "Kenya": "singapore",
    "Saudi Arabia": "singapore", "Oman": "singapore",
    "Egypt": "mediterranean", "Israel": "mediterranean", "Morocco": "mediterranean",
    "South Africa": "singapore",
    "Dominican Republic": "usgc", "Chile": "usgc", "Brazil": "usgc",
    "United States of America": "usgc",
}
# 2026-10-22: the 109 economies outside the core sample by the same rule (they have no month of their own, so the
# market sets their whole series): Asia-Pacific, the Gulf and East and Southern Africa buy in Singapore, the
# Americas on the US Gulf Coast; Europe, the CIS, North, West and Central Africa and the Levant stay Mediterranean
FILL_MARKET.update({c: "singapore" for c in (
    "Afghanistan", "Bangladesh", "Bhutan", "Cambodia", "Fiji", "Laos", "Malaysia", "Myanmar", "Nepal", "New Zealand",
    "Papua New Guinea", "Taiwan", "Thailand", "Iran", "Iraq", "United Arab Emirates", "Yemen", "Botswana", "Eritrea",
    "Ethiopia", "Malawi", "Mozambique", "Namibia", "Rwanda", "South Sudan", "Sudan", "Uganda",
    "United Republic of Tanzania", "Zambia", "Zimbabwe")})
FILL_MARKET.update({c: "usgc" for c in (
    "Argentina", "Belize", "Bolivia", "Canada", "Colombia", "Costa Rica", "Cuba", "Ecuador", "Guatemala", "Guyana",
    "Haiti", "Honduras", "Mexico", "Nicaragua", "Panama", "Paraguay", "Peru", "Suriname", "Uruguay", "Venezuela")})
FILL_DEFAULT = "mediterranean"        # the European economies
MIN_OVERLAP = 12                       # months needed to calibrate the ratio


def market_monthly(market: str) -> dict:
    """{'diesel': Series, 'jet': Series}, $/GJ, monthly"""
    if market == "usgc":
        g = pd.read_csv(P / "fossil_monthly_gj_lhv.csv", index_col=0)
        g.index = pd.PeriodIndex(g.index, freq="M")
        return {"diesel": g.diesel.dropna(), "jet": g.jet.dropna()}
    if market == "singapore":
        d = pd.read_csv(P / "sg_mops" / "sg_mops_products.csv", parse_dates=["date"])
        jet = d[d["product"] == "jet"].set_index("date").price_usd_per_bbl
        dsl = pd.concat([
            d[(d["product"] == "diesel") & d.spec.str.contains("0.5%", regex=False)]
            .set_index("date").price_usd_per_bbl.loc[:"2006-09-30"],
            d[(d["product"] == "diesel") & d.spec.str.contains("0.05%", regex=False)]
            .set_index("date").price_usd_per_bbl.loc["2006-10-01":]])
        out = {}
        for prod, s in (("diesel", dsl), ("jet", jet)):
            s = s.sort_index()
            s = s[~s.index.duplicated(keep="last")].resample("ME").mean().dropna()
            s.index = s.index.to_period("M")
            out[prod] = s / gj_per_unit("bbl", prod)
        return out
    if market == "mediterranean":
        tab = load()
        it = tab[tab.country == "Italy"]
        return {prod: pd.Series(e.usd_gj.to_numpy(), index=pd.PeriodIndex(e.month, freq="M"))
                for prod, e in it.groupby("product") if prod in ("diesel", "jet")}
    raise KeyError(market)


def _weighted(d: pd.Series, j: pd.Series, w_diesel: float, w_jet: float) -> pd.Series:
    both = pd.concat([d, j], axis=1, keys=["d", "j"])
    wd = both.d.notna() * w_diesel
    wj = both.j.notna() * w_jet
    val = (both.d.fillna(0.0) * wd + both.j.fillna(0.0) * wj) / (wd + wj)
    only_d = both.d.notna() & both.j.isna()
    only_j = both.j.notna() & both.d.isna()
    val[only_d] = both.d[only_d]
    val[only_j] = both.j[only_j]
    return val.dropna().sort_index()


def country_buy_monthly_filled(country: str, w_diesel: float, w_jet: float,
                               table: pd.DataFrame | None = None):
    """own months first; every other month of W0..W1 from the economy's
    import market, scaled by its own median ratio to that market"""
    own, basis = country_buy_monthly(country, w_diesel, w_jet, table)
    market = FILL_MARKET.get(country, FILL_DEFAULT)
    mk = market_monthly(market)
    bench = _weighted(mk.get("diesel", pd.Series(dtype=float)),
                      mk.get("jet", pd.Series(dtype=float)), w_diesel, w_jet)
    idx = pd.period_range(W0, W1, freq="M")
    bench = bench.reindex(idx)
    ov = pd.concat([own, bench], axis=1, keys=["own", "b"]).dropna()
    ratio = float((ov.own / ov.b).median()) if len(ov) >= MIN_OVERLAP else 1.0
    filled = own.reindex(idx).combine_first(bench * ratio).dropna()
    n_own = int(own.reindex(idx).notna().sum())
    n_fill = len(filled) - n_own
    return filled, (f"{basis} || own {n_own} months, filled {n_fill} months from "
                    f"{market} x {ratio:.3f} (median own/market over {len(ov)} months)")


def ammonia_status() -> pd.DataFrame:
    """net importer / net exporter / self-sufficient, from the 2015-2025
    ammonia trade totals (imports_ammonia/ammonia_trade_balance.csv)"""
    f = P / "imports_ammonia" / "ammonia_trade_balance.csv"
    if not f.exists():
        return pd.DataFrame(columns=["imports_t", "exports_t", "status"])
    d = pd.read_csv(f)
    # annual Comtrade totals for core economies the monthly download does
    # not cover in 2015-2025 (Madagascar, Sri Lanka); used only where the
    # monthly table has no row for the economy in that window
    sup = P / "imports_ammonia" / "ammonia_trade_balance_annual_supplement.csv"
    if sup.exists():
        s = pd.read_csv(sup)
        have = set(d[(d.year >= 2015) & (d.year <= 2025)].country.map(_norm_country))
        s = s[~s.country.map(_norm_country).isin(have)]
        d = pd.concat([d, s[["country", "year", "imports_t", "exports_t"]]], ignore_index=True)
    d = d[(d.year >= 2015) & (d.year <= 2025)]
    g = d.assign(country=d.country.map(_norm_country)).groupby("country")
    t = g[["imports_t", "exports_t"]].sum()
    t["n_years"] = g.year.nunique()        # years reported, for annual means
    big = t[["imports_t", "exports_t"]].max(axis=1)
    net = t.imports_t - t.exports_t
    t["status"] = np.where(net.abs() < 0.10 * big, "self-sufficient",
                           np.where(net > 0, "net importer", "net exporter"))
    return t


MIN_NH3_MONTHS = 12


def country_ammonia_monthly(country: str, table: pd.DataFrame | None = None):
    """the economy's own ammonia import unit value, $/GJ, when it is a net
    importer of ammonia with at least MIN_NH3_MONTHS usable months; else an
    empty series and the reason (the caller keeps the constructed cost)"""
    st = ammonia_status()
    if country not in st.index:
        return pd.Series(dtype=float), "no ammonia trade data"
    status = st.at[country, "status"]
    if status != "net importer":
        return pd.Series(dtype=float), f"{status} of ammonia"
    t = load() if table is None else table
    e = t[(t.country == country) & (t["product"] == "ammonia")]
    if len(e) < MIN_NH3_MONTHS:
        return pd.Series(dtype=float), f"net importer, only {len(e)} months of import prices"
    s = pd.Series(e.usd_gj.to_numpy(), index=pd.PeriodIndex(e.month, freq="M"))
    return s, "ammonia import unit value, " + "; ".join(sorted(e.basis.unique()))


def coverage(countries) -> pd.DataFrame:
    from .gap import CRISES
    t = load()
    allsrc = pd.read_csv(P / "country_import_prices_all_sources_gj.csv")
    idx = pd.period_range(W0, W1, freq="M")
    crisis = pd.Series(False, index=idx)
    for a, b in CRISES.values():
        crisis.loc[a:b] = True
    rows = []
    for c in countries:
        for p in PRODUCTS:
            e = t[(t.country == c) & (t["product"] == p)]
            m = pd.PeriodIndex(e.month, freq="M")
            a = allsrc[(allsrc.country == c) & (allsrc["product"] == p)]
            rows.append(dict(country=c, product=p, months=len(e),
                             first=str(m.min()) if len(m) else "", last=str(m.max()) if len(m) else "",
                             crisis_months=int(crisis.reindex(m).fillna(False).sum()),
                             of_crisis=int(crisis.sum()),
                             dropped_outliers=int(a.dropped.sum()) if len(a) else 0,
                             basis="; ".join(sorted(e.basis.unique()))))
    out = pd.DataFrame(rows)
    out.to_csv(P / "country_import_prices_coverage.csv", index=False)
    return out


if __name__ == "__main__":
    from .coreset import CORE30_LIST
    k = build()
    pd.set_option("display.width", 250)
    print(coverage(CORE30_LIST).to_string(index=False))
    st = ammonia_status()
    if len(st):
        print("\nammonia trade status (2015-2025):")
        print(st.reindex(CORE30_LIST).to_string())


# 2026-09-14 (Figure 3, ammonia): economies that produce their own gas at an
# administered or domestic-contract price and have no ammonia import price of
# their own are priced from that national gas (the grey-ammonia route of
# gap.fossil_for_fuel), not from the world urea price: their plants buy local
# gas. Importers without an own price take the urea-implied price.
# 2026-10-13 (audit S52): Australia removed -- it exports the ammonia molecule but imports about 55% of
# its nitrogen (mostly urea), so its marginal tonne is priced at the urea-implied import price like the other
# importers without an own price.
NH3_GAS_ROUTE = frozenset({"Saudi Arabia", "Oman", "Egypt", "Indonesia"})

# 2026-09-14: an ammonia importer without an import price of
# its own takes the urea-implied price scaled by the median own/urea ratio of
# the observed importers in its region (the landed premium of that market)
NH3_REGION = {
    "Germany": "Europe", "Italy": "Europe", "Spain": "Europe", "Norway": "Europe",
    "Poland": "Europe", "Netherlands": "Europe", "United Kingdom": "Europe",
    "Ireland": "Europe",
    "China": "Asia-Pacific", "India": "Asia-Pacific", "Japan": "Asia-Pacific",
    "South Korea": "Asia-Pacific", "Philippines": "Asia-Pacific",
    "Indonesia": "Asia-Pacific", "Vietnam": "Asia-Pacific",
    "Sri Lanka": "Asia-Pacific", "Pakistan": "Asia-Pacific",
    "Australia": "Asia-Pacific",
    "Morocco": "Middle East and Africa", "South Africa": "Middle East and Africa",
    "Egypt": "Middle East and Africa", "Kenya": "Middle East and Africa",
    "Madagascar": "Middle East and Africa", "Israel": "Middle East and Africa",
    "Saudi Arabia": "Middle East and Africa", "Oman": "Middle East and Africa",
    "United States of America": "Americas", "Brazil": "Americas",
    "Chile": "Americas", "Dominican Republic": "Americas",
}
_NH3_REGION_RATIO = {}


def nh3_regional_urea_ratio(country: str, table=None):
    """(ratio, n): the median over the region's observed ammonia importers of
    their median own-price / urea-implied-price ratio; (1.0, 0) if none"""
    reg = NH3_REGION.get(country)
    if reg not in _NH3_REGION_RATIO:
        from . import prices as PR
        proxy = PR.load(verified=True).ammonia_implied
        rs = []
        for c, r in NH3_REGION.items():
            if r != reg:
                continue
            own, _ = country_ammonia_monthly(c, table)
            ov = pd.concat([own, proxy], axis=1, keys=["o", "p"]).dropna() \
                if len(own) else pd.DataFrame()
            if len(ov) >= 12:
                rs.append(float((ov.o / ov.p).median()))
        _NH3_REGION_RATIO[reg] = (float(np.median(rs)), len(rs)) if rs else (1.0, 0)
    return _NH3_REGION_RATIO[reg]
