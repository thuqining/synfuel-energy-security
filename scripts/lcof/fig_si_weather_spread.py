"""
fig_si_weather_spread.py - Supplementary figure (Note 2): how much the
hydrogen cost of a cell moves between weather years (2026-10-05; replaces the
fixed-design figure).

  a  range of the 20 per-year optimal hydrogen costs, (max - min) / median
     year, per cell
  b  interquartile range across the 20 years over the median year, per cell

Both from lcoh_global_<year>_reg.csv, the cost layer of every figure. The
per-economy boxes of Fig. 3 show the same spread at the cheapest cell. (The
event price-change violins briefly added here as panel c belong with the
fossil-price heatmap and now live in fig_main_crisis.py.)

From scripts/:  python -u -m lcof.fig_si_weather_spread
Writes cf_global_final/figures/pptx/fig_si_weather_spread.(pdf|png).
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


def main():
    H = pd.DataFrame({y: pd.read_csv(inputs.MAPS / f"lcoh_global_{y}{SUFFIX}.csv")
                      .set_index("cell_id")["lcoh_usd_gj"] for y in YEARS}).dropna()
    meta = inputs.load_meta(2025)
    H = H[H.index.isin(meta.index[meta.cell_type == "land"])]
    med = H.median(axis=1)
    rng = (H.max(axis=1) - H.min(axis=1)) / med * 100
    iqr = (H.quantile(0.75, axis=1) - H.quantile(0.25, axis=1)) / med * 100

    fig = plt.figure(figsize=(183 * MM, 62 * MM))
    a = fig.add_axes([0.00, 0.02, 0.49, 0.93])
    b = fig.add_axes([0.51, 0.02, 0.49, 0.93])
    _nat_map(fig, a, rng.clip(upper=40).to_dict(), "magma_r", 0, 40,
             "Range across 20 weather years (% of median year)", "")
    _nat_map(fig, b, iqr.clip(upper=15).to_dict(), "magma_r", 0, 15,
             "Interquartile range across years (% of median year)", "")
    for ax, letter in ((a, "a"), (b, "b")):
        ax.text(0.0, 1.0, letter, transform=ax.transAxes, fontsize=8, fontweight="bold", va="top")
    fig.savefig(OUT / "fig_si_weather_spread.pdf", bbox_inches="tight")
    fig.savefig(OUT / "fig_si_weather_spread.png", dpi=600, bbox_inches="tight")
    plt.close(fig)
    print(f"saved fig_si_weather_spread.(pdf|png): {len(H)} land cells; range median {rng.median():.1f}% "
          f"(IQR {rng.quantile(.25):.1f}-{rng.quantile(.75):.1f}%, {100 * (rng > 40).mean():.0f}% above 40%); "
          f"IQR median {iqr.median():.1f}% (IQR {iqr.quantile(.25):.1f}-{iqr.quantile(.75):.1f}%, "
          f"{100 * (iqr > 15).mean():.0f}% above 15%)")


if __name__ == "__main__":
    main()
