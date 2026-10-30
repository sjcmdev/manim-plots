"""Task 21: the field source, the region payload's values and the RK4 step.

Rows FS-1 and FS-3 of `docs/acceptance/21-fields-flow.md`.
"""

from __future__ import annotations

import numpy as np
import pytest

from manim_plots.core.payload import Payload
from manim_plots.core.sources import rk4_step


def rotation(points):
    points = np.asarray(points, dtype=float)
    return np.column_stack((-points[:, 1], points[:, 0]))


def grid(rows: int, cols: int) -> np.ndarray:
    ys, xs = np.mgrid[0:rows, 0:cols]
    return np.column_stack((xs.ravel(), ys.ravel())).astype(float)


def test_fs1_values_default_to_none_on_every_payload():
    assert Payload.path(np.zeros((3, 2))).values is None


def test_fs1_a_region_carries_vectors_or_scalars():
    coords = grid(3, 4)
    segments = np.array([[0, 12]])
    vectors = Payload(
        kind="region",
        coords=coords,
        segments=segments,
        topology=(3, 4),
        values=np.ones((12, 2)),
    )
    assert vectors.values is not None and vectors.values.shape == (12, 2)
    scalars = Payload(
        kind="region",
        coords=coords,
        segments=segments,
        topology=(3, 4),
        values=np.arange(12.0),
    )
    assert scalars.values is not None and scalars.values.shape == (12,)


def test_fs1_values_of_the_wrong_length_raise():
    with pytest.raises(ValueError, match="values"):
        Payload(
            kind="region",
            coords=grid(3, 4),
            segments=np.array([[0, 12]]),
            topology=(3, 4),
            values=np.ones((11, 2)),
        )


def test_fs3_one_rk4_step_is_the_classical_one():
    p = np.array([[1.0, 0.0], [0.3, -0.7]])
    dt = 0.1
    k1 = rotation(p)
    k2 = rotation(p + dt / 2 * k1)
    k3 = rotation(p + dt / 2 * k2)
    k4 = rotation(p + dt * k3)
    expected = p + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
    np.testing.assert_allclose(rk4_step(rotation, p, dt), expected, atol=1e-15)


def test_fs3_an_orbit_closes_after_one_period():
    p = np.array([[1.0, 0.0]])
    steps = 1000
    for _ in range(steps):
        p = rk4_step(rotation, p, 2 * np.pi / steps)
    np.testing.assert_allclose(p, [[1.0, 0.0]], atol=1e-6)
