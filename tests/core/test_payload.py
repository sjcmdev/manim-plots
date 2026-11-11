"""The Source payload and its validation (F-114, F-1006).

Rows P-1 to P-29 of `docs/acceptance/06-core-contracts.md`: one test per row of the
invalid-input table of `docs/scope.md`, plus the read-only arrays of ADR 0003 §1 and the
segment helper `Map` uses after masking. Every expected value is written out by hand.
"""

from __future__ import annotations

import dataclasses
import itertools

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from manim_plots.core.payload import Payload, split_segments

T, F = True, False


def xy(n: int) -> np.ndarray:
    """``n`` finite samples on a line, shape ``(n, 2)``."""
    return np.column_stack([np.arange(n, dtype=float), np.arange(n, dtype=float) ** 2])


def seg(*pairs: tuple[int, int]) -> np.ndarray:
    return np.array(pairs, dtype=np.intp).reshape(-1, 2)


def mask(*values: bool) -> np.ndarray:
    return np.array(values, dtype=bool)


def grid_coords() -> np.ndarray:
    """A 2 x 3 grid, row-major: sample ``r * 3 + c`` sits at ``(c, r)``."""
    return np.array([[c, r] for r in range(2) for c in range(3)], dtype=float)


def message_names(excinfo: pytest.ExceptionInfo[BaseException], *words: str) -> None:
    text = str(excinfo.value)
    for word in words:
        assert word in text, f"{word!r} not in {text!r}"


# --- P-1, P-2: kind ----------------------------------------------------------------


def test_p1_kind_of_wrong_type_raises_type_error():
    with pytest.raises(TypeError, match="kind"):
        Payload(kind=1, coords=xy(3), segments=seg((0, 3)))  # type: ignore[arg-type]


def test_p2_unknown_kind_raises_value_error():
    with pytest.raises(ValueError, match="kind"):
        Payload(kind="line", coords=xy(3), segments=seg((0, 3)))  # type: ignore[arg-type]


# --- P-3 to P-5: coords ------------------------------------------------------------


@pytest.mark.parametrize(
    "coords",
    [
        [[0.0, 1.0], [1.0, 2.0]],
        np.array([[0, 1], [1, 2]]),
        np.array([[True, False], [False, True]]),
    ],
    ids=["list", "integer array", "boolean array"],
)
def test_p3_coords_not_a_float_array_raises_type_error(coords):
    with pytest.raises(TypeError, match="coords"):
        Payload("path", coords, seg((0, 2)))


@pytest.mark.parametrize(
    "coords",
    [np.zeros(3), np.zeros((2, 2, 2))],
    ids=["one-dimensional", "three-dimensional"],
)
def test_p4_coords_not_two_dimensional_raises_value_error(coords):
    with pytest.raises(ValueError, match="coords"):
        Payload("points", coords, seg((0, len(coords))))


def test_p5_another_float_width_is_stored_as_float64():
    coords = xy(4).astype(np.float32)
    payload = Payload("path", coords, seg((0, 4)))  # type: ignore[arg-type]
    assert payload.coords.dtype == np.float64
    np.testing.assert_array_equal(payload.coords, coords)


# --- P-6 to P-10: segments ---------------------------------------------------------


@pytest.mark.parametrize(
    "segments",
    [[[0, 3]], np.array([[0.0, 3.0]]), np.array([[False, True]])],
    ids=["list", "float array", "boolean array"],
)
def test_p6_segments_not_an_integer_array_raises_type_error(segments):
    with pytest.raises(TypeError, match="segments"):
        Payload("path", xy(3), segments)


@pytest.mark.parametrize(
    "segments",
    [np.array([0, 3], dtype=np.intp), np.array([[0, 1, 3]], dtype=np.intp)],
    ids=["one-dimensional", "three columns"],
)
def test_p7_segments_not_of_shape_s_by_2_raises_value_error(segments):
    with pytest.raises(ValueError, match="segments"):
        Payload("path", xy(3), segments)


