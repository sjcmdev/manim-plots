"""Sources: analytic, parametric and array (F-104, F-108, F-113, F-703-F-707).

Rows B-1 to B-3, FS-1 to FS-10, PS-1 to PS-4 and AS-1 to AS-6 of
`docs/acceptance/07-sources-shape-params.md`. Oracles: the functions themselves
evaluated here, the chord tolerance of ADR 0003 §3 measured here on screen, and
hand-built expected arrays.
"""

from __future__ import annotations

import math
import warnings

import numpy as np
import pytest

from manim_plots.core.nodes import AffineNode, Chain, FrameMap, ScaleNode, SystemMap
from manim_plots.core.payload import Payload
from manim_plots.core.scales import LinearScale, LogScale
from manim_plots.core.sources import (
    CHORD_TOLERANCE,
    INITIAL_SAMPLES,
    PIXEL,
    ArraySource,
    Bounds,
    Box,
    FunctionSource,
    ParametricSource,
    Source,
)

LOWER = np.array([-3.0, -2.0])
UPPER = np.array([3.0, 2.0])


def system(x=(-6.0, 6.0), y=(-4.0, 4.0), *, log_x=False, frame=None):
    """A system mapping the data box ``x`` by ``y`` onto the local box, and the box."""
    x0, x1 = (math.log10(v) for v in x) if log_x else x
    y0, y1 = y
    sx, sy = (UPPER[0] - LOWER[0]) / (x1 - x0), (UPPER[1] - LOWER[1]) / (y1 - y0)
    nodes = [ScaleNode(LogScale() if log_x else LinearScale(), 0, 2)]
    nodes.append(
        AffineNode.from_parts(
            np.diag([sx, sy]), np.array([LOWER[0] - x0 * sx, LOWER[1] - y0 * sy])
        )
    )
    if frame is None:
        frame = FrameMap(LOWER, UPPER, FrameMap.lattice(LOWER, UPPER, 9))
    return SystemMap(Chain(nodes), frame), Box(LOWER, UPPER)


def chord_deviations(payload: Payload, f, map_) -> np.ndarray:
    """Screen distance from the true midpoint of each valid interval to its chord."""
    out = []
    for start, stop in payload.segments:
        x = payload.coords[start:stop, 0]
        if len(x) < 2:
            continue
        mid = (x[:-1] + x[1:]) / 2
        a = map_.to_screen(payload.coords[start : stop - 1])[:, :2]
        b = map_.to_screen(payload.coords[start + 1 : stop])[:, :2]
        m = map_.to_screen(np.c_[mid, [f(v) for v in mid]])[:, :2]
        ab, am = b - a, m - a
        length = np.linalg.norm(ab, axis=1)
        t = np.clip(np.einsum("ij,ij->i", am, ab) / np.maximum(length**2, 1e-300), 0, 1)
        out.append(np.linalg.norm(am - t[:, None] * ab, axis=1))
    return np.concatenate(out) if out else np.zeros(0)


def segment_spans(payload: Payload) -> list[tuple[float, float]]:
    return [
        (payload.coords[a, 0], payload.coords[b - 1, 0]) for a, b in payload.segments
    ]


# --- B: bounds ---------------------------------------------------------------------


def test_b1_a_box_is_bounds_with_read_only_corners():
    box = Box(LOWER, UPPER)
    assert isinstance(box, Bounds)
    assert not box.lower.flags.writeable
    assert not box.upper.flags.writeable


@pytest.mark.parametrize(
    "lower, upper",
    [((0.0, 0.0), (0.0, 1.0)), ((1.0, 0.0), (0.0, 1.0)), ((np.nan, 0.0), (1.0, 1.0))],
    ids=["flat", "reversed", "nan"],
)
def test_b1_a_malformed_box_raises(lower, upper):
    with pytest.raises(ValueError):
        Box(np.array(lower), np.array(upper))


