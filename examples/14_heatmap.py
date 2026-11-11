"""A heatmap revealed cell by cell, its colorbar, and contour lines on top.

`ax.imshow` places a 2D array in data space by its `extent`; `RevealCells` shows the
cells in order; `ax.contour` draws level lines of the same function and
`RevealContours` traces them level by level.

    manim -pql examples/14_heatmap.py Heatmap
"""

from manim import *

import manim_plots as mp


class Heatmap(Scene):
    def construct(self):
        ax = mp.Axes(
            x_range=(-3, 3, 1),
            y_range=(-3, 3, 1),
            x_length=6,
            y_length=6,
            axis_config={"include_numbers": True},
            theme="origin",
        ).shift(LEFT)
        x = np.linspace(-3, 3, 24)
        X, Y = np.meshgrid(x, x)
        hill = np.exp(-((X - 1) ** 2 + Y**2))
        Z = hill + 0.8 * np.exp(-((X + 1.2) ** 2 + (Y - 1) ** 2))
        heat = ax.imshow(Z, extent=(-3, 3, -3, 3), origin="lower", colorscale="magma")
        bar = ax.colorbar(heat, label="z")
        lines = ax.contour(X, Y, Z, levels=6, color=WHITE, stroke_width=2)

        self.play(Create(ax))
        self.play(mp.RevealCells(heat, order="column", lag_ratio=0.01), run_time=2.5)
        self.play(mp.FillColorbar(bar))
        self.play(mp.RevealContours(lines), run_time=2)
        self.wait()