@pytest.mark.parametrize(
    "bad, values",
    [((-1, 2), "-1"), ((5, 10), "10"), ((7, 7), "7"), ((8, 6), "8")],
    ids=["negative start", "stop past n", "empty", "reversed"],
)
def test_p8_out_of_bounds_or_empty_pair_names_its_index_and_values(bad, values):
    coords = xy(9)
    valid = np.ones(9, dtype=bool)
    with pytest.raises(ValueError, match="segments") as excinfo:
        Payload("path", coords, seg((0, 1), (2, 3), bad), valid=valid)
    message_names(excinfo, "2", values)


def test_p9_unsorted_pairs_raise_naming_the_second():
    with pytest.raises(ValueError, match="segments") as excinfo:
        Payload("path", xy(6), seg((3, 6), (0, 3)))
    message_names(excinfo, "1")


def test_p9_overlapping_pairs_raise():
    with pytest.raises(ValueError, match="segments"):
        Payload("path", xy(6), seg((0, 4), (3, 6)))


def test_p9_touching_pairs_are_legal_a_split_with_no_invalid_sample():
    payload = Payload("path", xy(6), seg((0, 3), (3, 6)))
    np.testing.assert_array_equal(payload.segments, [[0, 3], [3, 6]])


@pytest.mark.parametrize("kind", ["points", "region"])
@pytest.mark.parametrize(
    "segments",
    [seg((0, 5)), seg((0, 3), (3, 6)), seg((1, 6)), np.empty((0, 2), dtype=np.intp)],
    ids=["short", "two", "offset", "none"],
)
def test_p10_points_and_regions_carry_exactly_one_full_segment(kind, segments):
    topology = (2, 3) if kind == "region" else None
    with pytest.raises(ValueError, match="segments"):
        Payload(kind, grid_coords(), segments, topology=topology)


@pytest.mark.parametrize("kind", ["points", "region"])
def test_p10_an_empty_point_set_or_region_carries_no_segment(kind):
    topology = np.empty((0, 4), dtype=np.intp) if kind == "region" else None
    payload = Payload(
        kind, np.empty((0, 2)), np.empty((0, 2), dtype=np.intp), topology=topology
    )
    assert payload.segments.shape == (0, 2)
    with pytest.raises(ValueError, match="segments"):
        Payload(kind, np.empty((0, 2)), seg((0, 0)), topology=topology)


# --- P-11 to P-15: valid and finiteness --------------------------------------------


@pytest.mark.parametrize(
    "valid",
    [[True, True, True], np.array([1, 1, 1])],
    ids=["list", "integer array"],
)
def test_p11_valid_not_a_boolean_array_raises_type_error(valid):
    with pytest.raises(TypeError, match="valid"):
        Payload("points", xy(3), seg((0, 3)), valid=valid)


@pytest.mark.parametrize(
    "valid",
    [np.ones(2, dtype=bool), np.ones((3, 1), dtype=bool)],
    ids=["too short", "two-dimensional"],
)
def test_p12_valid_of_the_wrong_shape_raises_value_error(valid):
    with pytest.raises(ValueError, match="valid"):
        Payload("points", xy(3), seg((0, 3)), valid=valid)


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_p13_a_non_finite_sample_without_a_mask_names_its_index(bad):
    coords = xy(6)
    coords[3, 1] = bad
    with pytest.raises(ValueError) as excinfo:
        Payload("points", coords, seg((0, 6)))
    message_names(excinfo, "3")


def test_p14_a_non_finite_sample_marked_valid_names_its_index():
    coords = xy(6)
    coords[4, 0] = np.nan
    valid = mask(T, T, F, T, T, T)
    with pytest.raises(ValueError, match="valid") as excinfo:
        Payload("points", coords, seg((0, 6)), valid=valid)
    message_names(excinfo, "4")


