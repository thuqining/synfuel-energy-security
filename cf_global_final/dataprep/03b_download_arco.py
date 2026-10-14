"""
03b_download_arco.py
--------------------
Same purpose as 03_download_era5.py, but pulls ERA5 from ARCO-ERA5 (Google Cloud,
no CDS queue) by monkeypatching atlite's downloader. Produces era5_<year>.nc in
the IDENTICAL atlite-cutout format, so 04_compute_cf.py converts them unchanged.

Usage (conda env 'synfuel'):
  conda run -n synfuel python scripts/03b_download_arco.py --test
  conda run -n synfuel python scripts/03b_download_arco.py --year 2020
  conda run -n synfuel python scripts/03b_download_arco.py --start 2008 --end 2025
"""
from pathlib import Path
import argparse
import gc
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import arco_era5
arco_era5.patch_atlite()          # <-- swap CDS downloader for ARCO BEFORE using atlite
import atlite                      # noqa: E402
import xarray as xr               # noqa: E402

import os
PROJECT = Path(os.environ.get("SYNF_DATA", Path(__file__).resolve().parents[1]))
RAW_DIR = PROJECT / "data" / "raw_era5"
RAW_DIR.mkdir(parents=True, exist_ok=True)

X = slice(-180, 180)
Y = slice(-90, 90)
DX = DY = 2.5
FEATURES = ["influx", "temperature", "wind"]
YEARS = list(range(2006, 2026))


def build_cutout(raw_path, x, y, time):
    cutout = atlite.Cutout(path=str(raw_path), module="era5",
                           x=x, y=y, dx=DX, dy=DY, time=time)
    cutout.prepare(features=FEATURES)
    return cutout


def download_year(year):
    raw_path = RAW_DIR / f"era5_{year}.nc"
    if raw_path.exists():
        print(f"[{year}] raw present ({raw_path.stat().st_size/1e6:.0f} MB) -> skip")
        return
    print(f"[{year}] building cutout from ARCO-ERA5 ...")
    cutout = build_cutout(raw_path, X, Y, str(year))
    cutout.data.close()
    print(f"[{year}] DONE -> {raw_path.name} ({raw_path.stat().st_size/1e6:.0f} MB)")
    del cutout
    gc.collect()


def run_test():
    """Small region/time matching the earlier CDS smoke test, then convert + report
    so ARCO-derived CFs can be compared against the CDS-derived ones."""
    raw_path = RAW_DIR / "era5_ARCOTEST.nc"
    if raw_path.exists():
        raw_path.unlink()
    x, y = slice(-88.75, -78.75), slice(28.75, 38.75)
    time = slice("2020-06-01", "2020-06-02")
    print("[TEST] building ARCO cutout (Georgia, 2020-06-01..02) ...")
    cutout = build_cutout(raw_path, x, y, time)

    pv = cutout.pv(panel="CSi", orientation="latitude_optimal", tracking=None,
                   capacity_factor_timeseries=True)
    won = cutout.wind(turbine="NREL_ReferenceTurbine_2020ATB_4MW",
                      capacity_factor_timeseries=True)
    print("[TEST] dims:", dict(pv.sizes))
    print(f"[TEST] pv     min={float(pv.min()):.3f} max={float(pv.max()):.3f} "
          f"mean={float(pv.mean()):.3f}")
    print(f"[TEST] wind   min={float(won.min()):.3f} max={float(won.max()):.3f} "
          f"mean={float(won.mean()):.3f}")
    cell = pv.sel(x=-82.5, y=32.5, method="nearest").values[:24]
    print("[TEST] PV first 24h (UTC):")
    for h, v in enumerate(cell):
        print(f"   {h:02d}:00 {v:5.3f} " + "#" * int(v * 40))
    cutout.data.close()
    raw_path.unlink(missing_ok=True)
    print("[TEST] (compare to CDS test: pv mean ~0.219, peak ~18:00 UTC)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--year", type=int, default=None)
    ap.add_argument("--start", type=int, default=None)
    ap.add_argument("--end", type=int, default=None)
    args = ap.parse_args()

    if args.test:
        run_test()
        return
    if args.year:
        years = [args.year]
    elif args.start and args.end:
        years = list(range(args.start, args.end + 1))
    else:
        years = YEARS
    print(f"Downloading from ARCO: {years}")
    for yr in years:
        download_year(yr)
    print("ALL ARCO DOWNLOADS COMPLETE")


if __name__ == "__main__":
    main()
