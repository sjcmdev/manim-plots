"""Bound surfaces, wireframes and level contours in three dimensions."""

from __future__ import annotations

import copy
import inspect
from collections.abc import Callable, Sequence
from typing import Any, Literal, Self, cast

import numpy as np
from manim import (
    BLUE_D,
    BLUE_E,
    LIGHT_GREY,
    ManimColor,
    Mobject,
    VGroup,
    VMobject,
)
from manim.mobject.three_d.three_dimensions import ThreeDVMobject
from manim.utils.color import ParsableManimColor
from numpy.typing import ArrayLike

import manim_plots as mp
from manim_plots.core import FloatArray
from manim_plots.core.nodes import CompiledMap
from manim_plots.core.params import Parameter
from manim_plots.core.payload import Payload
from manim_plots.core.scales import Scale
from manim_plots.core.sources import ArraySource, Bounds
from manim_plots.mobjects.artists import (
    FunctionPlot,
    ParametricPlot,
    _clip_axes,
    _clip_box,
    _clip_has_margin,
    _CurvePlot,
    _parameterize,
    _validate_clip,
)
from manim_plots.mobjects.colormaps import ColorMapping, resolve_colorscale
from manim_plots.mobjects.context import animation_context
from manim_plots.mobjects.geometry import PlanePlot, _ensure_binding
from manim_plots.mobjects.helpers import _Binding
from manim_plots.mobjects.leaves import _ClipInput


def _parameterize_surface(
    function: Callable[..., Any], options: dict[str, Any]
) -> tuple[Callable[..., Any], dict[str, Parameter[Any]]]:
    def point_function(point: FloatArray, *args: object, **values: object) -> object:
        return cast(object, function(point[..., 0], point[..., 1], *args, **values))

    try:
        signature = inspect.signature(function)
        cast(Any, point_function).__signature__ = signature.replace(
            parameters=[
                inspect.Parameter("point", inspect.Parameter.POSITIONAL_ONLY),
                *list(signature.parameters.values())[2:],
            ]
        )
    except (ValueError, TypeError):
        pass
    return _parameterize(point_function, options)


class _FaceStyle(VMobject):
    _styled: bool
    _owner: Any

    def set_fill(
        self,
        color: ParsableManimColor | None = None,
        opacity: float | None = None,
        family: bool = True,
    ) -> Self:
        self._styled = True
        return super().set_fill(color, opacity, family)

    def set_color(self, *args: object, **kwargs: object) -> Self:
        self._styled = True
        return cast(Self, cast(Any, super().set_color)(*args, **kwargs))

    def set_style(self, *args: object, **kwargs: object) -> Self:
        self._styled = True
        return cast(Self, cast(Any, super().set_style)(*args, **kwargs))

    def _paint(
        self, rgb_fill: ParsableManimColor, rgb_stroke: ParsableManimColor | None = None
    ) -> None:
        VMobject.set_fill(self, rgb_fill, opacity=self._owner._opacity)
        if rgb_stroke is not None:
            VMobject.set_stroke(self, rgb_stroke)


class _Face(_FaceStyle, ThreeDVMobject):
    def __init__(self, owner: SurfacePlot, **kwargs: object) -> None:
        self._owner = owner
        self._styled = False
        self._face_points = np.empty((0, 3))
        super().__init__(**cast(dict[str, Any], kwargs))
        self._styled = False

    @property
    def points(self) -> FloatArray:
        driver = self._owner.__dict__.get("_driver")
        if driver is not None and not self._owner._building:
            driver._ensure()
        elif self._owner._building:
            presentation = self.__dict__.get("_presentation")
            if presentation is not None:
                presentation()
        return self._face_points

    @points.setter
    def points(self, value: ArrayLike) -> None:
        self._face_points = np.asarray(value, float)

    def get_fill_color(self) -> ManimColor:
        _ = self.points
        return super().get_fill_color()

    def get_stroke_color(self, background: bool = False) -> ManimColor:
        _ = self.points
        return cast(ManimColor, super().get_stroke_color(background))


class FaceGroup(VGroup):
    """Hold stable surface cells addressed by their grid or triangle key.

    Parameters
    ----------
    faces
        Mapping from cell keys to faces.
    """

    def __init__(self, faces: dict[tuple[int, int] | int, _Face]) -> None:
        self._faces = faces
        super().__init__(*faces.values())

    def at(self, key: tuple[int, int] | int) -> _Face:
        """Return a face, raising KeyError for an absent key.

        Parameters
        ----------
        key
            Grid index pair or triangle number.

        Returns
        -------
        VMobject
            The stable face object.
        """
        return self._faces[key]


