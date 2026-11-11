"""A 3D histogram of a 2D sample, grown column by column, under a turning camera.

`ax.hist3d` counts with `numpy.histogram2d` and draws shaded columns coloured by
count; `GrowBars` raises them; the faces are drawn far to near as the camera turns.

    manim -pql examples/17_histogram_3d.py Histogram3D
"""

from manim import *

import manim_plots as mp


class Histogram3D(ThreeDScene):
    def construct(self):
        rng = np.random.default_rng(5)
        ax = mp.ThreeDAxes(
            x_range=(-3, 3, 1),
            y_range=(-3, 3, 1),
            z_range=(0, 180, 60),
            x_length=5,
            y_length=5,
            z_length=3.5,
            frame="box",
        )
        self.set_camera_orientation(**ax.view(25, -55))
        x, y = rng.normal(0, 1, 2000), rng.normal(0, 1, 2000)
        hist = ax.hist3d(x, y, bins=8, range=((-3, 3), (-3, 3)))

        self.play(Create(ax))
        self.play(mp.GrowBars(hist, lag_ratio=0.02), run_time=2.5)
        self.move_camera(**ax.view(35, 30), run_time=4)
        self.wait()