def test_p14_a_non_finite_sample_marked_invalid_is_legal():
    coords = xy(5)
    coords[2] = np.nan
    payload = Payload("points", coords, seg((0, 5)), valid=mask(T, T, F, T, T))
    assert np.isnan(payload.coords[2]).all()


def test_p15_a_covered_sample_marked_invalid_names_its_index():
    with pytest.raises(ValueError) as excinfo:
        Payload("path", xy(5), seg((0, 5)), valid=mask(T, T, F, T, T))
    message_names(excinfo, "2")


def test_p15_an_uncovered_sample_marked_valid_names_its_index():
    with pytest.raises(ValueError) as excinfo:
        Payload("path", xy(5), seg((0, 2), (3, 5)), valid=mask(T, T, T, T, T))
    message_names(excinfo, "2")


def test_p15_without_a_mask_every_sample_must_be_covered():
    with pytest.raises(ValueError) as excinfo:
        Payload("path", xy(5), seg((0, 2), (3, 5)))
    message_names(excinfo, "2")


def test_p15_an_invalid_sample_left_uncovered_is_how_a_path_splits():
    coords = xy(5)
    coords[2] = np.nan
    payload = Payload("path", coords, seg((0, 2), (3, 5)), valid=mask(T, T, F, T, T))
    np.testing.assert_array_equal(payload.segments, [[0, 2], [3, 5]])


def test_p15_points_are_excluded_by_the_mask_alone():
    payload = Payload("points", xy(4), seg((0, 4)), valid=mask(T, F, T, T))
    np.testing.assert_array_equal(payload.segments, [[0, 4]])


# --- P-16 to P-22: topology --------------------------------------------------------


@pytest.mark.parametrize("kind", ["path", "points"])
def test_p16_a_path_or_point_set_with_a_topology_raises(kind):
    with pytest.raises(ValueError, match="topology"):
        Payload(kind, grid_coords(), seg((0, 6)), topology=(2, 3))


def test_p17_a_region_without_a_topology_raises():
    with pytest.raises(ValueError, match="topology"):
        Payload("region", grid_coords(), seg((0, 6)))


@pytest.mark.parametrize(
    "topology",
    [
        [2, 3],
        (2.0, 3.0),
        (True, 6),
        (1, 2, 3),
        np.array([[0, 1, 4, 3]], dtype=float),
    ],
    ids=["list", "float tuple", "bool in tuple", "three-tuple", "float cells"],
)
def test_p18_a_topology_of_the_wrong_type_raises_type_error(topology):
    with pytest.raises(TypeError, match="topology"):
        Payload("region", grid_coords(), seg((0, 6)), topology=topology)


@pytest.mark.parametrize(
    "topology", [(2, 2), (3, 3), (0, 6), (6, 0), (-2, -3)], ids=str
)
def test_p19_a_grid_whose_product_is_not_n_raises(topology):
    with pytest.raises(ValueError, match="topology"):
        Payload("region", grid_coords(), seg((0, 6)), topology=topology)


def test_p19_a_matching_grid_is_legal_in_either_tuple_order_that_multiplies():
    assert Payload("region", grid_coords(), seg((0, 6)), topology=(2, 3)).topology == (
        2,
        3,
    )
    assert Payload("region", grid_coords(), seg((0, 6)), topology=(1, 6)).topology


@pytest.mark.parametrize(
    "topology",
    [np.array([[0, 1]], dtype=np.intp), np.array([0, 1, 4, 3], dtype=np.intp)],
    ids=["two corners", "one-dimensional"],
)
def test_p20_a_cell_array_not_m_by_at_least_3_raises(topology):
    with pytest.raises(ValueError, match="topology"):
        Payload("region", grid_coords(), seg((0, 6)), topology=topology)


