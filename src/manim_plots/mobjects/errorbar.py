"""Error bars with data-space segments and scene-space caps."""

from __future__ import annotations

import copy
from numbers import Integral, Real
from typing import Any, Self, Unpack, cast

import numpy as np
from manim import Mobject, VGroup, VMobject
from manim.animation.transform import _MethodAnimation
from manim.typing import PathFuncType
from manim.utils.color import ParsableManimColor
from numpy.typing import ArrayLike

import manim_plots as mp
from manim_plots.core import BoolArray, FloatArray
from manim_plots.core.payload import Payload
from manim_plots.core.shape import clip as clip_path
from manim_plots.core.shape import corners
from manim_plots.core.sources import ArraySource, Source, _numeric
from manim_plots.mobjects.artists import (
    LinePlot,
    Marker,
    ScatterPlot,
    _clip_axes,
    _clip_box,
    _CurvePlot,
    _cycle_style,
    _MarkerLeaf,
    _resolve_coordinates,
    _SampleWarnings,
    _unclipped_box,
    _validate_clip,
    _validate_label,
)
from manim_plots.mobjects.context import animation_context
from manim_plots.mobjects.leaves import (
    _STRAIGHT,
    _ClipInput,
    _ClipValue,
    _VMStyle,
)


def _errors(value: ArrayLike | None, n: int, name: str) -> FloatArray | None:
    if value is None:
        return None
    array = _numeric(value, name)
    if array.shape == ():
        if array < 0:
            raise ValueError(f"{name}[0] must be nonnegative")
        array = np.full((2, n), float(array))
    elif array.shape == (n,):
        array = np.broadcast_to(array, (2, n)).copy()
    elif array.shape == (2, n):
        array = array.copy()
    else:
        raise ValueError(f"{name} must be scalar or have shape ({n},) or (2, {n})")
    if np.any(array < 0):
        index = tuple(int(i) for i in np.argwhere(array < 0)[0])
        raise ValueError(f"{name}{index} must be nonnegative")
    array.flags.writeable = False
    return array


def _size(value: float, name: str) -> float:
    if not isinstance(value, Real) or isinstance(value, bool):
        raise TypeError(f"{name} must be a real number")
    if not np.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return float(value)


def _every(value: int | tuple[int, int]) -> tuple[int, int]:
    pair = value if isinstance(value, tuple) else (0, value)
    if len(pair) != 2:
        raise ValueError("errorevery must contain start and step")
    if any(not isinstance(v, Integral) or isinstance(v, bool) for v in pair):
        raise TypeError("errorevery must contain integers")
    start, step = pair
    if start < 0 or step <= 0:
        raise ValueError("errorevery requires start >= 0 and step > 0")
    return int(start), int(step)


class _ErrorWarnings(_SampleWarnings):
    def __init__(self, source: ArraySource) -> None:
        super().__init__()
        self.source = source
        self.version = 0

    def warn(
        self,
        system: mp.CartesianAxes,
        source: Source,
        message: str,
        versions: tuple[int, ...] = (),
    ) -> None:
        # All parts report one data change, even when they use separate sources.
        super().warn(system, self.source, message, (self.version,))


