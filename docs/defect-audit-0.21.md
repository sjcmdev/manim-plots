# Defect audit — ManimCE 0.21.0

Re-validation of the defect inventory that task 01 inherited. The original audit ran
against **0.19.2**; this one runs against **0.21.0**, the version installed in the
project's own `.venv` and the version `manim-plots` targets.

Every verdict below comes from executing code against that install, not from reading a
changelog. The probes are kept as `tests/test_defect_audit_0_21.py`, so an upstream fix
turns into a failing test rather than a stale document.

## Environment

| | |
|---|---|
| Manim | 0.21.0 (`.venv/Lib/site-packages/manim`) |
| Python | 3.13.12 (uv-managed) |
| NumPy | >= 2.1 |
| Renderer | Cairo |
| Date | 2026-09-05 |

A note that cost a review round: the machine's default interpreter
(`~/Desktop/dev/Python`) carries Manim **0.20.0**. Reading Manim source from there gives
line numbers that do not match what the project runs. Read from `.venv`.

## Summary

Of the 14 named defects, **12 reproduce, 1 reproduces partially, 1 is gone**. The sweep
for unlisted findings turned up **6 more**, one of them more severe than anything on the
original list.

**Re-checked on 0.22.0 (2026-10-23).** Every probe gives the same verdict except two.
15c is fixed upstream by ManimCommunity/manim#5039: `point_to_number` and `p2c` now
apply the scale. 15f is half fixed: the `point_to_number` annotation is correct, the
`LogBase.inverse_function` one is not. Defect 11 has no probe and was not re-checked.
The probes assert whichever behaviour the installed version has.

| # | Defect | 0.19.2 | 0.21.0 |
|---|---|---|---|
| 1 | Float accumulation in tick generation via `np.arange` | yes | **reproduces** |
| 2 | `include_tip` alters tick range and coordinate mapping | yes | **partial** — tick range only |
| 3 | Plot curves escape the viewport; no clipping | yes | **reproduces** |
| 4 | Aspect ratio distortion from independent lengths | yes | **reproduces** |
| 5 | `unit_size` ignored when passed through `axis_config` | yes | **reproduces** |
| 6 | Mutating `x_range` leaves ticks stale | yes | **reproduces** |
| 7 | No legend primitive | yes | **reproduces** |
| 8 | `LogBase.inverse_function` ndarray guard broken | yes | **reproduces** |
| 9 | `LogBase` has no minor ticks between decades | yes | **reproduces** |
| 10 | `LogBase` naming: `function()` is exponential | yes | **reproduces** |
| 11 | Label overlap: no de-confliction | yes | **reproduces** |
| 12 | Ticks centred; cannot be directed outward only | yes | **reproduces** |
| 13 | `_origin_shift` clamps to the range minimum | yes | **reproduces** |
| 14 | Geometric ops on `NumberLine` corrupt the mapping | yes | **gone** |
| 15a | `plot()` joins across a pole instead of breaking | — | **new** |
| 15b | Tick step doubles as the curve sampling step | — | **new** |
| 15c | `p2n` is not the inverse of `n2p` on a non-linear scale | — | **new, severe** |
| 15d | A zero tick step fails with an unrelated error | — | **new, minor** |
| 15e | An out-of-range label is placed off the line silently | — | **new, minor** |
| 15f | Annotations contradict the implementation; the round trip does not type-check | — | **new** |

---

## 1. Float accumulation in tick generation

**Reproduces.** `NumberLine.get_tick_range` builds ticks with `np.arange`
(`number_line.py:346`, `:352-353`), which accumulates the step in floating point.

```
x_range=[0, 1, 0.1] -> 11 ticks, 3 of them inexact
0.30000000000000004, 0.6000000000000001, 0.7000000000000001
max deviation 1.11e-16
```

The absolute error is tiny; the consequence is not. Anything that keys on a tick value —
a label lookup, a dictionary of user styling, an equality test in a test suite — sees
`0.30000000000000004` where the user wrote `0.3`. This is the direct source of the
requirement that generated parts be keyed by a canonicalized value rather than a raw
float.

