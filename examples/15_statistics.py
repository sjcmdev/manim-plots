"""Box plots, violin plots and a pie chart, each with its own entrance.

`ax.boxplot` and `ax.violinplot` follow matplotlib's statistics; `GrowBoxPlot` opens
each box from its median and `UnfoldViolin` from its centre line. `mp.PieChart` is a
standalone mobject: `SweepPie` sweeps it in and `ExplodePie` pulls a wedge out.

    manim -pql examples/15_statistics.py Statistics
"""

from manim import *

import manim_plots as mp


class Statistics(Scene):
    def construct(self):
        rng = np.random.default_rng(4)
        ax = mp.Axes(x_range=(0, 5, 1), y_range=(-3, 5, 1), x_length=9, y_length=5.5)
        ax.y.set_position("left")
        samples = [
            rng.normal(m, s, 200) for m, s in ((0, 1), (1.5, 0.6), (2, 1.2), (1, 0.4))
        ]
        boxes = ax.boxplot(samples[:2], positions=[1, 2])
        violins = ax.violinplot(samples[2:], positions=[3, 4])

        self.play(Create(ax))
        self.play(mp.GrowBoxPlot(boxes), mp.UnfoldViolin(violins), run_time=2)
        self.wait()
        self.play(FadeOut(ax, boxes, violins))

        pie = mp.PieChart([35, 25, 20, 20], radius=2.5, labels=["a", "b", "c", "d"])
        self.play(mp.SweepPie(pie), run_time=2)
        self.play(mp.ExplodePie(pie, indices=[1], amount=0.3), run_time=1.5)
        self.wait()