def test_b2_contains_is_inclusive_and_ignores_z():
    box = Box(LOWER, UPPER)
    p = np.array(
        [[3.0, 2.0, 7.0], [-3.0, -2.0, 0.0], [3.0001, 0.0, 0.0], [np.nan, 0.0, 0.0]]
    )
    np.testing.assert_array_equal(box.contains(p), [True, True, False, False])
    np.testing.assert_array_equal(box.contains(p[:, :2]), [True, True, False, False])


# --- FS: analytic sources ----------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs, error, word",
    [
        ({"function": 3.0}, TypeError, "function"),
        ({"use_vectorized": 1}, TypeError, "use_vectorized"),
        ({"x_range": (0.0,)}, ValueError, "x_range"),
        ({"x_range": (0.0, np.inf)}, ValueError, "x_range"),
        ({"x_range": (1.0, 1.0)}, ValueError, "x_range"),
        ({"x_range": (2.0, 1.0)}, ValueError, "x_range"),
        ({"x_range": (0.0, 1.0, 0.0)}, ValueError, "step"),
        ({"x_range": (0.0, 1.0, -0.1)}, ValueError, "step"),
        ({"dt": 0.0}, ValueError, "dt"),
        ({"discontinuities": [np.nan]}, ValueError, "discontinuities"),
    ],
    ids=str,
)
def test_fs1_argument_checks(kwargs, error, word):
    arguments = {"function": np.sin} | kwargs
    with pytest.raises(error, match=word):
        FunctionSource(**arguments)


def test_fs1_a_source_is_a_source():
    assert isinstance(FunctionSource(np.sin), Source)
    assert isinstance(ParametricSource(lambda t: (t, t)), Source)
    assert isinstance(ArraySource([0, 1], [0, 1]), Source)


def test_fs2_one_call_per_sample_with_a_numpy_scalar():
    seen = []

    def f(x):
        seen.append(x)
        return math.sin(x)

    payload = FunctionSource(f).sample(*system())
    assert len(seen) >= len(payload.coords)
    assert all(type(x) is np.float64 for x in seen)


def test_fs2_vectorized_calls_take_arrays_one_per_pass():
    seen = []

    def f(x):
        seen.append(x)
        return np.sin(x)

    payload = FunctionSource(f, use_vectorized=True).sample(*system())
    assert all(isinstance(x, np.ndarray) and x.ndim == 1 for x in seen)
    assert all(x.dtype == np.float64 for x in seen)
    assert len(seen) <= 20
    assert sum(len(x) for x in seen) >= len(payload.coords)


@pytest.mark.parametrize(
    "function, vectorized",
    [(lambda x: "y", False), (lambda x: np.zeros(3), True), (lambda x: [1.0], False)],
    ids=["string", "wrong length", "list"],
)
def test_fs2_an_unreadable_return_raises_type_error(function, vectorized):
    with pytest.raises(TypeError, match="function"):
        FunctionSource(function, use_vectorized=vectorized).sample(*system())


def test_fs2_the_functions_own_exception_propagates():
    def f(x):
        raise KeyError("mine")

    with pytest.raises(KeyError, match="mine"):
        FunctionSource(f).sample(*system())


def test_fs2_numpy_warnings_are_suppressed():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        FunctionSource(lambda x: 1 / x, x_range=(-1.0, 1.0)).sample(*system())
        FunctionSource(np.log, use_vectorized=True).sample(*system())


def test_fs3_samples_the_viewport_in_data_coordinates_ascending():
    payload = FunctionSource(np.sin).sample(*system())
    assert payload.kind == "path"
    x, y = payload.coords.T
    assert x[0] == -6.0 and x[-1] == 6.0
    assert (np.diff(x) > 0).all()
    np.testing.assert_allclose(y, np.sin(x), rtol=1e-15)


def test_fs3_a_plots_own_range_is_intersected_with_the_viewport():
    payload = FunctionSource(np.sin, x_range=(-2.0, 30.0)).sample(*system())
    assert payload.coords[0, 0] == -2.0
    assert payload.coords[-1, 0] == 6.0