@pytest.mark.parametrize(
    "bad_cell", [[1, 2, 6, 4], [1, 2, -1, 4], [1, 2, 2, 4]], ids=["n", "-1", "repeat"]
)
def test_p21_an_out_of_range_or_repeated_corner_names_the_cell(bad_cell):
    cells = np.array([[0, 1, 4, 3], [0, 1, 4, 3], bad_cell], dtype=np.intp)
    with pytest.raises(ValueError, match="topology") as excinfo:
        Payload("region", grid_coords(), seg((0, 6)), topology=cells)
    message_names(excinfo, "2")


def test_p22_inconsistent_winding_names_the_first_cell_that_turns_the_other_way():
    cells = np.array([[0, 1, 4, 3], [1, 2, 5, 4], [4, 5, 2, 1]], dtype=np.intp)
    with pytest.raises(ValueError, match="winding") as excinfo:
        Payload("region", grid_coords(), seg((0, 6)), topology=cells)
    message_names(excinfo, "2")


def test_p22_consistent_winding_either_way_round_is_legal():
    counter = np.array([[0, 1, 4, 3], [1, 2, 5, 4]], dtype=np.intp)
    clockwise = counter[:, ::-1].copy()
    for cells in (counter, clockwise):
        payload = Payload("region", grid_coords(), seg((0, 6)), topology=cells)
        np.testing.assert_array_equal(payload.topology, cells)


def test_p22_a_cell_with_an_invalid_corner_is_skipped_by_the_winding_check():
    coords = grid_coords()
    coords[5] = np.nan
    cells = np.array([[0, 1, 4, 3], [4, 5, 2, 1]], dtype=np.intp)
    valid = mask(T, T, T, T, T, F)
    Payload("region", coords, seg((0, 6)), topology=cells, valid=valid)


def test_p22_a_cell_of_zero_area_is_skipped_by_the_winding_check():
    coords = np.array([[0, 0], [1, 0], [1, 1], [0, 1], [2, 0], [3, 0]], dtype=float)
    # Cell 1 is three collinear corners; cell 2 turns the same way as cell 0.
    cells = np.array([[0, 1, 2], [1, 4, 5], [0, 2, 3]], dtype=np.intp)
    Payload("region", coords, seg((0, 6)), topology=cells)


def test_p22_a_region_needs_two_dimensions():
    with pytest.raises(ValueError):
        Payload("region", np.zeros((4, 1)), seg((0, 4)), topology=(2, 2))


# --- P-23, P-24: immutability ------------------------------------------------------


def region_with_everything() -> Payload:
    cells = np.array([[0, 1, 4, 3], [1, 2, 5, 4]], dtype=np.intp)
    return Payload(
        "region", grid_coords(), seg((0, 6)), topology=cells, valid=np.ones(6, bool)
    )


@pytest.mark.parametrize("field", ["coords", "segments", "topology", "valid"])
def test_p23_stored_arrays_are_read_only(field):
    array = getattr(region_with_everything(), field)
    assert not array.flags.writeable
    with pytest.raises(ValueError):
        array[0] = 0


def test_p24_a_payload_is_frozen():
    payload = region_with_everything()
    with pytest.raises(dataclasses.FrozenInstanceError):
        payload.kind = "points"  # type: ignore[misc]


# --- P-25 to P-29: constructors and the segment helper -----------------------------


def test_p25_path_builds_the_runs_of_valid_samples():
    coords = xy(7)
    coords[2] = np.nan
    valid = mask(T, T, F, T, T, F, T)
    payload = Payload.path(coords, valid)
    assert payload.kind == "path"
    np.testing.assert_array_equal(payload.segments, [[0, 2], [3, 5], [6, 7]])
    np.testing.assert_array_equal(payload.valid, valid)


def test_p25_path_without_a_mask_is_one_segment():
    payload = Payload.path(xy(4))
    np.testing.assert_array_equal(payload.segments, [[0, 4]])
    assert payload.valid is None


def test_p25_path_refuses_a_non_finite_sample_without_a_mask():
    coords = xy(4)
    coords[1, 0] = np.inf
    with pytest.raises(ValueError) as excinfo:
        Payload.path(coords)
    message_names(excinfo, "1")


