"""Locators and the ticks of one axis (F-401-F-413).

Rows K-1, L-1 to L-18 and T-1 to T-7 of
`docs/acceptance/08-ticks-formatters-lifecycle.md`.
Oracles: exact multiples computed here from integers, matplotlib's step rule worked by
hand, and the invariants of F-413 (one key per value on every range, no two values with
one key) under Hypothesis.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from manim_plots.core.scales import LinearScale, LogScale, SymLogScale
from manim_plots.core.ticks import (
    MAX_GENERATED,
    FixedLocator,
    FunctionLocator,
    Locator,
    LogLocator,
    MaxNLocator,
    MinorCountLocator,
    MultipleLocator,
    NullLocator,
    SymLogLocator,
    Tick,
    as_locator,
    axis_ticks,
    round_key,
)

LIN = LinearScale()
LOG = LogScale()


def values(locator: Locator, lo: float, hi: float, scale=LIN, max_ticks: int = 10):
    return locator.values(lo, hi, scale, max_ticks).tolist()


# --- K-1 ---------------------------------------------------------------------------


def test_k1_round_key_merges_float_noise_and_signed_zero():
    assert round_key(0.1 + 0.2) == round_key(0.3)
    assert round_key(-0.0) == round_key(0.0)
    assert hash(round_key(-0.0)) == hash(round_key(0.0))
    assert round_key(1.23456789012345) == 1.23456789012
    assert round_key(1.0) != round_key(1.0 + 1e-9)


@pytest.mark.parametrize("bad", [math.nan, math.inf])
def test_k1_round_key_refuses_non_finite(bad):
    with pytest.raises(ValueError):
        round_key(bad)


# --- L-1 to L-7: the shared rules ----------------------------------------------------

ALL = [
    MultipleLocator(0.5),
    MaxNLocator(),
    LogLocator(),
    SymLogLocator(),
    FixedLocator([0.5, 2.0, 7.0]),
    NullLocator(),
    MinorCountLocator(MultipleLocator(1.0)),
    FunctionLocator(lambda lo, hi: [1.0, 3.0, 2.0]),
]


@pytest.mark.parametrize("locator", ALL, ids=lambda loc: type(loc).__name__)
def test_l1_every_locator_is_a_locator(locator):
    assert isinstance(locator, Locator)


@pytest.mark.parametrize("locator", ALL, ids=lambda loc: type(loc).__name__)
def test_l1_a_reversed_range_gives_descending_values(locator):
    scale = LOG if isinstance(locator, LogLocator) else LIN
    up = locator.values(0.1, 9.0, scale, 10)
    down = locator.values(9.0, 0.1, scale, 10)
    assert up.dtype == np.float64
    np.testing.assert_array_equal(down, up[::-1])
    assert (np.diff(up) > 0).all()


@pytest.mark.parametrize("locator", ALL, ids=lambda loc: type(loc).__name__)
def test_l1_an_empty_range_has_no_ticks(locator):
    assert locator.values(2.0, 2.0, LIN, 10).shape == (0,)


@pytest.mark.parametrize("bad", [(math.nan, 1.0), (0.0, math.inf)])
def test_l1_a_non_finite_range_raises(bad):
    with pytest.raises(ValueError):
        lo, hi = bad
        MultipleLocator(1.0).values(lo, hi, LIN, 10)


def test_l1_max_ticks_must_be_a_non_negative_int():
    with pytest.raises(TypeError):
        MaxNLocator().values(0.0, 1.0, LIN, 2.5)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        MaxNLocator().values(0.0, 1.0, LIN, True)
    with pytest.raises(ValueError):
        MaxNLocator().values(0.0, 1.0, LIN, -1)


def test_l2_values_outside_the_domain_are_dropped_without_error():
    assert values(MultipleLocator(1.0), -3.0, 3.0, LOG) == [1.0, 2.0, 3.0]
    assert values(FixedLocator([-1.0, 0.0, 5.0]), -3.0, 10.0, LOG) == [5.0]


def test_l2_only_values_inside_the_range():
    assert values(FixedLocator([0.5, 2.0, 7.0]), 1.0, 5.0) == [2.0]


def test_l3_multiples_are_exact_products():
    got = values(MultipleLocator(0.1), 0.0, 1.0, max_ticks=100)
    assert got == [k * 0.1 for k in range(11)]


@given(
    st.floats(1e-3, 1e3),
    st.floats(-1e4, 1e4),
    st.floats(1e-2, 1e4),
    st.floats(-1e4, 1e4),
)
def test_l4_l5_a_multiple_keys_each_value_once_on_every_range(step, lo, span, shift):
    if span / step > MAX_GENERATED / 2:
        return
    locator = MultipleLocator(step)
    hi = lo + span
    first = locator.values(lo, hi, LIN, 10)
    keys = [locator.key(v) for v in first]
    assert len(set(keys)) == len(keys)
    other = locator.values(lo + shift, hi + shift, LIN, 10)
    shared = set(first.tolist()) & set(other.tolist())
    by_value = {v: locator.key(v) for v in other}
    for v in shared:
        assert by_value[v] == locator.key(v)


@given(st.floats(-1e6, 1e6), st.floats(1e-3, 1e6), st.integers(1, 30))
def test_l4_l5_maxn_keys_are_unique_and_range_free(lo, span, max_ticks):
    locator = MaxNLocator()
    got = locator.values(lo, lo + span, LIN, max_ticks)
    keys = [locator.key(v) for v in got]
    assert len(set(keys)) == len(keys)
    assert keys == [round_key(v) for v in got]


@given(st.floats(-100.0, 100.0), st.floats(0.5, 100.0), st.integers(1, 20))
def test_l6_contains_agrees_with_values(lo, span, max_ticks):
    hi = lo + span
    for locator in (MultipleLocator(0.5), MaxNLocator(), SymLogLocator()):
        got = locator.values(lo, hi, LIN, max_ticks)
        for v in got:
            assert locator.contains(float(v), lo, hi, LIN, max_ticks)
        for probe in (lo - 1.0, hi + 1.0):
            assert not locator.contains(probe, lo, hi, LIN, max_ticks)


def test_l6_contains_respects_the_density():
    locator = MaxNLocator()
    assert locator.contains(1.0, 0.0, 10.0, LIN, 11)
    assert not locator.contains(1.0, 0.0, 10.0, LIN, 3)


def test_l7_too_many_ticks_raise_naming_the_parameter():
    with pytest.raises(ValueError, match="step"):
        MultipleLocator(1e-9).values(0.0, 1.0, LIN, 10)


# --- L-10 to L-18: each locator -------------------------------------------------------


@pytest.mark.parametrize("step", [0.0, -1.0, math.nan, math.inf])
def test_l10_a_degenerate_step_raises_naming_it(step):
    with pytest.raises(ValueError, match="step"):
        MultipleLocator(step)


def test_l10_keys_are_integer_multiples():
    locator = MultipleLocator(0.25)
    assert [locator.key(v) for v in locator.values(-0.5, 0.5, LIN, 10)] == [
        -2,
        -1,
        0,
        1,
        2,
    ]
    assert locator.key(0.75) == 3


def test_l10_range_ends_are_inclusive_within_the_tolerance():
    assert values(MultipleLocator(0.1), 0.0, 0.30000000000000004) == [
        0.0,
        0.1,
        0.2,
        3 * 0.1,
    ]
    assert values(MultipleLocator(1.0), 0.0, 3.0 - 1e-10) == [0.0, 1.0, 2.0, 3.0]
    assert values(MultipleLocator(1.0), 0.0, 3.0 - 1e-6) == [0.0, 1.0, 2.0]


def test_l10_contains_off_grid_is_false():
    locator = MultipleLocator(0.5)
    assert locator.contains(1.5, 0.0, 2.0, LIN, 10)
    assert not locator.contains(1.25, 0.0, 2.0, LIN, 10)
    assert not locator.contains(2.5, 0.0, 2.0, LIN, 10)


def test_l10_max_ticks_is_ignored():
    assert values(MultipleLocator(1.0), 0.0, 10.0, max_ticks=2) == [
        float(k) for k in range(11)
    ]


@pytest.mark.parametrize(
    "lo, hi, n, expected",
    [
        (0.0, 10.0, 6, [0.0, 2.0, 4.0, 6.0, 8.0, 10.0]),
        (0.0, 10.0, 11, [float(k) for k in range(11)]),
        (0.0, 10.0, 3, [0.0, 5.0, 10.0]),
        (0.0, 1.0, 5, [0.0, 0.25, 0.5, 0.75, 1.0]),
        (-3.0, 7.0, 6, [-2.0, 0.0, 2.0, 4.0, 6.0]),
        (0.3, 0.7, 1, [0.5]),
    ],
)
def test_l11_maxn_picks_the_smallest_nice_step_that_fits(lo, hi, n, expected):
    np.testing.assert_allclose(values(MaxNLocator(n), lo, hi, max_ticks=100), expected)


def test_l11_maxn_never_exceeds_the_label_space():
    for max_ticks in range(1, 15):
        got = MaxNLocator().values(0.0, 13.7, LIN, max_ticks)
        assert 0 < len(got) <= max_ticks
    assert values(MaxNLocator(n=20), 0.0, 10.0, max_ticks=3) == [0.0, 5.0, 10.0]
    assert values(MaxNLocator(), 0.0, 10.0, max_ticks=0) == []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"n": 0},
        {"steps": ()},
        {"steps": (2, 1)},
        {"steps": (0.5, 1)},
        {"steps": (1, 11)},
    ],
    ids=str,
)
def test_l11_impossible_parameters_raise(kwargs):
    with pytest.raises(ValueError):
        MaxNLocator(**kwargs)


def test_l12_decades_and_subdivisions():
    assert values(LogLocator(), 0.5, 2000.0, LOG) == [1.0, 10.0, 100.0, 1000.0]
    got = values(LogLocator(subs=(1.0, 2.0, 5.0)), 1.0, 100.0, LOG, max_ticks=50)
    np.testing.assert_allclose(got, [1, 2, 5, 10, 20, 50, 100])
    assert values(LogLocator(base=2.0), 1.0, 16.0, LOG) == [1.0, 2.0, 4.0, 8.0, 16.0]


def test_l12_keys_are_decade_and_sub_index():
    locator = LogLocator(subs=(1.0, 2.0, 5.0))
    assert locator.key(1.0) == (0, 0)
    assert locator.key(500.0) == (2, 2)
    assert locator.key(0.02) == (-2, 1)
    assert locator.key(0.001) == (-3, 0)
    off = locator.key(3.0)
    assert isinstance(off, tuple) and off[0] == "off"
    with pytest.raises(ValueError):
        locator.key(-1.0)


def test_l12_many_decades_are_thinned():
    got = LogLocator().values(1e-10, 1e10, LOG, 6)
    assert 0 < len(got) <= 6
    decades = np.log10(got)
    np.testing.assert_allclose(decades, np.round(decades))
    stride = np.diff(np.round(decades))
    assert (stride == stride[0]).all()
    assert all(round(d) % int(stride[0]) == 0 for d in decades)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"base": 1.0},
        {"subs": ()},
        {"subs": (0.5,)},
        {"subs": (1.0, 10.0)},
        {"subs": (5.0, 2.0)},
    ],
    ids=str,
)
def test_l12_impossible_parameters_raise(kwargs):
    with pytest.raises(ValueError):
        LogLocator(**kwargs)


def test_l13_symlog_ticks_zero_and_decades_on_both_sides():
    symlog = SymLogScale()
    got = values(SymLogLocator(), -150.0, 1500.0, symlog, max_ticks=20)
    assert got == [-100.0, -10.0, -1.0, 0.0, 1.0, 10.0, 100.0, 1000.0]
    locator = SymLogLocator()
    assert locator.key(0.0) == (0,)
    assert locator.key(-10.0) == (-1, 1, 0)
    assert locator.key(100.0) == (1, 2, 0)


def test_l13_decades_start_at_the_threshold():
    got = values(
        SymLogLocator(linthresh=10.0),
        -1000.0,
        1000.0,
        SymLogScale(linthresh=10.0),
        max_ticks=20,
    )
    assert got == [-1000.0, -100.0, -10.0, 0.0, 10.0, 100.0, 1000.0]


def test_l14_fixed_entries_and_levels():
    fixed = FixedLocator(
        [1.0, (2.0,), (3.0, "three"), (0.5, "half", "minor"), (4.0, None, "major")]
    )
    assert values(fixed, 0.0, 10.0) == [1.0, 2.0, 3.0, 4.0]
    assert values(fixed.minor, 0.0, 10.0) == [0.5]
    assert fixed.label(3.0) == "three"
    assert fixed.label(1.0) is None
    assert all(isinstance(t, Tick) for t in fixed.entries)
    assert {t.level for t in fixed.entries} == {"major", "minor"}


@pytest.mark.parametrize(
    "entry, error",
    [
        ((1.0, "a", "major", "x"), ValueError),
        ((1.0, "a", "middle"), ValueError),
        ((math.nan, "a"), ValueError),
        ((1.0, 5), TypeError),
        ((), ValueError),
    ],
    ids=["arity", "level", "nan", "label type", "empty"],
)
def test_l14_a_malformed_entry_raises(entry, error):
    with pytest.raises(error):
        FixedLocator([entry])


def test_l14_two_entries_with_one_key_raise_naming_both():
    with pytest.raises(ValueError) as excinfo:
        FixedLocator([(0.3, "a"), (0.1 + 0.2, "b")])
    assert "a" in str(excinfo.value) or "0.3" in str(excinfo.value)


def test_l15_null_has_nothing():
    assert values(NullLocator(), 0.0, 10.0) == []
    assert not NullLocator().contains(1.0, 0.0, 10.0, LIN, 10)


def test_l16_minor_count_between_and_beyond_majors():
    minor = MinorCountLocator(MultipleLocator(1.0), n=4)
    got = minor.values(-0.5, 2.0, LIN, 10)
    np.testing.assert_allclose(
        got, [-0.4, -0.2, 0.2, 0.4, 0.6, 0.8, 1.2, 1.4, 1.6, 1.8], atol=1e-12
    )


def test_l16_minor_count_needs_two_majors():
    assert values(MinorCountLocator(MultipleLocator(10.0), n=4), 1.0, 9.0) == []
    with pytest.raises(ValueError):
        MinorCountLocator(MultipleLocator(1.0), n=0)


def test_l17_a_wrapped_callable_is_filtered_and_ordered():
    locator = FunctionLocator(lambda lo, hi: [5.0, -1.0, 2.0, 50.0])
    assert values(locator, 0.0, 10.0) == [2.0, 5.0]
    assert values(locator, 10.0, 0.0) == [5.0, 2.0]


def test_l17_a_callable_emitting_one_key_twice_raises():
    locator = FunctionLocator(lambda lo, hi: [0.3, 0.1 + 0.2])
    with pytest.raises(ValueError):
        locator.values(0.0, 1.0, LIN, 10)


def test_l18_as_locator():
    m = MultipleLocator(1.0)
    assert as_locator(m) is m
    assert isinstance(as_locator(lambda lo, hi: [1.0]), FunctionLocator)
    with pytest.raises(TypeError):
        as_locator(3.0)


# --- T-1 to T-7: the ticks of one axis ------------------------------------------------


def ticks(*args, **kwargs) -> list[tuple[float, str, object, object]]:
    return [(t.value, t.level, t.key, t.label) for t in axis_ticks(*args, **kwargs)]


def test_t1_minor_ticks_on_majors_are_removed():
    got = axis_ticks(MultipleLocator(1.0), MultipleLocator(0.5), 0.0, 2.0, LIN, 10)
    assert [(t.value, t.level) for t in got] == [
        (0.0, "major"),
        (0.5, "minor"),
        (1.0, "major"),
        (1.5, "minor"),
        (2.0, "major"),
    ]


def test_t2_ticks_whose_images_are_out_of_order_raise():
    class Backwards:
        domain, closed, increasing = (-math.inf, math.inf), (False, False), True

        def forward(self, x):
            return -np.asarray(x, dtype=float)

        def inverse(self, u):
            return -np.asarray(u, dtype=float)

        def limit_range(self, lo, hi, minpos):
            return lo, hi

    with pytest.raises(ValueError):
        axis_ticks(MultipleLocator(1.0), None, 0.0, 3.0, Backwards(), 10)


def test_t3_a_locator_that_repeats_a_key_is_named():
    class Repeating:
        def values(self, lo, hi, scale, max_ticks):
            return np.array([1.0, 2.0])

        def key(self, value):
            return "same"

        def contains(self, value, lo, hi, scale, max_ticks):
            return True

    with pytest.raises(ValueError, match="Repeating"):
        axis_ticks(Repeating(), None, 0.0, 3.0, LIN, 10)


def test_t4_replace_keeps_only_the_explicit_entries():
    explicit = FixedLocator([(0.5, "half"), (20.0, "far"), (1.5, None, "minor")])
    got = ticks(
        MultipleLocator(1.0), None, 0.0, 3.0, LIN, 10, explicit=explicit, mode="replace"
    )
    assert [(v, level, label) for v, level, _, label in got] == [
        (0.5, "major", "half"),
        (1.5, "minor", None),
    ]


def test_t5_add_lets_an_explicit_entry_win_whole_and_adds_the_rest():
    explicit = FixedLocator(
        [
            (2.0000000000000004, "two"),
            (2.5, "two and a half"),
            (1.25, "quarter", "minor"),
        ]
    )
    got = axis_ticks(
        MultipleLocator(1.0), MultipleLocator(0.5), 0.0, 3.0, LIN, 10, explicit=explicit
    )
    by_value = {t.value: t for t in got}
    two = by_value[2.0000000000000004]
    assert (two.level, two.key, two.label) == ("major", 2, "two")
    assert 2.0 not in by_value
    added = by_value[2.5]
    assert added.key == ("fixed", round_key(2.5))
    quarter = by_value[1.25]
    assert (quarter.level, quarter.key, quarter.label) == (
        "minor",
        ("fixed", 1.25),
        "quarter",
    )


def test_t6_the_merge_is_ordered_along_a_reversed_axis():
    explicit = FixedLocator([(2.5, "x")])
    got = axis_ticks(MultipleLocator(1.0), None, 3.0, 0.0, LIN, 10, explicit=explicit)
    assert [t.value for t in got] == [3.0, 2.5, 2.0, 1.0, 0.0]


def test_t6_generated_ticks_carry_their_locators_key_and_no_label():
    got = axis_ticks(MultipleLocator(0.5), None, 0.0, 1.0, LIN, 10)
    assert [(t.key, t.label) for t in got] == [(0, None), (1, None), (2, None)]


def test_t7_an_unknown_mode_raises():
    with pytest.raises(ValueError):
        axis_ticks(
            MultipleLocator(1.0),
            None,
            0.0,
            1.0,
            LIN,
            10,
            explicit=FixedLocator([0.5]),
            mode="merge",  # type: ignore[arg-type]
        )
