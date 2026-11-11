"""Curves, markers and a legend: the colour cycle, line styles and marker shapes.

Plots without a colour take the next colour of the cycle; `line_style` and `marker`
choose dashes and marker shapes; `ax.legend()` collects every labelled artist.

    manim -pql examples/03_legend_and_styles.py LegendAndStyles
"""

from manim import *

import manim_plots as mp


class LegendAndStyles(Scene):
    def construct(self):
        ax = mp.Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1), x_length=10, y_length=5.5)
        sine = ax.plot(np.sin, label="sin x")
        cosine = ax.plot(np.cos, label="cos x", line_style=mp.LineStyle.DASHED)
        line = ax.plot(lambda x: x / 3, label="x / 3", line_style=mp.LineStyle.DOTTED)

        rng = np.random.default_rng(1)
        xs = np.linspace(-2.8, 2.8, 15)
        samples = ax.scatter(
            xs, np.sin(xs) + rng.normal(0, 0.15, xs.size),
            marker=mp.Marker.STAR, color=YELLOW, label="samples",
        )  # fmt: skip

        self.play(mp.DrawAxes(ax))
        self.play(Create(sine), Create(cosine), Create(line), run_time=2)
        self.play(mp.ShowPoints(samples, order="x", pop=True, lag_ratio=0.2))
        # The legend collects every labelled artist and belongs to the axes.
        legend = ax.legend("lower right")
        self.play(mp.RevealLegend(legend))
        self.wait()
        self.play(ax.animate.scale(0.7).to_edge(LEFT))
        self.wait()
