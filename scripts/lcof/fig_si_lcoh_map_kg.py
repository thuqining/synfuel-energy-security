"""
fig_si_lcoh_map_kg.py — Supplementary figure: median levelized cost of hydrogen across the 20 weather years in every
land cell, at 2025 central equipment costs, in US$ per kg only (hydrogen readers think in US$/kg), colour 3-13 US$/kg
(YlGnBu_r). Restored 2026-10-22 (the script of 2026-10-09 was lost in the 2026-10-14 clean-up); same data and drawing
(fig_main_cost._nat_map) as fig_si_weather_spread.

From scripts/ (2025mid sandbox):  python ../work/caselow/run_mod.py ../work/caselow/2025mid 2025 lcof.fig_si_lcoh_map_kg
"""
from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd

mpl.use("Agg")

from . import inputs
from .fig_main_cost import MM, NAT_RC, _nat_map
from .fig_pptx_pairs import OUT, SUFFIX, YEARS

mpl.rcParams.update(NAT_RC)
mpl.rcParams.update({"pdf.fonttype": 42, "font.size": 7})
KG = 0.120          # GJ per kg of hydrogen (LHV)


def main():
    H = pd.DataFrame({y: pd.read_csv(inputs.MAPS / f"lcoh_global_{y}{SUFFIX}.csv")
                      .set_index("cell_id")["lcoh_usd_gj"] for y in YEARS}).dropna()
    meta = inputs.load_meta(2025)
    H = H[H.index.isin(meta.index[meta.cell_type == "land"])]
    med = H.median(axis=1) * KG
    fig = plt.figure(figsize=(183 * MM, 92 * MM))
    ax = fig.add_axes([0.0, 0.02, 1.0, 0.96])
    _nat_map(fig, ax, med.clip(3, 13).to_dict(), "YlGnBu_r", 3, 13,
             "Median levelized cost of hydrogen (US\$ per kg)", "")
    fig.savefig(OUT / "fig_si_lcoh_map_kg.pdf", bbox_inches="tight")
    fig.savefig(OUT / "fig_si_lcoh_map_kg.png", dpi=600, bbox_inches="tight")
    plt.close(fig)
    print(f"saved fig_si_lcoh_map_kg.(pdf|png): {len(med)} land cells, median {med.median():.2f} US$/kg "
          f"(p10 {med.quantile(.1):.2f}, p90 {med.quantile(.9):.2f})")


if __name__ == "__main__":
    main()
