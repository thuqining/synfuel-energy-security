"""
fetch_supplier_mirror.py — audit of the top-supplier shares in vulnerability_inputs.csv
(2026-10-07): some reporters book part or all of an energy import against a confidential
pseudo-partner (Comtrade 899 "Areas, nes", 837 "Bunkers", 838 "Free zones", 839 "Special
categories"; Germany's gas and Israel's crude). hhi_for() then reads that placeholder as one
supplier. Here, for the core economies:

  screen   the reporter's own 2023 partner detail for crude (2709), refined (2710) and gas
           (2711); share of value on pseudo-partners
  mirror   where that share is >= 20 %: the exports every other reporter books TO the
           economy (flow X, partner = economy), 2023, as the partner distribution

Raw JSON is cached in data/cost/sources/comtrade_energy/. Writes
data/cost/supplier_shares_audit.csv (reported and mirror top share / HHI per code).

From scripts/:  python -m lcof.fetch_supplier_mirror
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd

from . import inputs
from .fetch_nitrogen_trade import _get
from .fetch_vulnerability import HS, resolve_reporters

RAW = inputs.MAPS / "sources" / "comtrade_energy"
PSEUDO = {899, 837, 838, 839, 0}
YEAR = 2023
API_R = ("https://comtradeapi.un.org/public/v1/preview/C/A/HS?period={y}&reporterCode={r}"
         "&cmdCode={c}&flowCode=M&partnerCode=&partner2Code=0&customsCode=C00&motCode=0")
API_X = ("https://comtradeapi.un.org/public/v1/preview/C/A/HS?period={y}&partnerCode={p}"
         "&cmdCode={c}&flowCode=X&partner2Code=0&customsCode=C00&motCode=0")


def _load(fn):
    with open(fn, encoding="utf-8") as fh:
        return json.load(fh).get("data", [])


def _shares(vals: dict) -> tuple[float, float, float]:
    tot = sum(vals.values())
    if tot <= 0:
        return np.nan, np.nan, 0.0
    sh = np.array(sorted(vals.values(), reverse=True)) / tot
    return float(sh[0]), float((sh ** 2).sum()), float(tot)


def main():
    from .coreset import CORE30_LIST
    RAW.mkdir(parents=True, exist_ok=True)
    names = [c if c != "United States" else "United States of America" for c in CORE30_LIST]
    codes = resolve_reporters(names)
    rows = []
    for name, rc in codes.items():
        for label, hs in HS.items():
            fn = RAW / f"rep_{rc}_{hs}_{YEAR}.json"
            if not fn.exists():
                _get(API_R.format(y=YEAR, r=rc, c=hs), fn)
                time.sleep(2)
            vals, pseudo = {}, 0.0
            for r in _load(fn) if fn.exists() else []:
                p, v = r.get("partnerCode"), r.get("primaryValue") or 0
                if p in (0, None) or v <= 0:
                    continue
                if p in PSEUDO:
                    pseudo += v
                vals[p] = vals.get(p, 0) + v
            top_r, hhi_r, tot_r = _shares(vals)
            real = {p: v for p, v in vals.items() if p not in PSEUDO}
            ps = pseudo / tot_r if tot_r > 0 else 0.0
            rec = dict(country=name, code=label, reported_bn=tot_r / 1e9, pseudo_share=ps,
                       top_reported=top_r, hhi_reported=hhi_r)
            if ps >= 0.20:
                fx = RAW / f"mir_{rc}_{hs}_{YEAR}.json"
                if not fx.exists():
                    _get(API_X.format(y=YEAR, p=rc, c=hs), fx)
                    time.sleep(2)
                mv = {}
                for r in _load(fx) if fx.exists() else []:
                    rep, v = r.get("reporterCode"), r.get("primaryValue") or 0
                    if rep in (None,) or v <= 0:
                        continue
                    mv[rep] = mv.get(rep, 0) + v
                top_m, hhi_m, tot_m = _shares(mv)
                top_partner = max(mv, key=mv.get) if mv else None
                rec.update(mirror_bn=tot_m / 1e9, top_mirror=top_m, hhi_mirror=hhi_m,
                           top_mirror_partner=top_partner)
            rows.append(rec)
            print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in rec.items()}, flush=True)
    out = pd.DataFrame(rows)
    out.to_csv(inputs.MAPS / "supplier_shares_audit.csv", index=False)
    print(out[out.pseudo_share >= 0.20].round(3).to_string())


if __name__ == "__main__":
    main()
