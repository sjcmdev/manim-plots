"""Three-dimensional Cartesian systems and camera-dependent box decorations."""

from __future__ import annotations

import warnings
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from typing import Any, Literal, NoReturn, Self, cast

import numpy as np
from manim import (
    DOWN,
    LEFT,
    OUT,
    PI,
    RIGHT,
    SMALL_BUFF,
    UR,
    Mobject,
    ThreeDCamera,
    VGroup,
    VMobject,
    config,
)
from manim import ThreeDAxes as NativeThreeDAxes
from manim.camera.camera import Camera
from manim.utils.color import ParsableManimColor
from numpy.typing import ArrayLike

from manim_plots.core import FloatArray, ManimPlotsWarning
from manim_plots.core.scales import (
    MINPOS_UNKNOWN,
    LinearScale,
    LogScale,
    Scale,
    SymLogScale,
)
from manim_plots.core.sources import Box
from manim_plots.core.ticks import LogLocator, SymLogLocator
from manim_plots.mobjects.artists import LinePlot, ScatterPlot
from manim_plots.mobjects.axis import Axis, TickDirection, _range
from manim_plots.mobjects.context import _drawing_camera, _scene_camera
from manim_plots.mobjects.leaves import (
    AxisLine,
    BoundLabel,
    FrameLeaf,
    _ArtistOptions,
    _label,
    _VMStyle,
)
from manim_plots.mobjects.legend import Legend
from manim_plots.mobjects.system import CartesianAxes, _scale
from manim_plots.mobjects.themes import Theme, _resolve_theme


class Pane(VMobject):
    """Hold one box face and its separately styleable grid.

    Parameters
    ----------
    **kwargs
        Native vector mobject style options.
    """

    def __init__(self, **kwargs: object) -> None:
        options = {"fill_opacity": 0.08, "stroke_width": 0.5, **kwargs}
        super().__init__(**cast(_VMStyle, options))
        self.grid = VGroup(stroke_width=0.5, stroke_opacity=0.4)
        self._grid_lines: dict[tuple[int, float], VMobject] = {}
        self.set_shade_in_3d(True)
        self.add(self.grid)


