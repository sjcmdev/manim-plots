# ADR 0001 — Architecture of the 0.1 engine

- **Status:** Proposed — drafted 2026-10-23, awaiting the maintainer's grill.
- **Task:** `task/04-architecture` in `TODO.md`.
- **Builds on:** `PLAN.md` (the locked design), `docs/scope.md` (the `F-*` list),
  `docs/grill-log.md` (D1-D16).

## Context

Task 03 decided *what* 0.1 does and most of *how*: the `Source -> Map -> Shape`
pipeline, derived points, the placement chain, keyed identity, the invalid-input rule.
Task 04 has four open items, and this record closes them:

1. the public contracts third parties implement against — scale, locator, formatter;
2. the separation between the data model and the Manim geometry it produces;
3. how a coordinate system survives Manim's geometric transformations;
4. a module layout, which `TODO.md` deferred until scope was closed.

Item 3 is already decided in `PLAN.md` (*Integration: the `points` property on
library-owned leaves*) and is recorded here only by reference. Items 1, 2 and 4 are
new. Choices the maintainer has not seen yet are marked **proposed**; the questions
that need an answer before this record is accepted are collected at the end.

## Decision

### 1. Two layers, and the core never imports Manim

The package splits into a **numeric core** and a **Manim layer**.

- The **core** holds everything that is a function of numbers: the payload, map nodes,
  scales, locators, formatters, sources, `Shape` operations and parameters. It imports
  NumPy and the standard library and nothing else.
- The **Manim layer** holds everything that is a mobject: leaf types with the `points`
  property, the coordinate system, axis decoration, artists, legend and animations. It
  calls the core; the core never calls it.

This is the answer to item 2. It is also what makes the testing strategy in
`CONTRIBUTING.md` affordable: every float-to-float function the defect audit cares
about — scale inverses, tick placement, coordinate conversion — is property-tested with
Hypothesis in milliseconds, without constructing a mobject.

The rule is enforced, not hoped for: a test imports each core module in a fresh
interpreter and asserts that `manim` is not in `sys.modules`.

### 2. Module layout (proposed)

```
src/manim_plots/
    __init__.py       public re-exports; the only import users need
    # numeric core: NumPy only
    payload.py        Payload (F-114) and its construction-time validation
    nodes.py          Node protocol, affine collapse, compiled Map (F-105, F-109)
    scales.py         Scale protocol; Linear, Log, SymLog, FunctionScale (F-3xx)
    ticks.py          Locator protocol; MaxN, Multiple, Log, Fixed, Null, MinorCount (F-4xx)
    formatters.py     Formatter protocol and the 0.1 formatters (F-5xx)
    sources.py        Source protocol; analytic, array and parametric sources (F-7xx)
    shape.py          split at invalid samples, clip, dash (F-106, F-705, F-706, F-806)
    params.py         parameter descriptors and version counters (F-110, F-911)
    # Manim layer
    leaves.py         leaf mobjects carrying the `points` property (F-901..F-905)
    system.py         CoordinateSystem, CartesianAxes; owns Map and placement chain
    axis.py           Axis decoration (F-6xx)
    artists.py        the four 0.1 artists (F-701)
    legend.py         Legend (F-801)
    animations.py     DrawAxes, TraceCurve, ShowPoints, Morph (F-912)
    group.py          mp.Group broadcast handle (F-910)
```

Sixteen modules for 98 requirements. A module is split when it outgrows one reader, not
in advance.

### 3. The contracts

Signatures below are the contract; names are proposed. `FloatArray` is
`numpy.typing.NDArray[np.float64]`. Every contract is a `typing.Protocol`, so a third
party implements it without inheriting from us, and `mypy --strict` checks the
implementation (F-1002).

#### Scale — one dimension, monotonic (F-109, F-301..F-311)

```python
class Scale(Protocol):
    domain: tuple[float, float]   # open interval; +-inf allowed
    increasing: bool              # declared monotonic direction

    def forward(self, x: FloatArray) -> FloatArray: ...   # data -> scaled
    def inverse(self, u: FloatArray) -> FloatArray: ...   # scaled -> data
    def limit_range(self, lo: float, hi: float) -> tuple[float, float]: ...
```

- `forward` is the scale transform and `inverse` its inverse — never the other way
  round (F-303, defect 10).
- Both are vectorized over `ndarray`; a value outside `domain` maps to `NaN`, and the
  *caller* applies the surface rule from `docs/scope.md` (split, drop or raise). The
  scale itself never decides policy.
- `limit_range` is F-311: it normalises a configured range that leaves the domain, and
  is called on range configuration only, never on a conversion (F-202).
- `FunctionScale(forward, inverse, domain, increasing=True)` is how a user supplies a
  scale (F-302). Its constructor runs the sampled falsification of F-305 and raises
  naming the failed property.
- Deliberate ceiling: an open-interval domain cannot include its endpoint, so `sqrt`
  over `[0, inf)` treats `0` as invalid. A closed bound is additive later.

A scale is a value object, not a map node. The coordinate system compiles each scale
into a one-dimensional `Node`, which is where D6's `apply` / `is_affine` / `matrix` /
`inverse` / `domain` contract lives. That reconciles D6 and F-109: F-109 describes what
the *user* supplies, D6 what the *chain* runs.

#### Locator — tick values and their keys (F-401..F-413)

```python
class Locator(Protocol):
    def values(self, lo: float, hi: float, scale: Scale, max_ticks: int) -> FloatArray: ...
    def key(self, value: float) -> Hashable | None: ...
```

