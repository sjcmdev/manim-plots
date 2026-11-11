"""Manim's animations on a plot and on its axes, against plain twins (F-905, F-906,
F-916).

Rows MX-1 and MX-2 of `docs/acceptance/11b-data-channel.md`. A **twin** is a plain
`VMobject` with a library leaf's points and style (`helpers.plain`), given the same
animation in the same play. The end state must equal the twin's; what happens at the
next range change depends on the animation's kind (F-905): an introducer, an indication
or a movement leaves the curve attached, so it rebuilds; a remover or a transform to a
plain target leaves it detached, so it stays put.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import pytest
from manim import (
    PI,
    RIGHT,
    UP,
    AnimationGroup,
    ApplyWave,
    Circle,
    Circumscribe,
    Create,
    DrawBorderThenFill,
    FadeIn,
    FadeOut,
    GrowFromCenter,
    Homotopy,
    Indicate,
    LaggedStart,
    Mobject,
    MoveToTarget,
    ReplacementTransform,
    Rotate,
    Scene,
    ShowPassingFlash,
    ShrinkToCenter,
    Square,
    Succession,
    Transform,
    Uncreate,
    VGroup,
    Wiggle,
    Write,
)

import manim_plots as mp
from manim_plots.core.sources import CHORD_TOLERANCE

from .helpers import assert_same_curve, plain, probe


def system():
    ax = mp.Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1), x_length=6, y_length=4)
    return ax, ax.plot(np.sin)


def wave(x: float, y: float, z: float, t: float) -> tuple[float, float, float]:
    return (x, y + 0.3 * t * np.sin(2 * x), z)


def to_target(mob: Mobject) -> MoveToTarget:
    mob.generate_target()
    assert mob.target is not None
    mob.target.shift(UP)
    return MoveToTarget(mob)


Make = Callable[..., Any]

# name: (animation on one mobject, does the curve still follow its data afterwards)
ON_CURVE: dict[str, tuple[Make, bool]] = {
    "Create": (Create, True),
    "Write": (Write, True),
    "DrawBorderThenFill": (DrawBorderThenFill, True),
    "FadeIn": (FadeIn, True),
    "GrowFromCenter": (GrowFromCenter, True),
    "Uncreate": (Uncreate, False),
    "FadeOut": (FadeOut, False),
    # A transform to a copy of the curve, an artist target: adopted, so it rebuilds.
    "ShrinkToCenter": (ShrinkToCenter, True),
    "ShowPassingFlash": (lambda m: ShowPassingFlash(m, time_width=0.5), False),
    "Indicate": (Indicate, True),
    "Wiggle": (Wiggle, True),
    "Circumscribe": (Circumscribe, True),
    "ApplyWave": (ApplyWave, True),
    "Rotate": (lambda m: Rotate(m, PI / 3), True),
    "Transform to a Circle": (lambda m: Transform(m, Circle()), False),
    "ReplacementTransform to a Circle": (
        lambda m: ReplacementTransform(m, Circle()),
        False,
    ),
    "MoveToTarget": (to_target, True),
    ".animate.shift": (lambda m: m.animate.shift(RIGHT), True),
    # No target: S with the final shape (ADR 0003 §5, rule 6), so it stays.
    "Homotopy": (lambda m: Homotopy(wave, m), False),
}


def composed(kind: str, make_a: Make, make_b: Make) -> Make:
    """A composition of two animations of ``ON_CURVE`` on one mobject and a square."""

    def make(mob: Mobject) -> Any:
        square = Square().shift(3 * UP)
        if kind == "AnimationGroup":
            return AnimationGroup(make_a(mob), make_b(square))
        if kind == "Succession":
            return Succession(make_a(mob), make_b(mob))
        return LaggedStart(make_a(mob), make_b(square), lag_ratio=0.5)

    return make


COMPOSITIONS: dict[str, tuple[Make, bool]] = {
    "AnimationGroup(Create, FadeIn)": (
        composed("AnimationGroup", Create, FadeIn),
        True,
    ),
    "Succession(Create, Indicate)": (composed("Succession", Create, Indicate), True),
    "LaggedStart(Create, Create)": (composed("LaggedStart", Create, Create), True),
}

CASES = ON_CURVE | COMPOSITIONS
NON_AFFINE = {"Homotopy", "ApplyWave", "Wiggle"}


@pytest.mark.parametrize("name", list(CASES))
def test_mx1_an_animation_on_the_curve_ends_as_on_its_twin(name):
    make, follows = CASES[name]
    ax, curve = system()
    twin = plain(curve)

    def construct(scene: Scene) -> None:
        scene.add(ax, curve, twin)
        scene.play(make(curve), make(twin))

    probe(construct, lambda: None)
    atol = 1e-6 if name in NON_AFFINE else 1e-9
    assert curve.points.shape == twin.points.shape
    np.testing.assert_allclose(curve.points, twin.points, atol=atol)
    before = np.array(curve.points, copy=True)
    ax.x.range = (-2, 2)
    if follows:
        assert not np.array_equal(curve.points, before)
    else:
        np.testing.assert_array_equal(curve.points, before)


def leaves_of(ax) -> list[Any]:
    """Every family member of ``ax`` with points, the frame included, in family order:
    the order Manim's animations walk.
    """
    return [m for m in ax.get_family() if m.has_points()]


ON_AXES: dict[str, Make] = {
    "Create": Create,
    "FadeIn": FadeIn,
    "Indicate": Indicate,
    "Rotate": lambda m: Rotate(m, PI / 6),
    ".animate.shift": lambda m: m.animate.shift(RIGHT + 0.5 * UP),
    "Wiggle": Wiggle,
}


@pytest.mark.parametrize("name", list(ON_AXES))
def test_mx1_an_animation_on_the_axes_moves_their_leaves_as_twins(name):
    ax, curve = system()
    twins = VGroup(*[plain(m) for m in leaves_of(ax)])

    def construct(scene: Scene) -> None:
        scene.add(ax, curve, twins)
        scene.play(ON_AXES[name](ax), ON_AXES[name](twins))

    probe(construct, lambda: None)
    for leaf, twin in zip(leaves_of(ax), twins, strict=True):
        if leaf is ax.frame:
            continue
        np.testing.assert_allclose(leaf.points, twin.points, atol=1e-9)
    assert_same_curve(curve.points, ax.plot(np.sin).points, 2 * CHORD_TOLERANCE)


FRAME_BY_FRAME: dict[str, Make] = {
    "Create": Create,
    "Write": Write,
    "Uncreate": Uncreate,
    "FadeIn": FadeIn,
    "Transform to a Circle": lambda m: Transform(m, Circle()),
    "Indicate": Indicate,
}


def state(mob: Mobject) -> tuple[np.ndarray, float, float]:
    return (
        np.array(mob.points, copy=True),
        float(mob.get_stroke_opacity()),
        float(mob.get_stroke_width()),
    )


@pytest.mark.parametrize("name", list(FRAME_BY_FRAME))
def test_mx2_every_frame_on_the_curve_equals_its_twins(name):
    ax, curve = system()
    twin = plain(curve)
    make = FRAME_BY_FRAME[name]

    def construct(scene: Scene) -> None:
        scene.add(ax, curve, twin)
        scene.play(make(curve), make(twin))

    frames = probe(construct, lambda: (state(curve), state(twin)))
    assert len(frames) >= 5
    for ours, theirs in frames:
        assert ours[0].shape == theirs[0].shape
        np.testing.assert_allclose(ours[0], theirs[0], atol=1e-9)
        assert ours[1:] == pytest.approx(theirs[1:], abs=1e-9)


@pytest.mark.parametrize("name", ["Create", "FadeIn", "Indicate"])
def test_mx2_every_frame_on_the_axes_equals_their_twins(name):
    # The frame's twin keeps Manim's lag slots the same: F-1008's difference for
    # `Create(ax)` is the frame's slot, which a group of the visible leaves lacks.
    ax, curve = system()
    twins = VGroup(*[plain(m) for m in leaves_of(ax)])
    make = FRAME_BY_FRAME[name]

    def record() -> list[tuple[np.ndarray, float, float]]:
        return [state(m) for m in leaves_of(ax) if m is not ax.frame] + [
            state(t)
            for m, t in zip(leaves_of(ax), twins, strict=True)
            if m is not ax.frame
        ]

    def construct(scene: Scene) -> None:
        scene.add(ax, curve, twins)
        scene.play(make(ax), make(twins))

    for frame in probe(construct, record):
        half = len(frame) // 2
        for ours, theirs in zip(frame[:half], frame[half:], strict=True):
            np.testing.assert_allclose(ours[0], theirs[0], atol=1e-9)
            assert ours[1:] == pytest.approx(theirs[1:], abs=1e-9)


# --- MX-4: an artist into an artist ---------------------------------------------


def pairs():
    def same_axes():
        ax, curve = system()
        return ax, curve, ax, ax.plot(np.cos)

    def lines():
        ax = mp.Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1), x_length=6, y_length=4)
        return (
            ax,
            ax.line([-2, 0, 2], [0, 1, 0]),
            ax,
            ax.line([-2, -1, 0, 1, 2], [1, 0, 1, 0, 1]),
        )

    def other_axes():
        ax, curve = system()
        other = mp.Axes(x_range=(0, 6, 1), y_range=(-2, 2, 1), x_length=6, y_length=4)
        return ax, curve, other.shift(UP), other.plot(np.cos)

    return {"same axes": same_axes, "lines": lines, "other axes": other_axes}


PAIRS = pairs()


@pytest.mark.parametrize("kind", ["Transform", "ReplacementTransform"])
@pytest.mark.parametrize("name", list(PAIRS))
def test_mx4_an_artist_transforms_into_another_as_twins_do(name, kind):
    _, a, _, b = PAIRS[name]()
    twin_a, twin_b = plain(a), plain(b)
    animation = Transform if kind == "Transform" else ReplacementTransform

    def construct(scene: Scene) -> None:
        scene.add(a, twin_a)
        scene.play(animation(a, b), animation(twin_a, twin_b))

    frames = probe(
        construct,
        lambda: (np.array(a.points, copy=True), np.array(twin_a.points, copy=True)),
    )
    assert len(frames) >= 5
    for ours, theirs in frames:
        assert ours.shape == theirs.shape
        np.testing.assert_allclose(ours, theirs, atol=1e-9)


@pytest.mark.parametrize("name", list(PAIRS))
def test_mx4_after_transform_the_artist_draws_the_target_on_its_system(name):
    _, a, b_ax, b = PAIRS[name]()

    def construct(scene: Scene) -> None:
        scene.add(a)
        scene.play(Transform(a, b))

    probe(construct, lambda: None)
    b_ax.x.range = (-1, 2)
    assert_same_curve(a.points, b.points, 2 * CHORD_TOLERANCE)


def test_mx4_after_replacement_the_target_is_in_the_scene():
    _, a, _, b = PAIRS["same axes"]()
    seen: dict[str, bool] = {}

    def construct(scene: Scene) -> None:
        scene.add(a)
        scene.play(ReplacementTransform(a, b))
        seen["a"] = a in scene.mobjects
        seen["b"] = b in scene.mobjects

    probe(construct, lambda: None)
    assert seen == {"a": False, "b": True}


# --- MX-5: become ---------------------------------------------------------------


@pytest.mark.parametrize("name", list(PAIRS))
def test_mx5_become_adopts_the_other_artist(name):
    _, a, b_ax, b = PAIRS[name]()
    a.become(b)
    np.testing.assert_allclose(a.points, b.points, atol=1e-12)
    b_ax.x.range = (-1, 2)
    assert_same_curve(a.points, b.points, 2 * CHORD_TOLERANCE)
