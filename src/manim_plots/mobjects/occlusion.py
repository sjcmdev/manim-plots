"""Camera-space depth rasterisation and reversible vector-path occlusion."""

from __future__ import annotations

from itertools import pairwise
from typing import TYPE_CHECKING, Any, Protocol, cast

import numpy as np
from manim import Mobject, ThreeDCamera, VMobject

from manim_plots.core import FloatArray
from manim_plots.mobjects.artists import _CurvePlot, _MarkerLeaf
from manim_plots.mobjects.fields import ArrowVectorField, _FieldPart
from manim_plots.mobjects.geometry import PlanePlot
from manim_plots.mobjects.leaves import AxisLine
from manim_plots.mobjects.plots3d import BarPlot3D
from manim_plots.mobjects.surfaces import SurfacePlot, _SurfaceDriver

if TYPE_CHECKING:
    from manim_plots.mobjects.three_d import ThreeDAxes


class DepthBuffer(Protocol):
    """Rasterise projected triangles, retaining the largest depth at each pixel."""

    def render(self, triangles_px: FloatArray, depths: FloatArray) -> FloatArray:
        """Return nearest depths, with negative infinity at empty pixels.

        Parameters
        ----------
        triangles_px, depths
            Triangle vertices in pixels and their projected depths.

        Returns
        -------
        ndarray
            Height by width depth image.
        """
        ...


class NumpyDepth:
    """Rasterise triangles with vectorised barycentric coordinates.

    Parameters
    ----------
    width, height
        Render dimensions in pixels.
    """

    def __init__(self, width: int, height: int) -> None:
        self.width, self.height = width, height

    def render(self, triangles_px: FloatArray, depths: FloatArray) -> FloatArray:
        """Return the nearest depth image.

        Parameters
        ----------
        triangles_px, depths
            Pixel triangles and corresponding vertex depths.

        Returns
        -------
        ndarray
            Depth image, negative infinity where uncovered.
        """
        image = np.full((self.height, self.width), -np.inf)
        for p, z in zip(triangles_px, depths, strict=True):
            lo = np.maximum(np.floor(p.min(axis=0)).astype(int), 0)
            hi = np.minimum(
                np.ceil(p.max(axis=0)).astype(int), [self.width - 1, self.height - 1]
            )
            if np.any(lo > hi):
                continue
            a, b = p[1] - p[0], p[2] - p[0]
            determinant = a[0] * b[1] - a[1] * b[0]
            if abs(determinant) < 1e-12:
                continue
            y, x = np.mgrid[lo[1] : hi[1] + 1, lo[0] : hi[0] + 1]
            dx, dy = x + 0.5 - p[0, 0], y + 0.5 - p[0, 1]
            u = (dx * b[1] - dy * b[0]) / determinant
            v = (a[0] * dy - a[1] * dx) / determinant
            inside = (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9)
            values = z[0] + u * (z[1] - z[0]) + v * (z[2] - z[0])
            target = image[lo[1] : hi[1] + 1, lo[0] : hi[0] + 1]
            np.maximum(target, np.where(inside, values, -np.inf), out=target)
        return image


class GpuDepth(NumpyDepth):
    """Rasterise a depth pass in a standalone moderngl context.

    Parameters
    ----------
    width, height
        Render dimensions in pixels.
    """

    def __init__(self, width: int, height: int) -> None:
        super().__init__(width, height)
        import moderngl

        self.context = moderngl.create_standalone_context()
        self.program = self.context.program(
            vertex_shader="""#version 330
            in vec3 point;
            out float depth;
            void main() { gl_Position=vec4(point.xy,0,1); depth=point.z; }
            """,
            fragment_shader="""#version 330
            in float depth;
            out float value;
            uniform float low;
            uniform float span;
            void main() { value=depth; gl_FragDepth=1.0-(depth-low)/span; }
            """,
        )

    def render(self, triangles_px: FloatArray, depths: FloatArray) -> FloatArray:
        """Return a GPU depth image.

        Parameters
        ----------
        triangles_px, depths
            Pixel triangles and their vertex depths.

        Returns
        -------
        ndarray
            Nearest depths, negative infinity where empty.
        """
        import moderngl

        if not len(depths):
            return np.full((self.height, self.width), -np.inf)
        vertices = np.concatenate(
            (triangles_px / [self.width, self.height] * 2 - 1, depths[..., None]),
            axis=2,
        )
        low, high = float(depths.min()) - 1, float(depths.max()) + 1
        cast(moderngl.Uniform, self.program["low"]).value = low
        cast(moderngl.Uniform, self.program["span"]).value = high - low
        texture = self.context.texture((self.width, self.height), 1, dtype="f4")
        depth = self.context.depth_renderbuffer((self.width, self.height))
        framebuffer = self.context.framebuffer([texture], depth)
        buffer = self.context.buffer(vertices.astype("f4").tobytes())
        array = self.context.vertex_array(self.program, [(buffer, "3f", "point")])
        try:
            framebuffer.use()
            framebuffer.clear(-float("inf"), depth=1)
            self.context.enable(moderngl.DEPTH_TEST)
            array.render(moderngl.TRIANGLES)
            return (
                np.frombuffer(texture.read(), dtype=np.float32)
                .reshape(self.height, self.width)
                .astype(float)
            )
        finally:
            array.release()
            buffer.release()
            framebuffer.release()
            depth.release()
            texture.release()


