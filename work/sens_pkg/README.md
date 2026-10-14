# Sensitivity package (2026-10-09)

Optimization-based sensitivity runs at 2025 central costs: every land cell at its median weather
year, same linear programme as the main runs (dyn_worker.py, unchanged).

On the server run the base case, the equipment-cost variants and offshore wind:

    python sens_flex.py --test
    python sens_flex.py --groups base,drivers,offshore --workers 100

(about 44,000 LPs, roughly 5-6 hours with Gurobi). The flexibility variants (--groups flex) run
on the other PC. If interrupted, run the same command again: finished chunks are skipped.
When it prints "results zipped to results_sens_....zip", copy that zip back.

Requirements: Python 3.9+, numpy, scipy; gurobipy with a licence if available (else HiGHS).
