"""Plain-Manim twins and a probing scene: the oracles of the Manim-layer tests.

A **twin** is a plain `VMobject` with a library leaf's points and style; a group of
twins given the same operation as the library objects shows where Manim would leave
them. A **probe** runs a scene in a dry run and records a value on every rendered frame.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import numpy as np
from manim import Mobject, Scene, VGroup, VMobject, tempconfig
from scipy.spatial import cKDTree  # type: ignore[import-untyped]

MEDIA = Path(__file__).parents[1] / "visual" / "_out" / "media"
RUN = {
    "dry_run": True,
    "disable_caching": True,
    "progress_bar": "none",
    "media_dir": str(MEDIA),
    "frame_rate": 6,
    "pixel_width": 427,
    "pixel_height": 240,
}


def plain(mob: VMobject) -> VMobject:
    """A plain `VMobject` with ``mob``'s points and style."""
    twin = VMobject()
    twin.set_points(np.array(mob.points, copy=True))
    twin.match_style(mob)
    return twin


def visible_leaves(ax: Any) -> list[VMobject]:
    """The system's leaves with points, the hidden frame excluded."""
    return [m for m in ax.get_family() if m is not ax.frame and m.has_points()]


def twins(*mobs: Any) -> list[VMobject]:
    """A twin of every leaf with points of every mobject given, in order."""
    out = []
    for mob in mobs:
        leaves = (
            visible_leaves(mob)
            if hasattr(mob, "frame")
            else [m for m in mob.get_family() if m.has_points()]
        )
        out.extend(plain(m) for m in leaves)
    return out


def assert_same(
    ours: Sequence[Mobject], theirs: Sequence[Mobject], atol: float = 1e-9
) -> None:
    assert len(ours) == len(theirs)
    for a, b in zip(ours, theirs, strict=True):
        np.testing.assert_allclose(a.points, b.points, rtol=0, atol=atol)


def dense(points: np.ndarray, per_curve: int = 16) -> np.ndarray:
    """Points along a VMobject's cubic curves, ``per_curve`` per curve."""
    curves = np.asarray(points).reshape(-1, 4, 3)
    s = np.linspace(0, 1, per_curve)[:, None, None]
    p0, p1, p2, p3 = (curves[:, k][None] for k in range(4))
    out = (
        (1 - s) ** 3 * p0
        + 3 * (1 - s) ** 2 * s * p1
        + 3 * (1 - s) * s**2 * p2
        + s**3 * p3
    )
    return np.asarray(out).reshape(-1, 3)


def along(points: np.ndarray, per_curve: int = 64) -> np.ndarray:
    """Points along a VMobject's cubic curves in path order, ``per_curve`` per curve
    (`dense` returns the same points in another order, fine for sets)."""
    n = np.asarray(points).reshape(-1, 4, 3).shape[0]
    return (
        dense(points, per_curve)
        .reshape(per_curve, n, 3)
        .transpose(1, 0, 2)
        .reshape(-1, 3)
    )


def assert_same_curve(a: np.ndarray, b: np.ndarray, atol: float) -> None:
    """Two curves trace the same set within ``atol``, however they are sampled."""
    pa, pb = dense(a), dense(b)
    ab = cKDTree(pb).query(pa)[0].max()
    ba = cKDTree(pa).query(pb)[0].max()
    assert max(ab, ba) <= atol, (ab, ba)


def probe(
    construct: Callable[[Scene], Any], record: Callable[[], Any], **config: Any
) -> list[Any]:
    """Run ``construct`` and return ``record()`` after every frame's update."""
    records: list[Any] = []

    class ProbeScene(Scene):
        def construct(self) -> None:
            construct(self)

        def update_to_time(self, t: float) -> None:
            super().update_to_time(t)
            records.append(record())

    with tempconfig(RUN | config):
        ProbeScene().render()
    return records


def scene() -> Scene:
    """A scene to call methods on, outside a render; use inside `tempconfig(RUN)`."""
    return Scene()


def group(*mobs: VMobject) -> VGroup:
    return VGroup(*mobs)
