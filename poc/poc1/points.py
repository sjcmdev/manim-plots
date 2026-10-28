"""Disposable experiment, deliberately not a library API."""

import json
import warnings
from collections import Counter
from pathlib import Path
from time import perf_counter_ns

import numpy as np
from manim import Mobject, UpdateFromAlphaFunc, VMobject, override_animate

ROOT = Path(__file__).resolve().parent
METRICS = Counter()


def record(name, value):
    folder = ROOT / "results"
    folder.mkdir(exist_ok=True)
    (folder / f"{name}.json").write_text(
        json.dumps(value, indent=2, default=float) + "\n", encoding="utf-8"
    )


def place(points, nodes):
    for kind, node in nodes:
        if kind == "affine":
            matrix, offset = node
            points = points @ matrix.T + offset
        else:
            points = node(points)
    return points


class System:
    def __init__(self):
        self.matrix = np.diag([0.8, 0.6, 1.0])
        self.placement = []
        self.version = 0
        self.leaves = []  # Registration, not Manim parenting; exposes deepcopy cost.

    def append(self, kind, node):
        if kind == "affine" and self.placement and self.placement[-1][0] == kind:
            old_matrix, old_offset = self.placement[-1][1]
            matrix, offset = node
            self.placement[-1] = (
                kind,
                (matrix @ old_matrix, matrix @ old_offset + offset),
            )
        else:
            self.placement.append((kind, node))
        self.version += 1

    def c2p(self, points):
        return place(np.asarray(points) @ self.matrix.T, self.placement)

    def rotate(self, angle):
        return rotate_system(self, angle)


class Leaf(VMobject):
    def __init__(self, source, system=None, variant="A", **kwargs):
        super().__init__(**kwargs)
        self.source = np.array(source, copy=True)
        self.source.flags.writeable = False
        self.system = system if system is not None else System()
        self.system.leaves.append(self)
        self.variant = variant
        self.amplitude = 1.0
        self._dirty = True
        self._seen_version = -1
        self._transient = False
        self._suspend_calls = 0
        self._ready = True
        self._rebuild()

    def __setattr__(self, name, value):
        state = self.__dict__
        if (
            name == "amplitude"
            and state.get("_ready", False)
            and value != state.get(name)
        ):
            state["_dirty"] = True
        super().__setattr__(name, value)

    def derived(self):
        points = self.source * np.array([1.0, self.amplitude, 1.0])
        return self.system.c2p(points)

    def _rebuild(self):
        start = perf_counter_ns()
        self._cache = self.derived()
        self._shadow = self._cache.copy()
        self._dirty = False
        self._seen_version = self.system.version
        METRICS["rebuild_ns"] += perf_counter_ns() - start
        METRICS["rebuilds"] += 1

    def _clean(self):
        start = perf_counter_ns()
        clean = np.array_equal(self._cache, self._shadow)
        METRICS["shadow_ns"] += perf_counter_ns() - start
        METRICS["shadow_calls"] += 1
        return clean

    @property
    def points(self):
        METRICS["getters"] += 1
        if self.__dict__.get("_ready", False):
            clean = self._clean()
            if (
                not self._transient
                and clean
                and (self._dirty or self._seen_version != self.system.version)
            ):
                self._rebuild()
        return self._cache

    @points.setter
    def points(self, points):
        state = self.__dict__
        if not state.get("_ready", False):
            METRICS["bootstrap_sets"] += 1
        elif (
            state.get("_owned_affine") is not None and points.shape == self._cache.shape
        ):
            self.system.append("affine", self._owned_affine)
            self._rebuild()
            return
        self._cache = np.asarray(points)

    def refresh(self):
        self._rebuild()
        return self

    def _temporary_geometry(self):
        return self._transient or not self._clean()

    def _geometry(self, function, affine=None):
        points = self.points
        if self._temporary_geometry():
            warnings.warn(
                "Transient geometry; use refresh() before reusing data.", stacklevel=3
            )
            self.points = function(points)
        elif affine is not None:
            self._owned_affine = affine
            try:
                self.points = function(points)
            finally:
                self._owned_affine = None
        else:
            self.system.append("function", function)
            self._rebuild()
        return self

    def shift(self, *vectors):
        vector = np.sum(vectors, axis=0)
        return self._geometry(lambda points: points + vector, (np.eye(3), vector))

    def apply_points_function_about_point(
        self, func, about_point=None, about_edge=None
    ):
        if about_point is None:
            about_point = self.get_critical_point(
                np.zeros(3) if about_edge is None else about_edge
            )
        pivot = np.array(about_point, copy=True)

        def function(points):
            return func(points - pivot) + pivot

        # This is only a probe, not a general affine-recognition algorithm.
        probes = np.vstack([np.zeros(3), np.eye(3), -np.eye(3), [2, 3, 4]])
        output = function(probes)
        offset = output[0]
        matrix = (output[1:4] - offset).T
        affine = None
        if np.allclose(output, probes @ matrix.T + offset, rtol=1e-12, atol=1e-12):
            affine = (matrix, offset)
        return self._geometry(function, affine)

    def suspend_updating(self, recursive=True):
        self._suspend_calls += 1
        if self.variant == "B":
            self._transient = True
            METRICS["suspends"] += 1
        return super().suspend_updating(recursive)

    def resume_updating(self, recursive=True):
        if self.variant == "B":
            self._transient = False
            if self._dirty or self._seen_version != self.system.version:
                self._rebuild()
        return super().resume_updating(recursive)


class OverrideLeaf(Leaf):
    def shift(self, *vectors):
        return super().shift(*vectors)

    @override_animate(shift)
    def _animate_shift(self, *vectors, anim_args=None):
        vector = np.sum(vectors, axis=0)
        initial = list(self.system.placement)

        def update(_mob, alpha):
            self.system.placement = list(initial)
            self.system.append("affine", (np.eye(3), alpha * vector))
            # This animation owns the live placement parameter, not a point buffer.
            self._rebuild()

        return UpdateFromAlphaFunc(self, update, **(anim_args or {}))


def curve(samples=31, phase=0.0):
    x = np.linspace(-3, 3, samples)
    return VMobject().set_points_as_corners(np.c_[x, np.sin(x + phase), x * 0]).points


def rotate_system(system, angle):
    matrix = np.array(
        [
            [np.cos(angle), -np.sin(angle), 0],
            [np.sin(angle), np.cos(angle), 0],
            [0, 0, 1],
        ]
    )
    system.append("affine", (matrix, np.zeros(3)))
    return matrix


def nonlinear(point):
    return point + np.array([0, 0.15 * point[0] ** 2, 0])


def pointwise_nonlinear(leaf):
    # Control: bypass VMobject's handle preconditioning, keeping the two PLAN hooks.
    return Mobject.apply_function(leaf, nonlinear)
