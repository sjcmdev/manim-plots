"""Executable record of the ManimCE 0.21.0 defect audit.

These tests assert that the defects in ``docs/defect-audit-0.21.md`` still reproduce.
That is deliberate and inverted from a normal suite: a failure here means upstream
changed something, and the audit plus the requirements derived from it need revisiting.
Keep it free of rendering and of LaTeX so it runs in the default suite.

The ``type: ignore`` comments below are themselves audit evidence: Manim annotates
``LogBase.inverse_function`` as taking a ``float`` although its body branches on
``isinstance(value, np.ndarray)``, and annotates ``NumberLine.point_to_number`` as
taking a ``Sequence[float]`` although ``number_to_point`` returns an ``ndarray``. Its
own round trip does not type-check. See finding 15f in ``docs/defect-audit-0.21.md``.
"""

from __future__ import annotations

import numpy as np
import pytest
from manim import Axes, NumberLine
from manim.mobject.graphing.scale import LogBase


def unit_size(ax: Axes, axis: int) -> float:
    """Scene distance covered by one data unit along ``axis`` (0 = x, 1 = y)."""
    step = [0.0, 0.0]
    step[axis] = 1.0
    return float(np.linalg.norm(ax.c2p(*step) - ax.c2p(0, 0)))


def test_d1_tick_generation_accumulates_float_error():
    ticks = NumberLine(x_range=[0, 1, 0.1]).get_tick_range()
    assert any(t != round(float(t), 1) for t in ticks)


def test_d2_include_tip_drops_the_endpoint_tick():
    without = NumberLine(x_range=[0, 10, 1], include_tip=False).get_tick_range()
    with_tip = NumberLine(x_range=[0, 10, 1], include_tip=True).get_tick_range()
    assert len(without) == len(with_tip) + 1
    assert without[-1] == 10.0
    assert with_tip[-1] == 9.0


def test_d2_include_tip_leaves_the_mapping_alone():
    """The half of defect 2 that no longer holds: the mapping itself is unaffected."""
    a = NumberLine(x_range=[0, 10, 1], length=10, include_tip=False)
    b = NumberLine(x_range=[0, 10, 1], length=10, include_tip=True)
    assert np.allclose(a.number_to_point(10), b.number_to_point(10))


def test_d3_curves_are_not_clipped_to_the_viewport():
    ax = Axes(x_range=[-3, 3, 1], y_range=[-3, 3, 1], x_length=6, y_length=6)
    curve = ax.plot(lambda x: 1 / x, x_range=[0.1, 3], use_smoothing=False)
    assert curve.points[:, 1].max() > ax.c2p(0, 3)[1] + 1.0


def test_d4_equal_ranges_give_unequal_units():
    ax = Axes(x_range=[0, 10, 1], y_range=[0, 10, 1], x_length=10, y_length=4)
    assert not np.isclose(unit_size(ax, 0), unit_size(ax, 1))


def test_d5_unit_size_is_ignored_through_axis_config():
    ax = Axes(
        x_range=[0, 10, 1],
        y_range=[0, 10, 1],
        x_length=10,
        y_length=10,
        axis_config={"unit_size": 3},
    )
    assert not np.isclose(unit_size(ax, 0), 3.0)
    solo = NumberLine(x_range=[0, 10, 1], unit_size=3)
    solo_unit = float(np.linalg.norm(solo.number_to_point(1) - solo.number_to_point(0)))
    assert np.isclose(solo_unit, 3.0)


def test_d6_changing_x_range_leaves_the_tick_mobjects_stale():
    nl = NumberLine(x_range=[0, 5, 1])
    built = len(nl.ticks)
    nl.x_range = np.array([0.0, 10.0, 1.0])
    assert len(nl.get_tick_range()) != built
    assert len(nl.ticks) == built


def test_d7_there_is_no_legend_primitive():
    import manim

    assert not [n for n in dir(manim) if "legend" in n.lower()]
    assert not [n for n in dir(Axes) if "legend" in n.lower()]


