"""
fig_sd_map_zoom.py - Fig. 2 with regional maps (2026-10-19 draft): a, the global
supply-demand map exactly as fig_sd_map.full draws it; b-d, three regions (Europe; Japan and the Korean
Peninsula; South and Southeast Asia) drawn as maps of their own member countries (not crops of a): only members carry the class colors, inside a firm regional outline;
neighbouring land is left blank with a faint outline. No corridors or flows (those stay in the SI).
Display only: classes, counts and key values still come from the 2,740 cells.

From scripts/:  python ../work/caselow/run_mod.py ../work/caselow/2025mid 2025 lcof.fig_sd_map_zoom
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch

mpl.use("Agg")

from . import inputs
from . import fig_sd_map as SD
from . import fig_pptx_pairs as FPP
from .fig_main_cost import MM, NAT_RC

INK = "#1F2A36"
FAINT = "#A7AFB8"
EXT = (-181.25, 178.75, -63.75, 86.25)
# Europe: every European country except Russia (UN M49 Europe, with Crown dependencies, the Faroes and
# Aland), plus the transcontinental members of European institutions (Turkey, the whole island of Cyprus,
# Georgia, Armenia, Azerbaijan); Russia and Kazakhstan are left out; Crimea is drawn with Ukraine
EUROPE = ["Albania", "Aland", "Andorra", "Austria", "Belarus", "Belgium", "Bosnia and Herzegovina", "Bulgaria",
          "Croatia", "Czechia", "Denmark", "Estonia", "Faroe Islands", "Finland", "France", "Germany", "Gibraltar",
          "Greece", "Guernsey", "Hungary", "Iceland", "Ireland", "Isle of Man", "Italy", "Jersey", "Kosovo", "Latvia",
          "Liechtenstein", "Lithuania", "Luxembourg", "Malta", "Moldova", "Monaco", "Montenegro", "Netherlands",
          "North Macedonia", "Norway", "Poland", "Portugal", "Republic of Serbia", "Romania", "San Marino",
          "Slovakia", "Slovenia", "Spain", "Sweden", "Switzerland", "Ukraine", "United Kingdom", "Vatican",
          "Turkey", "Cyprus", "Northern Cyprus", "Cyprus No Mans Area", "Akrotiri Sovereign Base Area",
          "Dhekelia Sovereign Base Area", "Georgia", "Armenia", "Azerbaijan"]
SOUTH_ASIA = ["Afghanistan", "Bangladesh", "Bhutan", "India", "Maldives", "Nepal", "Pakistan", "Sri Lanka",
              "Siachen Glacier"]
SOUTHEAST_ASIA = ["Brunei", "Cambodia", "Indonesia", "Laos", "Malaysia", "Myanmar", "Philippines", "Singapore",
                  "Thailand", "East Timor", "Vietnam"]
# members, and the box that keeps each member's home territory (drops French overseas regions, the
# Canaries, Azores, Madeira and Svalbard; Japan's remote Pacific islands are dropped below)
REGIONS = [
    ("b", "Europe", EUROPE, (-26, 52, 34, 72)),
    ("c", "Japan and the Korean Peninsula", ["Japan", "South Korea", "North Korea"], (122, 149, 24, 46)),
    ("d", "South and Southeast Asia", SOUTH_ASIA + SOUTHEAST_ASIA, (55, 142, -12, 40)),
]


def _field():
    df = pd.read_csv(inputs.MAPS / "sd_map_classes.csv", index_col=0)
    cache = FPP.OUT / "_fig2_kriged.npz"
    if cache.exists():
        z = np.load(cache)
        Uz, Vz, Dz = z["Uz"], z["Vz"], z["Dz"]
    else:
        U, V = SD._rank_fields(df)
        Uz, Dz, _ = SD._krige(U, 10, k=24)
        Vz, _, _ = SD._krige(V, 10, k=24)
        np.savez_compressed(cache, Uz=Uz, Vz=Vz, Dz=Dz)
    return df, Uz, Vz, Dz


def _patch(ax, geom):
    """a clipping patch of a (multi)polygon"""
    polys = getattr(geom, "geoms", [geom])
    verts, codes = [], []
    for poly in polys:
        for ring in [poly.exterior] + list(poly.interiors):
            xy = np.asarray(ring.coords)
            if len(xy) < 3:
                continue
            verts.append(xy)
            codes.append(np.r_[MPath.MOVETO, np.full(len(xy) - 1, MPath.LINETO)])
    return PathPatch(MPath(np.vstack(verts), np.concatenate(codes)), transform=ax.transData, fc="none", ec="none")


def _members(names, box):
    """the member countries' home territory: polygons whose centroid lies in the box"""
    from shapely.geometry import box as sbox
    from shapely.ops import unary_union
    C = SD._COUNTRIES.set_index("country")
    missing = [n for n in names if n not in C.index]
    assert not missing, missing
    b = sbox(box[0], box[2], box[1], box[3])
    keep = {}
    for n in names:
        g = C.loc[n, "geometry"]
        ps = [p for p in getattr(g, "geoms", [g]) if b.contains(p.centroid)]
        if n == "Japan":                      # Ogasawara and Daito: remote Pacific islands
            ps = [p for p in ps if not (p.centroid.y < 30 and p.centroid.x > 130)]
        if n == "Ukraine":                    # Crimea, held in the boundary file under Russia
            crimea = C.loc["Russia", "geometry"].intersection(sbox(32.3, 44.3, 36.65, 46.25))
            ps = ps + [crimea]
        if ps:
            keep[n] = unary_union(ps)
    return keep, unary_union(list(keep.values()))


