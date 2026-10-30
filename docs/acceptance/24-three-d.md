# Acceptance table — task 24, the 3D system

**Status: Living until task 24 merges, then Record.** Written 2026-10-30 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: ADR 0006 §1-§4 and §6; the grill log's D7; task 15
(clipping per axis), task 20 (themes). Surfaces are task 25; coordinates and geometry task 26; occlusion task 30.

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
        frame=None,  # "origin" (default) or "box"; a theme may set it
        aspect=None,  # None, "equal" or a (x, y, z) box ratio
        face_camera=None,  # numbers and labels; default True in "box"
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
    def view(self, elev=30, azim=-60, roll=0) -> dict: ...  # for set_camera_orientation

    panes: dict[str, Pane]  # "x", "y", "z" in "box": each a part with .grid

    def line(self, x, y, z, **kwargs) -> LinePlot: ...
```

In 2D, `CartesianAxes` and `NumberPlane` take `frame="origin" | "box"` too (FR-5).

## TS — one system by dimension (ADR 0006 §1)

| ID | Row |
|---|---|
| TS-1 | The map of a `ThreeDAxes` is the 2D map's composition at `dim=3`: one `ScaleNode` per non-linear axis and one `AffineNode`; `c2p(x, y, z)` and `p2c` are inverse within `1e-9` on linear, log and symlog axes; arrays broadcast as on `CartesianAxes` (one column per point, Manim's shape `(3, n)`); `c2p(x, y)` is `c2p(x, y, 0)` |
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
| TK-3 | Scatter points outside the box are hidden when clipped, per axis, as in 2D (the marker stays, its opacity drops to zero) |

## FR — frame styles (ADR 0006 §4)

| ID | Row |
|---|---|
| FR-1 | The style is kept as `ax.frame_style` (`ax.frame` is the system's invisible frame, task 09). `frame="origin"` (the default) is Manim's picture: the axes cross at the data origin, or where `set_position` puts them, as TA-1 to TA-4 say |
| FR-2 | `frame="box"` draws the box of the three ranges with three panes on its far sides, each a filled part with a grid at its two axes' major ticks (`ax.panes["x"]` is the pane perpendicular to x, `.grid` its lines), and the three axes on near edges, their ticks inward and numbers outward, numbered by default, no tips (as the 2D box) *(default taken: matplotlib's)*. Far and near are read from the camera: with the camera direction `d = (sin φ cos θ, sin φ sin θ, cos φ)` of `ThreeDScene`'s `phi` and `theta`, the x pane lies at the x end opposite `sign(d_x)` (x_min when `d_x > 0`), the same for y and z; the x axis runs along the near bottom edge (`y` at the end of `sign(d_y)`, `z` at its far end), the y axis likewise, the z axis along the vertical edge farthest to the camera's right among the near ones *(default taken: matplotlib's choices)* |
| FR-3 | The panes, edges and axes follow the camera: a `move_camera` or an ambient rotation that crosses a pane's plane moves the pane and the axes to the other side on that frame, keyed by side so a style set on a pane or an axis is kept; a still camera costs nothing per frame. The system finds the camera of the `ThreeDScene` it is drawn in without being told and without patching Manim; `ax.set_camera(camera)` names one explicitly *(default taken)* |
| FR-4 | `frame="box"` with a plain `Scene` (no 3D camera) draws the box as seen from the default view (`phi = 0`) and warns once through `ManimPlotsWarning` |
| FR-5 | In 2D, `frame="box"` on `CartesianAxes` and `NumberPlane` is the framed plot: x at the bottom, y at the left, unlabelled mirrors at the top and right, no tips, ticks inward (task 19b, ADR 0005 §1); it draws exactly what `x.set_position("bottom")`, `y.set_position("left")` and the theme field `box=True` draw today. `frame="origin"` is the default. A theme with `position="border"` and `box=True` sets `frame="box"`, and an explicit `frame` wins |
| FR-6 | `face_camera=True` turns every number and label to face the camera on every frame the camera moves (the label's plane normal parallel to `d`, its up direction the screen's up: its flat points `p` become `centre + (p - centre) @ M` with `M = camera.generate_rotation_matrix()`; `get_rotation_matrix()` is the matrix of the last captured frame), as Manim's `add_fixed_orientation_mobjects` does, kept centred where it was placed; it defaults to `True` in `"box"` and `False` in `"origin"` (Manim's flat labels) |

## VW — view and aspect

| ID | Row |
|---|---|
| VW-1 | `ax.view(elev=30, azim=-60, roll=0)` returns the keywords of Manim's `set_camera_orientation` and `move_camera` for matplotlib's angles: `phi = 90° - elev`, `theta = azim`, `gamma = roll`, in radians, so `self.set_camera_orientation(**ax.view(30, -60))` shows what matplotlib's `view_init(30, -60)` shows and `self.move_camera(**ax.view(...))` animates to it *(default taken: the axes do not move the camera themselves)* |
| VW-2 | `aspect="equal"` makes one data unit the same scene length on all three axes, keeping `x_length` and adapting the other two lengths; `aspect=(a, b, c)` sets the lengths in that ratio, keeping `x_length` (matplotlib's `set_box_aspect`); a length given with an aspect that fixes it raises `ValueError` naming both, as F-205 in 2D |

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
`tests/mobjects/test_frames.py`: FR and VW: the panes and edges under four camera
angles, a pane switching sides during `move_camera`, a styled pane kept, the 2D box
against the manual framed plot, `face_camera`, `view`, `aspect`. Visual: also
`test_three_d_box` and `test_three_d_box_turned` (the same axes from `azim = 120°`), and
`test_axes_box_2d`. Frame-cost readings: three curves under `ax.animate.set_z_range`,
and a `"box"` frame under `move_camera`, p95 of `update`.