class _SurfaceDriver(_CurvePlot):
    def __init__(self, owner: SurfacePlot) -> None:
        self.owner = owner
        self.parameters = owner._parameters
        super().__init__(
            ArraySource(np.empty((0, 3)), dim=3),
            owner._system,
            clip=False,
            color=BLUE_D,
        )
        owner._system.add(self)

    def _rebuild(self) -> None:
        self.owner._derive()
        self._data_seen = self.owner._system._data_version
        self._frame_seen = self.owner._system.frame.version
        self._dirty = False
        self._parameter_versions = {
            name: p.version for name, p in self.parameters.items()
        }

    def _ensure(self) -> None:
        # The curve driver owns dependency polling and the dirty fast path.
        if self.owner._building:
            return
        old = self._frame_seen
        if old != self.owner._system.frame.version and _clip_has_margin(
            self.owner._clip
        ):
            self._dirty = True
        super()._ensure()
        if self.owner._placed_frame != self.owner._system.frame.version:
            self.owner._place_faces()
            self._frame_seen = self.owner._system.frame.version


class SurfacePlot(VGroup):
    """Draw stable, individually styleable cells of a data-space surface.

    Parameters
    ----------
    system
        Owning three-dimensional coordinate system.
    function
        Scalar height function of two parameters.
    u_range, v_range
        Parameter intervals, defaulting to the x and y ranges.
    colorscale, colorscale_axis
        Colour rule and coordinate or callable used for values.
    resolution
        Cell count per parameter, or a pair of counts.
    vmin, vmax, norm, clip
        Colour normalisation and box clipping policy.
    **kwargs
        Manim Surface style options.
    """

    def __init__(
        self,
        system: mp.ThreeDAxes,
        function: Callable[..., Any],
        u_range: Sequence[float] | None = None,
        v_range: Sequence[float] | None = None,
        colorscale: object = None,
        colorscale_axis: int | str | Callable[..., Any] = 2,
        *,
        resolution: int | tuple[int, int] = 32,
        vmin: float | None = None,
        vmax: float | None = None,
        norm: Scale | str | None = None,
        clip: _ClipInput = True,
        _kind: str = "height",
        _vertices: FloatArray | None = None,
        _triangles: ArrayLike | None = None,
        _axis: int = 2,
        **kwargs: object,
    ) -> None:
        self._system = system
        self._kind, self._vertices = _kind, _vertices
        self._triangles = (
            None if _triangles is None else np.asarray(_triangles, dtype=np.intp)
        )
        self._axis = _axis
        options = cast(dict[str, Any], kwargs)
        if _kind in {"height", "parametric"}:
            self._function, self._parameters = _parameterize_surface(function, options)
        elif _kind == "revolution":
            self._function, self._parameters = _parameterize(function, options)
        else:
            self._function, self._parameters = function, {}
        self._u_range, self._v_range = u_range, v_range
        self._resolution = (
            (resolution, resolution) if isinstance(resolution, int) else resolution
        )
        self._clip = _validate_clip(clip, 3)
        self._building = True
        self._colorscale, self._color_axis = colorscale, colorscale_axis
        self._vmin, self._vmax, self._norm = vmin, vmax, norm
        self._color_mapping: ColorMapping | None = None
        self._checker = options.pop(
            "checkerboard_colors", False if _kind == "triangles" else (BLUE_D, BLUE_E)
        )
        self._fill = options.pop("fill_color", BLUE_D)
        self._opacity = options.pop("fill_opacity", 1)
        self._explicit_stroke = "stroke_color" in kwargs
        self._stroke = options.pop("stroke_color", LIGHT_GREY)
        self._stroke_width = options.pop("stroke_width", 0.5)
        self._jagged = options.pop("should_make_jagged", False)
        options.pop("pre_function_handle_to_anchor_scale_factor", None)
        piece_config = options.pop("surface_piece_config", {})
        super().__init__(**options)
        if _kind == "triangles":
            assert self._triangles is not None
        keys: list[tuple[int, int] | int] = (
            list(range(len(cast(Any, self._triangles))))
            if _kind == "triangles"
            else [
                (i, j)
                for i in range(self._resolution[0])
                for j in range(self._resolution[1])
            ]
        )
        self.faces = FaceGroup(
            {
                key: _Face(
                    self,
                    **options,
                    fill_opacity=self._opacity,
                    stroke_width=self._stroke_width,
                    **piece_config,
                )
                for key in keys
            }
        )
        self.add(self.faces)
        self._local_faces: list[FloatArray] = []
        self._driver = _SurfaceDriver(self)
        self._building = False

    @property
    def color_mapping(self) -> ColorMapping | None:
        """Return the current value mapping, or None for a checkerboard."""
        self._driver._ensure()
        if self._building:
            # Buffer ownership suspends geometry, not the bound colour range.
            self._system._sync_data()
            self._paint_faces()
        return self._color_mapping

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        result = type(self).__new__(type(self))
        memo[id(self)] = result
        for key, value in self.__dict__.items():
            result.__dict__[key] = (
                value if key == "_system" else copy.deepcopy(value, memo)
            )
        return result

    def suspend_updating(self, recursive: bool = True) -> Self:
        """Let native animations own the face buffers.

        Parameters
        ----------
        recursive
            Suspend descendants as on a native surface.
        """
        self._building = True
        return super().suspend_updating(recursive)

    def resume_updating(self, recursive: bool = True) -> Self:
        """Restore binding and adopt a completed surface transform.

        Parameters
        ----------
        recursive
            Resume descendants as on a native surface.
        """
        animation = animation_context(finishing=True)
        target = getattr(animation, "target_mobject", None)
        if (
            isinstance(target, SurfacePlot)
            and animation is not None
            and animation.rate_func(1) == 1
        ):
            self._adopt(target)
        self._building = False
        return super().resume_updating(recursive)

    def _adopt(self, target: SurfacePlot) -> None:
        for name in (
            "_kind",
            "_vertices",
            "_triangles",
            "_axis",
            "_function",
            "_parameters",
            "_u_range",
            "_v_range",
            "_resolution",
            "_clip",
            "_colorscale",
            "_color_axis",
            "_vmin",
            "_vmax",
            "_norm",
            "_checker",
            "_fill",
            "_opacity",
            "_explicit_stroke",
            "_stroke",
            "_stroke_width",
            "_jagged",
        ):
            setattr(self, name, copy.copy(getattr(target, name)))
        self.faces = cast(FaceGroup, self.submobjects[0])
        del self.faces.submobjects[len(target.faces) :]
        self.faces._faces = dict(
            zip(
                target.faces._faces,
                cast(list[_Face], self.faces.submobjects),
                strict=False,
            )
        )
        for face in self.faces:
            cast(_Face, face)._owner = self
        self._driver.parameters = self._parameters
        self._driver._dirty = True

    def become(
        self,
        mobject: Mobject,
        match_height: bool = False,
        match_width: bool = False,
        match_depth: bool = False,
        match_center: bool = False,
        stretch: bool = False,
    ) -> Self:
        """Adopt another surface's bound definition after native alignment.

        Parameters
        ----------
        mobject, match_height, match_width, match_depth, match_center, stretch
            Native target and placement options.
        """
        super().become(
            mobject, match_height, match_width, match_depth, match_center, stretch
        )
        if isinstance(mobject, SurfacePlot):
            self._adopt(mobject)
        return self

    def _evaluate(self, uv: FloatArray) -> FloatArray:
        u, v = uv[..., 0], uv[..., 1]

        def evaluate(a: FloatArray, b: FloatArray) -> FloatArray:
            if self._kind == "revolution":
                radius = self._function(a)
                along = np.broadcast_to(a, np.shape(a))
                components = (
                    [radius * np.cos(b), radius * np.sin(b), along]
                    if self._axis == 2
                    else [along, radius * np.cos(b), radius * np.sin(b)]
                    if self._axis == 0
                    else [radius * np.sin(b), along, radius * np.cos(b)]
                )
                return np.stack(components, axis=-1)
            result = np.asarray(self._function(np.stack((a, b), axis=-1)), float)
            if self._kind == "height":
                if result.shape != np.shape(a):
                    raise ValueError("shape")
                return np.stack((a, b, result), axis=-1)
            if result.shape == (3, *np.shape(a)):
                return np.moveaxis(result, 0, -1)
            if result.shape != (*np.shape(a), 3):
                raise ValueError("shape")
            return result

        try:
            return evaluate(u, v)
        except Exception:
            result = np.vectorize(evaluate, signature="(),()->(d)")(u, v)
            return np.asarray(result, float)

    def _derive(self) -> None:
        self._building = True
        try:
            if self._kind in {"grid", "triangles"}:
                assert self._vertices is not None
                if self._kind == "triangles":
                    assert self._triangles is not None
                    corners = self._vertices[self._triangles]
                    self._grid = self._vertices
                else:
                    grid = self._vertices
                    corners = np.stack(
                        (grid[:-1, :-1], grid[1:, :-1], grid[1:, 1:], grid[:-1, 1:]),
                        axis=-2,
                    ).reshape(-1, 4, 3)
                    self._grid = grid.reshape(-1, 3)
                self._centres = corners.mean(axis=1)
                self._corner_data = corners
                mapped = self._system._data.forward(corners.reshape(-1, 3)).reshape(
                    corners.shape
                )
                self._local_faces = [
                    VMobject().set_points_as_corners(np.concatenate((c, c[:1]))).points
                    for c in mapped
                ]
                self._clip_faces()
                self._place_faces()
                self._paint_faces()
                return
            nu, nv = self._resolution
            ur = (
                self._u_range
                if self._u_range is not None
                else self._system.get_axis(
                    self._axis if self._kind == "revolution" else 0
                ).range.value
            )
            self._us = np.linspace(float(ur[0]), float(ur[1]), nu + 1)
            vr = (
                self._v_range
                if self._v_range is not None
                else self._system.y.range.value
            )
            self._vs = np.linspace(float(vr[0]), float(vr[1]), nv + 1)
            u, v = np.meshgrid(self._us[:-1], self._vs[:-1], indexing="ij")
            U, V = np.meshgrid(self._us[1:], self._vs[1:], indexing="ij")
            uv = np.stack(
                (
                    np.stack((u, v), -1),
                    np.stack((U, v), -1),
                    np.stack((U, V), -1),
                    np.stack((u, V), -1),
                    np.stack((u, v), -1),
                ),
                -2,
            ).reshape(-1, 5, 2)
            alpha = np.linspace(0, 1, 4)
            bezier = (
                uv[:, :-1, None, :] * (1 - alpha[None, None, :, None])
                + uv[:, 1:, None, :] * alpha[None, None, :, None]
            ).reshape(-1, 16, 2)
            gu, gv = np.meshgrid(self._us, self._vs, indexing="ij")
            self._uv_grid = np.stack((gu, gv), -1).reshape(-1, 2)
            self._grid = self._evaluate(self._uv_grid)
            points = self._evaluate(bezier)
            self._corner_data = points[:, ::4]
            self._centres = self._evaluate((uv[:, 0] + uv[:, 2]) / 2)
            self._local_faces = list(
                self._system._data.forward(points.reshape(-1, 3)).reshape(-1, 16, 3)
            )
            self._clip_faces()
            self._place_faces()
            self._paint_faces()
        finally:
            self._building = False

    def _clip_faces(self) -> None:
        bounds = _clip_box(self._system, self._clip)
        enabled = np.array([a is not False for a in _clip_axes(self._clip, 3)])
        native = self._system._data.forward(self._corner_data.reshape(-1, 3)).reshape(
            self._corner_data.shape
        )
        finite = np.isfinite(native).all(axis=(1, 2))
        below = (native < bounds.lower - 1e-12) & enabled
        above = (native > bounds.upper + 1e-12) & enabled
        inside = ~(below | above).any(axis=(1, 2))
        outside = (below.all(axis=1) | above.all(axis=1)).any(axis=1)
        for k in np.flatnonzero(~finite | outside):
            self._local_faces[k] = np.empty((0, 3))
        for k in np.flatnonzero(finite & ~inside & ~outside):
            polygon = native[k]
            for axis in np.flatnonzero(enabled):
                for edge, sign in ((bounds.lower[axis], 1), (bounds.upper[axis], -1)):
                    output = []
                    for a, b in zip(polygon, np.roll(polygon, -1, axis=0), strict=True):
                        ia, ib = (
                            sign * (a[axis] - edge) >= 0,
                            sign * (b[axis] - edge) >= 0,
                        )
                        if ia:
                            output.append(a)
                        if ia != ib:
                            output.append(
                                a + (edge - a[axis]) / (b[axis] - a[axis]) * (b - a)
                            )
                    polygon = np.asarray(output, float).reshape(-1, 3)
                    if not len(polygon):
                        break
                if not len(polygon):
                    break
            self._local_faces[k] = (
                VMobject()
                .set_points_as_corners(np.concatenate((polygon, polygon[:1])))
                .points
                if len(polygon)
                else np.empty((0, 3))
            )

    def _place_faces(self) -> None:
        was_building = self._building
        self._building = True
        self._placed_frame = self._system.frame.version
        try:
            for face, local in zip(self.faces, self._local_faces, strict=True):
                if np.isfinite(local).all():
                    face.set_points(self._system.frame.mapping.forward(local))
                    if self._jagged:
                        face.make_jagged()
                else:
                    face.clear_points()
        finally:
            self._building = was_building

    def _paint_faces(self) -> None:
        colors = None
        if self._colorscale is not None:
            limits: Sequence[float] | FloatArray
            axis = self._color_axis
            if callable(axis):
                try:
                    values = np.asarray(axis(*self._centres.T), float)
                    if values.shape != (len(self._centres),):
                        raise ValueError("shape")
                except Exception:
                    values = np.array([axis(*p) for p in self._centres], float)
                limits = (float(np.nanmin(values)), float(np.nanmax(values)))
                scale = None
            else:
                index = "xyz".index(axis) if isinstance(axis, str) else int(axis)
                coordinate = self._system.get_axis(index)
                limits, scale = coordinate.range.value, coordinate._scale
                values = self._centres[:, index]
            self._color_mapping = resolve_colorscale(
                self._colorscale,
                vmin=self._vmin,
                vmax=self._vmax,
                norm=self._norm,
                default_range=limits,
                default_scale=scale,
            )
            colors = self._color_mapping(values)
        else:
            self._color_mapping = None
        for k, (key, face) in enumerate(self.faces._faces.items()):
            if not face._styled:
                index = sum(key) if isinstance(key, tuple) else key
                color = (
                    ManimColor.from_rgb(colors[k])
                    if colors is not None
                    else self._checker[index % len(self._checker)]
                    if self._checker
                    else self._fill
                )
                stroke = (
                    color
                    if colors is not None and not self._explicit_stroke
                    else self._stroke
                )
                face._paint(color, stroke)

    def set_colorscale(
        self,
        colorscale: object,
        colorscale_axis: int | str | Callable[..., Any] = 2,
        *,
        vmin: float | None = None,
        vmax: float | None = None,
        norm: Scale | str | None = None,
    ) -> Self:
        """Replace the colour rule and discard individual face overrides.

        Parameters
        ----------
        colorscale, colorscale_axis, vmin, vmax, norm
            Colormap, value source and normalisation options.
        """
        self._colorscale, self._color_axis = colorscale, colorscale_axis
        self._vmin, self._vmax, self._norm = vmin, vmax, norm
        for face in self.faces._faces.values():
            face._styled = False
        self._paint_faces()
        return self

    def set_fill_by_checkerboard(
        self, *colors: ParsableManimColor, opacity: float | None = None
    ) -> Self:
        """Replace the colour rule with alternating fills.

        Parameters
        ----------
        *colors, opacity
            Checkerboard colours and optional fill opacity.
        """
        self._checker, self._colorscale, self._color_mapping = colors, None, None
        if opacity is not None:
            self._opacity = opacity
        for face in self.faces._faces.values():
            face._styled = False
        self._paint_faces()
        return self

    def set_fill_by_value(
        self,
        axes: mp.ThreeDAxes,
        colorscale: object = None,
        axis: int | str | Callable[..., Any] = 2,
        **kwargs: object,
    ) -> Self:
        """Replace the colour rule with a value mapping.

        Parameters
        ----------
        axes, colorscale, axis, **kwargs
            Coordinate system, colormap, value coordinate and normalisation.
        """
        if colorscale is not None:
            self.set_colorscale(colorscale, axis, **cast(dict[str, Any], kwargs))
        return self

    def slice(
        self, *, x: object = None, y: object = None, z: object = None, **style: object
    ) -> ParametricPlot | ContourPlot:
        """Draw a bound coordinate section of this surface.

        Parameters
        ----------
        x, y, z, **style
            Exactly one bound coordinate and ordinary curve style options.

        Returns
        -------
        ParametricPlot or ContourPlot
            The surface section, following the coordinate and surface parameters.
        """
        axis, value = _slice_input("slice", (x, y, z))
        if self._kind == "height" and axis < 2:
            artist = _SurfaceSlice(self, axis, value, **style)
            self._system.add(artist)
            return artist
        binding = _slice_binding(self, self._system, axis, value)
        binding.ensure()
        from manim_plots.mobjects.artists import _cycle_style

        _cycle_style(self._system, cast(Any, style))
        result = self.contour(
            [binding.number("coordinate")], zdir="xyz"[axis], **cast(Any, style)
        )
        for line in result._lines.values():
            line._slice_binding = binding
        return result

    def contour(
        self,
        levels: Sequence[float] | int | None = None,
        *,
        zdir: str = "z",
        offset: float | Literal["pane"] | None = None,
        colorscale: object = None,
        **kwargs: object,
    ) -> ContourPlot:
        """Extract smooth level lines, optionally projected onto a plane.

        Parameters
        ----------
        levels, zdir, offset, colorscale, **kwargs
            Levels, coordinate, projection plane, colormap and curve styles.

        Returns
        -------
        ContourPlot
            Bound curves addressed by their level values.
        """
        return ContourPlot(
            self, levels, zdir=zdir, offset=offset, colorscale=colorscale, **kwargs
        )


