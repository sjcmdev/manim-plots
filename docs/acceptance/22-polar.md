# Acceptance table — task 22, polar

**Status: Living until task 22 merges, then Record.** Written 2026-10-30 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: ADR 0004 §2 (polar, `Node` public), §5 (matplotlib's
names where Manim has none), §9 (customisation); the grill log's D7 (*a coordinate
system is one mapping*: polar supplies one coupled node); the parity survey, *Polar*.
Builds on tasks 06-21.

Two systems, because Manim has one and the release needs the other:

- **`mp.PolarPlane`** is Manim's: a Cartesian system, `c2p(x, y)` as on `Axes`, with
  circles and spokes behind it and azimuth labels around it. Code written for Manim's
  `PolarPlane` runs unchanged (rows PP).
- **`mp.PolarAxes`** is a true polar system: its data coordinates are `(r, θ)`, its map
  is one coupled node, `plot` draws `r = f(θ)`, its radial scale may be logarithmic and
  everything on it is clipped to the disk (rows PX).

Modules: `src/manim_plots/core/nodes.py` (`Node` public), `core/formatters.py`
(`AngleFormatter`), `src/manim_plots/mobjects/polar.py` (new), `mobjects/system.py`
(the polar helpers of every system), `src/manim_plots/__init__.py`.

```python
class PolarPlane(CartesianAxes):  # mp.PolarPlane, not in __all__ (Manim's name)
    def __init__(
        self,
        radius_max=config.frame_y_radius,
        size=None,
        radius_step=1,
        azimuth_step=None,
        azimuth_units="PI radians",
        azimuth_compact_fraction=True,
        azimuth_offset=0,
        azimuth_direction="CCW",
        azimuth_label_buff=SMALL_BUFF,
        azimuth_label_font_size=24,
        radius_config=None,
        background_line_style=None,
        faded_line_style=None,
        faded_line_ratio=1,
        make_smooth_after_applying_functions=True,
        *,
        theme=None,
        cycle=None,
        **kwargs,
    ): ...

    background_lines: VGroup  # major spokes, then major circles
    faded_lines: VGroup
    circles: Parts  # circles.at(r), major and faded
    spokes: Parts  # spokes.at(theta), theta in radians, major and faded

    def get_coordinate_labels(
        self, r_values=None, a_values=None, **kwargs
    ) -> VDict: ...
    def add_coordinates(self, r_values=None, a_values=None) -> Self: ...
    def get_radian_label(self, number, font_size=24, **kwargs) -> MathTex: ...


class PolarAxes(VGroup):  # mp.PolarAxes, star-exported
    def __init__(
        self,
        r_range=None,  # (r_min, r_max[, step]); default (0, config.frame_y_radius, 1)
        size=None,  # diameter in scene units; default 2 * config.frame_y_radius
        *,
        r_scale="linear",  # Scale or "linear", "log", "symlog"
        azimuth_step=None,
        azimuth_units="PI radians",
        azimuth_compact_fraction=True,
        azimuth_offset=0,
        azimuth_direction="CCW",
        r_axis_angle=PI / 8,
        r_axis_config=None,
        azimuth_axis_config=None,
        background_line_style=None,
        faded_line_style=None,
        faded_line_ratio=1,
        theme=None,
        cycle=None,
        **kwargs,
    ): ...

    r_axis: Axis  # the radial axis, a ray at r_axis_angle
    azimuth_axis: Axis  # the rim, a circle
    background_lines: VGroup
    faded_lines: VGroup
    circles: Parts  # as PolarPlane's
    spokes: Parts
    r_range: np.ndarray  # (r_min, r_max, step), read-only

    def c2p(self, r, theta) -> np.ndarray: ...  # == pr2pt
    def p2c(self, point) -> np.ndarray: ...  # (r, θ), θ in [0, TAU)
    def set_r_range(self, r_range) -> Self: ...  # animatable
    def plot(self, r_func, theta_range=None, **kwargs): ...  # r = r_func(θ)
    def plot_polar_graph(self, r_func, theta_range=None, **kwargs): ...  # the same

    # scatter, line, plot_line_graph: (r, θ) data
```

On every system (`CartesianAxes`, `NumberPlane`, `PolarPlane`, `PolarAxes`, twins):

