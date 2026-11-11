"""A flower on polar axes: `r = 1.5 + a sin 5θ`, with `a` on a tracker.

`mp.PolarAxes` takes data in `(r, θ)` and `plot` draws `r = f(θ)`, clipped to the
disk; `SweepPolar` draws the axes by angle. Past `a = 1.5` the petals are cut at the
rim.

    manim -pql examples/10_polar.py PolarFlower
"""

from manim import *

import manim_plots as mp


class PolarFlower(Scene):
    def construct(self):
        a = ValueTracker(0.2)
        ax = mp.PolarAxes(r_range=(0, 3, 1), size=6.4).shift(0.3 * DOWN)
        flower = ax.plot(lambda t, a=0.2: 1.5 + a * np.sin(5 * t), a=a, color=YELLOW)
        formula = MathTex(r"r = 1.5 + a \sin 5\theta", color=YELLOW).to_corner(UL)
        readout = always_redraw(
            lambda: MathTex(f"a = {a.get_value():.2f}").next_to(formula, DOWN)
        )

        self.play(mp.SweepPolar(ax), run_time=2)
        self.play(Create(flower), Write(formula), FadeIn(readout), run_time=2)
        self.play(a.animate.set_value(1.0), run_time=2)
        self.play(a.animate.set_value(2.2), run_time=2)
        self.play(a.animate.set_value(0.6), run_time=2)
        self.wait()