class _LineGroup(VGroup):
    def __init__(self, values: Callable[[], FloatArray], *lines: VMobject) -> None:
        self._values = values
        super().__init__(*lines)

    def at(self, value: float) -> VMobject:
        for v, line in zip(self._values(), self.submobjects, strict=True):
            if abs(v - value) <= 1e-9:
                return line
        raise KeyError(value)


class _WireframeLine(ParametricPlot):
    def _rebuild(self) -> None:
        # Default parameter intervals read current ranges inside the curve function.
        self._native_sample_key = None
        super()._rebuild()


class WireframePlot(VGroup):
    """Draw adaptive curves at evenly spaced surface parameters.

    Parameters
    ----------
    system, function, u_range, v_range
        Axes, height function and optional parameter ranges.
    resolution, clip, **kwargs
        Interval counts, clipping policy and curve styles.
    """

    def __init__(
        self,
        system: mp.ThreeDAxes,
        function: Callable[..., Any],
        u_range: Sequence[float] | None = None,
        v_range: Sequence[float] | None = None,
        *,
        resolution: int | tuple[int, int] = 10,
        clip: _ClipInput = True,
        **kwargs: object,
    ) -> None:
        from manim_plots.mobjects.artists import _cycle_style

        super().__init__()
        options = cast(dict[str, Any], kwargs)
        function, parameters = _parameterize_surface(function, options)
        _cycle_style(system, cast(Any, options))
        nu, nv = (resolution, resolution) if isinstance(resolution, int) else resolution

        def us() -> FloatArray:
            r = u_range if u_range is not None else system.x.range.value
            return np.linspace(float(r[0]), float(r[1]), nu + 1)

        def vs() -> FloatArray:
            r = v_range if v_range is not None else system.y.range.value
            return np.linspace(float(r[0]), float(r[1]), nv + 1)

        def curve(index: int, along_u: bool) -> VMobject:
            def point(t: float) -> FloatArray:
                a, b = us(), vs()
                u = a[index] if along_u else a[0] + t * (a[-1] - a[0])
                v = b[0] + t * (b[-1] - b[0]) if along_u else b[index]
                return np.array([u, v, function(np.array([u, v]))])

            line = _WireframeLine(
                point, system, t_range=(0, 1), clip=clip, **cast(Any, options)
            )
            line.parameters = parameters
            line._rebuild()
            system.add(line)
            return line

        self.u_lines = _LineGroup(us, *(curve(i, True) for i in range(nu + 1)))
        self.v_lines = _LineGroup(vs, *(curve(i, False) for i in range(nv + 1)))
        self.add(self.u_lines, self.v_lines)


