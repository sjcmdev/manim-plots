"""A histogram coloured by count that follows a moving sample, then is rebinned.

`ax.hist` counts with NumPy's rules; `color_by="count"` maps each bin through viridis,
shown by a colorbar; `.animate.set_data` recounts into the same bins; `RebinHistogram`
changes the bins.

    manim -pql examples/13_histogram.py Histogram
"""

from manim import *

import manim_plots as mp


class Histogram(Scene):
    def construct(self):
        rng = np.random.default_rng(3)
        ax = mp.Axes(
            x_range=(-4, 4, 1),
            y_range=(0, 300, 100),
            x_length=8,
            y_length=5,
            axis_config={"include_numbers": True},
        ).shift(0.6 * LEFT + 0.3 * DOWN)
        ax.y.set_position("left")
        hist = ax.hist(
            rng.normal(-1, 0.8, 1500), bins=24, range=(-4, 4),
            color_by="count", vmin=0, vmax=300,
        )  # fmt: skip
        bar = ax.colorbar(hist, label="n")

        self.play(Create(ax), mp.FillColorbar(bar))
        self.play(mp.GrowBars(hist.bars, lag_ratio=0.03), run_time=2)
        for centre in (0.5, 1.5):
            self.play(
                hist.animate.set_data(rng.normal(centre, 0.8, 1500)), run_time=1.5
            )
        self.play(mp.RebinHistogram(hist, 48), run_time=2)
        self.wait()
