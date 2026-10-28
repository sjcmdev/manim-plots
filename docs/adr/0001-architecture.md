# ADR 0001 — Architecture of the 0.1 engine

- **Status:** Frozen, 2026-10-24. Accepted on 2026-10-23 with the maintainer's answers
  to its five questions, amended the next day after four proofs of concept (D17-D21) and
  after two independent freeze reviews (D22-D27). From here on, a change to a contract
  in this record needs a new ADR.
- **Task:** `task/04-architecture` in `TODO.md`.
- **Builds on:** `docs/plan.md`, `docs/scope.md` (the `F-*` list), `docs/grill-log.md`
  (D1-D27), the proof-of-concept reports `docs/poc/`, the arch-crew review
  `docs/reviews/2026-10-24-arch-crew.md` and the freeze reviews `docs/reviews/`.

## Context

Task 03 decided *what* 0.1 does and most of *how*: the `Source -> Map -> Shape`
pipeline, derived points, keyed identity, the invalid-input rule. Task 04 had four open
items, and this record closes them:

1. the public contracts third parties implement against — scale, locator, formatter,
   source;
2. the separation between the data model and the Manim geometry it produces;
3. how a coordinate system survives Manim's geometric transformations and animations;
4. a module layout.

Item 3 was first taken from `docs/plan.md` by reference. The proofs of concept replaced that
design, and section 4 records what replaced it. The questions that had to be answered
before this record was accepted are collected at the end, with the maintainer's answers.

## Decision

### 1. Two layers; the core never imports Manim; one module reads Manim's internals

The package splits into a **numeric core** and a **Manim layer**.

- The **core** holds everything that is a function of numbers: the payload, map nodes
  and the frame's numerics, scales, locators and the tick pool's plan, formatters,
  sources, `Shape` operations, parameters, and the leaf lifecycle's transition function.
  It imports NumPy, SciPy and the standard library and nothing else. SciPy is allowed
  because Manim already depends on it, and the frame's sparse product costs 0.14 ms where
  NumPy gathers cost 1.4-3.8 ms (`docs/reviews/2026-10-24-claude.md`, A1).
- The **Manim layer** holds everything that is a mobject: leaf types with the `points`
  property, the coordinate system and its frame, axis decoration, artists, legend and
  animations. It calls the core; the core never calls it.

This is the answer to item 2. It is also what makes the testing strategy in
`CONTRIBUTING.md` affordable: every float-to-float function the defect audit cares
about — scale inverses, tick placement, coordinate conversion, frame fitting — and every
lifecycle transition is tested in milliseconds, without constructing a mobject.

Two rules are enforced, not hoped for, by one static test that parses the source:

- no module under `core/` imports `manim` or anything from `mobjects/`. The check is
  static because a runtime one cannot work: importing `manim_plots.core.scales` first
  runs `manim_plots/__init__.py`, which re-exports the Manim layer;
- only `mobjects/context.py` reads Manim's call stack — `sys._getframe`, `f_code`,
  `f_locals`, `inspect.currentframe`. The other dependencies on Manim internals cannot be
  checked statically: the Manim methods the library overrides, the animation attributes
  it assigns, and the order in which Manim calls them. They are listed in F-917's
  inventory and pinned per supported version.

### 2. Module layout

```
src/manim_plots/
    __init__.py         public re-exports; the only import users need
    core/               numeric core: NumPy, SciPy, the standard library
        payload.py      Payload (F-114) and its validation
        nodes.py        Node protocol, affine collapse, compiled Map; the frame map —
                        affine solve, bilinear weights, inverse; an artist's own
                        transform (F-105, F-109, F-914)
        scales.py       Scale protocol; Linear, Log, SymLog, FunctionScale (F-3xx)
        ticks.py        Locator protocol; MaxN, Multiple, Log, Fixed, Null, MinorCount;
                        the tick pool's plan (F-4xx, F-920)
        formatters.py   Formatter protocol and the 0.1 formatters (F-5xx)
        sources.py      Source protocol; analytic, array and parametric sources (F-7xx)
        shape.py        split, clip, dash, densify (F-106, F-705, F-706, F-806, F-914)
        params.py       parameter descriptors and version counters (F-110, F-911)
        lifecycle.py    the leaf lifecycle's states, events and transition function (F-919)
    mobjects/           Manim layer
        leaves.py       leaf mobjects: the `points` property, applying lifecycle actions
        context.py      the only reader of Manim's call stack, and its pins (F-917)
        system.py       CoordinateSystem, CartesianAxes, NumberPlane; the frame, keyed alignment
        axis.py         Axis decoration, in NumberLine's vocabulary (F-6xx)
        artists.py      the four 0.1 artists (F-701)
        legend.py       Legend (F-801)
        animations.py   DrawAxes, TraceCurve, ShowPoints, Morph (F-912)
```