class _ContourSource:
    def __init__(
        self,
        surface: SurfacePlot,
        level: float,
        axis: int,
        offset: float | Literal["pane"] | None,
    ) -> None:
        self.surface, self.level, self.axis, self.offset = surface, level, axis, offset
        self.value_function: Callable[[FloatArray], FloatArray] | None = None

    def at(self, t: ArrayLike) -> FloatArray:
        raise NotImplementedError("contours are sampled as connected paths")

    def sample(self, map: CompiledMap, bounds: Bounds) -> Payload:
        from manim_plots.core.shape import _assemble, marching_squares

        s = self.surface
        s._driver._ensure()
        values = (
            s._grid[:, self.axis]
            if self.value_function is None
            else self.value_function(s._grid)
        ) - self.level
        if s._kind == "triangles":
            locations: dict[tuple[int, int], FloatArray] = {}
            neighbours: dict[tuple[int, int], list[tuple[int, int]]] = {}
            assert s._triangles is not None
            for triangle in s._triangles:
                crossings = []
                for i, j in zip(triangle, np.roll(triangle, -1), strict=True):
                    a, b = values[i], values[j]
                    if not np.isfinite([a, b]).all() or (a >= 0) == (b >= 0):
                        continue
                    key = (
                        (int(i), int(i))
                        if a == 0
                        else (int(j), int(j))
                        if b == 0
                        else (min(int(i), int(j)), max(int(i), int(j)))
                    )
                    locations[key] = s._grid[i] + a / (a - b) * (
                        s._grid[j] - s._grid[i]
                    )
                    crossings.append(key)
                if len(crossings) == 2 and crossings[0] != crossings[1]:
                    akey, bkey = crossings
                    neighbours.setdefault(akey, []).append(bkey)
                    neighbours.setdefault(bkey, []).append(akey)
            parts = []
            while neighbours:
                current = next(
                    (k for k, v in neighbours.items() if len(v) == 1),
                    next(iter(neighbours)),
                )
                path = [locations[current]]
                while current in neighbours:
                    following = neighbours[current].pop()
                    if not neighbours[current]:
                        del neighbours[current]
                    neighbours[following].remove(current)
                    if not neighbours[following]:
                        del neighbours[following]
                    path.append(locations[following])
                    current = following
                parts.append(np.array(path))
            payload = _assemble(parts, 3)
        else:
            coords = s._uv_grid if s._kind not in {"grid", "triangles"} else s._grid
            nu, nv = s._resolution
            valid = np.isfinite(coords).all(axis=1) & np.isfinite(values)
            region = Payload._trusted(
                "region",
                coords,
                np.array([[0, len(coords)]]),
                (nu + 1, nv + 1),
                valid,
                values,
            )
            extracted = marching_squares(region, bounds)
            points = (
                s._evaluate(extracted.coords)
                if s._kind != "grid"
                else extracted.coords.copy()
            )
            payload = Payload("path", points, extracted.segments)
        if self.offset is not None:
            points = payload.coords.copy()
            offset = self.offset
            if offset == "pane":
                sides = s._system._pane_sides
                offset = (
                    s._system.get_axis(self.axis).range.value[int(not sides[self.axis])]
                    if sides
                    else s._system.get_axis(self.axis).range.value[0]
                )
            points[:, self.axis] = float(offset)
            payload = Payload("path", points, payload.segments)
        return payload