## 2. `include_tip` alters the tick range

**Partially reproduces — tick range only, not the coordinate mapping.**

```
NumberLine(x_range=[0,10,1], length=10)
  include_tip=False -> 11 ticks, last 10.0, unit 1.0, n2p(10) = [5, 0]
  include_tip=True  -> 10 ticks, last  9.0, unit 1.0, n2p(10) = [5, 0]
Axes: c2p(10,10) identical either way
```

The cause is explicit: `get_tick_range` opens with

```python
if not self.include_tip:
    x_max += 1e-6
```

(`number_line.py:341-342`), so the endpoint tick exists only when there is no tip. The
coordinate mapping is untouched, so the original finding overstated the defect. Adding a
tip still silently removes the last tick, which is the part worth keeping as a
requirement.

## 3. Plot curves escape the viewport

**Reproduces.**

```
Axes(x_range=[-3,3,1], y_range=[-3,3,1], x_length=6, y_length=6)
ax.plot(lambda x: 1/x, x_range=[0.1, 3])
frame top at scene y = 3.0; the curve reaches y = 10.0
-> 7.0 scene units outside the frame
```

`Axes.plot` takes no clipping parameter. Every asymptotic function drawn on a bounded
axis leaks over the rest of the scene, and the usual workaround — narrowing `x_range`
until it happens not to — is a guess that changes with the function.

## 4. Aspect ratio distortion from independent lengths

**Reproduces.**

```
Axes(x_range=[0,10,1], y_range=[0,10,1], x_length=10, y_length=4)
unit_x = 1.0, unit_y = 0.4, ratio 2.5
```

Equal data ranges, unequal scene units. A circle in data space renders as an ellipse, a
right angle is not a right angle, and there is no parameter that locks the aspect. The
lengths and the ranges are four independent numbers with no constraint between them.

## 5. `unit_size` ignored through `axis_config`

**Reproduces.**

```
Axes(..., x_length=10, axis_config={"unit_size": 3}) -> effective unit 1.0
NumberLine(x_range=[0,10,1], unit_size=3)            -> effective unit 3.0
```

The parameter is accepted, passed down and then overridden by the length the `Axes`
computes. It fails silently: no warning, no error, and the value the user asked for is
simply not what they get.

## 6. Mutating `x_range` leaves ticks stale

**Reproduces.**

```
NumberLine(x_range=[0,5,1]) -> 6 ticks built
nl.x_range = [0, 10, 1]
get_tick_range() now returns 11 values
the tick mobjects are still the original 6
```

`x_range` is a plain attribute with no setter and no invalidation. The computed range and
the drawn geometry disagree from the moment it is assigned, and nothing tells the user.
This is the defect that the whole dirty-and-rebuild design in `docs/plan.md` exists to remove.

## 7. No legend primitive

**Reproduces.** Nothing in the `manim` namespace and no method on `Axes` contains
"legend". Users assemble one out of `VGroup`, `Dot` and `Text` by hand, per scene, and
keeping it in sync with the curves is manual.

## 8. `LogBase.inverse_function` guard is broken

**Reproduces, and the guard is worse than absent.**

```
condition = value.any() <= 0        # scale.py:157
```

`value.any()` is a bool. `True <= 0` is `False`; `False <= 0` is `True`. So the guard
fires exactly when the array is *all zeros*, and never when it contains a negative:

```
inverse_function([-5, 1, 10])  -> [nan, 0.0, 1.0]   (RuntimeWarning, no exception)
inverse_function([-5, -1])     -> no exception
inverse_function([0, 0])       -> ValueError
```

A negative value becomes a silent `NaN` that propagates into geometry. The scalar branch
(`value <= 0`, `:165`) is correct; only the array branch is inverted.

## 9. `LogBase` has no minor ticks

**Reproduces.**

```
NumberLine(x_range=[0,3,1], scaling=LogBase(10)).get_tick_range()
-> [1, 10, 100, 1000]
```

Decade boundaries only. There are no 2..9 minors between decades and no parameter to ask
for them, which is the one thing a log axis is expected to show.

