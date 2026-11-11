"""The public surface is annotated, and the annotations resolve (F-1002, F-1005).

Rows TY-1 and TY-3 of `docs/acceptance/13-hardening.md`. `tests/usage/test_usage.py`
(TY-2) checks that the annotations say what the code does, through mypy in the gate.
"""

from __future__ import annotations

import enum
import inspect
import typing
from collections.abc import Callable, Iterator

import numpy as np
import pytest

import manim_plots as mp
from manim_plots.mobjects.axis import Axis

SKIP = {"__version__", "COLOR_CYCLE"}


def public_objects() -> dict[str, object]:
    names = (set(mp.__all__) - SKIP) | {"Axes", "NumberPlane"}
    found: dict[str, object] = {name: getattr(mp, name) for name in sorted(names)}
    found["Axis"] = Axis
    return found


def own_callables(
    owner: str, obj: object
) -> Iterator[tuple[str, Callable[..., object]]]:
    """The callables a public name defines in this library: a function itself, or a
    class's own public methods, its `__init__` and its properties' getters."""
    if inspect.isfunction(obj):
        yield owner, obj
        return
    if not inspect.isclass(obj) or issubclass(obj, enum.Enum):
        return
    for klass in obj.__mro__:
        if not klass.__module__.startswith("manim_plots"):
            continue
        for name, member in vars(klass).items():
            if name.startswith("_") and name != "__init__":
                continue
            if isinstance(member, property) and member.fget is not None:
                yield f"{owner}.{name}", member.fget
            elif isinstance(member, (staticmethod, classmethod)):
                yield f"{owner}.{name}", member.__func__
            elif inspect.isfunction(member) and member.__module__.startswith(
                "manim_plots"
            ):
                # Not typing's own `__init__` that `Protocol` puts on the class.
                yield f"{owner}.{name}", member


CALLABLES = sorted(
    {
        name: func
        for owner, obj in public_objects().items()
        for name, func in own_callables(owner, obj)
    }.items()
)


@pytest.mark.parametrize("name, func", CALLABLES, ids=[name for name, _ in CALLABLES])
def test_ty1_every_public_callable_is_fully_annotated(name, func):
    signature = inspect.signature(func)
    missing = [
        p.name
        for i, p in enumerate(signature.parameters.values())
        if p.annotation is inspect.Parameter.empty
        and not (i == 0 and p.name in {"self", "cls"})
    ]
    assert not missing, f"{name}: unannotated {missing}"
    assert signature.return_annotation is not inspect.Signature.empty, f"{name}: return"


@pytest.mark.parametrize("name, func", CALLABLES, ids=[name for name, _ in CALLABLES])
def test_ty1_the_annotations_resolve(name, func):
    typing.get_type_hints(func)


def test_ty3_plot_is_overloaded():
    assert len(typing.get_overloads(mp.CartesianAxes.plot)) >= 2


def test_ty3_a_parameter_has_a_typed_value():
    ax = mp.Axes()
    value = type(ax.x.range).value
    assert isinstance(value, property) and value.fget is not None
    assert "return" in typing.get_type_hints(value.fget)
    assert isinstance(ax.x.range.value, np.ndarray)


def test_ty3_parts_are_reached_by_attribute_and_value():
    ax = mp.Axes()
    assert ax.x_axis is ax.x
    tick = ax.x_axis.ticks.at(1.0)
    assert tick in ax.x_axis.ticks.submobjects
