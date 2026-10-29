# Acceptance table — task 09, leaves, context, frame

**Status: Living until task 09 merges, then Record.** Written 2026-10-29 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: ADR 0001 §4 (surviving Manim's transformations, the
leaf lifecycle), ADR 0003 §5 and §6; `docs/plan.md`, *Integration*; `docs/scope.md`
F-101, F-102, F-111, F-112, F-208, F-701, F-702, F-708, F-709, F-901-F-905, F-914-F-917,
F-1004, F-1007; the mechanism of PoC 4 (`poc/poc4/model.py`, `context.py`). Builds on
tasks 06-08: the frame map, the pipeline, parameters, ticks, the lifecycle reducer.

Modules: `src/manim_plots/mobjects/leaves.py`, `mobjects/context.py` (the stack readers
join the pins), `mobjects/system.py`, `mobjects/axis.py`, `mobjects/artists.py`.

**Scope of the system in this task.** Two axis lines, major ticks without numbers, tips,
the hidden frame, `c2p`/`p2c`, a range parameter per axis, and one analytic artist from
`ax.plot(f)`. Numbers, labels, `axis_config`, grids and the rest of the decoration are
task 10; the other artists, `.animate` on data and `Transform` between systems are task
11. Where a row below compares with Manim, the oracle is Manim's own `Axes` run in the
same test, never a value computed by the library.

## AX — `CartesianAxes`

```python
class CartesianAxes(VGroup):
    def __init__(
        self,
        x_range: Sequence[float] | None = None,
        y_range: Sequence[float] | None = None,
        x_length: float | None = None,
        y_length: float | None = None,
        *,
        tips: bool = True,
    ) -> None: ...

    x_axis: Axis
    x: Axis  # the same object (F-602)
    y_axis: Axis
    y: Axis
    frame: FrameLeaf  # the hidden grid (F-914)

    def c2p(self, *coords) -> np.ndarray: ...  # coords_to_point
    def p2c(self, point) -> np.ndarray: ...  # point_to_coords
    def __matmul__(self, coords) -> np.ndarray: ...
    def plot(
        self, function, x_range=None, use_vectorized=False, **kwargs
    ) -> FunctionPlot: ...
    def set_x_range(self, x_range) -> Self: ...
    def set_y_range(self, y_range) -> Self: ...
    def add(self, *artists) -> Self: ...  # registers; F-708


Axes = CartesianAxes  # manim_plots.Axes, not star-exported


class Axis(VGroup):
    line: AxisLine
    ticks: VGroup  # major ticks, NumberLine's name
    tip: TipLeaf | None
    range: Param  # (lo, hi), read-only array value
```

| ID | Row |
|---|---|
| AX-1 | Defaults are Manim's `Axes()` at the default config: `x_range=[-7, 7, 1]`, `y_range=[-4, 4, 1]` (from the frame radius, rounded), `x_length=12`, `y_length=6`, `tips=True`. A two-element range has step 1; a step installs `MultipleLocator(step)` (D12). `mp.Axes is mp.CartesianAxes`; `CartesianAxes` is star-exported, `Axes` is not (A-1) |
| AX-2 | A range with a non-finite entry, `lo == hi`, or not of length 2 or 3: `ValueError` naming `x_range`/`y_range`; a step `<= 0`: `ValueError` naming the step (F-409); a length `<= 0` or non-finite: `ValueError` naming it. Under the OpenGL renderer construction raises `ValueError` naming Cairo (F-1007) |
| AX-3 | Family: `ax.submobjects == [ax.x_axis, ax.y_axis, ax.frame]` — the frame last (ADR 0001 §4); an axis holds its `line`, its `ticks` group and its `tip`. Every family member with points is an instance of `manim_plots.mobjects.leaves.Leaf` (F-1004); an artist is never in the family (F-708) |
| AX-4 | Geometry and style match Manim's `Axes` built with the same arguments — the oracle is Manim's object in the same test: each axis line's points equal the `NumberLine`'s, each tip's points and fill equal Manim's tip's, every Manim tick has a tick of equal points at the same place, within `1e-9`; stroke colour, width and opacity of lines, ticks and tips equal Manim's. The one difference: the tick under a tip, which Manim drops, is kept (F-411, the defaults table). Cases: the default, `x_range=(0, 10, 1), y_range=(-2, 2, 0.5)`, `x_range=(-3, 5), x_length=8, tips=False` |
| AX-5 | `c2p` and `p2c` follow Manim's calling convention and return Manim's values on every input Manim maps (the oracle is Manim's `Axes`): `c2p(x, y)` → `(3,)`; `c2p(xs, ys)` with arrays → `(3, n)`; `c2p(array of shape (n, 2))` → `(n, 3)`; `p2c(point)` → `(2,)`; `p2c(points of shape (n, 3))` → `(n, 2)` (corrected after Codex's run: Manim's shape, the oracle, not the `(2, n)` first written here). `ax @ (x, y)` is `c2p` |
| AX-6 | `c2p` raises `ValueError` on a non-finite coordinate or one outside a scale's domain, `p2c` on a non-finite point and on a point off the plane (F-207, task 06's `PLANE_RTOL`); neither ever returns `NaN` (F-202) |
| AX-7 | `p2c(c2p(x, y)) == (x, y)` within `1e-9` times the range span, everywhere in the range, after any affine operation on `ax` (F-201, F-208: rotate, scale, stretch, shift, flip, apply_matrix, and the defect 14 set) |
| AX-8 | `ax.x is ax.x_axis` (F-602). `ax.x.range` is a parameter (F-911): `.value` a read-only `(lo, hi)` array, `ax.x.range = (0, 20)` sets it, as does `ax.set_x_range((0, 20))`; `ax.x.range.bind(callable)` binds it (task 07, PA-4). A range change regenerates the ticks and the lines (F-412), never changes the locator (a step given later is a locator change, task 10), and rebuilds every artist bound to `ax` lazily (F-102) |
| AX-9 | `ax.plot(f, x_range=None, use_vectorized=False, **kwargs)` returns a registered `FunctionPlot` over a `FunctionSource` (F-701, F-702). Keywords other than those are `VMobject` style keywords; the default stroke is Manim's plot default (white, width 4). A parameter name of `f` after the first (F-702) is task 11's |
| AX-10 | `ax.add(artist)` registers an artist (F-708) and returns `ax`; adding it again to its own system does nothing; registering an artist bound to another system raises `ValueError` (F-112). Adding `ax` to a scene adds no artist; adding an artist separately is allowed (F-709) |

