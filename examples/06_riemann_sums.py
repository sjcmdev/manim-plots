"""Riemann rectangles that rise from the axis and refine toward the exact area.

`get_riemann_rectangles` and `get_area` keep Manim's names and colours; `GrowRiemann`
raises the rectangles from the axis and `RefineRiemann` splits them to a smaller `dx`.

    manim -pql examples/06_riemann_sums.py RiemannSums
"""

from manim import *

import manim_plots as mp


class RiemannSums(Scene):
    def construct(self):
        ax = mp.Axes(x_range=(-1, 5, 1), y_range=(-1, 6, 1), x_length=9, y_length=5)
        ax.shift(0.4 * DOWN)
        graph = ax.plot(lambda x: x**2 / 4 + 0.5, color=BLUE)
        rects = ax.get_riemann_rectangles(graph, x_range=(0, 4), dx=1, fill_opacity=0.7)
        area = ax.get_area(graph, x_range=(0, 4), opacity=0.4)
        integral = MathTex(
            r"\int_0^4 \left(\frac{x^2}{4} + \frac12\right) dx"
        ).to_corner(UL)

        self.play(Create(ax), Create(graph))
        self.play(mp.GrowRiemann(rects, lag_ratio=0.2))
        self.play(mp.RefineRiemann(rects, 0.5), run_time=1.5)
        self.play(mp.RefineRiemann(rects, 0.25), run_time=1.5)
        self.play(mp.RefineRiemann(rects, 0.05), run_time=1.5)
        self.play(FadeOut(rects), mp.GrowRegion(area), Write(integral))
        self.wait()
