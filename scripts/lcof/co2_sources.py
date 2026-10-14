"""
co2_sources.py — facility-level CO2 sources from Climate TRACE, the input to
the CO2 feedstock price of every cell.

Reproduces the query of the earlier project (synfuels/cost/src/
download_real_data.py) so years can be compared like for like: the same
eleven subsectors, the same subsector capture costs, the same biogenic
flag, the same 50,000 t/yr cutoff. One change: the earlier run stopped each
subsector at 50 pages of 500; here paging continues until the API returns
nothing, and the manifest records whether the old limit would have cut the
list, so a 2024-vs-2025 difference can be told apart from a truncation.

Source: Climate TRACE API v7, /sources (https://api.climatetrace.org/v7),
annual emissions by asset. Full-year 2025 data released 26 February 2026.

From scripts/:  conda run -n synfuel python -u -m lcof.co2_sources 2025
Outputs: data/co2/climate_trace/co2_sources_climatetrace_<year>.csv
         data/co2/climate_trace/manifest_<year>.csv
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request

import pandas as pd

from . import inputs

OUT = inputs.PROJECT / "data" / "co2" / "climate_trace"
API = "https://api.climatetrace.org/v7/sources"
LIMIT, OLD_MAX_PAGES, MIN_T = 500, 50, 50_000

SUBSECTORS = ["cement", "lime", "chemicals", "other-chemicals",
              "petrochemical-steam-cracking", "oil-and-gas-refining",
              "electricity-generation", "iron-and-steel", "pulp-and-paper",
              "biological-treatment-of-solid-waste-and-biogenic",
              "industrial-wastewater-treatment-and-discharge"]
CAPTURE_COST = {"cement": 55.0, "lime": 50.0, "chemicals": 65.0,
                "other-chemicals": 75.0, "petrochemical-steam-cracking": 70.0,
                "oil-and-gas-refining": 65.0, "electricity-generation": 85.0,
                "iron-and-steel": 80.0, "pulp-and-paper": 70.0,
                "biological-treatment-of-solid-waste-and-biogenic": 45.0,
                "industrial-wastewater-treatment-and-discharge": 60.0}
BIOGENIC = {"biological-treatment-of-solid-waste-and-biogenic",
            "industrial-wastewater-treatment-and-discharge", "pulp-and-paper"}


def _get(params, tries=5):
    url = API + "?" + urllib.parse.urlencode(params)
    for k in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:                      # retry transient errors
            if k == tries - 1:
                raise RuntimeError(f"{url}: {e}")
            time.sleep(3 * (k + 1))


def fetch(year: int) -> pd.DataFrame:
    rows, manifest = [], []
    for sub in SUBSECTORS:
        offset, pages, n_raw, last_small = 0, 0, 0, None
        while True:
            data = _get({"year": year, "gas": "co2", "subsectors": sub,
                         "limit": LIMIT, "offset": offset})
            vals = data if isinstance(data, list) else (data or {}).get("value", [])
            if not vals:
                break
            pages += 1
            n_raw += len(vals)
            for it in vals:
                c = it.get("centroid") or {}
                q = it.get("emissionsQuantity")
                if c.get("latitude") is None or c.get("longitude") is None or q is None:
                    continue
                rows.append(dict(source_id=f"ct_{it.get('id')}",
                                 source_name=it.get("name", ""),
                                 lat=c["latitude"], lon=c["longitude"],
                                 country=it.get("country", ""),
                                 sector=it.get("sector", ""),
                                 subsector=it.get("subsector", sub),
                                 source_type=it.get("sourceType", ""),
                                 co2_t_per_year=q, year=it.get("year", year),
                                 capture_cost_usd_tco2=CAPTURE_COST[sub],
                                 carbon_type=("biogenic_or_mixed" if sub in BIOGENIC
                                              else "fossil_point_source")))
            if pages == OLD_MAX_PAGES:
                last_small = min(v.get("emissionsQuantity") or 0 for v in vals)
            if len(vals) < LIMIT:
                break
            offset += LIMIT
        manifest.append(dict(subsector=sub, pages=pages, records=n_raw,
                             old_limit_would_cut=pages > OLD_MAX_PAGES,
                             smallest_at_old_limit_t=last_small))
        print(f"  {sub:50s} {n_raw:7d} records, {pages:3d} pages", flush=True)
    df = pd.DataFrame(rows).drop_duplicates("source_id")
    kept = df[df.co2_t_per_year >= MIN_T].copy()
    OUT.mkdir(parents=True, exist_ok=True)
    kept.to_csv(OUT / f"co2_sources_climatetrace_{year}.csv", index=False)
    pd.DataFrame(manifest).to_csv(OUT / f"manifest_{year}.csv", index=False)
    print(f"{year}: {len(df)} unique sources, {len(kept)} at >= {MIN_T:,} t/yr")
    return kept


if __name__ == "__main__":
    fetch(int(sys.argv[1]) if len(sys.argv) > 1 else 2025)