## LF — leaves (`mobjects/leaves.py`)

| ID | Row |
|---|---|
| LF-1 | `Leaf(VMobject)` is the base of every library-generated leaf; `points` is a property on it (F-901) |
| LF-2 | While nothing is dirty, two reads of `points` return the same object (F-902): identity, not equality |
| LF-3 | A data change — a range, a parameter, a bound tracker — marks the leaves that depend on it dirty, and the next read of `points` rebuilds; a read with nothing dirty does not rebuild (F-102) |
| LF-4 | `FunctionPlot.points` is the curve through the frame: every anchor lies on `c2p(x, f(x))` of its own sample within `1e-9`, its ends are where the viewport cuts the curve or where `x_range` ends, and it never leaves the axes' rectangle (F-706, F-107). A pole splits it into subpaths (F-705) |
| LF-5 | The frame (F-914) is invisible under every style call — `set_color`, `set_stroke`, `set_fill`, `set_opacity`, `fade`, `match_style` on `ax` leave its stroke and fill opacity 0 — ignores partial drawing (`pointwise_become_partial` leaves its points), and gives no boundary anchors: `ax.get_center()`, `ax.width`, `ax.height` equal those of a `VGroup` of `ax`'s other leaves |
| LF-6 | Every generated leaf type survives `copy()`, keeping its type (F-1004) |

## WR — writes outside animations (F-904, F-208)

The oracle is a **plain twin**: a `VGroup` of plain `VMobject`s with the same points, in
the same container structure, given the same operation. A row passes when every library
leaf ends where its twin does, within `1e-9` for an affine operation and `1e-2` for a
non-affine one (the bilinear frame, ADR 0001 §4).

| ID | Row |
|---|---|
| WR-1 | An operation on `ax` — `shift`, `rotate`, `scale`, `stretch`, `flip`, `apply_matrix`, `move_to`, `next_to`, `to_corner`, `apply_function` — moves its leaves and every artist bound to it, as the twin of `VGroup(ax's leaves, artist)` moves (the frame moved; the artists follow it, F-914) |
| WR-2 | `VGroup(ax, curve).shift(v)`, in either order and nested one level, moves the curve once (F-904: the container holds the frame, the write is ignored) |
| WR-3 | `VGroup(curve, dot).shift(v)` moves the curve as the twin; the move is the curve's own transform and survives a later data change (`ax.x.range = ...`): the rebuilt curve stays offset by `v` from where it would be |
| WR-4 | `curve.shift(UP)` then `ax.shift(RIGHT)`: the curve is where the twin of `ax` + the shifted curve ends — its own transform lives in the system's local space and moves with `ax`; after `ax.rotate(θ)` it turns with `ax` |
| WR-5 | `curve.rotate`, `curve.scale`, `curve.stretch`, `curve.apply_matrix` become exact matrices of the own transform: after the operation and a data change the curve equals the twin given the same operation after the same data change |
| WR-6 | A bare NumPy write into `curve.points` stays until the next rebuild; `curve.refresh()` replaces it with the derived points (F-111) |
| WR-7 | After `ax.scale(0)`, `p2c` raises `ValueError` mentioning "singular", and an operation that needs the inverse — `curve.shift(UP)` — raises `ValueError` and leaves `curve` unchanged (ADR 0003 §6) |

