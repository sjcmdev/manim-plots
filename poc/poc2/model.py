import copy
import json
import weakref
from collections import Counter
from pathlib import Path
from time import perf_counter_ns

import numpy as np
from manim import VGroup, VMobject
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parent
METRICS = Counter()


def record(name, value):
    folder = ROOT / "results"
    folder.mkdir(exist_ok=True)
    (folder / f"{name}.json").write_text(
        json.dumps(value, indent=2, default=float) + "\n", encoding="utf-8"
    )


def error(a, b):
    if np.shape(a) != np.shape(b):
        a, b = np.asarray(a).reshape(-1, 3), np.asarray(b).reshape(-1, 3)
        return float(max(cKDTree(a).query(b)[0].max(), cKDTree(b).query(a)[0].max()))
    return float(np.max(np.linalg.norm(np.asarray(a) - b, axis=-1), initial=0))


def path(points):
    return VMobject().set_points_as_corners(points).points.copy()


def source(samples=101, function=np.sin, split=False):
    xs = (
        [np.linspace(-3, -0.15, samples // 2), np.linspace(0.15, 3, samples // 2)]
        if split
        else [np.linspace(-3, 3, samples)]
    )
    result = np.concatenate([path(np.c_[x, function(x), x * 0]) for x in xs])
    result.flags.writeable = False
    return result


class Frame(VMobject):
    def __init__(self, n=17):
        self.n = n
        super().__init__()
        x, y = np.meshgrid(np.linspace(-3, 3, n), np.linspace(-2, 2, n))
        nodes = np.vstack([np.c_[x.ravel(), y.ravel(), x.ravel() * 0], [0, 0, 1]])
        # Each sample is a degenerate cubic, keeping VMobject's 4-point invariant.
        self.reference = np.repeat(nodes, 4, axis=0)
        self.points = self.reference.copy()
        indices = np.array([0, n - 1, n * (n - 1), n * n]) * 4
        self.probes = indices
        self.probe_inverse = np.linalg.inv(np.c_[self.reference[indices], np.ones(4)])
        self.seen = None
        self.version = 0
        self.force_bilinear = False

    def set_fill(self, color=None, opacity=None, family=True):
        return super().set_fill(color, 0, family)

    def set_stroke(
        self, color=None, width=None, opacity=None, background=False, family=True
    ):
        return super().set_stroke(color, 0, 0, background, family)

    def interpolate_color(self, *args):
        super().interpolate_color(*args)
        self.set_fill(opacity=0)
        self.set_stroke(width=0, opacity=0)
        self.set_stroke(width=0, opacity=0, background=True)
        return self

    def pointwise_become_partial(self, _other, _a, _b):
        return self

    def check(self):
        start = perf_counter_ns()
        same = self.seen is not None and np.array_equal(self.points, self.seen)
        METRICS["compare_ns"] += perf_counter_ns() - start
        METRICS["compare_calls"] += 1
        if not same:
            self.seen = self.points.copy()
            self.version += 1
            self.affine = self.probe_inverse @ self.points[self.probes]
            self.is_affine = np.allclose(
                np.c_[self.reference, np.ones(len(self.reference))] @ self.affine,
                self.points,
                rtol=1e-12,
                atol=1e-12,
            )
        return self.version

    def forward(self, points):
        self.check()
        p = np.asarray(points)
        if self.is_affine and not self.force_bilinear:
            return p @ self.affine[:3] + self.affine[3]
        uv = (p[..., :2] + [3, 2]) * [(self.n - 1) / 6, (self.n - 1) / 4]
        ij = np.clip(np.floor(uv).astype(int), 0, self.n - 2)
        t = uv - ij
        i, j = ij[..., 0], ij[..., 1]
        u, v = t[..., 0, None], t[..., 1, None]
        grid = self.points[::4][: self.n**2].reshape(self.n, self.n, 3)
        return (
            (1 - u) * (1 - v) * grid[j, i]
            + u * (1 - v) * grid[j, i + 1]
            + (1 - u) * v * grid[j + 1, i]
            + u * v * grid[j + 1, i + 1]
            + p[..., 2, None] * self.affine[2]
        )

    def inverse(self, points):
        self.check()
        p = np.asarray(points)
        if self.is_affine:
            return np.linalg.solve(self.affine[:3].T, (p - self.affine[3]).T).T
        guess = np.linalg.lstsq(self.affine[:3].T, (p - self.affine[3]).T, rcond=None)[
            0
        ].T
        for _ in range(20):
            residual = p - self.forward(guess)
            if np.max(abs(residual)) < 1e-11:
                break
            jac = np.stack(
                [
                    (self.forward(guess + np.eye(3)[k] * 1e-5) - self.forward(guess))
                    / 1e-5
                    for k in range(3)
                ],
                axis=-1,
            )
            delta = np.array(
                [
                    np.linalg.lstsq(j, r, rcond=None)[0]
                    for j, r in zip(jac, residual, strict=True)
                ]
            )
            guess += delta
        return guess


class System(VGroup):
    def __init__(self, n=17, sync=True, ticks=10):
        super().__init__()
        self.artists = weakref.WeakSet()
        self.frame = Frame(n)
        self.x_range = np.array([-3.0, 3.0])
        self.add(self.frame)
        self.add(Derived(path([[-3, 0, 0], [3, 0, 0]]), self))
        self.add(Derived(path([[0, -2, 0], [0, 2, 0]]), self))
        for x in np.linspace(-3, 3, ticks):
            self.add(Derived(path([[x, -0.06, 0], [x, 0.06, 0]]), self))
        if sync:
            self.add_updater(sync_updater)

    def c2p(self, points, y=None):
        if y is not None:
            points = np.array([points, y, 0.0])
        p = np.array(points, dtype=float, copy=True)
        p[..., 0] = (p[..., 0] - self.x_range[0]) * 6 / np.ptp(self.x_range) - 3
        return self.frame.forward(p)

    def p2c(self, points):
        p = self.frame.inverse(np.atleast_2d(points))
        p[..., 0] = (p[..., 0] + 3) * np.ptp(self.x_range) / 6 + self.x_range[0]
        return p

    def set_x_range(self, limits):
        self.x_range = np.array(limits, dtype=float)
        return self

    def plot(self, function=np.sin, samples=101, tracker=None, split=False, sync=True):
        return Artist(
            source(samples, function, split), self, tracker=tracker, sync=sync
        )

    def __deepcopy__(self, memo):
        result = type(self).__new__(type(self))
        memo[id(self)] = result
        result.artists = weakref.WeakSet()
        for key, value in self.__dict__.items():
            if key != "artists":
                setattr(result, key, copy.deepcopy(value, memo))
        for artist in self.artists:
            if id(artist) in memo:
                clone = memo[id(artist)]
                clone.system = result
                result.artists.add(clone)
        return result


def sync_updater(_mob):
    pass


class Derived(VMobject):
    def __init__(self, data, system, **kwargs):
        super().__init__(**kwargs)
        self.source = data
        self.system = system
        self.tracker = None
        self.placement = []
        self.detached = False
        self._transient = False
        self._dirty = True
        self._key = None
        self._candidate = None
        self._ready = True
        self.rebuild()

    def data_points(self):
        return self.source * [1, self.tracker.get_value() if self.tracker else 1, 1]

    def derived(self):
        p = self.system.c2p(self.data_points())
        for function in self.placement:
            p = function(p)
        return p

    def key(self):
        return (
            self.system.frame.check(),
            tuple(self.system.x_range),
            self.tracker.get_value() if self.tracker else 1,
        )

    def rebuild(self):
        start = perf_counter_ns()
        self._cache = self.derived()
        self._key = self.key()
        self._dirty = False
        METRICS["rebuild_ns"] += perf_counter_ns() - start
        METRICS["rebuilds"] += 1
        return self

    @property
    def points(self):
        if (
            self.__dict__.get("_ready", False)
            and not self._transient
            and (self._dirty or self.key() != self._key)
        ):
            self.rebuild()
        return self._cache

    @points.setter
    def points(self, value):
        self._cache = np.asarray(value)
        if self.__dict__.get("_ready", False) and not self._transient:
            self._dirty = True

    def suspend_updating(self, recursive=True):
        self._transient = True
        return super().suspend_updating(recursive)

    def resume_updating(self, recursive=True):
        candidate = self._candidate
        if (
            candidate is not None
            and np.shape(self._cache) == np.shape(candidate.points)
            and np.allclose(self._cache, candidate.points, rtol=0, atol=1e-10)
        ):
            self.adopt(candidate)
            METRICS["adoptions"] += 1
        self._candidate = None
        self._transient = False
        self.rebuild()
        return super().resume_updating(recursive)

    def align_data(self, mobject, skip_point_alignment=False):
        result = super().align_data(mobject, skip_point_alignment)
        self._candidate = mobject.copy()
        return result

    def adopt(self, other):
        if isinstance(other, Derived):
            self.source = other.source
            self.tracker = other.tracker
            self.placement = list(other.placement)
            self.detached = other.detached
        else:
            self.source = self.system.p2c(other.points)
            self.tracker = None
            self.placement = []
            self.detached = True
        self.match_style(other)
        self._dirty = True

    def become(self, other, **kwargs):
        if kwargs:
            raise NotImplementedError("PoC tests plain become only")
        self.adopt(other)
        return self.rebuild()

    def __deepcopy__(self, memo):
        result = type(self).__new__(type(self))
        memo[id(self)] = result
        for key, value in self.__dict__.items():
            if key in {"source", "tracker"}:
                setattr(result, key, value)
            elif key == "system":
                result.system = memo.get(id(value), value)
            elif key == "_candidate":
                result._candidate = None
            else:
                setattr(result, key, copy.deepcopy(value, memo))
        if isinstance(result, Artist):
            result.system.artists.add(result)
        return result


class Artist(Derived):
    def __init__(self, data, system, tracker=None, sync=True):
        super().__init__(data, system, stroke_width=2)
        self.tracker = tracker
        system.artists.add(self)
        if sync:
            self.add_updater(sync_updater)

    def geometry(self, function):
        if self._transient:
            self._cache = function(self._cache)
        else:
            self.placement.append(function)
            self.rebuild()
        return self

    def shift(self, *vectors):
        vector = np.sum(vectors, axis=0)
        return self.geometry(lambda points: points + vector)

    def apply_points_function_about_point(
        self, func, about_point=None, about_edge=None
    ):
        if about_point is None:
            about_point = self.get_critical_point(
                np.zeros(3) if about_edge is None else about_edge
            )
        pivot = np.array(about_point, copy=True)
        return self.geometry(lambda points: func(points - pivot) + pivot)
