"""Private artists for coordinate-plane projections and drawn-data shadows."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, cast

import numpy as np
from manim import Mobject, VMobject
from numpy.typing import ArrayLike

import manim_plots as mp
from manim_plots.core import FloatArray
from manim_plots.core import lifecycle as lc
from manim_plots.core.payload import Payload
from manim_plots.core.shape import clip as clip_path
from manim_plots.core.sources import ArraySource, FunctionSource, ParametricSource
from manim_plots.mobjects.artists import (
    FunctionPlot,
    LinePlot,
    ParametricPlot,
    ScatterPlot,
    _clip_axes,
    _clip_box,
    _CurvePlot,
    _MarkerLeaf,
    _unclipped_box,
)
from manim_plots.mobjects.geometry import _ensure_binding
from manim_plots.mobjects.helpers import _Binding
from manim_plots.mobjects.leaves import _ArtistOptions, _ClipInput


def _juggle(u: ArrayLike, v: ArrayLike, c: ArrayLike, zdir: str) -> FloatArray:
    if zdir not in ("x", "y", "z"):
        raise ValueError("zdir must be x, y or z")
    return np.stack(
        np.broadcast_arrays(
            *((c, u, v) if zdir == "x" else (u, c, v) if zdir == "y" else (u, v, c))
        ),
        axis=-1,
    )


class _PlanePlot(FunctionPlot):
    def __init__(
        self,
        system: mp.ThreeDAxes,
        function: Callable[..., Any],
        x_range: Sequence[float] | None = None,
        use_vectorized: bool = False,
        *,
        zs: object,
        zdir: str,
        **kwargs: object,
    ) -> None:
        _juggle(0, 0, 0, zdir)
        self._binding = _Binding(system, lambda b: None, {"zs": zs})
        self._binding_seen = -1
        super().__init__(function, system, x_range, use_vectorized, **cast(Any, kwargs))
        original = cast(FunctionSource, self.source)

        def point(t: float) -> FloatArray:
            xy = original.at(t)[0]
            return _juggle(xy[0], xy[1], self._binding.number("zs"), zdir)

        self.source = ParametricSource(
            point,
            original._range or tuple(system.x.range.value),
            dim=3,
            discontinuities=original.discontinuities,
            dt=original.dt,
        )
        self._dirty = True
        self._ensure()

    def _ensure(self) -> None:
        if self._lifecycle.state is lc.State.ATTACHED and not self._alignment_locked:
            _ensure_binding(self._binding)
            if self._binding_seen != self._binding.version:
                self._dirty = True
                self._native_sample_key = None
        super()._ensure()
        self._binding_seen = self._binding.version

    def _poll(self) -> None:
        super()._poll()
        self._binding.poll()

    def _needs_sync(self, moving: frozenset[Any]) -> bool:
        return self._binding.needs_sync(moving) or super()._needs_sync(moving)


class _ShadowCurve(ParametricPlot):
    def __init__(
        self,
        system: mp.ThreeDAxes,
        artist: _CurvePlot,
        binding: _Binding,
        axis: int,
        **style: object,
    ) -> None:
        self._artist, self._binding, self._axis = artist, binding, axis
        self._binding_seen = -1
        super().__init__(lambda t: np.zeros(3), system, **cast(_ArtistOptions, style))

    def _poll(self) -> None:
        self._binding.poll()

    def _needs_sync(self, moving: frozenset[Any]) -> bool:
        return self._binding.needs_sync(moving)

    def _ensure(self) -> None:
        if self._lifecycle.state is lc.State.ATTACHED and not self._alignment_locked:
            _ensure_binding(self._binding)
            if self._binding_seen != self._binding.version:
                self._dirty = True
        super()._ensure()
        self._binding_seen = self._binding.version

    def _rebuild(self) -> None:
        assert self._system is not None
        artist = self._artist
        artist._ensure()
        assert artist._system is not None
        points = artist._system._data.inverse(artist._local).copy()
        points[:, self._axis] = self._binding.number("offset")
        payload = Payload._trusted(
            "path",
            self._system._data.forward(points),
            artist._geometry_payload.segments,
        )
        bounds = _clip_box(self._system, self._clip)
        axes = _clip_axes(self._clip, 3)
        if any(axis is False for axis in axes):
            bounds = _unclipped_box(bounds, axes, payload.coords)
        self._geometry_payload = clip_path(payload, bounds)
        self._place(self._frame())
        self._data_seen = self._system._data_version
        self._dirty = False


class _ShadowMarker(_MarkerLeaf):
    def __init__(
        self,
        native: Mobject,
        source: ArraySource,
        index: int,
        system: mp.ThreeDAxes,
        binding: _Binding,
        clip: _ClipInput,
    ) -> None:
        self._binding, self._binding_seen = binding, -1
        super().__init__(native, source, index, system, clip)

    def _poll(self) -> None:
        self._binding.poll()

    def _needs_sync(self, moving: frozenset[Any]) -> bool:
        return self._binding.needs_sync(moving)

    def _ensure(self) -> None:
        _ensure_binding(self._binding)
        if self._binding_seen != self._binding.version:
            self.source = ArraySource(
                self._binding.parts["points"], dim=3, kind="points"
            )
            self._dirty = True
            self._binding_seen = self._binding.version
        super()._ensure()


def _shadow(
    system: mp.ThreeDAxes,
    artist: object,
    zdir: str,
    offset: object,
    style: dict[str, Any],
) -> ParametricPlot | ScatterPlot:
    _juggle(0, 0, 0, zdir)
    if not isinstance(artist, (FunctionPlot, ParametricPlot, LinePlot, ScatterPlot)):
        raise TypeError(f"shadow does not support {type(artist).__name__}")
    if artist._system is None:
        raise ValueError("shadow requires an attached artist")
    axis = "xyz".index(zdir)
    if offset is None:
        offset = (
            "pane"
            if system.frame_style == "box"
            else system.get_axis(axis).range.value[0]
        )
    pane = isinstance(offset, str) and offset == "pane"
    if isinstance(offset, str) and (not pane or system.frame_style != "box"):
        raise ValueError('offset="pane" requires a box frame')

    def pane_offset() -> float:
        sides = system._pane_sides
        return float(
            system.get_axis(axis).range.value[int(not sides[axis]) if sides else 0]
        )

    def drawn() -> FloatArray:
        if isinstance(artist, ScatterPlot):
            artist._poll()
            return artist.source.data
        for p in artist.parameters.values():
            p.poll(p.version + 1)
        artist._ensure()
        assert artist._system is not None
        return artist._system._data.inverse(artist._local)

    binding = _Binding(
        system,
        lambda b: None,
        {"offset": pane_offset if pane else offset, "data": drawn},
    )
    _ensure_binding(binding)
    result: ParametricPlot | ScatterPlot
    if isinstance(artist, ScatterPlot):
        style.setdefault(
            "color", cast(VMobject, artist._marker_template).get_fill_color()
        )
        style.setdefault("fill_opacity", 0.35)

        def project(b: _Binding) -> None:
            points = np.asarray(b.parameters["data"].value, dtype=float).copy()
            points[:, axis] = b.number("offset")
            b.parts["points"] = points

        binding.derive = project
        project(binding)
        result = ScatterPlot(binding.parts["points"], system, **style)
        result.submobjects = [
            _ShadowMarker(
                result._marker_template,
                result.source,
                i,
                system,
                binding,
                result._clip,
            )
            for i in range(len(result.source.data))
        ]
    else:
        style.setdefault("color", artist.get_stroke_color())
        style.setdefault("stroke_opacity", 0.35)
        result = _ShadowCurve(system, artist, binding, axis, **style)
    system.add(result)
    return result
