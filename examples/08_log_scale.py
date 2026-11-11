"""Power laws on log-log axes, and a range that grows by decades.

`x_scale="log"` and `y_scale="log"` map the data; log locators put the ticks at the
decades with minor ticks between. On log-log axes every power law is a straight line.

    manim -pql examples/08_log_scale.py LogScale
"""

from manim import *

import manim_plots as mp


class LogScale(Scene):
    def construct(self):
        ax = mp.Axes(
            x_range=(1, 100),
            y_range=(0.1, 1e4),
            x_length=8,
            y_length=5.5,
            x_scale="log",
            y_scale="log",
            axis_config={"include_numbers": True},
            theme="origin",
        ).shift(0.2 * DOWN + 0.6 * LEFT)
        curves = [
            ax.plot(np.sqrt, label="√x"),
            ax.plot(lambda x: x, label="x"),
            ax.plot(lambda x: x**2, label="x²"),
        ]
        legend = ax.legend()
        legend.next_to(ax, RIGHT, aligned_edge=UP)

        self.play(Create(ax))
        self.play(*(Create(c) for c in curves), run_time=2)
        self.play(FadeIn(legend))
        self.wait()
        self.play(ax.animate.set_x_range((1, 1e4)).set_y_range((0.1, 1e8)), run_time=3)
        self.wait()