def test_fs3_the_interval_comes_back_through_the_map():
    payload = FunctionSource(np.log10).sample(*system(x=(0.1, 1000.0), log_x=True))
    np.testing.assert_allclose(payload.coords[[0, -1], 0], [0.1, 1000.0], rtol=1e-12)


def test_fs3_no_overlap_gives_an_empty_path():
    payload = FunctionSource(np.sin, x_range=(10.0, 20.0)).sample(*system())
    assert payload.kind == "path"
    assert payload.coords.shape == (0, 2)
    assert payload.segments.shape == (0, 2)


def test_fs4_non_finite_values_are_invalid_samples():
    payload = FunctionSource(np.sqrt, use_vectorized=True).sample(*system())
    x = payload.coords[:, 0]
    valid = np.ones(len(x), bool) if payload.valid is None else payload.valid
    np.testing.assert_array_equal(valid, x >= 0)
    assert (payload.coords[payload.segments[0, 0], 0]) >= 0


def test_fs5_every_valid_interval_passes_the_chord_test():
    map_, bounds = system()
    payload = FunctionSource(np.sin).sample(map_, bounds)
    assert chord_deviations(payload, math.sin, map_).max() <= CHORD_TOLERANCE * 1.0001


def test_fs5_the_tolerance_is_half_a_1080p_pixel():
    assert PIXEL == 8 / 1080
    assert CHORD_TOLERANCE == 0.5 * PIXEL


def test_fs5_a_straight_line_needs_no_refinement():
    payload = FunctionSource(lambda x: 2 * x + 1).sample(*system())
    assert len(payload.coords) == INITIAL_SAMPLES == 33


def test_fs5_a_step_caps_the_spacing():
    payload = FunctionSource(lambda x: 0.5, x_range=(-1.0, 1.0, 0.01)).sample(*system())
    assert np.diff(payload.coords[:, 0]).max() <= 0.01 + 1e-12


def test_fs5_density_follows_the_screen_not_the_data():
    # The same curve drawn four times larger needs more samples.
    small = FunctionSource(np.sin).sample(*system(y=(-16.0, 16.0)))
    large = FunctionSource(np.sin).sample(*system(y=(-1.0, 1.0)))
    assert len(large.coords) > len(small.coords)


def test_fs6_a_pole_splits_the_path():
    payload = FunctionSource(lambda x: 1 / (x - 0.1)).sample(*system())
    spans = segment_spans(payload)
    assert len(spans) == 2
    assert spans[0][1] < 0.1 < spans[1][0]
    # The curve runs to the edge of the viewport on both sides of the pole.
    left, right = payload.segments
    assert payload.coords[left[1] - 1, 1] < -4.0
    assert payload.coords[right[0], 1] > 4.0


def test_fs6_tan_splits_at_every_pole():
    payload = FunctionSource(np.tan, use_vectorized=True).sample(*system())
    spans = segment_spans(payload)
    poles = [k * math.pi + math.pi / 2 for k in range(-2, 2)]
    assert len(spans) == len(poles) + 1
    for pole, (_, end), (start, _) in zip(poles, spans, spans[1:], strict=False):
        # A sample may land on the float nearest the pole, where tan is finite.
        assert end <= pole <= start


def test_fs6_a_steep_line_through_zero_does_not_split():
    payload = FunctionSource(lambda x: 100 * x).sample(*system())
    assert len(payload.segments) == 1


def test_fs7_a_discontinuity_leaves_a_gap_of_two_dt():
    def step(x):
        return x if x < 1 else x + 2

    payload = FunctionSource(step, discontinuities=[1.0], dt=1e-3).sample(*system())
    x = payload.coords[:, 0]
    assert np.isclose(x, 1 - 1e-3).any() and np.isclose(x, 1 + 1e-3).any()
    assert not ((x > 1 - 1e-3 + 1e-12) & (x < 1 + 1e-3 - 1e-12)).any()
    spans = segment_spans(payload)
    assert any(math.isclose(end, 1 - 1e-3) for _, end in spans)
    assert any(math.isclose(start, 1 + 1e-3) for start, _ in spans)