```python
def polar_to_point(self, radius, azimuth) -> np.ndarray: ...
def point_to_polar(self, point) -> tuple[float, float]: ...
def pr2pt(self, radius, azimuth) -> np.ndarray: ...
def pt2pr(self, point) -> tuple[float, float]: ...
def plot_polar_graph(self, r_func, theta_range=None, **kwargs) -> ParametricPlot: ...
```

## PH — the polar helpers of every system (parity survey, *Polar*)

| ID | Row |
|---|---|
| PH-1 | `polar_to_point(radius, azimuth)` is Manim's, `c2p(r cos θ, r sin θ)`, and `pr2pt` its alias, on every Cartesian system; arrays of radii and azimuths broadcast as `c2p`'s arrays do |
| PH-2 | `point_to_polar(point)` is Manim's, `(hypot(x, y), arctan2(y, x))` of `p2c(point)`, the azimuth in `(-π, π]`, and `pt2pr` its alias; `pt2pr(pr2pt(r, θ))` returns `(r, θ)` within `1e-9` for `r > 0` and `θ` in `(-π, π]` |
| PH-3 | `plot_polar_graph(r_func, theta_range=None, **kwargs)` is Manim's: the parametric curve `θ ↦ pr2pt(r_func(θ), θ)` over `theta_range` (default `[0, TAU]`), a `ParametricPlot` (task 11a) that follows the system, is clipped, takes the colour cycle and the plot keywords, and carries `underlying_function = r_func`. |

## PP — `mp.PolarPlane` (parity survey, *Polar*)

| ID | Row |
|---|---|
| PP-1 | Manim's signature and defaults, plus `theme` and `cycle`. A Cartesian system over `(-radius_max, radius_max)` in x and y with `radius_step` as both steps; `size` the diameter, so the unit is `size / (2 radius_max)`, and `size=None` gives unit 1, as Manim's (`PolarPlane()` is 8 by 8). `radius_config` as Manim's: no ticks, no tips, numbers `DL` of the x axis, stroke width 2, font size 24. `azimuth_units` outside Manim's five and `azimuth_direction` outside `"CW"`, `"CCW"` raise `ValueError`, as Manim's |
| PP-2 | `background_lines` holds the major spokes, then the major circles, `faded_lines` the rest, as Manim's: spokes every `TAU / azimuth_step / faded_line_ratio` from `azimuth_offset`, `azimuth_step` defaulting by unit as Manim's (20, 20, 36, 40, 1); circles every `radius_step / faded_line_ratio` up to `radius_max`; every `faded_line_ratio`-th one major; styles as Manim's (`BLUE_D`, width 2, the faded style halving every number). Manim's circle of radius 0 is left out (a defect) *(default taken)*, so `PolarPlane()` has 20 spokes and 4 circles in `background_lines` |
| PP-3 | `plane.circles.at(r)` is the circle of radius `r`, `plane.spokes.at(θ)` the spoke at azimuth θ (radians from `azimuth_offset`, in the azimuth direction), major and faded alike, each styleable on its own (ADR 0004 §9); a missing one raises `KeyError`, as an axis's `numbers.at` does. The grid follows the system: the radius of the plane is the x range's upper end, so a changed or animated range moves and re-derives circles and spokes, keyed by value, a circle beyond the new radius removed and one inside kept with its style; the spokes reach the new rim |
| PP-4 | `pr2pt` and `pt2pr` on a `PolarPlane` follow its `azimuth_offset` and `azimuth_direction`, so the point at azimuth θ lies on the spoke labelled θ: `pr2pt(r, θ) = c2p(r cos φ, r sin φ)` with `φ = offset + θ` for `"CCW"` and `offset − θ` for `"CW"`, and `pt2pr` its inverse, θ in `(-π, π]` *(default taken; Manim ignores both, a defect; with Manim's defaults the numbers are Manim's)*. `plot_polar_graph` goes through it |
| PP-5 | `get_coordinate_labels(r_values, a_values)` returns Manim's `VDict`-like pair: `[0]` the radius numbers (by default the x axis's tick values `> 0`, placed as the x axis numbers), `[1]` the azimuth labels (by default `a_values = arange(0, 1, 1 / azimuth_step)`, fractions of a turn), each label `next_to` its rim point in the direction from the plane's centre, `azimuth_label_buff` away, at `azimuth_label_font_size`, the rim point `pr2pt(radius_max, a · TAU)`. Text as Manim's: `get_radian_label` for π and τ radians, `{360a:g}^{\circ}`, `{400a:g}^{g}`, `{a:g}`. `add_coordinates` adds them, keeps them as `coordinate_labels` and returns the plane. The labels follow the plane (a shift, a scale, an animated range) *(Manim places them around the scene origin with the radius `get_right()[0]`, and its `[0]` is the whole x axis, added a second time: defects)* |
| PP-6 | `get_radian_label(number, font_size=24, **kwargs)` is Manim's, string for string: `number` a fraction of a turn, written with `\pi` or `\tau`, compact (`\tfrac{3\pi}{4}`) or not (`\tfrac{3}{4}\pi`) by `azimuth_compact_fraction`, `0` for zero; it calls `AngleFormatter` (AF-1) |

