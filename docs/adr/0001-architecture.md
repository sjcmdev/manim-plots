# ADR 0001 — Architecture of the 0.1 engine

- **Status:** Accepted — drafted 2026-10-23; the maintainer answered the five open
  questions the same day (see the end of this record). Amended 2026-10-24 after four
  proofs of concept: section 4 and the module layout now record D17-D21 of the grill
  log instead of the shadow-test integration.
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

Item 3 was first taken from `PLAN.md` by reference. The proofs of concept replaced that
design, and section 4 now summarises what replaced it. Items 1, 2 and 4 are new. The questions that had to be answered before this record was accepted are
collected at the end, with the maintainer's answers.

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

The rule is enforced, not hoped for: a test parses every module under `core/` and
asserts that none imports `manim` or anything from `mobjects/`. The check is static
because a runtime one cannot work: importing `manim_plots.core.scales` first runs
`manim_plots/__init__.py`, which re-exports the Manim layer. Since core modules import
only each other, a per-file check also covers the transitive case.

### 2. Module layout

```
src/manim_plots/
    __init__.py         public re-exports; the only import users need
    core/               numeric core: NumPy only
        payload.py      Payload (F-114) and its construction-time validation
        nodes.py        Node protocol, affine collapse, compiled Map (F-105, F-109)
        scales.py       Scale protocol; Linear, Log, SymLog, FunctionScale (F-3xx)
        ticks.py        Locator protocol; MaxN, Multiple, Log, Fixed, Null, MinorCount (F-4xx)
        formatters.py   Formatter protocol and the 0.1 formatters (F-5xx)
        sources.py      Source protocol; analytic, array and parametric sources (F-7xx)
        shape.py        split at invalid samples, clip, dash (F-106, F-705, F-706, F-806)
        params.py       parameter descriptors and version counters (F-110, F-911)
    mobjects/           Manim layer
        leaves.py       leaf mobjects: the `points` property and the lifecycle (F-901..F-907)
        context.py      what the leaves read from Manim's call stack, and its pins (F-917)
        system.py       CoordinateSystem, CartesianAxes; owns Map, the frame (F-914), keyed alignment (F-908)
        axis.py         Axis decoration (F-6xx)
        artists.py      the four 0.1 artists (F-701)
        legend.py       Legend (F-801)
        animations.py   DrawAxes, TraceCurve, ShowPoints, Morph (F-912)
```

Fifteen modules for 104 requirements, in two subpackages that name the layer, so the
boundary is visible in every import path and not only in the test. A module is split
when it outgrows one reader, not in advance.

### 3. The contracts

Signatures below are the contract; names are proposed. `FloatArray` is
`numpy.typing.NDArray[np.float64]`. Every contract is a `typing.Protocol`, so a third
party implements it without inheriting from us, and `mypy --strict` checks the
implementation (F-1002).

#### Scale — one dimension, monotonic (F-109, F-301..F-311)

```python
class Scale(Protocol):
    domain: tuple[float, float]  # bounds; +-inf allowed
    closed: tuple[bool, bool]  # whether each bound belongs to the domain
    increasing: bool  # declared monotonic direction

    def forward(self, x: FloatArray) -> FloatArray: ...  # data -> scaled
    def inverse(self, u: FloatArray) -> FloatArray: ...  # scaled -> data
    def limit_range(self, lo: float, hi: float) -> tuple[float, float]: ...
```

- `forward` is the scale transform and `inverse` its inverse — never the other way
  round (F-303, defect 10).
- Both are vectorized over `ndarray`; a value outside `domain` — an open bound itself
  included — maps to `NaN`, and the *caller* applies the surface rule from
  `docs/scope.md` (split, drop or raise). The scale itself never decides policy.
- Bounds are closed per side, so `sqrt` is `domain=(0, inf), closed=(True, False)` and
  `0` is a valid input, while `Log` stays open at `0`. An infinite bound is always open;
  a scale that declares it closed is rejected at construction.
- `limit_range` is F-311: it normalises a configured range that leaves the domain, and
  is called on range configuration only, never on a conversion (F-202).