def test_fs7_a_discontinuity_outside_the_interval_is_ignored():
    payload = FunctionSource(np.sin, discontinuities=[50.0]).sample(*system())
    assert len(payload.segments) == 1


def test_fs9_at_is_exact_anywhere():
    source = FunctionSource(np.sin, x_range=(0.0, 1.0))
    np.testing.assert_allclose(source.at(2.0), [[2.0, math.sin(2.0)]])
    t = np.array([-5.0, 0.3, 40.0])
    np.testing.assert_allclose(source.at(t), np.c_[t, np.sin(t)])
    assert source.at(t).shape == (3, 2)


def test_fs10_sampling_is_pure():
    source = FunctionSource(np.sin)
    a = source.sample(*system())
    b = source.sample(*system(y=(-1.0, 1.0)))
    c = source.sample(*system())
    np.testing.assert_array_equal(a.coords, c.coords)
    np.testing.assert_array_equal(a.segments, c.segments)
    assert len(b.coords) != len(a.coords)


# --- PS: parametric sources --------------------------------------------------------


def circle(t):
    return (np.cos(t), np.sin(t))


def test_ps1_argument_checks():
    with pytest.raises(ValueError, match="t_range"):
        ParametricSource(circle, t_range=(1.0, 1.0))
    with pytest.raises(TypeError):
        ParametricSource(5)


@pytest.mark.parametrize(
    "function",
    [
        circle,
        lambda t: np.array([np.cos(t), np.sin(t), np.zeros_like(t)]),
    ],
    ids=["tuple", "rows with z"],
)
def test_ps2_vectorized_orientations(function):
    payload = ParametricSource(
        function, t_range=(0.0, math.tau), use_vectorized=True
    ).sample(*system())
    np.testing.assert_allclose(np.hypot(*payload.coords.T), 1.0, rtol=1e-12)


def test_ps2_a_wrong_return_raises_type_error():
    with pytest.raises(TypeError):
        ParametricSource(lambda t: (t,), t_range=(0.0, 1.0)).sample(*system())


def test_ps3_samples_the_whole_parameter_range_in_order():
    payload = ParametricSource(lambda t: (5 * np.cos(t), 5 * np.sin(t)), (0.0, math.pi))
    coords = payload.sample(*system()).coords
    np.testing.assert_allclose(coords[0], [5.0, 0.0], atol=1e-12)
    np.testing.assert_allclose(coords[-1], [-5.0, 0.0], atol=1e-12)
    angles = np.unwrap(np.arctan2(coords[:, 1], coords[:, 0]))
    assert (np.diff(angles) > 0).all()


def test_ps3_refines_on_screen():
    map_, bounds = system()
    big = ParametricSource(lambda t: (5 * np.cos(t), 3 * np.sin(t)), (0.0, math.tau))
    assert len(big.sample(map_, bounds).coords) > INITIAL_SAMPLES


def test_ps4_at_is_exact():
    source = ParametricSource(circle, (0.0, 1.0))
    np.testing.assert_allclose(
        source.at([0.0, 4.0]), [[1.0, 0.0], [math.cos(4), math.sin(4)]]
    )


# --- AS: array sources -------------------------------------------------------------


def test_as1_two_sequences_or_pairs():
    a = ArraySource([0, 1, 2], [3, 4, 5])
    b = ArraySource([(0, 3), (1, 4), (2, 5)])
    np.testing.assert_array_equal(a.data, b.data)
    assert a.data.dtype == np.float64
    assert a.data.shape == (3, 2)


def test_as1_lengths_that_differ_are_named():
    with pytest.raises(ValueError) as excinfo:
        ArraySource([0, 1, 2], [3, 4, 5, 6])
    assert "3" in str(excinfo.value) and "4" in str(excinfo.value)


