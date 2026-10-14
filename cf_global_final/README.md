# Global capacity-factor generator (solar PV + onshore wind)

Region- and IEC-class-appropriate **solar PV** and **onshore wind** capacity
factors (CF) on a 2.5° global grid from ERA5 reanalysis, for one weather year.
Implemented in **Python (atlite)**; an independent MATLAB implementation was used
for cross-validation during development (not included here).

## Method

**Wind — IEC 61400-1 class matched to the local mean 100 m wind speed.**
Instead of one turbine everywhere, each cell uses a modern representative turbine
for its wind class (this removes the unrealistic high-CF tail that a low-specific-
power machine would give at very windy sites):

| local mean wind @100 m | IEC class | turbine | hub | character |
|---|---|---|---|---|
| < 7.5 m/s | III | NREL 2020 ATB 4 MW | 110 m | modern low specific power |
| 7.5–9.0 m/s | II | Enercon E101 3 MW | 99 m | medium |
| ≥ 9.0 m/s | I | Vestas V90 3 MW | 80 m | robust, high specific power |

**Solar — c-Si module; single-axis tracking in real tracker markets, fixed
elsewhere.** Module tech is globally homogeneous (c-Si ≈ 95 %+), so the lever is
tracking. Tracking is assigned by country using real 2024 tracker-market data
(US, India, Saudi, Spain, Brazil, Australia, MENA, Chile, Mexico, ...); fixed
tilt in high-latitude / diffuse / humid-tropic markets (N. Europe, Scandinavia,
Russia, Canada, Japan, SE-Asia); a resource fallback (track where fixed CF ≥ 0.17)
covers unlisted countries.

**Offshore wind — only the 19 countries with operational offshore wind (end-2024,
GWEC).** A coastal land cell in one of them gains an offshore option = best
near-shore-neighbour offshore CF (marinised 15 MW turbine, ~2× onshore CF).
Foundation = the lowest-LCOS feasible route: fixed-bottom (3300 $/kW) on shallow
shelves; floating (5500 $/kW) only where near-shore water is deep (Norway,
Portugal). Held as a SEPARATE layer (`wind_offshore_cf`, `offshore_type`,
`offshore_capex_usd_kw`) — onshore vs offshore is chosen later in the LCOS, not
as a CF max. See `docs/04_regional_technology.md`.

Conversion physics: wind = hub-height extrapolation + turbine power curve; PV =
simple isotropic transposition + Huld (2010) CSi panel model; single-axis
horizontal tracking per atlite's `SurfaceOrientation`.

Full sourcing and citations: `docs/04_regional_technology.md`.

## Layout (self-contained — data lives inside this folder)

```
dataprep/ 01_define_grid.py      build the 2.5° grid (auto-downloads Natural Earth)
          arco_era5.py            ARCO-ERA5 (public, Google Cloud) downloader shim
          03b_download_arco.py    build data/raw_era5/era5_<year>.nc from ARCO
python/   generate_cf_global.py   annual-MEAN CF + heatmaps (all years)
          generate_cf_hourly.py   HOURLY (8760) per-cell CF for the dispatch LCOS
          plot_style.py           country-aware global map renderer
docs/     04_regional_technology.md     method + data sources (URLs)
data/     raw_era5/   era5_<year>.nc  prepared ERA5 cutouts (2006-2025, ~3 GB/yr)
          grid/       2.5° grid + Natural Earth countries (GIS)
          cost/       cf_global_<year>.csv   per-cell mean CF + assignment  [output]
          cf_profiles/cf_global_<year>.nc    annual-mean CF fields          [output]
          cf_hourly/  cf_hourly_<year>.nc    HOURLY per-cell CF (~160 MB/yr) [output]
figures/  heatmap_{pv,wind,wind_offshore}_cf_<year>.png                 [output]
sample_outputs/   example heatmaps
```

Two output levels: **annual-mean** (`cf_global_*` — small, for heatmaps/resource
maps) and **hourly 8760** (`cf_hourly_*` — dims (cell, time); the time series the
dispatch LCOS consumes). Both follow the identical region/IEC-class scheme.

Paths default to this folder (`Path(__file__).parents[1]`); override the root
with the `SYNF_DATA` environment variable. The raw ERA5 cutouts (~61 GB for
20 years) are the only large input; if absent they are regenerated from public
sources by `dataprep/` (ARCO-ERA5 on Google Cloud + Natural Earth, no account).

## Run

```bash
# annual-mean CF + heatmaps, all 20 years
python python/generate_cf_global.py --start 2006 --end 2025
# hourly 8760 per-cell CF (LCOS input), all 20 years  (~160 MB/yr, ~1 min/yr)
python python/generate_cf_hourly.py  --start 2006 --end 2025
# (either accepts --year 2020 for a single year)
```
To rebuild inputs from scratch (only if data/ is empty):
```bash
python dataprep/01_define_grid.py                      # grid + Natural Earth
python dataprep/03b_download_arco.py --start 2006 --end 2025   # ERA5 from ARCO
```
Requirements: Python conda env with `atlite`, `xarray`, `geopandas`, `gcsfs`.

## Outputs (per year, 2006-2025)

- `data/cost/cf_global_<year>.csv` — per-cell wind/PV CF + assignment:
  `wind_cf` (onshore, IEC-class), `pv_fixed`/`pv_track`/`pv_cf` (selected PV),
  `wind_offshore_cf`/`offshore_type`/`offshore_capex_usd_kw`/`offshore_real`.
- `data/cf_profiles/cf_global_<year>.nc` — annual-mean CF fields.
- `data/cf_hourly/cf_hourly_<year>.nc` — **hourly** per-cell CF, dims (cell, time):
  `wind_onshore_cf`, `pv_fixed_cf`, `pv_track_cf`, `wind_offshore_cf` (the LCOS input).
- `figures/heatmap_{pv,wind,wind_offshore}_cf_<year>.png` — **darker = higher CF**.

## Validation

Benchmarked against
Renewables.ninja: solar within ~2 %; the wind difference is fully explained by
turbine vintage (modern low-SP machine vs ninja's 2000s V90) — with the same
turbine our CF is actually slightly below ninja, i.e. the conversion is not
inflating.
