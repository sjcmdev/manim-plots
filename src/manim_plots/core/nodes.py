"""Numeric transform nodes, compiled chains and lattice frame maps."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from math import isqrt
from typing import Protocol, runtime_checkable

import numpy as np
from numpy.typing import ArrayLike
from scipy.sparse import csr_matrix  # type: ignore[import-untyped]

from manim_plots.core import BoolArray, FloatArray, IntArray
from manim_plots.core.payload import Payload, split_segments
from manim_plots.core.scales import LinearScale, Scale

SINGULAR_RTOL = 1e-12
AFFINE_RTOL = 1e-9
PLANE_RTOL = 1e-6
FRAME_NODES = 33


class Node(Protocol):
    """Describe a numeric transformation of fixed-dimensional samples."""

    @property
    def dim(self) -> int:
        """Return the input and output dimension."""
        ...

    @property
    def is_affine(self) -> bool:
        """Return whether a homogeneous matrix describes the node."""
        ...

    @property
    def matrix(self) -> FloatArray | None:
        """Return the column-vector homogeneous matrix, when affine."""
        ...

    def apply(self, x: FloatArray) -> FloatArray:
        """Transform samples.

        Parameters
        ----------
        x
            Array of shape ``(n, dim)``.

        Returns
        -------
        FloatArray
            Transformed samples of the same shape.
        """
        ...

    def inverse(self, y: FloatArray) -> FloatArray:
        """Invert samples or raise when the inverse is unavailable.

        Parameters
        ----------
        y
            Array of shape ``(n, dim)``.

        Returns
        -------
        FloatArray
            Inverse images of the same shape.
        """
        ...

    def valid(self, x: FloatArray) -> BoolArray:
        """Check finite inputs, domain membership and finite outputs.

        Parameters
        ----------
        x
            Array of shape ``(n, dim)``.

        Returns
        -------
        BoolArray
            Per-sample validity.
        """
        ...


@runtime_checkable
class CompiledMap(Protocol):
    """Expose the read-only mapping operations available to a source."""

    @property
    def is_affine(self) -> bool:
        """Return whether the complete screen mapping is affine."""
        ...

    def forward(self, data: FloatArray) -> FloatArray:
        """Map data coordinates to local coordinates.

        Parameters
        ----------
        data
            Data samples.

        Returns
        -------
        FloatArray
            Local samples.
        """
        ...

    def inverse(self, local: FloatArray) -> FloatArray:
        """Map local coordinates to data coordinates.

        Parameters
        ----------
        local
            Local samples.

        Returns
        -------
        FloatArray
            Data samples.
        """
        ...

    def valid(self, data: FloatArray) -> BoolArray:
        """Check validity throughout the data chain.

        Parameters
        ----------
        data
            Data samples.

        Returns
        -------
        BoolArray
            Per-sample validity.
        """
        ...

    def to_screen(self, data: FloatArray) -> FloatArray:
        """Map data through local placement and the frame.

        Parameters
        ----------
        data
            Data samples.

        Returns
        -------
        FloatArray
            Three-dimensional scene samples.
        """
        ...


def _readonly(value: ArrayLike) -> FloatArray:
    with np.errstate(all="ignore"):
        result = np.array(value, dtype=np.float64, copy=True)
    result.flags.writeable = False
    return result


def _samples(value: FloatArray, dim: int, name: str) -> FloatArray:
    with np.errstate(all="ignore"):
        result = np.asarray(value, dtype=np.float64)
    if result.ndim != 2 or result.shape[1] != dim:
        raise ValueError(f"{name} must have shape (n, {dim})")
    return result


def _finite(value: FloatArray, name: str) -> None:
    bad = ~np.isfinite(value)
    if np.any(bad):
        index = tuple(int(i) for i in np.argwhere(bad)[0])
        raise ValueError(f"{name} at index {index} must be finite")


def _dimension(dim: int) -> None:
    if not isinstance(dim, int) or isinstance(dim, bool):
        raise TypeError("dim must be an int")
    if dim < 1:
        raise ValueError("dim must be positive")


def _singular(linear: FloatArray) -> bool:
    singular_values = np.linalg.svd(linear, compute_uv=False)
    return bool(
        singular_values[0] == 0
        or singular_values[-1] <= SINGULAR_RTOL * singular_values[0]
    )


class AffineNode:
    """Apply a homogeneous affine matrix using column-vector conventions.

    Parameters
    ----------
    matrix
        Finite square matrix of shape ``(d+1, d+1)`` with last row
        ``[0, ..., 0, 1]``.
    """

    def __init__(self, matrix: FloatArray) -> None:
        matrix = _readonly(matrix)
        if (
            matrix.ndim != 2
            or matrix.shape[0] < 2
            or matrix.shape[0] != matrix.shape[1]
        ):
            raise ValueError("matrix must have shape (d+1, d+1), d >= 1")
        _finite(matrix, "matrix")
        last = np.zeros(matrix.shape[1])
        last[-1] = 1
        if not np.array_equal(matrix[-1], last):
            raise ValueError(
                f"matrix last row at index {len(matrix) - 1} must be [0, ..., 0, 1]"
            )
        self._matrix = matrix

    @classmethod
    def from_parts(cls, linear: FloatArray, offset: FloatArray) -> AffineNode:
        """Build a homogeneous matrix from a linear part and translation.

        Parameters
        ----------
        linear
            Finite square array of shape ``(d, d)``.
        offset
            Finite translation of shape ``(d,)``.

        Returns
        -------
        AffineNode
            The combined transformation.
        """
        linear = _readonly(linear)
        offset = _readonly(offset)
        if linear.ndim != 2 or not len(linear) or linear.shape[0] != linear.shape[1]:
            raise ValueError("linear must have shape (d, d), d >= 1")
        if offset.shape != (len(linear),):
            raise ValueError(f"offset must have shape ({len(linear)},)")
        _finite(linear, "linear")
        _finite(offset, "offset")
        matrix = np.eye(len(linear) + 1)
        matrix[:-1, :-1] = linear
        matrix[:-1, -1] = offset
        return cls(matrix)

    @property
    def dim(self) -> int:
        """Return the coordinate dimension."""
        return len(self._matrix) - 1

    @property
    def is_affine(self) -> bool:
        """Return True for an affine node."""
        return True

    @property
    def matrix(self) -> FloatArray:
        """Return a read-only view of the homogeneous matrix."""
        return self._matrix.view()

    def apply(self, x: FloatArray) -> FloatArray:
        """Apply the linear part followed by translation.

        Parameters
        ----------
        x
            Samples of shape ``(n, dim)``.

        Returns
        -------
        FloatArray
            Transformed samples.
        """
        x = _samples(x, self.dim, "x")
        with np.errstate(all="ignore"):
            return x @ self._matrix[:-1, :-1].T + self._matrix[:-1, -1]

    def inverse(self, y: FloatArray) -> FloatArray:
        """Solve the affine inverse, refusing singular linear parts.

        Parameters
        ----------
        y
            Samples of shape ``(n, dim)``.

        Returns
        -------
        FloatArray
            Inverse images.

        Raises
        ------
        ValueError
            If the matrix is singular at the configured relative tolerance.
        """
        y = _samples(y, self.dim, "y")
        linear = self._matrix[:-1, :-1]
        if _singular(linear):
            raise ValueError("matrix linear part is singular")
        with np.errstate(all="ignore"):
            return np.linalg.solve(linear, (y - self._matrix[:-1, -1]).T).T

    def valid(self, x: FloatArray) -> BoolArray:
        """Check that inputs and their affine images are finite.

        Parameters
        ----------
        x
            Samples of shape ``(n, dim)``.

        Returns
        -------
        BoolArray
            Per-sample validity.
        """
        x = _samples(x, self.dim, "x")
        return np.isfinite(x).all(axis=1) & np.isfinite(self.apply(x)).all(axis=1)


class ScaleNode:
    """Apply a scale to one coordinate of a sample array.

    Parameters
    ----------
    scale
        One-dimensional scale.
    axis
        Column to transform.
    dim
        Sample dimension.
    """

    def __init__(self, scale: Scale, axis: int, dim: int) -> None:
        _dimension(dim)
        if not isinstance(axis, int) or isinstance(axis, bool):
            raise TypeError("axis must be an int")
        if not 0 <= axis < dim:
            raise ValueError(f"axis {axis} is outside [0, {dim})")
        self.scale = scale
        self.axis = axis
        self._dim = dim

    @property
    def dim(self) -> int:
        """Return the coordinate dimension."""
        return self._dim

    @property
    def is_affine(self) -> bool:
        """Return True exactly for a linear scale."""
        return isinstance(self.scale, LinearScale)

    @property
    def matrix(self) -> FloatArray | None:
        """Return the identity for a linear scale, otherwise None."""
        return _readonly(np.eye(self.dim + 1)) if self.is_affine else None

    def apply(self, x: FloatArray) -> FloatArray:
        """Transform the selected coordinate, preserving the others.

        Parameters
        ----------
        x
            Samples of shape ``(n, dim)``.

        Returns
        -------
        FloatArray
            Scaled samples.
        """
        result = _samples(x, self.dim, "x").copy()
        result[:, self.axis] = self.scale.forward(result[:, self.axis])
        return result

    def inverse(self, y: FloatArray) -> FloatArray:
        """Invert the selected coordinate, preserving the others.

        Parameters
        ----------
        y
            Samples of shape ``(n, dim)``.

        Returns
        -------
        FloatArray
            Inverse images.
        """
        result = _samples(y, self.dim, "y").copy()
        result[:, self.axis] = self.scale.inverse(result[:, self.axis])
        return result

    def valid(self, x: FloatArray) -> BoolArray:
        """Check finite inputs, the scale domain and finite output.

        Parameters
        ----------
        x
            Samples of shape ``(n, dim)``.

        Returns
        -------
        BoolArray
            Per-sample validity.
        """
        values = _samples(x, self.dim, "x")[:, self.axis]
        lo, hi = self.scale.domain
        lower = values >= lo if self.scale.closed[0] else values > lo
        upper = values <= hi if self.scale.closed[1] else values < hi
        return (
            np.isfinite(x).all(axis=1)
            & lower
            & upper
            & np.isfinite(self.apply(x)).all(axis=1)
        )


class FunctionNode:
    """Apply a coupled, non-affine numeric function.

    Parameters
    ----------
    function
        Vectorized sample transform.
    inverse
        Optional vectorized inverse transform.
    dim
        Input and output dimension.
    """

    def __init__(
        self,
        function: Callable[[FloatArray], FloatArray],
        inverse: Callable[[FloatArray], FloatArray] | None = None,
        *,
        dim: int,
    ) -> None:
        _dimension(dim)
        if not callable(function):
            raise TypeError("function must be callable")
        if inverse is not None and not callable(inverse):
            raise TypeError("inverse must be callable or None")
        self._function = function
        self._inverse = inverse
        self._dim = dim

    @property
    def dim(self) -> int:
        """Return the coordinate dimension."""
        return self._dim

    @property
    def is_affine(self) -> bool:
        """Return False for a function node."""
        return False

    @property
    def matrix(self) -> None:
        """Return None because function nodes are never compiled as affine."""
        return None

    def apply(self, x: FloatArray) -> FloatArray:
        """Call the function with a private copy of the samples.

        Parameters
        ----------
        x
            Samples of shape ``(n, dim)``.

        Returns
        -------
        FloatArray
            Function images with the same shape.
        """
        x = _samples(x, self.dim, "x")
        with np.errstate(all="ignore"):
            result = _samples(self._function(x.copy()), self.dim, "function output")
        if result.shape != x.shape:
            raise ValueError("function output must have the same shape as x")
        return result.copy()

    def inverse(self, y: FloatArray) -> FloatArray:
        """Call the inverse, raising when none was supplied.

        Parameters
        ----------
        y
            Samples of shape ``(n, dim)``.

        Returns
        -------
        FloatArray
            Inverse images.
        """
        if self._inverse is None:
            raise ValueError("inverse was not supplied for function")
        y = _samples(y, self.dim, "y")
        with np.errstate(all="ignore"):
            result = _samples(self._inverse(y.copy()), self.dim, "inverse output")
        if result.shape != y.shape:
            raise ValueError("inverse output must have the same shape as y")
        return result.copy()

    def valid(self, x: FloatArray) -> BoolArray:
        """Check finite inputs and finite function output.

        Parameters
        ----------
        x
            Samples of shape ``(n, dim)``.

        Returns
        -------
        BoolArray
            Per-sample validity.
        """
        x = _samples(x, self.dim, "x")
        return np.isfinite(x).all(axis=1) & np.isfinite(self.apply(x)).all(axis=1)


class Chain:
    """Compile adjacent affine nodes and evaluate them in order.

    Parameters
    ----------
    nodes
        Iterable of nodes with a common dimension.

    Notes
    -----
    An empty chain acts as an identity on arrays of any dimension. Its declared
    dimension defaults to two, the data-space dimension of a Cartesian system.
    """

    def __init__(self, nodes: Iterable[Node]) -> None:
        original = tuple(nodes)
        self._dim = original[0].dim if original else 2
        if any(node.dim != self.dim for node in original):
            raise ValueError("nodes must have the same dim")
        compiled: list[Node] = []
        pending: FloatArray | None = None
        for node in original:
            if node.is_affine:
                matrix = node.matrix
                if matrix is None:
                    raise ValueError("nodes: affine node has no matrix")
                with np.errstate(all="ignore"):
                    pending = matrix.copy() if pending is None else matrix @ pending
            else:
                if pending is not None:
                    compiled.append(AffineNode(pending))
                    pending = None
                compiled.append(node)
        if pending is not None:
            compiled.append(AffineNode(pending))
        self.nodes = tuple(compiled)

    @property
    def dim(self) -> int:
        """Return the common dimension, or two for an empty chain."""
        return self._dim

    @property
    def is_affine(self) -> bool:
        """Return whether the chain is an identity or a single affine node."""
        return not self.nodes or (len(self.nodes) == 1 and self.nodes[0].is_affine)

    def forward(self, x: FloatArray) -> FloatArray:
        """Apply the compiled nodes in order.

        Parameters
        ----------
        x
            Samples of the chain's dimension.

        Returns
        -------
        FloatArray
            A new array of transformed samples.
        """
        with np.errstate(all="ignore"):
            result = np.array(x, dtype=np.float64, copy=True)
            for node in self.nodes:
                result = node.apply(result)
        return result

    def inverse(self, y: FloatArray) -> FloatArray:
        """Apply inverse nodes in reverse order.

        Parameters
        ----------
        y
            Transformed samples.

        Returns
        -------
        FloatArray
            A new array of inverse images.
        """
        with np.errstate(all="ignore"):
            result = np.array(y, dtype=np.float64, copy=True)
            for node in reversed(self.nodes):
                result = node.inverse(result)
        return result

    def valid(self, x: FloatArray) -> BoolArray:
        """Accumulate validity at each node's current coordinates.

        Parameters
        ----------
        x
            Samples in the original input space.

        Returns
        -------
        BoolArray
            Samples valid through every compiled node.
        """
        with np.errstate(all="ignore"):
            current = np.array(x, dtype=np.float64, copy=True)
            mask = np.isfinite(current).all(axis=1)
            for node in self.nodes:
                mask &= node.valid(current)
                current = node.apply(current)
        return mask

    def apply_payload(self, payload: Payload) -> Payload:
        """Transform a payload and rebuild path segments after masking.

        Parameters
        ----------
        payload
            Validated input payload, which remains unchanged.

        Returns
        -------
        Payload
            New payload retaining invalid rows and the original topology.
        """
        current = payload.coords.copy()
        mask = (
            np.ones(len(current), dtype=np.bool_)
            if payload.valid is None
            else payload.valid.copy()
        )
        with np.errstate(all="ignore"):
            for node in self.nodes:
                mask &= node.valid(current)
                current = node.apply(current)
        segments = (
            split_segments(payload.segments, mask)
            if payload.kind == "path"
            else payload.segments
        )
        valid = None if payload.valid is None and mask.all() else mask
        return Payload(payload.kind, current, segments, payload.topology, valid)


class FrameMap:
    """Fit an affine frame or interpolate a deformed rectangular lattice.

    Parameters
    ----------
    lower, upper
        Finite two-dimensional corners with upper greater on both axes.
    nodes
        Scene positions of a square lattice, shape ``(n*n, 3)``, n at least two.
    """

    def __init__(self, lower: FloatArray, upper: FloatArray, nodes: FloatArray) -> None:
        self.lower = _readonly(lower)
        self.upper = _readonly(upper)
        self.nodes = _readonly(nodes)
        self._check_bounds(self.lower, self.upper)
        if self.nodes.ndim != 2 or self.nodes.shape[1] != 3:
            raise ValueError("nodes must have shape (n*n, 3)")
        self.n = isqrt(len(self.nodes))
        if self.n < 2 or self.n * self.n != len(self.nodes):
            raise ValueError("nodes length must be n*n for n >= 2")
        _finite(self.nodes, "nodes")
        with np.errstate(all="ignore"):
            self._span = self.upper - self.lower
            uv = self.lattice(np.zeros(2), np.ones(2), self.n)[:, :2]
            design = np.column_stack((uv, np.ones(len(uv))))
            coefficients = np.linalg.lstsq(design, self.nodes, rcond=None)[0]
            self._size = float(np.linalg.norm(np.ptp(self.nodes, axis=0)))
            if self._size == 0:
                coefficients[:2] = 0
                coefficients[2] = self.nodes[0]
            residual = np.linalg.norm(design @ coefficients - self.nodes, axis=1)
            self._is_affine = bool(np.max(residual) <= AFFINE_RTOL * self._size)
            self._basis = coefficients[:2] / self._span[:, None]
            self._origin = coefficients[2]
            self._is_singular = self.is_affine and _singular(self._basis)
            row_sizes = np.linalg.norm(self._basis, axis=1)
            normalized = np.divide(
                self._basis,
                row_sizes[:, None],
                out=np.zeros_like(self._basis),
                where=row_sizes[:, None] != 0,
            )
            normal = np.cross(normalized[0], normalized[1])
            length = np.linalg.norm(normal)
            self._normal = normal / length if length else np.zeros(3)

    @staticmethod
    def _check_bounds(lower: FloatArray, upper: FloatArray) -> None:
        if lower.shape != (2,):
            raise ValueError("lower must have shape (2,)")
        if upper.shape != (2,):
            raise ValueError("upper must have shape (2,)")
        _finite(lower, "lower")
        _finite(upper, "upper")
        if np.any(upper <= lower):
            i = int(np.flatnonzero(upper <= lower)[0])
            raise ValueError(f"upper[{i}] must be greater than lower[{i}]")

    @staticmethod
    def lattice(lower: FloatArray, upper: FloatArray, n: int) -> FloatArray:
        """Build row-major reference nodes over a local rectangle.

        Parameters
        ----------
        lower, upper
            Two-dimensional rectangle corners.
        n
            Number of nodes on each axis, at least two.

        Returns
        -------
        FloatArray
            Array of shape ``(n*n, 3)`` with zero z coordinates.
        """
        lower = _readonly(lower)
        upper = _readonly(upper)
        FrameMap._check_bounds(lower, upper)
        if not isinstance(n, int) or isinstance(n, bool):
            raise TypeError("n must be an int")
        if n < 2:
            raise ValueError("n must be at least 2")
        with np.errstate(all="ignore"):
            x, y = np.meshgrid(
                np.linspace(lower[0], upper[0], n), np.linspace(lower[1], upper[1], n)
            )
        return np.column_stack((x.ravel(), y.ravel(), np.zeros(n * n)))

    @property
    def is_affine(self) -> bool:
        """Return whether the fitted residual meets AFFINE_RTOL."""
        return self._is_affine

    @property
    def is_singular(self) -> bool:
        """Return whether the affine in-plane part meets SINGULAR_RTOL."""
        return self._is_singular

    def _cells(self, xy: FloatArray) -> tuple[IntArray, FloatArray]:
        uv = (xy - self.lower) * ((self.n - 1) / self._span)
        ij = np.floor(np.clip(uv, 0, self.n - 2)).astype(np.intp)
        index = ij[:, 1] * self.n + ij[:, 0]
        return index, uv - ij

    def _bilinear(self, xy: FloatArray) -> FloatArray:
        index, fractions = self._cells(xy)
        u, v = fractions.T
        indices = index[:, None] + [0, 1, self.n, self.n + 1]
        weights = np.column_stack(((1 - u) * (1 - v), u * (1 - v), (1 - u) * v, u * v))
        matrix = csr_matrix(
            (weights.ravel(), indices.ravel(), np.arange(0, 4 * len(xy) + 1, 4)),
            shape=(len(xy), len(self.nodes)),
        )
        return np.asarray(matrix @ self.nodes, dtype=np.float64)

    def forward(self, local: FloatArray) -> FloatArray:
        """Map local samples through the affine fit or bilinear interpolant.

        Parameters
        ----------
        local
            Array of shape ``(m, 2)`` or ``(m, 3)``. Missing z is zero;
            supplied z follows the unit normal of the fitted plane.

        Returns
        -------
        FloatArray
            Scene points of shape ``(m, 3)``. Edge cells extrapolate outside
            the local rectangle.
        """
        with np.errstate(all="ignore"):
            local = np.asarray(local, dtype=np.float64)
        if local.ndim != 2 or local.shape[1] not in (2, 3):
            raise ValueError("local must have shape (m, 2) or (m, 3)")
        result = np.full((len(local), 3), np.nan)
        good = np.isfinite(local).all(axis=1)
        points = local[good]
        with np.errstate(all="ignore"):
            mapped = (
                (points[:, :2] - self.lower) @ self._basis + self._origin
                if self.is_affine
                else self._bilinear(points[:, :2])
            )
            if local.shape[1] == 3:
                mapped += points[:, 2, None] * self._normal
            result[good] = mapped
        return result

    def _jacobian(self, xy: FloatArray) -> FloatArray:
        index, fractions = self._cells(xy)
        u, v = fractions.T[:, :, None]
        p00 = self.nodes[index]
        p10 = self.nodes[index + 1]
        p01 = self.nodes[index + self.n]
        p11 = self.nodes[index + self.n + 1]
        dx = ((1 - v) * (p10 - p00) + v * (p11 - p01)) * (self.n - 1) / self._span[0]
        dy = ((1 - u) * (p01 - p00) + u * (p11 - p10)) * (self.n - 1) / self._span[1]
        return np.stack((dx, dy), axis=2)

    def inverse(self, scene: FloatArray) -> FloatArray:
        """Invert scene points, projecting only within the plane tolerance.

        Parameters
        ----------
        scene
            Scene points of shape ``(m, 3)``.

        Returns
        -------
        FloatArray
            Local coordinates of shape ``(m, 3)``, with z equal to zero.

        Raises
        ------
        ValueError
            For a singular frame, an off-plane sample, or failure to converge
            within 50 Newton steps.

        Notes
        -----
        For a non-affine frame the branch returned is the one Newton reaches
        from the affine guess. The plane is that of the least-squares fit.
        """
        if self.is_singular:
            raise ValueError("frame is singular")
        scene = _samples(scene, 3, "scene")
        _finite(scene, "scene")
        with np.errstate(all="ignore"):
            distance = (scene - self._origin) @ self._normal
            off_plane = np.abs(distance) > PLANE_RTOL * self._size
            if np.any(off_plane):
                i = int(np.flatnonzero(off_plane)[0])
                raise ValueError(f"scene sample {i} is off the frame plane")
            projected = scene - distance[:, None] * self._normal
            xy = np.linalg.lstsq(
                self._basis.T, (projected - self._origin).T, rcond=None
            )[0].T
            xy += self.lower
            if not self.is_affine:
                tolerance = 1e-11 * self._size
                for _ in range(50):
                    residual = projected - self.forward(xy)
                    active = np.linalg.norm(residual, axis=1) > tolerance
                    finite = np.isfinite(xy).all(axis=1) & np.isfinite(residual).all(
                        axis=1
                    )
                    if not finite.all() or not np.any(active):
                        break
                    jacobian = self._jacobian(xy[active])
                    delta = np.einsum(
                        "nij,nj->ni",
                        np.linalg.pinv(jacobian, rcond=SINGULAR_RTOL),
                        residual[active],
                    )
                    xy[active] += delta
                residual = np.linalg.norm(projected - self.forward(xy), axis=1)
                failed = ~np.isfinite(residual) | (residual > tolerance)
                if np.any(failed):
                    i = int(np.flatnonzero(failed)[0])
                    raise ValueError(
                        f"scene sample {i}: frame inverse did not converge"
                    )
        return np.column_stack((xy, np.zeros(len(scene))))


class SystemMap:
    """Combine a data chain, artist placement and frame for source queries.

    Parameters
    ----------
    data
        Two-dimensional data-to-local chain.
    frame
        Local-to-scene frame map.
    own
        Optional three-dimensional artist placement chain.
    """

    def __init__(self, data: Chain, frame: FrameMap, own: Chain | None = None) -> None:
        if data.dim != 2:
            raise ValueError("data dim must be 2")
        if own is not None and own.nodes and own.dim != 3:
            raise ValueError("own dim must be 3")
        self.data = data
        self.frame = frame
        self.own = own

    @property
    def is_affine(self) -> bool:
        """Return whether data, placement and frame are all affine."""
        return (
            self.data.is_affine
            and (self.own is None or self.own.is_affine)
            and self.frame.is_affine
        )

    def forward(self, data: FloatArray) -> FloatArray:
        """Map data coordinates to local coordinates.

        Parameters
        ----------
        data
            Data samples of shape ``(n, 2)``.

        Returns
        -------
        FloatArray
            Local samples of shape ``(n, 2)``.
        """
        return self.data.forward(data)

    def inverse(self, local: FloatArray) -> FloatArray:
        """Invert the data-to-local chain.

        Parameters
        ----------
        local
            Local samples of shape ``(n, 2)``.

        Returns
        -------
        FloatArray
            Data samples of shape ``(n, 2)``.
        """
        return self.data.inverse(local)

    def valid(self, data: FloatArray) -> BoolArray:
        """Check validity throughout the data chain.

        Parameters
        ----------
        data
            Data samples of shape ``(n, 2)``.

        Returns
        -------
        BoolArray
            Per-sample validity.
        """
        return self.data.valid(data)

    def to_screen(self, data: FloatArray) -> FloatArray:
        """Map data through artist placement and the frame.

        Parameters
        ----------
        data
            Data samples of shape ``(n, 2)``.

        Returns
        -------
        FloatArray
            Scene samples of shape ``(n, 3)``.
        """
        local = self.data.forward(data)
        padded = np.column_stack((local, np.zeros(len(local))))
        placed = padded if self.own is None else self.own.forward(padded)
        return self.frame.forward(placed)