- `FunctionScale(forward, inverse, domain, closed=(False, False), increasing=True)` is
  how a user supplies a scale (F-302). Its constructor runs the sampled falsification of
  F-305, sampling each closed bound as well as the interior, and raises naming the
  failed property.

A scale is a value object, not a map node. The coordinate system compiles each scale
into a one-dimensional `Node`, which is where D6's `apply` / `is_affine` / `matrix` /
`inverse` / `domain` contract lives. That reconciles D6 and F-109: F-109 describes what
the *user* supplies, D6 what the *chain* runs.

#### Locator — tick values and their keys (F-401..F-413)

```python
class Locator(Protocol):
    def values(
        self, lo: float, hi: float, scale: Scale, max_ticks: int
    ) -> FloatArray: ...
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
    text: Sequence[str]  # one per tick, same order
    offset: str | None = None  # the shared exponent slot; always None in 0.1 (F-503)


class Formatter(Protocol):
    def __call__(self, values: FloatArray) -> Labels: ...
```

- The formatter receives every tick at once, so context-dependent labelling — shared
  precision, an SI prefix chosen for the whole axis — is possible (F-501).
- A label string is LaTeX in math mode, rendered with `MathTex`. That matches Manim's
  own tick labels and the `r"\pi"` tick list the maintainer approved in Q3.3 of
  `docs/api-sketch.md`. Plain `Text` is not offered in 0.1, so labels need a TeX
  install, as Manim's do.
- Numeric labels are assembled from a process-wide glyph cache, as Manim's
  `DecimalNumber` does; a whole `MathTex` per string is reserved for labels fixed at
  configuration, such as `r"\pi"`. In PoC 1 (H5), compiling each new string during an
  animated range cost a p95 of 1.3 s cold; the cache bounds compilation to the
  alphabet. Warm, both strategies still took about 5.3 ms at p95 in frames that
  introduced labels, because that run rebuilt its dictionaries; an in-process cache
  that lives across frames, with keyed identity reusing surviving labels, is unmeasured.
  F-1001 is measured after the first TeX compile.
- A plain callable `float -> str` is accepted and wrapped (F-504).

#### Source and Shape (F-103, F-114, F-707)

```python
class Source(Protocol):
    def sample(self, map: CompiledMap, bounds: Bounds) -> Payload: ...
    def at(self, t: FloatArray) -> FloatArray: ...  # data coords, for i2gp (F-707)
```

`map` is read-only: it is the pipeline's one feedback edge (D6), so adaptive sampling
can measure curvature on screen. `Shape` operations are plain functions
`Payload -> Payload` owned by the artist (F-106), and live in `shape.py` so they are
core and testable without a mobject.

### 4. Surviving Manim's geometric transformations

The first draft of this record took this item from `PLAN.md` as decided: a shadow copy
telling an animation from a direct call, overrides appending to a placement chain, and
a setter classifying whole-array writes. The first proof of concept falsified it
(`docs/poc-points-property.md`), and three more tested the replacement
(`docs/poc2-frame-lifecycle.md`, `docs/poc3-stack-context.md`,
`docs/poc4-keyed-alignment.md`). `PLAN.md` and D17-D21 of the grill log now hold the
decision; in short:

- **Every library-generated leaf carries a `points` property** whose getter is the
  lazy-rebuild trigger and returns the cache object itself (F-901, F-902).
- **A hidden grid in the system's family carries placement** (F-914). Manim moves it
  natively, so the system overrides no geometric method, `.animate` chains, and a
  container holding the system moves its artists exactly once.
- **Leaves have a lifecycle instead of a test** (F-903 to F-907). They are transient
  inside an animation and adopt its target at the end. A remover leaves them detached,
  and an introducer re-attaches them.
- **Outside animations, a write is attributed from the call stack** (F-904): which
  container wrote, and with which function. Every frame read is pinned (F-917).
- **Artists follow only permanent changes of their system** (F-916).
- **The data channel is native under `.animate`**, through keyed family alignment
  (F-908, F-909).

The layering above adds one constraint: the frame's map, affine or bilinear, is computed
by core functions from the grid's node array, and an artist's own transform is stored
as core `Node`s, so `c2p` and `p2c` after `ax.rotate(...)` are still property-testable
without rendering (F-201, F-208). Only reading the grid from the mobject is Manim-side.