class _ContourLine(_CurvePlot):
    def __init__(
        self, source: _ContourSource, *, _follow_mapping: bool = False, **kwargs: object
    ) -> None:
        self.surface = source.surface
        self._follow_mapping = _follow_mapping
        self._last_mapping = self.surface.color_mapping if _follow_mapping else None
        self.parameters = self.surface._parameters
        self._pane_seen: Any = None
        self._slice_binding: _Binding | None = None
        super().__init__(cast(Any, source), self.surface._system, **cast(Any, kwargs))
        self.surface._system.add(self)

    def _ensure(self) -> None:
        source = cast(_ContourSource, self.source)
        if self._slice_binding is not None:
            _ensure_binding(self._slice_binding)
            level = self._slice_binding.number("coordinate")
            if source.level != level:
                source.level = level
                self._dirty = True
        if source.offset == "pane":
            sides = self.surface._system._pane_sides
            if sides != self._pane_seen:
                self._pane_seen = sides
                self._dirty = True
        super()._ensure()
        if self._follow_mapping:
            mapping = self.surface.color_mapping
            if mapping is not None and mapping is not self._last_mapping:
                previous = self._last_mapping
                current = self.get_stroke_color()
                if previous is None or current == ManimColor.from_rgb(
                    previous(source.level)
                ):
                    VMobject.set_stroke(
                        self, ManimColor.from_rgb(mapping(source.level))
                    )
                self._last_mapping = mapping

    def _rebuild(self) -> None:
        if self._slice_binding is not None and not self._slice_binding.valid:
            self._geometry_payload = Payload.empty("path", 3)
            self._place(self._frame())
            self._dirty = False
            self._data_seen = self.surface._system._data_version
            return
        super()._rebuild()

    def _needs_sync(self, moving: frozenset[Any]) -> bool:
        return (
            (self._slice_binding is not None and self._slice_binding.needs_sync(moving))
            or cast(_ContourSource, self.source).offset == "pane"
            or super()._needs_sync(moving)
        )


