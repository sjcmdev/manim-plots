# Acceptance table — task 07, sources, shape, parameters

**Status: Living until task 07 merges, then Record.** Written 2026-10-29 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: ADR 0001 §3 (`Source`, `Bounds`, `Shape`), ADR 0003
§1 (the pipeline's order) and §4 (bindings), `docs/scope.md` F-104, F-106-F-108, F-110,
F-113, F-703-F-707, F-806, F-911, F-918. Builds on task 06 (`Payload`, `Chain`,
`FrameMap`, `SystemMap`).

Modules: `src/manim_plots/core/sources.py`, `core/shape.py`, `core/params.py`.

**Moved:** `resample_like` (F-710) goes to task 12 with `Morph`, its only caller, so that
its signature is settled next to the animation that needs it *(default taken)*.

## The representation after `Shape`

A path leaves the source as **anchors** — samples, in data coordinates — and `Map` turns
them into local coordinates. The first `Shape` stage of a path artist turns anchors into
**curves**: cubic Bézier curves in Manim's layout, four points per curve
`[a0, h0, h1, a1]`, consecutive curves repeating the shared anchor, as
`VMobject.points` holds them. Every later stage — clip, dash, densify — works on curves,
so a straight and a smoothed path are clipped and dashed by one code path, and the leaf
assigns the result to `points` unchanged. A curve payload is `kind="path"` with every
segment's length a multiple of 4 and `valid=None`; which representation a payload is in
is the artist's knowledge, not a field *(default taken)*. ADR 0003 §1's order becomes:
source (bracketing samples, splits) → `Map` (validity, splits) → `smooth` or `corners` →
`clip` → `dash` → `densify`.

## B — `Bounds` and `Box` (`core/sources.py`)

```python
@runtime_checkable
class Bounds(Protocol):
    @property
    def lower(self) -> FloatArray: ...  # (2,), read-only
    @property
    def upper(self) -> FloatArray: ...
    def contains(self, local: FloatArray) -> BoolArray: ...


@dataclass(frozen=True)
class Box:
    lower: FloatArray
    upper: FloatArray
```

| ID | Row |
|---|---|
| B-1 | `Box(lower, upper)`: two finite `(2,)` arrays with `lower < upper` on both axes, else `ValueError`; stored read-only. `Box` satisfies `Bounds` |
| B-2 | `contains(local)` takes `(n, 2)` or `(n, 3)` local points and is true where `lower <= (x, y) <= upper`, inclusive, the z ignored; a non-finite point is outside |
| B-3 | `Bounds` is the clip region in the system's local space. `lower` and `upper` are its bounding box; `contains` is the truth for a region that is not a box (a disc, in 0.2's polar). The 0.1 `Shape` stages clip to the box *(default taken)* |

## FS — `FunctionSource` (analytic, `ax.plot(f)`)

```python
@runtime_checkable
class Source(Protocol):
    def sample(self, map: CompiledMap, bounds: Bounds) -> Payload: ...
    def at(self, t: ArrayLike) -> FloatArray: ...


class FunctionSource:
    def __init__(
        self,
        function: Callable[..., Any],
        x_range: Sequence[float] | None = None,  # (lo, hi) or (lo, hi, step)
        *,
        use_vectorized: bool = False,
        discontinuities: Iterable[float] | None = None,
        dt: float = 1e-8,
    ) -> None: ...


PIXEL = 8 / 1080  # one pixel of a 1080p frame, in scene units
CHORD_TOLERANCE = 0.5 * PIXEL
INITIAL_SAMPLES = 33
MAX_DEPTH = 12
MAX_SAMPLES = 20_000
```

