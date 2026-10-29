# Acceptance table — task 11, part B: the data channel and the F-906 matrix

**Status: Living until task 11 merges, then Record.** Written 2026-10-29 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: `docs/scope.md` F-903-F-911, F-915-F-920, F-922,
F-1005, F-1008; ADR 0001 §4; ADR 0003 §5, §7, §8; PoC 4's keyed alignment
(`docs/poc/poc4-keyed-alignment.md`, `poc/poc4/model.py`). Builds on tasks 09-11a.

Modules: `src/manim_plots/mobjects/system.py`, `axis.py`, `artists.py`, `leaves.py`,
`context.py`; the tick pool of `core/ticks.py` (task 08).

```python
class CartesianAxes:
    def set_x_range(self, x_range) -> Self: ...  # task 09; under .animate, the data channel
    def set_y_range(self, y_range) -> Self: ...


class FunctionPlot:
    def set_parameters(self, **values) -> Self: ...  # (default taken: the name)
```

## DC — `.animate` on data (F-908, F-909, F-911, F-920)

"Visible" below means a leaf with points and a stroke opacity above 0. "A correct plot of
a range" means: equal, as a curve within twice `CHORD_TOLERANCE` (two adaptive samplings
of one curve), to `ax.plot` of the same function on a fresh `mp.Axes` built with that
range, the same lengths, and moved where `ax` is.

| ID | Row |
|---|---|
| DC-1 | `ax.animate.set_x_range(r)` is Manim's own `.animate`: no public method of the library carries `override_animate` (F-908). On every rendered frame, `ax.x.range.value` is the start and end ranges interpolated by the frame's rate-function alpha; the visible major ticks sit at the locator's values for that range; every bound `FunctionPlot` is a correct plot of that range. After the play, the range is `r` and a later `ax.x.range = ...` still rebuilds |
| DC-2 | `ax.animate.shift(v).set_x_range(r)` is one animation (F-909): on every frame, the curve is DC-1's plot for that frame's range moved by alpha × `v`. Either order of the two calls gives the same frames |
| DC-3 | Identity through the play (F-413, D21): a tick whose value is in the range at the start and at the end is the same object after the play; a tick given `set_color(RED)` before a play under `there_and_back` that takes its value out of the range and back is the same object and red after it. A tick entering the range during the play is visible at the end with opacity 1, its opacity never falling while it enters; a tick leaving is not visible at the end, its opacity never rising while it leaves |
| DC-4 | The tick pool (F-920): a play with the default `MaxNLocator`, whose step changes during the play, emits no warning and shows the locator's values on every frame. A key first seen at render time takes a spare; out of spares the play warns once through `ManimPlotsWarning` — once per play, not per frame |
| DC-5 | A plot parameter animates the same way: `curve.animate.set_parameters(a=3)` on `ax.plot(lambda x, a=1: a * np.sin(x))` shows, on every frame, a correct plot of `a` interpolated by alpha; after it `curve.parameters["a"].value == 3`. A parameter that is not one of `f`'s raises `ValueError` naming it, outside and inside `.animate` |
| DC-6 | `Transform(ax, other)` with `other` an `mp.Axes` of the same scale types: on every frame `ax`'s ranges are the two systems' interpolated by alpha, its ticks are the locator's for them, and its bound curve is a correct plot on them; after it, `ax` has `other`'s ranges and placement and its curve follows `ax`. Between different locators the ticks without a matching key fade out and in. A change of scale type (`x_scale="linear"` to `"log"`) raises `ValueError` naming `FadeTransform` when the animation begins (ADR 0003 §8) |
| DC-7 | `ReplacementTransform(ax, new_ax)`: when it finishes, the artists registered to `ax` are registered to `new_ax` (`new_ax.artists`) and follow it — `new_ax.shift(v)` moves them, `new_ax.x.range = ...` rebuilds them on `new_ax` — and `ax.artists` is empty (F-708, F-919) |

## RG — the registry holds artists weakly (found on 2026-10-29 by a probe)

