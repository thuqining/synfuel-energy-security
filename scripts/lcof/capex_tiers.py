"""
capex_tiers.py — central and highest 2030 cost tiers for the Supplementary Information
(2026-10-07: lowest = main case, central and highest = SI), built exactly
like the lowest tier (lcof.capex_2030low) with the other end of each published range:

  electrolyser  IEA GHR 2026 annex, STEPS 2030: China 680 / 910, non-Chinese 1,700 / 1,870;
                Chinese systems installed abroad from the 2025 values x the global 2030/2025
                ratio: 1,950 x 1,700/2,200 = 1,507 (central), 2,400 x 1,870/2,500 = 1,795 (high)
  PV / wind     own level (IRENA 2025 national average, else the central layer) x regional
                weighted-average / weighted-average (central) or 95th percentile / weighted
                average (highest), x the IEA 2030/2025 LCOE ratio
  synthesis     Haber-Bosch 1,306 (mid) / 1,660 (high) US$/kW; single published values otherwise
  battery 2030  NREL ATB 2024 Moderate (central) / Conservative (highest) 2030 index
  tank, DAC     the DEA 2030/2025 ratios of the lowest tier; DAC from today's 500 / 600 US$/t

2025 tiers (2026-10-08, for the SI of Figs 1-3), the 2025 column of the same annex table:
  electrolyser  China 820 (the 2025 cost IEA uses in its LCOH analysis) / 1,100 (top of 550-1,100);
                non-Chinese 2,200 (IEA LCOH analysis) / 2,500 (top of 1,920-2,500); Chinese systems
                abroad 1,950 / 2,400 (GHR 2025: midpoint and top of 1,500-2,400)
  PV / wind     as above without the 2030/2025 ratio; battery, tank at today's central layer;
                DAC 500 / 600 US$/t; Haber-Bosch as in 2030 (IEA holds synthesis flat to 2030)

Writes data/cost/capex_by_country_{2025,2030}{mid,high}.csv and the tier rows (tier, year) to
data/cost/tier_scalars.csv.
"""
from __future__ import annotations

import geopandas as gpd
import pandas as pd

from . import capex_2030low as L

PV95 = {"Africa": 1139, "Central America and the Caribbean": 1016, "Eurasia": 1256, "Europe": 1501,
        "Oceania": 1785, "Other Asia": 2020, "Other North America": 1777, "Other South America": 1538,
        "Brazil": 1138, "China": 785, "India": 656, "United States": 1767}
WD95 = {"Africa": 1897, "Eurasia": 1982, "Europe": 2380, "Oceania": 1787, "Other Asia": 2881,
        "Other North America": 2250, "Other South America": 2252, "Brazil": 1516, "China": 1163,
        "India": 1301, "United States": 2672}
WD95["Central America and the Caribbean"] = WD95["Other North America"]
ELY = {"mid": {"cn": 680.0, "west": 1700.0, "cn_import": round(1950 * 1700 / 2200)},
       "high": {"cn": 910.0, "west": 1870.0, "cn_import": round(2400 * 1870 / 2500)}}
ELY_2025 = {"mid": {"cn": 820.0, "west": 2200.0, "cn_import": 1950.0},
            "high": {"cn": 1100.0, "west": 2500.0, "cn_import": 2400.0}}
HB = {"mid": 1306e3, "high": 1660e3}
ATB_CASE = {"mid": "Moderate", "high": "Conservative"}
DAC_2025 = {"mid": 500.0, "high": 600.0}