class ContourPlot(VGroup):
    """Hold one bound smooth curve for each surface level.

    Parameters
    ----------
    surface, levels
        Source surface and explicit levels, interior count, or axis ticks.
    zdir, offset, colorscale, **kwargs
        Level coordinate, optional projection plane, colormap and curve style.
    """

    def __init__(
        self,
        surface: SurfacePlot,
        levels: Sequence[float] | int | None = None,
        *,
        zdir: str = "z",
        offset: float | Literal["pane"] | None = None,
        colorscale: object = None,
        **kwargs: object,
    ) -> None:
        super().__init__()
        if zdir not in ("x", "y", "z"):
            raise ValueError("zdir must be x, y or z")
        s, axis = surface, "xyz".index(zdir)
        s._driver._ensure()
        if offset == "pane" and s._system.frame_style != "box":
            raise ValueError('offset="pane" needs a box frame')
        lo, hi = float(np.nanmin(s._grid[:, axis])), float(np.nanmax(s._grid[:, axis]))
        if levels is None:
            levels = [
                v for v in s._system.get_axis(axis).get_tick_range() if lo < v < hi
            ]
        elif isinstance(levels, int):
            levels = np.linspace(lo, hi, levels + 2)[1:-1].tolist()
        self.levels = tuple(float(v) for v in cast(Sequence[float], levels))
        self._lines: dict[float, _ContourLine] = {}
        mapping = (
            resolve_colorscale(
                colorscale,
                default_range=(min(self.levels), max(self.levels))
                if len(set(self.levels)) > 1
                else (lo, hi),
            )
            if colorscale is not None
            else s.color_mapping
            if s._color_axis in (axis, zdir)
            else None
        )
        for level in self.levels:
            style = dict(kwargs)
            if "color" not in style and "stroke_color" not in style:
                style["color"] = (
                    ManimColor.from_rgb(mapping(level))
                    if mapping
                    else s._system.x.line.get_color()
                )
            line = _ContourLine(
                _ContourSource(s, level, axis, offset),
                _follow_mapping=(
                    colorscale is None
                    and s._color_axis in (axis, zdir)
                    and "color" not in kwargs
                    and "stroke_color" not in kwargs
                ),
                **style,
            )
            self._lines[level] = line
            self.add(line)

    def at(self, level: float) -> VMobject:
        """Return the curve for one level.

        Parameters
        ----------
        level
            Level value, matched within numerical tolerance.

        Returns
        -------
        VMobject
            The bound curve at the requested level.
        """
        for value, line in self._lines.items():
            if abs(value - level) <= 1e-9:
                return line
        raise KeyError(level)


