"""A vector field, dots carried along it, and flowing stream lines.

`ax.get_vector_field` and `ax.get_stream_lines` take the field in data coordinates and
belong to the axes; `mp.Flow` moves each dot along its own path; the stream lines keep
Manim's `create`, `start_animation` and `end_animation`.

    manim -pql examples/11_vector_field.py VectorField
"""

from manim import *

import manim_plots as mp


def swirl(point):
    """Two vortices and a drift between them."""
    x, y = point[0], point[1]
    return np.array([np.sin(y), np.cos(x) - 0.3 * y, 0.0])


class VectorField(Scene):
    def construct(self):
        ax = mp.NumberPlane(
            x_range=(-6, 6, 1), y_range=(-3, 3, 1), x_length=12, y_length=6
        )
        field = ax.get_vector_field(swirl, opacity=0.6)
        dots = VGroup(
            *(
                Dot(ax.c2p(x, y), color=YELLOW)
                for x in (-5, -3, -1, 1, 3, 5)
                for y in (-2, 0, 2)
            )
        )

        self.play(Create(ax), FadeIn(field), run_time=1.5)
        self.play(FadeIn(dots))
        self.play(mp.Flow(field, dots, run_time=4))
        self.play(FadeOut(dots), FadeOut(field))

        lines = ax.get_stream_lines(swirl, stroke_width=2)
        self.play(lines.create(run_time=2))
        lines.start_animation(warm_up=False, flow_speed=1.5)
        self.wait(3)
        self.play(lines.end_animation())