| ID | Row |
|---|---|
| FS-1 | Arguments: `function` not callable, `use_vectorized` not a `bool`: `TypeError`. `x_range` not of length 2 or 3, a non-finite entry, `lo >= hi` *(default taken: the plot's own range is ascending, as Manim's `t_range` is)*, a step `<= 0`: `ValueError` naming `x_range` (or `step`). `dt <= 0` or non-finite: `ValueError` naming `dt`. A non-finite discontinuity: `ValueError` |
| FS-2 | Calling convention (F-704, Manim's): with `use_vectorized=False` the function is called once per sample with a `np.float64` scalar; with `use_vectorized=True`, once per refinement pass with a 1-D `float64` array, and must return an array of its length. A return that cannot be read as a float (or an array of the wrong length) raises `TypeError` naming the function. NumPy warnings during the calls are suppressed; an exception the function raises propagates unchanged |
| FS-3 | `sample(map, bounds)` returns a `path` payload in **data** coordinates `(n, 2)`, `[x, f(x)]`, `x` ascending. The sampled interval is the data x-extent of the bounds — `map.inverse` of the box's left and right edge midpoints — intersected with `x_range` when given; ends exactly on the interval's ends. An empty intersection gives `Payload.empty("path", 2)` |
| FS-4 | Samples where `f` is non-finite are kept with `valid` false and split the path (F-705) — `Payload.path`'s rule. The map's own validity is `Map`'s job, not the source's |
| FS-5 | **Adaptive refinement** (F-704, ADR 0003 §3): start from `INITIAL_SAMPLES` uniform samples, or more so that no two neighbours are farther apart in `x` than the step when `x_range` has one. An interval is bisected when the screen distance (`map.to_screen`) from its midpoint's image to the chord of its ends' images exceeds `CHORD_TOLERANCE`, or when exactly one end is valid (to locate the edge of a domain or a pole), until `MAX_DEPTH` bisections or `MAX_SAMPLES` samples. After refinement, every interval with both ends valid passes the chord test or is at the depth limit |
| FS-6 | **Pole split** (F-705, defect 15a): where two neighbouring valid samples have values of opposite sign and both lie outside the bounds in local y on opposite sides, the interval is bisected up to 40 times keeping the sign change. If the bracket's ends still lie outside on opposite sides, the path splits between them (touching segments, both ends kept); if not, the interval is ordinary. So `1/x` and `tan` split at their poles and a steep line through zero does not |
| FS-7 | `discontinuities` with `dt` (Manim's): for each discontinuity `d` strictly inside the interval, samples at `d - dt` and `d + dt` and none between them, and the path splits there |
| FS-8 | Sampling density depends on the map and the function, never on a locator (F-414): no tick argument exists |
| FS-9 | `at(t)` returns `(m, 2)` data points `[t, f(t)]` for a 1-D `t` (a scalar gives `(1, 2)`), exact, with the calling convention of FS-2; any `t` is accepted, inside or outside `x_range` (F-707) |
| FS-10 | A source is immutable and keeps no state between calls: `sample` with equal arguments gives equal payloads, and one source serves two systems (F-104, F-113) |

## PS — `ParametricSource` (`ax.plot_parametric_curve`)

```python
class ParametricSource:
    def __init__(
        self,
        function: Callable[..., Any],  # t -> (x, y) or (x, y, z)
        t_range: Sequence[float] = (0.0, 1.0),  # Manim's default
        *,
        use_vectorized: bool = False,
        discontinuities: Iterable[float] | None = None,
        dt: float = 1e-8,
    ) -> None: ...
```

| ID | Row |
|---|---|
| PS-1 | The argument rules of FS-1, with `t_range` for `x_range` |
| PS-2 | The function returns two or three coordinates per `t` (a `z` is dropped). Vectorised, it returns a sequence of two or three arrays of length `m`, Manim's convention (`x, y, z = function(t)` in `ParametricFunction`). Anything else: `TypeError` naming the function |
| PS-3 | `sample(map, bounds)` samples the whole `t_range` (the bounds clip later; they do not restrict `t`), refining by FS-5 and splitting by FS-4, FS-6 (in local y and x) and FS-7. Coordinates are in data space, in `t` order |
| PS-4 | `at(t)` returns `(m, 2)`, exact |

## AS — `ArraySource` (`ax.line`, `ax.scatter`, `plot_line_graph`)

```python
class ArraySource:
    def __init__(
        self,
        xs: ArrayLike,
        ys: ArrayLike | None = None,
        *,
        kind: Literal["path", "points"] = "path",
    ) -> None: ...
```

| ID | Row |
|---|---|
| AS-1 | Input shapes (F-703): `ArraySource(xs, ys)` with two 1-D sequences, or `ArraySource(pairs)` with `ys=None` and an `(n, 2)` sequence. Lengths that differ raise `ValueError` naming both lengths; `pairs` not `(n, 2)`, or `xs`/`ys` not 1-D, raise `ValueError`; non-numeric data raises `TypeError` |
| AS-2 | The data is copied once into a read-only `(n, 2)` `float64` array (`source.data`) and never changed (F-104) |
| AS-3 | Non-finite values are legal data: they are invalid samples and split a path (F-705) |
| AS-4 | `sample(map, bounds)` **filters** (F-104): it keeps every sample that is an end of an edge whose x-extent meets the bounds' data x-extent (FS-3's interval), so a segment from outside to outside across the viewport survives (ADR 0003 §1); a lone sample is kept when it lies in the interval. Kept samples keep their order; a gap where samples were dropped splits the path. A `points` source keeps the samples inside the interval |
| AS-5 | An array path does not split at a sign change: data is drawn as given *(default taken)* |
| AS-6 | `at(t)` (F-707) interpolates `y` linearly in `x`. `x` must be strictly monotonic, increasing or decreasing, else `ValueError` naming the first index where it is not; `t` outside the data's x-extent raises `ValueError`; a non-finite sample's neighbourhood raises `ValueError` *(default taken)* |

## SH — `core/shape.py`

```python
Shape = Callable[[Payload, Bounds], Payload]


def corners(payload: Payload, bounds: Bounds) -> Payload: ...
def smooth(payload: Payload, bounds: Bounds) -> Payload: ...
def clip(payload: Payload, bounds: Bounds) -> Payload: ...
def dash(
    payload: Payload, bounds: Bounds, *, on: float, off: float, phase: float = 0.0
) -> Payload: ...
def densify(payload: Payload, bounds: Bounds, *, pieces: int) -> Payload: ...
def arc_length(payload: Payload) -> FloatArray: ...  # per segment
```

Every stage leaves its input unchanged, returns a new valid payload, and takes the
`Bounds` even when it does not use them, so it is a `Shape` (`dash` and `densify` through
`functools.partial`).

| ID | Row |
|---|---|
| SH-1 | `Shape` is exported from `core/shape.py` as the alias of ADR 0003 §1 |
| SH-2 | `corners`: each segment of `m >= 2` anchors becomes `m - 1` straight curves with handles at 1/3 and 2/3 (Manim's `add_points_as_corners`); a segment of one anchor becomes one curve of four equal points. Invalid samples, being uncovered, are dropped; the output has `valid=None` |
| SH-3 | `smooth`: as `corners`, with the handles of Manim's `get_smooth_cubic_bezier_handle_points` for each segment's anchors — the closed variant when its first and last anchors coincide (Manim's `use_smoothing=True`). Reimplemented in the core; equal to Manim's within `1e-12` relative |
| SH-4 | `clip` on a curve path: each curve is split at every parameter in `(0, 1)` where its `x` or `y` crosses a side of the box (roots of the cubic), and the sub-curves whose parameter midpoint lies in the closed box are kept, contiguous ones joined into one segment. A curve whose four points are inside is kept whole and not split. Crossing anchors lie on the box side within `1e-9` of the box's size. A path wholly outside gives no segment (`(0, 2)`) |
| SH-5 | `clip` on `points`: `valid` becomes false at every sample outside the box (`contains`); coordinates and the segment are unchanged |
| SH-6 | `clip` on a `region`: conservative whole-cell removal (`docs/scope.md`): a cell with any corner outside the box or invalid is dropped; the result carries a cell array (a grid topology is expanded first) |
| SH-7 | `dash` on a curve path (F-806): `on > 0`, `off >= 0`, `phase` finite, else `ValueError`. Along each segment, by arc length measured from the segment's start, the pattern `on, off, on, …` begins `phase` into itself, so every segment restarts the phase (ADR 0003 §1). Each dash is one output segment of curves split at the exact arc-length positions (within `1e-9` of the segment's length); `off == 0` returns the path unchanged |
| SH-8 | Dashes are stable under resampling: the same geometry with different anchors gives dash ends at the same arc-length positions, within `1e-9` relative |
| SH-9 | `arc_length(payload)` of a curve path: the length of each segment, by an 8-point Gauss-Legendre rule per curve *(default taken)*, accurate to `1e-9` relative for the curves `smooth` makes of a sampled smooth function |
| SH-10 | `densify(..., pieces=k)`: every curve is split into `k` curves of equal parameter span (de Casteljau), `k >= 1` else `ValueError`; the geometry is unchanged (F-914: sparse leaves bend under a non-affine frame) |
| SH-11 | `smooth`, `corners`, `dash`, `densify` on a `points` or `region` payload raise `ValueError` naming the kind; `clip` accepts all three kinds |
| SH-12 | Empty input gives empty output of the same kind, every stage |

## PA — `core/params.py` (F-110, F-911, F-918, ADR 0003 §4)

```python
class Parameter(Generic[T]):
    def __init__(
        self, value: Any, *, name: str, validate: Callable[[Any], T] | None = None
    ) -> None: ...
    @property
    def name(self) -> str: ...
    @property
    def value(self) -> T: ...
    @value.setter
    def value(self, value: Any) -> None: ...
    @property
    def tracker(self) -> object | None: ...
    @property
    def version(self) -> int: ...
    def bind(self, source: object) -> None: ...
    def unbind(self) -> None: ...
    def poll(self, token: int | None = None) -> int: ...


class Param(Generic[T]):  # descriptor
    def __init__(
        self, default: Any, *, validate: Callable[[Any], T] | None = None
    ) -> None: ...
```

| ID | Row |
|---|---|
| PA-1 | `Parameter(value, name=..., validate=...)` runs `validate` (identity when `None`) on the initial value and every assignment; its `ValueError`/`TypeError` propagate and leave the value and version unchanged |
| PA-2 | A stored value is immutable: an array is copied and made read-only, a list or tuple of numbers becomes a read-only array *(default taken)*, a scalar stays a scalar |
| PA-3 | Our own parameters never compare values (plan, *Bound parameters are polled*): every assignment increments `version` by one, equal value or not |
| PA-4 | `bind(source)`: a **foreign** source is an object with `get_value()` (Manim's `ValueTracker`, duck-typed: the core cannot import it); anything else callable is a **callable** binding; anything else raises `TypeError`. `tracker` returns the bound source, or `None`. Assigning a value while bound unbinds first. `unbind()` keeps the last value |
| PA-5 | `poll(token)` reads a foreign source: the value is validated and snapshotted (PA-2), and compared with the last snapshot NaN-aware — scalars equal or both `NaN`, arrays by `np.array_equal(..., equal_nan=True)` against the copy, never a live view — and `version` increments only when it differs (F-110). A source mutated in place without a `set_value` is still seen, because the comparison is against a copy |
| PA-6 | A **callable** binding is dirty once per token (ADR 0003 §4): `poll(token)` with a token different from the last one calls it, stores the result and increments `version`; the same token again neither calls nor increments. `poll()` without a token on a callable binding raises `ValueError` *(default taken)*. `value` returns the last stored result and never calls |
| PA-7 | `version` reads without polling; `poll` returns the version after polling. An unbound parameter's `poll` returns `version` unchanged |
| PA-8 | `Param(default, validate=...)` is a descriptor: on an instance, attribute access returns that instance's own `Parameter` (created on first access, named after the attribute), assignment sets its `value` (`ax.x.range = (0, 30)`, F-911); on the class it returns the descriptor. No `__setattr__` override is involved |
| PA-9 | `Parameter` and `Param` are generic and fully annotated (F-1005); mypy infers `T` from `validate` |

## BM — benchmark

| ID | Row |
|---|---|
| BM-1 | `tests/benchmark/test_core_pipeline.py`: four artists — `FunctionSource` with `use_vectorized=True` and `x_range` steps giving 2 000 samples — through `sample`, `Chain.apply_payload`, `smooth`, `clip` and `FrameMap.forward`, over 60 frames of an animated range, on an affine and on a warped frame. Reports p50/p95/max per frame; recorded, not gated. The first reading of F-1001's 4 ms margin, core only |

## Tests

| File | Rows |
|---|---|
| `tests/core/test_sources.py` | B-1 … B-3, FS-1 … FS-10, PS-1 … PS-4, AS-1 … AS-6 |
| `tests/core/test_shape.py` | SH-1 … SH-12, and the pipeline order of ADR 0003 §1: a segment from outside to outside across the viewport, a single point, a pole gap |
| `tests/core/test_params.py` | PA-1 … PA-9 |
| `tests/benchmark/test_core_pipeline.py` | BM-1 |
