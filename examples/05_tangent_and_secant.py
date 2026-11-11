"""Close a secant into the tangent, then slide it along the curve.

Manim's calculus helpers keep their names and take trackers directly:
`get_secant_slope_group(x, graph, dx=dx)` follows both `x` and `dx`, and at `dx = 0`
the secant is the tangent. `slope_of_tangent` feeds an ordinary `DecimalNumber`.

    manim -pql examples/05_tangent_and_secant.py TangentAndSecant
"""

from manim import *

import manim_plots as mp


class TangentAndSecant(Scene):
    def construct(self):
        ax = mp.Axes(x_range=(-1, 5, 1), y_range=(-1, 6, 1), x_length=9, y_length=5)
        ax.shift(0.4 * DOWN)
        graph = ax.plot(lambda x: x**2 / 4 + 0.5, color=BLUE)
        x, dx = ValueTracker(1.0), ValueTracker(2.0)
        secant = ax.get_secant_slope_group(
            x, graph, dx=dx, dx_label="dx", dy_label="dy", secant_line_length=7
        )
        t_label = ax.get_T_label(x, graph, label=MathTex("x_0"))

        slope = DecimalNumber(0, num_decimal_places=2)
        slope.add_updater(
            lambda d: d.set_value(ax.slope_of_tangent(x.get_value(), graph))
        )
        readout = VGroup(MathTex(r"f'(x_0) ="), slope).arrange(RIGHT).to_corner(UL)

        self.play(Create(ax), Create(graph))
        self.play(FadeIn(secant), FadeIn(t_label))
        self.play(dx.animate.set_value(0.0), run_time=3)
        self.play(FadeIn(readout))
        self.play(x.animate.set_value(3.5), run_time=3)
        self.play(x.animate.set_value(0.5), run_time=2)
        self.wait()
