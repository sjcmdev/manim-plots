"""Validated, immutable payloads exchanged by numeric pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from manim_plots.core import BoolArray, FloatArray, IntArray

Kind = Literal["path", "points", "region"]


def _coords(value: FloatArray) -> FloatArray:
    if not isinstance(value, np.ndarray) or not np.issubdtype(value.dtype, np.floating):
        raise TypeError("coords must be an ndarray of floating dtype")
    if value.ndim != 2:
        raise ValueError("coords must have shape (n, d)")
    with np.errstate(all="ignore"):
        return np.asarray(value, dtype=np.float64)


def _segments(value: IntArray, n: int | None) -> None:
    if not isinstance(value, np.ndarray) or not np.issubdtype(value.dtype, np.integer):
        raise TypeError("segments must be an ndarray of integer dtype")
    if value.ndim != 2 or value.shape[1] != 2:
        raise ValueError("segments must have shape (s, 2)")
    bad = (value[:, 0] < 0) | (value[:, 1] <= value[:, 0])
    if n is not None:
        bad |= value[:, 1] > n
    if np.any(bad):
        i = int(np.flatnonzero(bad)[0])
        raise ValueError(
            f"segments pair {i}: {value[i].tolist()} is out of bounds or empty"
        )
    overlap = value[1:, 0] < value[:-1, 1]
    if np.any(overlap):
        i = int(np.flatnonzero(overlap)[0]) + 1
        raise ValueError(
            f"segments pair {i}: {value[i].tolist()} overlaps or is unsorted"
        )


def _valid(value: BoolArray | None, n: int) -> None:
    if value is None:
        return
    if not isinstance(value, np.ndarray) or value.dtype != np.bool_:
        raise TypeError("valid must be an ndarray of bool dtype")
    if value.shape != (n,):
        raise ValueError(f"valid must have shape ({n},)")


def _whole_segment(n: int) -> IntArray:
    return np.array([[0, n]], dtype=np.intp) if n else np.empty((0, 2), dtype=np.intp)


def _runs(valid: BoolArray) -> IntArray:
    changes = np.diff(np.concatenate(([False], valid, [False])).astype(np.intp))
    return np.column_stack(
        (np.flatnonzero(changes == 1), np.flatnonzero(changes == -1))
    )


@dataclass(frozen=True)
class Payload:
    """Hold samples, connectivity and a per-sample validity mask.

    Parameters
    ----------
    kind
        Geometry kind: path, points or region.
    coords
        Floating array of shape ``(n, d)``.
    segments
        Sorted, non-overlapping half-open sample intervals of shape ``(s, 2)``.
    topology
        Region grid shape or cell corners; absent for other kinds.
    valid
        Boolean mask of shape ``(n,)``, or None when all samples are valid.

    Notes
    -----
    Stored arrays are read-only views. Their owners must not mutate the backing
    arrays while the payload is in use.
    """

    kind: Kind
    coords: FloatArray
    segments: IntArray
    topology: IntArray | tuple[int, int] | None = None
    valid: BoolArray | None = None

    @classmethod
    def _trusted(
        cls,
        kind: Kind,
        coords: FloatArray,
        segments: IntArray,
        topology: IntArray | tuple[int, int] | None = None,
        valid: BoolArray | None = None,
    ) -> Payload:
        """Freeze core output whose dtype, coverage and validity are already known.

        Callers must establish every constructor invariant, including finiteness
        and region winding after a coordinate transform.
        """
        result = object.__new__(cls)
        for name, value in (
            ("kind", kind),
            ("coords", coords),
            ("segments", segments),
            ("topology", topology),
            ("valid", valid),
        ):
            if isinstance(value, np.ndarray):
                value = value.view()
                value.flags.writeable = False
            object.__setattr__(result, name, value)
        return result

    def __post_init__(self) -> None:
        if not isinstance(self.kind, str):
            raise TypeError("kind must be a str")
        if self.kind not in {"path", "points", "region"}:
            raise ValueError(f"kind {self.kind!r} is unknown")
        coords = _coords(self.coords)
        n = len(coords)
        _segments(self.segments, n)
        if self.kind != "path" and not np.array_equal(self.segments, _whole_segment(n)):
            raise ValueError("segments must cover all coords for points or region")
        _valid(self.valid, n)
        valid = np.ones(n, dtype=np.bool_) if self.valid is None else self.valid
        bad = ~np.isfinite(coords).all(axis=1) & valid
        if np.any(bad):
            i = int(np.flatnonzero(bad)[0])
            raise ValueError(f"coords sample {i} is not finite where valid")
        if self.kind == "path":
            coverage = np.zeros(n + 1, dtype=np.intp)
            np.add.at(coverage, self.segments[:, 0], 1)
            np.add.at(coverage, self.segments[:, 1], -1)
            mismatch = (np.cumsum(coverage[:-1]) > 0) != valid
            if np.any(mismatch):
                i = int(np.flatnonzero(mismatch)[0])
                raise ValueError(f"segments and valid disagree at sample {i}")
        if self.kind != "region" and self.topology is not None:
            raise ValueError("topology must be None for path or points")
        if self.kind == "region":
            self._validate_topology(coords, valid)
        object.__setattr__(self, "coords", coords.view())
        object.__setattr__(
            self, "segments", np.asarray(self.segments, dtype=np.intp).view()
        )
        self.coords.flags.writeable = False
        self.segments.flags.writeable = False
        if self.valid is not None:
            object.__setattr__(self, "valid", self.valid.view())
            self.valid.flags.writeable = False
        if isinstance(self.topology, np.ndarray):
            topology = np.asarray(self.topology, dtype=np.intp).view()
            topology.flags.writeable = False
            object.__setattr__(self, "topology", topology)

    def _validate_topology(self, coords: FloatArray, valid: BoolArray) -> None:
        topology = self.topology
        if topology is None:
            raise ValueError("topology is required for region")
        n = len(coords)
        if isinstance(topology, tuple):
            if len(topology) != 2 or any(
                not isinstance(v, int) or isinstance(v, bool) for v in topology
            ):
                raise TypeError("topology grid must be a tuple of two ints")
            rows, cols = topology
            if rows < 1 or cols < 1 or rows * cols != n:
                raise ValueError(
                    f"topology grid {topology} does not match coords length {n}"
                )
            r, c = np.meshgrid(np.arange(rows - 1), np.arange(cols - 1), indexing="ij")
            start = (r * cols + c).ravel()
            cells = np.column_stack((start, start + 1, start + cols + 1, start + cols))
        elif isinstance(topology, np.ndarray) and np.issubdtype(
            topology.dtype, np.integer
        ):
            if topology.ndim != 2 or topology.shape[1] < 3:
                raise ValueError("topology cells must have shape (m, k), k >= 3")
            cells = topology
        else:
            raise TypeError("topology must be a grid tuple or an integer ndarray")
        bad = ((cells < 0) | (cells >= n)).any(axis=1)
        repeated = (np.diff(np.sort(cells, axis=1), axis=1) == 0).any(axis=1)
        if np.any(bad | repeated):
            i = int(np.flatnonzero(bad | repeated)[0])
            raise ValueError(
                f"topology cell {i}: {cells[i].tolist()} has invalid corners"
            )
        if coords.shape[1] < 2:
            raise ValueError(
                "coords for region topology must have dimension at least 2"
            )
        corners = coords[cells, :2]
        usable = valid[cells].all(axis=1) & np.isfinite(corners).all(axis=(1, 2))
        # Normalize each cell before products to keep winding finite at large scales.
        with np.errstate(all="ignore"):
            xy = corners.astype(np.longdouble)
            magnitude = np.max(np.abs(xy), axis=(1, 2), keepdims=True)
            xy = np.divide(xy, magnitude, out=np.zeros_like(xy), where=magnitude != 0)
            xy -= xy[:, :1]
            area = np.sum(
                xy[:, :, 0] * np.roll(xy[:, :, 1], -1, axis=1)
                - xy[:, :, 1] * np.roll(xy[:, :, 0], -1, axis=1),
                axis=1,
            )
        indices = np.flatnonzero(usable & (area != 0))
        if len(indices):
            different = np.sign(area[indices]) != np.sign(area[indices[0]])
            if np.any(different):
                i = int(indices[np.flatnonzero(different)[0]])
                raise ValueError(f"topology cell {i} has inconsistent winding")

    @classmethod
    def path(cls, coords: FloatArray, valid: BoolArray | None = None) -> Payload:
        """Build a path with maximal runs of valid samples.

        Parameters
        ----------
        coords
            Floating sample coordinates of shape ``(n, d)``.
        valid
            Optional boolean per-sample mask.

        Returns
        -------
        Payload
            A validated path retaining every input sample.
        """
        checked = _coords(coords)
        _valid(valid, len(checked))
        segments = _whole_segment(len(checked)) if valid is None else _runs(valid)
        return cls("path", coords, segments, valid=valid)

    @classmethod
    def points(cls, coords: FloatArray, valid: BoolArray | None = None) -> Payload:
        """Build a point set with one segment covering its samples.

        Parameters
        ----------
        coords
            Floating sample coordinates of shape ``(n, d)``.
        valid
            Optional boolean per-sample mask.

        Returns
        -------
        Payload
            A validated point set.
        """
        checked = _coords(coords)
        return cls("points", coords, _whole_segment(len(checked)), valid=valid)

    @classmethod
    def empty(cls, kind: Kind, dim: int) -> Payload:
        """Build an empty payload of the requested dimension and kind.

        Parameters
        ----------
        kind
            Geometry kind.
        dim
            Positive coordinate dimension; regions require at least two.

        Returns
        -------
        Payload
            An empty payload with no validity mask.
        """
        if not isinstance(dim, int) or isinstance(dim, bool):
            raise TypeError("dim must be an int")
        if dim < 1:
            raise ValueError("dim must be positive")
        topology = np.empty((0, 4), dtype=np.intp) if kind == "region" else None
        return cls(kind, np.empty((0, dim)), np.empty((0, 2), dtype=np.intp), topology)


def split_segments(segments: IntArray, valid: BoolArray) -> IntArray:
    """Split each interval into maximal runs of valid samples.

    Parameters
    ----------
    segments
        Sorted half-open intervals of shape ``(s, 2)``.
    valid
        One-dimensional boolean mask covering all supplied intervals. Trailing
        samples outside the intervals are allowed.

    Returns
    -------
    IntArray
        New intervals, preserving boundaries between touching input segments.
    """
    if not isinstance(valid, np.ndarray) or valid.dtype != np.bool_:
        raise TypeError("valid must be an ndarray of bool dtype")
    if valid.ndim != 1:
        raise ValueError("valid must have shape (n,)")
    _segments(segments, None)
    if len(segments) and segments[-1, 1] > len(valid):
        raise ValueError("valid shape must cover every sample in segments")
    pieces = [_runs(valid[start:stop]) + start for start, stop in segments]
    return np.concatenate(pieces) if pieces else np.empty((0, 2), dtype=np.intp)
