from functools import partial
from time import perf_counter_ns

import numpy as np
from manim import Scene
from manim.renderer.cairo_renderer import CairoRenderer

from poc4.model import METRICS


class ProbeRenderer(CairoRenderer):
    def __init__(self):
        super().__init__()
        self.frames = []
        self.pixels = []
        self.observe = None
        self.keep_pixels = False

    def render(self, scene, time, moving_mobjects=None):
        start = perf_counter_ns()
        super().render(scene, time, moving_mobjects)
        item = dict(METRICS)
        item["render_ns"] = perf_counter_ns() - start
        if self.observe:
            item.update(self.observe(scene))
        self.frames.append(item)
        if self.keep_pixels:
            self.pixels.append(self.get_frame().copy())


class ProbeScene(Scene):
    def __init__(self):
        super().__init__(renderer=ProbeRenderer())

    def update_to_time(self, time):
        METRICS.clear()
        super().update_to_time(time)


def count_interpolation(animation):
    calls = []
    animation.interpolate = partial(counted_interpolate, animation.interpolate, calls)
    return calls


def counted_interpolate(interpolate, calls, alpha):
    calls.append(float(alpha))
    return interpolate(alpha)


def pixels(*mobjects):
    scene = ProbeScene()
    scene.add(*mobjects)
    scene.renderer.update_frame(scene)
    return np.array(scene.renderer.get_frame(), copy=True)
