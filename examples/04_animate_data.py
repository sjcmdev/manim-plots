"""Animate the data with Manim's own tools: `.animate`, `ValueTracker`, `Transform`.

A range animates through `ax.animate.set_x_range`; a plot parameter is bound to a
tracker (here the one inside Manim's `Variable`), so the curve is redrawn on every
frame; data and geometry chain in one `.animate`.

    manim -pql examples/04_animate_data.py AnimateData
"""

from manim import *

import manim_plots as mp


class AnimateData(Scene):
    def construct(self):
        ax = mp.Axes(
            x_range=(-3, 3, 1),
            y_range=(-3, 3, 1),
            x_length=9,
            y_length=5,
            axis_config={"include_numbers": True},
        ).shift(0.4 * DOWN)
        a = Variable(1.0, MathTex("a"), num_decimal_places=2).to_corner(UR)
        # The keyword `a=` binds the function's parameter `a` to the tracker.
        wave = ax.plot(lambda x, a=1.0: a * np.sin(x), a=a.tracker, color=BLUE)
        formula = MathTex(r"y = a \sin x", color=BLUE).to_corner(UL)

        self.play(Create(ax), Create(wave), Write(formula), FadeIn(a))
        self.play(ax.animate.set_x_range((0, 10)), run_time=2)
        self.play(a.tracker.animate.set_value(2.5), run_time=1.5)
        self.play(a.tracker.animate.set_value(0.5), run_time=1.5)
        self.play(ax.animate.scale(0.7).set_x_range((-6, 6)), run_time=2)

        parabola = ax.plot(lambda x: x**2 / 6 - 2, color=YELLOW)
        self.play(
            Transform(wave, parabola),
            Transform(formula, MathTex(r"y = x^2/6 - 2", color=YELLOW).to_corner(UL)),
            FadeOut(a),
            run_time=1.5,
        )
        self.wait()