## AF — `mp.AngleFormatter`

| ID | Row |
|---|---|
| AF-1 | `mp.AngleFormatter(units="PI radians", compact_fraction=True, max_denominator=100)` is a `Formatter` (task 08) of angles in radians: for `"PI radians"` and `"TAU radians"`, the fraction `θ / π` or `θ / τ` limited to `max_denominator`, written as `get_radian_label` writes it; `"degrees"` `{deg:g}^{\circ}`; `"gradians"` `{grad:g}^{g}`; `None` the fraction of a turn `{θ/τ:g}`. Units outside the five raise `ValueError` naming `units` |
| AF-2 | On any axis: `ax.x.set_formatter(mp.AngleFormatter())` with `ax.x.set_locator(mp.MultipleLocator(PI / 2))` writes `0, π/2, π, 3π/2, 2π` as `0`, `\tfrac{\pi}{2}`, `\pi`, `\tfrac{3\pi}{2}`, `2\pi`, the sign kept for negative angles (`-\tfrac{\pi}{2}`) |

## PX — `mp.PolarAxes`, a true polar system

| ID | Row |
|---|---|
| PX-1 | Data coordinates are `(r, θ)`, θ in radians, the order of Manim's `polar_to_point` *(default taken: matplotlib's `plot(theta, r)` puts θ first)*. The map is one coupled node (D7): the radial scale (linear, `"log"`, `"symlog"` or any `Scale`, as `x_scale`) maps `r` to a distance from the centre, `r_min` at the centre and `r_max` on the rim at `size / 2`; then `φ = azimuth_offset ± θ` (`"CCW"` +, `"CW"` −) and the point is `centre + d (cos φ, sin φ)`. `c2p(r, θ)` and `pr2pt(r, θ)` are the same map; `p2c` and `pt2pr` its inverse, θ in `[0, TAU)`, `p2c(c2p(r, θ))` within `1e-9` |
| PX-2 | Constructor validation as `PolarPlane`'s for the azimuth keywords; `r_range` as an axis range: `r_min < r_max`, both in the scale's domain (a log scale refuses `r_min ≤ 0`, naming `r_range`); `size > 0` |
| PX-3 | `ax.plot(r_func, theta_range=None, **kwargs)` draws `r = r_func(θ)` over `theta_range` (default `[0, TAU]`) as a function plot (task 11a) with θ as its parameter: adaptive in θ, sampled until the scene curve is smooth (the cardioid `1 + cos θ` on `r_range=(0, 2)` passes within `1e-3` scene units of its analytic point at each of 400 θ values), following `r_func`'s parameters and trackers as `plot`'s do, and taking the colour cycle, the legend and every plot keyword; `plot_polar_graph` is the same. `scatter(r, theta)`, `line`, `plot_line_graph` take `(r, θ)` data; a segment between two data points is joined straight in the scene, as on a log axis *(default taken: matplotlib interpolates a spiral arc)*. Task 16's and 17's helpers (drop lines, calculus, regions) and `errorbar` raise `NotImplementedError` naming the method and `PolarAxes` *(default taken: polar helpers are later)* |
| PX-4 | Clipping: every artist is clipped to the disk, to the annulus between `r_min` and `r_max` in data: a curve with `r > r_max` is cut where it crosses the rim, at the rim, within `1e-6` scene units, and resumes where it comes back; a point with `r < r_min` is invalid (F-705) on a log scale and cut at the centre on a linear one. `clip=False` draws it unclipped |
| PX-5 | The azimuth axis is the rim: a circle with ticks and numbers, `azimuth_axis.set_locator(...)`, `set_formatter(...)`, `set_tick_style(...)`, `set_ticks_direction(...)` and numbers as on any axis (task 10), its default locator `MultipleLocator(TAU / azimuth_step)` and formatter `AngleFormatter(azimuth_units, azimuth_compact_fraction)`, numbers outside the rim, `azimuth_label_buff` away from it in the direction from the centre, ticks pointing in (TH-11: the rim is a border). The axis is periodic: tick values are taken modulo `TAU` and keyed by their remainder, so `0` and `2π` are one tick with one number and a full turn of locator values never duplicates the first |
| PX-6 | The radial axis is a ray from the centre at `r_axis_angle` (scene angle), numbers beside it on the counter-clockwise side, no ticks by default, `r_axis.set_locator(...)` and the rest as on any axis, its default locator the step of `r_range` or `LogLocator` on a log scale. Grid: circles at the radial ticks (minor ones faded, `faded_line_ratio` as PP-2) and spokes at the azimuth ticks, from the centre to the rim, in `background_lines` and `faded_lines`, styled as PP-2, keyed by value, each styleable on its own |
| PX-7 | `set_r_range(r_range)` changes the radial range and `ax.animate.set_r_range(...)` animates it: the curves, scatter points, grid circles and radial numbers follow on every frame, keyed by value as F-413 keys ticks; the rim, the spokes and the azimuth numbers stay. A changed range with nothing else changed costs one map compile, no re-sampling of an unchanged curve's θ grid |
| PX-8 | A theme (task 20) fills `PolarAxes`' defaults as it fills `CartesianAxes`' (cycle, legend, grid style, tick direction); a `PolarAxes` takes `ax.add`, `ax.legend()`, `Create`, `DrawAxes`, `Transform` between two `PolarAxes` and copy, as a `CartesianAxes` does |

