"""
generate_cf_global.py  —  FINAL global capacity-factor generator (Python/atlite).
================================================================================
Region-/class-appropriate solar PV and onshore wind capacity factors on the 2.5°
grid for one weather year, following the agreed scheme:

  WIND : IEC 61400-1 class matched to the local mean 100 m wind speed, each class
         using a modern representative turbine
            Class III (<7.5 m/s)  NREL 2020 ATB 4 MW  @110 m   (low specific power)
            Class II  (7.5-9 m/s)  Enercon E101 3 MW   @99 m
            Class I   (>=9 m/s)    Vestas V90 3 MW     @80 m   (robust, high SP)
  SOLAR: c-Si module; single-axis horizontal tracking in real tracker markets
         (US, India, Saudi, Spain, Brazil, Australia, MENA, Chile, Mexico, ...),
         fixed tilt in high-latitude / diffuse / humid-tropic markets, with a
         resource fallback (track where fixed CF >= 0.17) for unlisted countries.

Sources: IEC 61400-1; LBNL Land-Based Wind Market Report 2023; NREL ATB 2024;
solar-tracker market shares 2024 (APAC 36%, NA 33%, EU 22%; top5 US/India/Saudi/
Spain/Brazil). See docs/04_regional_technology.md.

Outputs
  data/cost/cf_global_<year>.csv          per-cell wind/PV CF + assignment
  data/cf_profiles/cf_global_<year>.nc    mean-CF fields
  figures/heatmap_pv_cf_<year>.png        global PV CF   (dark = high CF)
  figures/heatmap_wind_cf_<year>.png      global wind CF (dark = high CF)

Usage:  conda run -n synfuel python scripts/generate_cf_global.py --year 2020
"""
from pathlib import Path
import os, argparse
import numpy as np, pandas as pd, xarray as xr
import atlite
import plot_style as ps

# Self-contained: data + outputs live under this folder (cf_global_final/).
# data/raw_era5/era5_<year>.nc (inputs), data/grid/ (GIS), data/cost, data/cf_profiles,
# figures/ (outputs). Override the root with env SYNF_DATA if desired.
PROJECT = Path(os.environ.get("SYNF_DATA", Path(__file__).resolve().parents[1]))
(PROJECT / "data" / "cost").mkdir(parents=True, exist_ok=True)
(PROJECT / "data" / "cf_profiles").mkdir(parents=True, exist_ok=True)
(PROJECT / "figures").mkdir(parents=True, exist_ok=True)
CMAP = "YlGnBu"        # sequential, light = low CF, DARK = high CF

CLASS_TURBINE = {"III": "NREL_ReferenceTurbine_2020ATB_4MW",
                 "II":  "Enercon_E101_3000kW",
                 "I":   "Vestas_V90_3MW"}
WSPD_THRESH = (7.5, 9.0)                       # m/s class boundaries III|II|I
PANEL = "CSi"

TRACK = {  # real single-axis-tracking markets (sunny / DNI-rich)
    "United States of America","Mexico","Brazil","Chile","Argentina","Peru","Bolivia",
    "Colombia","Spain","Italy","Portugal","Greece","Turkey","India","Pakistan",
    "Saudi Arabia","United Arab Emirates","Oman","Qatar","Kuwait","Yemen","Jordan",
    "Israel","Iraq","Iran","Egypt","Morocco","Algeria","Tunisia","Libya","Sudan",
    "South Africa","Namibia","Botswana","Zimbabwe","Mozambique","Angola","Mali",
    "Niger","Chad","Mauritania","Australia","Turkmenistan","Uzbekistan","Afghanistan",
    "Ethiopia","Kenya","Tanzania","Somalia","Senegal","Nigeria","Eritrea","Djibouti"}
FIXED = {  # high-latitude / diffuse / humid-tropics: fixed tilt dominates
    "Germany","United Kingdom","Ireland","Netherlands","Belgium","Denmark","Norway",
    "Sweden","Finland","Estonia","Latvia","Lithuania","Poland","Czechia","Slovakia",
    "Austria","Switzerland","Hungary","Romania","Bulgaria","Russia","Belarus","Ukraine",
    "Canada","Iceland","Indonesia","Malaysia","Philippines","Vietnam","Thailand",
    "Cambodia","Laos","Myanmar","Japan","South Korea","North Korea","New Zealand",
    "Papua New Guinea","Democratic Republic of the Congo","Gabon","France",
    "Republic of the Congo","Bangladesh","Nepal","Bhutan","Brunei"}


# Offshore wind: only countries with operational offshore wind (end-2024, 19
# total: 13 EU + 5 Asia + 1 N.America; GWEC 2024). A coastal LAND cell in one of
# these gains an offshore option = best adjacent near-shore cell's offshore CF.
OFFSHORE_COUNTRIES = {
    "United Kingdom","Germany","Netherlands","Denmark","Belgium","France","Sweden",
    "Finland","Ireland","Norway","Portugal","Spain","Italy",              # Europe (13)
    "China","Taiwan","Japan","South Korea","Vietnam",                      # Asia (5)
    "United States of America"}                                            # N.America (1)
