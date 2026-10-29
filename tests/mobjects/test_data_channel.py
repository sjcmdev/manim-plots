"""Data under Manim's native `.animate`, and systems transformed into systems (F-908,
F-909, F-911, F-919, F-920).

Rows DC-1 to DC-7 of `docs/acceptance/11b-data-channel.md`. The oracle of a frame is a
fresh plot of the same function on fresh axes built with that frame's range and placed
where the animated axes are; two adaptive samplings of one curve agree within twice the
chord tolerance.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from itertools import pairwise
from typing import Any

import numpy as np
import pytest
from manim import (
    DOWN,
    RED,
    RIGHT,
    UP,
    ManimColor,
    ReplacementTransform,
    Scene,
    Transform,
    smooth,
    there_and_back,
)

import manim_plots as mp
from manim_plots.core import ManimPlotsWarning
from manim_plots.core.sources import CHORD_TOLERANCE
from manim_plots.mobjects.axis import Axis

from .helpers import assert_same_curve, probe

LENGTHS = {"x_length": 6, "y_length": 4}
Y = (-2, 2, 1)
TOL = 2 * CHORD_TOLERANCE
FPS = 6  # helpers.RUN


def system(x_range=(-3, 3, 1), f: Callable[..., Any] = np.sin):
    ax = mp.Axes(x_range=x_range, y_range=Y, **LENGTHS)
    return ax, ax.plot(f)


def tick_values(ax) -> tuple[set[float], set[float]]:
    """The x axis's visible tick values, in data, and those fully opaque."""
    visible, full = set(), set()
    for tick in ax.x_axis.ticks:
        if not tick.has_points() or tick.get_stroke_opacity() == 0:
            continue
        value = round(float(ax.p2c(tick.get_center())[0]), 6)
        visible.add(value)
        if tick.get_stroke_opacity() == 1:
            full.add(value)
    return visible, full


def snapshot(ax, curve) -> dict[str, Any]:
    lo, hi = (float(v) for v in ax.x.range.value)
    return {
        "range": (lo, hi),
        "corner": np.array(ax.c2p(lo, Y[0]), dtype=float),
        "curve": np.array(curve.points, copy=True),
        "ticks": tick_values(ax),
    }


def oracle(frame: dict[str, Any], f: Callable[..., Any] = np.sin, locator=None):
    """The curve and the tick values fresh axes show at a frame's range and place."""
    lo, hi = frame["range"]
    other = mp.Axes(x_range=(lo, hi, 1), y_range=Y, **LENGTHS)
    if locator is not None:
        other.x_axis.set_locator(locator)
    other.shift(frame["corner"] - other.c2p(lo, Y[0]))
    return np.array(other.plot(f).points), tick_values(other)[0]


def check_frame(frame: dict[str, Any], **oracle_kwargs: Any) -> None:
    points, expected = oracle(frame, **oracle_kwargs)
    assert_same_curve(frame["curve"], points, TOL)
    visible, full = frame["ticks"]
    assert expected <= visible, (frame["range"], expected - visible)
    assert full <= expected, (frame["range"], full - expected)


def alphas(n: int) -> np.ndarray:
    """The rate-function alpha of each of ``n`` frames of a one-second play."""
    return np.array([smooth(k / FPS) for k in range(n)])


def rebuilds(ax, curve) -> bool:
    before = np.array(curve.points, copy=True)
    ax.x.range = (-2, 2)
    return not np.array_equal(curve.points, before)


# --- DC-1 ----------------------------------------------------------------------------


def test_dc1_no_library_method_overrides_animate():
    for cls in (mp.CartesianAxes, Axis, mp.FunctionPlot):
        for name, member in inspect.getmembers(cls):
            module = getattr(member, "__module__", "") or ""
            if module.startswith("manim_plots"):
                assert not hasattr(member, "_override_animate"), (cls, name)


def test_dc1_every_frame_is_a_plot_of_its_range():
    ax, curve = system()

    def construct(scene: Scene) -> None:
        scene.add(ax, curve)
        scene.play(ax.animate.set_x_range((0, 10)), run_time=1)

    frames = probe(construct, lambda: snapshot(ax, curve))
    assert len(frames) >= 5
    for frame, alpha in zip(frames, alphas(len(frames)), strict=True):
        lo, hi = frame["range"]
        assert abs((lo + 3) / 3 - alpha) < 1e-9
        assert abs((hi - 3) / 7 - alpha) < 1e-9
        check_frame(frame)
    np.testing.assert_array_equal(ax.x.range.value, [0, 10])
    assert rebuilds(ax, curve)


