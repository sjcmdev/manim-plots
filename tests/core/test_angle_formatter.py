"""Task 22: `AngleFormatter`, rows AF-1 and AF-2 of `docs/acceptance/22-polar.md`.

The oracle is Manim's own `PolarPlane.get_radian_label`, called with `MathTex` replaced
by the identity so it returns its LaTeX string.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
from manim import PI, TAU, PolarPlane
from manim.mobject.graphing import coordinate_systems

import manim_plots as mp

TURNS = [k / 24 for k in range(25)] + [1 / 20, 3 / 20, 7 / 10, 1 / 3, 5 / 6]


def manim_label(monkeypatch, units: str, compact: bool, turn: float) -> str:
    monkeypatch.setattr(coordinate_systems, "MathTex", lambda s, **_: s)
    plane = SimpleNamespace(azimuth_units=units, azimuth_compact_fraction=compact)
    return PolarPlane.get_radian_label(plane, turn)  # type: ignore[arg-type]


def text(formatter, values) -> list[str]:
    return list(formatter.format_ticks(np.asarray(values, dtype=float)).text)


@pytest.mark.parametrize("units", ["PI radians", "TAU radians"])
@pytest.mark.parametrize("compact", [True, False])
def test_af1_radians_match_manims_radian_label(monkeypatch, units, compact):
    formatter = mp.AngleFormatter(units, compact_fraction=compact)
    expected = [manim_label(monkeypatch, units, compact, t) for t in TURNS]
    assert text(formatter, [t * TAU for t in TURNS]) == expected


def test_af1_degrees_gradians_and_turns():
    turns = [k / 36 for k in range(36)]
    angles = [t * TAU for t in turns]
    assert text(mp.AngleFormatter("degrees"), angles) == [
        f"{360 * t:g}" + r"^{\circ}" for t in turns
    ]
    assert text(mp.AngleFormatter("gradians"), angles) == [
        f"{400 * t:g}" + r"^{g}" for t in turns
    ]
    assert text(mp.AngleFormatter(None), angles) == [f"{t:g}" for t in turns]


def test_af1_is_a_formatter_and_refuses_unknown_units():
    assert isinstance(mp.AngleFormatter(), mp.Formatter)
    with pytest.raises(ValueError, match="units"):
        mp.AngleFormatter("radians")


def test_af1_max_denominator_limits_the_fraction():
    formatter = mp.AngleFormatter(max_denominator=4)
    assert text(formatter, [PI / 3.01]) == [r"\tfrac{\pi}{3}"]


def test_af2_on_an_axis_with_a_multiple_locator():
    ax = mp.Axes(
        x_range=(0, TAU, 1), y_range=(-1, 1, 1), axis_config={"include_numbers": True}
    )
    ax.x.set_locator(mp.MultipleLocator(PI / 2))
    ax.x.set_formatter(mp.AngleFormatter())
    values = [0, PI / 2, PI, 3 * PI / 2, TAU]
    assert text(mp.AngleFormatter(), values) == [
        "0",
        r"\tfrac{\pi}{2}",
        r"\pi",
        r"\tfrac{3\pi}{2}",
        r"2\pi",
    ]
    assert ax.x.numbers.at(PI / 2) is not None


def test_af2_negative_angles_keep_their_sign_outside():
    assert text(mp.AngleFormatter(), [-PI / 2, -PI, -3 * PI / 4]) == [
        r"-\tfrac{\pi}{2}",
        r"-\pi",
        r"-\tfrac{3\pi}{4}",
    ]
    assert text(mp.AngleFormatter(compact_fraction=False), [-PI / 2]) == [
        r"-\tfrac{1}{2}\pi"
    ]
