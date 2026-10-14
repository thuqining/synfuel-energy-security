"""
generate_cf_hourly.py — LCOS-ready HOURLY (8760) capacity-factor profiles per
land cell, under the SAME region/IEC-class scheme as generate_cf_global.py.

For each land cell and each hour it stores:
  wind_onshore_cf  : IEC-class-matched onshore turbine (single feasible machine)
  pv_fixed_cf      : fixed-tilt PV        ) both kept — fixed vs tracking is a COST
  pv_track_cf      : single-axis tracking ) choice the LCOS makes per cell
  wind_offshore_cf : 15 MW offshore at the best near-shore neighbour (coastal cells
                     in the 19 offshore-wind countries; NaN elsewhere)

Output: data/cf_hourly/cf_hourly_<year>.nc   dims (cell, time), zlib-compressed.
~150-300 MB/year. The annual-mean generate_cf_global.py is the summary/heatmap;
THIS is the time series the dispatch LCOS consumes.

Usage:  python python/generate_cf_hourly.py --start 2006 --end 2025
"""
from pathlib import Path
import argparse
import numpy as np, xarray as xr
import atlite
import plot_style as ps
import generate_cf_global as G   # reuse scheme: constants + helpers (single source)

PROJECT = G.PROJECT
OUT = PROJECT / "data" / "cf_hourly"; OUT.mkdir(parents=True, exist_ok=True)


def main(year):
    raw = PROJECT / "data" / "raw_era5" / f"era5_{year}.nc"
    cutout = atlite.Cutout(path=str(raw))
    lon = cutout.data.x.values; lat = cutout.data.y.values
    xi = {round(float(v), 3): i for i, v in enumerate(lon)}
    yi = {round(float(v), 3): i for i, v in enumerate(lat)}

    grid = ps.load_grid()
    land = grid[grid.cell_type == "land"].reset_index(drop=True)
    n = len(land)
    iy = np.array([yi[round(float(la), 3)] for la in land.lat])
    ix = np.array([xi[round(float(lo), 3)] for lo in land.lon])

    # IEC class per land cell: CLIMATOLOGICAL (2006-2025 mean, make_class_ref.py)
    # so the turbine choice does not flip with the weather year.
    ref_path = PROJECT / "data" / "grid" / "tech_assignment_ref.csv"
    if ref_path.exists():
        import pandas as pd
        ref = pd.read_csv(ref_path).set_index("cell_id")
        cls = ref.loc[land.cell_id, "iec_class_ref"].values
    else:
        print("WARNING: tech_assignment_ref.csv missing -> per-year assignment")
        wspd = cutout.data["wnd100m"].mean("time").compute().values     # (y,x)
        mw = wspd[iy, ix]
        cls = np.where(mw < G.WSPD_THRESH[0], "III",
              np.where(mw < G.WSPD_THRESH[1], "II", "I"))

    def wind_ts(turbine):
        da = cutout.wind(turbine=turbine, capacity_factor_timeseries=True).compute()
        return da.transpose("time", "y", "x").values.astype("float32")  # (T,y,x)

    nt = cutout.data.sizes["time"]
    # ---- onshore: class-matched ----
    print(f"[{year}] onshore hourly (3 classes) ...", flush=True)
    wind_on = np.full((nt, n), np.nan, "float32")
    for cname, t in G.CLASS_TURBINE.items():
        g = wind_ts(t)[:, iy, ix]              # (T, n)
        sel = (cls == cname)
        wind_on[:, sel] = g[:, sel]
        del g
    # ---- PV: fixed + tracking ----
    print(f"[{year}] PV hourly (fixed + tracking) ...", flush=True)
    pv_fix = cutout.pv(panel=G.PANEL, orientation="latitude_optimal", tracking=None,
                       capacity_factor_timeseries=True).compute().transpose("time","y","x").values.astype("float32")[:, iy, ix]
    pv_trk = cutout.pv(panel=G.PANEL, orientation="latitude_optimal", tracking="horizontal",
                       capacity_factor_timeseries=True).compute().transpose("time","y","x").values.astype("float32")[:, iy, ix]
    # Huld model can exceed nameplate on cold sunny hours; cap at the inverter
    # rating (CF = 1). Affects 0.006 % of cell-hours, annual means by <0.001.
    np.minimum(pv_fix, 1.0, out=pv_fix)
    np.minimum(pv_trk, 1.0, out=pv_trk)
    # ---- offshore: hourly at best near-shore neighbour ----
    print(f"[{year}] offshore hourly (15 MW) ...", flush=True)
    off_grid = wind_ts(G.OFFSHORE_TURBINE)                  # (T,y,x)
    off_mean = off_grid.mean(axis=0)                        # (y,x)
    coastal = grid[grid.cell_type == "coastal_offshore"]
    cmap = {(int(r.row), int(r.col)): (yi[round(float(r.lat),3)], xi[round(float(r.lon),3)])
            for r in coastal.itertuples()}
    ncols = int(grid.col.max()) + 1
    wind_off = np.full((nt, n), np.nan, "float32")
    for k, r in enumerate(land.itertuples()):
        if r.country not in G.OFFSHORE_COUNTRIES:
            continue
        best, bcf = None, -1
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                key = (int(r.row) + dr, (int(r.col) + dc) % ncols)
                if key in cmap:
                    jy, jx = cmap[key]
                    if off_mean[jy, jx] > bcf:
                        bcf, best = off_mean[jy, jx], (jy, jx)
        if best is not None:
            wind_off[:, k] = off_grid[:, best[0], best[1]]
    del off_grid

    # ---- save (cell, time) ----
    ds = xr.Dataset(
        {"wind_onshore_cf": (("time", "cell"), wind_on),
         "pv_fixed_cf":     (("time", "cell"), pv_fix),
         "pv_track_cf":     (("time", "cell"), pv_trk),
         "wind_offshore_cf":(("time", "cell"), wind_off)},
        coords={"time": cutout.data.time.values, "cell_id": ("cell", land.cell_id.values),
                "lon": ("cell", land.lon.values), "lat": ("cell", land.lat.values),
                "iec_class": ("cell", cls)})
    ds.attrs["scheme"] = "IEC-class onshore; PV fixed+tracking; 15MW offshore (19 nations)"
    enc = {v: {"zlib": True, "complevel": 4, "dtype": "float32"} for v in ds.data_vars}
    ds.to_netcdf(OUT / f"cf_hourly_{year}.nc", encoding=enc)
    mb = (OUT / f"cf_hourly_{year}.nc").stat().st_size / 1e6
    print(f"[{year}] saved cf_hourly_{year}.nc ({mb:.0f} MB) | cells {n} hours {nt}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=None)
    ap.add_argument("--start", type=int, default=2006)
    ap.add_argument("--end", type=int, default=2025)
    a = ap.parse_args()
    years = [a.year] if a.year else list(range(a.start, a.end + 1))
    for y in years:
        if not (PROJECT / "data" / "raw_era5" / f"era5_{y}.nc").exists():
            print(f"[{y}] raw missing -> skip", flush=True); continue
        main(y)
    print("ALL HOURLY DONE:", years)
