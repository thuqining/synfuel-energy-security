"""labels.py — greedy anti-collision point labelling shared by the
scatter panels (payoff quadrant, supply-demand), so every core-30
economy is named without labels overlapping points, other labels or
reserved zones. Works in data units of the current axes; call after
set_xlim/set_ylim and a canvas draw."""
from __future__ import annotations

import numpy as np

OFFS = [(4, 2, "left"), (4, -10, "left"), (-4, 2, "right"),
        (-4, -10, "right"), (0, 6, "center"), (0, -14, "center"),
        (11, -4, "left"), (-11, -4, "right"), (14, 6, "left"),
        (-14, 6, "right"), (14, -16, "left"), (-14, -16, "right")]


def place_labels(ax, fig, xs, ys, names, *, order=None, reserved=(),
                 fontsize=8, color="#333333", cw=5.8, ch=10.5,
                 logx=False, logy=False, pad_px=4, margin=0.01):
    """Return the number of labels placed. `reserved` is a list of data
    boxes (x0, x1, y0, y1) that labels must avoid. For log axes the
    collision test runs in log10 space."""
    fig.canvas.draw()
    bb = ax.get_window_extent()
    xl, yl = ax.get_xlim(), ax.get_ylim()
    fx = (lambda v: np.log10(v)) if logx else (lambda v: v)
    fy = (lambda v: np.log10(v)) if logy else (lambda v: v)
    XL = (fx(xl[0]), fx(xl[1]))
    YL = (fy(yl[0]), fy(yl[1]))
    kx = (XL[1] - XL[0]) / bb.width
    ky = (YL[1] - YL[0]) / bb.height
    placed = [(fx(r[0]), fx(r[1]), fy(r[2]), fy(r[3])) for r in reserved]
    pts = list(zip(xs, ys, names))
    for x, y, _ in pts:
        placed.append((fx(x) - pad_px * kx, fx(x) + pad_px * kx,
                       fy(y) - pad_px * ky, fy(y) + pad_px * ky))

    def free(box):
        x0, x1, y0, y1 = box
        return all(not (x0 < u1 and u0 < x1 and y0 < v1 and v0 < y1)
                   for u0, u1, v0, v1 in placed)

    idx = list(range(len(pts))) if order is None else list(order)
    n = 0
    mx = (XL[1] - XL[0]) * margin
    my = (YL[1] - YL[0]) * margin
    for i in idx:
        x, y, nm = pts[i]
        w = len(nm) * cw * kx
        h = ch * ky
        for dx, dy, ha in OFFS:
            lx = fx(x) + dx * kx
            ly = fy(y) + dy * ky
            if ha == "left":
                box = (lx, lx + w, ly, ly + h)
            elif ha == "right":
                box = (lx - w, lx, ly, ly + h)
            else:
                box = (lx - w / 2, lx + w / 2, ly, ly + h)
            if (box[0] < XL[0] + mx or box[1] > XL[1] - mx
                    or box[2] < YL[0] + my or box[3] > YL[1] - my):
                continue
            if free(box):
                ax.annotate(nm, (x, y), textcoords="offset points",
                            xytext=(dx, dy), ha=ha, fontsize=fontsize,
                            color=color)
                placed.append(box)
                n += 1
                break
    return n
