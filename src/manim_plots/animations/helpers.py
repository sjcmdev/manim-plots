"""Temporary data-space reveals for bound two-dimensional helpers."""

from __future__ import annotations

import copy
from collections.abc import Callable
from copy import deepcopy
from typing import Any, cast

import numpy as np
from manim import (
    Animation,
    AnimationGroup,
    Create,
    FadeIn,
    FadeOut,
    Mobject,
    Scene,
    Uncreate,
    Unwrite,
    VGroup,
    VMobject,
    Write,
    linear,
)

from manim_plots.core import FloatArray
from manim_plots.core.params import Parameter
from manim_plots.mobjects.errorbar import ErrorBars
from manim_plots.mobjects.helpers import (
    FilledRegion,
    HelperLine,
    _Binding,
    _RegionBinding,
    _RiemannGroup,
)

from ._base import MappedPresentation, Presentation, flags, window


class ExtendReference(MappedPresentation):
    """Extend a reference or drop line from a selected endpoint.

    Parameters
    ----------
    line
        Bound reference or drop line.
    origin
        Start, end or center of the visible interval.
    reverse, remover, **kwargs
        Playback direction, scene removal and native animation options.
    """

    def __init__(
        self,
        line: HelperLine,
        *,
        origin: str = "start",
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        if origin not in ("start", "end", "center"):
            raise ValueError("unknown origin")
        if not isinstance(line, HelperLine):
            raise TypeError("line must be a bound helper line")
        self.line, self.origin, self.reverse = line, origin, reverse
        flags(reverse, remover, kwargs)
        super().__init__(line, **cast(dict[str, Any], kwargs))

    def interpolate_mobject(self, alpha: float) -> None:
        """Derive the visible interval using the current mapping."""
        self._alpha = alpha
        line = self.line
        binding = line._binding
        binding.ensure()
        original = binding.parts[line._part]
        p = self.rate_func(1 - alpha if self.reverse else alpha)
        system = binding.system
        data = system._data.inverse(original)
        anchor = (
            data[0]
            if self.origin == "start"
            else (data[-1] if self.origin == "end" else (data[0] + data[-1]) / 2)
        )
        try:
            binding.parts[line._part] = system._data.forward(
                anchor + p * (data - anchor)
            )
            line._rebuild()
        finally:
            binding.parts[line._part] = original

    def restore(self) -> None:
        """Release the temporary hook and restore bound geometry."""
        super().restore()
        self.line._rebuild()


class GrowRegion(MappedPresentation):
    """Grow a filled region from its retained paired boundary.

    Parameters
    ----------
    region, axis
        Bound region and growth axis; None infers the dependent coordinate.
    reverse, remover, **kwargs
        Playback direction, scene removal and native animation options.
    """

    def __init__(
        self,
        region: FilledRegion,
        *,
        axis: str | None = None,
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        if axis not in (None, "x", "y"):
            raise ValueError("axis must be x or y")
        if not isinstance(region, FilledRegion):
            raise TypeError("region must have paired boundaries")
        self.region, self.reverse = region, reverse
        self.axis = (
            (0 if region._binding.transpose else 1)
            if axis is None
            else (0 if axis == "x" else 1)
        )
        flags(reverse, remover, kwargs)
        super().__init__(region, **cast(dict[str, Any], kwargs))

    def interpolate_mobject(self, alpha: float) -> None:
        """Interpolate the first boundary in data coordinates."""
        self._alpha = alpha
        p = self.rate_func(1 - alpha if self.reverse else alpha)
        self.region._rebuild(growth=(self.axis, p))

    def restore(self) -> None:
        """Restore the complete paired region."""
        super().restore()
        self.region._rebuild()


class SweepRegion(GrowRegion):
    """Reveal a region behind a closed data-space frontier.

    Parameters
    ----------
    region, axis, direction
        Bound region, sweep coordinate and direction (1 or -1).
    reverse, remover, **kwargs
        Playback direction, scene removal and native animation options.
    """

    def __init__(
        self,
        region: FilledRegion,
        *,
        axis: str = "x",
        direction: int = 1,
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        if direction not in (-1, 1):
            raise ValueError("direction must be 1 or -1")
        if axis not in ("x", "y"):
            raise ValueError("axis must be x or y")
        self.direction = direction
        super().__init__(
            region,
            axis=axis,
            reverse=reverse,
            remover=remover,
            **cast(dict[str, Any], kwargs),
        )

    def interpolate_mobject(self, alpha: float) -> None:
        """Clip both boundaries at the current frontier."""
        self._alpha = alpha
        p = self.rate_func(1 - alpha if self.reverse else alpha)
        self.region._rebuild(sweep=(self.axis, p, self.direction))


class SweepSpan(SweepRegion):
    """Sweep a span along its data interval, retaining viewport fractions.

    Parameters
    ----------
    span, direction
        Bound span and direction (1 or -1).
    reverse, remover, **kwargs
        Playback direction, scene removal and native animation options.
    """

    def __init__(
        self,
        span: FilledRegion,
        *,
        direction: int = 1,
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        if not isinstance(span, FilledRegion):
            raise TypeError("span must be a bound filled region")
        super().__init__(
            span,
            axis="y" if span._binding.transpose else "x",
            direction=direction,
            reverse=reverse,
            remover=remover,
            **cast(dict[str, Any], kwargs),
        )


class GrowRiemann(MappedPresentation):
    """Grow signed Riemann rectangles in their retained interval order.

    Parameters
    ----------
    rectangles, lag_ratio
        Bound rectangles and stagger between their equal windows.
    reverse, remover, **kwargs
        Playback direction, scene removal and native animation options.
    """

    def __init__(
        self,
        rectangles: VGroup,
        *,
        lag_ratio: float = 0.05,
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        if not isinstance(rectangles, _RiemannGroup):
            raise TypeError("rectangles must be bound Riemann rectangles")
        self.rectangles, self.reverse = rectangles, reverse
        flags(reverse, remover, kwargs)
        super().__init__(
            rectangles, lag_ratio=lag_ratio, **cast(dict[str, Any], kwargs)
        )

    def interpolate_mobject(self, alpha: float) -> None:
        """Apply signed heights with one driver for all rectangles."""
        self._alpha = alpha
        if self.reverse:
            alpha = 1 - alpha
        for i, rect in enumerate(self.rectangles):
            p = self.rate_func(window(alpha, i, len(self.rectangles), self.lag_ratio))
            cast(FilledRegion, rect)._rebuild(growth=(1, p))

    def restore(self) -> None:
        """Restore every rectangle without repartitioning."""
        super().restore()
        for rect in self.rectangles:
            cast(FilledRegion, rect)._rebuild()


class GrowErrorBars(MappedPresentation):
    """Grow errors from their samples, finishing with scene-sized caps.

    Parameters
    ----------
    errors, lag_ratio, cap_lag
        Bound errors, sample stagger and final window fraction for caps.
    reverse, remover, **kwargs
        Playback direction, scene removal and native animation options.
    """

    def __init__(
        self,
        errors: ErrorBars,
        *,
        lag_ratio: float = 0.05,
        cap_lag: float = 0.15,
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        if not isinstance(errors, ErrorBars):
            raise TypeError("errors must be ErrorBars")
        if not np.isfinite(cap_lag) or not 0 <= cap_lag <= 1:
            raise ValueError("cap_lag must be between zero and one")
        self.errors, self.cap_lag, self.reverse = errors, cap_lag, reverse
        flags(reverse, remover, kwargs)
        super().__init__(errors, lag_ratio=lag_ratio, **cast(dict[str, Any], kwargs))

    def begin(self) -> None:
        """Capture independently customised marker styles."""
        self._marker_styles = [
            [
                (leaf, leaf.copy())
                for leaf in marker.get_family()
                if isinstance(leaf, VMobject)
            ]
            for marker in (self.errors.markers or [])
        ]
        super().begin()

    def interpolate_mobject(self, alpha: float) -> None:
        """Drive all errors and optional foreground parts in source order."""
        self._alpha = alpha
        if self.reverse:
            alpha = 1 - alpha
        errors = self.errors
        count = len(errors.source.data)
        progress = np.array(
            [
                self.rate_func(window(alpha, i, count, self.lag_ratio))
                for i in range(count)
            ]
        )
        caps = (
            np.clip((progress - (1 - self.cap_lag)) / self.cap_lag, 0, 1)
            if self.cap_lag
            else (progress > 0).astype(float)
        )
        original = errors._errors
        try:
            errors._errors = tuple(
                None if e is None else e * progress for e in original
            )
            for part in (errors.xbars, errors.ybars, errors.xcaps, errors.ycaps):
                if part is not None:
                    part._rebuild(cap_progress=caps)
        finally:
            errors._errors = original
        for p, styles in zip(progress, self._marker_styles, strict=False):
            for leaf, old in styles:
                leaf.set_fill(opacity=float(old.get_fill_opacity()) * p, family=False)
                leaf.set_stroke(
                    opacity=float(old.get_stroke_opacity()) * p, family=False
                )
        if errors.line is not None:
            errors.line._rebuild()
            full = VMobject().set_points(errors.line._cache.copy())
            errors.line.pointwise_become_partial(full, 0, self.rate_func(alpha))

    def restore(self) -> None:
        """Restore canonical errors, cap widths and foreground styles."""
        super().restore()
        for part in (
            self.errors.xbars,
            self.errors.ybars,
            self.errors.xcaps,
            self.errors.ycaps,
            self.errors.line,
        ):
            if part is not None:
                part._rebuild()
        for styles in self._marker_styles:
            for leaf, old in styles:
                leaf.match_style(old, family=False)


class _Composition(AnimationGroup, Presentation):
    _canonical: list[tuple[VMobject, FloatArray, dict[str, Any]]]

    def _setup_scene(self, scene: Scene) -> None:
        Animation._setup_scene(self, scene)

    def begin(self) -> None:
        self._canonical = [
            (
                cast(VMobject, leaf),
                leaf.points.copy(),
                deepcopy(cast(VMobject, leaf).get_style()),
            )
            for leaf in self.mobject.get_family()
            if isinstance(leaf, VMobject)
        ]
        for leaf, _, _ in self._canonical:
            for name in ("fill_rgbas", "stroke_rgbas", "background_stroke_rgbas"):
                setattr(leaf, name, getattr(leaf, name).copy())
        super().begin()

    def restore(self) -> None:
        for leaf, points, style in self._canonical:
            leaf.set_points(points.copy())
            leaf.set_style(**style, family=False)

    def finish(self) -> None:
        super().finish()
        self.restore()

    def clean_up_from_scene(self, scene: Scene) -> None:
        # Children own temporary groups; only the public target owns scene membership.
        Animation.clean_up_from_scene(self, scene)
        self.restore()


class _LiveOpacity:
    """Native fades with style-only interpolation for replaceable live glyphs."""

    def begin(self: Any) -> None:
        self._styles = {
            leaf: deepcopy(leaf.get_style())
            for leaf in self.mobject.get_family()
            if isinstance(leaf, VMobject)
        }
        Animation.begin(self)

    def create_starting_mobject(self: Any) -> Mobject:
        return Mobject()

    def get_all_mobjects(self: Any) -> list[Mobject]:
        return [self.mobject]

    def interpolate_mobject(self: Any, alpha: float) -> None:
        p = self.rate_func(alpha)
        if isinstance(self, FadeOut):
            p = 1 - p

        def apply(mob: Mobject, inherited: dict[str, Any]) -> None:
            style = self._styles.get(mob, inherited)
            if isinstance(mob, VMobject):
                mob.set_style(**deepcopy(style), family=False)
                mob.set_fill(
                    opacity=np.asarray(style["fill_opacity"]) * p, family=False
                )
                mob.set_stroke(
                    opacity=np.asarray(style["stroke_opacity"]) * p, family=False
                )
                mob.set_stroke(
                    opacity=np.asarray(style["background_stroke_opacity"]) * p,
                    background=True,
                    family=False,
                )
            for child in mob.submobjects:
                apply(child, style)

        apply(self.mobject, self._styles[self.mobject])


class _LiveFadeIn(_LiveOpacity, FadeIn):
    pass


class _LiveFadeOut(_LiveOpacity, FadeOut):
    pass


class RevealAnnotation(_Composition):
    """Draw an annotation arrow and write its original text in two stages.

    Parameters
    ----------
    annotation, text_first, lag_ratio
        Bound annotation, stage order and overlap.
    reverse, remover, **kwargs
        Playback direction, scene removal and native animation options.
    """

    def __init__(
        self,
        annotation: VGroup,
        *,
        text_first: bool = False,
        lag_ratio: float = 0.3,
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        text = cast(Any, annotation).text
        arrow = cast(Any, annotation).arrow
        rate = cast(Callable[[float], float], kwargs.pop("rate_func", linear))
        children: list[Animation] = [
            (Unwrite if reverse else Write)(text, run_time=1, rate_func=rate)
        ]
        if arrow is not None:
            children.insert(
                1 if text_first else 0,
                (Uncreate if reverse else Create)(arrow, run_time=1, rate_func=rate),
            )
        if reverse:
            children.reverse()
        flags(reverse, remover, kwargs)
        super().__init__(
            *children,
            group=annotation,
            lag_ratio=lag_ratio,
            **cast(dict[str, Any], kwargs),
        )


class _IntersectionLines(MappedPresentation):
    def __init__(self, crosshair: VGroup, *, reverse: bool, **kwargs: object) -> None:
        self.crosshair, self.reverse = cast(Any, crosshair), reverse
        super().__init__(
            VGroup(self.crosshair.vline, self.crosshair.hline),
            **cast(dict[str, Any], kwargs),
        )

    def interpolate_mobject(self, alpha: float) -> None:
        self._alpha = alpha
        p = self.rate_func(1 - alpha if self.reverse else alpha)
        cross = self.crosshair
        for line in (cross.vline, cross.hline):
            binding = line._binding
            binding.ensure()
            original = binding.parts[line._part]
            system = binding.system
            center = system.p2c(cross.dot.get_center())[:2]
            data = system._data.inverse(original)
            index = 0 if line is cross.vline else 1
            data[:, index] = center[index]
            try:
                binding.parts[line._part] = system._data.forward(
                    center + p * (data - center)
                )
                line._rebuild()
            finally:
                binding.parts[line._part] = original

    def restore(self) -> None:
        super().restore()
        for line in (self.crosshair.vline, self.crosshair.hline):
            line._rebuild()


class RevealCrosshair(_Composition):
    """Reveal the live intersection, outward lines and optional readout.

    Parameters
    ----------
    crosshair, lag_ratio
        Bound crosshair and overlap of its three stages.
    reverse, remover, **kwargs
        Playback direction, scene removal and native animation options.
    """

    def __init__(
        self,
        crosshair: VGroup,
        *,
        lag_ratio: float = 0.15,
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        cross = cast(Any, crosshair)
        rate = cast(Callable[[float], float], kwargs.pop("rate_func", linear))
        fade = _LiveFadeOut if reverse else _LiveFadeIn
        children: list[Animation] = [
            fade(cross.dot, run_time=1, rate_func=rate),
            _IntersectionLines(crosshair, reverse=reverse, run_time=1, rate_func=rate),
        ]
        if cross.readout is not None:
            children.append(fade(cross.readout, run_time=1, rate_func=rate))
        if reverse:
            children.reverse()
        flags(reverse, remover, kwargs)
        super().__init__(
            *children,
            group=crosshair,
            lag_ratio=lag_ratio,
            **cast(dict[str, Any], kwargs),
        )

    def restore(self) -> None:
        """Restore styles while retaining the live intersection and readout."""
        for leaf, _, style in self._canonical:
            leaf.set_style(**style, family=False)
        cross = cast(Any, self.mobject)
        cross.vline._rebuild()
        cross.hline._rebuild()
        driver = cross.dot.__dict__["_helper_driver"]
        driver._ensure()
        # A sibling tracker may finish later; let the scene's final update poll again.
        cross.vline._binding.system._poll_token = None


class RefineRiemann(Presentation):
    """Change a Riemann partition through its nested parent intervals.

    Parameters
    ----------
    rectangles, dx, lag_ratio, order, **kwargs
        Bound rectangles, target step, parent stagger, interval key and Manim options.
    """

    def __init__(
        self,
        rectangles: _RiemannGroup,
        dx: float,
        *,
        lag_ratio: float = 0,
        order: str | Callable[[tuple[float, float]], Any] = "data",
        **kwargs: object,
    ) -> None:
        if not isinstance(rectangles, _RiemannGroup):
            raise TypeError("rectangles must be bound Riemann rectangles")
        if not np.isfinite(dx) or dx <= 0:
            raise ValueError("dx must be finite and positive")
        if not np.isfinite(lag_ratio) or lag_ratio < 0:
            raise ValueError("lag_ratio must be finite and nonnegative")
        if order != "data" and not callable(order):
            raise ValueError("order must be data or an interval key")
        self.rectangles, self.dx, self.order = rectangles, dx, order
        kwargs.setdefault("suspend_mobject_updating", False)
        super().__init__(
            rectangles, lag_ratio=lag_ratio, **cast(dict[str, Any], kwargs)
        )

    def begin(self) -> None:
        """Resolve the current partition and acquire its derivation."""
        group = self.rectangles
        binding = group._binding
        binding.poll()
        binding.ensure()
        self._old_dx = binding.number("dx")
        ratio = max(self.dx, self._old_dx) / min(self.dx, self._old_dx)
        if not np.isclose(ratio, round(ratio)):
            raise ValueError("Riemann partitions must be nested")
        if "_topology_writer" in binding.__dict__:
            raise ValueError("concurrent Riemann writers conflict")
        self._binding = binding
        self._derive = binding.derive
        self._parameter = binding.parameters["dx"]
        self._styles = [r.get_style() for r in group]
        self._progress = 0.0
        binding.__dict__["_topology_writer"] = self
        binding.derive = self._transition
        super().begin()

    def _partition(self, dx: float) -> dict[str, Any]:
        binding = self._binding
        parameter = binding.parameters["dx"]
        binding.parameters["dx"] = Parameter(dx, name="dx")
        try:
            self._derive(binding)
            return copy.deepcopy(binding.boundaries)
        finally:
            binding.parameters["dx"] = parameter

    def _transition(self, base: _Binding) -> None:
        binding = cast(_RegionBinding, base)
        coarse = max(self.dx, self._old_dx)
        fine = min(self.dx, self._old_dx)
        parents = self._partition(coarse)
        children = self._partition(fine)
        count = len(parents)
        key = self.order
        # Interval order is semantic even when widths are drawn with an overlap.
        intervals = [(i * coarse, (i + 1) * coarse) for i in range(count)]
        if parents:
            start = float(binding.system._data.inverse(parents["0"][0][0])[0, 0])
            intervals = [(a + start, b + start) for a, b in intervals]
        order = (
            sorted(range(count), key=lambda i: key(intervals[i]))
            if callable(key)
            else list(range(count))
        )
        ranks = {parent: rank for rank, parent in enumerate(order)}
        factor = round(coarse / fine)
        for j, pieces in enumerate(children.values()):
            parent = min(j // factor, count - 1)
            p = self.rate_func(
                window(self._progress, ranks[parent], count, self.lag_ratio)
            )
            if self.dx > self._old_dx:
                p = 1 - p
            top, bottom = pieces[0]
            old_top, old_bottom = parents[str(parent)][0]
            top[:, 1] = (1 - p) * old_top[0, 1] + p * top[:, 1]
            bottom[:, 1] = (1 - p) * old_bottom[0, 1] + p * bottom[:, 1]
        binding.boundaries = children

    def interpolate_mobject(self, alpha: float) -> None:
        """Derive child heights from the absolute parent progress."""
        self._progress = alpha
        binding = self._binding
        binding._seen = None
        binding.ensure()
        self.rectangles._ensure_regions()
        factor = round(max(self.dx, self._old_dx) / min(self.dx, self._old_dx))
        for i, member in enumerate(self.rectangles):
            rect = cast(FilledRegion, member)
            source = i // factor if self.dx < self._old_dx else i
            rect.set_style(**self._styles[min(source, len(self._styles) - 1)])
            rect._binding_seen = -1
            rect.refresh()

    def restore(self) -> None:
        """Commit the target step while retaining an existing tracker input."""
        binding = self._binding
        if binding.__dict__.get("_topology_writer") is not self:
            return
        binding.derive = self._derive
        binding.__dict__.pop("_topology_writer")
        self.rectangles._follow_dx = True
        tracker = self._parameter.tracker
        setter = getattr(tracker, "set_value", None)
        if callable(setter):
            setter(self.dx)
            self._parameter.poll()
        else:
            self._parameter.value = self.dx
        binding._seen = None
        binding.ensure()
        self.rectangles._ensure_regions()
        for rect in self.rectangles:
            rect.refresh()