def build(tier: str, year: int = 2030):
    cap = pd.read_csv(L.COST / "capex_by_country_ghr2026.csv").set_index("country")
    low = pd.read_csv(L.COST / f"capex_by_country_{year}low.csv").set_index("country")
    ne = gpd.read_file(L.ROOT / "data/grid/naturalearth/ne_10m_admin_0_countries.shp")[
        ["ADMIN", "NAME", "NAME_LONG", "CONTINENT", "SUBREGION"]]
    pvc = pd.read_csv(L.SRC / "irena2025_pv_tic_country.csv", index_col=0).pv_2025.rename(L.IRENA_NAME)
    wdc = pd.read_csv(L.SRC / "irena2025_wind_tic_country.csv", index_col=0).wind_2025.rename(L.IRENA_NAME)
    out = low.copy()                     # same blocs, battery/tank columns, syn location factors
    for c in cap.index:
        rg = L.irena_region(c, ne)
        if rg is None:
            continue
        p5, pa = L.PV[rg]
        w5, wa = L.WD[rg]
        fp = 1.0 if tier == "mid" else PV95[rg] / pa
        fw = 1.0 if tier == "mid" else WD95[rg] / wa
        pv25 = (pvc[c] if c in pvc.index else cap.pv_capex_usd_kw[c]) * fp
        wd25 = (wdc[c] if c in wdc.index else cap.wind_capex_usd_kw[c]) * fw
        k = L.IEA_COUNTRY.get(c) or L.IEA_REGION.get(rg) or "median"
        r_pv, r_wd = (L.R_PV[k], L.R_WD[k]) if year == 2030 else (1.0, 1.0)
        out.loc[c, "pv_capex_usd_kw"] = round(pv25 * r_pv)
        out.loc[c, "wind_capex_usd_kw"] = round(wd25 * r_wd)
        bloc = low.manuf_bloc[c]
        out.loc[c, "electrolyser_capex_usd_kw"] = (ELY if year == 2030 else ELY_2025)[tier][bloc]
        out.loc[c, "electrolyser_source"] = (f"IEA GHR 2026 annex, STEPS 2030 {tier} ({bloc})" if year == 2030
                                             else f"IEA GHR 2026 annex, 2025 {tier} ({bloc})")
    t = pd.read_csv(L.COST / "trajectory_index.csv")
    b30 = (float(t[(t.tech == "battery_energy") & (t.case == ATB_CASE[tier])].iloc[0]["2030"])
           if year == 2030 else 1.0)
    out["battery_energy_usd_kwh"] = cap.battery_energy_usd_kwh.reindex(out.index) * b30
    out["battery_power_usd_kw"] = cap.battery_power_usd_kw.reindex(out.index) * b30
    out.reset_index().to_csv(L.COST / f"capex_by_country_{year}{tier}.csv", index=False)
    s = L.scalars(year)
    s.update(dac_usd_t=DAC_2025[tier] * (L.DAC_2030_OVER_2025 if year == 2030 else 1.0), battery=b30,
             tier=tier, hb_usd_kw=HB[tier] / 1e3)
    return out, s


def build_future(tier: str, year: int):
    """2026-10-08: 2040 and 2050 central and highest tiers. One learning path for every
    tier (2026-10-07): the tier's own 2030 layer times the DEA / NREL ATB
    2030 -> year ratios (trajectory_dea_atb.csv), exactly as the lowest tier is carried forward
    (capex_2030low.layers). Haber-Bosch is carried by the DEA ammonia ratio, DAC by the DEA
    ratio from the tier's own 2030 value."""
    c30 = pd.read_csv(L.COST / f"capex_by_country_2030{tier}.csv").set_index("country")
    g = pd.read_csv(L.COST / "trajectory_dea_atb.csv").set_index("item")[str(year)].astype(float)
    out = c30.copy()
    for col, k in (("pv_capex_usd_kw", "pv"), ("wind_capex_usd_kw", "wind_onshore"),
                   ("electrolyser_capex_usd_kw", "electrolyser")):
        out[col] = (c30[col] * g[k]).round()
    out["battery_energy_usd_kwh"] = c30["battery_energy_usd_kwh"] * g["battery"]
    out["battery_power_usd_kw"] = c30["battery_power_usd_kw"] * g["battery"]
    out["h2_tank_usd_kwh"] = c30["h2_tank_usd_kwh"] * g["h2_tank"]
    out["electrolyser_source"] = out["electrolyser_source"] + f" x DEA {year}/2030"
    out.reset_index().to_csv(L.COST / f"capex_by_country_{year}{tier}.csv", index=False)
    ts = pd.read_csv(L.COST / "tier_scalars.csv").set_index(["tier", "year"]).loc[(tier, 2030)]
    s = L.scalars(year)                    # eta_el, tank, synthesis ratios: the common path
    s.update(battery=float(ts.battery) * g["battery"], dac_usd_t=float(ts.dac_usd_t) * g["dac"],
             tier=tier, hb_usd_kw=float(ts.hb_usd_kw) * g["ammonia"])
    return out, s


if __name__ == "__main__":
    rows = []
    for year in (2025, 2030):
        for tier in ("mid", "high"):
            out, s = build(tier, year)
            rows.append(s)
            c = ["China", "Germany", "Japan", "Chile", "United States of America"]
            print(year, tier, out.loc[c, ["electrolyser_capex_usd_kw", "pv_capex_usd_kw", "wind_capex_usd_kw",
                                          "battery_energy_usd_kwh"]].round(0).to_string().replace("\n", "\n   "))
    pd.DataFrame(rows).set_index(["tier", "year"]).to_csv(L.COST / "tier_scalars.csv")
    for year in (2040, 2050):              # carried forward from the 2030 tiers just written
        for tier in ("mid", "high"):
            out, s = build_future(tier, year)
            rows.append(s)
            print(year, tier, out.loc[c, ["electrolyser_capex_usd_kw", "pv_capex_usd_kw", "wind_capex_usd_kw",
                                          "battery_energy_usd_kwh"]].round(0).to_string().replace("\n", "\n   "))
    pd.DataFrame(rows).set_index(["tier", "year"]).to_csv(L.COST / "tier_scalars.csv")
    print(pd.DataFrame(rows).set_index(["tier", "year"]).round(3).to_string())