# --- DC-2 ----------------------------------------------------------------------------


@pytest.mark.parametrize("order", ["shift first", "range first"])
def test_dc2_geometry_and_data_chain_into_one_animation(order):
    ax, curve = system()
    start = np.array(ax.c2p(-3, Y[0]), dtype=float)
    v = 2 * RIGHT + 0.5 * UP

    def construct(scene: Scene) -> None:
        scene.add(ax, curve)
        if order == "shift first":
            builder = ax.animate.shift(v).set_x_range((0, 10))
        else:
            builder = ax.animate.set_x_range((0, 10)).shift(v)
        scene.play(builder, run_time=1)

    frames = probe(construct, lambda: snapshot(ax, curve))
    for frame, alpha in zip(frames, alphas(len(frames)), strict=True):
        assert abs((frame["range"][0] + 3) / 3 - alpha) < 1e-9
        np.testing.assert_allclose(frame["corner"], start + alpha * v, atol=1e-9)
        check_frame(frame)
    np.testing.assert_allclose(ax.c2p(0, Y[0]), start + v, atol=1e-9)


# --- DC-3 ----------------------------------------------------------------------------


def play(ax, curve, animation, **kwargs: Any) -> None:
    def construct(scene: Scene) -> None:
        scene.add(ax, curve)
        scene.play(animation, **kwargs)

    probe(construct, lambda: None)


def test_dc3_a_tick_in_range_at_both_ends_keeps_its_object():
    ax, curve = system()
    tick = ax.x_axis.ticks.at(2.0)
    play(ax, curve, ax.animate.set_x_range((1, 7)))
    assert ax.x_axis.ticks.at(2.0) is tick


def test_dc3_a_styled_tick_survives_an_exit_and_return_in_one_play():
    ax, curve = system()
    tick = ax.x_axis.ticks.at(2.0)
    tick.set_color(RED)
    play(ax, curve, ax.animate.set_x_range((10, 16)), rate_func=there_and_back)
    np.testing.assert_array_equal(ax.x.range.value, [-3, 3])
    assert ax.x_axis.ticks.at(2.0) is tick
    assert ManimColor(tick.get_stroke_color()) == ManimColor(RED)


def test_dc3_entering_ticks_fade_in_and_leaving_ticks_fade_out():
    ax, curve = system()

    def opacities() -> dict[float, float]:
        out = {}
        for tick in ax.x_axis.ticks:
            if tick.has_points():
                value = round(float(ax.p2c(tick.get_center())[0]), 6)
                out[value] = float(tick.get_stroke_opacity())
        return out

    def construct(scene: Scene) -> None:
        scene.add(ax, curve)
        scene.play(ax.animate.set_x_range((0, 6)), run_time=1)

    frames = probe(construct, opacities)
    for value in (4.0, 5.0):
        seq = [frame.get(value, 0.0) for frame in frames]
        assert all(b >= a - 1e-9 for a, b in pairwise(seq)), (value, seq)
        assert ax.x_axis.ticks.at(value).get_stroke_opacity() == 1
    for value in (-2.0, -1.0):
        seq = [frame.get(value, 0.0) for frame in frames]
        assert all(b <= a + 1e-9 for a, b in pairwise(seq)), (value, seq)
        assert value not in tick_values(ax)[0]


# --- DC-4 ----------------------------------------------------------------------------


def test_dc4_a_step_change_mid_play_shows_the_locator_and_warns_nothing():
    ax, curve = system()
    ax.x_axis.set_locator(mp.MaxNLocator())

    def construct(scene: Scene) -> None:
        scene.add(ax, curve)
        scene.play(ax.animate.set_x_range((-300, 300)), run_time=1)

    frames = probe(construct, lambda: snapshot(ax, curve))
    for frame in frames:
        check_frame(frame, locator=mp.MaxNLocator())


