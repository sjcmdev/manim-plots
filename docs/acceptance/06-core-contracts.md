# Acceptance table — task 06, core contracts

**Status: Living until task 06 merges, then Record.** Written 2026-10-29 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts come from ADR 0001 §3 and ADR 0003 §§1-3; this table
only fills in what they leave open. Row IDs are cited by the tests.

Modules: `src/manim_plots/core/__init__.py`, `core/payload.py`, `core/scales.py`,
`core/nodes.py`, `src/manim_plots/mobjects/__init__.py`, `mobjects/context.py`,
`src/manim_plots/__init__.py`.

## C — `manim_plots.core`

| ID | Row |
|---|---|
| C-1 | `FloatArray = NDArray[np.float64]`, `BoolArray = NDArray[np.bool_]`, `IntArray = NDArray[np.intp]`, defined in `core/__init__.py` |
| C-2 | `class ManimPlotsWarning(UserWarning)`, defined in `core/__init__.py`, re-exported as `manim_plots.ManimPlotsWarning` |
| C-3 | `core/__init__.py` imports nothing from its submodules, so importing one submodule loads no other |

## P — `core/payload.py`

```python
Kind = Literal["path", "points", "region"]


@dataclass(frozen=True)
class Payload:
    kind: Kind
    coords: FloatArray  # (n, d)
    segments: IntArray  # (s, 2), half-open [start, stop)
    topology: IntArray | tuple[int, int] | None = None
    valid: BoolArray | None = None

    @classmethod
    def path(cls, coords: FloatArray, valid: BoolArray | None = None) -> Payload: ...
    @classmethod
    def points(cls, coords: FloatArray, valid: BoolArray | None = None) -> Payload: ...
    @classmethod
    def empty(cls, kind: Kind, dim: int) -> Payload: ...


def split_segments(segments: IntArray, valid: BoolArray) -> IntArray: ...
```

Validation runs in `__post_init__`, in the order of the rows below; the first failure
raises. A message names the field, and the offending index, pair or cell.

