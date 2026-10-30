# Acceptance table — task 21, fields and flow

**Status: Living until task 21 merges, then Record.** Written 2026-10-29 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: ADR 0004 §2 (the field source with vector fields,
stream lines and flow; `get_vector`; `plot_implicit_curve` if it falls out), §6 (one
source, one integrator), §9 (customisation); `docs/scope.md` F-114 (the `region` payload,
implemented here), F-712 (amended here), F-706, F-918; the grill log's D15, *Field
artists unify into one pipeline head*. Builds on tasks 06-20.

Modules: `src/manim_plots/core/payload.py` (an optional `values` field),
`core/sources.py` (`FieldSource`, the RK4 step), `core/shape.py` (marching squares),
`src/manim_plots/mobjects/fields.py` (new), `mobjects/system.py`,
`src/manim_plots/__init__.py`.

```python
class ArrowVectorField(VGroup):  # mp.ArrowVectorField, star-exported
    def __init__(
        self,
        func,
        system,
        color=None,
        color_scheme=None,
        min_color_scheme_value=0,
        max_color_scheme_value=2,
        colors=DEFAULT_SCALAR_FIELD_COLORS,
        x_range=None,
        y_range=None,
        length_func=lambda norm: 0.45 * sigmoid(norm),
        opacity=1.0,
        vector_config=None,
        use_vectorized=False,
        **kwargs,
    ): ...

    arrows: list[VMobject]  # in grid order, x outer, y inner

    def nudge(self, mob, dt=1, substeps=1, pointwise=False) -> Self: ...
    def nudge_submobjects(self, dt=1, substeps=1, pointwise=False) -> Self: ...
    def get_nudge_updater(self, speed=1, pointwise=False) -> Callable: ...
    def start_submobject_movement(self, speed=1, pointwise=False) -> Self: ...
    def stop_submobject_movement(self) -> Self: ...


class StreamLines(VGroup):  # mp.StreamLines, star-exported
    def __init__(
        self,
        func,
        system,
        color=None,
        color_scheme=None,
        min_color_scheme_value=0,
        max_color_scheme_value=2,
        colors=DEFAULT_SCALAR_FIELD_COLORS,
        x_range=None,
        y_range=None,
        noise_factor=None,
        n_repeats=1,
        dt=0.05,
        virtual_time=3,
        max_anchors_per_line=100,
        padding=3,
        stroke_width=1,
        opacity=1,
        use_vectorized=False,
        **kwargs,
    ): ...

    stream_lines: list[VMobject]

    def create(self, lag_ratio=None, run_time=None, **kwargs) -> AnimationGroup: ...
    def start_animation(
        self,
        warm_up=True,
        flow_speed=1,
        time_width=0.3,
        rate_func=linear,
        line_animation_class=ShowPassingFlash,
        **kwargs,
    ) -> Self: ...
    def end_animation(self) -> AnimationGroup: ...

    # and the nudge family of ArrowVectorField


class Flow(Animation):  # mp.Flow, star-exported
    def __init__(self, field, *mobjects, speed=1, pointwise=False, **kwargs): ...


class CartesianAxes:
    def get_vector_field(self, func, **kwargs) -> ArrowVectorField: ...
    def get_stream_lines(self, func, **kwargs) -> StreamLines: ...
    def get_vector(self, coords, **kwargs) -> HelperGroup: ...
    def plot_implicit_curve(self, func, min_depth=5, max_quads=1500, **kwargs): ...
```

## FS — the field source and the region payload (F-114, F-712)

| ID | Row |
|---|---|
| FS-1 | `FieldSource(func, *, x_range=None, y_range=None, use_vectorized=False)` (in `core/sources.py`, with `.sample(map, bounds) -> Payload` as every source) samples a function of data coordinates on a grid over the system's viewport, or over `x_range` and `y_range` when given, and returns a `region` payload whose `topology` is the grid's `(rows, cols)` — rows along y, columns along x, `coords` in C order — and whose `values` field, new, optional and `None` by default for every other payload, holds the sampled vectors `(n, 2)` or scalars `(n,)`. A non-finite sample is invalid in `valid` (F-114); `values` of the wrong length raises `ValueError` naming `values`; no other payload changes, and every existing test of `core/payload.py` passes |
| FS-2 | `func` takes Manim's convention, one point `np.array([x, y, 0])` in data coordinates, and returns a vector of length 2 or 3 (a third component is ignored) or a scalar; with `use_vectorized=True` it takes an `(n, 3)` array and returns `(n, 2)`, `(n, 3)` or `(n,)` *(default taken: Manim's convention, in data coordinates)* |
| FS-3 | One integrator: `rk4_step(func, points, dt)` (in `core/sources.py`; `func` vectorized over `(n, 2)` data points, returning `(n, 2)`) advances data points by one classical Runge-Kutta step; every motion along a field in this task — stream lines, `nudge`, `Flow`, `start_animation` — goes through it |
| FS-4 | The grid includes both ends of each range, as Manim's `ArrowVectorField` does (Manim's `StreamLines` leaves the upper end out; here both use one grid rule) *(default taken)*. Its step defaults to the x and y range steps, the third entries of `x_range` and `y_range`, or the system's tick steps; it follows a changed range: an animated range re-samples the field on every frame it changes, keeping each grid point's identity by its index (F-413 for arrows) |