def test_dc4_out_of_spares_warns_once_per_play():
    ax, curve = system()
    rng = np.random.default_rng(0)

    def construct(scene: Scene) -> None:
        scene.add(ax, curve)
        scene.play(
            ax.animate.set_x_range((1000, 1006)),
            rate_func=lambda t: float(rng.random()),
            run_time=2,
        )

    with pytest.warns(ManimPlotsWarning) as record:
        probe(construct, lambda: None)
    assert sum(issubclass(w.category, ManimPlotsWarning) for w in record) == 1


# --- DC-5 ----------------------------------------------------------------------------


def test_dc5_a_plot_parameter_animates_through_set_parameters():
    ax = mp.Axes(x_range=(-3, 3, 1), y_range=(-4, 4, 1), **LENGTHS)
    curve = ax.plot(lambda x, a=1: a * np.sin(x))

    def construct(scene: Scene) -> None:
        scene.add(ax, curve)
        scene.play(curve.animate.set_parameters(a=3), run_time=1)

    frames = probe(construct, lambda: np.array(curve.points, copy=True))
    for points, alpha in zip(frames, alphas(len(frames)), strict=True):
        a = 1 + 2 * alpha
        other = mp.Axes(x_range=(-3, 3, 1), y_range=(-4, 4, 1), **LENGTHS)
        assert_same_curve(points, other.plot(lambda x, a=a: a * np.sin(x)).points, TOL)
    assert curve.parameters["a"].value == 3


def test_dc5_an_unknown_parameter_raises_outside_and_inside_animate():
    ax = mp.Axes(x_range=(-3, 3, 1), y_range=Y, **LENGTHS)
    curve = ax.plot(lambda x, a=1: a * np.sin(x))
    with pytest.raises(ValueError, match="b"):
        curve.set_parameters(b=2)
    with pytest.raises(ValueError, match="b"):
        curve.animate.set_parameters(b=2)


# --- DC-6 ----------------------------------------------------------------------------


def test_dc6_transform_between_systems_interpolates_and_replots():
    ax, curve = system()
    start = np.array(ax.c2p(-3, Y[0]), dtype=float)
    other = mp.Axes(x_range=(0, 10, 1), y_range=Y, **LENGTHS).shift(UP)

    def construct(scene: Scene) -> None:
        scene.add(ax, curve)
        scene.play(Transform(ax, other), run_time=1)

    frames = probe(construct, lambda: snapshot(ax, curve))
    for frame, alpha in zip(frames, alphas(len(frames)), strict=True):
        lo, hi = frame["range"]
        assert abs(lo - 3 * alpha + 3) < 1e-9 and abs(hi - 3 - 7 * alpha) < 1e-9
        np.testing.assert_allclose(frame["corner"], start + alpha * UP, atol=1e-9)
        check_frame(frame)
    np.testing.assert_array_equal(ax.x.range.value, [0, 10])
    before = np.array(curve.points, copy=True)
    ax.shift(RIGHT)
    np.testing.assert_allclose(curve.points, before + RIGHT, atol=1e-9)
    assert rebuilds(ax, curve)


def test_dc6_ticks_of_another_locator_end_as_the_targets():
    ax, curve = system()
    other = mp.Axes(x_range=(0, 10, 2), y_range=Y, **LENGTHS)
    play(ax, curve, Transform(ax, other))
    assert tick_values(ax)[0] == tick_values(other)[0]


def test_dc6_a_change_of_scale_type_names_fade_transform():
    ax, curve = system()
    log = mp.Axes(x_range=(0.1, 100), y_range=Y, x_scale="log", **LENGTHS)
    with pytest.raises(ValueError, match="FadeTransform"):
        play(ax, curve, Transform(ax, log))


# --- DC-7 ----------------------------------------------------------------------------


def test_dc7_replacement_transform_hands_the_artists_over():
    ax, curve = system()
    new_ax = mp.Axes(x_range=(0, 10, 1), y_range=Y, **LENGTHS).shift(DOWN)
    play(ax, curve, ReplacementTransform(ax, new_ax))
    assert list(new_ax.artists) == [curve]
    assert list(ax.artists) == []
    before = np.array(curve.points, copy=True)
    new_ax.shift(RIGHT)
    np.testing.assert_allclose(curve.points, before + RIGHT, atol=1e-9)
    new_ax.x.range = (0, 5)
    frame = {"range": (0.0, 5.0), "corner": np.array(new_ax.c2p(0, Y[0]))}
    assert_same_curve(curve.points, oracle(frame)[0], TOL)