@pytest.mark.parametrize(
    "args",
    [([[0, 1, 2]],), ([[0, 1], [2, 3]], [0, 1]), ([0, 1], [[0, 1]])],
    ids=["three columns", "2-d xs", "2-d ys"],
)
def test_as1_wrong_shapes_raise_value_error(args):
    with pytest.raises(ValueError):
        ArraySource(*args)


def test_as1_non_numeric_data_raises_type_error():
    with pytest.raises(TypeError):
        ArraySource(["a", "b"], [1, 2])


def test_as2_data_is_copied_read_only():
    xs = np.array([0.0, 1.0])
    source = ArraySource(xs, [1.0, 2.0])
    xs[0] = 50.0
    assert source.data[0, 0] == 0.0
    assert not source.data.flags.writeable


def test_as3_non_finite_values_split_a_path():
    payload = ArraySource([-2, -1, 0, 1, 2], [0, 1, np.nan, 1, 0]).sample(*system())
    np.testing.assert_array_equal(payload.valid, [True, True, False, True, True])
    np.testing.assert_array_equal(payload.segments, [[0, 2], [3, 5]])


def test_as4_samples_of_edges_meeting_the_viewport_are_kept():
    payload = ArraySource([-10, -8, 0, 8, 10], [0, 0, 0, 0, 0]).sample(*system())
    np.testing.assert_array_equal(payload.coords[:, 0], [-8, 0, 8])
    np.testing.assert_array_equal(payload.segments, [[0, 3]])


def test_as4_a_segment_from_outside_to_outside_survives():
    payload = ArraySource([-10, 10], [0, 0]).sample(*system())
    np.testing.assert_array_equal(payload.coords[:, 0], [-10, 10])


def test_as4_a_gap_where_samples_were_dropped_splits_the_path():
    payload = ArraySource([0, 10, 11, 12, 0], [0, 1, 2, 3, 4]).sample(*system())
    np.testing.assert_array_equal(payload.coords[:, 0], [0, 10, 12, 0])
    np.testing.assert_array_equal(payload.segments, [[0, 2], [2, 4]])


def test_as4_the_data_is_never_changed():
    source = ArraySource([-10, -8, 0, 8, 10], [0, 1, 2, 3, 4])
    before = source.data.copy()
    source.sample(*system(x=(-1.0, 1.0)))
    np.testing.assert_array_equal(source.data, before)


def test_as4_a_point_set_keeps_the_samples_inside():
    payload = ArraySource([-10, -2, 3, 9], [0, 0, 0, 0], kind="points").sample(
        *system()
    )
    assert payload.kind == "points"
    np.testing.assert_array_equal(payload.coords[:, 0], [-2, 3])


def test_as5_an_array_path_does_not_split_at_a_sign_change():
    payload = ArraySource([-1, 1], [-100, 100]).sample(*system())
    assert len(payload.segments) == 1


def test_as6_at_interpolates_linearly_in_x():
    source = ArraySource([0, 1, 3], [0, 10, 30])
    np.testing.assert_allclose(source.at([0.5, 2.0]), [[0.5, 5.0], [2.0, 20.0]])
    falling = ArraySource([3, 1, 0], [30, 10, 0])
    np.testing.assert_allclose(falling.at(2.0), [[2.0, 20.0]])


def test_as6_non_monotonic_x_raises_naming_the_index():
    source = ArraySource([0, 1, 3, 2], [0, 1, 2, 3])
    with pytest.raises(ValueError) as excinfo:
        source.at(0.5)
    assert "3" in str(excinfo.value)


def test_as6_outside_the_data_raises():
    with pytest.raises(ValueError):
        ArraySource([0, 1], [0, 1]).at(1.5)


def test_as6_near_an_invalid_sample_raises():
    with pytest.raises(ValueError):
        ArraySource([0, 1, 2], [0, np.nan, 2]).at(0.5)
