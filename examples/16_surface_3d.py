"""A surface swept in on 3D box axes, then seen from all around.

`mp.ThreeDAxes(frame="box")` draws matplotlib's box, whose panes change sides as the
camera turns; `ax.plot_surface` colours by height; `SweepSurface` reveals the surface
along `u`. `ax.view(elev, azim)` gives the `ThreeDScene` camera matplotlib's angles.

    manim -pql examples/16_surface_3d.py Surface3D
"""

from manim import *

import manim_plots as mp


class Surface3D(ThreeDScene):
    def construct(self):
        ax = mp.ThreeDAxes(
            x_range=(-3, 3, 1),
            y_range=(-3, 3, 1),
            z_range=(-1, 1, 0.5),
            x_length=5,
            y_length=5,
            z_length=3,
            frame="box",
        )
        self.set_camera_orientation(**ax.view(25, -55))
        surface = ax.plot_surface(
            lambda u, v: np.sin(u) * np.cos(v), (-3, 3), (-3, 3), colorscale="viridis"
        )

        self.play(Create(ax))
        self.play(mp.SweepSurface(surface), run_time=2.5)
        self.move_camera(**ax.view(40, 60), run_time=5)
        self.move_camera(**ax.view(25, -55), run_time=3)
        self.wait()