def _project(camera: ThreeDCamera, points: FloatArray) -> FloatArray:
    p = np.asarray(camera.project_points(points.copy()), float)
    p[:, :2] -= camera.frame_center[:2]
    p[:, :2] *= [
        camera.pixel_width / camera.frame_width,
        -camera.pixel_height / camera.frame_height,
    ]
    p[:, :2] += [camera.pixel_width / 2, camera.pixel_height / 2]
    return p


def _split(p: FloatArray, t: float) -> tuple[FloatArray, FloatArray]:
    a = (1 - t) * p[:-1] + t * p[1:]
    b = (1 - t) * a[:-1] + t * a[1:]
    c = (1 - t) * b[0] + t * b[1]
    return np.array([p[0], a[0], b[0], c]), np.array([c, b[1], a[2], p[3]])


def _cut(points: FloatArray, camera: ThreeDCamera, image: FloatArray) -> FloatArray:
    def hidden(p: FloatArray) -> np.ndarray[Any, np.dtype[np.bool_]]:
        projected = _project(camera, p)
        x, y = np.floor(projected[:, :2]).astype(int).T
        inside = (x >= 0) & (x < image.shape[1]) & (y >= 0) & (y < image.shape[0])
        result = np.zeros(len(p), dtype=bool)
        result[inside] = image[y[inside], x[inside]] > projected[inside, 2] + 1e-3
        return result

    pieces = []
    unchanged = True
    for p in points.reshape(-1, 4, 3):

        def evaluate(t: FloatArray, p: FloatArray = p) -> FloatArray:
            t = t[:, None]
            return cast(
                FloatArray,
                (
                    (1 - t) ** 3 * p[0]
                    + 3 * (1 - t) ** 2 * t * p[1]
                    + 3 * (1 - t) * t * t * p[2]
                    + t**3 * p[3]
                ),
            )

        polygon = _project(camera, p)[:, :2]
        count = max(
            8, int(np.ceil(np.linalg.norm(np.diff(polygon, axis=0), axis=1).sum() * 2))
        )
        ts = np.linspace(0, 1, count + 1)
        states = hidden(evaluate(ts))
        if not states.any():
            pieces.append(p)
            continue
        unchanged = False
        cuts = [0.0]
        for i in np.flatnonzero(states[:-1] != states[1:]):
            lo, hi = ts[i], ts[i + 1]
            while (
                np.linalg.norm(
                    np.diff(
                        _project(camera, evaluate(np.array([lo, hi])))[:, :2], axis=0
                    )
                )
                >= 0.5
            ):
                mid = (lo + hi) / 2
                if hidden(evaluate(np.array([mid])))[0] == states[i]:
                    lo = mid
                else:
                    hi = mid
            cuts.append(float((lo + hi) / 2))
        cuts.append(1.0)
        for lo, hi in pairwise(cuts):
            if not hidden(evaluate(np.array([(lo + hi) / 2])))[0]:
                left = _split(p, hi)[0]
                pieces.append(_split(left, lo / hi)[1] if lo else left)
    return (
        points if unchanged else np.concatenate(pieces) if pieces else np.empty((0, 3))
    )


def occlude(system: ThreeDAxes, camera: ThreeDCamera) -> None:
    """Update drawn paths when geometry or the camera changes.

    Parameters
    ----------
    system, camera
        Owning three-dimensional axes and active drawing camera.
    """
    if system.__dict__.get("_occluding", False):
        return
    system.__dict__["_occluding"] = True
    try:
        _occlude(system, camera)
    finally:
        system.__dict__["_occluding"] = False


