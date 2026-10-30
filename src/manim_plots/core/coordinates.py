"""NumPy conversions using ISO polar and azimuth angles."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike

from manim_plots.core import FloatArray


def spherical_to_cartesian(
    r: ArrayLike, theta: ArrayLike, phi: ArrayLike
) -> FloatArray:
    """Convert radius, polar angle and azimuth to Cartesian columns.

    Parameters
    ----------
    r, theta, phi
        Broadcastable radii and angles in radians.

    Returns
    -------
    FloatArray
        Cartesian coordinates with coordinate axis first.
    """
    radius, polar, azimuth = np.broadcast_arrays(r, theta, phi)
    return np.asarray(
        [
            radius * np.sin(polar) * np.cos(azimuth),
            radius * np.sin(polar) * np.sin(azimuth),
            radius * np.cos(polar),
        ]
    )


def cartesian_to_spherical(points: ArrayLike) -> FloatArray:
    """Convert Cartesian rows to radius, polar angle and azimuth.

    Parameters
    ----------
    points
        Cartesian triples with coordinate axis last.

    Returns
    -------
    FloatArray
        Spherical triples, with zero angles at the origin.
    """
    p = np.asarray(points, dtype=float)
    r = np.linalg.norm(p, axis=-1)
    cosine = np.divide(p[..., 2], r, out=np.ones_like(r), where=r != 0)
    return np.stack(
        (
            r,
            np.arccos(np.clip(cosine, -1, 1)),
            np.where(r == 0, 0, np.arctan2(p[..., 1], p[..., 0])),
        ),
        axis=-1,
    )


def cylindrical_to_cartesian(
    rho: ArrayLike, phi: ArrayLike, z: ArrayLike
) -> FloatArray:
    """Convert cylindrical coordinates to Cartesian columns.

    Parameters
    ----------
    rho, phi, z
        Broadcastable radius, azimuth in radians and height.

    Returns
    -------
    FloatArray
        Cartesian coordinates with coordinate axis first.
    """
    radius, azimuth, height = np.broadcast_arrays(rho, phi, z)
    return np.asarray([radius * np.cos(azimuth), radius * np.sin(azimuth), height])


def cartesian_to_cylindrical(points: ArrayLike) -> FloatArray:
    """Convert Cartesian rows to cylindrical coordinates.

    Parameters
    ----------
    points
        Cartesian triples with coordinate axis last.

    Returns
    -------
    FloatArray
        Radius, azimuth in radians and height, with coordinate axis last.
    """
    p = np.asarray(points, dtype=float)
    return np.stack(
        (np.hypot(p[..., 0], p[..., 1]), np.arctan2(p[..., 1], p[..., 0]), p[..., 2]),
        axis=-1,
    )
