"""Registration: one system per artist, `ax.add`, `ax.remove`, copies (F-112, F-708,
F-709, F-919's copy row, ADR 0003 §8).

Rows AR-10 and AR-11 of `docs/acceptance/11a-artists.md`, across the four artists.
"""

from __future__ import annotations

import numpy as np
import pytest
from manim import RIGHT

import manim_plots as mp


def axes():
    return mp.Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1), x_length=6, y_length=4)


MAKERS = {
    "function": lambda ax: ax.plot(np.sin),
    "line": lambda ax: ax.line([-2, 0, 2], [0, 1, 0]),
    "scatter": lambda ax: ax.scatter([-1, 1], [1, -1]),
    "parametric": lambda ax: ax.plot_parametric_curve(
        lambda t: (t, t / 2), t_range=(-2, 2)
    ),
}


@pytest.mark.parametrize("kind", list(MAKERS))
def test_registered_in_order_and_bound_to_one_system(kind):
    ax, other = axes(), axes()
    first, second = MAKERS[kind](ax), MAKERS[kind](ax)
    assert list(ax.artists) == [first, second]
    with pytest.raises(ValueError):
        other.add(first)


@pytest.mark.parametrize("kind", list(MAKERS))
def test_ar10_remove_unregisters_and_freezes(kind):
    ax, other = axes(), axes()
    artist = MAKERS[kind](ax)
    ax.remove(artist)
    assert artist not in list(ax.artists)
    before = np.array(artist.get_all_points(), copy=True)
    ax.shift(RIGHT)
    ax.x.range = (-1, 1)
    np.testing.assert_array_equal(artist.get_all_points(), before)
    other.add(artist)
    assert artist in list(other.artists)
    other.shift(RIGHT)
    assert not np.array_equal(artist.get_all_points(), before)


def test_ar10_removing_an_unregistered_artist_raises():
    ax, other = axes(), axes()
    curve = other.plot(np.sin)
    with pytest.raises(ValueError):
        ax.remove(curve)


@pytest.mark.parametrize("kind", list(MAKERS))
def test_ar11_a_copy_follows_the_system_unregistered(kind):
    ax = axes()
    artist = MAKERS[kind](ax)
    copy = artist.copy()
    assert copy not in list(ax.artists)
    start = np.array(copy.get_all_points(), copy=True)
    ax.shift(RIGHT)
    np.testing.assert_allclose(copy.get_all_points(), start + RIGHT, atol=1e-9)
    with pytest.raises(ValueError):
        ax.remove(copy)


def test_ar11_a_copied_system_has_no_artists():
    ax = axes()
    curve = ax.plot(np.sin)
    twin = ax.copy()
    assert list(twin.artists) == []
    before = np.array(curve.points, copy=True)
    twin.shift(RIGHT)
    np.testing.assert_array_equal(curve.points, before)
