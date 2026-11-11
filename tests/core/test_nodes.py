"""Map nodes, the compiled chain and the frame map (F-105, F-109, F-201, F-207, F-914).

Rows N-1 to N-17 of `docs/acceptance/06-core-contracts.md`. Oracles: matrices and
transforms built here by hand, the round-trip invariant of F-201 under Hypothesis on
random affine frames, and bilinear interpolation of a warped grid computed here.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from functools import cache
from typing import Any

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from manim_plots.core.nodes import (
    AffineNode,
    Chain,
    CompiledMap,
    FrameMap,
    FunctionNode,
    Node,
    ScaleNode,
    SystemMap,
)
from manim_plots.core.payload import Payload
from manim_plots.core.scales import LinearScale, LogScale

LOWER = np.array([-3.0, -2.0])
UPPER = np.array([3.0, 2.0])
DIAGONAL = math.hypot(6.0, 4.0)  # the lattice rectangle's diagonal


def homogeneous(linear: Any, offset: Any) -> Any:
    linear = np.asarray(linear, dtype=float)
    d = len(linear)
    m = np.eye(d + 1)
    m[:d, :d] = linear
    m[:d, d] = offset
    return m


def shift(dx: float, dy: float = 0.0) -> AffineNode:
    return AffineNode(homogeneous(np.eye(2), [dx, dy]))


def lattice(n: int = 9) -> np.ndarray:
    return FrameMap.lattice(LOWER, UPPER, n)


def frame_of(transform: Callable[[Any], Any], n: int = 9) -> FrameMap:
    return FrameMap(LOWER, UPPER, transform(lattice(n)))


def linear_frame(matrix: Any, offset: Any = (0.0, 0.0, 0.0), n: int = 9) -> FrameMap:
    m = np.asarray(matrix, dtype=float)
    return frame_of(lambda p: p @ m.T + np.asarray(offset), n)


def size_of(nodes: np.ndarray) -> float:
    return float(np.linalg.norm(np.ptp(nodes, axis=0)))


def rotation_x(phi: float) -> Any:
    c, s = math.cos(phi), math.sin(phi)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rotation_z(theta: float) -> Any:
    c, s = math.cos(theta), math.sin(theta)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def warp(p: Any) -> Any:
    """A smooth, injective, non-affine map of the plane."""
    x, y = p[:, 0], p[:, 1]
    return np.c_[x + 0.3 * np.sin(y), y + 0.2 * np.cos(x), np.zeros(len(p))]


def xy_path(x: Any) -> Payload:
    x = np.asarray(x, dtype=float)
    return Payload.path(np.c_[x, np.zeros_like(x)])


# --- N-1 to N-5: nodes -------------------------------------------------------------


def test_n1_affine_node_applies_its_matrix_to_row_vectors():
    m = homogeneous([[2.0, 1.0], [0.0, 3.0]], [5.0, -1.0])
    node = AffineNode(m)
    x = np.array([[1.0, 1.0], [0.0, -2.0]])
    np.testing.assert_allclose(node.apply(x), [[8.0, 2.0], [3.0, -7.0]])
    assert node.is_affine is True
    assert node.dim == 2
    np.testing.assert_array_equal(node.matrix, m)
    assert not node.matrix.flags.writeable


def test_n1_from_parts_is_the_same_node():
    a = AffineNode.from_parts(np.array([[2.0, 1.0], [0.0, 3.0]]), np.array([5.0, -1.0]))
    b = AffineNode(homogeneous([[2.0, 1.0], [0.0, 3.0]], [5.0, -1.0]))
    np.testing.assert_array_equal(a.matrix, b.matrix)


@pytest.mark.parametrize(
    "matrix",
    [
        np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 1.0, 1.0]]),
        np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 2.0]]),
        np.array([[np.nan, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]),
        np.eye(3)[:2],
    ],
    ids=["last row", "scaled last row", "nan", "not square"],
)
def test_n1_a_malformed_matrix_raises(matrix):
    with pytest.raises(ValueError):
        AffineNode(matrix)


@pytest.mark.parametrize(
    "linear",
    [[[1.0, 0.0], [0.0, 0.0]], [[0.0, 0.0], [0.0, 0.0]], [[1.0, 0.0], [0.0, 1e-13]]],
)
def test_n2_a_singular_affine_node_refuses_to_invert(linear):
    node = AffineNode.from_parts(np.array(linear), np.zeros(2))
    with pytest.raises(ValueError, match="singular"):
        node.inverse(np.array([[1.0, 1.0]]))


def test_n2_a_small_but_regular_node_inverts():
    node = AffineNode.from_parts(
        np.array([[1.0, 0.0], [0.0, 1e-6]]), np.array([1.0, 2.0])
    )
    x = np.array([[0.5, -3.0], [2.0, 7.0]])
    np.testing.assert_allclose(node.inverse(node.apply(x)), x, rtol=0, atol=1e-9)


def test_n3_scale_node_transforms_one_column():
    node = ScaleNode(LogScale(), axis=0, dim=2)
    x = np.array([[100.0, 5.0], [0.1, -2.0]])
    np.testing.assert_allclose(node.apply(x), [[2.0, 5.0], [-1.0, -2.0]])
    np.testing.assert_allclose(node.inverse(node.apply(x)), x)
    assert node.is_affine is False
    assert node.matrix is None


def test_n3_a_linear_scale_node_is_the_affine_identity():
    node = ScaleNode(LinearScale(), axis=1, dim=2)
    assert node.is_affine is True
    np.testing.assert_array_equal(node.matrix, np.eye(3))


@pytest.mark.parametrize("axis", [-1, 2])
def test_n3_an_axis_outside_the_dimension_raises(axis):
    with pytest.raises(ValueError, match="axis"):
        ScaleNode(LinearScale(), axis=axis, dim=2)


def test_n4_function_node_is_a_barrier_and_may_lack_an_inverse():
    node = FunctionNode(lambda x: x**3, dim=2)
    assert node.is_affine is False
    assert node.matrix is None
    np.testing.assert_allclose(node.apply(np.array([[2.0, -1.0]])), [[8.0, -1.0]])
    with pytest.raises(ValueError):
        node.inverse(np.array([[8.0, -1.0]]))
    paired = FunctionNode(lambda x: x**3, np.cbrt, dim=2)
    np.testing.assert_allclose(paired.inverse(np.array([[8.0, -1.0]])), [[2.0, -1.0]])


def test_n5_valid_rejects_non_finite_input_out_of_domain_input_and_non_finite_output():
    x = np.array([[1.0, 1.0], [np.nan, 1.0], [1.0, np.inf], [-1.0, 1.0], [0.0, 1.0]])
    np.testing.assert_array_equal(shift(1.0).valid(x), [True, False, False, True, True])
    log = ScaleNode(LogScale(), axis=0, dim=2)
    np.testing.assert_array_equal(log.valid(x), [True, False, False, False, False])
    reciprocal = FunctionNode(lambda v: 1.0 / v, dim=2)
    with np.errstate(divide="ignore"):
        np.testing.assert_array_equal(
            reciprocal.valid(x), [True, False, False, True, False]
        )


# --- N-6 to N-9: the compiled chain ------------------------------------------------


def test_n6_adjacent_affine_nodes_collapse_in_order():
    a = AffineNode(homogeneous([[2.0, 0.0], [0.0, 1.0]], [1.0, 0.0]))
    b = AffineNode(homogeneous([[0.0, -1.0], [1.0, 0.0]], [0.0, 3.0]))
    c = shift(0.5, 0.5)
    d = AffineNode(homogeneous([[3.0, 0.0], [0.0, 3.0]], [0.0, 0.0]))
    chain = Chain([a, b, ScaleNode(LogScale(), 0, 2), c, d])
    assert len(chain.nodes) == 3
    np.testing.assert_allclose(np.asarray(chain.nodes[0].matrix), b.matrix @ a.matrix)
    assert chain.nodes[1].is_affine is False
    np.testing.assert_allclose(np.asarray(chain.nodes[2].matrix), d.matrix @ c.matrix)
    assert chain.is_affine is False


def test_n6_a_linear_scale_collapses_with_its_neighbours():
    chain = Chain([shift(1.0), ScaleNode(LinearScale(), 0, 2), shift(2.0)])
    assert len(chain.nodes) == 1
    assert chain.is_affine is True
    np.testing.assert_allclose(chain.forward(np.array([[0.0, 0.0]])), [[3.0, 0.0]])


def test_n6_an_empty_chain_is_the_identity():
    chain = Chain([])
    assert chain.is_affine is True
    x = np.array([[1.0, 2.0]])
    np.testing.assert_array_equal(chain.forward(x), x)
    np.testing.assert_array_equal(chain.inverse(x), x)


def test_n6_nodes_of_different_dimensions_raise():
    with pytest.raises(ValueError):
        Chain([shift(1.0), ScaleNode(LinearScale(), 0, 3)])


def test_n7_forward_is_the_nodes_in_turn_and_inverse_undoes_it():
    nodes: list[Node] = [
        AffineNode(homogeneous([[2.0, 0.5], [0.0, 1.0]], [3.0, 0.0])),
        ScaleNode(LogScale(), 0, 2),
        AffineNode(homogeneous([[1.0, 0.0], [0.0, 4.0]], [-1.0, 1.0])),
        FunctionNode(lambda v: v**3, np.cbrt, dim=2),
    ]
    chain = Chain(nodes)
    x = np.array([[1.0, 2.0], [10.0, -3.0], [0.25, 0.0]])
    expected = x
    for node in nodes:
        expected = node.apply(expected)
    np.testing.assert_allclose(chain.forward(x), expected, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(
        chain.inverse(chain.forward(x)), x, rtol=1e-9, atol=1e-12
    )


def test_n8_apply_payload_keeps_kind_and_returns_a_new_payload():
    payload = xy_path([1.0, 2.0, 3.0])
    before = payload.coords.copy()
    out = Chain([shift(1.0)]).apply_payload(payload)
    assert out is not payload
    assert out.kind == "path"
    assert out.valid is None
    np.testing.assert_allclose(out.coords[:, 0], [2.0, 3.0, 4.0])
    np.testing.assert_array_equal(out.segments, [[0, 3]])
    np.testing.assert_array_equal(payload.coords, before)


def test_n8_a_point_set_keeps_its_segment_and_marks_the_sample():
    payload = Payload.points(np.array([[1.0, 0.0], [-1.0, 0.0], [10.0, 0.0]]))
    out = Chain([ScaleNode(LogScale(), 0, 2)]).apply_payload(payload)
    np.testing.assert_array_equal(out.segments, [[0, 3]])
    np.testing.assert_array_equal(out.valid, [True, False, True])


def test_n8_a_region_passes_its_topology_through():
    coords = np.array([[c + 1.0, r + 1.0] for r in range(2) for c in range(3)])
    payload = Payload(
        "region", coords, np.array([[0, 6]], dtype=np.intp), topology=(2, 3)
    )
    out = Chain([ScaleNode(LogScale(), 1, 2)]).apply_payload(payload)
    assert out.kind == "region"
    assert out.topology == (2, 3)
    assert out.valid is None


def test_n9_a_later_node_invalidates_a_sample_the_earlier_one_kept():
    chain = Chain([shift(-2.0), ScaleNode(LogScale(), 0, 2)])
    out = chain.apply_payload(xy_path([1.0, 3.0, 4.0, 5.0]))
    np.testing.assert_array_equal(out.valid, [False, True, True, True])
    np.testing.assert_array_equal(out.segments, [[1, 4]])


def test_n9_a_sample_invalid_on_entry_stays_invalid():
    coords = np.c_[[1.0, np.nan, 3.0, 4.0], np.zeros(4)]
    payload = Payload.path(coords, np.array([True, False, True, True]))
    out = Chain([shift(1.0)]).apply_payload(payload)
    np.testing.assert_array_equal(out.valid, [True, False, True, True])
    np.testing.assert_array_equal(out.segments, [[0, 1], [2, 4]])


# --- N-10 to N-15: the frame map ---------------------------------------------------


def test_n10_the_lattice_is_row_major_over_the_rectangle():
    nodes = FrameMap.lattice(LOWER, UPPER, 3)
    assert nodes.shape == (9, 3)
    for j in range(3):
        for i in range(3):
            np.testing.assert_allclose(nodes[j * 3 + i], [-3 + 3 * i, -2 + 2 * j, 0])


@pytest.mark.parametrize(
    "nodes",
    [np.zeros((10, 3)), np.zeros((1, 3)), np.zeros((9, 2))],
    ids=["not square", "one node", "two columns"],
)
def test_n11_nodes_must_be_a_square_lattice_of_scene_points(nodes):
    with pytest.raises(ValueError):
        FrameMap(LOWER, UPPER, nodes)


def test_n11_the_rectangle_must_have_extent():
    with pytest.raises(ValueError):
        FrameMap(np.array([1.0, -2.0]), np.array([1.0, 2.0]), lattice(3))


def test_n11_the_frame_keeps_its_own_copy():
    nodes = lattice()
    frame = FrameMap(LOWER, UPPER, nodes)
    before = frame.forward(np.array([[1.0, 1.0, 0.0]]))
    nodes += 5.0
    np.testing.assert_array_equal(frame.forward(np.array([[1.0, 1.0, 0.0]])), before)


def test_n12_affine_and_warped_frames_are_told_apart():
    assert linear_frame(rotation_z(0.7) * 2.0, (1.0, -4.0, 0.5)).is_affine is True
    assert frame_of(warp).is_affine is False


def test_n12_a_frame_collapsed_to_a_point_is_affine_and_singular():
    frame = frame_of(lambda p: np.full_like(p, 1.0))
    assert frame.is_affine is True
    assert frame.is_singular is True


@pytest.mark.parametrize(
    "matrix, singular",
    [
        (np.diag([1.0, 0.0, 1.0]), True),
        (np.diag([1e-13, 1.0, 1.0]), True),
        (np.diag([1e-6, 1.0, 1.0]), False),
        (np.eye(3), False),
    ],
    ids=["a line", "near-singular", "small", "identity"],
)
def test_n13_singular_frames(matrix, singular):
    assert linear_frame(matrix).is_singular is singular


@pytest.mark.parametrize("transform", ["affine", "warped"])
def test_n14_forward_reproduces_every_lattice_node(transform):
    nodes = (
        lattice() @ (rotation_x(0.4) @ rotation_z(0.3)).T + [1.0, 2.0, 3.0]
        if transform == "affine"
        else warp(lattice())
    )
    frame = FrameMap(LOWER, UPPER, nodes)
    np.testing.assert_allclose(
        frame.forward(lattice()), nodes, rtol=0, atol=1e-12 * size_of(nodes)
    )


def test_n14_a_missing_z_is_zero():
    frame = frame_of(warp)
    p = np.array([[0.3, -1.1], [2.0, 1.5]])
    np.testing.assert_array_equal(frame.forward(p), frame.forward(np.c_[p, [0.0, 0.0]]))
    assert frame.forward(p).shape == (2, 3)


def test_n14_local_z_runs_along_the_unit_normal():
    assert np.allclose(
        linear_frame(np.eye(3)).forward(np.array([[1.0, 1.0, 0.5]])), [[1, 1, 0.5]]
    )
    m = rotation_x(math.pi / 2) @ np.diag([2.0, 3.0, 1.0])
    frame = linear_frame(m, (1.0, 1.0, 1.0))
    base = frame.forward(np.array([[0.5, 0.5, 0.0]]))[0]
    up = frame.forward(np.array([[0.5, 0.5, 1.0]]))[0] - base
    normal = np.cross(m[:, 0], m[:, 1])
    np.testing.assert_allclose(up, normal / np.linalg.norm(normal), atol=1e-12)


def test_n14_a_warped_frame_interpolates_bilinearly_inside_a_cell():
    n = 9
    nodes = warp(lattice(n))
    frame = FrameMap(LOWER, UPPER, nodes)
    dx, dy = (UPPER - LOWER) / (n - 1)
    for i, j in [(0, 0), (3, 5), (7, 7)]:
        corners = [j * n + i, j * n + i + 1, (j + 1) * n + i, (j + 1) * n + i + 1]
        for u, v in [(0.5, 0.5), (0.25, 0.75)]:
            weights = [(1 - u) * (1 - v), u * (1 - v), (1 - u) * v, u * v]
            expected = np.tensordot(weights, nodes[corners], axes=1)
            local = [LOWER[0] + (i + u) * dx, LOWER[1] + (j + v) * dy, 0.0]
            np.testing.assert_allclose(
                frame.forward(np.array([local]))[0], expected, atol=1e-12
            )


def test_n15_inverse_of_a_singular_frame_refuses():
    frame = linear_frame(np.diag([1.0, 0.0, 1.0]))
    with pytest.raises(ValueError, match="singular"):
        frame.inverse(np.array([[1.0, 0.0, 0.0]]))


def test_n15_inverse_returns_local_points_on_the_plane():
    frame = linear_frame(rotation_z(0.5) * 2.0, (1.0, 1.0, 0.0))
    p = np.array([[1.0, -1.0, 0.0], [2.5, 0.5, 0.0]])
    local = frame.inverse(frame.forward(p))
    assert local.shape == (2, 3)
    np.testing.assert_array_equal(local[:, 2], [0.0, 0.0])
    np.testing.assert_allclose(local, p, atol=1e-12)


def test_n15_a_point_near_the_plane_is_projected():
    frame = linear_frame(np.eye(3))
    size = size_of(lattice())
    local = frame.inverse(np.array([[1.0, 1.0, 1e-8 * size]]))
    np.testing.assert_allclose(local, [[1.0, 1.0, 0.0]], atol=1e-12)


def test_n15_a_point_far_off_the_plane_raises_naming_its_index():
    frame = linear_frame(np.eye(3))
    size = size_of(lattice())
    points = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 1e-3 * size]])
    with pytest.raises(ValueError) as excinfo:
        frame.inverse(points)
    assert "2" in str(excinfo.value)


def test_n15_a_point_with_no_preimage_raises_naming_its_index():
    folded = frame_of(lambda p: np.c_[p[:, 0] ** 2 / 3, p[:, 1], p[:, 2]])
    assert folded.is_affine is False
    points = np.array([[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0]])
    with pytest.raises(ValueError) as excinfo:
        folded.inverse(points)
    assert "1" in str(excinfo.value)


def test_n15_the_docstring_names_the_branch():
    assert "branch" in (FrameMap.inverse.__doc__ or "").lower()


# --- N-16: round trip --------------------------------------------------------------

unit = st.floats(min_value=-1.0, max_value=1.0)


@st.composite
def affine_frames(draw):
    theta = draw(st.floats(-math.pi, math.pi))
    phi = draw(st.floats(-1.2, 1.2))
    s1, s2 = draw(st.floats(0.1, 10.0)), draw(st.floats(0.1, 10.0))
    shear = draw(unit)
    t = [draw(st.floats(-10.0, 10.0)) for _ in range(3)]
    m = (
        rotation_x(phi)
        @ rotation_z(theta)
        @ np.array([[s1, shear, 0], [0, s2, 0], [0, 0, 1]])
    )
    return linear_frame(m, t)


local_points = st.tuples(st.floats(-6.0, 6.0), st.floats(-4.0, 4.0))


@given(affine_frames(), st.lists(local_points, min_size=1, max_size=8))
def test_n16_affine_round_trip(frame, points):
    assert frame.is_affine and not frame.is_singular
    p = np.c_[np.array(points), np.zeros(len(points))]
    np.testing.assert_allclose(
        frame.inverse(frame.forward(p)), p, rtol=0, atol=1e-9 * DIAGONAL
    )


@cache
def warped_33() -> FrameMap:
    return FrameMap(LOWER, UPPER, warp(FrameMap.lattice(LOWER, UPPER, 33)))


@given(
    st.lists(
        st.tuples(st.floats(-2.99, 2.99), st.floats(-1.99, 1.99)),
        min_size=1,
        max_size=8,
    )
)
def test_n16_bilinear_round_trip_inside_the_rectangle(points):
    p = np.c_[np.array(points), np.zeros(len(points))]
    frame = warped_33()
    np.testing.assert_allclose(
        frame.inverse(frame.forward(p)), p, rtol=0, atol=1e-9 * DIAGONAL
    )


# --- N-17: the system map ----------------------------------------------------------


def data_chain(*extra: Node) -> Chain:
    return Chain(
        [
            ScaleNode(LinearScale(), 0, 2),
            AffineNode(homogeneous([[0.5, 0.0], [0.0, 2.0]], [1.0, -1.0])),
            *extra,
        ]
    )


def test_n17_system_map_composes_data_own_transform_and_frame():
    frame = linear_frame(rotation_z(0.3), (1.0, 2.0, 0.0))
    own = Chain([AffineNode(homogeneous(np.eye(3) * 2.0, [0.0, 0.5, 0.0]))])
    system = SystemMap(data_chain(), frame, own)
    x = np.array([[2.0, 1.0], [-4.0, 0.25]])
    local = data_chain().forward(x)
    expected = frame.forward(own.forward(np.c_[local, np.zeros(len(x))]))
    np.testing.assert_allclose(system.to_screen(x), expected, atol=1e-12)
    np.testing.assert_allclose(system.forward(x), local)
    np.testing.assert_allclose(system.inverse(local), x)
    np.testing.assert_array_equal(system.valid(x), [True, True])


def test_n17_without_an_own_transform_the_frame_places_the_local_points():
    frame = linear_frame(np.eye(3))
    system = SystemMap(data_chain(), frame)
    x = np.array([[2.0, 1.0]])
    np.testing.assert_allclose(system.to_screen(x), [[2.0, 1.0, 0.0]])


def test_n17_is_affine_needs_every_part_affine():
    flat = linear_frame(np.eye(3))
    assert SystemMap(data_chain(), flat).is_affine is True
    assert SystemMap(data_chain(ScaleNode(LogScale(), 1, 2)), flat).is_affine is False
    assert SystemMap(data_chain(), frame_of(warp)).is_affine is False
    bent = Chain([FunctionNode(lambda v: v**3, dim=3)])
    assert SystemMap(data_chain(), flat, bent).is_affine is False


def test_n17_a_system_map_is_a_read_only_compiled_map():
    system = SystemMap(data_chain(), linear_frame(np.eye(3)))
    assert isinstance(system, CompiledMap)
    with pytest.raises(AttributeError):
        system.is_affine = False  # type: ignore[misc]


def test_n17_the_data_chain_is_two_dimensional():
    with pytest.raises(ValueError):
        SystemMap(Chain([ScaleNode(LinearScale(), 0, 3)]), linear_frame(np.eye(3)))
