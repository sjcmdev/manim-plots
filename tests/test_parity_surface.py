"""Guard the Manim section of ``docs/parity-survey.md`` against upstream drift.

The survey gives a verdict to every public callable on Manim's graphing classes. If
upstream adds, removes or renames one, the document silently stops being an inventory.
This test fails instead, naming what moved.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path

from manim import (
    Axes,
    ComplexPlane,
    ImplicitFunction,
    NumberLine,
    NumberPlane,
    PolarPlane,
    ThreeDAxes,
)
from manim.mobject.graphing.coordinate_systems import CoordinateSystem
from manim.mobject.graphing.functions import FunctionGraph, ParametricFunction
from manim.mobject.graphing.scale import LinearBase, LogBase, _ScaleBase

SURVEY = Path(__file__).parents[1] / "docs" / "parity-survey.md"

SURVEYED_CLASSES = (
    CoordinateSystem,
    Axes,
    ThreeDAxes,
    NumberPlane,
    PolarPlane,
    ComplexPlane,
    NumberLine,
    ParametricFunction,
    FunctionGraph,
    ImplicitFunction,
    _ScaleBase,
    LinearBase,
    LogBase,
)


def live_surface() -> set[str]:
    """Public callables defined on the surveyed classes themselves."""
    names: set[str] = set()
    for cls in SURVEYED_CLASSES:
        names |= {
            name
            for name, value in vars(cls).items()
            if not name.startswith("_")
            and (
                inspect.isfunction(value)
                or isinstance(value, staticmethod | classmethod | property)
            )
        }
    return names


def surveyed_names() -> set[str]:
    """Method names in the first column of the survey's verdict tables."""
    text = SURVEY.read_text(encoding="utf-8")
    rows = re.findall(r"^\| `(\w+)` \|", text, re.MULTILINE)
    return set(rows)


def test_every_public_method_has_a_verdict():
    missing = sorted(live_surface() - surveyed_names())
    assert not missing, f"public in Manim but absent from the survey: {missing}"


def test_the_survey_names_no_method_that_is_gone():
    stale = sorted(surveyed_names() - live_surface())
    assert not stale, f"in the survey but no longer public in Manim: {stale}"


def test_the_surface_is_the_size_the_survey_claims():
    assert len(live_surface()) == 73
