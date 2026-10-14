"""
co2_feedstock.py — the CO2 feedstock price of every land cell, from
facility-level Climate TRACE sources.

Per cell i, over every allowed source s within MAX_KM (1,000 km) of the cell centre:
    price_i = min( capture_cost_s + distance(i, s) / 100 km * transport,
                   direct-air-capture price )
with the subsector capture costs of co2_sources.py and $6 per tonne per
100 km. This is the rule of the earlier project, with two corrections:

  * the direct-air-capture ceiling is the cascade's own price
    (params.C_CO2_DAC, $500/t), not the $180 the earlier run used. Under a
    $180 ceiling every cell whose cheapest source cost $180-500 fell back
    to capture and was later relabelled $500, although a real source was
    cheaper than that.
  * prices are computed at the model's own land-cell centres. The earlier
    search grid stopped at 72.5 N, so every land cell north of it took the
    fallback regardless of the sources near it.

2026-10-05 (author): sources are reachable only within MAX_KM = 1,000 km of the
cell centre. Beyond it a cell has no point source and buys direct air capture.
Before this, any distance was allowed at $6/t per 100 km, so even a cell
2,400 km from the nearest source took a fossil source (at about $200/t), and
direct air capture was never the cheapest option.

From scripts/:  conda run -n synfuel python -u -m lcof.co2_feedstock <sources.csv> <out.csv> [year] [--neutral]
(--neutral: biogenic sources only, i.e. the climate-neutral layer)
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from . import inputs, params as P

TRANSPORT_PER_100KM = 6.0
MAX_KM = 1000.0          # 2026-10-05: largest distance a cell may buy point-source CO2 from
R_EARTH = 6371.0


def _haversine(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1)[:, None], np.radians(lat2)[None, :]
    dp = p2 - p1
    dl = np.radians(lon2)[None, :] - np.radians(lon1)[:, None]
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * R_EARTH * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def build(sources: pd.DataFrame, dac: float = P.C_CO2_DAC,
          allowed=("fossil_point_source", "biogenic_or_mixed"),
          max_km: float = MAX_KM) -> pd.DataFrame:
    meta = inputs.load_meta(2025)
    land = meta[meta.cell_type == "land"]
    src = sources[sources.carbon_type.isin(allowed)].reset_index(drop=True)
    slat, slon = src.lat.to_numpy(float), src.lon.to_numpy(float)
    cap = src.capture_cost_usd_tco2.to_numpy(float)
    out = []
    for a in range(0, len(land), 256):
        g = land.iloc[a:a + 256]
        d = _haversine(g.lat.to_numpy(float), g.lon.to_numpy(float), slat, slon)
        tot = cap[None, :] + d / 100.0 * TRANSPORT_PER_100KM
        tot = np.where(d <= max_km, tot, np.inf)          # out of reach
        j = tot.argmin(axis=1)
        best = tot[np.arange(len(g)), j]
        for k, cid in enumerate(g.index):
            if best[k] >= dac:
                out.append((cid, dac, "DAC", None, np.nan))
            else:
                s = src.iloc[j[k]]
                path = "biogenic" if s.carbon_type == "biogenic_or_mixed" else "industrial"
                out.append((cid, float(best[k]), path, s.source_id, float(d[k, j[k]])))
    df = pd.DataFrame(out, columns=["cell_id", "co2_cost", "pathway", "source_id", "distance_km"])
    df = df.set_index("cell_id").join(land[["lon", "lat", "country"]])
    df["scenario"] = "short_term"
    return df.reset_index()[["cell_id", "lon", "lat", "country", "co2_cost",
                             "pathway", "scenario", "source_id", "distance_km"]]


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    srcs = pd.read_csv(args[0])
    res = build(srcs, allowed=("biogenic_or_mixed",)) if "--neutral" in sys.argv else build(srcs)
    if len(args) > 2:
        res["source_year"] = int(args[2])
    res.to_csv(args[1], index=False)
    print(f"{len(res)} land cells; pathway: {res.pathway.value_counts().to_dict()}; "
          f"median ${res.co2_cost.median():.0f}/t")