class ThreeDAxes(CartesianAxes):
    """Build an affine Cartesian system with three independently scaled axes.

    Parameters
    ----------
    x_range, y_range, z_range
        Data endpoints and optional major tick spacing.
    x_length, y_length, z_length
        Scene lengths, using Manim's defaults when omitted.
    z_axis_config, z_normal
        Z decoration options and Manim's tick-plane normal.
    num_axis_pieces, light_source, depth, gloss
        Manim's axis shading controls.
    x_scale, y_scale, z_scale
        Linear, log, symlog, or custom scales.
    frame, face_camera
        Origin or camera-following box; optionally orient text to the camera.
    aspect
        Equal data units or a positive three-component box ratio.
    theme, cycle
        Decoration defaults and artist colour cycle.
    **kwargs
        Cartesian axis and native mobject options.
    """

    def __init__(
        self,
        x_range: Sequence[float] = (-6, 6, 1),
        y_range: Sequence[float] = (-5, 5, 1),
        z_range: Sequence[float] = (-4, 4, 1),
        x_length: float | None = None,
        y_length: float | None = None,
        z_length: float | None = None,
        z_axis_config: dict[str, Any] | None = None,
        z_normal: ArrayLike = DOWN,
        num_axis_pieces: int = 20,
        light_source: ArrayLike = 9 * DOWN + 7 * LEFT + 10 * OUT,
        depth: object = None,
        gloss: float = 0.5,
        *,
        x_scale: Scale | str = "linear",
        y_scale: Scale | str = "linear",
        z_scale: Scale | str = "linear",
        frame: Literal["origin", "box"] | None = None,
        aspect: str | Sequence[float] | None = None,
        face_camera: bool | None = None,
        theme: str | Theme | Mapping[str, Any] | None = None,
        cycle: str | Sequence[ParsableManimColor] | None = None,
        **kwargs: object,
    ) -> None:
        chosen = _resolve_theme(theme)
        style = frame or (
            "box" if chosen.position == "border" and chosen.box else "origin"
        )
        if style not in ("origin", "box"):
            raise ValueError("frame must be origin or box")
        lengths = [
            config.frame_height + 2.5 if x_length is None else x_length,
            config.frame_height + 2.5 if y_length is None else y_length,
            config.frame_height - 1.5 if z_length is None else z_length,
        ]
        if aspect is not None:
            if y_length is not None or z_length is not None:
                raise ValueError("aspect cannot fix y_length or z_length")
            ratios = (
                np.array([r[1] - r[0] for r in (x_range, y_range, z_range)])
                if aspect == "equal"
                else np.asarray(aspect, dtype=float)
            )
            if (
                ratios.shape != (3,)
                or not np.isfinite(ratios).all()
                or (ratios <= 0).any()
            ):
                raise ValueError("aspect must be equal or three positive ratios")
            lengths = (lengths[0] * ratios / ratios[0]).tolist()
        self._camera: Camera | None = None
        self._camera_explicit = False
        self._camera_angles: tuple[float, float, float] | None = None
        self._camera_warned = False
        self._pane_sides: tuple[bool, ...] | None = None
        self.face_camera = style == "box" if face_camera is None else face_camera
        self.panes: dict[str, Pane] = {}
        self._axis_titles: list[BoundLabel] = []
        self._legend_pending: Legend | None = None
        # The 3D frame supplies its own border decorations.
        super().__init__(
            x_range,
            y_range,
            lengths[0],
            lengths[1],
            x_scale=_scale(x_scale, "x_scale"),
            y_scale=_scale(y_scale, "y_scale"),
            theme=replace(chosen, position="origin", box=False, grid=()),
            cycle=cycle,
            **cast(_VMStyle, kwargs),
        )
        self.theme = chosen
        self._frame_style = style
        self._syncing = True
        scale = _scale(z_scale, "z_scale")
        limits = _range(z_range, "z_range")
        if not np.isfinite(scale.forward(limits)).all():
            raise ValueError("z_range must be inside the scale domain")
        valid = scale.limit_range(float(limits[0]), float(limits[1]), MINPOS_UNKNOWN)
        if not np.allclose(valid, limits):
            raise ValueError("z_range must be inside the scale domain")
        options = {**self.axis_config, **(z_axis_config or {})}
        native_range = [*scale.forward(limits), z_range[2] if len(z_range) == 3 else 1]
        native = NativeThreeDAxes(
            x_range,
            y_range,
            native_range,
            x_length=lengths[0],
            y_length=lengths[1],
            z_length=lengths[2],
            z_axis_config={**options, "include_numbers": False},
            z_normal=np.asarray(z_normal, dtype=float),
            num_axis_pieces=num_axis_pieces,
        )
        if not isinstance(scale, LinearScale):
            native.z_axis.shift(
                -0.5 * (native.z_axis.get_start()[2] + native.z_axis.get_end()[2]) * OUT
            )
        locator = (
            LogLocator(base=scale.base)
            if isinstance(scale, LogScale)
            else SymLogLocator(base=scale.base, linthresh=scale.linthresh)
            if isinstance(scale, SymLogScale)
            else None
        )
        self.z_axis = Axis(
            self, 2, z_range, native.z_axis, scale, locator, axis_config=options
        )
        self.z = self.z_axis
        self.z.line.match_style(cast(VGroup, native.z_axis.pieces)[0])
        self.z.tick_under_tip = True
        if len(native.z_axis.ticks):
            tick = native.z_axis.ticks[0]
            for leaf in self.z._tick_leaves.values():
                leaf.match_style(tick)
            self.z._tick_reference = (
                tick.points - tick.get_center()
            ) / native.z_axis.tick_size
        self.z_length = lengths[2]
        self.z_axis_config = options
        self.z_normal = np.asarray(z_normal)
        self.num_axis_pieces = num_axis_pieces
        self.light_source = np.asarray(light_source)
        if not np.isfinite(lengths).all() or min(lengths) <= 0:
            raise ValueError("axis lengths must be positive and finite")
        self.gloss = gloss
        self.dimension = 3
        self._ranges = (self.x, self.y, self.z)
        self.axes = VGroup(*self._ranges)
        lower = -np.asarray(lengths) / 2
        upper = -lower
        if isinstance(scale, LinearScale) and not limits[0] < 0 < limits[1]:
            lower[2] = native.z_axis.get_start()[2]
            upper[2] = native.z_axis.get_end()[2]
        self.bounds = Box(lower, upper)
        self.frame = FrameLeaf(lower, upper, self)
        self._channel_frame = self.frame
        self.submobjects = [*self._ranges, self.frame]
        self._field_steps = (*self._field_steps, native_range[2])
        self._compile()
        for axis in self._ranges:
            axis._configure()
        self._syncing = False
        self._add_3d_pieces()
        self._set_axis_shading()
        if style == "box":
            for axis in self._ranges:
                axis.set_tips(start=False, end=False)
            self.panes = {name: Pane() for name in "xyz"}
            self.submobjects[:0] = list(self.panes.values())
            self._update_view(0, -PI / 2)
            for axis in self._ranges:
                axis.add_numbers()
        if style == "box" or self.face_camera:
            self.add_updater(_camera_update)

    def _add_3d_pieces(self) -> None:
        for axis in self._ranges:
            template = VMobject().set_points(axis.line.points)
            axis.pieces = VGroup(
                *(
                    AxisLine(piece.points, self).match_style(axis.line)
                    for piece in template.get_pieces(self.num_axis_pieces)
                )
            )
            axis.add(axis.pieces)
            axis._tick_styles["major"].setdefault(
                "width", float(axis.line.get_stroke_width())
            )
            axis.line.set_stroke(width=0, family=False)
            axis._crossing_frame = -1
            axis._configure()
            axis.set_shade_in_3d(True)

    def _set_axis_shading(self) -> None:
        def gradient(axis: Axis) -> Callable[[], tuple[FloatArray, FloatArray]]:
            return lambda: (
                axis.get_edge_center(-self.light_source),
                axis.get_edge_center(self.light_source),
            )

        for axis in self._ranges:
            for member in axis.family_members_with_points():
                native = cast(Any, member)
                native.get_gradient_start_and_end_points = gradient(axis)
                native.get_unit_normal = lambda a: np.ones(3)
                member.set_sheen(0.2)

    def _refresh_pieces(self) -> None:
        fractions = (
            np.arange(self.num_axis_pieces)[:, None] + np.linspace(0, 1, 4)
        ) / self.num_axis_pieces
        for axis in self._ranges:
            if not hasattr(axis, "pieces"):
                continue
            line = axis.line.points
            points = line[0] + fractions[:, :, None] * (line[-1] - line[0])
            for piece, geometry in zip(axis.pieces, points, strict=True):
                piece.set_points(geometry)

    def _configure_grid(self) -> None:
        if len(self._ranges) != 3:
            return
        for axis in self._ranges:
            self._save_flat_text(axis)
        self._pane_sides = None
        self._update_view(
            *(self._camera_angles[:2] if self._camera_angles else (0, -PI / 2))
        )

    @property
    def z_range(self) -> FloatArray:
        """Return z endpoints and the locator's original step."""
        return np.append(self.z.range.value, self.z._step)

    def set_z_range(self, z_range: Sequence[float]) -> Self:
        """Set z endpoints, retaining keyed decorations.

        Parameters
        ----------
        z_range
            New data endpoints and optional field spacing.
        """
        limits = _range(z_range, "z_range")
        if not np.isfinite(self.z._scale.forward(limits)).all():
            raise ValueError("z_range must be inside the scale domain")
        self.z.range = limits
        if len(z_range) == 3:
            self._field_steps = (*self._field_steps[:2], float(z_range[2]))
        return self

    def get_z_axis(self) -> Axis:
        """Return the z decoration."""
        return self.z

    def get_z_axis_label(
        self,
        label: object,
        edge: ArrayLike = OUT,
        direction: ArrayLike = RIGHT,
        buff: float = SMALL_BUFF,
        rotation: float = PI / 2,
        rotation_axis: ArrayLike = RIGHT,
        **kwargs: object,
    ) -> BoundLabel:
        """Place a bound z title with Manim's rotation defaults.

        Parameters
        ----------
        label, edge, direction, buff, rotation, rotation_axis, **kwargs
            Manim's axis-label content, placement, rotation and style options.
        """
        result = _label(label)
        result.next_to(
            self.z.get_edge_center(np.asarray(edge)),
            direction=np.asarray(direction),
            buff=buff,
        )
        result.rotate(rotation, axis=np.asarray(rotation_axis))
        result.set(**kwargs)
        title = BoundLabel(result, self)
        self._axis_titles.append(title)
        return title

    def get_y_axis_label(
        self,
        label: object,
        edge: ArrayLike | None = UR,
        direction: ArrayLike | None = UR,
        buff: float = SMALL_BUFF,
        rotation: float = PI / 2,
        rotation_axis: ArrayLike = OUT,
        **kwargs: object,
    ) -> BoundLabel:
        """Place a bound y title with Manim's 3D defaults.

        Parameters
        ----------
        label, edge, direction, buff, rotation, rotation_axis, **kwargs
            Native label content, placement, rotation and style options.
        """
        result = super().get_y_axis_label(
            label, edge, direction, buff, **cast(_VMStyle, kwargs)
        )
        result.rotate(rotation, axis=np.asarray(rotation_axis))
        self._axis_titles.append(result)
        return result

    def get_axis_labels(
        self, x_label: object = "x", y_label: object = "y", z_label: object = "z"
    ) -> VGroup:
        """Return the three bound axis titles.

        Parameters
        ----------
        x_label, y_label, z_label
            Label content for each axis.
        """
        labels = VGroup(
            self.get_x_axis_label(x_label),
            self.get_y_axis_label(y_label),
            self.get_z_axis_label(z_label),
        )
        for title in labels:
            if isinstance(title, BoundLabel) and title not in self._axis_titles:
                self._axis_titles.append(title)
        return labels

    def line(
        self,
        xs: ArrayLike,
        ys: ArrayLike | None = None,
        zs: ArrayLike | None = None,
        **kwargs: object,
    ) -> LinePlot:
        """Join data triples with straight segments.

        Parameters
        ----------
        xs, ys, zs, **kwargs
            Coordinate arrays (or rows in xs) and artist options.
        """
        data = (
            xs
            if ys is None
            else np.column_stack((np.asarray(xs), np.asarray(ys), np.asarray(zs)))
        )
        artist = LinePlot(data, self, **cast(_ArtistOptions, kwargs))
        self.add(artist)
        return artist

    def scatter(
        self,
        xs: ArrayLike,
        ys: ArrayLike | None = None,
        zs: ArrayLike | None = None,
        **kwargs: object,
    ) -> ScatterPlot:
        """Place flat markers at data triples.

        Parameters
        ----------
        xs, ys, zs, **kwargs
            Coordinate arrays (or rows in xs) and artist options.
        """
        data = (
            xs
            if ys is None
            else np.column_stack((np.asarray(xs), np.asarray(ys), np.asarray(zs)))
        )
        artist = ScatterPlot(data, self, **cast(_VMStyle, kwargs))
        self.add(artist)
        return artist

    def legend(
        self,
        location: str | None = None,
        *,
        font_size: float = 24,
        buff: float = 0.25,
        frame: bool | None = None,
        frame_style: Mapping[str, Any] | None = None,
    ) -> Legend:
        """Attach a legend, fixing it in the camera frame on its first update.

        Parameters
        ----------
        location, font_size, buff, frame, frame_style
            Legend placement, typography and frame options as in CartesianAxes.
        """
        result = super().legend(
            location,
            font_size=font_size,
            buff=buff,
            frame=frame,
            frame_style=frame_style,
        )
        self._legend_pending = result
        if _camera_update not in self._actual_updaters:
            self.add_updater(_camera_update)
        return result

    def view(
        self, elev: float = 30, azim: float = -60, roll: float = 0
    ) -> dict[str, float]:
        """Return Manim camera keywords for angles in degrees.

        Parameters
        ----------
        elev, azim, roll
            Matplotlib elevation, azimuth and camera roll.

        Returns
        -------
        dict
            Radian phi, theta and gamma for a ThreeDScene.
        """
        return {
            "phi": float(np.deg2rad(90 - elev)),
            "theta": float(np.deg2rad(azim)),
            "gamma": float(np.deg2rad(roll)),
        }

    def get_family(self, recurse: bool = True) -> list[Mobject]:
        """Return the family after reading a camera that is drawing it.

        Parameters
        ----------
        recurse
            Passed through to Manim's family traversal.

        Returns
        -------
        list of Mobject
            The unchanged family returned by Manim.
        """
        if self.face_camera or self.__dict__.get("_frame_style") == "box":
            camera = _drawing_camera()
            if camera is not None:
                if not self._camera_explicit and self._camera is not camera:
                    self._camera = camera
                    self._camera_angles = None
                self._read_camera()
        return super().get_family(recurse)

    def set_camera(self, camera: Camera) -> Self:
        """Name a camera explicitly and immediately refresh the frame.

        Parameters
        ----------
        camera
            Camera used to select box sides and text orientation.
        """
        self._camera = camera
        self._camera_explicit = True
        self._camera_angles = None
        self._read_camera()
        return self

    def _save_flat_text(self, axis: Axis) -> None:
        for number in (*axis.numbers, *axis.labels):
            members = number.family_members_with_points()
            # Axis-local geometry stays unturned even after the camera faces text.
            flats = [
                self.frame.mapping.forward(leaf._axis_local)
                if getattr(leaf, "_axis_local", None) is not None
                else leaf.points.copy()
                for leaf in members
            ]
            if not flats:
                continue
            points = np.concatenate(flats)
            number._flat_anchor = (points.min(axis=0) + points.max(axis=0)) / 2
            for leaf, flat in zip(members, flats, strict=True):
                leaf._flat_offset = flat - number._flat_anchor

    def _read_camera(self) -> None:
        if not isinstance(self._camera, ThreeDCamera):
            if (
                self._camera is not None
                and not self._camera_warned
                and (self.frame_style == "box" or self.face_camera)
            ):
                warnings.warn(
                    "ThreeDAxes requires a ThreeDCamera for its view",
                    ManimPlotsWarning,
                    stacklevel=2,
                )
                self._camera_warned = True
            return
        angles = (
            self._camera.get_phi(),
            self._camera.get_theta(),
            self._camera.get_gamma(),
        )
        if angles == self._camera_angles:
            return
        self._camera_angles = angles
        self._update_view(*angles[:2])

    def _update_view(self, phi: float, theta: float) -> None:
        d = np.array(
            [np.sin(phi) * np.cos(theta), np.sin(phi) * np.sin(theta), np.cos(phi)]
        )
        sides = tuple(bool(v > 0) for v in d)
        if self.panes and sides != self._pane_sides:
            self._pane_sides = sides
            near = [
                axis.range.value[int(side)]
                for axis, side in zip(self._ranges, sides, strict=True)
            ]
            far = [
                axis.range.value[int(not side)]
                for axis, side in zip(self._ranges, sides, strict=True)
            ]
            for index, pane in enumerate(self.panes.values()):
                others = [i for i in range(3) if i != index]
                corners = np.tile(far, (5, 1))
                for row, (a, b) in enumerate(((0, 0), (1, 0), (1, 1), (0, 1), (0, 0))):
                    corners[row, others] = [
                        self._ranges[others[0]].range.value[a],
                        self._ranges[others[1]].range.value[b],
                    ]
                pane.set_points_as_corners(self._mapping().to_screen(corners))
                lines: dict[tuple[int, float], VMobject] = {}
                for along, across in (others, others[::-1]):
                    for value in self.get_axis(along).get_tick_range():
                        endpoints = np.tile(far, (2, 1))
                        endpoints[:, along] = value
                        endpoints[:, across] = self.get_axis(across).range.value
                        key = along, float(value)
                        line = pane._grid_lines.get(key)
                        if line is None:
                            line = VMobject().match_style(pane.grid)
                        line.set_points_as_corners(self._mapping().to_screen(endpoints))
                        lines[key] = line
                pane._grid_lines = lines
                pane.grid.submobjects = list(lines.values())
            right = np.array([-np.sin(theta), np.cos(theta)])
            edges = [
                (x, y)
                for x in self.x.range.value
                for y in self.y.range.value
                if (x, y) != tuple(far[:2])
            ]
            best = max(edges, key=lambda e: float(np.dot(e, right)))
            for axis, crossing in zip(
                self._ranges,
                ([0, near[1], far[2]], [near[0], 0, far[2]], [*best, 0]),
                strict=True,
            ):
                axis._edge_coordinates = crossing
                axis._tick_styles["major"].setdefault("direction", TickDirection.IN)
                axis._crossing_frame = -1
                axis._configure()
                self._save_flat_text(axis)
        self._refresh_pieces()
        if self.face_camera and isinstance(self._camera, ThreeDCamera):
            rotation = self._camera.generate_rotation_matrix()
            texts = [
                number
                for axis in self._ranges
                for number in (*axis.numbers, *axis.labels)
            ]
            for number in (*texts, *self._axis_titles):
                if not hasattr(number, "_flat_anchor"):
                    number._flat_anchor = number.get_center()
                for leaf in number.family_members_with_points():
                    if not hasattr(leaf, "_flat_offset"):
                        leaf._flat_offset = leaf.points - number._flat_anchor
                    leaf.set_points(number._flat_anchor + leaf._flat_offset @ rotation)

    def twinx(self, *args: object, **kwargs: object) -> NoReturn:
        """Refuse the two-dimensional twinx helper.

        Parameters
        ----------
        *args, **kwargs
            Arguments reserved for the two-dimensional system.
        """
        raise NotImplementedError("twinx is not available on ThreeDAxes")

    def twiny(self, *args: object, **kwargs: object) -> NoReturn:
        """Refuse the two-dimensional twiny helper.

        Parameters
        ----------
        *args, **kwargs
            Arguments reserved for the two-dimensional system.
        """
        raise NotImplementedError("twiny is not available on ThreeDAxes")

    def twin(self, *args: object, **kwargs: object) -> NoReturn:
        """Refuse the two-dimensional twin helper.

        Parameters
        ----------
        *args, **kwargs
            Arguments reserved for the two-dimensional system.
        """
        raise NotImplementedError("twin is not available on ThreeDAxes")

    def secondary_xaxis(self, *args: object, **kwargs: object) -> NoReturn:
        """Refuse the two-dimensional secondary_xaxis helper.

        Parameters
        ----------
        *args, **kwargs
            Arguments reserved for the two-dimensional system.
        """
        raise NotImplementedError("secondary_xaxis is not available on ThreeDAxes")

    def secondary_yaxis(self, *args: object, **kwargs: object) -> NoReturn:
        """Refuse the two-dimensional secondary_yaxis helper.

        Parameters
        ----------
        *args, **kwargs
            Arguments reserved for the two-dimensional system.
        """
        raise NotImplementedError("secondary_yaxis is not available on ThreeDAxes")

    def get_vector_field(self, *args: object, **kwargs: object) -> NoReturn:
        """Refuse the two-dimensional get_vector_field helper.

        Parameters
        ----------
        *args, **kwargs
            Arguments reserved for the two-dimensional system.
        """
        raise NotImplementedError("get_vector_field is not available on ThreeDAxes")

    def get_stream_lines(self, *args: object, **kwargs: object) -> NoReturn:
        """Refuse the two-dimensional get_stream_lines helper.

        Parameters
        ----------
        *args, **kwargs
            Arguments reserved for the two-dimensional system.
        """
        raise NotImplementedError("get_stream_lines is not available on ThreeDAxes")

    def get_vector(self, *args: object, **kwargs: object) -> NoReturn:
        """Refuse the two-dimensional get_vector helper.

        Parameters
        ----------
        *args, **kwargs
            Arguments reserved for the two-dimensional system.
        """
        raise NotImplementedError("get_vector is not available on ThreeDAxes")

    def plot_implicit_curve(self, *args: object, **kwargs: object) -> NoReturn:
        """Refuse the two-dimensional plot_implicit_curve helper.

        Parameters
        ----------
        *args, **kwargs
            Arguments reserved for the two-dimensional system.
        """
        raise NotImplementedError("plot_implicit_curve is not available on ThreeDAxes")

    def errorbar(self, *args: object, **kwargs: object) -> NoReturn:
        """Refuse the two-dimensional errorbar helper.

        Parameters
        ----------
        *args, **kwargs
            Arguments reserved for the two-dimensional system.
        """
        raise NotImplementedError("errorbar is not available on ThreeDAxes")

    def get_line_from_axis_to_point(self, *args: object, **kwargs: object) -> NoReturn:
        """Refuse the two-dimensional get_line_from_axis_to_point helper.

        Parameters
        ----------
        *args, **kwargs
            Arguments reserved for the two-dimensional system.
        """
        raise NotImplementedError(
            "get_line_from_axis_to_point is not available on ThreeDAxes"
        )

    def get_vertical_line(self, *args: object, **kwargs: object) -> NoReturn:
        """Refuse the two-dimensional get_vertical_line helper.

        Parameters
        ----------
        *args, **kwargs
            Arguments reserved for the two-dimensional system.
        """
        raise NotImplementedError("get_vertical_line is not available on ThreeDAxes")

    def get_horizontal_line(self, *args: object, **kwargs: object) -> NoReturn:
        """Refuse the two-dimensional get_horizontal_line helper.

        Parameters
        ----------
        *args, **kwargs
            Arguments reserved for the two-dimensional system.
        """
        raise NotImplementedError("get_horizontal_line is not available on ThreeDAxes")

    def get_lines_to_point(self, *args: object, **kwargs: object) -> NoReturn:
        """Refuse the two-dimensional get_lines_to_point helper.

        Parameters
        ----------
        *args, **kwargs
            Arguments reserved for the two-dimensional system.
        """
        raise NotImplementedError("get_lines_to_point is not available on ThreeDAxes")

    def get_vertical_lines_to_graph(self, *args: object, **kwargs: object) -> NoReturn:
        """Refuse the two-dimensional get_vertical_lines_to_graph helper.

        Parameters
        ----------
        *args, **kwargs
            Arguments reserved for the two-dimensional system.
        """
        raise NotImplementedError(
            "get_vertical_lines_to_graph is not available on ThreeDAxes"
        )

    def axvline(self, *args: object, **kwargs: object) -> NoReturn:
        """Refuse the two-dimensional axvline helper.

        Parameters
        ----------
        *args, **kwargs
            Arguments reserved for the two-dimensional system.
        """
        raise NotImplementedError("axvline is not available on ThreeDAxes")

    def axhline(self, *args: object, **kwargs: object) -> NoReturn:
        """Refuse the two-dimensional axhline helper.

        Parameters
        ----------
        *args, **kwargs
            Arguments reserved for the two-dimensional system.
        """
        raise NotImplementedError("axhline is not available on ThreeDAxes")

    def angle_of_tangent(self, *args: object, **kwargs: object) -> NoReturn:
        """Refuse the two-dimensional angle_of_tangent helper.

        Parameters
        ----------
        *args, **kwargs
            Arguments reserved for the two-dimensional system.
        """
        raise NotImplementedError("angle_of_tangent is not available on ThreeDAxes")

    def slope_of_tangent(self, *args: object, **kwargs: object) -> NoReturn:
        """Refuse the two-dimensional slope_of_tangent helper.

        Parameters
        ----------
        *args, **kwargs
            Arguments reserved for the two-dimensional system.
        """
        raise NotImplementedError("slope_of_tangent is not available on ThreeDAxes")

    def get_tangent_line(self, *args: object, **kwargs: object) -> NoReturn:
        """Refuse the two-dimensional get_tangent_line helper.

        Parameters
        ----------
        *args, **kwargs
            Arguments reserved for the two-dimensional system.
        """
        raise NotImplementedError("get_tangent_line is not available on ThreeDAxes")

    def get_tangent_vector(self, *args: object, **kwargs: object) -> NoReturn:
        """Refuse the two-dimensional get_tangent_vector helper.

        Parameters
        ----------
        *args, **kwargs
            Arguments reserved for the two-dimensional system.
        """
        raise NotImplementedError("get_tangent_vector is not available on ThreeDAxes")

    def get_secant_slope_group(self, *args: object, **kwargs: object) -> NoReturn:
        """Refuse the two-dimensional get_secant_slope_group helper.

        Parameters
        ----------
        *args, **kwargs
            Arguments reserved for the two-dimensional system.
        """
        raise NotImplementedError(
            "get_secant_slope_group is not available on ThreeDAxes"
        )

    def plot_derivative_graph(self, *args: object, **kwargs: object) -> NoReturn:
        """Refuse the two-dimensional plot_derivative_graph helper.

        Parameters
        ----------
        *args, **kwargs
            Arguments reserved for the two-dimensional system.
        """
        raise NotImplementedError(
            "plot_derivative_graph is not available on ThreeDAxes"
        )

    def plot_antiderivative_graph(self, *args: object, **kwargs: object) -> NoReturn:
        """Refuse the two-dimensional plot_antiderivative_graph helper.

        Parameters
        ----------
        *args, **kwargs
            Arguments reserved for the two-dimensional system.
        """
        raise NotImplementedError(
            "plot_antiderivative_graph is not available on ThreeDAxes"
        )

    def get_area(self, *args: object, **kwargs: object) -> NoReturn:
        """Refuse the two-dimensional get_area helper.

        Parameters
        ----------
        *args, **kwargs
            Arguments reserved for the two-dimensional system.
        """
        raise NotImplementedError("get_area is not available on ThreeDAxes")

    def fill_between(self, *args: object, **kwargs: object) -> NoReturn:
        """Refuse the two-dimensional fill_between helper.

        Parameters
        ----------
        *args, **kwargs
            Arguments reserved for the two-dimensional system.
        """
        raise NotImplementedError("fill_between is not available on ThreeDAxes")

    def get_riemann_rectangles(self, *args: object, **kwargs: object) -> NoReturn:
        """Refuse the two-dimensional get_riemann_rectangles helper.

        Parameters
        ----------
        *args, **kwargs
            Arguments reserved for the two-dimensional system.
        """
        raise NotImplementedError(
            "get_riemann_rectangles is not available on ThreeDAxes"
        )

    def apply_function(
        self, function: Callable[[FloatArray], FloatArray], **kwargs: object
    ) -> Self:
        """Refuse non-affine deformation of the frame.

        Parameters
        ----------
        function, **kwargs
            Native pointwise deformation and options.
        """
        raise NotImplementedError(
            "apply_function is not available on ThreeDAxes: an affine frame is required"
        )


def _camera_update(mobject: Mobject, dt: float) -> None:
    assert isinstance(mobject, ThreeDAxes)
    axes = mobject
    if axes._camera is None:
        axes._camera = _scene_camera()
    if axes._legend_pending is not None and isinstance(axes._camera, ThreeDCamera):
        axes._camera.add_fixed_in_frame_mobjects(axes._legend_pending)
        axes._legend_pending = None
    axes._read_camera()