def _slice_input(name: str, values: tuple[object, ...]) -> tuple[int, object]:
    chosen = [(i, value) for i, value in enumerate(values) if value is not None]
    if len(chosen) != 1:
        raise ValueError(f"{name} requires exactly one coordinate")
    return chosen[0]


def _surface_revision(surface: SurfacePlot) -> str:
    for parameter in surface._parameters.values():
        parameter.poll(parameter.version + 1)
    surface._driver._ensure()
    return repr(
        (
            tuple(p.version for p in surface._parameters.values()),
            surface._system._data_version,
            surface._system.frame.version,
            tuple(surface._u_range) if surface._u_range is not None else None,
            tuple(surface._v_range) if surface._v_range is not None else None,
        )
    )


def _slice_binding(
    surface: SurfacePlot, system: mp.CartesianAxes, axis: int, value: object
) -> _Binding:
    def derive(binding: _Binding) -> None:
        coordinate = binding.number("coordinate")
        low, high = np.nanmin(surface._grid[:, axis]), np.nanmax(surface._grid[:, axis])
        binding.valid = bool(low <= coordinate <= high)
        if not binding.valid and binding.version == 0:
            raise ValueError(f"{'xyz'[axis]} must be inside the surface range")

    return _Binding(
        system,
        derive,
        {"coordinate": value, "surface": lambda: _surface_revision(surface)},
    )


class _SliceArtist(_CurvePlot):
    def _ensure(self) -> None:
        from manim_plots.core import lifecycle as lc

        if self._lifecycle.state is lc.State.ATTACHED and not self._alignment_locked:
            _ensure_binding(self._binding)
            if self._binding_seen != self._binding.version:
                self._dirty = True
                self._native_sample_key = None
        super()._ensure()
        self._binding_seen = self._binding.version

    def _poll(self) -> None:
        self._binding.poll()

    def _needs_sync(self, moving: frozenset[Any]) -> bool:
        return self._binding.needs_sync(moving)

    def _rebuild(self) -> None:
        if not self._binding.valid:
            self._geometry_payload = Payload.empty(
                "path", len(self._binding.system._ranges)
            )
            self._place(self._frame())
            self._dirty = False
            self._data_seen = self._binding.system._data_version
            return
        super()._rebuild()

    _binding: _Binding
    _binding_seen: int


