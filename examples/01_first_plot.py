"""A first plot: axes, a curve and its label, drawn with Manim's own animations.

The curve and its label belong to the axes: when the axes move, scale or change their
range, everything plotted on them follows.

    manim -pql examples/01_first_plot.py FirstPlot
"""

from manim import *

import manim_plots as mp


class FirstPlot(Scene):
    def construct(self):
        ax = mp.Axes(
            x_range=(-4, 4, 1),
            y_range=(-2, 2, 1),
            x_length=10,
            y_length=5,
            axis_config={"include_numbers": True},
        )
        # Ticks are located again whenever the range changes: at most 9 of them.
        ax.x.set_locator(mp.MaxNLocator(9))
        labels = ax.get_axis_labels(x_label="x", y_label="y")
        curve = ax.plot(np.sin, color=BLUE)
        label = ax.get_graph_label(curve, MathTex(r"\sin x"), x_val=2.5)

        self.play(Create(ax), Write(labels))
        self.play(Create(curve), run_time=2)
        self.play(FadeIn(label, shift=UP))
        self.wait()

        # Move the axes like any mobject: the curve and its label come along.
        self.play(ax.animate.scale(0.6).to_corner(UL))
        # Change the data range: ticks, numbers and the curve are rebuilt every frame.
        self.play(ax.animate.set_x_range((-8, 8)), run_time=2)
        self.play(ax.animate.scale(1 / 0.6).move_to(ORIGIN))
        self.wait()
