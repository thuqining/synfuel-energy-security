"""
flex_worker.py — cluster worker for the fuel-specific flexible-synthesis run
(numpy + scipy only). Uses the LP of dyn_worker.solve with the synthesis
window (minimum load, ramp) and each fuel's own synthesis annuity.

Run locally for a check:  python flex_worker.py --npz cells.npz --only 0
"""
import argparse
import csv
import os
import sys
import time

import numpy as np

import dyn_worker as dw

FUELS = ["ammonia", "methanol", "e-methane", "e-diesel", "ethanol"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz", default="cells.npz")
    ap.add_argument("--only", type=int, default=None)
    ap.add_argument("--min-load", type=float, default=0.60)
    ap.add_argument("--ramp", type=float, default=0.05)
    ap.add_argument("--fuels", default=",".join(FUELS))
    ap.add_argument("--tag", default="flex60")
    ap.add_argument("--solver", default="highs")
    ap.add_argument("--grb-method", type=int, default=None)
    ap.add_argument("--grb-crossover", type=int, default=None)
    ap.add_argument("--grb-threads", type=int, default=1)
    # multi-year mode: task -> (weather year, chunk of cells)
    ap.add_argument("--years", default=None, help="comma list; profiles in years/cells_<y>.npz")
    ap.add_argument("--costs", default="costs.npz")
    ap.add_argument("--nchunk", type=int, default=50)
    ap.add_argument("--base", action="store_true", help="also solve the constant-load LP")
    ap.add_argument("--syn-mult", type=float, default=1.0, help="scale the synthesis annuity (degradation test)")
    ap.add_argument("--outdir", default="out")
    # 2026-09-26 sensitivity: scale annuities (e.g. "Cpv=0.7,Cbp=0.7,Cbe=0.7";
    # "all" = every hydrogen-system annuity) and the electrolyser efficiency
    ap.add_argument("--scale", default="", help="comma list key=mult")
    ap.add_argument("--eta-el-mult", type=float, default=1.0)
    ap.add_argument("--sample", default=None, help="file of cell indices to solve")
    args = ap.parse_args()
    dw.SOLVER.update(name=args.solver, method=args.grb_method, crossover=args.grb_crossover,
                     threads=args.grb_threads)
    print(f"python {sys.executable}, numpy {np.__version__}, window "
          f"{args.min_load:.2f}/{args.ramp:.2f}", flush=True)
    task = int(os.environ.get("SLURM_ARRAY_TASK_ID", 0))
    if args.years:
        years = [int(y) for y in args.years.split(",")]
        yr, chunk = years[task // args.nchunk], task % args.nchunk
        d = np.load(args.costs, allow_pickle=True)
        prof = np.load(f"years/cells_{yr}.npz")
        assert (prof["cell_id"] == d["cell_id"]).all()
        cells = d["cell_id"]
        idx = [args.only] if args.only is not None else list(range(chunk, len(cells), args.nchunk))
        tag_task = f"{yr}_{chunk:03d}"
    else:
        d = prof = np.load(args.npz, allow_pickle=True)
        cells = d["cell_id"]
        ntask = int(os.environ.get("SLURM_ARRAY_TASK_COUNT", 1))
        pool = (np.loadtxt(args.sample, dtype=int).tolist() if args.sample
                else list(range(len(cells))))
        idx = [args.only] if args.only is not None else pool[task::ntask]
        tag_task = f"{task:03d}"
    K0 = dict(d["K"].item())
    K0["eta_el"] = K0["eta_el"] * args.eta_el_mult
    fuels = [f for f in args.fuels.split(",") if f]
    SYS = ("Cpv", "Cw", "Cez", "Chs", "Cbp", "Cbe")
    mult = {}
    for kv in [x for x in args.scale.split(",") if x]:
        k, v = kv.split("=")
        for kk in (SYS if k == "all" else (k,)):
            mult[kk] = mult.get(kk, 1.0) * float(v)

    def cf(x):
        x = np.asarray(x)
        return x.astype(float) / 65535.0 if x.dtype == np.uint16 else x.astype(float)
    rows, t0 = [], time.time()
    os.makedirs(args.outdir, exist_ok=True)
    path = f"{args.outdir}/part_{tag_task}.csv"

    def flush():
        """rewrite the part file after every cell, so a task that hits the
        time limit keeps what it finished"""
        keys = []
        for r in rows:
            keys += [k for k in r if k not in keys]
        tmp = path + ".tmp"
        with open(tmp, "w", newline="") as fh:
            wr = csv.DictWriter(fh, fieldnames=keys)
            wr.writeheader()
            for r in rows:
                wr.writerow({k: (float(v) if isinstance(v, np.floating) else v) for k, v in r.items()})
        os.replace(tmp, path)
    for i in idx:
        base = {k: float(d[k][i]) * mult.get(k, 1.0)
                for k in ("Cpv", "Cw", "Cez", "Chs", "Cbp", "Cbe", "water")}
        pv, w = cf(prof["pv"][i]), cf(prof["wind"][i])
        out = dict(cell_id=int(cells[i]), year=int(prof["year"][i]))
        tc = time.time()
        if args.base:
            r = dw.solve(pv, w, dict(base, syn=float(d["syn_ammonia"][i])),
                         dict(K0, eta_syn=K0["eta_syn_by_fuel"]["ammonia"]), eff="const", syn=None)
            if r is None:
                out["status_base"] = "fail"
            else:
                out.update({f"{k}_base": v for k, v in r.items() if k in ("lcoh", "lcoe_mwh", "sto_h")})
        for f in fuels:
            a = dict(base, syn=float(d[f"syn_{f}"][i]) * args.syn_mult * mult.get("syn", 1.0))
            K = dict(K0, eta_syn=K0["eta_syn_by_fuel"][f])
            r = dw.solve(pv, w, a, K, eff="const", syn=(args.min_load, args.ramp))
            if r is None:
                out[f"status_{f}"] = "fail"
                continue
            for k, v in r.items():
                out[f"{k}_{args.tag}_{f}"] = v
        out["solver"] = dw.SOLVER["name"] + (f"-m{args.grb_method}c{args.grb_crossover}t{args.grb_threads}"
                                              if dw.SOLVER["name"] == "gurobi" else "")
        out["sec"] = time.time() - tc
        rows.append(out)
        flush()
        print(f"[task {tag_task}] cell {cells[i]} done ({len(rows)}/{len(idx)}, "
              f"{(time.time()-t0)/60:.1f} min)", flush=True)


if __name__ == "__main__":
    main()