## ND — `Node` public

| ID | Row |
|---|---|
| ND-1 | `mp.Node` (the protocol of `core/nodes.py`, made runtime-checkable), `mp.AffineNode`, `mp.ScaleNode` and `mp.FunctionNode` are exported, typed and documented with numpy docstrings; `PolarAxes`' coupled map is one `FunctionNode` with its inverse, and it is the only polar-specific code in the map *(default taken: no system takes a user's own node yet; a curvilinear system of the user's own is later)* |

## Defects fixed (probed on 0.21.0)

`polar_to_point` and `pr2pt` on a `PolarPlane` ignore `azimuth_offset` and
`azimuth_direction`, so a point at azimuth 0 is off the spoke labelled 0 once either is
set. `get_coordinate_labels` places the azimuth labels around the scene origin, at the
radius `get_right()[0]`: on a shifted plane they ring the wrong centre, and once
coordinates are added the radius grows. Its first entry is the x axis itself
(`add_numbers` returns the axis), which `add_coordinates` then adds a second time. The
background lines hold a circle of radius 0.

## Tests

`tests/core/test_angle_formatter.py`: AF-1 string for string against Manim's
`get_radian_label` on a grid of fractions, both compactnesses, both constants, degrees,
gradians, `None`, negative angles, bad units. `tests/mobjects/test_polar.py`: the helpers
on `Axes`, a log axis and a twin; `PolarPlane` against Manim's on its defaults and on
`size`, `radius_max`, `faded_line_ratio`, every unit; the offset and direction fix; the
labels on a shifted plane; the grid following an animated range; `PolarAxes`' map and its
inverse, log and linear; a cardioid against its analytic curve; clipping at the rim; the
periodic azimuth axis; an animated radial range in a probe; the themes. Visual:
`test_polar_plane` with a `__manim` twin, `test_polar_plane_degrees_cw` with its twin,
`test_polar_axes_rose`, `test_polar_axes_log` and `test_polar_axes_clipped`. A frame-cost
reading: a flower curve and a scatter of 50 points on a `PolarAxes` under
`ax.animate.set_r_range`, p95 of `update` in ms, recorded, not gated.
