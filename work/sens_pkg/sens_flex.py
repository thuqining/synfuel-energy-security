"""
sens_flex.py — optimization-based sensitivity runs at 2025 central costs (2026-10-09).
Same linear programme as the main runs (dyn_worker.solve, flexible synthesis), every land cell
at its median weather year (sens_inputs.npz). Variants:

  base            minimum load 60 %, ramp 5 %/h (the main case)
  min00..min100   minimum load 0, 20, 40, 80, 100 % (100 % = constant load), ramp 5 %/h
  ramp01..ramp100 ramp 1, 2, 10, 20 %/h and unlimited, minimum load 60 %
  <item>_x0.7 / _x1.3   one capital cost scaled (pv, wind, ez, tank, battery, syn), plant re-optimized
  eta_x1.1 / eta_x0.9   electrolyser efficiency scaled
  all_x0.6        every hydrogen-system capital cost x 0.6
  offshore        coastal cells only: wind at fixed-bottom offshore wind cost

Outputs out/<variant>/part_<chunk>.csv (50 chunks of cells); finished chunks are skipped.

  python sens_flex.py --profiles          # once: extract median-year profiles from years/
  python sens_flex.py --test              # one cell, prints solver and seconds
  python sens_flex.py --groups flex --workers 24
  python sens_flex.py --groups drivers,offshore --workers 100
Groups: base, flex, drivers, offshore, all.  At the end: results_sens_<groups>_<time>.zip
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time
import zipfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
NCHUNK = 50
CAP = ("Cpv", "Cw", "Cez", "Chs", "Cbp", "Cbe")
SCALE_KEYS = {"pv": ("Cpv",), "wind": ("Cw",), "ez": ("Cez",), "tank": ("Chs",),
              "battery": ("Cbp", "Cbe"), "syn": ("syn",)}


def variants():
    v = {"base": dict(group="base")}
    for m in (0.0, 0.2, 0.4, 0.8, 1.0):
        v[f"min{int(round(m * 100)):02d}"] = dict(group="flex", min_load=m)
    for r in (0.01, 0.02, 0.10, 0.20, 1.0):
        v[f"ramp{int(round(r * 100)):02d}"] = dict(group="flex", ramp=r)
    for k in SCALE_KEYS:
        for s in (0.7, 1.3):
            v[f"{k}_x{s}"] = dict(group="drivers", scale={k: s})
    for s in (1.1, 0.9):
        v[f"eta_x{s}"] = dict(group="drivers", eta=s)
    v["all_x0.6"] = dict(group="drivers", scale={k: 0.6 for k in ("pv", "wind", "ez", "tank", "battery")})
    v["offshore"] = dict(group="offshore", offshore=True)
    return v


G = {}


def _init(solver):
    sys.path.insert(0, str(HERE))
    import dyn_worker as dw
    if solver == "gurobi":
        dw.SOLVER.update(name="gurobi", method=2, crossover=0, threads=1)
    else:
        dw.SOLVER.update(name="highs")
    G["dw"] = dw
    G["c"] = np.load(HERE / "costs.npz", allow_pickle=True)
    G["s"] = np.load(HERE / "sens_inputs.npz")
    G["p"] = np.load(HERE / "sens_profiles.npz")


def _cells(name, spec, chunk):
    s = np.load(HERE / "sens_inputs.npz")
    idx = np.arange(chunk, len(s["cell_id"]), NCHUNK)
    if spec.get("offshore"):
        idx = idx[s["coastal"][idx]]
    return idx


def _solve_chunk(name, spec, chunk, path):
    dw, c, s, p = G["dw"], G["c"], G["s"], G["p"]
    K0 = dict(c["K"].item())
    K = dict(K0, eta_syn=K0["eta_syn_by_fuel"]["ammonia"])
    K["eta_el"] = K0["eta_el"] * spec.get("eta", 1.0)
    win = (spec.get("min_load", 0.60), spec.get("ramp", 0.05))
    rows = []
    for i in _cells(name, spec, chunk):
        a = {k: float(c[k][i]) for k in CAP + ("water",)}
        a["syn"] = float(c["syn_ammonia"][i])
        for key, f in spec.get("scale", {}).items():
            for k in SCALE_KEYS[key]:
                a[k] *= f
        if spec.get("offshore"):
            a["Cw"] = float(s["cw_offshore"][i])
        cf = lambda x: x.astype(float) / 65535.0 if x.dtype == np.uint16 else x.astype(float)
        t0 = time.time()
        r = dw.solve(cf(p["pv"][i]), cf(p["wind"][i]), a, K, eff="const", syn=win)
        out = dict(cell_id=int(s["cell_id"][i]), year=int(s["med_year"][i]), variant=name)
        if r is None:
            out["status"] = "fail"
        else:
            out.update({k: float(v) for k, v in r.items()})
        out["solver"] = dw.SOLVER["name"]
        out["sec"] = time.time() - t0
        rows.append(out)
    keys = []
    for r in rows:
        keys += [k for k in r if k not in keys]
    tmp = str(path) + ".tmp"
    with open(tmp, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, path)
    return name, chunk, len(rows), sum(r["sec"] for r in rows)


def _complete(path, n):
    if not path.exists():
        return False
    with open(path) as fh:
        return sum(1 for _ in fh) - 1 == n


def extract_profiles():
    s = np.load(HERE / "sens_inputs.npz")
    cells, years = s["cell_id"], s["med_year"]
    pv = wind = None
    for y in sorted(set(years.tolist())):
        z = np.load(HERE / "years" / f"cells_{y}.npz")
        assert (z["cell_id"] == cells).all()
        if pv is None:
            pv = np.zeros((len(cells), z["pv"].shape[1]), dtype=z["pv"].dtype)
            wind = np.zeros_like(pv)
        m = years == y
        pv[m], wind[m] = z["pv"][m], z["wind"][m]
        print(f"weather year {y}: {int(m.sum())} cells", flush=True)
    np.savez_compressed(HERE / "sens_profiles.npz", pv=pv, wind=wind)
    print("wrote sens_profiles.npz")


def solver_name():
    try:
        import gurobipy as gp
        m = gp.Model()
        m.Params.OutputFlag = 0
        m.addVar()
        m.optimize()
        return "gurobi"
    except Exception as ex:
        print(f"Gurobi not usable ({ex.__class__.__name__}); using HiGHS", flush=True)
        return "highs"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles", action="store_true")
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--groups", default="all")
    ap.add_argument("--variants", default=None, help="comma list of variant names (overrides --groups)")
    ap.add_argument("--tasks", default=None, help="lo-hi slice of the (variant, chunk) list, for cluster arrays")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 8) - 8))
    a = ap.parse_args()
    if a.profiles:
        extract_profiles()
        return
    solver = solver_name()
    print(f"solver: {solver}", flush=True)
    V = variants()
    if a.test:
        _init(solver)
        t0 = time.time()
        r = G["dw"].solve(*(G["p"][k][0].astype(float) / 65535.0 for k in ("pv", "wind")),
                          {**{k: float(G["c"][k][0]) for k in CAP + ("water",)}, "syn": float(G["c"]["syn_ammonia"][0])},
                          dict(G["c"]["K"].item(), eta_syn=G["c"]["K"].item()["eta_syn_by_fuel"]["ammonia"]),
                          eff="const", syn=(0.6, 0.05))
        print(f"test: one LP in {time.time() - t0:.0f} s, LCOH {r['lcoh']:.3f} US$/GJ")
        return
    groups = set(a.groups.split(","))
    names = [n for n, sp in V.items() if "all" in groups or sp["group"] in groups]
    if a.variants:
        names = [n for n in a.variants.split(",") if n in V]
    todo = []
    allt = [(n, ch) for n in names for ch in range(NCHUNK)]
    if a.tasks:
        lo, hi = (int(x) for x in a.tasks.split("-"))
        allt = allt[lo:hi + 1]
    for n in names:
        (HERE / "out" / n).mkdir(parents=True, exist_ok=True)
        for ch in range(NCHUNK):
            path = HERE / "out" / n / f"part_{ch:03d}.csv"
            if (n, ch) in allt and not _complete(path, len(_cells(n, V[n], ch))):
                todo.append((n, ch, path))
    print(f"{len(names)} variants, {len(todo)} chunks to run with {a.workers} workers", flush=True)
    t0, done, secs = time.time(), 0, []
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_init, initargs=(solver,)) as ex:
        futs = [ex.submit(_solve_chunk, n, V[n], ch, path) for n, ch, path in todo]
        for f in as_completed(futs):
            n, ch, k, s = f.result()
            done += 1
            secs.append(time.time() - t0)
            el = (time.time() - t0) / 3600
            eta = el / done * (len(todo) - done) if done else float("nan")
            print(f"{time.strftime('%H:%M')} {n} chunk {ch} ({k} cells) | {done}/{len(todo)} in {el:.2f} h, "
                  f"about {eta:.1f} h left", flush=True)
    if a.tasks:
        return                      # cluster array task: no zip
    z = HERE / f"results_sens_{(a.variants or a.groups).replace(',', '+')[:40]}_{time.strftime('%Y%m%d_%H%M')}.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for n in names:
            for p in sorted((HERE / "out" / n).glob("part_*.csv")):
                zf.write(p, p.relative_to(HERE))
    print(f"results zipped to {z.name} - copy this file back", flush=True)


if __name__ == "__main__":
    main()
