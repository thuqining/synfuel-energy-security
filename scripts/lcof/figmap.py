"""
figmap.py — the world-map panel of the main-text Figs 3-5 (2026-10-21), in the style of Fig. 2 (fig_sd_map): full width,
the same map extent, mid-gray 0.1 pt borders, economies outside the 139 modelled left blank, and the key on the open
South Pacific at the lower left.
"""
import geopandas as gpd
import pandas as pd
from matplotlib.patches import Patch

from lcof import inputs


def draw(sf, cat, colors, labels, title=None, rect=(0.0, 0.0, 1.0, 1.0), legend=True, ylim=(-58, 84)):
    """cat: {model country name: class}; colors and labels: {class: colour / key text}, in key order.
    2026-10-21: no key title (the caption names the 139 economies); rect places the map in the subfigure."""
    ne = gpd.read_file(inputs.PROJECT / "data" / "grid" / "naturalearth" / "ne_10m_admin_0_countries.shp")[
        ["ADMIN", "geometry"]]
    ne = ne[ne.ADMIN != "Antarctica"]
    # 2026-10-22: borders simplified to 0.05 degrees (about 5 km), invisible at print size; keeps the PDF small
    ne["geometry"] = ne.geometry.simplify(0.05, preserve_topology=True)
    missing = sorted(set(cat) - set(ne.ADMIN))
    assert not missing, missing
    ne["cat"] = ne.ADMIN.map(cat)
    ax = sf.add_axes(list(rect))
    for k, col in colors.items():
        sub = ne[ne.cat == k]
        if len(sub):
            sub.plot(ax=ax, color=col, linewidth=0)
    ne.boundary.plot(ax=ax, color="0.4", linewidth=0.1)
    ax.set_xlim(-180, 180)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.axis("off")
    counts = pd.Series(cat).value_counts()
    hd = [Patch(fc=colors[k], ec="none", label=f"{labels[k]} ({int(counts.get(k, 0))})") for k in colors]
    if legend:
        ax.legend(handles=hd, loc="lower left", bbox_to_anchor=(0.005, 0.03), fontsize=7.0, frameon=False,
                  handlelength=1.5, handleheight=1.0, labelspacing=0.45, borderaxespad=0.0, alignment="left")
    return ax, hd