## VF — `ArrowVectorField` (parity survey, *Fields*)

| ID | Row |
|---|---|
| VF-1 | Manim's signature and defaults, plus `system` and `use_vectorized`. One arrow per grid point, a Manim `Vector`-shaped arrow (line and `ArrowTriangleFilledTip`) starting at the point *(default taken: Manim centres its arrows on the point; `vector_config={"center": True}` gives that)*, its direction the data vector mapped through the system, so it is right on unequal unit lengths and log scales, its scene length `length_func(norm)` with `norm` the data vector's length |
| VF-2 | Colour: `color` for every arrow when given, else `colors` interpolated by `color_scheme(vector)` (default: the norm) between `min_color_scheme_value` and `max_color_scheme_value`, as Manim's |
| VF-3 | `field.arrows[i]` is the arrow of grid point `i`, in Manim's order: x outer, y inner, from the lower left; each takes its own style, kept through re-derivation (ADR 0004 §9); `vector_config` styles them all |
| VF-4 | Clipping: an arrow is drawn when its start lies in the viewport, by the artists' `clip` rule, per axis (task 15) |

## SL — `StreamLines` (parity survey, *Fields*)

| ID | Row |
|---|---|
| SL-1 | Manim's signature and defaults, plus `system` and `use_vectorized`. Start points on the grid of `x_range` and `y_range` with `n_repeats` copies, offset by `noise_factor` noise from a seeded generator *(default taken: seed 0, so a scene renders the same twice)*; each line integrates with FS-3 for `virtual_time` in steps of `dt` and stops when it leaves the viewport grown by `padding` data steps on every side, the same on every side |
| SL-2 | Each line is an artist clipped to the viewport (F-706), smoothed through at most `max_anchors_per_line` anchors, coloured along its length by `color_scheme` of the field at its points (a stroke gradient) unless `color` is given; `stream_lines[i]` is line `i`, styleable on its own |
| SL-3 | `create(lag_ratio, run_time)`, `start_animation(...)` and `end_animation()` keep Manim's meaning and defaults; the flow of `start_animation` moves at `flow_speed` times the field's magnitude along each line |
| SL-4 | The lines follow the system: a changed or animated range re-integrates them from the same start points in data space |

## FL — flow and nudging

| ID | Row |
|---|---|
| FL-1 | `field.nudge(mob, dt=1, substeps=1, pointwise=False)` moves `mob`'s centre (or with `pointwise=True` every point) along the field by `dt`, in `substeps` RK4 steps (FS-3), converting scene points to data with the system's `p2c` and back with `c2p`, as Manim's moves them in scene coordinates; `nudge_submobjects`, `get_nudge_updater(speed, pointwise)`, `start_submobject_movement` and `stop_submobject_movement` keep Manim's meaning |
| FL-2 | `Flow(field, *mobjects, speed=1, pointwise=False, run_time=...)` is an animation that advects each mobject for `speed * run_time` of field time, frame by frame through FS-3, so `self.play(Flow(field, dots))` moves dots along the stream lines with no updater left behind |
| FL-3 | A point that leaves the viewport keeps moving by the field, and stops where the field is not finite |

## GV — `get_vector`, `plot_implicit_curve`

| ID | Row |
|---|---|
| GV-1 | `ax.get_vector(coords, **kwargs)`: Manim's `NumberPlane.get_vector` on every system, an arrow from the data origin to `coords`, bound like task 16's helpers (it follows the system; `coords` may hold trackers), a `HelperGroup` of `.line` and `.tip` |
| GV-2 | `ax.plot_implicit_curve(func, min_depth=5, max_quads=1500, **kwargs)`: Manim's signature; the zero set of `func(x, y)` by marching squares on a `FieldSource` grid of about `max_quads` cells over the viewport, refined `min_depth` times where the sign changes *(default taken: the refinement)*, as one path artist that follows the system and `func`'s parameters (bound as `plot`'s are). On Manim's default axes the circle `x**2 + y**2 - 4` lies within `1e-3` of radius 2 |

## Defects fixed (probed on 0.21.0)

`StreamLines` integrates with Euler while `nudge` uses RK4; its start points come from
`np.arange` and accumulate; its out-of-box test pads the upper side by a step less than
the lower; its `if not step` branch never runs; Manim's fields live in scene
coordinates and ignore the axes except through `fit_to_coordinate_system`.

## Tests

`tests/core/test_fields.py`: the payload's `values` and its validation; the grid and its
topology; RK4 against an analytic orbit (a rotation field: after one period a point is
back within `1e-6`); a stream line of the rotation field closing on itself.
`tests/mobjects/test_fields.py`: arrows' count, positions, directions and lengths
against hand-computed values on unequal units and a log axis; colours by norm; per-arrow
style surviving a range change; stream lines inside the padded box, clipped, coloured;
`create`, `start_animation` and `end_animation` in a probe; `nudge` against RK4 by hand;
`Flow` moving a dot along the rotation field's circle; `get_vector`; the implicit circle.
Visual: `test_vector_field`, `test_stream_lines` and `test_implicit_curve`, each with a
`__manim` twin where Manim draws the same scene (its fields on a `NumberPlane` with
`fit_to_coordinate_system`). A frame-cost reading: a stream-line field under
`start_animation` and an arrow field under an animated range, recorded, not gated.
