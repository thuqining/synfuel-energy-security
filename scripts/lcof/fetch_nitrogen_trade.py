"""
fetch_nitrogen_trade.py -- UN Comtrade trade in ammonia and nitrogen fertilizers,
2023-2025, for the nitrogen balance of nitrogen_consumption.py (2026-10-07).

Reporter totals (partner World) for every HS code in N_CONTENT, imports and
exports, each year; and, for the producers that report no exports in a year,
the mirror flows (imports their partners report from them). Raw JSON goes to
data/demand/usgs/nitrogen/. Uses the public preview API (500 records a call),
one code at a time for totals and three code groups at a time for mirrors.

From scripts/:  python -m lcof.fetch_nitrogen_trade [totals|mirror]
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request

from . import inputs

OUT = inputs.PROJECT / "data" / "demand" / "usgs" / "nitrogen"
API = ("https://comtradeapi.un.org/public/v1/preview/C/A/HS?period={y}&cmdCode={c}"
       "&flowCode={f}&partnerCode={p}&includeDesc=true")
YEARS = (2025, 2024, 2023)

# nitrogen mass fraction of each traded product (t N per t product). Standard nutrient
# contents (FAO, Fertilizers by Product / IFA statistics conventions); for the mixed
# headings the typical grade is used.
N_CONTENT = {
    "281410": 14.0 / 17.0,   # anhydrous ammonia
    "281420": 0.25 * 14.0 / 17.0,   # ammonia in aqueous solution, ~25% NH3
    "310210": 0.46,          # urea
    "310221": 0.21,          # ammonium sulphate
    "310229": 0.26,          # double salts / mixtures of ammonium sulphate and nitrate
    "310230": 0.34,          # ammonium nitrate (fertilizer and technical grade)
    "310240": 0.27,          # ammonium nitrate with calcium carbonate (CAN)
    "310250": 0.16,          # sodium nitrate
    "310260": 0.155,         # calcium nitrate / ammonium nitrate double salts
    "310280": 0.30,          # urea-ammonium nitrate solutions (28-32% N)
    "310290": 0.25,          # other nitrogenous fertilizers and mixtures
    "310520": 0.15,          # NPK compounds
    "310530": 0.18,          # diammonium phosphate (DAP, 18-46-0)
    "310540": 0.11,          # monoammonium phosphate (MAP, 11-52-0)
    "310551": 0.20,          # NP fertilizers containing nitrates and phosphates
    "310559": 0.18,          # other NP fertilizers (e.g. 16-20-0)
    "310590": 0.10,          # other compound fertilizers with nitrogen (NK etc.)
}
MIRROR_GROUPS = [["281410", "281420", "310210"], ["310221", "310229", "310230", "310240", "310250", "310260"],
                 ["310280", "310290", "310520", "310530", "310540", "310551", "310559", "310590"]]


def _get(url: str, fn) -> int | None:
    """fetch one preview call; waits out the hourly call quota (HTTP 403) instead of
    counting it as a failure"""
    import re
    import urllib.error
    tries = 0
    while tries < 8:
        try:
            raw = urllib.request.urlopen(url, timeout=90).read()
            d = json.loads(raw)
            if "data" in d:
                fn.write_bytes(raw)
                return len(d["data"])
            tries += 1
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "ignore")
            m = re.search(r"replenished in (\d+):(\d+):(\d+)", body)
            if e.code == 403 and m:
                wait = int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3]) + 30
                print(f"  quota: waiting {wait // 60} min", flush=True)
                time.sleep(wait)
                continue
            tries += 1
        except Exception:
            tries += 1
        time.sleep(10)
    return None


def totals():
    OUT.mkdir(parents=True, exist_ok=True)
    for y in YEARS:
        for c in N_CONTENT:
            for f in "MX":
                fn = OUT / f"tot_{c}_{y}_{f}.json"
                if fn.exists():
                    continue
                n = _get(API.format(y=y, c=c, f=f, p=0), fn)
                print(y, c, f, n, flush=True)
                if n is not None and n >= 500:
                    print("  WARNING: 500-record cap reached", flush=True)
                time.sleep(2)


def mirror(codes: dict[str, int]):
    """codes: exporter name -> Comtrade partner code"""
    OUT.mkdir(parents=True, exist_ok=True)
    for name, pc in codes.items():
        for y in YEARS:
            for k, grp in enumerate(MIRROR_GROUPS):
                fn = OUT / f"mir_{name}_{y}_{k}.json"
                if fn.exists():
                    continue
                n = _get(API.format(y=y, c=",".join(grp), f="M", p=pc), fn)
                print(name, y, k, n, flush=True)
                if n is not None and n >= 500:
                    print("  WARNING: 500-record cap reached", flush=True)
                time.sleep(2)


PARTNER_GROUPS = [["281410", "281420"], ["310210"], ["310221", "310229", "310230", "310240"],
                  ["310250", "310260", "310280", "310290"], ["310520", "310590"],
                  ["310530", "310540", "310551", "310559"]]
API_P = ("https://comtradeapi.un.org/public/v1/preview/C/A/HS?period={y}&reporterCode={r}"
         "&cmdCode={c}&flowCode=M&includeDesc=true")


def partners():
    """partner-level imports of every reporter, in its latest reported import year,
    for the supplier concentration of the nitrogen chain"""
    from .nitrogen_consumption import latest, _load
    d = _load("M")
    yr = d.groupby("reporter").year.max()
    codes = {}
    for y in YEARS:
        for c in N_CONTENT:
            f = OUT / f"tot_{c}_{y}_M.json"
            if f.exists():
                for x in json.load(open(f, encoding="utf-8"))["data"]:
                    codes[x["reporterDesc"]] = x["reporterCode"]
    from .ammonia_consumption import _name
    rc = {}
    for desc, code in codes.items():
        rc[_name(desc)] = code
    from .coreset import CORE30_LIST
    order = [c for c in CORE30_LIST if c in yr.index] + [c for c in yr.index if c not in CORE30_LIST]
    allc = ",".join(N_CONTENT)
    for rep in order:
        if rep not in rc:
            continue
        y = int(yr[rep])
        fn = OUT / f"par_{rc[rep]}_{y}_all.json"
        if fn.exists() or any(OUT.glob(f"par_{rc[rep]}_{y}_g*.json")):
            continue
        n = _get(API_P.format(y=y, r=rc[rep], c=allc), fn)
        if n is not None and n >= 500:
            fn.unlink()
            print(f"  cap {rep}: by group", flush=True)
            for k, grp in enumerate(PARTNER_GROUPS):
                _get(API_P.format(y=y, r=rc[rep], c=",".join(grp)), OUT / f"par_{rc[rep]}_{y}_g{k}.json")
                time.sleep(2)
        print(rep, y, n, flush=True)
        time.sleep(2)


if __name__ == "__main__":
    if sys.argv[1] == "totals":
        totals()
    elif sys.argv[1] == "partners":
        partners()
    elif sys.argv[1] == "mirror":
        from .nitrogen_consumption import MIRROR, latest
        _, yx = latest("X")
        mirror({c: k for c, k in MIRROR.items() if c not in yx.index or yx[c] < 2025})
