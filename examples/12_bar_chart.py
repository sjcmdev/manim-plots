"""A bar chart race: bars grow, take each year's values, and sort themselves.

`ax.bar` takes category names, which become the x ticks; `GrowBars` raises the bars
with a lag; `.animate.set_data` moves each bar to its new height by category; `SortBars`
slides the bars to their places with their names; `HighlightBar` dims the others.

    manim -pql examples/12_bar_chart.py BarChart
"""

from manim import *

import manim_plots as mp


class BarChart(Scene):
    def construct(self):
        names = ["Ada", "Bob", "Cy", "Dee", "Eve"]
        years = {
            2021: [3, 5, 2, 4, 1],
            2022: [4, 5, 6, 4, 3],
            2023: [6, 5, 7, 8, 5],
            2024: [9, 6, 7, 8, 10],
        }
        ax = mp.Axes(
            y_range=(0, 10, 2),
            x_length=9,
            y_length=5,
            axis_config={"include_numbers": True},
        ).shift(0.4 * DOWN)
        first, *rest = years.items()
        bars = ax.bar(
            names, first[1], c="height", colorscale="viridis", vmin=0, vmax=10
        )
        year = Integer(first[0], group_with_commas=False).to_corner(UR)

        self.play(Create(ax), FadeIn(year))
        self.play(mp.GrowBars(bars, lag_ratio=0.15), run_time=1.5)
        for label, values in rest:
            self.play(
                bars.animate.set_data(x=names, height=values),
                year.animate.set_value(label),
            )
            self.play(mp.SortBars(bars, reverse=True))
        self.play(mp.HighlightBar(bars, "Eve"), run_time=1.5)
        self.wait()
