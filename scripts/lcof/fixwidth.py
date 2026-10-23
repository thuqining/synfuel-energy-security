"""
fixwidth.py — make every figure saved with bbox_inches="tight" come out exactly at Nature's full-page width
(183 mm), 2026-10-22. Font sizes stay as set; the canvas is narrowed (or widened) until the tight box, plus the
save padding, measures 183 mm, so the overhang of keys and labels is taken out of the panels, not out of the text.

    import lcof.fixwidth; lcof.fixwidth.install()      # before the figure module saves
"""
import matplotlib as mpl
import matplotlib.figure as mf

TARGET_MM = 183.0
MIN_PT = None          # install(min_pt=7): every text raised to at least this size before saving
_orig = mf.Figure.savefig


def _raise_type(fig, pt):
    """2026-10-22: no text below `pt` points — tick labels through tick_params, so a redraw keeps them"""
    import matplotlib.text as mt
    fig.canvas.draw()
    for ax in fig.axes:
        for axis, name in ((ax.xaxis, "x"), (ax.yaxis, "y")):
            labs = [t for t in axis.get_ticklabels(which="both") if t.get_text()]
            if labs and min(t.get_fontsize() for t in labs) < pt:
                ax.tick_params(axis=name, which="both", labelsize=pt)
    for t in fig.findobj(mt.Text):
        if t.get_visible() and t.get_text().strip() and t.get_fontsize() < pt:
            t.set_fontsize(pt)


def _savefig(self, fname, *args, **kwargs):
    if MIN_PT:
        _raise_type(self, MIN_PT)
    if kwargs.get("bbox_inches") == "tight":
        pad = kwargs.get("pad_inches", mpl.rcParams["savefig.pad_inches"])
        pad = 0.1 if pad in (None, "layout") else float(pad)
        target = TARGET_MM / 25.4
        for _ in range(8):
            self.canvas.draw()
            bb = self.get_tightbbox(self.canvas.get_renderer())
            w = bb.width + 2 * pad
            if abs(w - target) < 0.004:
                break
            W, H = self.get_size_inches()
            self.set_size_inches(W - (w - target), H)
    if str(fname).endswith(".pdf"):           # 2026-10-22: the same text checks as the new figures
        from lcof.figcheck import report
        report(self, str(fname).replace("\\", "/").split("/")[-1])
        # 2026-10-22: raster parts of a vector PDF (map fills, heat maps, colour bars) at 600 dpi
        dpi = kwargs.get("dpi")
        if not isinstance(dpi, (int, float)) or dpi < 600:      # None or "figure" included
            kwargs["dpi"] = 600
    return _orig(self, fname, *args, **kwargs)


def install(target_mm=183.0, min_pt=None):
    global TARGET_MM, MIN_PT
    TARGET_MM, MIN_PT = target_mm, min_pt
    mf.Figure.savefig = _savefig