## AN — animations (F-903, F-905, F-907, F-916)

The oracle is again a plain twin, animated by the same Manim animation in the same scene.
These rows cover the mechanism; task 11's F-906 matrix covers every animation.

| ID | Row |
|---|---|
| AN-1 | `Create(curve)`: every rendered frame equals `Create` of the curve's twin; after it the curve is attached: a later range change rebuilds it |
| AN-2 | `Uncreate(curve)` then `Create(curve)` draws the current curve (F-907), where Manim draws nothing |
| AN-3 | `FadeOut(curve)` leaves it removed: a later range change does not move it until `curve.refresh()` |
| AN-4 | `Transform(curve, Circle())` leaves it shaped: it keeps the circle, follows `ax.shift(v)`, ignores a range change |
| AN-5 | `Rotate(ax, PI / 2)`: the curve follows `ax` on every frame and ends rotated; `Indicate(ax)`: the curve does not move on any frame (F-916, the frozen frame) |
| AN-6 | `ax.animate.shift(RIGHT)`: on every frame the curve sits where it sits on `ax` moved by the same fraction, and ends shifted with `ax` |
| AN-7 | `Wiggle(curve)` ends where it started, attached |

## SY — the synchronisation updater and Cairo's static background (F-915, F-918)

| ID | Row |
|---|---|
| SY-1 | `scene.get_moving_mobjects(*animations)` — for a play that involves neither `ax` nor a tracker its artists are bound to, `ax` and its artists are not moving, in either order of `scene.add` (they stay in the static background) |
| SY-2 | For `ax.animate.shift(v)`, and for a play animating a tracker an artist is bound to, the artists are moving even when added before `ax` — reported through `.updaters` on both Manim versions (ADR 0003 §5) |
| SY-3 | A frozen `wait()` stays frozen: no artist rebuilds during it |
| SY-4 | A range bound to a callable is evaluated once per rendered frame (ADR 0003 §4) |

## Render tests (`render` marker, both Manim versions in the gate)

| ID | Row |
|---|---|
| RT-1 | F-914: the last frame of `ax` plus `ax.plot(np.sin)` is pixel-identical (Manim's tolerance) to the same scene with `VGroup` of `ax`'s submobjects but the frame — and so after `ax.set_color(RED)`, `ax.set_stroke(width=8)`, `ax.set_fill(BLUE, opacity=1)`, `ax.rotate(0.3)` |
| RT-2 | F-915: the middle frame of `ax.animate.shift(2 * RIGHT)`, with the curve added before `ax` and after it, equals a still frame of `ax` and the curve shifted by `RIGHT` |
| RT-3 | The first visual pair: `mp.Axes()` with `plot(np.sin)` and `Axes()` with `plot(np.sin)` in plain Manim (`__manim` twin); and `x_range=(-1, 10, 1), y_range=(-2, 2, 0.5)` with `plot(lambda x: 1 / (x - 4.5))` — the pole split and the clipping (F-705, F-706) — with its twin |

## BM — benchmark

| ID | Row |
|---|---|
| BM-1 | `tests/benchmark/test_f1001.py`: four `FunctionPlot`s, 2 000 samples each (`use_vectorized=True`, an `x_range` step), on one `CartesianAxes` whose x range is bound to a callable reading a tracker that `play` animates for one second at 1080p60; the affine frame and, after `ax.apply_function` of a smooth warp, the bilinear one. No labels (task 10). Recorded, not gated: the first end-to-end reading of F-1001 |

## Tests

| File | Rows |
|---|---|
| `tests/mobjects/test_system.py` | AX-1 … AX-10 |
| `tests/mobjects/test_leaves.py` | LF-1 … LF-6 |
| `tests/mobjects/test_context.py` | WR-1 … WR-7 |
| `tests/mobjects/test_animations_basic.py` | AN-1 … AN-7, SY-1 … SY-4 |
| `tests/visual/test_first_plots.py` | RT-1 … RT-3 |
| `tests/benchmark/test_f1001.py` | BM-1 |