class _ErrorPart(_CurvePlot):
    def __init__(self, owner: ErrorBars, axis: int, caps: bool) -> None:
        self._owner, self._axis, self._caps = owner, axis, caps
        self._error_seen = -1
        self._view_seen: object = None
        assert owner._system is not None
        super().__init__(
            owner.source,
            owner._system,
            use_smoothing=False,
            clip=owner._clip,
            color=owner._ecolor,
            stroke_width=owner._capthick if caps else owner._elinewidth,
        )
        if caps and len(owner._system._ranges) == 3:
            cast(Any, owner._system)._register_field_view(self)

    def _turn(self) -> None:
        self._dirty = True
        self._ensure()

    def _ensure(self) -> None:
        if self._error_seen != self._owner._version or (
            self._caps
            and self._system is not None
            and self._frame_seen != self._system.frame.version
        ):
            self._dirty = True
        super()._ensure()

    def get_subpaths(self) -> list[FloatArray]:
        """Return separate bar or cap paths, including coincident endpoints."""
        points = self.points
        if self._alignment_locked:
            return super().get_subpaths()
        return [points[start:stop] for start, stop in self._render_segments]

    def _rebuild(self, *, cap_progress: FloatArray | None = None) -> None:
        system = self._system
        if system is None:
            return
        system._sync_data()
        frame = self._frame()
        ends, cap_mask = self._owner._endpoints(self._axis)
        dim = len(system._ranges)
        if self._caps:
            if self._owner.capsize == 0:
                ends = np.empty((0, 2, dim))
            elif dim == 3:
                from manim_plots.mobjects.fields import _facing_basis

                centers = ends.reshape(-1, dim)[cap_mask.ravel()]
                probes = centers.copy()
                probes[:, self._axis] += 1
                placed = frame.forward(centers)
                tangent = frame.forward(probes) - placed
                tangent /= np.maximum(np.linalg.norm(tangent, axis=1)[:, None], 1e-12)
                direction, _ = _facing_basis(system, tangent, None)
                half = direction * self._owner.capsize / 2
                ends = frame.inverse(
                    np.stack((placed - half, placed + half), axis=1).reshape(-1, 3)
                ).reshape(-1, 2, 3)
            else:
                centers = ends.reshape(-1, 2)[cap_mask.ravel()]
                probes = np.repeat(centers[:, None, :], 3, axis=1)
                probes[:, 1, 0] += 1
                probes[:, 2, 1] += 1
                placed = frame.forward(probes.reshape(-1, 2)).reshape(-1, 3, 3)
                dx, dy = placed[:, 1] - placed[:, 0], placed[:, 2] - placed[:, 0]
                normal = np.cross(dx, dy)
                tangent = dx if self._axis == 0 else dy
                direction = np.cross(tangent, normal)
                norm = np.linalg.norm(direction, axis=1)
                usable = np.isfinite(norm) & (norm > 0)
                half = (
                    direction[usable] / norm[usable, None] * (self._owner.capsize / 2)
                )
                if cap_progress is not None:
                    widths = np.repeat(cap_progress[self._owner._indices()], 2)
                    half *= widths[cap_mask.ravel()][usable, None]
                centers3 = placed[usable, 0]
                scene_ends = np.stack((centers3 - half, centers3 + half), axis=1)
                ends = frame.inverse(scene_ends.reshape(-1, 3)).reshape(-1, 2, 3)
        bounds = _clip_box(system, self._clip)
        points = ends.reshape(-1, ends.shape[-1])
        edges = np.arange(0, len(points), 2, dtype=np.intp)
        payload = corners(
            Payload._trusted("path", points, np.column_stack((edges, edges + 2))),
            bounds,
        )
        axes = _clip_axes(self._clip, dim)
        if any(axis is not False for axis in axes):
            if any(axis is False for axis in axes):
                bounds = _unclipped_box(bounds, axes, payload.coords)
            payload = clip_path(payload, bounds)
        self._geometry_payload = payload
        self._place(frame)
        self._data_seen = system._data_version
        self._error_seen = self._owner._version
        self._dirty = False