class _SurfaceSlice(_SliceArtist, ParametricPlot):
    def __init__(
        self, surface: SurfacePlot, axis: int, value: object, **style: object
    ) -> None:
        self._binding = _slice_binding(surface, surface._system, axis, value)
        self._binding_seen = -1
        self._binding.ensure()

        def point(t: float) -> FloatArray:
            ranges = (surface._u_range, surface._v_range)
            interval = ranges[1 - axis]
            if interval is None:
                interval = tuple(surface._system.get_axis(1 - axis).range.value)
            other = interval[0] + t * (interval[1] - interval[0])
            uv = np.array([self._binding.number("coordinate"), other])
            if axis == 1:
                uv = uv[::-1]
            return surface._evaluate(uv)

        super().__init__(point, surface._system, t_range=(0, 1), **cast(Any, style))


class _SliceProfile(_SliceArtist, FunctionPlot):
    def __init__(
        self,
        system: mp.CartesianAxes,
        surface: SurfacePlot,
        axis: int,
        value: object,
        **style: object,
    ) -> None:
        self._surface, self._axis = surface, axis
        self._binding = _slice_binding(surface, system, axis, value)
        self._binding_seen = -1
        self._binding.ensure()

        def height(t: float) -> float:
            uv = np.array([self._binding.number("coordinate"), t])
            return float(surface._evaluate(uv if axis == 0 else uv[::-1])[2])

        super().__init__(height, system, self._interval(), **cast(Any, style))

    def _interval(self) -> tuple[float, float]:
        surface = self._surface
        interval = surface._v_range if self._axis == 0 else surface._u_range
        if interval is None:
            interval = tuple(surface._system.get_axis(1 - self._axis).range.value)
        return float(interval[0]), float(interval[1])

    def _rebuild(self) -> None:
        from manim_plots.core.sources import FunctionSource

        source = cast(FunctionSource, self.source)
        self.source = FunctionSource(source.function, self._interval(), dim=2)
        super()._rebuild()


def _plane_trace(
    surface: SurfacePlot, plane: PlanePlot
) -> tuple[FloatArray, FloatArray, tuple[float, float] | None]:
    _ensure_binding(plane._binding)
    p0 = plane._point.copy()
    h = np.cross([0, 0, 1], plane._normal)
    length = np.linalg.norm(h)
    if length == 0:
        raise ValueError("plane must not be horizontal")
    h /= length
    lower, upper = -np.inf, np.inf
    for i, interval in enumerate((surface._u_range, surface._v_range)):
        lo, hi = sorted(
            interval
            if interval is not None
            else surface._system.get_axis(i).range.value
        )
        if abs(h[i]) < 1e-15:
            if not lo <= p0[i] <= hi:
                return p0, h, None
        else:
            a, b = sorted(((lo - p0[i]) / h[i], (hi - p0[i]) / h[i]))
            lower, upper = max(lower, a), min(upper, b)
    return p0, h, (float(lower), float(upper)) if lower < upper else None


def _plane_profile(
    system: mp.CartesianAxes, surface: SurfacePlot, plane: object, **style: object
) -> FunctionPlot:
    if not isinstance(plane, PlanePlot):
        raise TypeError("plane must be a PlanePlot")
    if plane._input_name in ("x", "y"):
        axis = "xy".index(plane._input_name)
        parameter = plane._binding.parameters[f"point{axis}"]
        return _SliceProfile(
            system,
            surface,
            axis,
            parameter.tracker if parameter.tracker is not None else parameter.value,
            **style,
        )
    return _PlaneProfile(system, surface, plane, **style)


class _PlaneProfile(_SliceArtist, FunctionPlot):
    def __init__(
        self,
        system: mp.CartesianAxes,
        surface: SurfacePlot,
        plane: PlanePlot,
        **style: object,
    ) -> None:
        def revision() -> str:
            _ensure_binding(plane._binding)
            return repr((plane._binding.version, _surface_revision(surface)))

        def derive(binding: _Binding) -> None:
            self._p0, self._h, interval = _plane_trace(surface, plane)
            binding.valid = interval is not None
            if interval is None and binding.version == 0:
                raise ValueError("plane trace misses the surface domain")
            self._interval = (0.0, 1.0) if interval is None else interval

        self._binding = _Binding(system, derive, {"dependency": revision})
        self._binding_seen = -1
        self._binding.ensure()

        def height(s: float) -> float:
            return float(surface._evaluate((self._p0 + s * self._h)[:2])[2])

        super().__init__(height, system, self._interval, **cast(Any, style))

    def _rebuild(self) -> None:
        from manim_plots.core.sources import FunctionSource

        source = cast(FunctionSource, self.source)
        self.source = FunctionSource(source.function, self._interval, dim=2)
        super()._rebuild()


from manim_plots.animations.surfaces import GrowSurface as GrowSurface  # noqa: E402