- `values` returns tick positions in data space, in axis order: ascending, or
  descending for a reversed range (F-209). `max_ticks` is the label-space estimate of
  F-408: how many labels fit, measured from rendered label size, as matplotlib's
  `get_tick_space` does. A count rather than a length keeps it independent of the
  scale. No `np.arange` over a step anywhere (F-402): `Multiple(step)` computes
  `k * step` from integer `k`.
- `key(value)` is the identity of a tick (F-413, D10). It returns `None` for a value
  this locator would not emit — `Multiple(0.5).key(0.3)` is `None`. That one rule gives
  three mechanisms a common footing:
  - **identity across rebuilds** — a rebuild reuses the mobject whose key survived;
  - **minor-on-major removal** (F-407) — a minor value is dropped when the *major*
    locator returns a key for it that is in the major set;
  - **explicit-over-generated merge** (F-405) — an explicit entry is keyed with the
    generated locator's `key`, and wins on a match; a `None` key simply adds it.
- Major and minor ticks come from two locators on one axis. `Fixed` is the exception:
  its entries are `(value, label, level)` (F-404) and it feeds both levels.
- A plain callable `(lo, hi) -> Iterable[float]` is accepted and wrapped (F-406). Its
  key falls back to fixed-significant-digit rounding, as `PLAN.md` states.

#### Formatter — sees the whole tick list (F-501..F-504)

```python
@dataclass(frozen=True)
class Labels:
    text: Sequence[str]        # one per tick, same order
    offset: str | None = None  # the shared exponent slot; always None in 0.1 (F-503)

class Formatter(Protocol):
    def __call__(self, values: FloatArray) -> Labels: ...
```

- The formatter receives every tick at once, so context-dependent labelling — shared
  precision, an SI prefix chosen for the whole axis — is possible (F-501).
- **Proposed:** a label string is LaTeX in math mode, rendered with `MathTex`. That
  matches Manim's own tick labels and the `r"\pi"` tick list the maintainer approved
  in Q3.3 of `docs/api-sketch.md`.
- A plain callable `float -> str` is accepted and wrapped (F-504).

#### Source and Shape (F-103, F-114, F-707)

```python
class Source(Protocol):
    def sample(self, map: CompiledMap, bounds: Bounds) -> Payload: ...
    def at(self, t: FloatArray) -> FloatArray: ...   # data coords, for i2gp (F-707)
```

`map` is read-only: it is the pipeline's one feedback edge (D6), so adaptive sampling
can measure curvature on screen. `Shape` operations are plain functions
`Payload -> Payload` owned by the artist (F-106), and live in `shape.py` so they are
core and testable without a mobject.

### 4. Surviving Manim's geometric transformations

Decided in `PLAN.md` and recorded here by reference: every library-generated leaf
carries a `points` property; the getter is the lazy-rebuild trigger and returns the
cache object itself; a shadow copy tells an in-flight animation from a direct call;
`shift` and `apply_points_function_about_point` are overridden to append exact affines
to the placement chain; a whole-array assignment is either a recoverable affine or a
transient override. Requirements F-901 to F-909.

The layering above adds one constraint: the placement chain is stored as core `Node`s,
so `c2p` and `p2c` after `ax.rotate(...)` are still core functions, property-testable
without rendering (F-201, F-208).

## Consequences

**What gets tested, and where:**

| Obligation | Layer | Kind |
|---|---|---|
| `p2c(c2p(x)) == x` on every scale, whole range (F-201, defect 15c) | core | Hypothesis |
| `scale.inverse(scale.forward(x)) == x` and declared monotonicity (F-305) | core | Hypothesis |
| no float accumulation: `Multiple(0.1)` over `[0, 1]` gives exact multiples (F-402) | core | example + property |
| one locator never emits two values with one key (F-413) | core | Hypothesis |
| the payload validation table in `docs/scope.md` raises row by row | core | one test per row |
| the core imports no Manim | core | subprocess import check |
| every generated leaf is a library type (F-1004) | Manim | structural |
| the getter returns the cache object itself (F-902) | Manim | identity, not equality |
| every public mutator carries `override_animate` (F-908) | Manim | mechanical sweep |
| the eight restoring animations end on the derived points (F-906) | Manim | one per animation |
| p95 rebuild <= 4 ms and <= 1.5x baseline (F-1001) | Manim | benchmark, run apart from the four checks |

Render tests carry the `render` marker from task 02 and stay out of the default run.

**What becomes harder.** A third party reading NumPy arrays instead of mobjects is the
point of the core, but it also means the core cannot use Manim's colour or config
types; style crosses the boundary as plain values.

**What stays open.** Polar (0.2) is the first non-separable system and the first user
of a public `Node`. Until then `Node` is frozen in shape but not exported, so it can
still change without breaking anyone — see question 1.

## Questions for the maintainer

1. **Is `Node` public in 0.1?** Proposed: no. `Scale` is the public extension point;
   `Node` is internal until polar needs it in 0.2. The cost is that a user cannot
   write a coupled transform in 0.1, which no 0.1 requirement asks for.
2. **Label markup.** Proposed: LaTeX math mode via `MathTex`. The alternative is plain
   text via `Text`, which renders without a TeX install but cannot show `\pi`.
3. **`key()` returning `None` for off-grid values.** Proposed as the single rule behind
   identity, minor-on-major removal and explicit merge. It makes every locator answer
   "would I emit this value?", which `MaxN` can only answer for the range it last saw.
   Acceptable, or should coincidence (F-407) compare values with a tolerance instead?
4. **Domain as an open interval.** Proposed, with the `sqrt`-at-zero ceiling above.
5. **Module names.** `system.py` / `axis.py` / `artists.py` and the rest are
   placeholders in the same sense as the API sketch: rename freely.
