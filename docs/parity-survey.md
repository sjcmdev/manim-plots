# Parity survey

Source material for `docs/scope.md`. Three axes, in the order D15 ranked them:

1. **Manim itself** — what an existing scene loses by switching to `manim-plots`.
   Decides whether people *can* move at all, so it outranks the other two. Complete
   below.
2. **matplotlib** — what people expect a plotting library to have. To come.
3. **gnuplot 6.0 / OriginPro** — tick and axis control, where both of the above are
   thin. To come.

## 1. Manim 0.21.0

Enumerated from the installed source rather than from memory: every public callable
defined on a graphing class itself, inherited `Mobject` machinery excluded. The
generator asserts in both directions, so no name in the surface is missing a verdict and
no verdict names a method that does not exist.

**73 distinct public names across 98 members.** D15 estimated "around 40 entries" and
listed 18 from memory; all 18 exist, and the real surface is nearly double the estimate.

| Verdict | Count |
|---|---|
| **0.1** | 43 |
| **0.2** | 21 |
| **later** | 4 |
| **non-goal** | 5 |

A verdict of 0.1 does not mean the same spelling. Most of these arrive under the names
the plotting world already uses — a tick comes from a locator, a label from a formatter,
an axis is a decoration that does not own the mapping — and `PLAN.md` gives the reasoning.
What the verdict promises is that the *capability* is there in 0.1, so a scene using it
has somewhere to go.

Classes surveyed: `CoordinateSystem`, `Axes`, `ThreeDAxes`, `NumberPlane`, `PolarPlane`,
`ComplexPlane`, `NumberLine`, `ParametricFunction`, `FunctionGraph`, `ImplicitFunction`,
`_ScaleBase`, `LinearBase`, `LogBase`.

### Coordinate mapping (15)

| Manim method | Defined on | Verdict | Note |
|---|---|---|---|
| `c2p` | `CoordinateSystem` | **0.1** | also `ax @ (x, y)` |
| `coords_to_point` | `CoordinateSystem`, `Axes` | **0.1** | the spelled-out name is kept |
| `get_origin` | `CoordinateSystem` | **0.1** | and no `_origin_shift` clamp (defect 13) |
| `get_unit_size` | `NumberLine` | **0.1** |  |
| `get_unit_vector` | `NumberLine` | **0.1** |  |
| `get_x_unit_size` | `CoordinateSystem` | **0.1** |  |
| `get_y_unit_size` | `CoordinateSystem` | **0.1** |  |
| `n2p` | `ComplexPlane`, `NumberLine` | **0.1** | on an axis; `ComplexPlane`'s complex overload is 0.2 |
| `number_to_point` | `ComplexPlane`, `NumberLine` | **0.1** | same |
| `p2c` | `CoordinateSystem` | **0.1** | **fixed**: must invert `c2p` on every scale (defect 15c) |
| `p2n` | `ComplexPlane`, `NumberLine` | **0.1** | **fixed**; also stops projecting off-axis points silently (defect 14 note) |
| `point_to_coords` | `CoordinateSystem`, `Axes` | **0.1** | same fix |
| `point_to_number` | `ComplexPlane`, `NumberLine` | **0.1** | same |
| `rotate_about_number` | `NumberLine` | **0.1** | falls out of the placement chain: `rotate(about_point=n2p(v))` |
| `rotate_about_zero` | `NumberLine` | **0.1** | same |

### Artists (8)

| Manim method | Defined on | Verdict | Note |
|---|---|---|---|
| `get_graph_label` | `CoordinateSystem` | **0.1** | subsumed by the legend, which is 0.1 |
| `i2gc` | `CoordinateSystem` | **0.1** | same |
| `i2gp` | `CoordinateSystem` | **0.1** | a query against the source and the map, not a search in the points |
| `input_to_graph_coords` | `CoordinateSystem` | **0.1** | same |
| `input_to_graph_point` | `CoordinateSystem` | **0.1** | same |
| `plot` | `CoordinateSystem` | **0.1** | analytic artist; `ax.plot(f)` |
| `plot_line_graph` | `Axes` | **0.1** | splits into `ax.line(xs, ys)` and `ax.scatter(...)` |
| `plot_parametric_curve` | `CoordinateSystem` | **0.1** | fourth artist; the only 0.1 source mapping one parameter to two coordinates |

### Decoration (17)

| Manim method | Defined on | Verdict | Note |
|---|---|---|---|
| `add_coordinates` | `CoordinateSystem`, `PolarPlane`, `ComplexPlane` | **0.1** | replaced by locator plus formatter |
| `add_labels` | `NumberLine` | **0.1** | same |
| `add_numbers` | `NumberLine` | **0.1** | same |
| `add_ticks` | `NumberLine` | **0.1** | replaced by the locator protocol |
| `get_axes` | `CoordinateSystem`, `Axes`, `PolarPlane` | **0.1** | as `ax.x` / `ax.y`, which are decorations and do not own the mapping |
| `get_axis` | `CoordinateSystem` | **0.1** | same |
| `get_axis_labels` | `CoordinateSystem`, `Axes`, `ThreeDAxes` | **0.1** |  |
| `get_labels` | `NumberLine` | **0.1** | same |
| `get_number_mobject` | `NumberLine` | **0.1** | same |
| `get_number_mobjects` | `NumberLine` | **0.1** | same |
| `get_tick` | `NumberLine` | **0.1** | a tick is addressable by canonical key |
| `get_tick_marks` | `NumberLine` | **0.1** | same |
| `get_tick_range` | `NumberLine` | **0.1** | locator output; no `np.arange` accumulation (defect 1) |
| `get_x_axis` | `CoordinateSystem` | **0.1** | same |
| `get_x_axis_label` | `CoordinateSystem` | **0.1** |  |
| `get_y_axis` | `CoordinateSystem` | **0.1** | same |
| `get_y_axis_label` | `CoordinateSystem`, `ThreeDAxes` | **0.1** |  |