Sixteen modules for 108 requirements of tier 0.1, in two subpackages that name the
layer, so the boundary is visible in every import path and not only in the test. A
module is split when it outgrows one reader, not in advance.

### 3. The contracts

Signatures below are the contract; names are proposed. `FloatArray` is
`numpy.typing.NDArray[np.float64]` and `BoolArray` its boolean counterpart. Every
contract is a `typing.Protocol`, so a third party implements it without inheriting from
us, and `mypy --strict` checks the implementation (F-1002).

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
- Manim's `LogBase`, passed as `axis_config={"scaling": LogBase()}`, is accepted with
  Manim's meaning: the range is in exponents (D23).

A scale is a value object, not a map node. The coordinate system compiles each scale
into a one-dimensional `Node`, which is where D6's `apply` / `is_affine` / `matrix` /
`inverse` / `domain` contract lives. That reconciles D6 and F-109: F-109 describes what
the *user* supplies, D6 what the *chain* runs. A coupled node — polar, in 0.2 — is not
held to a monotonic direction.

#### Locator — tick values, identity and membership (F-401..F-413)

```python
class Locator(Protocol):
    def values(
        self, lo: float, hi: float, scale: Scale, max_ticks: int
    ) -> FloatArray: ...
    def key(self, value: float) -> Hashable: ...
    def contains(self, value: float, lo: float, hi: float, scale: Scale) -> bool: ...
```

- `values` returns tick positions in data space, in axis order: ascending, or
  descending for a reversed range (F-209). `max_ticks` is the label-space estimate of
  F-408: how many labels fit, from the label font size, as matplotlib's `get_tick_space`
  does. A count rather than a length keeps it independent of the scale. No `np.arange`
  over a step anywhere (F-402): `Multiple(step)` computes `k * step` from integer `k`.
- `key(value)` is the identity of a tick (F-413, D10, D25). It depends on the value and
  the locator's configuration only, never on the range, so one value has one key on
  every range an animation passes through. `Multiple` keys by the integer multiple,
  `Log` by `(decade, mantissa index)`, `MaxN` and wrapped callables by a canonical
  rounding of the value to a fixed number of significant digits.
- `contains(value, lo, hi, scale)` answers "would this locator emit this value on this
  range?". Membership and identity are separate, and the two mechanisms that need both
  use both:
  - **minor-on-major removal** (F-407) — a minor value is dropped when the major locator
    contains it;
  - **explicit-over-generated merge** (F-405) — an explicit entry replaces a generated
    one with the same key; an entry the generated locator does not contain is added.
- Major and minor ticks come from two locators on one axis. `Fixed` is the exception:
  its entries are `(value, label, level)` (F-404) and it feeds both levels.
- A plain callable `(lo, hi) -> Iterable[float]` is accepted and wrapped (F-406).
- The tick pool (F-920) is planned in `ticks.py` from `values` and `key` alone: the union
  of keys along a sampled parameter path, plus spare leaves.

#### Formatter — sees the whole tick list (F-501..F-504)

```python
@dataclass(frozen=True)
class Labels:
    text: Sequence[str]  # one per tick, same order
    text_mode: Sequence[bool] | None = None  # per label: text mode instead of math
    offset: str | None = None  # the shared exponent slot; always None in 0.1 (F-503)


class Formatter(Protocol):
    def __call__(self, values: FloatArray) -> Labels: ...
```

- The formatter receives every tick at once, so context-dependent labelling — shared
  precision, an SI prefix chosen for the whole axis — is possible (F-501).
- A label string is LaTeX in math mode unless `text_mode` says otherwise. Strings given
  through Manim's `add_labels` are text mode, as Manim's `Tex` renders them (D23).