class ErrorBars(VGroup):
    """Group independently styleable markers, a line, bars and caps.

    Parameters
    ----------
    x, y
        Separate one-dimensional coordinates, or pairs in x with y omitted.
    system
        Coordinate system supplying scales, clipping and placement.
    yerr, xerr
        Nonnegative scalar, n errors, or (2, n) lower and upper errors.
    marker
        Marker enum or native template; None omits markers.
    line
        Draw a connecting line when true.
    ecolor, elinewidth, capthick
        Bar colour, bar width (default 2), and cap width (default bar width).
    capsize
        Full cap length in scene units, independent of axis zoom.
    barsabove
        Place bars after markers in family order when true.
    errorevery
        Draw every kth error, or (start, k).
    label
        One legend entry for the complete artist.
    clip
        Boolean, scene-unit margin, or independent (x, y) policies.
    **style
        Native styles applied to the markers and connecting line.

    Attributes
    ----------
    markers, line
        ScatterPlot and LinePlot, or None when omitted.
    ybars, xbars, ycaps, xcaps
        One leaf per segment family, or None when that error is absent.

    Notes
    -----
    Data changes preserve existing parts and their styles. Animated changes
    require equal point counts and interpolate points and errors by index.
    An error family added or removed during an animation grows from or shrinks
    to zero; it is omitted once the animation ends with no errors of that kind.
    """

    def __init__(
        self,
        x: object,
        system: mp.CartesianAxes,
        y: object = None,
        yerr: ArrayLike | None = None,
        xerr: ArrayLike | None = None,
        *,
        zerr: ArrayLike | None = None,
        marker: Mobject | Marker | None = Marker.DOT,
        line: bool = False,
        ecolor: ParsableManimColor | None = None,
        elinewidth: float | None = None,
        capsize: float = 0.1,
        capthick: float | None = None,
        barsabove: bool = False,
        errorevery: int | tuple[int, int] = 1,
        label: str | None = None,
        clip: _ClipInput = True,
        **style: Unpack[_VMStyle],
    ) -> None:
        self._dim = len(system._ranges)
        x, y = _resolve_coordinates(system, x, y)
        source = ArraySource(x, y, kind="points", dim=self._dim)
        errors: tuple[FloatArray | None, ...] = (
            _errors(xerr, len(source.data), "xerr"),
            _errors(yerr, len(source.data), "yerr"),
        )
        if self._dim == 3:
            errors += (_errors(zerr, len(source.data), "zerr"),)
        _validate_label(label)
        self._clip = _validate_clip(clip, self._dim)
        _clip_box(system, self._clip)
        if marker is not None and not isinstance(marker, (Mobject, Marker)):
            raise TypeError("marker must be a Marker, Mobject or None")
        if not isinstance(line, bool):
            raise TypeError("line must be bool")
        if not isinstance(barsabove, bool):
            raise TypeError("barsabove must be bool")
        self.capsize = _size(capsize, "capsize")
        self._elinewidth = (
            2.0 if elinewidth is None else _size(elinewidth, "elinewidth")
        )
        self._capthick = (
            self._elinewidth if capthick is None else _size(capthick, "capthick")
        )
        self._every = _every(errorevery)
        self._system: mp.CartesianAxes | None = system
        self.source, self._errors = source, errors
        self._label, self._barsabove = label, barsabove
        self._version = 0
        self._data_animation = False
        self._channel_errors = errors
        self._sample_warnings = _ErrorWarnings(source)
        _cycle_style(system, style, scatter=True)
        seed = self._seed_data()
        self.markers = (
            None
            if marker is None
            else ScatterPlot(seed, system, marker=marker, clip=clip, **style)
        )
        line_style = style.copy()
        if "color" not in line_style and "stroke_color" not in line_style:
            line_style["color"] = (
                self.markers.get_color()
                if self.markers is not None
                else style.get("fill_color") or "#FFFFFF"
            )
        self.line = LinePlot(seed, system, clip=clip, **line_style) if line else None
        self._ecolor = (
            ecolor
            if ecolor is not None
            else (
                self.markers[0].get_color()
                if self.markers is not None and len(source.data)
                else self.line.get_color()
                if self.line is not None
                else style.get("color", style.get("stroke_color", "#FFFFFF"))
                or "#FFFFFF"
            )
        )
        self.xbars: _ErrorPart | None = None
        self.ybars: _ErrorPart | None = None
        self.xcaps: _ErrorPart | None = None
        self.ycaps: _ErrorPart | None = None
        self.zbars: _ErrorPart | None = None
        self.zcaps: _ErrorPart | None = None
        super().__init__()
        self._poll()
        self._update_parts()

    def _seed_data(self) -> FloatArray:
        assert self._system is not None
        # Install the shared warning sink before exposing invalid input to parts.
        center = [np.mean(axis.range.value) for axis in self._system._ranges]
        return np.tile(center, (max(1, len(self.source.data)), 1))

    def _poll(self) -> None:
        system = self._system
        if system is not None and (
            not len(self.source.data)
            or not system._data.valid(self.source.data).all()
            or any(e is not None and not np.isfinite(e).all() for e in self._errors)
        ):
            self._sample_warnings.warn(
                system,
                self.source,
                "errorbar contains invalid samples; bars are hidden",
            )

    def _indices(self) -> np.ndarray[Any, np.dtype[np.intp]]:
        system = self._system
        assert system is not None
        data = self.source.data
        start, step = self._every
        indices = np.arange(start, len(data), step)
        valid = system._data.valid(data[indices])
        for errors in self._errors:
            if errors is not None:
                valid &= np.isfinite(errors[:, indices]).all(axis=0)
        return indices[valid]

    def _endpoints(self, axis: int) -> tuple[FloatArray, BoolArray]:
        system = self._system
        assert system is not None
        error = self._errors[axis]
        if error is None:
            return np.empty((0, 2, self._dim)), np.empty((0, 2), dtype=bool)
        data = self.source.data
        indices = self._indices()
        ends = np.repeat(data[indices, None, :], 2, axis=1)
        with np.errstate(over="ignore", invalid="ignore"):
            ends[:, 0, axis] -= error[0, indices]
            ends[:, 1, axis] += error[1, indices]
        component = system._ranges[axis]
        cap_mask = np.isfinite(component._scale.forward(ends[:, :, axis]))
        if not cap_mask.all():
            lo, hi = sorted(component.range.value)
            ends[:, :, axis] = np.where(
                cap_mask, ends[:, :, axis], np.clip(ends[:, :, axis], lo, hi)
            )
        local = system._data.forward(ends.reshape(-1, self._dim)).reshape(
            -1, 2, self._dim
        )
        finite = np.isfinite(local).all(axis=(1, 2))
        return local[finite], cap_mask[finite]

    def _update_parts(self) -> None:
        system = self._system
        if system is None:
            return
        for axis, prefix in enumerate("xyz"[: self._dim]):
            for caps, suffix in ((False, "bars"), (True, "caps")):
                name = prefix + suffix
                part = getattr(self, name)
                if self._errors[axis] is None and not self._data_animation:
                    setattr(self, name, None)
                elif part is None and self._errors[axis] is not None:
                    setattr(self, name, _ErrorPart(self, axis, caps))
                elif part is not None:
                    part._dirty = True
                    part._rebuild()
        if self.markers is not None:
            markers = self.markers
            count = len(self.source.data)
            if len(markers.submobjects) < count:
                extra = ScatterPlot(
                    self._seed_data(),
                    system,
                    marker=markers._marker_template,
                    clip=self._clip,
                    **markers.get_style(),
                )
                markers.submobjects.extend(
                    extra.submobjects[len(markers.submobjects) :]
                )
            del markers.submobjects[count:]
            markers.source = self.source
            markers._sample_warnings = self._sample_warnings
            markers._validity_seen = -1
            for member in markers.get_family():
                if isinstance(member, _MarkerLeaf):
                    member.source = self.source
                    member._sample_warnings = self._sample_warnings
                    member._dirty = True
                    member._rebuild()
        if self.line is not None:
            self.line.source = ArraySource(self.source.data, dim=self._dim)
            self.line._sample_warnings = self._sample_warnings
            self.line._source_invalid = not np.isfinite(self.source.data).all()
            self.line._dirty = True
            self.line._rebuild()
        bars: list[VMobject | None] = [self.ybars, self.xbars, self.ycaps, self.xcaps]
        if self._dim == 3:
            bars += [self.zbars, self.zcaps]
        foreground: list[VMobject | None] = [self.line, self.markers]
        parts = foreground + bars if self._barsabove else bars + foreground
        self.submobjects = [part for part in parts if part is not None]

    def set_data(
        self,
        x: object,
        y: object = None,
        *coordinates: ArrayLike,
        yerr: ArrayLike | None = None,
        xerr: ArrayLike | None = None,
        zerr: ArrayLike | None = None,
    ) -> Self:
        """Replace immutable coordinates and errors, preserving existing styles.

        Parameters
        ----------
        x, y
            Separate coordinates, or pairs with y omitted.
        *coordinates
            Third coordinate in 3D, followed by positional error arrays.
        yerr, xerr, zerr
            Scalar, n values, (2, n) lower/upper values, or None to omit bars.

        Returns
        -------
        Self
            This artist with all parts re-derived.
        """
        if self._dim == 3 and y is not None:
            if not coordinates:
                raise ValueError("z coordinates are required")
            x = np.column_stack(
                (cast(ArrayLike, x), cast(ArrayLike, y), coordinates[0])
            )
            y = None
            coordinates = coordinates[1:]
            if coordinates:
                zerr = coordinates[0]
                coordinates = coordinates[1:]
        if coordinates:
            yerr = coordinates[0]
        if len(coordinates) > 1:
            xerr = coordinates[1]
        if len(coordinates) > 2:
            raise TypeError("too many error arrays")
        if self._system is not None:
            x, y = _resolve_coordinates(self._system, x, y)
        source = ArraySource(
            cast(ArrayLike, x), cast(ArrayLike | None, y), kind="points", dim=self._dim
        )
        errors: tuple[FloatArray | None, ...] = (
            _errors(xerr, len(source.data), "xerr"),
            _errors(yerr, len(source.data), "yerr"),
        )
        if self._dim == 3:
            errors += (_errors(zerr, len(source.data), "zerr"),)
        if self._data_animation:
            expanded = [
                _errors(0, len(source.data), "error")
                if new is None and old is not None
                else new
                for old, new in zip(self._errors, errors, strict=True)
            ]
            errors = tuple(expanded)
        self.source, self._errors = source, errors
        self._version += 1
        self._sample_warnings.version = self._version
        self._poll()
        self._update_parts()
        return self

    def set_label(self, label: str | None) -> Self:
        """Set the legend label.

        Parameters
        ----------
        label
            Entry text, or None to omit this artist.
        """
        _validate_label(label)
        self._label = label
        return self

    def get_label(self) -> str | None:
        """Return the legend label, or None when unset."""
        return self._label

    def set_clip(self, value: _ClipInput) -> Self:
        """Set clipping independently for each axis on every part.

        Parameters
        ----------
        value
            Boolean, finite scene-unit margin, or an (x, y) pair of policies.
        """
        clip = _validate_clip(value, self._dim)
        if self._system is not None:
            _clip_box(self._system, clip)
        self._clip = clip
        for part in self.submobjects:
            if isinstance(part, (_CurvePlot, ScatterPlot)):
                part.set_clip(clip)
        return self

    def get_clip(self) -> _ClipValue:
        """Return the supplied clipping policy, with pairs stored as tuples."""
        return self._clip

    def align_data(self, mobject: Mobject, skip_point_alignment: bool = False) -> Self:
        """Prepare an indexed data channel for native method animations.

        Parameters
        ----------
        mobject, skip_point_alignment
            Native target and point alignment option.
        """
        animation = animation_context(transform_only=True)
        if (
            isinstance(animation, _MethodAnimation)
            and isinstance(mobject, ErrorBars)
            and self._version != mobject._version
        ):
            if len(self.source.data) != len(mobject.source.data):
                raise ValueError("set_data animation requires the same point count")
            self._data_animation = mobject._data_animation = True
            for artist in (self, mobject):
                artist._channel_errors = artist._errors
            for axis in range(self._dim):
                if (self._errors[axis] is None) != (mobject._errors[axis] is None):
                    for artist in (self, mobject):
                        if artist._errors[axis] is None:
                            errors = list(artist._errors)
                            errors[axis] = _errors(0, len(self.source.data), "error")
                            artist._errors = tuple(errors)
                            artist._update_parts()
        return super().align_data(mobject, skip_point_alignment)

    def family_members_with_points(self) -> list[Mobject]:
        """Run the group's data channel after native child interpolation."""
        if self._data_animation:
            # Clipping may empty a part mid-play; keep the indexed family stable.
            family = [
                part
                for part in self.get_family()
                if isinstance(part, _CurvePlot) or part.has_points()
            ]
            return [*family, self]
        return super().family_members_with_points()

    def interpolate(
        self,
        mobject1: Mobject,
        mobject2: Mobject,
        alpha: float,
        path_func: PathFuncType = _STRAIGHT,
    ) -> Self:
        """Interpolate coordinates and errors by their original point indices.

        Parameters
        ----------
        mobject1, mobject2, alpha, path_func
            Native endpoints, progress and geometric interpolation path.
        """
        if self._data_animation:
            assert isinstance(mobject1, ErrorBars) and isinstance(mobject2, ErrorBars)
            data = (1 - alpha) * mobject1.source.data + alpha * mobject2.source.data
            errors: list[FloatArray | None] = []
            for a, b in zip(mobject1._errors, mobject2._errors, strict=True):
                errors.append(
                    None if a is None or b is None else (1 - alpha) * a + alpha * b
                )
            self.set_data(
                data,
                xerr=errors[0],
                yerr=errors[1],
                zerr=errors[2] if self._dim == 3 else None,
            )
            return self
        return super().interpolate(mobject1, mobject2, alpha, path_func)

    def resume_updating(self, recursive: bool = True) -> Self:
        """Return all derived parts to their ordinary attached lifecycle.

        Parameters
        ----------
        recursive
            Resume the native family when true.
        """
        active = self._data_animation
        animation = animation_context(finishing=True)
        super().resume_updating(recursive)
        if active:
            self._data_animation = False
            if animation is not None:
                start = animation.starting_mobject
                target = getattr(animation, "target_copy", None)
                if isinstance(start, ErrorBars) and isinstance(target, ErrorBars):
                    alpha = animation.rate_func(1)
                    if alpha == 0 or alpha == 1:
                        endpoint = start if alpha == 0 else target
                        self._errors = endpoint._channel_errors
            self._update_parts()
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        result = type(self).__new__(type(self))
        memo[id(self)] = result
        for key, value in self.__dict__.items():
            if key == "_system":
                result.__dict__[key] = memo.get(id(value), value)
            elif key in {"source", "_errors"}:
                result.__dict__[key] = value
            else:
                result.__dict__[key] = copy.deepcopy(value, memo)
        return result