# Foundation route actually deployed: floating only where near-shore water is deep
# (Norway Hywind Tampen, Portugal WindFloat); all shallow-shelf markets are fixed.
FLOATING_OFFSHORE = {"Norway", "Portugal"}
OFFSHORE_TURBINE = "NREL_ReferenceTurbine_2020ATB_15MW_offshore"   # marinised 15 MW

# established offshore-wind clusters (lon0, lon1, lat0, lat1) — curated from real
# deployment regions (OSM seamark coverage too sparse; GEM/4C are gated). The
# offshore HEATMAP shows only cells in these clusters; the CF table keeps every
# 19-country coastal offshore option so the LCOS can still choose freely.
OFFSHORE_CLUSTERS = [
    (-4, 9, 51, 61), (10, 26, 53, 61), (-6, 1.5, 50, 56), (-5, 2, 46, 51),   # N.Sea/Baltic/UK/FR
    (-10, -1, 36, 44), (8, 19, 38, 45),                                       # Iberia/Med
    (108, 123, 19, 41), (119, 122, 22, 26),                                   # China/Taiwan
    (138, 143, 33, 43), (124, 130, 33, 38), (105, 109, 8, 12),                # Japan/Korea/Vietnam
    (-75, -68, 38, 43),                                                       # US NE Atlantic
]
def in_offshore_cluster(lon, lat):
    return any(x0 <= lon <= x1 and y0 <= lat <= y1 for x0, x1, y0, y1 in OFFSHORE_CLUSTERS)


def pv_is_tracking(country, fixed_cf):
    if country in TRACK: return True
    if country in FIXED: return False
    return fixed_cf >= 0.17               # resource fallback for unlisted countries


