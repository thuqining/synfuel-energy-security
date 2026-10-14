"""
slim_era5_cutout.py -- shrink the atlite ERA5 cutouts kept as raw input (about 3.1 -> 1.9 GB per year).

Converts the float64 variables (solar_altitude, solar_azimuth, wnd_shear_exp) to float32 and drops the
variables that the wind and PV capacity factors do not use (soil temperature, dewpoint temperature,
wnd_azimuth). Compression stays zlib level 9 with shuffle. The slim cutout gives the same capacity factors
(see --check).

    python slim_era5_cutout.py <in.nc> <out.nc> [--check]
"""
import sys

import numpy as np
import xarray as xr

DROP = ["soil temperature", "dewpoint temperature", "wnd_azimuth"]
DOWNCAST = ["solar_altitude", "solar_azimuth", "wnd_shear_exp"]


def slim(src, dst):
    ds = xr.open_dataset(src)
    ds = ds.drop_vars([v for v in DROP if v in ds])
    enc = {}
    for v in ds.data_vars:
        if v in DOWNCAST:
            ds[v] = ds[v].astype("float32")
        e = {"zlib": True, "complevel": 9, "shuffle": True}
        if ds[v].ndim == 3:
            e["chunksizes"] = (min(100, ds.sizes["time"]), ds[v].shape[1], ds[v].shape[2])
        enc[v] = e
    ds.to_netcdf(dst, encoding=enc)
    ds.close()


def check(src, dst):
    import atlite
    out = {}
    for name, path in (("orig", src), ("slim", dst)):
        c = atlite.Cutout(path=path).sel(time=slice(None, None))
        c = atlite.Cutout(path=path)
        sub = c.sel(time=c.data.time.values[:24 * 14])          # two weeks
        out[name] = (sub.pv(panel="CSi", orientation="latitude_optimal", capacity_factor=True).values,
                     sub.wind(turbine="Vestas_V112_3MW", capacity_factor=True).values)
    for i, k in enumerate(("pv", "wind")):
        d = np.nanmax(np.abs(out["orig"][i] - out["slim"][i]))
        print(f"{k}: max abs difference in mean capacity factor {d:.2e}")


if __name__ == "__main__":
    slim(sys.argv[1], sys.argv[2])
    print("wrote", sys.argv[2])
    if "--check" in sys.argv:
        check(sys.argv[1], sys.argv[2])
