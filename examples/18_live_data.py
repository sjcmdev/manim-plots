"""Data arriving live: the line grows point by point and the axes widen to keep it.

`mp.AppendData(line, x, y, autoscale=True)` draws the new points on one after another
and grows the ranges with matplotlib's margins; `ax.end_label` follows the last point
and reads its value.

    manim -pql examples/18_live_data.py LiveData
"""

from manim import *

import manim_plots as mp


class LiveData(Scene):
    def construct(self):
        ax = mp.Axes(
            x_range=(0, 2, 1),
            y_range=(0, 2, 1),
            x_length=9,
            y_length=5,
            axis_config={"include_numbers": True},
        ).shift(0.3 * DOWN)
        ax.x.set_locator(mp.MaxNLocator(8))
        ax.y.set_locator(mp.MaxNLocator(5))
        xs = np.arange(0, 41) / 4
        ys = 1 + xs / 3 + np.sin(xs)
        line = ax.line(xs[:3], ys[:3], color=YELLOW)
        label = ax.end_label(line)

        self.play(Create(ax), Create(line), FadeIn(label))
        self.play(mp.AppendData(line, xs[3:], ys[3:], autoscale=True), run_time=6)
        self.wait()
