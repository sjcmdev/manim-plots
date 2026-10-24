import copy
import json
import weakref
from collections import Counter
from pathlib import Path
from time import perf_counter_ns

import numpy as np
from manim import GrowFromCenter, VGroup, VMobject, config
from manim.utils.paths import straight_path
from scipy.sparse import csr_matrix
from scipy.spatial import cKDTree

from poc4.context import (
    affine_context,
    animation_context,
    handle_write,
    playback_context,
    writer_context,
)

ROOT = Path(__file__).resolve().parent
METRICS = Counter()
SIMULATING = False
STRAIGHT = straight_path()


class Multiple:
    def __init__(self, step=1):
        self.step = step

    def values(self, limits):
        lo, hi = limits
        return (
            np.arange(
                np.ceil(lo / self.step - 1e-12), np.floor(hi / self.step + 1e-12) + 1
            )
            * self.step
        )

    def key(self, value):
        return round(value / self.step)


class MaxN:
    def __init__(self, count=7):
        self.count = count

    def values(self, limits):
        raw = np.ptp(limits) / (self.count - 1)
        base = 10 ** np.floor(np.log10(raw))
        step = next(f * base for f in [1, 2, 5, 10] if f * base >= raw * (1 - 1e-12))
        return Multiple(step).values(limits)

    def key(self, value):
        return round(float(value), 12)


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
    points = np.asarray(points)
    result = np.empty((len(points) - 1, 4, 3))
    for k, t in enumerate(np.linspace(0, 1, 4)):
        result[:, k] = (1 - t) * points[:-1] + t * points[1:]
    return result.reshape(-1, 3)


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
        nodes = np.c_[x.ravel(), y.ravel(), x.ravel() * 0]
        # Each sample is a degenerate cubic, keeping VMobject's 4-point invariant.
        self.reference = np.repeat(nodes, 4, axis=0)
        self.points = self.reference.copy()
        indices = np.array([0, n - 1, n * (n - 1)]) * 4
        self.probes = indices
        self.probe_inverse = np.linalg.inv(
            np.c_[self.reference[indices, :2], np.ones(3)]
        )
        self.seen = None
        self.version = 0
        self.force_bilinear = False
        self.owner = None
        self.context_events = []
        self._suspensions = []
        self._indptr = {}

    def interpolate(self, start, target, alpha, path_func=STRAIGHT):
        result = super().interpolate(start, target, alpha, path_func)
        if self.owner is not None and self.owner._keyed_animation:
            self.owner._pool_alpha = alpha
            self.owner.x_range = (
                1 - alpha
            ) * start.owner.x_range + alpha * target.owner.x_range
            self.owner.update_pool()
        return result

    def snapshot(self):
        result = copy.copy(self)
        result.points = self.points.copy()
        result.seen = None
        result.owner = None
        result._suspensions = []
        return result

    def suspend_updating(self, recursive=True):
        if not SIMULATING and self.owner is not None:
            start = perf_counter_ns()
            animation, line = animation_context()
            stack_ns = perf_counter_ns() - start
            if animation is not None:
                start = perf_counter_ns()
                permanent = self.simulate(animation)
                simulation_ns = perf_counter_ns() - start
                family = animation.mobject.get_family()
                excluded = set(family)
                frozen = self.snapshot() if not permanent else None
                self._suspensions.append((animation, frozen, excluded))
                self.refresh_bindings()
                self.context_events.append(
                    {
                        "animation": type(animation).__name__,
                        "line": line,
                        "permanent": permanent,
                        "stack_ns": stack_ns,
                        "simulation_ns": simulation_ns,
                        "playback": playback_context(),
                        "excluded_artists": sum(
                            a in excluded for a in self.owner.artists
                        ),
                    }
                )
        return super().suspend_updating(recursive)

    def resume_updating(self, recursive=True):
        if not SIMULATING and self.owner is not None:
            animation, _ = animation_context(finishing=True)
            self._suspensions = [
                entry for entry in self._suspensions if entry[0] is not animation
            ]
            self.refresh_bindings()
        return super().resume_updating(recursive)

    def refresh_bindings(self):
        for artist in self.owner.artists:
            artist._frozen_frame = None
            for _animation, frozen, excluded in self._suspensions:
                if artist not in excluded:
                    artist._frozen_frame = frozen
            artist._dirty = True

    def simulate(self, animation):
        global SIMULATING
        memo = {}
        SIMULATING = True
        try:
            clone = copy.deepcopy(animation, memo)
            frame = memo.get(id(self))
            if frame is None:
                return False
            initial = frame.points.copy()
            limits = frame.owner.x_range.copy()
            scene = SimulationScene()
            clone._setup_scene(scene)
            clone.begin()
            clone.finish()
            clone.clean_up_from_scene(scene)
            return not (
                frame.points.shape == initial.shape
                and np.allclose(frame.points, initial, rtol=0, atol=1e-9)
                and np.array_equal(frame.owner.x_range, limits)
            )
        finally:
            SIMULATING = False

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

    def get_anchors(self):
        # Hidden grid nodes must not participate in visible bounds or pivots.
        return []

    def check(self):
        start = perf_counter_ns()
        same = self.seen is not None and np.array_equal(self.points, self.seen)
        METRICS["compare_ns"] += perf_counter_ns() - start
        METRICS["compare_calls"] += 1
        if not same:
            self.seen = self.points.copy()
            self.version += 1
            planar = self.probe_inverse @ self.points[self.probes]
            normal = np.cross(planar[0], planar[1])
            length = np.linalg.norm(normal)
            if length:
                normal /= length
            self.affine = np.vstack([planar[:2], normal, planar[2]])
            self.is_affine = np.allclose(
                np.c_[self.reference, np.ones(len(self.reference))] @ self.affine,
                self.points,
                rtol=1e-12,
                atol=1e-12,
            )
        return self.version

    def weights(self, p):
        METRICS["weight_builds"] += 1
        uv = (p[..., :2] + [3, 2]) * [(self.n - 1) / 6, (self.n - 1) / 4]
        ij = np.clip(np.floor(uv).astype(int), 0, self.n - 2)
        u, v = (uv - ij).T
        index = ij[:, 1] * self.n + ij[:, 0]
        indices = index[:, None] + [0, 1, self.n, self.n + 1]
        weights = np.array([(1 - u) * (1 - v), u * (1 - v), (1 - u) * v, u * v]).T
        if len(p) not in self._indptr:
            self._indptr[len(p)] = np.arange(0, 4 * len(p) + 1, 4, dtype=np.int32)
        return csr_matrix(
            (weights.ravel(), indices.ravel(), self._indptr[len(p)]),
            shape=(len(p), self.n**2),
        )

    def forward(self, points, weights=None, *, checked=False):
        if not checked:
            self.check()
        p = np.asarray(points)
        if self.is_affine and not self.force_bilinear:
            return p @ self.affine[:3] + self.affine[3]
        single = p.ndim == 1
        p = np.atleast_2d(p)
        weights = self.weights(p) if weights is None else weights
        mapped = weights @ self.points[::4]
        mapped += p[:, 2, None] * self.affine[2]
        return mapped[0] if single else mapped

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
    def __init__(self, n=17, sync=True, ticks=10, locator=None):
        super().__init__()
        self.locator = locator
        self._keyed_animation = False
        self.pool_evidence = []
        self.artists = weakref.WeakSet()
        self.frame = Frame(n)
        self.frame.owner = self
        self.x_range = np.array([-3.0, 3.0])
        self.add(self.frame)
        self.add(Derived(path([[-3, 0, 0], [3, 0, 0]]), self))
        self.add(Derived(path([[0, -2, 0], [0, 2, 0]]), self))
        for x in np.linspace(-3, 3, ticks):
            self.add(Derived(path([[x, -0.06, 0], [x, 0.06, 0]]), self))
        if locator is not None:
            self.submobjects = [self.frame]
            self.add(Decoration(("x-axis",), self), Decoration(("y-axis",), self))
            self.update_pool(trim=True)
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
        if self.locator is not None:
            self.update_pool(trim=not self._keyed_animation)
        return self

    def values_by_key(self, limits=None):
        values = self.locator.values(self.x_range if limits is None else limits)
        keyed = {self.locator.key(v): float(v) for v in values}
        if len(keyed) != len(values):
            raise ValueError("Locator emitted duplicate keys")
        return keyed

    def update_pool(self, trim=False):
        if self.locator is None:
            return
        active = self.values_by_key()
        existing = {m.role: m for m in self.submobjects if isinstance(m, Decoration)}
        roles = [("x-axis",), ("y-axis",)]
        for key in sorted(active):
            roles.append(("tick", key))
            if key in {-2, 0, 2}:
                roles.append(("label", key))
        if trim:
            self.submobjects = [self.frame] + [
                existing[role] if role in existing else Decoration(role, self)
                for role in roles
            ]
        for leaf in self.submobjects[1:]:
            if isinstance(leaf, Decoration):
                leaf.configure(active)

    def align_data(self, mobject, skip_point_alignment=False):
        animation, _ = animation_context(transform_only=True)
        if animation is None or not isinstance(mobject, System) or self.locator is None:
            return super().align_data(mobject, skip_point_alignment)
        start = perf_counter_ns()
        count = max(1, int(np.ceil(animation.run_time * config.frame_rate)))
        keys = set()
        presence = []
        for t in np.linspace(0, 1, count + 1):
            alpha = animation.rate_func(t)
            limits = (1 - alpha) * self.x_range + alpha * mobject.x_range
            current = self.values_by_key(limits)
            keys.update(current)
            presence.append((float(alpha), set(current)))
        keys.update(self.values_by_key())
        keys.update(mobject.values_by_key())
        roles = [("x-axis",), ("y-axis",)]
        for key in sorted(keys):
            roles.append(("tick", key))
            if key in {-2, 0, 2}:
                roles.append(("label", key))
        for system in [self, mobject]:
            existing = {
                m.role: m for m in system.submobjects if isinstance(m, Decoration)
            }
            system.submobjects = [system.frame] + [
                existing[role] if role in existing else Decoration(role, system)
                for role in roles
            ]
            system._keyed_animation = True
            system._pool_alpha = 0 if system is self else 1
            system._pool_presence = presence
            system.update_pool()
        self.pool_evidence.append(
            {
                "samples": count + 1,
                "keys": sorted(keys),
                "align_ns": perf_counter_ns() - start,
            }
        )
        return self

    def resume_updating(self, recursive=True):
        result = super().resume_updating(recursive)
        if self._keyed_animation:
            self._keyed_animation = False
            self.update_pool(trim=True)
        return result

    def plot(self, function=np.sin, samples=101, tracker=None, split=False, sync=True):
        artist = Artist(
            source(samples, function, split), self, tracker=tracker, sync=sync
        )
        xs = (
            [np.linspace(-3, -0.15, samples // 2), np.linspace(0.15, 3, samples // 2)]
            if split
            else [np.linspace(-3, 3, samples)]
        )
        for x in xs:
            x.flags.writeable = False
        artist.binding = (function, xs)
        return artist

    def __deepcopy__(self, memo):
        result = type(self).__new__(type(self))
        memo[id(self)] = result
        result.artists = weakref.WeakSet()
        for key, value in self.__dict__.items():
            if key != "artists":
                setattr(result, key, copy.deepcopy(value, memo))
        for artist in tuple(self.artists):
            if id(artist) in memo:
                clone = memo[id(artist)]
                clone.system.artists.discard(clone)
                clone.system = result
                result.artists.add(clone)
        return result


class SimulationScene:
    def __init__(self):
        self.mobjects = []

    def add(self, *mobjects):
        self.mobjects.extend(mobjects)

    def remove(self, *mobjects):
        self.mobjects = [m for m in self.mobjects if m not in mobjects]

    def replace(self, old, new):
        self.remove(old)
        self.add(new)

    def get_mobject_family_members(self):
        return [leaf for mob in self.mobjects for leaf in mob.get_family()]


def sync_updater(mob):
    if isinstance(mob, Artist) and mob.binding is not None and not mob.detached:
        context = playback_context()
        if context is None or context != mob._poll_frame:
            mob._source_dirty = True
            mob._poll_frame = context
            if context is None or len(context) == 3:
                mob.rebuild()


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
        self._frozen_frame = None
        self._weights = None
        self._sample_key = None
        self._local = None
        self._placement_version = 0
        self.binding = None
        self._source_dirty = False
        self.source_version = 0
        self.writer_events = []
        self.suspend_events = []
        self._poll_frame = None
        self.rebuild()

    def data_points(self):
        if self._source_dirty:
            function, xs = self.binding
            result = self.source.copy()
            offset = 0
            for x in xs:
                y = function(x)
                count = 4 * (len(x) - 1)
                handles = result[offset : offset + count, 1].reshape(-1, 4)
                for k, t in enumerate(np.linspace(0, 1, 4)):
                    handles[:, k] = (1 - t) * y[:-1] + t * y[1:]
                offset += count
            result.flags.writeable = False
            self.source = result
            self.source_version += 1
            self._source_dirty = False
            METRICS["source_samples"] += 1
        return self.source * [1, self.tracker.get_value() if self.tracker else 1, 1]

    def frame(self):
        return self._frozen_frame or self.system.frame

    def derived(self):
        sparse = not isinstance(self, Artist) and len(self.source) == 4
        if sparse:
            self.frame().check()
        dense = sparse and not self.frame().is_affine
        sample_key = (
            id(self.source),
            self.source_version,
            tuple(self.system.x_range),
            self.tracker.get_value() if self.tracker else 1,
            self._placement_version,
            dense,
        )
        if self._source_dirty or sample_key != self._sample_key:
            p = self.data_points()
            if dense:
                p = path(np.linspace(p[0], p[-1], 65))
            p[:, 0] = (p[:, 0] - self.system.x_range[0]) * 6 / np.ptp(
                self.system.x_range
            ) - 3
            for operation in self.placement:
                p = (
                    operation(p)
                    if callable(operation)
                    else p @ operation[:3] + operation[3]
                )
            self._local = p
            self._weights = self.frame().weights(p)
            self._sample_key = (
                id(self.source),
                self.source_version,
                tuple(self.system.x_range),
                self.tracker.get_value() if self.tracker else 1,
                self._placement_version,
                dense,
            )
        return self.frame().forward(self._local, self._weights, checked=sparse)

    def key(self):
        return (
            id(self.frame()),
            self.frame().check(),
            self.source_version,
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
        if handle_write():
            return self._cache
        if (
            self.__dict__.get("_ready", False)
            and not self._transient
            and not self.detached
            and (self._dirty or self._source_dirty or self.key() != self._key)
        ):
            self.rebuild()
        return self._cache

    @points.setter
    def points(self, value):
        self._cache = np.asarray(value)
        if self.__dict__.get("_ready", False):
            if not self._transient and not self.detached:
                self._dirty = True
            start = perf_counter_ns()
            context = writer_context()
            elapsed = perf_counter_ns() - start
            if context is not None:
                contains_frame = self.system.frame in context["container"].get_family()
                self.writer_events.append(
                    {
                        "kind": context["kind"],
                        "line": context["line"],
                        "container": type(context["container"]).__name__,
                        "contains_frame": contains_frame,
                        "stack_ns": elapsed,
                        "transient": self._transient,
                        "container_contains_leaf": self
                        in context["container"].get_family(),
                    }
                )
                if (
                    context["last"]
                    and not contains_frame
                    and not self._transient
                    and isinstance(self, Artist)
                ):
                    self.capture(context)

    def suspend_updating(self, recursive=True):
        animation, _ = animation_context()
        if self.detached and animation is not None and animation.is_introducer():
            self.refresh()
            if isinstance(animation, GrowFromCenter):
                # Its constructor captured the detached buffer's obsolete center.
                animation.point = self.get_center()
            animation.starting_mobject = animation.create_starting_mobject()
            if hasattr(animation, "get_outline"):
                animation.outline = animation.get_outline()
        if not SIMULATING:
            start = perf_counter_ns()
            animation, line = animation_context()
            elapsed = perf_counter_ns() - start
            self.suspend_events.append(
                {
                    "animation": type(animation).__name__ if animation else None,
                    "line": line,
                    "stack_ns": elapsed,
                    "playback": playback_context(),
                    "animation_contains_leaf": animation is not None
                    and self in animation.mobject.get_family(),
                }
            )
        self._transient = True
        return super().suspend_updating(recursive)

    def resume_updating(self, recursive=True):
        animation, _ = animation_context(finishing=True)
        if (
            isinstance(self, Artist)
            and animation is not None
            and animation.is_remover()
        ):
            self.detached = True
            self._candidate = None
            self._transient = False
            return super().resume_updating(recursive)
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
        if not self.detached:
            self.rebuild()
        return super().resume_updating(recursive)

    def align_data(self, mobject, skip_point_alignment=False):
        animation, _ = animation_context(transform_only=True)
        if self.detached and animation is not None and animation.is_introducer():
            self.refresh()
            # Align refreshed buffers early, but attach at the suspension boundary.
            self.detached = True
            if isinstance(mobject, Derived):
                mobject.refresh()
        if animation is not None:
            if not self._transient:
                _ = self.points
            self._transient = True
            if isinstance(mobject, Derived):
                if not mobject._transient:
                    _ = mobject.points
                mobject._transient = True
        result = super().align_data(mobject, skip_point_alignment)
        if animation is None or not animation.remover:
            self._candidate = mobject.copy()
        return result

    def adopt(self, other):
        if isinstance(other, Derived):
            self.source = other.source
            self.tracker = other.tracker
            self.placement = list(other.placement)
            self.detached = other.detached
            self.binding = other.binding
            self.source_version = other.source_version
        else:
            self.source = self.system.p2c(other.points)
            self.tracker = None
            self.placement = []
            self.detached = True
            self.binding = None
        self._placement_version += 1
        self._sample_key = None
        self._source_dirty = False
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
            if key in {"source", "tracker", "binding"}:
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

    def refresh(self):
        self.detached = False
        self._transient = False
        self._source_dirty = self.binding is not None
        self._sample_key = None
        return self.rebuild()


class Decoration(Derived):
    """A role/key leaf; labels use small corner paths without TeX."""

    def __init__(self, role, system):
        self.role = role
        self.value = role[1] if len(role) > 1 else 0
        self.active = True
        super().__init__(path([[0, 0, 0], [0, 0.1, 0]]), system)

    def configure(self, active):
        kind = self.role[0]
        lo, hi = self.system.x_range
        if kind == "x-axis":
            corners = [[lo, 0, 0], [hi, 0, 0]]
        elif kind == "y-axis":
            corners = [[0, -2, 0], [0, 2, 0]]
        else:
            self.active = self.role[1] in active
            self.value = active.get(self.role[1], self.value)
            x = self.value
            corners = (
                [[x, -0.06, 0], [x, 0.06, 0]]
                if kind == "tick"
                else [[x - 0.04, -0.16, 0], [x, -0.23, 0], [x + 0.04, -0.16, 0]]
            )
            # Keep the user's color and width; visibility belongs to the pool.
            opacity = float(self.active)
            if self.active and self.system._keyed_animation:
                alpha = self.system._pool_alpha
                absent = [
                    abs(alpha - t)
                    for t, keys in self.system._pool_presence
                    if self.role[1] not in keys
                ]
                if absent and alpha not in {0, 1}:
                    opacity = min(
                        1.0,
                        min(absent) * max(1, len(self.system._pool_presence) - 1) / 1.5,
                    )
            self.set_stroke(opacity=opacity, family=False)
        self.source = path(corners)
        self._sample_key = None
        self._dirty = True

    def interpolate(self, start, target, alpha, path_func=STRAIGHT):
        if self.system._keyed_animation:
            self._cache = self.derived()
            return self
        return super().interpolate(start, target, alpha, path_func)


class Artist(Derived):
    def __init__(self, data, system, tracker=None, sync=True):
        super().__init__(data, system, stroke_width=2)
        self.tracker = tracker
        system.artists.add(self)
        if sync:
            self.add_updater(sync_updater)

    def geometry(self, function, affine=None):
        if self._transient or self.detached:
            self._cache = function(self._cache)
        else:
            frame = self.frame().snapshot()
            frame.check()
            if frame.is_affine and affine is not None:
                inverse = np.linalg.inv(frame.affine[:3])
                operation = np.vstack(
                    [
                        frame.affine[:3] @ affine[:3] @ inverse,
                        (frame.affine[3] @ affine[:3] + affine[3] - frame.affine[3])
                        @ inverse,
                    ]
                )
                if self.placement and not callable(self.placement[-1]):
                    previous = self.placement.pop()
                    operation = np.vstack(
                        [
                            previous[:3] @ operation[:3],
                            previous[3] @ operation[:3] + operation[3],
                        ]
                    )
            else:

                def operation(points):
                    return frame.inverse(function(frame.forward(points)))

            self.placement.append(operation)
            self._placement_version += 1
            self.rebuild()
        return self

    def capture(self, context):
        if context["kind"] == "shift":
            vector = context["vector"].copy()
            self.geometry(
                lambda points: points + vector, np.vstack([np.eye(3), vector])
            )
        elif context["application"] is not None:
            container, function = context["application"]
            factor = container.pre_function_handle_to_anchor_scale_factor
            smooth = container.make_smooth_after_applying_functions

            def apply(points):
                native = VMobject().set_points(points.copy())
                native.pre_function_handle_to_anchor_scale_factor = factor
                native.make_smooth_after_applying_functions = smooth
                return native.apply_function(function).points

            self.geometry(apply)
        else:
            function, pivot = context["func"], context["pivot"]
            matrix = context["matrix"]
            affine = (
                None if matrix is None else np.vstack([matrix, pivot - pivot @ matrix])
            )
            self.geometry(lambda points: function(points - pivot) + pivot, affine)

    def apply_function(self, function, **kwargs):
        if self._transient:
            return super().apply_function(function, **kwargs)
        factor = self.pre_function_handle_to_anchor_scale_factor
        smooth = self.make_smooth_after_applying_functions

        def apply(points):
            native = VMobject().set_points(points.copy())
            native.pre_function_handle_to_anchor_scale_factor = factor
            native.make_smooth_after_applying_functions = smooth
            return native.apply_function(function, **kwargs).points

        return self.geometry(apply)

    def shift(self, *vectors):
        vector = np.sum(vectors, axis=0)
        return self.geometry(
            lambda points: points + vector, np.vstack([np.eye(3), vector])
        )

    def apply_points_function_about_point(
        self, func, about_point=None, about_edge=None
    ):
        if about_point is None:
            about_point = self.get_critical_point(
                np.zeros(3) if about_edge is None else about_edge
            )
        pivot = np.array(about_point, copy=True)
        matrix = affine_context()
        affine = None if matrix is None else np.vstack([matrix, pivot - pivot @ matrix])
        return self.geometry(lambda points: func(points - pivot) + pivot, affine)
