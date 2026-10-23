"""
figgroups.py — shared layout for the 139-economy figures (2026-10-21): one column per economy, the list cut into
two stacked rows at a group boundary so no group is split, the same column width in both rows, and each group
marked by a bold name over a bracket and an alternating light background.
"""
import numpy as np

INK = "#1A1A1A"
BAND = "#F1F3F5"


def split_rows(rows, group_of, first_row_groups):
    """two rows: the economies whose group is in first_row_groups, then the rest (order kept)."""
    top = [c for c in rows if group_of(c) in first_row_groups]
    bottom = [c for c in rows if group_of(c) not in first_row_groups]
    return [top, bottom], max(len(top), len(bottom))


def spans(blk, group_of):
    """[(group, start, end)] runs of one group in a row, end exclusive."""
    out, s = [], 0
    for j in range(1, len(blk) + 1):
        if j == len(blk) or group_of(blk[j]) != group_of(blk[s]):
            out.append((group_of(blk[s]), s, j))
            s = j
    return out


def mark_groups(axes, label_ax, blk, group_of, labels, counts=None, pad_pt=3.0, fontsize=6.0, band_axes=None,
                edges=None):
    """alternating background per group on every axis of the row, a bracket and a bold name above label_ax.
    2026-10-21: the bracket sits pad_pt points above label_ax and the name 1.5 points above the bracket,
    so every figure and row has the same spacing whatever the axis height. band_axes: the axes that get the
    alternating background (default: all); the dividers run through every axis. edges: column edges in data
    units (len(blk) + 1 values) when columns have unequal widths; default one unit per column."""
    import matplotlib.transforms as mtr
    fig = label_ax.figure
    base = label_ax.get_xaxis_transform()
    up = lambda pt: base + mtr.ScaledTranslation(0, pt / 72, fig.dpi_scale_trans)
    xe = np.arange(len(blk) + 1) - 0.5 if edges is None else np.asarray(edges, float)
    for k, (g, s, e) in enumerate(spans(blk, group_of)):
        lo, hi = xe[s], xe[e]
        if k % 2 == 0:
            for a in (axes if band_axes is None else band_axes):
                a.axvspan(lo, hi, color=BAND, lw=0, zorder=0)
        if k:
            for a in axes:
                a.axvline(lo, color=INK, lw=0.5, alpha=0.55, zorder=0.5)
        name = labels[g] + (f" ({counts[g]})" if counts else "")
        b0, b1 = lo + 0.2 * (xe[s + 1] - xe[s]), hi - 0.2 * (xe[e] - xe[e - 1])
        label_ax.plot([b0, b1], [1, 1], color=INK, lw=0.6, clip_on=False, transform=up(pad_pt + 2.5))
        for x in (b0, b1):
            label_ax.annotate("", xy=(x, 1), xycoords=up(pad_pt), xytext=(x, 1), textcoords=up(pad_pt + 2.5),
                              arrowprops=dict(arrowstyle="-", color=INK, lw=0.6, shrinkA=0, shrinkB=0))
        label_ax.text((lo + hi) / 2, 1, name, ha="center", va="bottom", fontsize=fontsize, fontweight="bold",
                      color=INK, clip_on=False, transform=up(pad_pt + 4.0))


def count(rows, group_of):
    from collections import Counter
    return Counter(group_of(c) for c in rows)


def col_font(ax, units, lo=5.0, hi=6.0):
    """2026-10-21: the largest font (pt) whose rotated labels fit a column `units` data units wide on ax:
    one line of text is about 1.18 x the font size high. Call after the x limits are set."""
    bb = ax.get_window_extent()
    x0, x1 = ax.get_xlim()
    col_mm = bb.width / ax.figure.dpi * 25.4 / abs(x1 - x0) * units
    return float(np.clip(col_mm / (0.3528 * 1.18), lo, hi))
