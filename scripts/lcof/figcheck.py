"""
figcheck.py — text-overlap check for the paper figures (2026-10-21).

Every visible, non-empty text in the figure (titles, axis and tick labels, legends, annotations, panel names,
numbers) is measured on the canvas and compared pairwise; any two boxes that intersect are reported. Call
overlaps(fig) after the figure is complete and before saving.
"""
import numpy as np
from matplotlib.text import Text


def overlaps(fig, shrink_px=0.5):
    """[(text a, text b, overlap in px)] for every pair of visible texts whose boxes intersect."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    items = []
    from matplotlib.axes import Axes
    hidden = {id(lab) for a in fig.findobj(Axes) if not a.axison
              for lab in a.get_xticklabels() + a.get_yticklabels()}   # never drawn when the axis is off
    for t in fig.findobj(Text):
        if not t.get_visible() or not t.get_text().strip() or t.get_alpha() == 0 or id(t) in hidden:
            continue
        try:
            bb = t.get_window_extent(r)
        except Exception:
            continue
        if bb.width <= 0 or bb.height <= 0:
            continue
        items.append((t.get_text().replace("\n", " ")[:40], bb.x0 + shrink_px, bb.y0 + shrink_px,
                      bb.x1 - shrink_px, bb.y1 - shrink_px))
    if len(items) < 2:
        return []
    a = np.array([i[1:] for i in items])
    x0, y0, x1, y1 = a.T
    ox = np.minimum(x1[:, None], x1[None, :]) - np.maximum(x0[:, None], x0[None, :])
    oy = np.minimum(y1[:, None], y1[None, :]) - np.maximum(y0[:, None], y0[None, :])
    hit = (ox > 0) & (oy > 0)
    np.fill_diagonal(hit, False)
    out = []
    for i, j in zip(*np.nonzero(np.triu(hit))):
        out.append((items[i][0], items[j][0], float(min(ox[i, j], oy[i, j]))))
    return out


def font_issues(fig):
    """[(text, size)] for visible texts outside Nature's 5-7 pt (panel letters, single bold a-z, may be 8 pt)."""
    fig.canvas.draw()
    from matplotlib.axes import Axes
    hidden = {id(lab) for a in fig.findobj(Axes) if not a.axison
              for lab in a.get_xticklabels() + a.get_yticklabels()}
    out = []
    for t in fig.findobj(Text):
        s = t.get_text().strip()
        if not t.get_visible() or not s or id(t) in hidden:
            continue
        fs = t.get_fontsize()
        letter = len(s) == 1 and s.isalpha() and t.get_fontweight() in ("bold", 700) and abs(fs - 8) < 0.05
        if (fs < 4.995 or fs > 7.005) and not letter:
            out.append((s.replace(chr(10), " ")[:30], round(fs, 2)))
    return out


def report(fig, name):
    for s, fs in font_issues(fig):
        print(f"  FONT {name}: '{s}' {fs} pt")
    o = overlaps(fig)
    for a, b, px in o:
        print(f"  OVERLAP {name}: '{a}' x '{b}' ({px:.1f} px)")
    print(f"  text-overlap check {name}: {'none' if not o else len(o)}")
    return o