def _paint(ax, rgb, Uz, Vz, Dz, clip_geom=None, s=1.0):
    """the full_krige rendering clipped to land (a) or to a region's member countries (b-d)"""
    import geopandas as gpd
    im = ax.imshow(rgb, origin="lower", interpolation="nearest", extent=EXT, zorder=1, rasterized=True)
    clip = SD._land_clip_patch(ax) if clip_geom is None else _patch(ax, clip_geom)
    im.set_clip_path(clip)
    yy = np.linspace(EXT[2], EXT[3], Uz.shape[0])
    xx = np.linspace(EXT[0], EXT[1], Uz.shape[1])
    lev = np.arange(1, SD.ND) / SD.ND
    for F in (Uz, Vz):
        cs = ax.contour(xx, yy, np.where(Dz <= 1.2, F, np.nan), levels=lev, colors="#3A4550",
                        linewidths=0.11 * s, alpha=0.45, zorder=2.5)
        cs.set_clip_path(clip)
    if clip_geom is None:
        SD._COUNTRIES.boundary.plot(ax=ax, color="#1A1A1A", linewidth=0.09 * s, zorder=2)
        gpd.GeoSeries([SD._LAND_UNION]).boundary.plot(ax=ax, color="#1A1A1A", linewidth=0.18 * s, zorder=3)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect("equal")


def main():
    import geopandas as gpd
    mpl.rcParams.update(NAT_RC)
    mpl.rcParams.update({"pdf.fonttype": 42})
    FPP.OUT.mkdir(parents=True, exist_ok=True)
    SD.ND = 3
    df, Uz, Vz, Dz = _field()
    pal = SD._paln(n=SD.ND, biv=SD.BIV_BO)
    lut = np.array([[mpl.colors.to_rgb(c) for c in row] for row in pal])
    ui = np.clip((np.clip(Uz, 0, 1) * SD.ND).astype(int), 0, SD.ND - 1)
    vi = np.clip((np.clip(Vz, 0, 1) * SD.ND).astype(int), 0, SD.ND - 1)
    rgb = lut[ui, vi]
    rgb[Dz > 1.2] = mpl.colors.to_rgb(SD.NODATA)

    regs = []
    for letter, name, names, box in REGIONS:
        keep, geom = _members(names, box)
        x0, y0, x1, y1 = geom.bounds
        pad = 0.04 * max(x1 - x0, y1 - y0)
        regs.append((letter, name, keep, geom, (x0 - pad, x1 + pad, y0 - pad, y1 + pad)))
        print(f"{letter} {name}: {len(keep)} members, extent {x0:.1f}..{x1:.1f} E, {y0:.1f}..{y1:.1f} N")

    W = 183.0
    gap = 5.0
    asp = [(e[1] - e[0]) / (e[3] - e[2]) for *_, e in regs]
    zh = (W - 2 * gap) / sum(asp)          # one height, widths follow each region's shape
    wh = W * 142 / 360
    lab = 10.0
    H = wh + lab + zh + 1.0
    fig = plt.figure(figsize=(W * MM, H * MM))

    # a: the world, as in the current Fig. 2
    ax = fig.add_axes([0, (H - wh) / H, 1, wh / H])
    _paint(ax, rgb, Uz, Vz, Dz)
    ax.set_xlim(-180, 180)
    ax.set_ylim(-58, 84)
    ax.axis("off")
    col, pal2, qc_lbl, qd_lbl = SD._classes8(df, biv=SD.BIV_BO)
    SD._key(ax, pal2, qc_lbl, qd_lbl, big=True)
    fig.text(0.0, 1.0, "a", fontsize=8, fontweight="bold", va="top", color=INK)

    # b-d: regional maps
    x = 0.0
    for k, (letter, name, keep, geom, (x0, x1, y0, y1)) in enumerate(regs):
        zw = zh * asp[k]
        rect = [x / W, 1.0 / H, zw / W, zh / H]
        x += zw + gap
        z = fig.add_axes(rect)
        SD._COUNTRIES.boundary.plot(ax=z, color=FAINT, linewidth=0.25, zorder=0.5)      # neighbours: outline only
        _paint(z, rgb, Uz, Vz, Dz, clip_geom=geom, s=2.2)
        gpd.GeoSeries(list(keep.values())).boundary.plot(ax=z, color="#1A1A1A", linewidth=0.22, zorder=3)
        gpd.GeoSeries([geom]).boundary.plot(ax=z, color=INK, linewidth=0.7, zorder=4)   # the region's outline
        z.set_xlim(x0, x1)
        z.set_ylim(y0, y1)
        z.set_anchor("S")
        z.axis("off")
        fig.text(rect[0], (1.0 + zh + 0.8) / H, letter, fontsize=8, fontweight="bold", color=INK, va="bottom")
        fig.text(rect[0] + 3.2 / W, (1.0 + zh + 0.8) / H, name, fontsize=7, color=INK, va="bottom")

    stem = FPP.OUT / "fig_sd_map_zoom"
    fig.savefig(str(stem) + ".pdf", bbox_inches="tight", dpi=600)
    fig.savefig(str(stem) + ".png", bbox_inches="tight", dpi=300)
    plt.close(fig)
    print("saved", stem, "height %.0f mm (world map %.0f mm, regions %.0f mm)" % (H, wh, zh))


if __name__ == "__main__":
    main()