## Consequences

**What gets tested, and where:**

| Obligation | Layer | Kind |
|---|---|---|
| `p2c(c2p(x)) == x` on every scale, whole range (F-201, defect 15c) | core | Hypothesis |
| `scale.inverse(scale.forward(x)) == x` and declared monotonicity (F-305) | core | Hypothesis |
| no float accumulation: `Multiple(0.1)` over `[0, 1]` gives exact multiples (F-402) | core | example + property |
| one locator never emits two values with one key (F-413) | core | Hypothesis |
| the payload validation table in `docs/scope.md` raises row by row | core | one test per row |
| the core imports no Manim | core | static import check over `core/` |
| every generated leaf is a library type (F-1004) | Manim | structural |
| the getter returns the cache object itself (F-902) | Manim | identity, not equality |
| every frame and local read from the call stack is pinned by source hash (F-917) | Manim | contract test, rerun per supported version |
| each animation in the regression matrix ends where Manim leaves a plain `VMobject` (F-906) | Manim | one per animation, systems and artists |
| the frame stays invisible and outside bounds under every style call and partial drawing (F-914) | Manim | pixel comparison against a frame-free scene |
| a bound artist does not freeze during an animation it is not part of (F-915) | Manim | rendered middle frames against fresh captures |
| `ax.animate.shift(v).set_x_range(r)` is a correct plot in every frame (F-909) | Manim | every rendered frame against an independent reference |
| p95 rebuild <= 4 ms and <= 1.5x baseline (F-1001) | Manim | benchmark, run apart from the four checks |

Render tests carry the `render` marker from task 02 and stay out of the default run.

**What becomes harder.** A third party reading NumPy arrays instead of mobjects is the
point of the core, but it also means the core cannot use Manim's colour or config
types; style crosses the boundary as plain values.

**What else becomes harder.** The Manim layer depends on Manim internals it does not
own: which frames call our setters, their locals, and the order in which
`Transform.begin` aligns and suspends. The pins make an upgrade fail loudly rather than
misbehave. Supporting a new Manim version is therefore a review step, not a
version-range bump.

**What stays open.** Polar (0.2) is the first non-separable system and the first user
of a public `Node`. Until then `Node` is frozen in shape but not exported, so it can
still change without breaking anyone — see question 1. Three contracts from the proofs
of concept are not written yet: the tick pool's schedule (which parameter samples it
covers), re-attaching introducers whose constructors captured a point, and the
grid density `N`, which the proofs of concept fixed at 33.

## Questions for the maintainer

Answered 2026-10-23.

1. **Is `Node` public in 0.1?** Proposed: no. `Scale` is the public extension point;
   `Node` is internal until polar needs it in 0.2. The cost is that a user cannot
   write a coupled transform in 0.1, which no 0.1 requirement asks for.
   **Answer: no, as proposed.**
2. **Label markup.** Proposed: LaTeX math mode via `MathTex`. The alternative is plain
   text via `Text`, which renders without a TeX install but cannot show `\pi`.
   **Answer: `MathTex`, as proposed.**
3. **`key()` returning `None` for off-grid values.** Proposed as the single rule behind
   identity, minor-on-major removal and explicit merge. It makes every locator answer
   "would I emit this value?", which `MaxN` can only answer for the range it last saw.
   Acceptable, or should coincidence (F-407) compare values with a tolerance instead?
   **Answer: `key()` for all three, as proposed.** The `MaxN` limitation is accepted:
   its key is relative to the current range, and the current range is what is drawn.
4. **Domain as an open interval.** Proposed, with the `sqrt`-at-zero ceiling.
   **Answer: no — closed bounds in 0.1.** The Scale contract above gains
   `closed: tuple[bool, bool]`, and the ceiling is gone.
5. **Module names.** `system.py` / `axis.py` / `artists.py` and the rest are
   placeholders in the same sense as the API sketch: rename freely.
   **Answer: keep the names, but split into `core/` and `mobjects/` subpackages.**
   Section 2 shows the result.
