"""Manim's scene caching with library mobjects (F-922).

Row MX-3 of `docs/acceptance/11b-data-channel.md`. The scene really writes partial
movies, small, under the ignored `_out/media`, so that the second render of the same
scene can take its play from the cache.
"""

from __future__ import annotations

import numpy as np
import pytest
from manim import Create, Scene, tempconfig

import manim_plots as mp

from .conftest import OUT

CACHED = {
    "disable_caching": False,
    "dry_run": False,
    "write_to_movie": True,
    "progress_bar": "none",
    "media_dir": str(OUT / "media"),
    "pixel_width": 160,
    "pixel_height": 90,
    "frame_rate": 6,
}


class CachedPlot(Scene):
    def construct(self) -> None:
        ax = mp.Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1))
        curve = ax.plot(np.sin)
        self.add(ax)
        self.play(Create(curve), run_time=0.5)


@pytest.mark.render
def test_mx3_the_second_render_takes_its_play_from_the_cache():
    with tempconfig(CACHED):
        first = CachedPlot()
        first.render()
        second = CachedPlot()
        second.render()
    hashes = first.renderer.animations_hashes
    assert hashes and all(
        isinstance(h, str) and not h.startswith("uncached") for h in hashes
    )
    assert second.renderer.animations_hashes == hashes
    assert second.renderer.skip_animations


def test_mx3_library_mobjects_hash_by_identity():
    a, b = mp.Axes(), mp.Axes()
    assert len({a, b, a}) == 2
    curve = a.plot(np.sin)
    assert curve in {curve} and hash(curve) != hash(a.plot(np.sin))
