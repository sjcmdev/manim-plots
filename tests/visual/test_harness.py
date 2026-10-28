"""Plain Manim scenes: they check the harness, and catch a Manim version that renders
differently from the one the baselines were reviewed on."""

import numpy as np
import pytest
from manim import WHITE, Axes, Circle, Create, Scene, Square

from .conftest import BORDER, _origins, render


@pytest.mark.render
def test_last_frame_of_plain_axes_with_a_graph(visual):
    def construct(scene: Scene) -> None:
        ax = Axes()
        scene.add(ax, ax.plot(np.sin))

    visual(construct)


@pytest.mark.render
def test_every_frame_of_create_circle(visual):
    def construct(scene: Scene) -> None:
        scene.play(Create(Circle()))

    visual(construct, frames="all")


def _create_over_a_translucent_square(scene: Scene) -> None:
    scene.add(Square().set_fill(WHITE, opacity=0.5))
    scene.play(Create(Circle()))


def _then_a_frozen_wait(scene: Scene) -> None:
    _create_over_a_translucent_square(scene)
    scene.wait(1)


@pytest.mark.render
def test_a_frozen_wait_does_not_change_the_last_frame():
    # A frozen wait caches the background; drawing the end frame over it would draw the
    # translucent square twice.
    with_wait, _ = render(_then_a_frozen_wait, "last")
    without, _ = render(_create_over_a_translucent_square, "last")
    assert np.array_equal(with_wait, without)


@pytest.mark.render
def test_a_frozen_wait_keeps_one_tile_per_frame_and_ends_as_it_froze():
    sheet, (h, w) = render(_then_a_frozen_wait, "all")
    tiles = [sheet[y : y + h, x : x + w] for y, x in _origins(sheet.shape, (h, w))]
    # At 6 fps: six frames of Create, six of the one-second wait, then the end frame.
    frozen = tiles[6:13]
    assert all(np.array_equal(tile, frozen[0]) for tile in frozen)
    assert (tiles[13] == BORDER).all()
