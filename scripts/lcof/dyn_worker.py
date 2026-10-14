"""
dyn_worker.py — self-contained cluster worker for the dynamic-operation
sensitivity (numpy + scipy only; same LP as lcof.dynamic_ops.solve).

Reads cells.npz (hourly PV and wind capacity factors of each cell's median
weather year, plus per-cell annuities), solves the six variants for the
cells assigned to this Slurm array task, writes out/part_<task>.csv.

Run locally for a check:  python dyn_worker.py --npz cells.npz --only 0
"""
import argparse
import os
import time

import csv
import sys

import numpy as np
from scipy import sparse
from scipy.optimize import linprog

SOLVER = {"name": "highs"}

VARIANTS = {
    "base":      dict(eff="const", syn=None),
    "pl_up":     dict(eff="up", syn=None),
    "pl_down":   dict(eff="down", syn=None),
    "flex_mod":  dict(eff="const", syn=(0.60, 0.05)),
    "flex_high": dict(eff="const", syn=(0.20, 0.20)),
    "flex_full": dict(eff="const", syn=(0.00, 1.00)),
}


def solve(cfpv, cfw, a, K, eff="const", syn=None):
    """a: dict of annuities ($/MW/yr or $/MWh/yr); K: constants."""
    n = len(cfpv)
    dt = 8760.0 / n
    F = 1.0
    eta, sig = K["eta_el"], K["sigma"]
    flex = syn is not None
    # variable layout
    cap = ["Cpv", "Cw", "Cez", "Chs", "Cbp", "Cbe"] + (["Cs"] if flex else [])
    blocks = ["pel", "h", "s", "bc", "bd", "e", "curt"] + (["y"] if flex else [])
    nc = len(cap)
    ci = {k: i for i, k in enumerate(cap)}
    bi = {k: nc + j * n for j, k in enumerate(blocks)}
    nv = nc + len(blocks) * n
    I = sparse.identity(n, format="csr")
    # cyclic shift: (R x)_t = x_{t-1}
    R = sparse.csr_matrix((np.ones(n), (np.arange(n), (np.arange(n) - 1) % n)), shape=(n, n))

    def row_block(parts, capcols=None):
        """one n-row constraint block: parts = {block: n x n matrix},
        capcols = {capacity: length-n column}"""
        capm = np.zeros((n, nc))
        for cname, v in (capcols or {}).items():
            capm[:, ci[cname]] = np.asarray(v, float)
        cols = [sparse.csr_matrix(capm)]
        for b in blocks:
            cols.append(sparse.csr_matrix(parts[b]) if b in parts
                        else sparse.csr_matrix((n, n)))
        return sparse.hstack(cols, format="csr")

    Aeq, beq, Aub, bub = [], [], [], []
    one = np.ones(n)
    # electricity balance
    Aeq.append(row_block({"pel": -I, "bc": -I, "bd": K["eta_dh"] * I, "curt": -I},
                         {"Cpv": cfpv, "Cw": cfw, **({"Cez": -sig * one} if eff == "down" else {})}))
    beq.append(np.zeros(n))
    # battery state of charge (cyclic)
    Aeq.append(row_block({"e": I - R, "bc": -K["eta_ch"] * dt * I, "bd": dt * I}))
    beq.append(np.zeros(n))
    for b, c in (("e", "Cbe"), ("bc", "Cbp"), ("bd", "Cbp"), ("pel", "Cez"), ("s", "Chs")):
        Aub.append(row_block({b: I}, {c: -one}))
        bub.append(np.zeros(n))
    # electrolyser production
    if eff == "const":
        Aeq.append(row_block({"h": I, "pel": -eta * I})); beq.append(np.zeros(n))
    elif eff == "down":
        Aeq.append(row_block({"h": I, "pel": -eta * (1 + sig) * I})); beq.append(np.zeros(n))
    else:
        hi, x0 = 0.70, 0.30
        slope = (eta - hi * x0) / (1 - x0)
        Aub.append(row_block({"h": I, "pel": -hi * I})); bub.append(np.zeros(n))
        Aub.append(row_block({"h": I, "pel": -slope * I}, {"Cez": -(hi - slope) * x0 * one}))
        bub.append(np.zeros(n))
    # hydrogen store balance (cyclic)
    if not flex:
        Aeq.append(row_block({"s": I - R, "h": -dt * I})); beq.append(-F * dt * one)
    else:
        mn, rp = syn
        Aeq.append(row_block({"s": I - R, "h": -dt * I, "y": dt * I})); beq.append(np.zeros(n))
        tot = sparse.lil_matrix((1, nv)); tot[0, bi["y"]:bi["y"] + n] = dt
        Aeq.append(tot.tocsr()); beq.append(np.array([F * 8760.0]))
        Aub.append(row_block({"y": I}, {"Cs": -one})); bub.append(np.zeros(n))
        if mn > 0:
            Aub.append(row_block({"y": -I}, {"Cs": mn * one})); bub.append(np.zeros(n))
        if rp < 1:
            Aub.append(row_block({"y": I - R}, {"Cs": -rp * one})); bub.append(np.zeros(n))
            Aub.append(row_block({"y": R - I}, {"Cs": -rp * one})); bub.append(np.zeros(n))
    c = np.zeros(nv)
    for k in ("Cpv", "Cw", "Cez", "Chs", "Cbp", "Cbe"):
        c[ci[k]] = a[k]
    if flex:
        c[ci["Cs"]] = a["syn"]
    c[bi["bc"]:bi["bc"] + n] = 1e-3 * dt
    c[bi["bd"]:bi["bd"] + n] = 1e-3 * dt
    c[bi["h"]:bi["h"] + n] = a["water"] * dt
    Aub_m, bub_v = sparse.vstack(Aub, format="csr"), np.concatenate(bub)
    Aeq_m, beq_v = sparse.vstack(Aeq, format="csr"), np.concatenate(beq)
    x = fun = None
    if SOLVER["name"] == "gurobi":
        try:
            import gurobipy as gp
            mdl = gp.Model()
            mdl.Params.OutputFlag = 0
            mdl.Params.Threads = SOLVER.get("threads", 1)
            if SOLVER.get("method") is not None:
                mdl.Params.Method = SOLVER["method"]          # 2 = barrier
            if SOLVER.get("crossover") is not None:
                mdl.Params.Crossover = SOLVER["crossover"]    # 0 = skip crossover
            xv = mdl.addMVar(nv, lb=0.0, obj=c)
            mdl.addMConstr(Aub_m, xv, "<", bub_v)
            mdl.addMConstr(Aeq_m, xv, "=", beq_v)
            mdl.optimize()
            if mdl.Status == 2:
                x, fun = xv.X, mdl.ObjVal
            else:
                return None
        except Exception as ex:                  # licence or import problem
            print(f"gurobi unavailable ({ex}); falling back to HiGHS", flush=True)
            SOLVER["name"] = "highs"
    if x is None:
        res = linprog(c, A_ub=Aub_m, b_ub=bub_v, A_eq=Aeq_m, b_eq=beq_v,
                      bounds=(0, None), method="highs")
        if res.status != 0:
            return None
        x, fun = res.x, res.fun
    Cs = x[ci["Cs"]] if flex else F
    syn_part = a["syn"] * Cs
    Z = fun + (0.0 if flex else a["syn"] * F)
    gen = (x[ci["Cpv"]] * cfpv + x[ci["Cw"]] * cfw).sum() * dt
    lcoe = (a["Cpv"] * x[ci["Cpv"]] + a["Cw"] * x[ci["Cw"]]) / gen
    gj = F * 8760.0 * 3.6
    genpv = (x[ci["Cpv"]] * cfpv).sum() * dt
    used = x[bi["pel"]:bi["pel"] + n].sum() * dt          # stage1: curtail = 1 - used / gen
    return dict(lcoh=(Z - syn_part) / gj, syn_gj=syn_part / (gj * K["eta_syn"]),
                lcoe_mwh=lcoe, sto_h=x[ci["Chs"]] / F, cs=Cs,
                # design, in the units of the constant-load layer (per MW of H2 delivered)
                cap_pv=x[ci["Cpv"]] / F, cap_wind=x[ci["Cw"]] / F, cap_ez=x[ci["Cez"]] / F,
                cap_bat_MW=x[ci["Cbp"]] / F, cap_bat_MWh=x[ci["Cbe"]] / F,
                solar_share=genpv / gen if gen > 0 else 0.0, curtail_share=1.0 - used / gen if gen > 0 else 0.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz", default="cells.npz")
    ap.add_argument("--only", type=int, default=None)
    ap.add_argument("--variants", default=",".join(VARIANTS))
    ap.add_argument("--solver", default="highs")
    args = ap.parse_args()
    SOLVER["name"] = args.solver
    print(f"python {sys.executable}, numpy {np.__version__}", flush=True)
    d = np.load(args.npz, allow_pickle=True)
    K = d["K"].item()
    cells = d["cell_id"]
    task = int(os.environ.get("SLURM_ARRAY_TASK_ID", 0))
    ntask = int(os.environ.get("SLURM_ARRAY_TASK_COUNT", 1))
    idx = [args.only] if args.only is not None else list(range(task, len(cells), ntask))
    names = args.variants.split(",")
    rows, t0 = [], time.time()
    for i in idx:
        a = {k: float(d[k][i]) for k in ("Cpv", "Cw", "Cez", "Chs", "Cbp", "Cbe", "syn", "water")}
        pv, w = d["pv"][i].astype(float), d["wind"][i].astype(float)
        out = dict(cell_id=int(cells[i]))
        tc = time.time()
        for name in names:
            r = solve(pv, w, a, K, **VARIANTS[name])
            if r is None:
                out[f"status_{name}"] = "fail"
                continue
            for k, v in r.items():
                out[f"{k}_{name}"] = v
        out["solver"] = SOLVER["name"]
        out["sec"] = time.time() - tc
        rows.append(out)
        print(f"[task {task}] cell {cells[i]} done ({len(rows)}/{len(idx)}, {(time.time()-t0)/60:.1f} min)", flush=True)
    os.makedirs("out", exist_ok=True)
    keys = []
    for r in rows:
        keys += [k for k in r if k not in keys]
    with open(f"out/part_{task:03d}.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: (float(v) if isinstance(v, np.floating) else v) for k, v in r.items()})


if __name__ == "__main__":
    main()
