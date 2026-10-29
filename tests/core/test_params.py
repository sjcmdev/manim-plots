"""Parameters: descriptors, version counters and bindings (F-110, F-911, F-918).

Rows PA-1 to PA-9 of `docs/acceptance/07-sources-shape-params.md`. The foreign source is
a duck-typed stand-in for Manim's `ValueTracker`, because the core cannot import Manim;
the last test checks the real one.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from manim_plots.core.params import Param, Parameter


class Tracker:
    """The part of `ValueTracker` a binding uses."""

    def __init__(self, value: object) -> None:
        self.value = value
        self.reads = 0

    def get_value(self) -> object:
        self.reads += 1
        return self.value


def positive(value: object) -> float:
    if not isinstance(value, (int, float)):
        raise TypeError("value must be a number")
    if not value > 0:
        raise ValueError("value must be positive")
    return float(value)


# --- PA-1 to PA-3: values ----------------------------------------------------------


def test_pa1_validation_runs_on_the_initial_value():
    with pytest.raises(ValueError):
        Parameter(-1.0, name="width", validate=positive)
    with pytest.raises(TypeError):
        Parameter("1", name="width", validate=positive)


def test_pa1_a_refused_assignment_changes_nothing():
    p = Parameter(2.0, name="width", validate=positive)
    version = p.version
    with pytest.raises(ValueError):
        p.value = 0.0
    assert p.value == 2.0
    assert p.version == version


def test_pa1_the_name_is_kept():
    assert Parameter(1.0, name="width").name == "width"


def test_pa2_an_array_is_copied_read_only():
    data = np.array([1.0, 2.0])
    p = Parameter(data, name="range")
    data[0] = 99.0
    assert p.value[0] == 1.0
    assert not p.value.flags.writeable


def test_pa2_a_sequence_of_numbers_becomes_a_read_only_array():
    p = Parameter((0, 10), name="range")
    assert isinstance(p.value, np.ndarray)
    np.testing.assert_array_equal(p.value, [0, 10])
    assert not p.value.flags.writeable


def test_pa2_a_scalar_stays_a_scalar():
    assert Parameter(3.5, name="a").value == 3.5
    assert not isinstance(Parameter(3.5, name="a").value, np.ndarray)


def test_pa3_every_assignment_bumps_the_version_even_to_an_equal_value():
    p = Parameter(1.0, name="a")
    v0 = p.version
    p.value = 1.0
    p.value = 2.0
    assert p.version == v0 + 2


# --- PA-4 to PA-7: bindings --------------------------------------------------------


def test_pa4_a_foreign_source_has_get_value():
    p = Parameter(0.0, name="a")
    tracker = Tracker(1.5)
    p.bind(tracker)
    assert p.tracker is tracker


def test_pa4_a_callable_without_get_value_is_a_callable_binding():
    p = Parameter(0.0, name="a")
    p.bind(lambda: 4.0)
    p.poll(1)
    assert p.value == 4.0


def test_pa4_anything_else_is_refused():
    with pytest.raises(TypeError):
        Parameter(0.0, name="a").bind(3.0)


def test_pa4_assigning_unbinds_and_unbind_keeps_the_last_value():
    p = Parameter(0.0, name="a")
    p.bind(Tracker(2.0))
    p.poll()
    p.value = 5.0
    assert p.tracker is None
    p.bind(Tracker(7.0))
    p.poll()
    p.unbind()
    assert p.tracker is None
    assert p.value == 7.0


def test_pa5_a_foreign_change_bumps_the_version_once():
    tracker = Tracker(1.0)
    p = Parameter(0.0, name="a")
    p.bind(tracker)
    first = p.poll()
    assert p.value == 1.0
    assert p.poll() == first
    tracker.value = 2.0
    assert p.poll() == first + 1
    assert p.value == 2.0
    assert p.poll() == first + 1


def test_pa5_nan_equals_nan():
    tracker = Tracker(math.nan)
    p = Parameter(0.0, name="a")
    p.bind(tracker)
    first = p.poll()
    tracker.value = float("nan")
    assert p.poll() == first


def test_pa5_arrays_compare_by_content_nan_aware():
    tracker = Tracker(np.array([1.0, np.nan]))
    p = Parameter(np.zeros(2), name="a")
    p.bind(tracker)
    first = p.poll()
    tracker.value = np.array([1.0, np.nan])
    assert p.poll() == first
    tracker.value = np.array([1.0, 2.0])
    assert p.poll() == first + 1


def test_pa5_an_in_place_change_of_the_source_is_seen():
    live = np.array([1.0, 2.0])
    tracker = Tracker(live)
    p = Parameter(np.zeros(2), name="a")
    p.bind(tracker)
    first = p.poll()
    live[1] = 3.0
    assert p.poll() == first + 1
    np.testing.assert_array_equal(p.value, [1.0, 3.0])


def test_pa5_a_foreign_value_is_validated():
    tracker = Tracker(-1.0)
    p = Parameter(1.0, name="a", validate=positive)
    p.bind(tracker)
    with pytest.raises(ValueError):
        p.poll()


def test_pa6_a_callable_binding_is_dirty_once_per_token():
    calls = []

    def source() -> float:
        calls.append(None)
        return 3.0

    p = Parameter(0.0, name="a")
    p.bind(source)
    v1 = p.poll(1)
    assert p.poll(1) == v1
    assert len(calls) == 1
    assert p.poll(2) == v1 + 1
    assert len(calls) == 2
    assert p.value == 3.0
    assert len(calls) == 2


def test_pa6_polling_a_callable_binding_needs_a_token():
    p = Parameter(0.0, name="a")
    p.bind(lambda: 1.0)
    with pytest.raises(ValueError):
        p.poll()


def test_pa7_version_reads_without_polling():
    tracker = Tracker(1.0)
    p = Parameter(0.0, name="a")
    p.bind(tracker)
    reads = tracker.reads
    _ = p.version
    assert tracker.reads == reads


def test_pa7_an_unbound_poll_changes_nothing():
    p = Parameter(1.0, name="a")
    assert p.poll() == p.version
    assert p.poll(5) == p.version


# --- PA-8: the descriptor ----------------------------------------------------------


class Axis:
    range = Param((0.0, 10.0))
    width = Param(1.0, validate=positive)


def test_pa8_each_instance_owns_a_named_parameter():
    a, b = Axis(), Axis()
    assert isinstance(a.range, Parameter)
    assert a.range is a.range
    assert a.range is not b.range
    assert a.range.name == "range"


def test_pa8_assignment_sets_the_value():
    a = Axis()
    a.range = (0, 30)
    np.testing.assert_array_equal(a.range.value, [0, 30])
    np.testing.assert_array_equal(Axis().range.value, [0, 10])


def test_pa8_assignment_is_validated():
    a = Axis()
    with pytest.raises(ValueError):
        a.width = -1.0
    assert a.width.value == 1.0


def test_pa8_the_class_attribute_is_the_descriptor():
    assert isinstance(Axis.__dict__["range"], Param)
    assert Axis.range is Axis.__dict__["range"]


def test_pa8_no_setattr_override():
    assert Axis.__setattr__ is object.__setattr__


def test_pa5_a_manim_value_tracker_binds():
    from manim import ValueTracker

    tracker = ValueTracker(2.0)
    p = Parameter(0.0, name="a")
    p.bind(tracker)
    first = p.poll()
    assert p.value == 2.0
    tracker.set_value(4.0)
    assert p.poll() == first + 1