- Numeric labels are assembled from a process-wide glyph cache, as Manim's
  `DecimalNumber` does; a whole `MathTex` per string is reserved for labels fixed at
  configuration, such as `r"\pi"`. In PoC 1 (H5), compiling each new string during an
  animated range cost a p95 of 1.3 s cold; the cache bounds compilation to the
  alphabet. F-1001 is measured with a warm cache.
- A plain callable `float -> str` is accepted and wrapped (F-504).

#### Source, Payload and Shape (F-103, F-114, F-707)

```python
class CompiledMap(Protocol):  # a read-only view handed to a source
    is_affine: bool

    def forward(self, data: FloatArray) -> FloatArray: ...  # (n, d) data -> local
    def inverse(self, local: FloatArray) -> FloatArray: ...
    def valid(self, data: FloatArray) -> BoolArray: ...  # inside every node's domain
    def to_screen(self, data: FloatArray) -> FloatArray: ...  # through the frame


class Bounds(Protocol):  # the clip region, in local space
    lower: FloatArray
    upper: FloatArray  # the bounding box

    def contains(self, local: FloatArray) -> BoolArray: ...  # a disc fits


class Source(Protocol):
    def sample(self, map: CompiledMap, bounds: Bounds) -> Payload: ...
    def at(self, t: FloatArray) -> FloatArray: ...  # data coords, for i2gp (F-707)
```

- `map` is read-only: it is the pipeline's one feedback edge (D6). Adaptive sampling
  measures its error through `to_screen` at sampling time, so curvature is measured on
  screen. A later placement change resamples only when the frame's linear scale has
  grown past twice the one sampled for.
- `at(t)` is exact for an analytic source. An array source interpolates linearly in its
  parameter, and raises on an `x` query against non-monotone `x` data.
- An optional `resample_like(other, n) -> Payload` exists for the sources `Morph`
  supports (F-710); a source without it is refused by `Morph`.
- **`Map` owns validity.** Each node combines the incoming `valid` mask with its own
  domain and finite-output mask, and rebuilds path segments, before the next stage sees
  the payload. Stages exchange validated payloads.
- The `region` branch of `Payload` is declared, not complete. Adding an optional field
  with a default — field values for contours and vector fields — is not a breaking
  change, and is how the later `FieldSource` extends it.
- `Shape` operations are plain functions `Payload -> Payload` owned by the artist
  (F-106). They take the clip `Bounds` explicitly, and live in `shape.py`, so they are
  core and testable without a mobject.

### 4. Surviving Manim's geometric transformations and animations

The first draft of this record took this item from `docs/plan.md` as decided: a shadow copy
telling an animation from a direct call, overrides appending to a placement chain, and
a setter classifying whole-array writes. The first proof of concept falsified it
(`docs/poc/poc1-points-property.md`), three more tested the replacement
(`docs/poc/poc2-frame-lifecycle.md`, `docs/poc/poc3-stack-context.md`,
`docs/poc/poc4-keyed-alignment.md`), and two reviews tested the result against 48 of Manim's
own example scenes and against Manim 0.22.0 (`docs/reviews/`). `docs/plan.md` and D17-D27 of
the grill log hold the reasoning; in short:

- **Every library-generated leaf carries a `points` property** whose getter is the
  lazy-rebuild trigger and returns the cache object itself (F-901, F-902).
- **A hidden grid in the system's family carries placement** (F-914). Manim moves it
  natively, so the system overrides no geometric method, `.animate` chains, and a
  container holding the system moves its artists exactly once. The grid is the last
  member of the system's family, contributes no boundary anchors, ignores partial
  drawing and stays invisible.
- **Outside animations, a write is attributed from the call stack** (F-904): which
  container wrote, with which function, read from Manim's frames by code object.
- **Leaves follow the lifecycle below** (F-903 to F-907, F-919).
- **Artists follow only permanent changes of their system** (F-916), decided by
  simulating the animation on a copy.
- **The data channel is native under `.animate`**, through keyed family alignment with
  a tick pool (F-908, F-909, F-920).

The layering adds one constraint: the frame's map, affine or bilinear, is computed by
core functions from the grid's node array, and an artist's own transform is stored as
core `Node`s, so `c2p` and `p2c` after `ax.rotate(...)` stay property-testable without
rendering (F-201, F-208). Only reading the grid from the mobject is Manim-side.

#### The leaf lifecycle

States:

- **A** — attached: derived from its data and the live frame.
- **T** — transient: owned by one or more running animations, keyed by animation
  identity; the buffer belongs to them.