`always_redraw(lambda: ax.plot(...))`, Manim's idiom for a live curve, makes a new plot
every frame; registered strongly, 150 frames left 152 artists on `ax`, each rebuilt on
every later data change.

| ID | Row |
|---|---|
| RG-1 | `ax` holds its registered artists weakly: an artist nothing else references leaves `ax.artists` (in order of registration, as AR-11 says, among the live ones) and is never rebuilt again. After a play of 60 frames under `always_redraw(lambda: ax.plot(...))`, `ax.artists` holds at most the one plot the updater keeps; `ax.legend()` and the colour cycle see only live artists. An artist referenced by a scene, a variable or a group stays registered |

## MX — the F-906 matrix

The oracle is a **plain twin** (task 09): plain `VMobject`s with the library leaves' points
and style, given the same animation in the same play.

| ID | Row |
|---|---|
| MX-1 | For each of `Create`, `Uncreate`, `Write`, `DrawBorderThenFill`, `FadeIn`, `FadeOut`, `GrowFromCenter`, `ShrinkToCenter`, `Indicate`, `Wiggle`, `Circumscribe`, `ShowPassingFlash`, `ApplyWave`, `Rotate`, `Transform` to a plain `Circle`, `ReplacementTransform` to a plain `Circle`, `MoveToTarget`, `.animate.shift`, `Homotopy`, and the compositions `AnimationGroup`, `Succession`, `LaggedStart` of two of them, played on a `FunctionPlot`: the curve's end points equal its twin's (within `1e-9`, or `1e-6` after a non-affine animation), and after the next range change the curve rebuilds when the animation was an introducer, an indication or a movement and stays put when it was a remover or a transform to a plain target (F-905). The animations on `ax` instead (`Create`, `FadeIn`, `Indicate`, `Rotate`, `.animate.shift`, `Wiggle`): every leaf of `ax` but the frame ends where its twin does, and the curve ends on `ax` |
| MX-4 | `Transform(a, b)` and `ReplacementTransform(a, b)` from one artist to another — a `FunctionPlot` to a `FunctionPlot` on the same axes, a `LinePlot` to a `LinePlot` with more points, a `FunctionPlot` to one on other axes — run: Manim's point alignment happens as between plain `VMobject`s, so on every frame `a`'s points equal its twin's under the same animation to `b`'s twin (within `1e-9`). After `Transform`, `a` adopts `b` (F-905): it draws `b`'s data on `b`'s system, so a range change on that system rebuilds `a` equal to `b`; after `ReplacementTransform`, `b` is in the scene and `a` is not. *(Found by a probe on 2026-10-29: every such pair raised a shape mismatch inside `Mobject.interpolate`.)* |
| MX-5 | `a.become(b)` between artists adopts `b`'s state at once (F-905, F-919's immediate `become`): `a` draws `b`'s data on `b`'s system from then on, so a later range change rebuilds `a` equal to `b`. *(Found by a probe on 2026-10-29: `a` went back to its own source at the next rebuild.)* |
| MX-2 | On every rendered frame of `Create`, `Write`, `Uncreate`, `FadeIn`, `Transform` to a `Circle` and `Indicate`, played on a `FunctionPlot`, the curve's points and stroke opacity equal its twin's; and on `ax` with its leaves' twins in a `VGroup`, outside F-1008's difference for `Create(ax)` (the frame's lag slot: the visible leaves finish at 24/25 of the run) |
| MX-3 | F-922: a scene with `mp.Axes` and a plot renders with Manim's caching on, twice in one session: every play has a real hash, the second render's hashes equal the first's, and its play is taken from the cache. Library mobjects hash by identity: a set of two systems has two members |

## Tests

| File | Rows |
|---|---|
| `tests/mobjects/test_data_channel.py` | DC-1 … DC-7 |
| `tests/mobjects/test_registry.py` | RG-1 |
| `tests/mobjects/test_matrix.py` | MX-1, MX-2 |
| `tests/visual/test_caching.py` | MX-3 (`render` marker) |
| `tests/visual/test_animated_pictures.py` | every frame of `ax.animate.set_x_range` with a plot, and of `Create(ax)` with a plot beside its `__manim` twin |
