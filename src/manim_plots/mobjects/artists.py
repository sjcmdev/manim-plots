"""Analytic artists derived from the numeric Source, Map and Shape pipeline."""

from __future__ import annotations

import warnings
from collections.abc import Callable, Iterable, Sequence
from typing import TYPE_CHECKING, Any, Self, Unpack

import numpy as np
from manim import VMobject
from manim.typing import Point3DLike, Vector3DLike
from numpy.typing import ArrayLike

from manim_plots.core import FloatArray, ManimPlotsWarning
from manim_plots.core import lifecycle as lc
from manim_plots.core.nodes import (
    AffineNode,
    Chain,
    FrameMap,
    FunctionNode,
    Node,
    SystemMap,
)
from manim_plots.core.payload import Payload, split_segments
from manim_plots.core.shape import clip, corners, densify, smooth
from manim_plots.core.sources import FunctionSource
from manim_plots.mobjects.context import (
    WriterContext,
    affine_context,
    buffer_write,
    playback_context,
    writer_context,
)
from manim_plots.mobjects.leaves import Leaf, _synchronise, _VMStyle

if TYPE_CHECKING:
    from manim_plots.mobjects.system import CartesianAxes


class FunctionPlot(Leaf):
    """Draw an analytic source through a Cartesian system's current frame.

    Parameters
    ----------
    function
        Analytic function returning y values.
    system
        Coordinate system supplying ranges, bounds and placement.
    x_range
        Optional sampling interval and maximum sample spacing.
    use_vectorized
        Evaluate arrays instead of individual scalars.
    use_smoothing
        Fit native cubic splines instead of straight cubic segments.
    discontinuities, dt
        Explicit gaps and their half-width, with Manim's meaning.
    **kwargs
        Native VMobject style options.
    """

    def __init__(
        self,
        function: Callable[..., Any],
        system: CartesianAxes,
        x_range: Sequence[float] | None = None,
        use_vectorized: bool = False,
        *,
        use_smoothing: bool = True,
        discontinuities: Iterable[float] | None = None,
        dt: float = 1e-8,
        **kwargs: Unpack[_VMStyle],
    ) -> None:
        self.source = FunctionSource(
            function,
            x_range,
            use_vectorized=use_vectorized,
            discontinuities=discontinuities,
            dt=dt,
        )
        self.use_smoothing = use_smoothing
        self._data_seen = -1
        self._local = np.empty((0, 3))
        self._geometry_payload = Payload.empty("path", 2)
        self._dense = False
        self._warned_change: tuple[int | None, int] | None = None
        super().__init__(system=system, **kwargs)
        self.add_updater(_synchronise)
        self._rebuild()

    def _frame(self) -> FrameMap:
        assert self._system is not None
        for _, frozen, excluded in self._system.frame._suspensions:
            if frozen is not None and self not in excluded:
                return frozen
        return (
            self._frozen_frame
            if self._frozen_frame is not None
            else self._system.frame.mapping
        )

    def _ensure(self) -> None:
        system = self._system
        state = self._lifecycle.state
        if system is None or state is lc.State.TRANSIENT or state is lc.State.REMOVED:
            return
        if self._lifecycle.state is lc.State.SHAPED:
            if self._shape is not None and self._frame_seen != system.frame.version:
                self._cache = self._frame().forward(self._shape)
                self._frame_seen = system.frame.version
            return
        system._sync_data()
        if self._dirty or self._data_seen != system._data_version:
            self._rebuild()
        elif self._frame_seen != system.frame.version:
            frame = self._frame()
            if self._dense == frame.is_affine:
                self._place(frame)
            else:
                self._cache = frame.forward(self._local)
                self._frame_seen = system.frame.version

    def _rebuild(self) -> None:
        system = self._system
        if system is None:
            return
        system._sync_data()
        frame = self._frame()
        mapping = SystemMap(system._data, frame)
        payload = self.source.sample(mapping, system.bounds)
        if (
            not len(payload.coords)
            or (payload.valid is not None and not payload.valid.all())
            or len(payload.segments) > len(self.source.discontinuities) + 1
        ):
            token = playback_context()
            change = (
                (None, system._data_version) if token is None else (token[0], token[2])
            )
            if self._warned_change != change:
                self._warned_change = change
                warnings.warn(
                    "function source is empty or contains invalid samples or a pole; "
                    "the path is split",
                    ManimPlotsWarning,
                    stacklevel=3,
                )
        payload = system._data.apply_payload(payload)
        if self.use_smoothing and len(payload.segments) > 1:
            # Keep visible samples and their brackets; remote pole tails ring globally.
            inside = system.bounds.contains(payload.coords)
            keep = inside.copy()
            keep[:-1] |= inside[1:]
            keep[1:] |= inside[:-1]
            if payload.valid is not None:
                keep &= payload.valid
            if inside.any():
                payload = Payload(
                    "path",
                    payload.coords,
                    split_segments(payload.segments, keep),
                    valid=keep,
                )
        payload = (smooth if self.use_smoothing else corners)(payload, system.bounds)
        self._geometry_payload = clip(payload, system.bounds)
        self._place(frame)
        self._data_seen = system._data_version
        self._dirty = False

    def _restore(self) -> None:
        system = self._system
        if system is None:
            return
        system._sync_data()
        if self._dirty or self._data_seen != system._data_version:
            self._rebuild()
        else:
            self._place(self._frame())

    def _place(self, frame: FrameMap) -> None:
        system = self._system
        assert system is not None
        payload = self._geometry_payload
        self._dense = not frame.is_affine
        count = len(payload.coords) // 4
        if self._dense and 0 < count < 64:
            payload = densify(payload, system.bounds, pieces=(64 + count - 1) // count)
        if self._own.nodes:
            local = np.column_stack((payload.coords, np.zeros(len(payload.coords))))
            self._local = self._own.forward(local)
        else:
            self._local = payload.coords
        self._cache = frame.forward(self._local)
        self._frame_seen = system.frame.version

    @property
    def points(self) -> FloatArray:
        """Return the current derived or animation-owned buffer itself."""
        if self._ready and not buffer_write():
            self._ensure()
        return self._cache

    @points.setter
    def points(self, value: ArrayLike) -> None:
        if not self._ready:
            self._cache = np.asarray(value, dtype=float)
            return
        context = writer_context()
        if context is None or self._lifecycle.state in {
            lc.State.TRANSIENT,
            lc.State.REMOVED,
        }:
            self._cache = np.asarray(value, dtype=float)
            return
        if self._write_start is None:
            self._write_start = self._cache.copy()
        self._cache = np.asarray(value, dtype=float)
        if not context.last:
            return
        start, self._write_start = self._write_start, None
        system = self._system
        if system is None:
            return
        writer = lc.Writer.FRAME if system.frame in context.family else lc.Writer.OTHER
        self._lifecycle, actions = lc.transition(self._lifecycle, lc.Write(writer))
        if actions[0].kind is lc.Kind.IGNORE:
            self._frame_seen = -1
            return
        self._cache = start
        self._capture(context)

    def _capture(self, context: WriterContext) -> None:
        if context.vector is not None:
            vector = context.vector
            self._geometry(lambda p: p + vector, np.eye(3), vector)
        elif context.application is not None:
            container, application = context.application
            factor = container.pre_function_handle_to_anchor_scale_factor
            smoothing = container.make_smooth_after_applying_functions

            def apply(points: FloatArray) -> FloatArray:
                native = VMobject().set_points(points.copy())
                native.pre_function_handle_to_anchor_scale_factor = factor
                native.make_smooth_after_applying_functions = smoothing
                return native.apply_function(application).points

            self._geometry(apply)
        else:
            function, pivot = context.function, context.pivot
            assert function is not None and pivot is not None
            matrix = context.matrix
            offset = None if matrix is None else pivot - pivot @ matrix
            self._geometry(lambda p: function(p - pivot) + pivot, matrix, offset)

    def _geometry(
        self,
        function: Callable[[FloatArray], FloatArray],
        matrix: FloatArray | None = None,
        offset: FloatArray | None = None,
    ) -> Self:
        if self._lifecycle.state in {lc.State.TRANSIENT, lc.State.REMOVED}:
            self._cache = function(self._cache)
            return self
        self._ensure()
        frame = self._frame()
        if frame.is_singular:
            raise ValueError("system frame is singular; artist transform refused")
        if self._lifecycle.state is lc.State.SHAPED:
            transformed = function(self.points)
            local = frame.inverse(transformed)
            self._shape, self._cache = local, transformed
            return self
        if frame.is_affine and matrix is not None:
            basis_points = frame.forward(np.vstack((np.zeros(3), np.eye(3))))
            origin = basis_points[0]
            basis = basis_points[1:] - origin
            inverse = np.linalg.inv(basis)
            shift = np.zeros(3) if offset is None else offset
            linear = basis @ matrix @ inverse
            translation = (origin @ matrix + shift - origin) @ inverse
            node: Node = AffineNode.from_parts(linear.T, translation)
        else:
            node = FunctionNode(
                lambda p: frame.inverse(function(frame.forward(p))), dim=3
            )
        self._own = Chain((*self._own.nodes, node))
        local = self._local
        if local.shape[1] == 2:
            local = np.column_stack((local, np.zeros(len(local))))
        self._local = node.apply(local)
        self._cache = function(self._cache)
        return self

    def shift(self, *vectors: Vector3DLike) -> Self:
        """Record a native translation in the system's local space.

        Parameters
        ----------
        *vectors
            Native scene-space vectors, summed before application.
        """
        vector = np.sum(np.asarray(vectors, dtype=float), axis=0)
        return self._geometry(lambda p: p + vector, np.eye(3), vector)

    def apply_points_function_about_point(
        self,
        func: Callable[[FloatArray], FloatArray],
        about_point: Point3DLike | None = None,
        about_edge: Vector3DLike | None = None,
    ) -> Self:
        """Record the exact native matrix or a non-affine placement node.

        Parameters
        ----------
        func, about_point, about_edge
            Native points function and pivot conventions.
        """
        if about_point is None:
            about_point = self.get_critical_point(
                np.zeros(3) if about_edge is None else about_edge
            )
        pivot = np.array(about_point, dtype=float, copy=True)
        matrix = affine_context()
        offset = None if matrix is None else pivot - pivot @ matrix
        return self._geometry(lambda p: func(p - pivot) + pivot, matrix, offset)

    def apply_function(
        self,
        function: Callable[..., Any],
        *,
        about_point: Point3DLike | None = None,
        about_edge: Vector3DLike | None = None,
    ) -> Self:
        """Apply Manim's handle preparation as a permanent local operation.

        Parameters
        ----------
        function, about_point, about_edge
            Native mapping and pivot options.
        """
        factor = self.pre_function_handle_to_anchor_scale_factor
        smoothing = self.make_smooth_after_applying_functions

        def apply(points: FloatArray) -> FloatArray:
            native = VMobject().set_points(points.copy())
            native.pre_function_handle_to_anchor_scale_factor = factor
            native.make_smooth_after_applying_functions = smoothing
            return native.apply_function(
                function, about_point=about_point, about_edge=about_edge
            ).points

        return self._geometry(apply)

    def _adopt(self, other: Leaf) -> None:
        if isinstance(other, FunctionPlot):
            self.source = other.source
            self.use_smoothing = other.use_smoothing
        super()._adopt(other)
        self._rebuild()
