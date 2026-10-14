"""2030 lowest-cost capex layer (2026-10-07).

Electrolyser (installed, US$/kW), IEA GHR 2026 Assumptions Annex, low end of the STEPS 2030 range:
  China 450; non-Chinese systems 1,440 (global average); Chinese systems installed abroad
  1,125 = GHR 2025 low end 1,500 x (1,440 / 1,920), no 2030 value published.
  Chinese systems are not available in the EEA (European Hydrogen Bank third auction and NZIA
  resilience criteria: no Chinese stacks) nor in the United States (Section 301 tariffs; kept
  conservative) nor Taiwan (cross-strait import restrictions); every other economy may use them.
Solar PV / onshore wind (US$/kW): IRENA RPGC 2025 Tables 2.1/3.1, 2025 total installed cost.
  Lowest = own cost level x (regional 5th percentile / regional weighted average), the own level
  being IRENA's 2025 national weighted average where reported, else the central layer. Never above
  the central layer. 2025 -> 2030 by the IEA GHR 2026 annex good-resource LCOE ratio (STEPS 2030 / 2025)
  of the matching IEA region; other regions take the median of the six IEA ratios.
Writes data/cost/capex_by_country_2030low.csv (same columns as capex_by_country.csv).
"""
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
COST = ROOT / "data" / "cost"
SRC = COST / "sources"

# IRENA RPGC 2025, 2025 TIC (2025 US$/kW): (5th percentile, weighted average)
PV = {"Africa": (593, 837), "Central America and the Caribbean": (649, 931), "Eurasia": (764, 998),
      "Europe": (518, 823), "Oceania": (612, 921), "Other Asia": (488, 882), "Other North America": (702, 887),
      "Other South America": (488, 867), "Brazil": (503, 672), "China": (374, 533), "India": (397, 545),
      "United States": (679, 1180)}
WD = {"Africa": (1391, 1550), "Eurasia": (845, 1397), "Europe": (1244, 1725), "Oceania": (1787, 1787),
      "Other Asia": (844, 1713), "Other North America": (1623, 1810), "Other South America": (1095, 1314),
      "Brazil": (1016, 1282), "China": (553, 789), "India": (782, 1172), "United States": (1014, 1668)}
WD["Central America and the Caribbean"] = WD["Other North America"]   # IRENA reports no onshore-wind row
# IEA GHR 2026 annex, good-resource LCOE (US$/MWh): 2025, STEPS 2030
IEA_PV = {"China": (23, 18), "Europe": (37, 30), "India": (23, 18), "Japan": (155, 128), "Korea": (88, 70),
          "North America": (37, 30)}
IEA_WD = {"China": (31, 30), "Europe": (49, 47), "India": (50, 46), "Japan": (100, 96), "Korea": (112, 109),
          "North America": (36, 35)}
R_PV = {k: b / a for k, (a, b) in IEA_PV.items()}
R_WD = {k: b / a for k, (a, b) in IEA_WD.items()}
R_PV["median"], R_WD["median"] = pd.Series(R_PV).median(), pd.Series(R_WD).median()
IEA_REGION = {"China": "China", "India": "India", "Europe": "Europe", "United States": "North America",
              "Other North America": "North America"}
IEA_COUNTRY = {"Japan": "Japan", "South Korea": "Korea"}

IRENA_NAME = {"Republic of Korea": "South Korea", "Türkiye": "Turkey", "Russian Federation": "Russia",
              "Lao PDR": "Laos", "United States": "United States of America",
              "Serbia": "Republic of Serbia"}
EU27 = ["Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czechia", "Denmark", "Estonia", "Finland",
        "France", "Germany", "Greece", "Hungary", "Ireland", "Italy", "Latvia", "Lithuania", "Luxembourg",
        "Malta", "Netherlands", "Poland", "Portugal", "Romania", "Slovakia", "Slovenia", "Spain", "Sweden"]
NO_CHINESE = set(EU27) | {"Norway", "Iceland", "Liechtenstein", "United States of America", "Taiwan"}
ELY = {"cn": 450.0, "west": 1440.0, "cn_import": round(1500 * 1440 / 1920)}

EURASIA = {"Russia", "Ukraine", "Belarus", "Turkey", "Kazakhstan", "Uzbekistan", "Turkmenistan", "Kyrgyzstan",
           "Tajikistan", "Azerbaijan", "Armenia", "Georgia", "Moldova"}


