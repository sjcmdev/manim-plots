"""Task 24c: the box frame's numbers on screen, rows FN of
`docs/acceptance/24c-box-numbers.md`.

The oracle: `ThreeDCamera.project_points`, the projection Manim draws with. Each number
is checked against its projected edge and against every other number's projected
bounding box.
"""

from __future__ import annotations

from itertools import combinations
from typing import Any

import numpy as np
import pytest
from manim import ThreeDScene, tempconfig

import manim_plots as mp

from .helpers import RUN

BUFF = 0.15
VIEWS = [(25, -45), (25, 45), (60, -60), (25, 135), (10, -120)]
SMALL: dict[str, Any] = {
    "x_range": (-2, 2, 1),
    "y_range": (-2, 2, 1),
    "z_range": (-2, 2, 1),
    "x_length": 5,
    "y_length": 5,
    "z_length": 3.5,
}


def shown(mob: Any) -> bool:
    return any(
        m.get_fill_opacity() > 0 or m.get_stroke_opacity() > 0
        for m in mob.family_members_with_points()
    )


def measure(ax: Any, elev: float, azim: float, titles: bool = False) -> dict[str, Any]:
    """Project the box's numbers (and titles) from one view."""
    out: dict[str, Any] = {}
    labels = ax.get_axis_labels() if titles else None

    class Shot(ThreeDScene):
        def construct(self) -> None:
            self.set_camera_orientation(**ax.view(elev, azim))
            self.add(ax)
            if labels is not None:
                self.add(labels)
            self.wait(1 / 6)
            project = self.camera.project_points
            centre = project(np.array([ax.c2p(*[np.mean(r[:2]) for r in ranges])]))
            out["centre"] = centre[0, :2]
            out["axes"] = []
            for axis in (ax.x, ax.y, ax.z):
                edge = project(np.array([axis.get_start(), axis.get_end()]))[:, :2]
                numbers = [
                    project(np.asarray(n.get_all_points()))[:, :2]
                    for n in axis.numbers
                    if shown(n)
                ]
                out["axes"].append((edge, numbers))
            if labels is not None:
                out["titles"] = [
                    project(np.asarray(t.get_all_points()))[:, :2] for t in labels
                ]

    ranges = (ax.x_range, ax.y_range, ax.z_range)
    with tempconfig(RUN):
        Shot().render()
    return out


def signed(points: np.ndarray, edge: np.ndarray, centre: np.ndarray) -> np.ndarray:
    """Distance from the edge line on screen, positive away from the box's centre."""
    a, b = edge
    d = (b - a) / np.linalg.norm(b - a)
    normal = np.array([-d[1], d[0]])
    if (centre - a) @ normal > 0:
        normal = -normal
    out: np.ndarray = (points - a) @ normal
    return out


def boxes_overlap(p: np.ndarray, q: np.ndarray) -> bool:
    return bool(
        p[:, 0].min() < q[:, 0].max()
        and q[:, 0].min() < p[:, 0].max()
        and p[:, 1].min() < q[:, 1].max()
        and q[:, 1].min() < p[:, 1].max()
    )


@pytest.mark.parametrize(("elev", "azim"), VIEWS)
@pytest.mark.parametrize("size", ["small", "default"])
def test_fn1_numbers_sit_outside_their_edge(elev, azim, size):
    ax = mp.ThreeDAxes(frame="box", **(SMALL if size == "small" else {}))
    seen = measure(ax, elev, azim)
    for edge, numbers in seen["axes"]:
        for points in numbers:
            near = signed(points, edge, seen["centre"]).min()
            assert near == pytest.approx(BUFF, abs=0.03)


@pytest.mark.parametrize(("elev", "azim"), VIEWS)
@pytest.mark.parametrize("size", ["small", "default"])
def test_fn2_no_two_numbers_overlap(elev, azim, size):
    ax = mp.ThreeDAxes(frame="box", **(SMALL if size == "small" else {}))
    seen = measure(ax, elev, azim)
    every = [points for _, numbers in seen["axes"] for points in numbers]
    assert len(every) >= 9  # most numbers stay visible
    for p, q in combinations(every, 2):
        assert not boxes_overlap(p, q)


@pytest.mark.parametrize(("elev", "azim"), VIEWS[:3])
def test_fn3_titles_sit_beyond_the_numbers(elev, azim):
    ax = mp.ThreeDAxes(frame="box", **SMALL)
    seen = measure(ax, elev, azim, titles=True)
    numbers = [points for _, group in seen["axes"] for points in group]
    for (edge, group), title in zip(seen["axes"], seen["titles"], strict=True):
        far = max(signed(points, edge, seen["centre"]).max() for points in group)
        assert signed(title, edge, seen["centre"]).min() >= far + BUFF - 0.03
        assert not any(boxes_overlap(title, points) for points in numbers)


def test_fn4_the_origin_frame_keeps_manims_placement():
    ours = mp.ThreeDAxes()
    before = [n.get_center().copy() for n in ours.x.numbers]
    measure(ours, 25, -45)
    after = [n.get_center() for n in ours.x.numbers]
    np.testing.assert_allclose(after, before, atol=1e-9)
