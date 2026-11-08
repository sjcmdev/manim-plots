"""Two quantities on two y axes that share one x axis.

`ax.twinx(y_range=...)` adds a y axis on the right with its own range; each curve
belongs to its own pair of axes, so the shared x range moves both and the right range
moves only its curve.

    manim -pql examples/09_twin_axes.py TwinAxes
"""

from manim import *

import manim_plots as mp


class TwinAxes(Scene):
    def construct(self):
        numbers = {"include_numbers": True, "font_size": 22}
        ax = mp.Axes(
            x_range=(0, 10, 1),
            y_range=(0, 100, 20),
            x_length=9,
            y_length=4.8,
            axis_config=numbers,
        ).shift(0.4 * DOWN)
        pressure = ax.twinx(y_range=(0, 2, 0.5), y_axis_config=numbers)
        temperature = ax.plot(lambda x: 50 + 30 * np.sin(x / 2), color=RED)
        drop = pressure.plot(lambda x: 1.8 * np.exp(-x / 6), color=BLUE)
        ax.y_axis.set_color(RED)
        pressure.y_axis.set_color(BLUE)
        left = Tex("temperature", color=RED).next_to(ax.y_axis, UP)
        right = Tex("pressure", color=BLUE).next_to(pressure.y_axis, UP)

        self.play(Create(ax), Create(pressure), FadeIn(left, right))
        self.play(Create(temperature), Create(drop), run_time=2)
        self.play(ax.animate.set_x_range((0, 20)), run_time=2.5)
        self.play(pressure.animate.set_y_range((0, 1, 0.25)), run_time=2)
        self.wait()