def test_p26_points_is_one_segment_or_none():
    np.testing.assert_array_equal(Payload.points(xy(3)).segments, [[0, 3]])
    assert Payload.points(np.empty((0, 2))).segments.shape == (0, 2)
    assert Payload.points(xy(3)).kind == "points"


@pytest.mark.parametrize("kind", ["path", "points", "region"])
def test_p27_empty_payloads(kind):
    payload = Payload.empty(kind, 3)
    assert payload.kind == kind
    assert payload.coords.shape == (0, 3)
    assert payload.segments.shape == (0, 2)
    assert payload.valid is None
    if kind == "region":
        assert isinstance(payload.topology, np.ndarray)
        assert payload.topology.shape == (0, 4)
    else:
        assert payload.topology is None


def test_p27_empty_refuses_a_dimension_below_one():
    with pytest.raises(ValueError):
        Payload.empty("path", 0)


def test_p28_split_segments_cuts_at_invalid_samples():
    out = split_segments(seg((0, 5)), mask(T, T, F, T, T))
    np.testing.assert_array_equal(out, [[0, 2], [3, 5]])
    assert out.dtype == np.intp
    assert out.shape == (2, 2)


def test_p28_split_segments_keeps_touching_segments_apart():
    out = split_segments(seg((0, 3), (3, 6)), np.ones(6, dtype=bool))
    np.testing.assert_array_equal(out, [[0, 3], [3, 6]])


def test_p28_split_segments_drops_a_segment_with_no_valid_sample():
    out = split_segments(seg((0, 2), (2, 4), (5, 6)), mask(T, T, F, F, T, T))
    np.testing.assert_array_equal(out, [[0, 2], [5, 6]])


def test_p28_split_segments_of_nothing_is_nothing():
    out = split_segments(np.empty((0, 2), dtype=np.intp), np.ones(3, dtype=bool))
    assert out.shape == (0, 2)


def test_p28_split_segments_refuses_a_mask_of_the_wrong_shape():
    with pytest.raises(ValueError):
        split_segments(seg((0, 5)), np.ones(4, dtype=bool))


@st.composite
def segmented_masks(draw):
    n = draw(st.integers(0, 40))
    valid = np.array(draw(st.lists(st.booleans(), min_size=n, max_size=n)), bool)
    cuts = sorted(set(draw(st.lists(st.integers(0, n), max_size=8))) | {0, n})
    pairs = [(a, b) for a, b in itertools.pairwise(cuts) if b > a]
    keep = draw(st.lists(st.booleans(), min_size=len(pairs), max_size=len(pairs)))
    chosen = [p for p, k in zip(pairs, keep, strict=True) if k]
    return seg(*chosen), valid


@given(segmented_masks())
def test_p28_split_segments_covers_exactly_the_covered_valid_samples(case):
    segments, valid = case
    out = split_segments(segments, valid)
    covered = np.zeros(len(valid), dtype=bool)
    for a, b in segments:
        covered[a:b] = True
    produced = np.zeros(len(valid), dtype=bool)
    for a, b in out:
        assert b > a
        assert not produced[a:b].any()
        produced[a:b] = True
        # Each run lies inside one input segment and is maximal there.
        (parent,) = [(s, e) for s, e in segments if s <= a and b <= e]
        assert a == parent[0] or not valid[a - 1]
        assert b == parent[1] or not valid[b]
    np.testing.assert_array_equal(produced, covered & valid)
    assert (np.diff(out[:, 0]) > 0).all()


def test_p29_empty_and_all_invalid_paths_are_legal():
    empty = Payload("path", np.empty((0, 2)), np.empty((0, 2), dtype=np.intp))
    assert empty.coords.shape == (0, 2)
    all_invalid = Payload(
        "path", xy(3), np.empty((0, 2), dtype=np.intp), valid=mask(F, F, F)
    )
    assert all_invalid.segments.shape == (0, 2)