def irena_region(c, ne):
    if c in ("China", "India", "Brazil"):
        return c
    if c == "United States of America":
        return "United States"
    if c in EURASIA:
        return "Eurasia"
    if c in ("Maldives",):
        return "Other Asia"
    if c in ("Mauritius", "Seychelles"):
        return "Africa"
    r = ne[(ne.ADMIN == c) | (ne.NAME == c) | (ne.NAME_LONG == c)]
    if r.empty:
        return None
    cont, sub = r.CONTINENT.iloc[0], r.SUBREGION.iloc[0]
    if cont == "North America":
        return "Central America and the Caribbean" if sub in ("Central America", "Caribbean") else "Other North America"
    return {"Africa": "Africa", "Europe": "Europe", "Oceania": "Oceania", "Asia": "Other Asia",
            "South America": "Other South America"}.get(cont)


def build():
    cap = pd.read_csv(COST / "capex_by_country_ghr2026.csv").set_index("country")
    ne = gpd.read_file(ROOT / "data/grid/naturalearth/ne_10m_admin_0_countries.shp")[
        ["ADMIN", "NAME", "NAME_LONG", "CONTINENT", "SUBREGION"]]
    pvc = pd.read_csv(SRC / "irena2025_pv_tic_country.csv", index_col=0).pv_2025.rename(IRENA_NAME)
    wdc = pd.read_csv(SRC / "irena2025_wind_tic_country.csv", index_col=0).wind_2025.rename(IRENA_NAME)
    missing = [c for c in list(pvc.index) + list(wdc.index) if c not in cap.index]
    assert not missing, missing
    out = cap.copy()
    log = []
    for c in cap.index:
        rg = irena_region(c, ne)
        if rg is None:          # open-ocean pseudo-countries keep the central layer
            log.append(dict(country=c, region=None))
            continue
        p5, pa = PV[rg]
        w5, wa = WD[rg]
        pv25 = (pvc[c] if c in pvc.index else cap.pv_capex_usd_kw[c]) * p5 / pa
        wd25 = (wdc[c] if c in wdc.index else cap.wind_capex_usd_kw[c]) * w5 / wa
        pv25, wd25 = min(pv25, cap.pv_capex_usd_kw[c]), min(wd25, cap.wind_capex_usd_kw[c])
        k = IEA_COUNTRY.get(c) or IEA_REGION.get(rg) or "median"
        pv30, wd30 = pv25 * R_PV[k], wd25 * R_WD[k]
        bloc = "cn" if c == "China" else ("west" if c in NO_CHINESE else "cn_import")
        out.loc[c, ["pv_capex_usd_kw", "wind_capex_usd_kw"]] = round(pv30), round(wd30)
        out.loc[c, "electrolyser_capex_usd_kw"] = ELY[bloc]
        out.loc[c, "manuf_bloc"] = bloc
        out.loc[c, "electrolyser_source"] = {
            "cn": "IEA GHR 2026 annex, STEPS 2030 low end, China",
            "west": "IEA GHR 2026 annex, STEPS 2030 low end, global average (no Chinese systems: EEA/US/Taiwan)",
            "cn_import": "Chinese system abroad: GHR 2025 low end 1,500 x (1,440/1,920)"}[bloc]
        out.loc[c, "pv_wind_source"] = (f"IRENA RPGC 2025 {rg}, " + ("PV national" if c in pvc.index else "PV central")
                                        + ("/wind national" if c in wdc.index else "/wind central") + " x p5/avg" + f"; x IEA 2030 LCOE ratio ({k})")
        log.append(dict(country=c, region=rg, bloc=bloc, pv_central=cap.pv_capex_usd_kw[c], pv_2025low=round(pv25),
                        pv_2030low=round(pv30), wind_central=cap.wind_capex_usd_kw[c], wind_2025low=round(wd25),
                        wind_2030low=round(wd30), pv_national=c in pvc.index, wind_national=c in wdc.index,
                        ely_central=cap.electrolyser_capex_usd_kw[c], ely_2030low=ELY[bloc], iea_ratio=k))
    out.reset_index().to_csv(COST / "capex_by_country_2030low.csv", index=False)
    lg = pd.DataFrame(log).set_index("country")
    lg.to_csv(COST / "capex_by_country_2030low_log.csv")
    return out, lg, [c for c in NO_CHINESE if c not in cap.index]


ELY_2025 = {"cn": 550.0, "west": 1920.0, "cn_import": 1500.0}    # IEA GHR 2026 / 2025 low ends
DAC_2025_LOW = 400.0          # US$/t, low end of today's 400-600 (params.C_CO2_DAC note)
DAC_2030_OVER_2025 = 0.848    # DEA 403.a levelised cost 2030/2025 (see trajectory_dea_atb.csv)
TANK_2030_OVER_2025 = 0.881   # DEA 151a, 2025 interpolated between 2020 and 2030
SYN_ITEM = {"ammonia": "ammonia", "methanol": "methanol", "ethanol": "ethanol",
            "e-diesel": "fischer_tropsch", "e-kerosene": "fischer_tropsch", "e-methane": "methanation"}


