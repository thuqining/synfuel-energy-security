"""
arco_era5.py
------------
Drop-in replacement for atlite's CDS downloader, backed by ARCO-ERA5 on Google
Cloud (public, no queue). Monkeypatching `atlite.datasets.era5.retrieve_data`
with the function here makes `cutout.prepare()` build a normal atlite ERA5 cutout
using ARCO data -> atlite's PV/wind conversion logic is reused unchanged.

ARCO dataset: gs://gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3
(0.25 deg, hourly; mirrors native ERA5, so accumulated radiation is in J/m**2.)
"""
import numpy as np
import pandas as pd
import xarray as xr

ARCO_URL = "gs://gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3"

# atlite long ERA5 name -> (ARCO variable name, atlite-expected short name)
VARMAP = {
    "10m_u_component_of_wind": ("10m_u_component_of_wind", "u10"),
    "10m_v_component_of_wind": ("10m_v_component_of_wind", "v10"),
    "100m_u_component_of_wind": ("100m_u_component_of_wind", "u100"),
    "100m_v_component_of_wind": ("100m_v_component_of_wind", "v100"),
    "forecast_surface_roughness": ("forecast_surface_roughness", "fsr"),
    "surface_net_solar_radiation": ("surface_net_solar_radiation", "ssr"),
    "surface_solar_radiation_downwards": ("surface_solar_radiation_downwards", "ssrd"),
    "toa_incident_solar_radiation": ("toa_incident_solar_radiation", "tisr"),
    "total_sky_direct_solar_radiation_at_surface":
        ("total_sky_direct_solar_radiation_at_surface", "fdir"),
    "2m_temperature": ("2m_temperature", "t2m"),
    "soil_temperature_level_4": ("soil_temperature_level_4", "stl4"),
    "2m_dewpoint_temperature": ("2m_dewpoint_temperature", "d2m"),
    "geopotential": ("geopotential_at_surface", "z"),
}

_ARCO = None


def arco():
    """Lazily open the ARCO-ERA5 zarr store (anonymous, time-chunked)."""
    global _ARCO
    if _ARCO is None:
        _ARCO = xr.open_zarr(ARCO_URL, chunks={"time": 24},
                             storage_options={"token": "anon"})
    return _ARCO


def _as_list(v):
    if isinstance(v, (list, tuple, np.ndarray)):
        return list(v)
    return [v]


def _build_times(updates):
    years = _as_list(updates["year"])
    months = _as_list(updates["month"])
    days = _as_list(updates["day"])
    hours = _as_list(updates["time"])
    ts = []
    for y in years:
        for m in months:
            for d in days:
                for hh in hours:
                    h = int(str(hh).split(":")[0])
                    try:
                        ts.append(pd.Timestamp(int(y), int(m), int(d), h))
                    except ValueError:
                        pass  # invalid date (e.g. 31 Feb) -> skip, like CDS
    return pd.DatetimeIndex(sorted(set(ts)))


def retrieve_data(product=None, chunks=None, tmpdir=None, lock=None, **updates):
    """ARCO-backed stand-in for atlite.datasets.era5.retrieve_data.

    Returns a dataset with ERA5 short-name variables on (valid_time, latitude,
    longitude) coords, matching the cutout grid implied by `area` and `grid`.
    """
    variable = _as_list(updates["variable"])
    area = updates["area"]            # [N, W, S, E]
    grid = str(updates["grid"])       # "dx/dy"
    dx, dy = (float(g) for g in grid.split("/"))
    N, W, S, E = (float(a) for a in area)

    xs = np.round(np.arange(W, E + 1e-6, dx), 5)        # -180 .. 177.5 (ascending)
    ys = np.round(np.arange(N, S - 1e-6, -dy), 5)       # 87.5 .. -90  (descending, CDS-like)

    ds = arco()[[VARMAP[v][0] for v in variable]]

    times = _build_times(updates)
    has_time = "time" in ds.dims
    if has_time and len(times):
        ds = ds.sel(time=times)

    # ARCO longitude is 0..359.75; map target xs (-180..177.5) onto it, keep order
    arco_lon = np.where(xs < 0, xs + 360.0, xs)
    ds = ds.sel(latitude=ys,
                longitude=xr.DataArray(arco_lon, dims="longitude"),
                method="nearest")
    # relabel onto the atlite cutout grid values
    ds = ds.assign_coords(longitude=xs, latitude=ys)

    if "time" in ds.dims:
        ds = ds.rename({"time": "valid_time"})
    else:
        ds = ds.expand_dims(valid_time=[times[0] if len(times)
                                        else pd.Timestamp("2000-01-01")])

    ds = ds.rename({VARMAP[v][0]: VARMAP[v][1] for v in variable})

    # ensure a 'units' attr exists (atlite reads ds['u100'].attrs['units'])
    for v in ds.data_vars:
        ds[v].attrs.setdefault("units", "")
    return ds


def patch_atlite():
    """Replace atlite's CDS downloader with the ARCO one."""
    import atlite.datasets.era5 as era5
    era5.retrieve_data = retrieve_data
    return era5
