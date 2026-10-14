"""
01_define_grid.py
-----------------
Build the 2.5-degree global analysis grid for the synthetic-fuels TEA.

Outputs a table of grid cells with:
  - cell_id, lat, lon (cell centre)
  - land_fraction (0..1) within the 2.5-deg cell
  - cell_type: 'land' | 'coastal_offshore'
  - country (dominant country for land cells; nearest for coastal)

Selection rules (locked in docs/00_plan.md):
  * land cell      : land_fraction > LAND_THRESHOLD, excluding Antarctica & Greenland
  * coastal_offshore: ocean cell (land_fraction <= LAND_THRESHOLD) that is an
                      8-neighbour of at least one selected land cell
                      (near-shore offshore-wind candidate)

Depth/distance classification (fixed vs floating) and offshore->land attribution
are deferred — they affect COST, not the resource profile, so they are not needed
to generate CF time series.

Run inside the 'synfuel' conda env:
    conda run -n synfuel python scripts/01_define_grid.py
"""

from pathlib import Path
import urllib.request
import zipfile
import numpy as np
import pandas as pd
import geopandas as gpd

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
RES = 2.5                     # grid resolution in degrees
LAND_THRESHOLD = 0.15         # min land fraction to count a cell as 'land'
EXCLUDE_COUNTRIES = {"Antarctica", "Greenland"}
EQUAL_AREA_CRS = "EPSG:6933"  # World Cylindrical Equal Area (for area calc)

import os
PROJECT = Path(os.environ.get("SYNF_DATA", Path(__file__).resolve().parents[1]))
GRID_DIR = PROJECT / "data" / "grid"
GRID_DIR.mkdir(parents=True, exist_ok=True)

# 10m (fine) resolution: includes small island nations that 110m omits
NE_URL = "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_0_countries.zip"
NE_DIR = GRID_DIR / "naturalearth"
NE_SHP = NE_DIR / "ne_10m_admin_0_countries.shp"


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def ensure_naturalearth():
    """Download Natural Earth 110m countries if not present locally."""
    if NE_SHP.exists():
        return NE_SHP
    NE_DIR.mkdir(parents=True, exist_ok=True)
    zpath = NE_DIR / Path(NE_URL).name
    print(f"Downloading Natural Earth countries -> {zpath}")
    urllib.request.urlretrieve(NE_URL, zpath)
    with zipfile.ZipFile(zpath) as z:
        z.extractall(NE_DIR)
    return NE_SHP


def build_grid_cells(res):
    """Create square polygons on the SAME centres as a global ERA5 2.5-deg cutout.

    atlite/ERA5 global 2.5-deg grid centres are at multiples of `res`:
        lon = -180, -177.5, ..., 177.5   (360/res points)
        lat =  -90,  -87.5, ...,  87.5   (180/res points)
    Cell (row=j, col=i) therefore maps directly to cutout array index [:, j, i].
    """
    from shapely.geometry import box

    half = res / 2.0
    lon_centers = np.arange(-180, 180, res)   # -180 .. 177.5
    lat_centers = np.arange(-90, 90, res)     # -90  .. 87.5
    records = []
    cid = 0
    for j, latc in enumerate(lat_centers):
        for i, lonc in enumerate(lon_centers):
            lon0, lon1 = max(lonc - half, -180), min(lonc + half, 180)
            lat0, lat1 = max(latc - half, -90), min(latc + half, 90)
            records.append(
                {
                    "cell_id": cid,
                    "row": j,
                    "col": i,
                    "lon": float(lonc),
                    "lat": float(latc),
                    "geometry": box(lon0, lat0, lon1, lat1),
                }
            )
            cid += 1
    gdf = gpd.GeoDataFrame(records, crs="EPSG:4326")
    return gdf