def test_d8_log_inverse_lets_negatives_through_as_nan():
    log = LogBase(10)
    out = np.asarray(log.inverse_function(np.array([-5.0, 1.0, 10.0])))  # type: ignore[arg-type]
    assert np.isnan(out[0])
    log.inverse_function(np.array([-5.0, -1.0]))  # type: ignore[arg-type]  # guard never fires
    with pytest.raises(ValueError):
        log.inverse_function(np.array([0.0, 0.0]))  # type: ignore[arg-type]  # ... except on all zeros


def test_d9_log_axis_has_decade_ticks_only():
    ticks = NumberLine(x_range=[0, 3, 1], scaling=LogBase(10)).get_tick_range()
    assert list(ticks) == [1.0, 10.0, 100.0, 1000.0]


def test_d10_logbase_function_is_the_exponential():
    log = LogBase(10)
    assert np.isclose(log.function(5), 1e5)
    assert np.isclose(log.inverse_function(1e5), 5.0)


def test_d12_ticks_straddle_the_axis_line():
    nl = NumberLine(x_range=[0, 3, 1], tick_size=0.1)
    tick = nl.ticks[1]
    midpoint = (tick.points[:, 1].min() + tick.points[:, 1].max()) / 2
    assert np.isclose(midpoint, nl.number_to_point(1)[1])
    assert not [n for n in dir(nl) if "tick_direction" in n or "tick_side" in n]


def test_d13_origin_shift_clamps_to_the_range_minimum():
    assert Axes._origin_shift([5, 10, 1]) == 5


@pytest.mark.parametrize(
    "operation",
    [
        lambda nl: nl.scale(2),
        lambda nl: nl.shift(np.array([0.0, 2.0, 0.0])),
        lambda nl: nl.stretch(3, 0),
        lambda nl: nl.rotate(np.pi / 3),
        lambda nl: nl.flip(),
        lambda nl: nl.apply_function(lambda p: np.array([p[0], p[0] ** 2 / 10, p[2]])),
    ],
)
def test_d14_geometric_ops_no_longer_break_the_mapping(operation):
    """Defect 14 is gone: the mapping derives from the live geometry."""
    nl = NumberLine(x_range=[0, 10, 1], length=10)
    operation(nl)
    assert np.isclose(float(nl.point_to_number(nl.number_to_point(4))), 4.0)  # type: ignore[arg-type]


def test_d15a_plot_joins_across_a_pole():
    ax = Axes(x_range=[-3, 3, 1], y_range=[-5, 5, 1], x_length=6, y_length=6)
    curve = ax.plot(lambda x: 1 / x, x_range=[-3, 3], use_smoothing=False)
    gaps = np.linalg.norm(np.diff(curve.points[:, :2], axis=0), axis=1)
    assert gaps.max() > 100.0


def test_d15b_tick_step_is_also_the_sampling_step():
    ax = Axes(x_range=[0, 10, 5], y_range=[-2, 2, 1], x_length=8, y_length=4)
    coarse = ax.plot(np.sin, use_smoothing=False)
    fine = ax.plot(np.sin, x_range=[0, 10, 0.05], use_smoothing=False)
    assert len(coarse.points) * 5 < len(fine.points)


def test_d15c_point_to_number_is_not_the_inverse_under_a_log_scale():
    nl = NumberLine(x_range=[0, 3, 1], length=6, scaling=LogBase(10))
    round_trip = float(nl.point_to_number(nl.number_to_point(10.0)))  # type: ignore[arg-type]
    assert not np.isclose(round_trip, 10.0)
    ax = Axes(
        x_range=[0, 3, 1],
        y_range=[0, 10, 1],
        x_length=6,
        y_length=6,
        x_axis_config={"scaling": LogBase(10)},
    )
    assert not np.isclose(ax.p2c(ax.c2p(10.0, 5.0))[0], 10.0)


def test_d15c_linear_scale_round_trips_exactly():
    """The control: the asymmetry only shows once a scale is non-trivial."""
    nl = NumberLine(x_range=[0, 10, 1], length=6)
    for value in (0.0, 3.0, 7.0, 10.0):
        back = float(nl.point_to_number(nl.number_to_point(value)))  # type: ignore[arg-type]
        assert np.isclose(back, value)


def test_d15d_zero_tick_step_fails_with_an_allocation_error():
    with pytest.raises(ValueError, match="Maximum allowed size exceeded"):
        NumberLine(x_range=[0, 10, 0]).get_tick_range()
