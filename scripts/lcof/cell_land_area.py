"""
cell_land_area.py - the land of each cell's own country inside the cell, for
the land-limited hydrogen potential (2026-10-05, consistency audit).

Before this, firm_h2_potential_gj applied the usable land share to the whole
2.5-degree box, sea and neighbouring countries included, which overstated the
land of coastal and island economies up to threefold (Israel, Dominican
Republic, Philippines, Sri Lanka, Ireland, Norway, Japan, United Kingdom).

Here each land cell gets the area of its assigned country's territory inside
the box (Natural Earth 10m, equal-area projection). Territory that lies in
cells assigned to a neighbour (or in coastal cells below the land threshold)
is spread over the country's own cells in proportion to their own land, so
each country's cells add up to its whole territory:

    A_i = own_i * (territory_c / sum_{j in c} own_j)

The usable share (5% of eligible land, at most 2% of territory) then applies
to A_i, so the national total is exactly share x territory, as the Methods
state.

From scripts/:  python -u -m lcof.cell_land_area
Writes data/cost/cell_land_area.csv (cell_id, country, box_km2, own_km2,
territory_km2, land_km2).
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box

from . import inputs

OUT = inputs.MAPS / "cell_land_area.csv"
EA = "EPSG:6933"


def build() -> pd.DataFrame:
    meta = inputs.load_meta(2025)
    land = meta[meta.cell_type == "land"]
    ne = gpd.read_file(inputs.PROJECT / "cf_global_final" / "data" / "grid" / "naturalearth" /
                       "ne_10m_admin_0_countries.shp")[["ADMIN", "geometry"]].to_crs(EA)
    cells = gpd.GeoDataFrame(land[["country"]].copy(),
                             geometry=[box(r.lon - 1.25, r.lat - 1.25, r.lon + 1.25, r.lat + 1.25)
                                       for r in land.itertuples()], crs="EPSG:4326").to_crs(EA)
    inter = gpd.overlay(cells.reset_index(), ne, how="intersection", keep_geom_type=True)
    inter["a"] = inter.area / 1e6
    own = inter[inter.country == inter.ADMIN].groupby("cell_id").a.sum()
    terr = ne.assign(a=ne.area / 1e6).groupby("ADMIN").a.sum()
    out = pd.DataFrame({"country": land.country, "box_km2": cells.area / 1e6})
    out["own_km2"] = own.reindex(out.index).fillna(0.0)
    out["territory_km2"] = out.country.map(terr)
    s = out.groupby("country").own_km2.transform("sum")
    out["land_km2"] = np.where(s > 0, out.own_km2 * out.territory_km2 / s, np.nan)
    # a country Natural Earth does not name (or with no own land in its cells)
    # keeps the old box area, so no potential silently disappears
    miss = out.land_km2.isna()
    out.loc[miss, "land_km2"] = out.loc[miss, "box_km2"]
    out.index.name = "cell_id"
    return out, sorted(out.loc[miss, "country"].unique())


def main():
    out, miss = build()
    out.round(1).to_csv(OUT)
    by = out.groupby("country").agg(cells=("box_km2", "size"), box=("box_km2", "sum"), land=("land_km2", "sum"))
    by["ratio"] = by.land / by.box
    print(f"wrote {OUT.name}: {len(out)} cells; land / box over all cells {out.land_km2.sum() / out.box_km2.sum():.2f}; "
          f"countries falling back to the box area: {miss}")
    print(by.sort_values("ratio").head(15).round(2).to_string())


if __name__ == "__main__":
    main()
