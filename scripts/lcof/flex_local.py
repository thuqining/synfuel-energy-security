"""
flex_local.py — run the 20-weather-year flexible-synthesis LP on this PC with
Gurobi (barrier, no crossover, 1 thread per process), in parallel processes.

Same LP (dyn_worker.solve), same inputs (costs_<year>.npz of flex_prepare_lowest)
and the same output files as the cluster job (flex_worker.py --years, nchunk 50):
<outdir>/out/part_<weather year>_<chunk>.csv, so both are collected the same way.
A part that already exists with all its cells is skipped, so the run resumes.

Gurobi barrier without crossover reproduced HiGHS to 4 decimals of LCOH on test
cells (2026-10-07) at ~5 s per LP instead of ~60 s.

From scripts/:  python -m lcof.flex_local <costs_npz> <outdir> [workers] [years]
"""
from __future__ import annotations

import csv
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

YEARS = list(range(2006, 2026))
NCHUNK = 50
TAG, FUEL, WINDOW = "flex60", "ammonia", (0.60, 0.05)
SYS = ("Cpv", "Cw", "Cez", "Chs", "Cbp", "Cbe", "water")


def _init():
    sys.path.insert(0, str(Path(__file__).parent))
    import dyn_worker as dw
    # 2026-10-13: LCOF_SOLVER=highs selects the free solver (dyn_worker also falls back to HiGHS when no
    # Gurobi licence is found); Gurobi barrier without crossover is the default used for the paper
    if os.environ.get("LCOF_SOLVER", "gurobi").lower() == "highs":
        dw.SOLVER.update(name="highs")
    else:
        dw.SOLVER.update(name="gurobi", method=2, crossover=0, threads=1)


def _solve_chunk(path, year, cells, pv, wind, costs, syn, K):
    import dyn_worker as dw
    rows = []
    for j, c in enumerate(cells):
        tc = time.time()
        a = dict({k: float(costs[k][j]) for k in SYS}, syn=float(syn[j]))
        r = dw.solve(pv[j], wind[j], a, dict(K, eta_syn=K["eta_syn_by_fuel"][FUEL]), eff="const", syn=WINDOW)
        out = dict(cell_id=int(c), year=int(year))
        if r is None:
            out[f"status_{FUEL}"] = "fail"
        else:
            out.update({f"{k}_{TAG}_{FUEL}": float(v) for k, v in r.items()})
        out["solver"] = "gurobi-m2c0t1"
        out["sec"] = time.time() - tc
        rows.append(out)
    keys = []
    for r in rows:
        keys += [k for k in r if k not in keys]
    tmp = path + ".tmp"
    with open(tmp, "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=keys)
        wr.writeheader()
        wr.writerows(rows)
    os.replace(tmp, path)
    return path, len(rows), sum(r["sec"] for r in rows)


def main(costs_npz, outdir, workers="24", years=None, tasks=None):
    """tasks: optional "lo-hi" range of cluster task ids (task = weather-year index x 50 + chunk),
    so a block of a cluster array can be taken over here without overlap (2026-10-08)"""
    from . import inputs
    out = Path(outdir) / "out"
    out.mkdir(parents=True, exist_ok=True)
    d = np.load(costs_npz, allow_pickle=True)
    cells = d["cell_id"]
    K = dict(d["K"].item())
    meta = inputs.load_meta(2025).reindex(cells)
    track = meta.pv_mode.astype(str).str.startswith("track").to_numpy()
    yrs = [int(y) for y in years.split(",")] if years else YEARS
    t0, done, cpu = time.time(), 0, 0.0
    with ProcessPoolExecutor(max_workers=int(workers), initializer=_init) as ex:
        for y in yrs:
            todo = []
            for ch in range(NCHUNK):
                if tasks:
                    lo, hi = (int(x) for x in tasks.split("-"))
                    if not lo <= YEARS.index(y) * NCHUNK + ch <= hi:
                        continue
                idx = np.arange(ch, len(cells), NCHUNK)
                path = str(out / f"part_{y}_{ch:03d}.csv")
                if os.path.exists(path):
                    with open(path) as fh:
                        if sum(1 for _ in fh) - 1 == len(idx):
                            continue
                todo.append((ch, idx, path))
            if not todo:
                continue
            ds = inputs.open_year(y)
            col = {int(c): i for i, c in enumerate(ds.cell_id.values)}
            ix = np.array([col[int(c)] for c in cells])
            wind = np.clip(np.nan_to_num(ds.wind_onshore_cf.values[:8760, ix].astype("float64")), 0, 1).T
            pvf = ds.pv_fixed_cf.values[:8760, ix].astype("float64")
            pvt = ds.pv_track_cf.values[:8760, ix].astype("float64")
            ds.close()
            pv = np.clip(np.nan_to_num(np.where(track[None, :], pvt, pvf)), 0, 1).T
            del pvf, pvt
            futs = [ex.submit(_solve_chunk, path, y, cells[idx], pv[idx], wind[idx],
                              {k: d[k][idx] for k in SYS}, d[f"syn_{FUEL}"][idx], K)
                    for ch, idx, path in todo]
            for f in as_completed(futs):
                p, n, s = f.result()
                done += n
                cpu += s
                el = (time.time() - t0) / 3600
                print(f"{time.strftime('%H:%M')} weather {y}: {os.path.basename(p)} ({n} cells) | "
                      f"{done} cell-years in {el:.2f} h, {cpu/max(done,1):.1f} s/LP", flush=True)
    print(f"ALL DONE {done} cell-years in {(time.time()-t0)/3600:.2f} h", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
