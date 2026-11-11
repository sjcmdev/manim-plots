"""The registry holds artists weakly (row RG-1 of
`docs/acceptance/11b-data-channel.md`).

Manim's idiom for a live curve, `always_redraw(lambda: ax.plot(...))`, makes a plot
every frame; only the one the updater keeps may stay registered.
"""

from __future__ import annotations

import gc

import numpy as np
from manim import Scene, ValueTracker, VGroup, always_redraw

import manim_plots as mp

from .helpers import probe


def axes():
    return mp.Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1), x_length=6, y_length=4)


def test_rg1_always_redraw_leaves_one_registered_plot():
    t = ValueTracker(0.0)
    ax = axes()
    wave = always_redraw(lambda: ax.plot(lambda x: np.sin(x + t.get_value())))

    def construct(scene: Scene) -> None:
        scene.add(ax, wave)
        scene.play(t.animate.set_value(3), run_time=10)

    probe(construct, lambda: None)  # 60 frames at 6 fps
    gc.collect()
    assert len(ax.artists) <= 1


def test_rg1_an_unreferenced_artist_leaves_the_registry():
    ax = axes()
    kept = ax.plot(np.sin)
    ax.plot(np.cos)  # nothing keeps it
    gc.collect()
    assert list(ax.artists) == [kept]


def test_rg1_a_referenced_artist_stays_in_order():
    ax = axes()
    first, second = ax.plot(np.sin), ax.plot(np.cos)
    group = VGroup(ax.plot(lambda x: x / 3))
    gc.collect()
    assert list(ax.artists) == [first, second, group[0]]


def test_rg1_the_legend_sees_only_live_artists():
    ax = axes()
    kept = ax.plot(np.sin, label="sin")
    ax.plot(np.cos, label="cos")  # dropped before the legend is made
    gc.collect()
    assert [e.artist for e in ax.legend().entries] == [kept]