## 10. `LogBase` naming is inverted

**Reproduces.**

```
LogBase(10).function(5)          -> 100000     # this is 10**5, an exponential
LogBase(10).inverse_function(1e5) -> 5.0       # this is the logarithm
```

On a class called `LogBase`, `function` is the exponential and `inverse_function` is the
log. Any third party implementing the scale protocol has to read the source to find out
which direction is which, and the docstring on `function` says
`self.function(5)==10**5` without remarking that this is the opposite of the class name.

## 11. Label overlap at high density

**Reproduces.**

```
Axes(x_range=[0,1,0.02], x_length=6).add_coordinates()
-> 49 labels, 48 overlapping neighbour pairs
de-confliction parameters: none
```

Labels are placed at every tick regardless of the space available. There is no thinning,
no rotation, no skipping, and no way to ask for any.

## 12. Ticks are centred on the axis line

**Reproduces.**

```
tick spans scene y -0.1 .. 0.1, axis line at y = 0.0, midpoint 0.0
direction parameters: none
```

Every tick straddles the line. Outward-only ticks — the default in matplotlib, gnuplot
and every published figure convention — cannot be requested.

## 13. `_origin_shift` clamps to the range minimum

**Reproduces.**

```
if axis_range[0] > 0:
    return axis_range[0]          # coordinate_systems.py:2403-2405
```

```
Axes._origin_shift([5, 10, 1]) -> 5
Axes(x_range=[5,10,1], y_range=[5,10,1]).c2p(5,5) -> [-3, -3]
```

When the range excludes zero, the axis is shifted so the *minimum* sits where the origin
would have been. The consequence is that a plot whose data starts at 5 is drawn as though
5 were zero: there is no way to say "the origin is off-frame, place the data accordingly".

## 14. Geometric ops corrupt the coordinate mapping

**Gone.** This one no longer reproduces on 0.21.0, and it is worth understanding why.

```
scale(2)                  -> n2p tracks; get_unit_size 1.0 -> 2.0
shift(UP*2)               -> n2p tracks
stretch(3, 0)             -> unit 3.0, tracks
rotate(pi/3)              -> p2n(n2p(7)) = 7.000000
flip()                    -> n2p(0) = [5,0], n2p(10) = [-5,0], p2n(n2p(2)) = 2.000000
put_start_and_end_on(...) -> p2n(n2p(6)) = 6.000000
apply_function(x -> x^2)  -> p2n(n2p(4)) = 4.000000
scale(2), tick mobject position vs n2p, max drift 0.00e+00
```

`number_to_point` and `point_to_number` both derive from `get_start_and_end()` live
(`number_line.py:426`), so the mapping is a function of the current geometry rather than
of stored state. That is the same principle `docs/plan.md` adopts — points derived, never
stored — and it is why the mapping cannot drift out of sync with the drawing.

Dropped from the requirement list, with one caveat kept as a note: a point off the line
is silently projected onto it (`p2n` of a point 0.5 above a rotated axis returns
`7.433013`, no warning), so `p2n` is a projection, not an inverse, for any point not
exactly on the axis.

---

## New findings from the sweep

### 15a. `plot()` joins across a pole instead of breaking

**New.**

```
Axes(x_range=[-3,3,1], y_range=[-5,5,1]).plot(lambda x: 1/x, x_range=[-3,3])
-> one connected path; longest single segment 7.5e13 scene units
plot() has no `discontinuities` parameter
```

The sampler walks straight through the asymptote and connects the last point before it to
the first point after, drawing a near-vertical line the height of the universe. Combined
with defect 3 — no clipping — this is what makes `1/x` unusable out of the box.

### 15b. The tick step doubles as the curve sampling step

**New.**

```
Axes(x_range=[0,10,5]).plot(sin)                     ->  80 points
Axes(x_range=[0,10,5]).plot(sin, x_range=[0,10,0.05]) -> 800 points
```

One number in `x_range` controls both how many labels appear and how finely the curve is
sampled. Asking for sparse labels silently coarsens every curve on the axis, and the fix
is to repeat the range on every `plot` call.

