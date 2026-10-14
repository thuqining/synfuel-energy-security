"""
plot_style.py
-------------
Shared plotting style + a country-aware global map renderer.

Renderer = "gridded + borders + island fill":
  * LAND grid cells drawn as a 2.5-deg raster, coloured by value
  * crisp Natural-Earth country borders overlaid on top
  * island / small countries that have NO land grid cell are filled on their
    actual country polygon, using the value of the nearest grid cell
    (so the available CF is marked on the country, not on the offshore cell)

Fonts: Times New Roman, 8 pt.
"""
from pathlib import Path
import os
import numpy as np
import geopandas as gpd
import matplotlib as mpl
import matplotlib.pyplot as plt

mpl.use("Agg")

# ---- global style: Times New Roman, 8 pt --------------------------------------
mpl.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "font.size": 8,
    "axes.titlesize": 8,
    "axes.labelsize": 8,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "figure.titlesize": 8,
    "mathtext.fontset": "stix",
    "axes.linewidth": 0.5,
})

PROJECT = Path(os.environ.get("SYNF_DATA", Path(__file__).resolve().parents[1]))
GRID_GPKG = PROJECT / "data" / "grid" / "grid_cells.gpkg"
NE_SHP = PROJECT / "data" / "grid" / "naturalearth" / "ne_10m_admin_0_countries.shp"


def load_grid():
    return gpd.read_file(GRID_GPKG)


def load_countries():
    g = gpd.read_file(NE_SHP)[["ADMIN", "geometry"]].rename(columns={"ADMIN": "country"})
    # drop poles / irrelevant
    return g[~g["country"].isin(["Antarctica"])].copy()


_LAND_UNION = None


def land_union(countries):
    """Dissolved (slightly simplified) global land polygon, cached."""
    global _LAND_UNION
    if _LAND_UNION is None:
        _LAND_UNION = countries.geometry.simplify(0.05).union_all()
    return _LAND_UNION


def _nearest_cell_values(cells, points_xy):
    """For each (lon,lat) in points_xy, return value of nearest grid cell."""
    cxy = np.column_stack([cells["lon"].to_numpy(), cells["lat"].to_numpy()])
    vals = cells["val"].to_numpy()
    out = np.full(len(points_xy), np.nan)
    for i, (px, py) in enumerate(points_xy):
        d2 = (cxy[:, 0] - px) ** 2 + (cxy[:, 1] - py) ** 2
        out[i] = vals[np.argmin(d2)]
    return out


def render_map(value_by_cellid, title, cbar_label, cmap="viridis",
               vmin=0, vmax=None, out=None, clip_to_land=True):
    """Render one global country-aware heatmap.

    value_by_cellid : dict {cell_id: value}
    """
    cells = load_grid()
    cells["val"] = cells["cell_id"].map(value_by_cellid)
    countries = load_countries()

    if vmax is None:
        vmax = float(np.nanquantile(cells["val"], 0.99))
        vmax = max(vmax, 0.35)

    fig, ax = plt.subplots(figsize=(7.2, 3.6))  # ~18 cm wide

    # 1) raster: land cells, clipped to the exact coastline so colour stays in borders
    raster = cells[(cells["cell_type"] == "land") & cells["val"].notna()].copy()
    if clip_to_land:
        raster = gpd.clip(raster, land_union(countries))
    raster.plot(column="val", cmap=cmap, ax=ax, vmin=vmin, vmax=vmax, linewidth=0)

    # 2) island / small countries with NO land grid cell -> fill polygon by nearest cell
    land_countries = set(cells.loc[cells["cell_type"] == "land", "country"].dropna())
    NO_FILL = {"Greenland"}  # large, ice-covered, irrelevant -> don't island-fill
    islands = countries[~countries["country"].isin(land_countries | NO_FILL)].copy()
    if len(islands):
        cent = islands.geometry.representative_point()
        pts = np.column_stack([cent.x.to_numpy(), cent.y.to_numpy()])
        islands["val"] = _nearest_cell_values(cells, pts)
        islands = islands[np.isfinite(islands["val"])]
        islands.plot(column="val", cmap=cmap, ax=ax, vmin=vmin, vmax=vmax, linewidth=0)

    # 3) crisp country borders on top
    countries.boundary.plot(ax=ax, color="0.25", linewidth=0.15)

    # colorbar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=mpl.colors.Normalize(vmin, vmax))
    cb = fig.colorbar(sm, ax=ax, shrink=0.7, pad=0.01, aspect=30)
    cb.set_label(cbar_label)
    cb.ax.tick_params(width=0.4)

    ax.set_title(title)
    ax.set_xlim(-180, 180)
    ax.set_ylim(-58, 84)
    ax.set_xticks([-120, -60, 0, 60, 120])
    ax.set_yticks([-40, 0, 40, 80])
    ax.set_xlabel("Longitude (°)")
    ax.set_ylabel("Latitude (°)")
    ax.set_aspect("equal")
    for s in ax.spines.values():
        s.set_linewidth(0.5)
    plt.tight_layout()
    if out:
        plt.savefig(out, dpi=300, bbox_inches="tight")
        plt.close(fig)
        print("saved ->", out)
    return fig