def scalars(year: int) -> dict:
    """Year-dependent scalars of the lowest-cost case (applied to params at run time).
    2025/2030: eta_el 0.65 (at or above IEA's 63-64 %); synthesis at the IEA low end, flat to
    2030 as IEA assumes; battery 2030 at the NREL ATB 2024 Advanced 2030 index (lowest of the
    range); tank and DAC 2025->2030 from DEA. After 2030 one authoritative path for every tier,
    relative to the 2030 anchor (data/cost/trajectory_dea_atb.csv): DEA Technology Data for the
    electrolyser, its efficiency, synthesis plants, hydrogen tanks and DAC; NREL ATB 2024
    Moderate for PV, onshore wind and batteries."""
    t = pd.read_csv(COST / "trajectory_index.csv")
    tr = pd.read_csv(COST / "trajectory_dea_atb.csv").set_index("item")
    atb_adv30 = float(t[(t.tech == "battery_energy") & (t.case == "Advanced")].iloc[0]["2030"])
    s = dict(year=year, eta_el=0.65, ely=1.0, pv=1.0, wind=1.0, battery=1.0, h2_storage=1.0,
             dac_usd_t=DAC_2025_LOW, **{f"syn_{f}": 1.0 for f in SYN_ITEM})
    if year >= 2030:
        s.update(battery=atb_adv30, h2_storage=TANK_2030_OVER_2025, dac_usd_t=DAC_2025_LOW * DAC_2030_OVER_2025)
    if year > 2030:
        g = tr[str(year)].astype(float)
        s.update(pv=g["pv"], wind=g["wind_onshore"], ely=g["electrolyser"], eta_el=0.65 * g["eta_el"])
        s["battery"] *= g["battery"]
        s["h2_storage"] *= g["h2_tank"]
        s["dac_usd_t"] *= g["dac"]
        for f, item in SYN_ITEM.items():
            s[f"syn_{f}"] = g[item]
    return s


def layers(years=(2025, 2030, 2040, 2050)):
    """Write capex_by_country_<year>low.csv for each year from the 2030 build and its log."""
    c30 = pd.read_csv(COST / "capex_by_country_2030low.csv").set_index("country")
    lg = pd.read_csv(COST / "capex_by_country_2030low_log.csv", index_col=0)
    ok = lg.region.notna()
    rows = []
    for y in years:
        s = scalars(y)
        L = c30.copy()
        if y == 2025:
            L.loc[ok[ok].index, "pv_capex_usd_kw"] = lg.loc[ok, "pv_2025low"]
            L.loc[ok[ok].index, "wind_capex_usd_kw"] = lg.loc[ok, "wind_2025low"]
            L.loc[ok[ok].index, "electrolyser_capex_usd_kw"] = lg.loc[ok, "bloc"].map(ELY_2025)
            L["electrolyser_source"] = L["electrolyser_source"].str.replace("STEPS 2030 low end", "2025 low end")
        else:
            for col, k in (("pv_capex_usd_kw", "pv"), ("wind_capex_usd_kw", "wind"),
                           ("electrolyser_capex_usd_kw", "ely")):
                L[col] = (c30[col] * s[k]).round()
            L["battery_energy_usd_kwh"] = c30["battery_energy_usd_kwh"] * s["battery"]
            L["battery_power_usd_kw"] = c30["battery_power_usd_kw"] * s["battery"]
            L["h2_tank_usd_kwh"] = c30["h2_tank_usd_kwh"] * s["h2_storage"]
        L.reset_index().to_csv(COST / f"capex_by_country_{y}low.csv", index=False)
        rows.append(s)
    sc = pd.DataFrame(rows).set_index("year")
    sc.to_csv(COST / "lowest_case_scalars.csv")
    return sc


if __name__ == "__main__":
    out, lg, absent = build()
    print(layers().round(3).to_string())
    print("EEA/US/Taiwan names not in the 199-economy table:", absent)
    print("unmapped:", list(lg.index[lg.region.isna()]))
    print(lg.bloc.value_counts())
    print("PV lowest capped by central:", int((lg.pv_2025low == lg.pv_central).sum()),
          " wind:", int((lg.wind_2025low == lg.wind_central).sum()))