### 15c. `p2n` is not the inverse of `n2p` on a non-linear scale

**New, and the most severe finding in this audit.**

```
NumberLine(x_range=[0,3,1], length=6, scaling=LogBase(10))
  n2p(1)    -> x = -3.0  -> p2n =    1.0     correct by coincidence (endpoint)
  n2p(10)   -> x = -1.0  -> p2n =  334.0     should be 10
  n2p(100)  -> x =  1.0  -> p2n =  667.0     should be 100
  n2p(1000) -> x =  3.0  -> p2n = 1000.0     correct by coincidence (endpoint)

Axes with a LogBase x axis:
  p2c(c2p(10, 5))  -> [334.0, 5.0]
  p2c(c2p(100, 5)) -> [667.0, 5.0]

linear control: p2n(n2p(v)) exact for v in 0, 3, 7, 10
```

`number_to_point` applies `self.scaling.inverse_function(number)`
(`number_line.py:392`). `point_to_number` interpolates linearly between `x_min` and
`x_max` and applies **no scaling at all** (`number_line.py:425-431`). The two are
therefore inverses only when the scale is the identity. The round trip appears to work at
the range endpoints, which is exactly the pair of points a casual test would check.

`CONTRIBUTING.md` names `p2c(c2p(x)) == x` as a required oracle for this library. Upstream
does not hold it.

### 15d. A zero tick step fails with an unrelated error

**New, minor.** `NumberLine(x_range=[0, 10, 0])` raises
`ValueError: Maximum allowed size exceeded` from inside `np.arange`. The step is never
validated; the user gets a memory-allocation error for a domain mistake.

### 15e. An out-of-range label is placed off the line

**New, minor.** `numbers_to_include=[99]` on a `0..5` line places the label at scene
`x = 96.5`, far outside the axis, with no warning. Nothing checks that a requested label
falls within the range.

### 15f. Annotations contradict the implementation

**New.** Found by running `mypy --strict` over the audit probes themselves.

```
LogBase.inverse_function(value: float) -> float
    ... but the body branches on isinstance(value, np.ndarray) (scale.py:156)

NumberLine.point_to_number(point: Sequence[float]) -> float
    ... but number_to_point returns np.ndarray, and the docstring example passes
        a list of points and gets an array back
```

The consequence is that `p2n(n2p(x))` — the library's own round trip, and the oracle
`CONTRIBUTING.md` requires — does not type-check. A downstream project running
`mypy --strict`, which this one does, has to suppress an error on the most ordinary call
it can make. The seven suppressions in `tests/test_defect_audit_0_21.py` are all this one
defect.

Note for the toolchain, since running the audit under `mypy --strict` is what exposed
it: `mypy` could not run at all with the configured `python_version = "3.11"`, because
NumPy's stubs use `type` statements that mypy only parses at 3.12 and above. Chasing
that down showed the declared floor was already wrong — NumPy 2.5 requires Python
**>= 3.12**, so `requires-python = ">=3.11"` described an install that cannot happen.
Both were raised to 3.12 and all four checks are green.

---

## Handoff to task 03

Every reproducing defect becomes an `F-*` requirement in `docs/scope.md`. The grouping
below is the shape they fall into, not the requirement text.

| Group | Defects | Note |
|---|---|---|
| Tick generation and identity | 1, 2, 6, 9, 12, 15d | Locator protocol with canonical keys |
| Coordinate mapping correctness | 5, 13, 15c | 15c is a correctness bug, not a missing feature |
| Scale protocol | 8, 10, 15c | Vectorized, invertible, validated at construction |
| Viewport and path shape | 3, 15a, 15b | Clipping and discontinuity splitting in `Shape` |
| Layout | 4, 11 | Aspect lock as a map node; label de-confliction |
| Missing primitives | 7, 15e | Legend; range validation on labels |
| Public typing | 15f | Annotations are part of the public contract |

Defect 14 is dropped. Its note — that `p2n` is a projection for off-axis points — is
carried into the scope document as a documentation requirement rather than a defect.
