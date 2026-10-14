"""
fig_main_cities.py — MAIN-TEXT city figure: the 30 core cities (one
demand centre per core-30 economy) with cost, weather risk, market
risk, vulnerability and the security verdict in ONE composition.

Per row (one city):
  blue box   LCOH of firm hydrogen AT THE CITY'S OWN GRID CELL across the
             20 weather years -> the cost of building at the demand centre
             (median line) and its WEATHER risk (box width)
  grey box   the national fossil comparator across 247 months -> MARKET
             risk (box width)
  column V   the vulnerability index of the host economy
  column yr  the security-parity year of the host economy (ENTSOG anchor)

The six original case cities (Beijing, Berlin, Denver, Perth, Riyadh,
Tokyo) are kept; the other 24 are the largest demand centres of the
remaining core-30 economies. Rows are coloured by core-30 type.

From scripts/:  conda run -n synfuel python -u -m lcof.fig_main_cities
Output: cf_global_final/figures/pptx/fig_main_cities.(pdf|png)
        data/cost/core30_cities.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

mpl.use("Agg")

from . import inputs
from .fig_pptx_pairs import OUT, SUFFIX, YEARS
from .gap import country_gas_monthly, fossil_for_fuel
from .coreset import CORE30_LIST, CORE30_TYPE

KG = 0.12                      # $/GJ (LHV) -> $/kg H2 (120 MJ/kg)
TYPE_COL = {"large consumer": "#000000",
            "industrial importer": "#D55E00",
            "emerging importer": "#E69F00",
            "island state": "#56B4E9",
            "resource-rich builder": "#009E73"}

# one demand centre per core-30 economy (lon, lat)
CITIES = {
    "China": ("Beijing", 116.4, 39.9),
    "United States of America": ("Denver", -104.99, 39.74),
    "India": ("Mumbai", 72.88, 19.08),
    "Japan": ("Tokyo", 139.69, 35.69),
    "Germany": ("Berlin", 13.40, 52.52),
    "South Korea": ("Seoul", 126.98, 37.57),
    "Brazil": ("Sao Paulo", -46.63, -23.55),
    "Indonesia": ("Jakarta", 106.85, -6.21),
    "Italy": ("Milan", 9.19, 45.46),
    "Spain": ("Madrid", -3.70, 40.42),
    "Israel": ("Tel Aviv", 34.78, 32.08),
    "Netherlands": ("Rotterdam", 4.48, 51.92),
    "Poland": ("Warsaw", 21.01, 52.23),
    "United Kingdom": ("London", -0.13, 51.51),
    "Vietnam": ("Ho Chi Minh City", 106.63, 10.82),
    "Egypt": ("Cairo", 31.24, 30.04),
    "Pakistan": ("Karachi", 67.01, 24.86),
    "Kenya": ("Nairobi", 36.82, -1.29),
    "Philippines": ("Manila", 120.98, 14.60),
    "Sri Lanka": ("Colombo", 79.86, 6.93),
    "Dominican Republic": ("Santo Domingo", -69.93, 18.49),
    "Madagascar": ("Antananarivo", 47.52, -18.88),
    "Ireland": ("Dublin", -6.26, 53.35),
    "Chile": ("Santiago", -70.67, -33.45),
    "Morocco": ("Casablanca", -7.59, 33.57),
    "Australia": ("Perth", 115.86, -31.95),
    "Saudi Arabia": ("Riyadh", 46.68, 24.71),
    "South Africa": ("Johannesburg", 28.05, -26.20),
    "Norway": ("Oslo", 10.75, 59.91),
    "Oman": ("Muscat", 58.41, 23.59),
}
assert set(CITIES) == set(CORE30_LIST)

MM = 1 / 25.4
mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "DejaVu Sans"],
    "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8,
    "xtick.labelsize": 8, "ytick.labelsize": 8,
    "axes.linewidth": 0.5, "xtick.major.width": 0.5,
    "ytick.major.width": 0.5,
})
BLUE, GREY, ORANGE, PURPLE = "#0072B2", "#E69F00", "#D55E00", "#CC79A7"


def _box(ax, y, data, color, h=0.30, alpha=0.78):
    lo, q1, med, q3, hi = np.percentile(data, [2, 25, 50, 75, 98])
    ax.plot([lo, hi], [y, y], color=color, lw=0.8, zorder=2)
    ax.add_patch(plt.Rectangle((q1, y - h / 2), q3 - q1, h, fc=color,
                               ec="none", alpha=alpha, zorder=3))
    ax.plot([med, med], [y - h / 2, y + h / 2], color="white", lw=0.9,
            zorder=4)


def _nearest_cell(land: pd.DataFrame, lon: float, lat: float,
                  country: str, avail) -> int:
    """the land cell of `country` closest to (lon, lat); falls back to
    the country's cheapest cell when no cell of that country exists (very
    small islands)."""
    cc = land[(land.country == country) & land.index.isin(avail)]
    if not len(cc):
        return None
    d2 = (cc.lon - lon) ** 2 + (cc.lat - lat) ** 2
    return int(d2.idxmin())


def main():
    vuln = pd.read_csv(inputs.MAPS / "vulnerability_index.csv",
                       index_col=0)
    py = pd.read_csv(inputs.MAPS / "parity_years.csv").set_index("country")
    gasdf, g = country_gas_monthly()
    frames = {y: pd.read_csv(inputs.MAPS / f"lcoh_global_{y}{SUFFIX}.csv")
              .set_index("cell_id") for y in YEARS}
    meta = inputs.load_meta(2025)
    land = meta[meta.cell_type == "land"]
    avail = frames[YEARS[0]].index

    rows, rec = [], []
    for c in CORE30_LIST:
        city, lon, lat = CITIES[c]
        cid = _nearest_cell(land, lon, lat, c, avail)
        if cid is None or c not in gasdf.columns:
            print(f"  ! {city} ({c}): no cell/comparator — skipped")
            continue
        syn = np.array([frames[y].loc[cid, "lcoh_usd_gj"] for y in YEARS])
        fos = fossil_for_fuel("hydrogen", gasdf[c], g, c).dropna().to_numpy()
        V = float(vuln.V.get(c, np.nan))
        sp = float(py.sec.get(c, np.nan))
        rows.append((city, c, syn * KG, fos * KG, V, sp))
        rec.append(dict(country=c, city=city, lon=lon, lat=lat, cell_id=cid,
                        cell_lon=float(land.loc[cid, "lon"]),
                        cell_lat=float(land.loc[cid, "lat"]),
                        lcoh_med_usd_kg=float(np.median(syn) * KG),
                        lcoh_min_usd_kg=float(syn.min() * KG),
                        lcoh_max_usd_kg=float(syn.max() * KG),
                        fossil_med_usd_kg=float(np.median(fos) * KG),
                        V=V, sec_parity=sp, type=CORE30_TYPE[c]))
    pd.DataFrame(rec).to_csv(inputs.MAPS / "core30_cities.csv", index=False)
    rows.sort(key=lambda x: np.median(x[2]))

    n = len(rows)
    fig, ax = plt.subplots(figsize=(183 * MM, (30 + 5.0 * n) * MM))
    for i, (city, c, syn, fos, V, sp) in enumerate(rows):
        _box(ax, i + 0.18, fos, GREY, alpha=0.55)
        _box(ax, i - 0.18, syn, BLUE)
        ax.scatter(-0.13, i, marker="s", s=13,
                   color=TYPE_COL[CORE30_TYPE[c]], clip_on=False, zorder=5)
        if np.isfinite(V):
            ax.text(13.35, i, f"{V:.2f}" if V > 0 else "0",
                    fontsize=8, va="center", ha="center",
                    color=PURPLE if V > 0.3 else "#777777",
                    fontweight="bold" if V > 0.3 else "normal")
        else:
            ax.text(13.35, i, "–", fontsize=8, va="center", ha="center",
                    color="#AAAAAA")
        lab = f"{sp:.0f}" if np.isfinite(sp) and sp < 2051 else "> 2050"
        ax.text(14.75, i, lab, fontsize=8, va="center", ha="center",
                color=ORANGE if np.isfinite(sp) and sp < 2051 else "#AAAAAA",
                fontweight="bold" if np.isfinite(sp) and sp <= 2030
                else "normal")
    ax.text(13.35, n - 0.1, "risk\n$V$", fontsize=8, ha="center",
            va="bottom", color=PURPLE, fontweight="bold")
    ax.text(14.75, n - 0.1, "security\nparity", fontsize=8, ha="center",
            va="bottom", color=ORANGE, fontweight="bold")

    ax.set_yticks(range(n))
    ax.set_yticklabels([r[0] for r in rows])
    ax.set_xlim(0, 15.3)
    ax.set_ylim(-0.8, n + 1.3)
    ax.axvline(12.7, color="#DDDDDD", lw=0.5)
    ax.set_xticks([0, 2, 4, 6, 8, 10, 12])
    ax.set_xlabel("hydrogen at the city's own grid cell, \\$/kg (LHV)")
    ax.tick_params(axis="y", pad=9)
    import matplotlib.patches as mp
    ax.legend(handles=[
        mp.Patch(color=BLUE, alpha=0.78,
                 label="build — climate variability (box width)"),
        mp.Patch(color=GREY, alpha=0.55,
                 label="buy — market variability (box width)")],
        loc="lower right", bbox_to_anchor=(0.845, 0.005), fontsize=8,
        frameon=False, handlelength=1.1)
    fig.legend(handles=[mp.Patch(color=v, label=k)
                        for k, v in TYPE_COL.items()],
               loc="lower center", bbox_to_anchor=(0.5, -0.008), ncol=5,
               fontsize=8, frameon=False, handlelength=1.0,
               columnspacing=1.1, title="core-30 type", title_fontsize=8)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(direction="out", length=2.5)
    ax.set_axisbelow(True)
    ax.grid(axis="x", alpha=0.22, lw=0.4)

    fig.savefig(OUT / "fig_main_cities.pdf", bbox_inches="tight")
    fig.savefig(OUT / "fig_main_cities.png", dpi=600, bbox_inches="tight")
    plt.close(fig)
    print(f"saved fig_main_cities.(pdf|png), {n} core cities; "
          f"core30_cities.csv")


if __name__ == "__main__":
    main()