### Scales (3)

| Manim method | Defined on | Verdict | Note |
|---|---|---|---|
| `function` | `_ScaleBase`, `LinearBase`, `LogBase` | **0.1** | renamed; `LogBase.function` being the exponential is defect 10 |
| `get_custom_labels` | `_ScaleBase`, `LogBase` | **0.1** | becomes the formatter, separate from the scale |
| `inverse_function` | `_ScaleBase`, `LinearBase`, `LogBase` | **0.1** | renamed; the broken ndarray guard is defect 8 |

### Calculus (8)

| Manim method | Defined on | Verdict | Note |
|---|---|---|---|
| `angle_of_tangent` | `CoordinateSystem` | **0.2** | needs `i2gp`, which is why that ships in 0.1 |
| `get_T_label` | `CoordinateSystem` | **0.2** |  |
| `get_area` | `CoordinateSystem` | **0.2** |  |
| `get_riemann_rectangles` | `CoordinateSystem` | **0.2** |  |
| `get_secant_slope_group` | `CoordinateSystem` | **0.2** |  |
| `plot_antiderivative_graph` | `CoordinateSystem` | **0.2** | same |
| `plot_derivative_graph` | `CoordinateSystem` | **0.2** | same |
| `slope_of_tangent` | `CoordinateSystem` | **0.2** | same |

### Drop lines (5)

| Manim method | Defined on | Verdict | Note |
|---|---|---|---|
| `get_horizontal_line` | `CoordinateSystem` | **0.2** | decoration artist bound to a coordinate; trivial once the artist protocol exists |
| `get_line_from_axis_to_point` | `CoordinateSystem` | **0.2** | same |
| `get_lines_to_point` | `CoordinateSystem` | **0.2** | same |
| `get_vertical_line` | `CoordinateSystem` | **0.2** | same |
| `get_vertical_lines_to_graph` | `CoordinateSystem` | **0.2** | same, bound to a curve rather than a point |

### Polar (7)

| Manim method | Defined on | Verdict | Note |
|---|---|---|---|
| `get_coordinate_labels` | `PolarPlane`, `ComplexPlane` | **0.2** | `PolarPlane` and `ComplexPlane` variants |
| `get_radian_label` | `PolarPlane` | **0.2** |  |
| `plot_polar_graph` | `CoordinateSystem` | **0.2** |  |
| `point_to_polar` | `CoordinateSystem` | **0.2** |  |
| `polar_to_point` | `CoordinateSystem` | **0.2** |  |
| `pr2pt` | `CoordinateSystem` | **0.2** |  |
| `pt2pr` | `CoordinateSystem` | **0.2** |  |

### Fields (2)

| Manim method | Defined on | Verdict | Note |
|---|---|---|---|
| `get_vector` | `NumberPlane`, `PolarPlane` | **0.2** | arrives with vector fields, which bind to a system rather than to scene space |
| `plot_implicit_curve` | `CoordinateSystem` | **later** | a `FieldSource` artist |

### 3D (3)

| Manim method | Defined on | Verdict | Note |
|---|---|---|---|
| `get_z_axis` | `CoordinateSystem` | **later** |  |
| `get_z_axis_label` | `ThreeDAxes` | **later** |  |
| `plot_surface` | `CoordinateSystem` | **later** | a `FieldSource` artist |

### Non-goal (5)

| Manim method | Defined on | Verdict | Note |
|---|---|---|---|
| `generate_points` | `ParametricFunction`, `ImplicitFunction` | **non-goal** | Manim's mobject construction hook; ours is the rebuild, driven by the `points` getter |
| `get_function` | `ParametricFunction`, `FunctionGraph` | **non-goal** | the `Source` is public and holds the callable, so there is nothing to unwrap |
| `get_point_from_function` | `ParametricFunction`, `FunctionGraph` | **non-goal** | `i2gp` answers this against the pipeline |
| `init_points` | `ParametricFunction`, `ImplicitFunction` | **non-goal** | same |
| `prepare_for_nonlinear_transform` | `NumberPlane`, `PolarPlane` | **non-goal** | subdivides points to survive a non-linear transform; our pipeline resamples instead, so there is nothing to prepare |



### What the inventory changed

Two decisions came out of building it, both now in `PLAN.md`:

- **The parametric curve became the fourth 0.1 artist.** `plot_parametric_curve` was
  otherwise a straight regression, and more importantly it is the only source among the
  four that maps one parameter to two coordinates — the one case that exercises the
  `Source` contract on a multi-component output before that contract is frozen.
- **`input_to_graph_point` ships in 0.1 as a pipeline query.** It answers by evaluating
  the source and the map at `x` rather than searching the generated points, so it is
  exact between samples and survives a rebuild. That makes it part of the `Source`
  contract, not a convenience on top, even though most of its callers are the 0.2
  calculus cluster.

Four smaller calls were made without a redesign: drop lines go to 0.2 as ordinary
decoration artists; `rotate_about_number` and `rotate_about_zero` fall out of the
placement chain for free and stay in 0.1; `prepare_for_nonlinear_transform` is a non-goal
because our pipeline resamples rather than subdividing; and `ParametricFunction`'s
construction hooks are non-goals because the rebuild replaces them.

## 2. matplotlib

To come.

## 3. gnuplot 6.0 and OriginPro

To come.
