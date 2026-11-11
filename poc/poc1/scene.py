from manim import Scene
from manim.renderer.cairo_renderer import CairoRenderer

from poc1.points import METRICS


class CountingRenderer(CairoRenderer):
    def __init__(self):
        super().__init__()
        self.frames = []

    def render(self, scene, time, moving_mobjects=None):
        super().render(scene, time, moving_mobjects)
        self.frames.append(dict(METRICS))


class ProbeScene(Scene):
    def __init__(self):
        super().__init__(renderer=CountingRenderer())

    def update_to_time(self, time):
        METRICS.clear()
        super().update_to_time(time)


def count_interpolation(animation):
    calls = []
    interpolate = animation.interpolate

    def counted(alpha):
        calls.append(float(alpha))
        return interpolate(alpha)

    animation.interpolate = counted
    return calls
