# Acceptance table — task 24, the 3D system

**Status: Living until task 24 merges, then Record.** Written 2026-10-30 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: ADR 0006 §1-§5; the grill log's D7; task 15
(clipping per axis), task 20 (themes). Surfaces are task 25; camera-facing labels task 26.

Modules: `core/nodes.py`, `core/sources.py`, `core/shape.py` (generalized by dimension),
`mobjects/system.py`, `mobjects/axis.py`, `mobjects/artists.py`, `mobjects/three_d.py`
(new), `src/manim_plots/__init__.py`.

```python
class ThreeDAxes(CartesianAxes):  # mp.ThreeDAxes, not in __all__ (Manim's name)
    def __init__(
        self,
        x_range=(-6, 6, 1),
        y_range=(-5, 5, 1),
        z_range=(-4, 4, 1),
        x_length=config.frame_height + 2.5,
        y_length=config.frame_height + 2.5,
        z_length=config.frame_height - 1.5,
        z_axis_config=None,
        z_normal=DOWN,
        num_axis_pieces=20,
        light_source=9 * DOWN + 7 * LEFT + 10 * OUT,
        depth=None,
        gloss=0.5,
        *,
        x_scale="linear",
        y_scale="linear",
        z_scale="linear",
        theme=None,
        cycle=None,
        **kwargs,  # axis_config, x_axis_config, y_axis_config, tips, as CartesianAxes
    ): ...

    z_axis: Axis
    z: Axis  # alias, as x and y
    z_range: np.ndarray

    def c2p(self, x, y, z=0) -> np.ndarray: ...
    def p2c(self, point) -> np.ndarray: ...  # (x, y, z)
    def set_z_range(self, z_range) -> Self: ...  # animatable
    def get_z_axis(self) -> Axis: ...
    def get_z_axis_label(
        self,
        label,
        edge=OUT,
        direction=RIGHT,
        buff=SMALL_BUFF,
        rotation=PI / 2,
        rotation_axis=RIGHT,
        **kwargs,
    ): ...
    def get_axis_labels(self, x_label="x", y_label="y", z_label="z") -> VGroup: ...
    def plot_parametric_curve(
        self, function, t_range=None, **kwargs
    ): ...  # 3 components
    def scatter(self, x, y, z, **kwargs) -> ScatterPlot: ...
    def line(self, x, y, z, **kwargs) -> LinePlot: ...
```

## TS — one system by dimension (ADR 0006 §1)

| ID | Row |
|---|---|
| TS-1 | The map of a `ThreeDAxes` is the 2D map's composition at `dim=3`: one `ScaleNode` per non-linear axis and one `AffineNode`; `c2p(x, y, z)` and `p2c` are inverse within `1e-9` on linear, log and symlog axes; arrays broadcast as on `CartesianAxes`; `c2p(x, y)` is `c2p(x, y, 0)` |
| TS-2 | Every existing test passes unchanged; a 2D system's map, leaves and per-frame cost are unchanged (F-1001 interleaved against `dev` equal) |
| TS-3 | Twins (`twinx`, `twiny`, `twin`), `secondary_xaxis`/`secondary_yaxis`, the field helpers of task 21 and task 16-18's helpers (drop lines, calculus, regions, error bars) raise `NotImplementedError` naming the method and `ThreeDAxes` *(default taken: 3D versions are later tasks)*. The polar helpers of task 22 keep Manim's meaning in the `z = 0` plane |

## TA — Manim's `ThreeDAxes` (parity survey, *3D*)

| ID | Row |
|---|---|
| TA-1 | Manim's signature and defaults (the code block), plus `x_scale`, `y_scale`, `z_scale`, `theme`, `cycle`. On Manim's defaults `c2p`, `p2c`, the axes' start and end points and unit sizes equal Manim's `ThreeDAxes` within `1e-9` (`c2p(1, 2, 3) = (0.875, 2.1, 2.4375)`), and every tick Manim draws is drawn at the same point (the library adds the tick under a tip, as on `mp.Axes`) |
| TA-2 | The z axis runs along `OUT` through the origin of x and y; its ticks lie in the plane Manim puts them, turned by `z_normal` as Manim turns them (along x for `DOWN`, along y for `RIGHT`); `num_axis_pieces`, `light_source`, `depth` and `gloss` style the axes as Manim's `_add_3d_pieces` and `_set_axis_shading` do |
| TA-3 | `x`, `y`, `z` are three `Axis` decorations with every control of task 10 (locator, formatter, tick style and direction, numbers, labels, grid off by default, tips); `z_axis_config` merges over `axis_config` as in Manim; `get_z_axis` returns `z_axis` |
| TA-4 | `get_z_axis_label` and `get_axis_labels(x, y, z)` keep Manim's placement and rotation defaults, string for string and point for point on Manim's defaults; a label follows its axis as task 10's labels do |
| TA-5 | `plot(f)` draws `y = f(x)` in the `z = 0` plane, as Manim's; `plot_parametric_curve` with a function returning three components draws a space curve; `i2gp` and `input_to_graph_point` keep Manim's meaning |