- **R** — removed: detached after a remover. The buffer is frozen as the animation's
  cleanup left it, and the artist behaves as plain Manim geometry.
- **S** — shaped: detached into a shape kept in system-local coordinates. It follows the
  frame and ignores the data.

**Freezing.** While its system runs a temporary animation the artist is not part of, an
**A** or **S** artist reads a frozen copy of the frame (F-916). "Temporary" means the
system ends where it started.

**Animation copies.** The starting copy and the target copy an animation makes are
attached, unregistered and follow the live frame. Only the animated subject enters
**T**.

| Event | A | T | R | S |
|---|---|---|---|---|
| Read points or bounds | the cache; rebuilt first if dirty | the buffer | the buffer | the shape through the live or frozen frame |
| Data change: parameter, range, bound tracker | dirty | recorded; applied when the last owner finishes | ignored until `refresh()` | ignored until `refresh()` |
| Write by a container whose family holds the system's frame | ignored: the frame moved | into the buffer | into the buffer | ignored: the frame moved |
| Write by any other container | becomes the artist's own transform | into the buffer | into the buffer | becomes a transform of the shape |
| Bare NumPy write, no writer frame | kept until the next rebuild | into the buffer | kept | kept until the next rebuild |
| `reverse_points()` | toggles the artist's direction | into the buffer | reverses the buffer | reverses the shape |
| An animation begins — `Transform.begin`'s `align_data`, or a suspension from `Animation.begin` | **T**, one owner | adds an owner | an introducer re-attaches, then **T**; anything else, **T** with origin **R** | an introducer re-attaches, then **T**; anything else, **T** with origin **S** |
| An owner finishes while others remain | — | that owner is dropped; its target is kept if it ended on it | — | — |
| The last owner finishes, ended on an artist target | — | adopts the target's source, own transform, style and system → **A**, rebuilt with live data | — | — |
| The last owner finishes, ended on a plain target | — | **S**, with the target's shape | — | — |
| The last owner finishes, ended on its start (buffer equals the live starting copy) | — | back to the origin state, rebuilt with live data | — | — |
| The last owner finishes, ended elsewhere, no target (`Homotopy`) | — | **S**, with the final shape | — | — |
| The last owner was a remover, after its cleanup | — | **R** | — | — |
| `refresh()` | rebuilt | deferred until the last owner finishes | **A** | **A** |
| `become(artist)` | adopts it → **A** | adopts it now; pending targets are cancelled; the owners keep the buffer | adopts it → **A** | adopts it → **A** |
| `become(plain mobject)` | **S** | **S** as the base; the owners keep the buffer | **S** | **S** |
| `copy()` | an unregistered **A** | an unregistered **A**, rebuilt | an **R** | an **S** |
| `suspend_updating()` with no animation on the stack | updaters paused; no state change | no state change | no state change | no state change |
| The system's frame moves | follows, or reads the frozen frame | its animation copies follow | unaffected | follows, or reads the frozen frame |
| `ReplacementTransform(ax, new_ax)` finishes | registered: rebinds to `new_ax` | rebinds when its own owners finish | stays with `ax` | registered: rebinds to `new_ax` |

Notes on the table:

- An introducer constructed on an **R** artist reads the geometry the artist has at
  construction, as in Manim; `GrowFromCenter` therefore grows from where the removed
  curve collapsed. `refresh()` before constructing it grows from the current centre.
- When several owners ended on targets, the last one to finish wins.
- `become` with Manim's `match_*` or `stretch` keywords runs Manim's preparation on a
  copy, then adopts the copy.
- `become` on a system adopts the other system's parameters and frame; its artists stay
  bound to it.
- `lifecycle.py` implements this table as a pure function `(state, event) -> (state,
  actions)`, and a unit test covers every cell. The differential matrix of F-906 covers
  each distinct transition once against plain Manim.

## Consequences

**What gets tested, and where:**