def main(year):
    raw = PROJECT / "data" / "raw_era5" / f"era5_{year}.nc"
    cutout = atlite.Cutout(path=str(raw))

    # ---- mean wind speed -> IEC class (materialise once) ----
    wspd = cutout.data["wnd100m"].mean("time").compute()
    cls = xr.where(wspd < WSPD_THRESH[0], 3,
          xr.where(wspd < WSPD_THRESH[1], 2, 1)).compute()

    # ---- per-class wind CF, then class-matched assembly ----
    print("wind: per-class CF ...", flush=True)
    cf = {c: cutout.wind(turbine=t, capacity_factor=True).compute()
          for c, t in CLASS_TURBINE.items()}
    wind = xr.where(cls == 3, cf["III"], xr.where(cls == 2, cf["II"], cf["I"])).compute()

    # ---- PV fixed + single-axis tracking ----
    print("solar: fixed + tracking CF ...", flush=True)
    pv_fix = cutout.pv(panel=PANEL, orientation="latitude_optimal",
                       tracking=None, capacity_factor=True).compute()
    pv_trk = cutout.pv(panel=PANEL, orientation="latitude_optimal",
                       tracking="horizontal", capacity_factor=True).compute()

    # ---- offshore wind CF (marinised 15 MW), for near-shore cells ----
    print("offshore: 15 MW CF ...", flush=True)
    wind_off = cutout.wind(turbine=OFFSHORE_TURBINE, capacity_factor=True).compute()

    # ---- assemble on the grid, assign PV mode by country ----
    grid = ps.load_grid()
    sel = lambda f, lo, la: float(f.sel(x=lo, y=la, method="nearest"))

    # CLIMATOLOGICAL technology assignment (make_class_ref.py): IEC class and PV
    # mode are investment decisions -> fixed on the 2006-2025 mean, not the
    # weather year (boundary cells otherwise flip technology between years).
    ref_path = PROJECT / "data" / "grid" / "tech_assignment_ref.csv"
    ref = None
    if ref_path.exists():
        ref = pd.read_csv(ref_path).set_index("cell_id")
        num = {"III": 3, "II": 2, "I": 1}
        cls_v = cls.values.copy()
        for r in grid.itertuples():
            iy = int(np.abs(cls.y.values - r.lat).argmin())
            ix = int(np.abs(cls.x.values - r.lon).argmin())
            cls_v[iy, ix] = num[ref.loc[r.cell_id, "iec_class_ref"]]
        cls = cls.copy(data=cls_v)
        wind = xr.where(cls == 3, cf["III"], xr.where(cls == 2, cf["II"], cf["I"])).compute()
    else:
        print("WARNING: tech_assignment_ref.csv missing -> per-year assignment")
    # offshore CF sampled at every near-shore (coastal_offshore) cell, keyed by (row,col)
    coastal_off = {(int(r.row), int(r.col)): sel(wind_off, r.lon, r.lat)
                   for r in grid.itertuples() if r.cell_type == "coastal_offshore"}
    ncols = int(grid.col.max()) + 1
    def best_offshore(row, col):                 # max offshore CF over 8 neighbours
        vals = [coastal_off.get((row + dr, (col + dc) % ncols))
                for dr in (-1, 0, 1) for dc in (-1, 0, 1)]
        vals = [v for v in vals if v is not None]
        return max(vals) if vals else np.nan

    rows = []
    for r in grid.itertuples():
        clname = {3: "III", 2: "II", 1: "I"}[int(sel(cls, r.lon, r.lat))]
        f_fix = round(sel(pv_fix, r.lon, r.lat), 3)
        if ref is not None:
            track = ref.loc[r.cell_id, "pv_mode_ref"] == "tracking"
        else:
            track = pv_is_tracking(r.country, f_fix)
        # offshore option: coastal LAND cell in an offshore-wind country
        off_cf, off_type, off_capex, off_real = np.nan, "", np.nan, False
        if r.cell_type == "land" and r.country in OFFSHORE_COUNTRIES:
            b = best_offshore(int(r.row), int(r.col))
            if np.isfinite(b):
                off_cf = round(b, 3)
                floating = r.country in FLOATING_OFFSHORE
                off_type = "floating" if floating else "fixed"
                off_capex = 5500 if floating else 3300          # $/kW (see params.py)
                off_real = in_offshore_cluster(r.lon, r.lat)    # in a real deployment cluster
        rows.append(dict(cell_id=r.cell_id, lon=r.lon, lat=r.lat, country=r.country,
                         cell_type=r.cell_type, mean_wspd100=round(sel(wspd, r.lon, r.lat), 2),
                         iec_class=clname, wind_cf=round(sel(wind, r.lon, r.lat), 3),
                         pv_fixed=f_fix, pv_track=round(sel(pv_trk, r.lon, r.lat), 3),
                         pv_mode="tracking" if track else "fixed",
                         wind_offshore_cf=off_cf, offshore_type=off_type,
                         offshore_capex_usd_kw=off_capex, offshore_real=off_real))
    df = pd.DataFrame(rows)
    df["pv_cf"] = np.where(df.pv_mode == "tracking", df.pv_track, df.pv_fixed)
    df.to_csv(PROJECT / "data" / "cost" / f"cf_global_{year}.csv", index=False)
    xr.Dataset({"wind_cf": wind, "wind_offshore": wind_off, "pv_fixed": pv_fix,
                "pv_track": pv_trk, "iec_class": cls, "mean_wspd100": wspd}).to_netcdf(
        PROJECT / "data" / "cf_profiles" / f"cf_global_{year}.nc")

    land = df[df.cell_type == "land"]
    off = land[land.wind_offshore_cf.notna()]
    print("\nLAND wind CF : median %.3f  p90 %.3f  max %.3f" % (
        land.wind_cf.median(), land.wind_cf.quantile(.9), land.wind_cf.max()))
    print("LAND PV CF   : median %.3f  p90 %.3f  | tracking %d / fixed %d cells" % (
        land.pv_cf.median(), land.pv_cf.quantile(.9),
        (land.pv_mode == "tracking").sum(), (land.pv_mode == "fixed").sum()))
    print("OFFSHORE     : %d coastal land cells in %d offshore-wind countries | "
          "CF median %.3f | fixed %d / floating %d" % (
          len(off), off.country.nunique(), off.wind_offshore_cf.median(),
          (off.offshore_type == "fixed").sum(), (off.offshore_type == "floating").sum()))

    # ---- heatmaps (DARK = HIGH CF) ----
    idx = df.set_index("cell_id")
    ps.render_map(idx.pv_cf.to_dict(),
                  f"Global solar PV capacity factor ({year}, region-appropriate)",
                  "PV CF", cmap=CMAP, vmin=0.05, vmax=0.28,
                  out=PROJECT / "figures" / f"heatmap_pv_cf_{year}.png")
    ps.render_map(idx.wind_cf.to_dict(),
                  f"Global onshore wind capacity factor ({year}, IEC class-matched)",
                  "Wind CF", cmap=CMAP, vmin=0.10, vmax=0.55,
                  out=PROJECT / "figures" / f"heatmap_wind_cf_{year}.png")
    # offshore CF map: only cells in REAL offshore-wind clusters (realistic view)
    real = land[land.offshore_real]
    ps.render_map(real.set_index("cell_id")["wind_offshore_cf"].to_dict(),
                  f"Offshore wind capacity factor ({year}, 15 MW, real offshore-wind clusters)",
                  "Offshore wind CF", cmap=CMAP, vmin=0.20, vmax=0.65,
                  out=PROJECT / "figures" / f"heatmap_wind_offshore_cf_{year}.png")
    print("  offshore in real clusters: %d cells" % len(real))
    print("saved -> heatmap_pv_cf_%d.png, heatmap_wind_cf_%d.png, "
          "heatmap_wind_offshore_cf_%d.png" % (year, year, year))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=None, help="single year")
    ap.add_argument("--start", type=int, default=2006)
    ap.add_argument("--end", type=int, default=2025)
    a = ap.parse_args()
    years = [a.year] if a.year else list(range(a.start, a.end + 1))
    for y in years:
        if not (PROJECT / "data" / "raw_era5" / f"era5_{y}.nc").exists():
            print(f"[{y}] raw cutout missing -> skip", flush=True); continue
        print(f"\n========== {y} ==========", flush=True)
        main(y)
    print("\nALL YEARS DONE:", years)