## TC — artists in 3D

| ID | Row |
|---|---|
| TC-1 | Curves are adaptive in their parameter against the mapped 3D curve (F-702's rule with the third coordinate), split at non-finite samples (F-705), take the colour cycle, the legend and every plot keyword, and follow their function's parameters and trackers as in 2D |
| TC-2 | `ax.scatter(x, y, z)` places one marker per point at `c2p(x, y, z)`; the default marker is task 12's flat marker, drawn as Manim draws a flat mobject in a 3D scene *(default taken: not `Dot3D`, ADR 0006 §4)*; `ax.line(x, y, z)` joins the points straight in the scene, as `plot_line_graph` does |
| TC-3 | Every 3D artist is an ordinary `VMobject` family, so `ThreeDScene`'s camera sorts and shades it as it does Manim's; a camera move changes no artist's points |

## TF — following

| ID | Row |
|---|---|
| TF-1 | Curves, scatter points, lines, ticks, numbers and labels follow an affine move of the axes (shift, scale, rotation about any axis, `Rotate`, `.animate.rotate`) on every frame, as in 2D *(the frame is affine in 3D: ADR 0006 §5)* |
| TF-2 | `apply_function` (and `ApplyPointwiseFunction`, `.animate.apply_function`) on a `ThreeDAxes` raises `NotImplementedError` naming the method and the affine frame |
| TF-3 | `set_x_range`, `set_y_range`, `set_z_range` change a range, and `.animate` of each animates it, every artist and tick following on every frame, keyed by value (F-413); a changed range costs one compile, no resampling of an unchanged curve's parameter grid |
| TF-4 | `z_scale="log"` (and `x_scale`, `y_scale`, symlog, any `Scale`) is a scale node as in 2D: ticks from `LogLocator`, data in the scale's domain, a range outside it refused naming `z_range` |
| TF-5 | A theme fills `ThreeDAxes`' defaults as `CartesianAxes`' (cycle, tick direction, tips, legend); a legend is placed in the frame with Manim's `add_fixed_in_frame_mobjects` when the scene is a `ThreeDScene` *(default taken)* |

## TK — clipping to the box

| ID | Row |
|---|---|
| TK-1 | An artist is clipped to the box of the three ranges by default: a helix of height 10 on Manim's defaults is cut at `z = ±4` within `1e-6` scene units and resumes inside; `clip=False` draws it whole, as Manim does |
| TK-2 | `clip=(x, y, z)` clips per axis, each entry a bool or a margin in scene units, as task 15's `clip=(x, y)`; a two-entry tuple on a `ThreeDAxes` raises `ValueError` naming `clip` |
| TK-3 | Scatter points outside the box are not drawn when clipped, per axis, as in 2D |

## Defects fixed (probed on 0.21.0)

Manim's curves on a `ThreeDAxes` keep their points when the axes move or a range
changes (no range can change); nothing is clipped (a helix on the defaults reaches
`z = ±4.875` past the box's `±3.25`); a log axis only through `LogBase` on one
`NumberLine`, with no z scale of its own.

## Tests

`tests/mobjects/test_three_d.py`: the map and its inverse on linear and log axes; parity
with Manim's `ThreeDAxes` on its defaults and on custom ranges and lengths (`c2p`, the
axes' endpoints, unit sizes, tick counts, `z_normal`); the labels; `plot` in `z = 0`; a
helix against its analytic points; scatter and line; following a shift and a rotation;
`apply_function` refused; animated `set_z_range` in a probe; a log z axis; the box
clip and `clip=(x, y, z)`; the refusals of TS-3; a theme. Visual (in a `ThreeDScene`
with the camera at `phi = 65°`, `theta = -45°`): `test_three_d_axes` with a `__manim`
twin, `test_three_d_helix_clipped` with its twin (Manim's unclipped), `test_three_d_log_z`.
A frame-cost reading: three curves under `ax.animate.set_z_range`, p95 of `update`.