| Obligation | Layer | Kind |
|---|---|---|
| `p2c(c2p(x)) == x` on every scale under an affine frame, whole range (F-201, defect 15c) | core | Hypothesis, plus fixed anchors and known examples |
| `scale.inverse(scale.forward(x)) == x` and declared monotonicity (F-305) | core | Hypothesis |
| no float accumulation: `Multiple(0.1)` over `[0, 1]` gives exact multiples (F-402) | core | example + property |
| one locator never emits two values with one key, and a key is the same on every range (F-413) | core | Hypothesis |
| the payload validation table in `docs/scope.md` raises row by row | core | one test per row |
| every cell of the lifecycle table (F-919) | core | one unit test per cell |
| the pool's plan covers the rendered alphas of every composition type (F-920) | core + Manim | one per composition |
| the core imports no Manim, and only `context.py` reads the stack | both | static check |
| every generated leaf is a library type (F-1004) | Manim | structural |
| the getter returns the cache object itself (F-902) | Manim | identity, not equality |
| every frame, local, override and assigned attribute is pinned, one set per Manim version (F-917) | Manim | contract test per supported version |
| each distinct lifecycle transition ends where Manim leaves a plain `VMobject`, or where the table says it differs (F-906) | Manim | differential, per supported version |
| `mp.Axes(...)` matches `Axes(...)` for every row of the defaults table, and corpus scene geometry matches modulo F-1008 (F-1009) | Manim | geometry-level parity against Manim's own `Axes` |
| the frame stays invisible and outside bounds under every style call and partial drawing (F-914) | Manim | pixel comparison, `render` marker |
| a bound artist does not freeze during an animation it is not part of (F-915) | Manim | rendered middle frames against fresh captures, `render` marker |
| `ax.animate.shift(v).set_x_range(r)` is a correct plot in every frame (F-909) | Manim | every rendered frame against an independent reference |
| F-1001, end to end on both frame paths | Manim | benchmark, run apart from the four checks |

Oracles are labelled: a test is either a **correctness oracle** — analytic, an
invariant, or plain Manim — or a **decision regression** asserting a recorded choice.
No expected value is computed by the code under test (`docs/reviews/2026-10-24-claude.md`,
E2). Render tests carry the `render` marker from task 02 and stay out of the default run.
They run with the per-version matrix before a release and on every Manim upgrade.

**What becomes harder.** A third party reading NumPy arrays instead of mobjects is the
point of the core, but it also means the core cannot use Manim's colour or config
types; style crosses the boundary as plain values.

**What else becomes harder.** The Manim layer depends on Manim internals it does not
own: which frames call our setters, their locals, the methods we override and the order
in which Manim calls them. Both reviewers found all seventeen frames the mechanism reads
byte-identical in 0.22.0, and 228 of 228 behavioural tests of PoC 4 pass there. Still,
each supported version needs its own pin set, and supporting a new one is a review step,
not a version-range bump.

**What stays open.** Polar (0.2) is the first non-separable system and the first user
of a public `Node`. Until then `Node` is frozen in shape but not exported, so it can
still change without breaking anyone — see question 1. The grid density is an internal
constant, `N = 33`, and not a contract.

## Questions for the maintainer

Answered 2026-10-23; question 3 revised on 2026-10-24.

1. **Is `Node` public in 0.1?** Proposed: no. `Scale` is the public extension point;
   `Node` is internal until polar needs it in 0.2. The cost is that a user cannot
   write a coupled transform in 0.1, which no 0.1 requirement asks for.
   **Answer: no, as proposed.**
2. **Label markup.** Proposed: LaTeX math mode via `MathTex`. The alternative is plain
   text via `Text`, which renders without a TeX install but cannot show `\pi`.
   **Answer: `MathTex`, as proposed.** Text mode was added later for Manim's own
   `add_labels` strings (D23).
3. **`key()` returning `None` for off-grid values.** Proposed as the single rule behind
   identity, minor-on-major removal and explicit merge. It makes every locator answer
   "would I emit this value?", which `MaxN` can only answer for the range it last saw.
   **Answer: `key()` for all three, as proposed.** The `MaxN` limitation was accepted.
   **Revised by D25:** the tick pool needs one key per value on every range, so identity
   and membership are now separate — `key(value)` never depends on the range, and
   `contains(...)` answers "would I emit this value?".
4. **Domain as an open interval.** Proposed, with the `sqrt`-at-zero ceiling.
   **Answer: no — closed bounds in 0.1.** The Scale contract above gains
   `closed: tuple[bool, bool]`, and the ceiling is gone.
5. **Module names.** `system.py` / `axis.py` / `artists.py` and the rest are
   placeholders in the same sense as the API sketch: rename freely.
   **Answer: keep the names, but split into `core/` and `mobjects/` subpackages.**
   Section 2 shows the result.