| ID | Input | Result |
|---|---|---|
| P-1 | `kind` not a `str` | `TypeError` |
| P-2 | `kind` a `str` other than the three | `ValueError` |
| P-3 | `coords` not an `ndarray` of a floating dtype (a list, an integer or boolean array) | `TypeError` |
| P-4 | `coords.ndim != 2` | `ValueError` |
| P-5 | `coords` of another float width | accepted; stored as `float64` |
| P-6 | `segments` not an `ndarray` of an integer dtype (`bool` is not an integer here) | `TypeError` |
| P-7 | `segments` not of shape `(s, 2)` | `ValueError` |
| P-8 | a pair with `start < 0`, `stop > n` or `stop <= start` | `ValueError` naming the pair's index and its values |
| P-9 | a pair starting before the previous one stops (unsorted or overlapping) | `ValueError` naming the pair's index. Touching pairs, `[a, b)` then `[b, c)`, are legal: a split with no invalid sample between, which F-705's sign-change split needs |
| P-10 | `kind` `points` or `region` with segments other than `[[0, n]]` for `n > 0`, or other than shape `(0, 2)` for `n == 0` | `ValueError` |
| P-11 | `valid` not `None` and not an `ndarray` of `bool` dtype | `TypeError` |
| P-12 | `valid` not of shape `(n,)` | `ValueError` |
| P-13 | a non-finite sample (any coordinate) while `valid is None` | `ValueError` naming the sample index |
| P-14 | a non-finite sample where `valid` is true | `ValueError` naming the sample index |
| P-15 | `kind="path"`: a sample covered by a segment where `valid` is false, or uncovered where `valid` is true (`valid is None` means every sample is valid, so every sample must be covered) | `ValueError` naming the sample index |
| P-16 | `kind` `path` or `points` with a topology | `ValueError` |
| P-17 | `kind="region"` with `topology=None` | `ValueError` |
| P-18 | topology neither a tuple nor an `ndarray`; a tuple not of two `int`s (`bool` excluded); an array of a non-integer dtype | `TypeError` |
| P-19 | grid tuple `(rows, cols)` with `rows < 1`, `cols < 1` or `rows * cols != n` | `ValueError` |
| P-20 | cell array not of shape `(m, k)` with `k >= 3` | `ValueError` |
| P-21 | a cell index outside `[0, n)`, or a cell with a repeated corner | `ValueError` naming the cell |
| P-22 | inconsistent winding: the signed (shoelace) area of the cells over `coords[:, :2]` changes sign. Cells with a non-finite or invalid corner and cells of zero area are skipped. A region with `d < 2` raises `ValueError` *(default taken)* | `ValueError` naming the first cell whose sign differs from the first cell with a non-zero area |
| P-23 | after validation `coords`, `segments`, `valid` and an array topology are views with `writeable=False`; a write raises `ValueError` (NumPy's) | — |
| P-24 | the payload is frozen: assigning a field raises `dataclasses.FrozenInstanceError` | — |
| P-25 | `Payload.path(coords, valid)` — segments are the maximal runs of valid samples (one run covering everything when `valid is None`); `valid` is kept as given. The same `ValueError`s as the constructor for a non-finite sample with `valid=None` | — |
| P-26 | `Payload.points(coords, valid)` — one segment `[[0, n]]`, or `(0, 2)` when `n == 0` | — |
| P-27 | `Payload.empty(kind, dim)` — `coords` of shape `(0, dim)`, segments `(0, 2)`, `valid=None`; for `region` the topology is an empty cell array of shape `(0, 4)` *(default taken)*. `dim < 1` raises `ValueError` | — |
| P-28 | `split_segments(segments, valid)` returns the maximal runs of `True` in `valid` inside each given segment, in order, as a new `(s', 2)` `intp` array; a segment with no valid sample disappears. `valid` of the wrong shape raises `ValueError` | — |
| P-29 | an empty `path` payload (`n == 0`) has segments of shape `(0, 2)`; a `path` with `n > 0` and every sample invalid also has `(0, 2)` segments | legal |

## S — `core/scales.py`

```python
@runtime_checkable
class Scale(Protocol):
    @property
    def domain(self) -> tuple[float, float]: ...
    @property
    def closed(self) -> tuple[bool, bool]: ...
    @property
    def increasing(self) -> bool: ...
    def forward(self, x: ArrayLike) -> FloatArray: ...
    def inverse(self, u: ArrayLike) -> FloatArray: ...
    def limit_range(
        self, lo: float, hi: float, minpos: float
    ) -> tuple[float, float]: ...


@dataclass(frozen=True)
class LinearScale: ...


@dataclass(frozen=True)
class LogScale:
    base: float = 10.0


@dataclass(frozen=True)
class SymLogScale:
    base: float = 10.0
    linthresh: float = 1.0
    linscale: float = 1.0


class FunctionScale:
    def __init__(
        self, forward, inverse, domain, closed=(False, False), increasing=True
    ): ...


MINPOS_UNKNOWN = 1e-300
```

Public names are matplotlib's, with the protocol as a suffix, so no two names collide
under `from manim_plots import *` — the locator called `Log` in ADR 0001 §2 is
`LogLocator` *(default taken)*.

| ID | Row |
|---|---|
| S-1 | All four satisfy `isinstance(s, Scale)`; `domain`, `closed`, `increasing` are read-only (assignment raises `AttributeError`, or `FrozenInstanceError` for a dataclass) |
| S-2 | `forward` and `inverse` accept anything `np.asarray(..., dtype=float)` takes, a scalar included, and return a new `float64` array of the input's shape (0-d for a scalar). They never emit a NumPy `RuntimeWarning` |
| S-3 | **The `NaN` rule**, both directions, every scale: the result is `NaN` where the input is `NaN` or infinite, where `forward`'s input lies outside the domain (an open bound itself included), and where the output is non-finite or (for `inverse`) outside the domain. Nothing raises for a value; the caller applies the surface rule |
| S-4 | `LinearScale`: domain `(-inf, inf)`, `closed=(False, False)`, `increasing=True`; `forward` and `inverse` are the identity on finite input |
| S-5 | `LogScale(base)`: domain `(0, inf)`, open at both ends; `forward(x) = log(x) / log(base)`, `inverse(u) = base ** u`; `increasing` is `base > 1`. `base` not a real number: `TypeError`; non-finite, `<= 0` or `== 1`: `ValueError` (matplotlib's rule) |
| S-6 | `SymLogScale(base, linthresh, linscale)` is matplotlib's `SymmetricalLogTransform`: with `a = linscale / (1 - 1/base)`, `forward(x) = x * a` for `abs(x) <= linthresh`, else `sign(x) * linthresh * (a + log(abs(x)/linthresh) / log(base))`; `inverse` is its exact inverse. Domain `(-inf, inf)`, `increasing=True`. `base <= 1`, `linthresh <= 0`, `linscale <= 0` or a non-finite one: `ValueError` |
| S-7 | Round trip (F-305, ADR 0003 §3): `inverse(forward(x))` equals `x` within `1e-9` relative, for every in-domain `x` with `1e-300 <= abs(x) <= 1e300`, and `0` where the domain holds it (Hypothesis, plus the anchors `0`, `±linthresh`, `±1e-300`, `±1e300`) |
| S-8 | Monotonicity: `forward` is strictly monotonic in the declared direction on any two distinct in-domain samples whose images are distinct floats |
| S-9 | `limit_range(lo, hi, minpos)`: `lo` or `hi` non-finite raises `ValueError` naming it; `minpos` not finite and positive raises `ValueError`. An end inside the domain is returned unchanged. An end beyond a **closed** bound becomes the bound. An end at or beyond an **open** finite bound `b` becomes the nearest float at least `minpos` inside it: `max(b + minpos, nextafter(b, +inf))` at a lower bound, symmetric at an upper one. Order is kept: `(10, -5)` under log gives `(10, minpos)`. Both ends outside the domain on the same side raises `ValueError` (F-409, ADR 0003 §2). The result is a tuple of Python `float`s |
| S-10 | `MINPOS_UNKNOWN == 1e-300`, the `minpos` a caller passes when it knows none (F-311) |
| S-11 | `LinearScale`, `LogScale`, `SymLogScale` are hashable and compare by value; `LogScale(10) == LogScale(10.0)` |
| S-12 | `FunctionScale` argument checks: `forward` or `inverse` not callable, `closed` not a pair of `bool`, `increasing` not a `bool`: `TypeError`. `domain` not a pair of real numbers: `TypeError`; a `NaN` bound, `lo >= hi`: `ValueError`; an infinite bound declared closed: `ValueError` |
| S-13 | `FunctionScale` falsification (F-305), at construction. Samples: on a finite domain `[a, b]`, 64 interior points `a + (b - a) * (k + 0.5) / 64`; on `(a, inf)`, `a + logspace(-6, 6, 64)`; on `(-inf, b)`, `b - logspace(-6, 6, 64)`; on `(-inf, inf)`, `-logspace(-6, 6, 32)`, `0`, `logspace(-6, 6, 32)`; each closed bound added. Checks in this order, each a `ValueError` whose message contains the quoted word and the first failing sample: (1) **"vectorized"** — `forward` called on the sample array returns an array of its shape equal (NaN-aware, `rtol=1e-12`) to the per-sample calls on 0-d arrays, and an exception from the array call is chained; the same for `inverse` on the images; (2) **"finite"** — every image is finite; (3) **"monotonic"** — the images are strictly ordered in the declared direction; (4) **"round trip"** — `abs(inverse(forward(x)) - x) <= 1e-9 * abs(x) + 1e-12`. The docstring says this is a heuristic blind to a reversal between samples |
| S-14 | `FunctionScale.forward` calls the user's `forward` only on finite in-domain input — an out-of-domain value never reaches it — and applies S-3 to the result; `inverse` the same with the user's `inverse` on finite input |
| S-15 | `FunctionScale` compares by identity |

## N — `core/nodes.py` (internal: not exported, imported by the tests by path)

```python
SINGULAR_RTOL = 1e-12      # smallest / largest singular value at or below: singular
AFFINE_RTOL = 1e-9         # frame affine when the fit residual is at most this x size
PLANE_RTOL = 1e-6          # off-plane distance accepted by FrameMap.inverse, x size
FRAME_NODES = 33           # N, the grid density (ADR 0001, What stays open)

class Node(Protocol):
    @property
    def dim(self) -> int: ...
    @property
    def is_affine(self) -> bool: ...
    @property
    def matrix(self) -> FloatArray | None: ...   # (dim+1, dim+1), column vectors
    def apply(self, x: FloatArray) -> FloatArray: ...      # (n, dim) -> (n, dim)
    def inverse(self, y: FloatArray) -> FloatArray: ...
    def valid(self, x: FloatArray) -> BoolArray: ...       # (n,)

class AffineNode:      # AffineNode(matrix) and AffineNode.from_parts(linear, offset)
class ScaleNode:       # ScaleNode(scale, axis, dim)
class FunctionNode:    # FunctionNode(function, inverse=None, *, dim)
class Chain:           # Chain(nodes)
class FrameMap:        # FrameMap(lower, upper, nodes)
class SystemMap:       # SystemMap(data, frame, own=None) — satisfies CompiledMap
```

| ID | Row |
|---|---|
| N-1 | `AffineNode(matrix)`: `matrix` a finite `(d+1, d+1)` array whose last row is `[0, …, 0, 1]`, else `ValueError`; `apply(x) = x @ M[:d, :d].T + M[:d, d]`. `AffineNode.from_parts(linear (d, d), offset (d,))` builds the same. `is_affine` is `True`; `matrix` returns a read-only view |
| N-2 | `AffineNode.inverse` raises `ValueError` mentioning "singular" when the linear part's smallest singular value is at most `SINGULAR_RTOL` times its largest, or the largest is 0 |
| N-3 | `ScaleNode(scale, axis, dim)` applies `scale.forward` to column `axis` and passes the others through; `inverse` applies `scale.inverse` there. `is_affine` is `True` exactly for a `LinearScale`, whose `matrix` is the identity; otherwise `matrix` is `None`. `axis` outside `[0, dim)` raises `ValueError` |
| N-4 | `FunctionNode(function, inverse=None, *, dim)` is never affine; `inverse` raises `ValueError` when no inverse was given |
| N-5 | `valid(x)` of every node is `True` exactly where every input coordinate is finite, the input lies in the node's domain (a `ScaleNode`'s scale domain on its axis), and the output is finite |
| N-6 | `Chain(nodes)` compiles: each maximal run of adjacent affine nodes collapses into one `AffineNode` whose matrix is the product in order (the later node's matrix on the left); a non-affine node is a barrier. `chain.nodes` is the compiled tuple; `chain.is_affine` is `True` when it compiled to at most one affine node (an empty chain is the identity). Nodes of different `dim`: `ValueError` |
| N-7 | `Chain.forward(x)` equals applying the original nodes one after another, within `1e-12` relative; `Chain.inverse(y)` applies the inverses in reverse order |
| N-8 | `Chain.apply_payload(payload)` — `Map` owns validity (ADR 0003 §1): at each compiled node, the mask is the incoming `valid` (all true for `None`) AND the node's `valid` at the current coordinates; coordinates become the node's output. A `path` gets `split_segments(payload.segments, mask)`; `points` and `region` keep their segments. `kind` and `topology` pass through. `valid` is `None` when the incoming one was `None` and the mask is all true, else the mask. A sample a node rejects keeps its row (possibly `NaN`) with `valid` false. Returns a new `Payload`; the input is unchanged |
| N-9 | The two-node case of ADR 0003 §1: a chain `shift x by -2` then `LogScale` on x, over the path `x = [1, 3, 4, 5]`: `valid == [False, True, True, True]`, segments `[[1, 4]]`; and a sample invalid on entry stays invalid |
| N-10 | `FrameMap.lattice(lower, upper, n)` (static) returns the `(n*n, 3)` reference nodes, row-major: node `j*n + i` sits at local `(lower[0] + i*(upper[0]-lower[0])/(n-1), lower[1] + j*(upper[1]-lower[1])/(n-1), 0)` |
| N-11 | `FrameMap(lower, upper, nodes)`: `nodes` the `(n*n, 3)` scene positions of the lattice nodes, `n >= 2` inferred from the length; anything else, or `upper <= lower` on an axis, raises `ValueError`. The arrays are copied read-only |
| N-12 | `is_affine`: the least-squares affine fit of `nodes` against the lattice leaves a max residual of at most `AFFINE_RTOL` times the frame size, the diagonal of the nodes' bounding box (a frame of size 0 is affine) |
| N-13 | `is_singular`: `is_affine` and the fit's in-plane linear part (the images of local x and y) has its smallest singular value at most `SINGULAR_RTOL` times its largest, or the largest is 0 |
| N-14 | `forward(local)`: `local` of shape `(m, 2)` or `(m, 3)` (a missing z is 0), returns `(m, 3)` scene points. Affine: the fit, with local z along the unit normal of the in-plane part, `cross(image of x, image of y)` normalised (so the identity frame maps z to z). Non-affine: bilinear interpolation of the four nodes of the cell containing `(x, y)`, cells extrapolated at the rectangle's edge, plus z along the fit's unit normal. At every lattice node, `forward` returns that node's position within `1e-12` of the frame size |
| N-15 | `inverse(scene)` returns `(m, 3)` local points with `z = 0`. A singular frame raises `ValueError` mentioning "singular" and changes nothing (ADR 0003 §6). A point farther from the frame's plane than `PLANE_RTOL` times the frame size raises `ValueError` naming its index; a nearer one is projected (F-207). Non-affine: Newton from the affine fit's solution, at most 50 steps to a residual of `1e-11` times the frame size; no convergence raises `ValueError` naming the index. The docstring says the branch returned is the one Newton reaches from the affine guess (F-201) |
| N-16 | Round trip (F-201, ADR 0003 §3): on an affine, non-singular frame, `inverse(forward(p)) == p` within `1e-9` times the lattice rectangle's diagonal; on a smooth non-affine frame the same holds inside the rectangle |
| N-17 | `SystemMap(data, frame, own=None)` satisfies `CompiledMap`: `forward` is `data.forward` (data to local, `dim` 2), `inverse` `data.inverse`, `valid` `data.valid`; `to_screen(x)` is `frame.forward(own.forward(pad(data.forward(x))))` with `pad` adding `z = 0` and `own` a `dim`-3 `Chain` (identity when `None`). `is_affine` is `data`, `own` and `frame` all affine. A `data` chain whose `dim` is not 2 raises `ValueError` |

## K — pins, `mobjects/context.py` (F-917)

```python
SYMBOLS: tuple[Callable[..., object], ...]  # the inventory
PINS: Mapping[str, Mapping[str, str]]  # Manim version -> qualname -> sha256


def symbol_name(symbol) -> str: ...  # its __qualname__
def source_hashes() -> dict[str, str]: ...  # for the installed Manim
def check_pins(version: str | None = None) -> None: ...
```

| ID | Row |
|---|---|
| K-1 | `SYMBOLS` holds PoC 4's 68 symbols (`poc/poc4/evidence.py::SYMBOLS`) plus `DrawBorderThenFill.begin` (which assigns `outline`) and `Mobject.get_family_updaters` (0.21.0's moving-object query), and nothing twice. Every symbol is importable on both supported versions |
| K-2 | `source_hashes()` maps `symbol_name(s)` to the SHA-256 of `"".join(inspect.getsourcelines(s)[0])`, UTF-8, for every symbol; names are unique |
| K-3 | `PINS` has exactly the keys `"0.21.0"` and `"0.22.0"`, each mapping every symbol name to its hash on that version. On the installed version, `source_hashes() == PINS[manim.__version__]` |
| K-4 | `check_pins(version)` — `version` defaults to `manim.__version__`. An unpinned version warns `ManimPlotsWarning` naming the version and the supported ones; a pinned version whose hashes differ warns `ManimPlotsWarning` naming the first symbol that differs. Nothing raises. `import manim_plots` calls it once |
| K-5 | Line numbers are never stored in `PINS`; anything that needs a line derives it from source at import (F-917) |
| K-6 | `Scene.get_moving_mobjects` sees a mobject whose updater list (`.updaters`, also through `get_family_updaters()`) holds a `dt`-free updater on both versions, directly and as a submobject: the query the library's synchronisation updater reports through (ADR 0003 §5) |

## L — layers (ADR 0001 §1)

| ID | Row |
|---|---|
| L-1 | No module under `src/manim_plots/core/` imports `manim` (any submodule) or `manim_plots.mobjects` (absolute or relative) — checked on the parsed source |
| L-2 | No module other than `src/manim_plots/mobjects/context.py` names `_getframe`, `currentframe`, `f_code`, `f_locals` or `f_back` — as an attribute, a name or an imported name |
| L-3 | ruff `TID251` bans `manim` imports outside `mobjects/`, the package `__init__.py`, `tests/` and `tools/` |

## A — public surface (D12, ADR 0003 §8)

| ID | Row |
|---|---|
| A-1 | `manim_plots.__all__` lists only names that exist on the package and that Manim's namespace (`dir(manim)`) lacks, on both versions |
| A-2 | After task 06, `__all__` is exactly `__version__`, `ManimPlotsWarning`, `Scale`, `LinearScale`, `LogScale`, `SymLogScale`, `FunctionScale`, `Payload`, `CompiledMap`. Later tasks extend it; the planned 0.1 list is below |
| A-3 | `CompiledMap` (the protocol of ADR 0001 §3, read-only `is_affine`) lives in `core/nodes.py`, runtime-checkable; `SystemMap` satisfies it |

**Planned 0.1 names**, for later tasks to add (each checked by A-1 when added):
`Bounds`, `Source`, `Shape`, `FunctionSource`, `ArraySource`, `ParametricSource` (07);
`Locator`, `MaxNLocator`, `MultipleLocator`, `LogLocator`, `SymLogLocator`,
`FixedLocator`, `NullLocator`, `MinorCountLocator`, `Formatter`, `Labels`,
`DecimalFormatter`, `FormatStrFormatter`, `ScientificFormatter`, `EngFormatter`,
`FixedFormatter`, `NullFormatter` (08); `CartesianAxes` (09-10; `mp.Axes` and
`mp.NumberPlane` reachable but not star-exported); the artist classes (11); `Legend`,
`LineStyle`, `Marker`, `DrawAxes`, `TraceCurve`, `ShowPoints`, `Morph` (12)
*(default taken)*.

## Tooling (Claude, before the tests)

- `scipy>=1.15` declared (Manim's own floor on Python 3.13); lock rewritten with uv 0.10.4.
- ruff: `TID251` with `manim` banned, per-file ignores for `mobjects/`, `__init__.py`,
  `tests/`, `tools/`.
- `tests/conftest.py`: a Hypothesis profile `gate` — `derandomize=True`, `database=None`,
  `deadline=None` — loaded by default; `HYPOTHESIS_PROFILE` selects another.
- `pyproject.toml`: `filterwarnings = ["error::manim_plots.ManimPlotsWarning"]`.
- `.venv-0.22/` (git-ignored) with Manim 0.22.0, for running the tests on both versions
  without `uv run --isolated`.

## Tests

| File | Rows |
|---|---|
| `tests/core/test_payload.py` | P-1 … P-29 |
| `tests/core/test_scales.py` | S-1 … S-15 |
| `tests/core/test_nodes.py` | N-1 … N-17 |
| `tests/mobjects/test_manim_contract.py` | K-1 … K-6 |
| `tests/test_layers.py` | L-1, L-2 |
| `tests/test_public_api.py` | A-1 … A-3, C-2 |