def _occlude(system: ThreeDAxes, camera: ThreeDCamera) -> None:
    roots: list[Mobject] = [
        artist.owner if isinstance(artist, _SurfaceDriver) else artist
        for artist in system.artists
    ]
    fields: dict[int, ArrowVectorField] = {}
    for artist in roots:
        if isinstance(artist, _FieldPart):
            field = getattr(artist._binding.derive, "__self__", None)
            if isinstance(field, ArrowVectorField):
                fields[id(field)] = field
    for ref in system._field_views:
        field = ref()
        if isinstance(field, ArrowVectorField):
            fields[id(field)] = field
    roots.extend(fields.values())
    family = list({id(m): m for root in roots for m in root.get_family()}.values())
    family.extend(
        m
        for m in Mobject.get_family(system)
        if isinstance(m, AxisLine) and system.frame_style == "origin"
    )
    faces = []
    excluded: set[int] = set()
    arrows = [arrow for field in fields.values() for arrow in field.arrows]
    excluded.update(id(m) for arrow in arrows for m in arrow.get_family())
    for owner in family:
        if isinstance(owner, (SurfacePlot, BarPlot3D, PlanePlot)):
            for face in Mobject.get_family(owner):
                excluded.add(id(face))
                if (
                    isinstance(face, VMobject)
                    and len(face.points)
                    and face.get_fill_opacity() >= 1 - 1e-9
                ):
                    faces.append(face)
    leaves = [
        m
        for m in family
        if id(m) not in excluded
        and isinstance(m, (_CurvePlot, AxisLine))
        and not isinstance(m, _MarkerLeaf)
    ]
    markers = [m for m in family if isinstance(m, _MarkerLeaf)]
    raw = []
    for leaf in leaves:
        _ = leaf.points
        raw.append(leaf._cache)
    signature = (
        camera.get_phi(),
        camera.get_theta(),
        camera.get_gamma(),
        camera.get_focal_distance(),
        camera.get_zoom(),
        tuple(camera.frame_center),
        camera.pixel_width,
        camera.pixel_height,
        system._data_version,
        system.frame.version,
        tuple((id(m), hash(p.tobytes())) for m, p in zip(leaves, raw, strict=True)),
        tuple(
            (id(f), hash(f.points.tobytes()), float(f.get_fill_opacity()))
            for f in faces
        ),
        tuple((id(m), hash(m.points.tobytes())) for m in [*markers, *arrows]),
    )
    if system.__dict__.get("_occlusion_signature") == signature:
        return
    system.__dict__["_occlusion_signature"] = signature
    if not faces:
        for leaf in leaves:
            leaf.__dict__.pop("_occlusion_drawn", None)
        for marker in [*markers, *arrows]:
            for member, style in marker.__dict__.pop("_occlusion_style", []):
                member.set_style(**style)
        return
    # Scene updaters run before ThreeDCamera refreshes its cached rotation.
    camera.reset_rotation_matrix()
    engine = system.__dict__.get("_depth_engine")
    if engine is None:
        if system._occlusion == "numpy":
            engine = NumpyDepth(camera.pixel_width, camera.pixel_height)
        else:
            try:
                engine = GpuDepth(camera.pixel_width, camera.pixel_height)
            except Exception as error:
                if system._occlusion == "gpu":
                    raise RuntimeError(
                        "moderngl standalone context unavailable"
                    ) from error
                engine = NumpyDepth(camera.pixel_width, camera.pixel_height)
        system.__dict__["_depth_engine"] = engine
    triangles: list[FloatArray] = []
    for face in faces:
        polygon = _project(camera, face.points[::4])
        triangles.extend(polygon[[0, i, i + 1]] for i in range(1, len(polygon) - 1))
    projected = np.asarray(triangles).reshape(-1, 3, 3)
    image = engine.render(projected[:, :, :2], projected[:, :, 2])
    for leaf, points in zip(leaves, raw, strict=True):
        leaf.__dict__["_occlusion_drawn"] = (points, _cut(points, camera, image))
    for marker in [*markers, *arrows]:
        point = marker.get_start() if marker in arrows else marker.get_center()
        p = _project(camera, np.array([point]))[0]
        x, y = np.floor(p[:2]).astype(int)
        hidden = (
            0 <= x < image.shape[1]
            and 0 <= y < image.shape[0]
            and image[y, x] > p[2] + 1e-3
        )
        if hidden and "_occlusion_style" not in marker.__dict__:
            marker.__dict__["_occlusion_style"] = [
                (member, member.get_style())
                for member in marker.get_family()
                if isinstance(member, VMobject)
            ]
            marker.set_opacity(0)
        elif not hidden and "_occlusion_style" in marker.__dict__:
            for member, style in marker.__dict__.pop("_occlusion_style"):
                member.set_style(**style)