def compute_land_fraction(cells, countries):
    """Area-weighted land fraction per cell + dominant country, in equal-area CRS."""
    cells_ea = cells.to_crs(EQUAL_AREA_CRS)
    cells_ea["cell_area"] = cells_ea.area
    land_ea = countries.to_crs(EQUAL_AREA_CRS)

    # intersection of cells with all land polygons
    inter = gpd.overlay(
        cells_ea[["cell_id", "cell_area", "geometry"]],
        land_ea[["country", "geometry"]],
        how="intersection",
        keep_geom_type=True,
    )
    inter["inter_area"] = inter.area

    # land fraction per cell
    frac = (
        inter.groupby("cell_id")["inter_area"].sum()
        / cells_ea.set_index("cell_id")["cell_area"]
    ).fillna(0.0)

    # dominant country per cell (largest intersecting land area)
    dom = (
        inter.sort_values("inter_area")
        .groupby("cell_id")["country"]
        .last()
    )

    out = cells.copy()
    out["land_fraction"] = out["cell_id"].map(frac).fillna(0.0).clip(0, 1)
    out["country"] = out["cell_id"].map(dom)
    return out


def classify_cells(cells):
    """Tag land vs coastal_offshore using the land fraction and grid adjacency."""
    cells = cells.copy()

    is_land = (cells["land_fraction"] > LAND_THRESHOLD) & (
        ~cells["country"].isin(EXCLUDE_COUNTRIES)
    )
    # any land at all (even a tiny island) -> anchors a coastal candidate
    has_any_land = (cells["land_fraction"] > 0) & (
        ~cells["country"].isin(EXCLUDE_COUNTRIES)
    )

    # set of (row,col) for cells containing ANY land (for neighbour lookup)
    anyland_set = set(
        map(tuple, cells.loc[has_any_land, ["row", "col"]].to_numpy().tolist())
    )
    ncols = cells["col"].max() + 1  # for longitude wrap-around

    def near_any_land(r, c):
        # the cell itself contains some land, or an 8-neighbour does
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                nc = (c + dc) % ncols  # wrap longitude
                nr = r + dr
                if (nr, nc) in anyland_set:
                    return True
        return False

    cell_type = []
    for _, row in cells.iterrows():
        if is_land.loc[row.name]:
            cell_type.append("land")
        elif near_any_land(int(row["row"]), int(row["col"])):
            cell_type.append("coastal_offshore")
        else:
            cell_type.append("ocean")  # dropped later
    cells["cell_type"] = cell_type
    return cells


def main():
    print("1) building 2.5-deg grid ...")
    cells = build_grid_cells(RES)
    print(f"   total cells: {len(cells)}")

    print("2) loading Natural Earth countries ...")
    ensure_naturalearth()
    countries = gpd.read_file(NE_SHP)[["ADMIN", "geometry"]].rename(
        columns={"ADMIN": "country"}
    )

    print("3) computing land fraction + dominant country ...")
    cells = compute_land_fraction(cells, countries)

    print("4) classifying land / coastal_offshore ...")
    cells = classify_cells(cells)

    selected = cells[cells["cell_type"].isin(["land", "coastal_offshore"])].copy()
    n_land = (selected["cell_type"] == "land").sum()
    n_coast = (selected["cell_type"] == "coastal_offshore").sum()
    print(f"   land cells:             {n_land}")
    print(f"   coastal_offshore cells: {n_coast}")
    print(f"   total selected:         {len(selected)}")

    # save: lightweight CSV (centres + attrs) and full GeoPackage (with geometry)
    csv_cols = ["cell_id", "row", "col", "lon", "lat",
                "land_fraction", "cell_type", "country"]
    selected[csv_cols].to_csv(GRID_DIR / "grid_cells.csv", index=False)
    selected.to_file(GRID_DIR / "grid_cells.gpkg", driver="GPKG")
    print(f"saved -> {GRID_DIR/'grid_cells.csv'}")
    print(f"saved -> {GRID_DIR/'grid_cells.gpkg'}")


if __name__ == "__main__":
    main()
