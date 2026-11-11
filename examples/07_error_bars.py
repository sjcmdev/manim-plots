"""Measurements with error bars, a fitted line, and a new measurement run.

`ax.errorbar` draws bars in data space with caps of a fixed size; `GrowErrorBars`
opens them from their samples; `.animate.set_data` moves every point and bar to its
new value.

    manim -pql examples/07_error_bars.py ErrorBars
"""

from manim import *

import manim_plots as mp


class ErrorBars(Scene):
    def construct(self):
        ax = mp.Axes(
            x_range=(0, 6, 1),
            y_range=(0, 5, 1),
            x_length=9,
            y_length=5,
            axis_config={"include_numbers": True},
        ).shift(0.4 * DOWN)
        labels = ax.get_axis_labels(Tex("time [s]"), Tex("height [m]"))
        xs = np.arange(1.0, 6.0)
        ys = np.array([1.4, 2.1, 2.4, 3.1, 3.4])
        data = ax.errorbar(xs, ys, yerr=0.3, xerr=0.15, color=YELLOW, label="run 1")
        slope, intercept = np.polyfit(xs, ys, 1)
        fit = ax.plot(lambda x: slope * x + intercept, color=BLUE, label="fit")

        self.play(Create(ax), Write(labels))
        self.play(mp.GrowErrorBars(data, lag_ratio=0.2))
        self.play(Create(fit), mp.RevealLegend(ax.legend("upper left")))
        self.wait()

        new = np.array([0.9, 1.9, 2.6, 3.5, 4.2])
        self.play(
            data.animate.set_data(xs, new, yerr=[0.2, 0.4, 0.2, 0.5, 0.3]),
            run_time=2,
        )
        slope, intercept = np.polyfit(xs, new, 1)
        self.play(Transform(fit, ax.plot(lambda x: slope * x + intercept, color=BLUE)))
        self.wait()
