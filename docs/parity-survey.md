# Parity survey

Source material for `docs/scope.md`. Three axes, in the order D15 ranked them:

1. **Manim itself** — what an existing scene loses by switching to `manim-plots`.
   Decides whether people *can* move at all, so it outranks the other two.
2. **matplotlib** — what people expect a plotting library to have, and where the
   extension points get their shape.
3. **gnuplot 6.0 / OriginPro** — tick and axis control, where both of the above are
   thin.

All three are complete. Section 1 is enumerated by reflection and guarded by
`tests/test_parity_surface.py`; sections 2 and 3 are read from the respective manuals,
and only section 1 can have a drift test, because only Manim is a dependency.

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

A verdict of 0.1 promises the capability **and Manim's spelling** wherever the
semantics match (D17, F-1009). This replaces the survey's first reading, under which a
verdict promised the capability only. The notes say how each name is built: a tick
comes from a locator, a label from a formatter, an axis is a decoration that does not
own the mapping — and the Manim name stays on top of that machinery.

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
| `rotate_about_number` | `NumberLine` | **0.1** | falls out of the frame: `rotate(about_point=n2p(v))` moves it natively (D18) |
| `rotate_about_zero` | `NumberLine` | **0.1** | same |

### Artists (8)

| Manim method | Defined on | Verdict | Note |
|---|---|---|---|
| `get_graph_label` | `CoordinateSystem` | **0.1** | kept: a positional label and optional dot bound to the graph, not a legend entry (D27) |
| `i2gc` | `CoordinateSystem` | **0.1** | same |
| `i2gp` | `CoordinateSystem` | **0.1** | a query against the source and the map, not a search in the points |
| `input_to_graph_coords` | `CoordinateSystem` | **0.1** | same |
| `input_to_graph_point` | `CoordinateSystem` | **0.1** | same |
| `plot` | `CoordinateSystem` | **0.1** | analytic artist; `ax.plot(f)` |
| `plot_line_graph` | `Axes` | **0.1** | kept, returning Manim's `VDict` of `line_graph` and `vertex_dots`, built on `ax.line` and `ax.scatter` (D27) |
| `plot_parametric_curve` | `CoordinateSystem` | **0.1** | fourth artist; the only 0.1 source mapping one parameter to two coordinates |

### Decoration (17)

| Manim method | Defined on | Verdict | Note |
|---|---|---|---|
| `add_coordinates` | `CoordinateSystem`, `PolarPlane`, `ComplexPlane` | **0.1** | kept, implemented by a locator plus a formatter |
| `add_labels` | `NumberLine` | **0.1** | same |
| `add_numbers` | `NumberLine` | **0.1** | same |
| `add_ticks` | `NumberLine` | **0.1** | kept, implemented by the locator protocol |
| `get_axes` | `CoordinateSystem`, `Axes`, `PolarPlane` | **0.1** | kept; also `ax.x` / `ax.y`. Both are decorations and do not own the mapping |
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
| `function` | `_ScaleBase`, `LinearBase`, `LogBase` | **0.1** | our `Scale` names it `forward`; Manim's `LogBase` passed in `axis_config` keeps its meaning (D23). `LogBase.function` being the exponential is defect 10 |
| `get_custom_labels` | `_ScaleBase`, `LogBase` | **0.1** | the formatter, separate from the scale; `LogBase(custom_labels=True)` keeps working |
| `inverse_function` | `_ScaleBase`, `LinearBase`, `LogBase` | **0.1** | our `Scale` names it `inverse`; the broken ndarray guard is defect 8 |

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

Two decisions came out of building it, both now in `docs/plan.md`:

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
frame for free and stay in 0.1; `prepare_for_nonlinear_transform` is a non-goal
because our pipeline resamples rather than subdividing; and `ParametricFunction`'s
construction hooks are non-goals because the rebuild replaces them.

## 2. matplotlib 3.11.1

### How this section was made

matplotlib is **not** a dependency of this project and never will be. The surface was
enumerated in a throwaway environment, so the numbers below are reproducible without
adding anything to `pyproject.toml`. The script is committed:

```
uv run --no-project --with matplotlib==3.11.1 python tools/mpl_surface.py
```

**235** public callables defined on `Axes` / `_AxesBase` themselves (inherited `Artist`
machinery excluded, exactly as the Manim section excludes `Mobject`), **75** on `Axis`,
**13** locator classes, **11** formatter classes and **7** registered scales.

The full name list is committed as `tools/mpl_surface_snapshot.json`, and the script
compares the live surface against it name by name, so a count in this section cannot
quietly come from a different release.

Unlike the Manim section this one has **no drift test in the suite**: a test may only
import what the project depends on, and matplotlib parity is an explicit non-goal in
`docs/plan.md`. The script is the manual substitute. The
section exists for two reasons — to name the capabilities a user arrives already
expecting, and to borrow the *shape* of the extension points, which matplotlib got right
and Manim never attempted.

### 2.1 Artists (what `Axes` can draw)

| Capability | matplotlib | Verdict | Note |
|---|---|---|---|
| Analytic function | *(none)* | **0.1** | matplotlib has no analytic source: the user samples with NumPy and passes arrays. `ax.plot(f)` with adaptive sampling is ours, and none of the three frameworks has it |
| Line from arrays | `plot`, `semilogx`, `semilogy`, `loglog` | **0.1** | the log variants are a scale, not an artist |
| Scatter | `scatter` | **0.1** | value-mapped colour and size (`c=`, `s=`, `cmap=`) is 0.2 |
| Parametric | `plot(xs, ys)` | **0.1** | matplotlib does not distinguish it; we do, because one parameter mapping to two coordinates is what tests the `Source` contract |
| Step | `step`, `stairs` | **0.2** | |
| Bars and histograms | `bar`, `barh`, `bar_label`, `barbs`, `broken_barh`, `grouped_bar`, `hist`, `hist2d` | **0.2** | |
| Error bars | `errorbar` | **0.2** | |
| Filled regions | `fill`, `fill_between`, `fill_betweenx`, `stackplot` | **0.2** | |
| Reference geometry | `axhline`, `axvline`, `axline`, `axhspan`, `axvspan`, `hlines`, `vlines` | **0.2** | the same cluster as Manim drop lines and Origin reference lines |
| Annotation | `annotate`, `text`, `arrow`, `table`, `clabel` | **0.2** | |
| Event / rug | `eventplot` | **0.2** | Origin has a Rug tab for the same thing |
| Legend | `legend`, `get_legend`, `get_legend_handles_labels` | **0.1** | the one Manim defect with no workaround (defect 7) |
| Colour cycle | `set_prop_cycle` | **0.1** | minimal cycle only; theming is later |
| Fields | `quiver`, `quiverkey`, `streamplot` | **later** | one `FieldSource`, five artists (D15) |
| 2D scalar data | `imshow`, `matshow`, `pcolor`, `pcolormesh`, `pcolorfast`, `contour`, `contourf`, `spy` | **later** | the same pipeline head |
| Statistical | `boxplot`, `bxp`, `violinplot`, `violin`, `pie`, `pie_label`, `ecdf`, `hexbin` | **non-goal** | already named in `docs/plan.md`; `ecdf` and `hexbin` are transforms of data, so a user computes them and plots the result |
| Spectral | `acorr`, `xcorr`, `cohere`, `csd`, `psd`, `specgram`, `magnitude_spectrum`, `angle_spectrum`, `phase_spectrum` | **non-goal** | NumPy and SciPy do the transform; we plot its output |
| Unstructured meshes | `tricontour`, `tricontourf`, `tripcolor`, `triplot` | **non-goal** | |
| Artist adders | `add_line`, `add_patch`, `add_collection`, `add_artist`, `add_image`, `add_table`, `add_container`, `add_child_axes` | **non-goal** | the Manim scene graph is the container; `ax.add(artist)` is registration (D11) |

### 2.2 Range, autoscale, aspect

| Capability | matplotlib | Verdict | Note |
|---|---|---|---|
| Set and read the range | `set_xlim`, `get_xlim`, `set_xbound`, `get_xbound`, `set_ylim` | **0.1** | `set_x_range` / `set_y_range`, animatable natively under `.animate` (D21) |
| Reversed axis | `invert_xaxis`, `set_xinverted`, `xaxis_inverted` | **0.1** | a range whose start exceeds its stop is legal, and every locator must survive it — cheap now, a redesign later |
| Aspect lock | `set_aspect`, `get_aspect`, `set_box_aspect`, `apply_aspect`, `get_data_ratio`, `set_adjustable`, `set_anchor` | **0.1** | a `Map` node, not a negotiation (defect 4) |
| Axis on/off, tight, equal | `axis`, `set_axis_off`, `set_axis_on` | **0.1** | as decoration visibility and the aspect node |
| Autoscale to the data | `autoscale`, `autoscale_view`, `set_autoscale_on`, `relim`, `update_datalim`, `has_data`, `margins`, `set_xmargin`, `use_sticky_edges` | **0.2** | **the largest expectation gap in 0.1**, and a deliberate one: an animated range is a parameter the author drives, and an axis that rescales itself mid-animation is usually the wrong pedagogy. Deferred with a note, not overlooked |
| Position and layout | `get_position`, `set_position`, `reset_position`, `set_axes_locator`, `label_outer`, `get_subplotspec`, `get_gridspec` | **non-goal** | the Manim scene places the mobject |
| Insets | `inset_axes`, `indicate_inset`, `indicate_inset_zoom` | **later** | the zoom-plot backlog item |

### 2.3 Scales

Registered names: `linear`, `log`, `symlog`, `logit`, `asinh`, `function`, `functionlog`.

| Capability | matplotlib | Verdict | Note |
|---|---|---|---|
| Linear, log, symlog | `linear`, `log`, `symlog` | **0.1** | log carries minor ticks between decades (defect 9) and a correct inverse (defect 8) |
| User-supplied pair | `FuncScale` (`function`), `FuncScaleLog` (`functionlog`) | **0.1** | the collaborator A1.3: forward and inverse supplied by the user. matplotlib validates neither monotonicity nor invertibility; we falsify both by sampling at construction, and assert tick order at generation |
| Logit, asinh | `logit`, `asinh` | **0.2** | ordinary library scales once the contract exists |
| Clamp a range to the scale domain | `ScaleBase.limit_range_for_scale(vmin, vmax, minpos)` | **0.1** | **found here.** Neither `docs/plan.md` nor the defect list had it: a scale must be able to correct a range that leaves its domain (`x=(0, 10)` under log) rather than let a `-inf` propagate through the pipeline. Becomes `F-311` |
| Per-node inverse | `Transform.inverted()`, `transform_non_affine` | **0.1** | our node contract already requires it; matplotlib is the precedent |
| Transform tree | `transData = transScale + transLimits + transAxes` | **0.1** | independent confirmation of `Source -> Map -> placement`, and of clipping in the local space of the system rather than in data or scene space |

### 2.4 Ticks: locators and formatters

The split — a *locator* decides where ticks go, a *formatter* decides what they say, and
a *scale* supplies sensible defaults for both — is matplotlib, and it is what Manim is
missing. All twelve concrete locators:

| matplotlib locator | Verdict | Ours |
|---|---|---|
| `AutoLocator` | **0.1** | `MaxN`, on request; the default stays Manim's step (`docs/scope.md`, defaults table) |
| `MaxNLocator` | **0.1** | `MaxN(n)`, nice-number steps |
| `MultipleLocator` | **0.1** | `Multiple(step)`, and the sugar behind the Manim `x_range` triple |
| `FixedLocator` | **0.1** | `Fixed([...])`, the gnuplot explicit list |
| `LinearLocator` | **0.1** | *n* evenly spaced; falls out of `Fixed` |
| `NullLocator` | **0.1** | no ticks |
| `LogLocator` | **0.1** | decades plus subs (defect 9) |
| `AutoMinorLocator` | **0.1** | minor count between majors |
| `SymmetricalLogLocator` | **0.1** | ships with symlog |
| `IndexLocator` | **0.2** | categorical axes |
| `LogitLocator`, `AsinhLocator` | **0.2** | with their scales |

| matplotlib formatter | Verdict | Ours |
|---|---|---|
| `ScalarFormatter` | **0.1** | the number formatter |
| `FormatStrFormatter`, `StrMethodFormatter` | **0.1** | one format-string formatter |
| `FuncFormatter` | **0.1** | a callable, the collaborator A3.3 |
| `FixedFormatter` | **0.1** | explicit labels paired with an explicit tick list |
| `EngFormatter` | **0.1** | SI prefixes |
| `LogFormatter` and its `SciNotation` and `Mathtext` variants | **0.1** | LaTeX exponent labels; our LaTeX formatter covers both |
| `NullFormatter` | **0.1** | unlabelled ticks — what a mirrored axis needs |
| `PercentFormatter`, `LogitFormatter` | **0.2** | |

`Axis`-level control worth taking:

| matplotlib | Verdict | Note |
|---|---|---|
| `set_major_locator`, `set_minor_locator`, `set_major_formatter`, `set_minor_formatter` | **0.1** | major and minor are configured separately, so the API is per-level from the start |
| `set_tick_params`, `get_tick_params` | **0.1** | our `ax.x.ticks` descriptor |
| `remove_overlapping_locs` | **0.1** | **found here.** A minor tick landing on a major one is a *different* problem from two labels overlapping, and both need an answer. Becomes `F-407` |
| `get_tick_space` | **0.1** | a density-aware locator needs to know how many labels fit, and the number comes from the rendered label size, so the locator protocol must be allowed to ask |
| `ScalarFormatter` offset text (the shared `x 10^3`) | **0.2** | **contract consequence.** Label text is per tick, but the offset is per axis. If the formatter protocol returns only per-tick strings in 0.1, adding the offset in 0.2 breaks it. So the 0.1 protocol returns per-tick strings **and** an optional axis-level offset string, `None` everywhere until 0.2 fills it in. Becomes `F-503` |
| `set_label_coords` | **0.2** | axis-title placement |
| `axis_date`, `set_converter`, `convert_units`, `update_units`, `have_units` | **0.2** | the unit framework is how a date axis works in matplotlib, and it is the machinery the date/time stress case is checked against |
| `set_view_interval`, `set_data_interval`, `limit_range_for_scale`, `get_minpos` | — | internal plumbing, listed so the reader knows it was considered |

### 2.5 Second axes, sharing, grids

| Capability | matplotlib | Verdict | Note |
|---|---|---|---|
| Grid | `grid`, `get_xgridlines`, `set_axisbelow` | **0.1** | |
| Mirrored decoration | `secondary_xaxis(functions=(f, g))` | **0.1** | same `Map`, second decoration — the first half of the collaborator dual-axis request |
| Independent second scale | `twinx`, `twiny` | **0.2** | a second `Map` sharing the system's frame |
| Linked axes | `sharex`, `sharey`, `get_shared_x_axes` | **0.2** | backlog |
| Interaction | `can_pan`, `can_zoom`, `start_pan`, `drag_pan`, `end_pan`, `format_coord`, `pick`, `set_navigate`, `set_mouseover` | **non-goal** | there is no cursor in a rendered animation |
| Renderer plumbing | `draw`, `draw_artist`, `redraw_in_frame`, `get_tightbbox`, `set_rasterized`, `set_agg_filter`, `set_clip_box`, `set_zorder`, `set_snap`, `set_url`, `set_gid`, `set_animated` | **non-goal** | Manim owns rendering |

### 2.6 What the matplotlib pass changed

Three findings, none cosmetic, all three now `F-*` in `docs/scope.md`:

- **A scale must be able to clamp a range** (`limit_range_for_scale`). Without it,
  `x=(0, 10)` under a log scale is a `-inf` that propagates through the whole pipeline.
- **Minor-on-major tick collision is not label overlap.** Two problems, two mechanisms;
  the plan had only the second.
- **The formatter protocol needs an axis-level slot in 0.1** for the shared exponent,
  even though nothing fills it until 0.2 — contracts freeze in 0.1, so the hole has to be
  cut now.

And one deliberate refusal, recorded rather than left implicit: **no autoscale in 0.1**.

## 3. gnuplot 6.0 and OriginPro

Both are here for one reason: tick and axis control, where matplotlib is adequate and
Manim is absent. gnuplot is quoted from the 6.0 manual; Origin from the Axis-dialog help
at `docs.originlab.com/origin-help/general-axis-dialog`.

### 3.1 gnuplot `set xtics`

```
set xtics {axis | border} {{no}mirror}
           {in | out} {scale {default | <major> {,<minor>}}}
           {{no}rotate {by <ang>}} {offset <offset> | nooffset}
           {add}
           {  autofreq
            | <incr>
            | <start>, <incr> {,<end>}
            | ({"<label>"} <pos> {<level>} {,{"<label>"}...) }
           { font "name{,<size>}" }
           { textcolor <colorspec> }
```

| Option | Verdict | Ours |
|---|---|---|
| `autofreq` | **0.1** | `MaxN`, on request; the default stays Manim's step |
| `<incr>` and `<start>,<incr>,<end>` | **0.1** | `Multiple(step)` with an optional generation window |
| `("label" <pos> <level>, ...)` | **0.1** | `Fixed([...])` taking `(value, label, level)`. **The level matters**: an explicit list must be able to place a *minor* tick, which neither the matplotlib `FixedLocator` nor the plan expressed. Becomes `F-404` |
| `add` | **0.1** | explicit ticks *added to* the generated ones rather than replacing them — a two-line union in the locator now, a breaking change later. Becomes `F-405` |
| `axis` or `border` | **0.1** | `ax.x.position` taking `"origin"`, `"bottom"`, `"top"` or a data value — the collaborator requirement, free after D7 |
| `mirror` and `nomirror` | **0.1** | a mirrored decoration with a null formatter |
| `in` or `out` | **0.1** | tick direction (defect 12), plus `BOTH`, since centred is what Manim does today |
| `scale <major>,<minor>` | **0.1** | tick length, per level |
| `rotate by <ang>` | **0.1** | label rotation, and one of the three answers to overlap |
| `offset`, and `left` / `right` / `center` / `autojustify` | **0.1** | label offset and justification |
| `format`, `font`, `textcolor`, `enhanced` | **0.1** | the formatter plus a style descriptor; font and colour are Manim `Tex` arguments |
| `rangelimited` | **0.2** | draw the axis line and its ticks only over the extent of the data |
| `front` or `back` | **non-goal** | Manim z-order does this |

### 3.2 The rest of the gnuplot axis surface

| Command | Verdict | Note |
|---|---|---|
| `set mxtics <n>` | **0.1** | minor tick count: the collaborator request and defect 9 |
| `set x2tics`, `set x2range` | **0.1** mirrored, **0.2** independent | the split already made in D9 |
| `set link x2 via f(x) inverse g(x)` | **0.2** | the independent second scale, expressed exactly as our node pair |
| `set nonlinear x via f(x) inverse g(x)` | **0.1** | **the gnuplot answer is our answer**: a non-linear axis is a hidden linear axis plus a forward/inverse pair. Independent confirmation of the user-defined scale contract (A1.3) |
| `set logscale x <base>` | **0.1** | log with an arbitrary base |
| `set format x "%.2f"`, and gprintf `%h`, `%T`, `%P` | **0.1** | the format-string formatter, with the `%h` superscript form as the LaTeX formatter |
| `set grid xtics mxtics` | **0.1** | a grid per level, major and minor separately |
| `set xzeroaxis` | **0.1** | the axis line through the origin — the `_origin_shift` defect (13) from the other side |
| `set border` | **0.1** | which frame edges are drawn |
| `set xrange [] reverse` | **0.1** | see reversed ranges above |
| `set xrange writeback` and `restore` | **non-goal** | interactive session state |
| `set offsets`, `set margins` | **non-goal** | the Manim scene owns the frame, not the plot |
| `set key` (legend position, columns, box, order) | **0.1** minimal | placement and a box in 0.1; column layout and ordering in 0.2 |
| `set arrow`, `set label`, `set object` | **0.2** | annotations |
| `set jitter` | **0.2** | with scatter styling |
| `set style line` | **0.1** | named style parameters, no matplotlib shorthand (D12) |

### 3.3 OriginPro — the Axis dialog

**Evidence quality, stated up front.** The Origin help
(`docs.originlab.com/origin-help/general-axis-dialog`, read 2026-09-06) names no Origin
release, and the dialog varies by release and by plot type — the same page says "There
are 8 tabs in this dialog" while enumerating ten topics. So Origin is treated here as
**unpinned evidence**: it is a catalogue of capabilities worth having, never an
authority for a requirement. **No 0.1 requirement rests on Origin alone**: every `F-*` this section feeds into 0.1 is
also justified by a reproduced defect, a gnuplot option, or a collaborator answer. What
Origin alone supports is `F-312` (its scale library) and `F-612` (axis breaks), both 0.2,
plus two non-goals — the tick-label table and Apply To...
The ten topics: Show, Scale, Tick Labels, Title, Grids, Line and Ticks, Special Ticks,
Reference Lines, Breaks, Rug.

| Origin control | Verdict | Note |
|---|---|---|
| Scale types: Linear, Log10, ln, Log2, Reciprocal, Offset Reciprocal, Probability, Probit, Logit, Double Log Reciprocal | **0.1** as a contract, **0.2** as a library | ten built-in scales is precisely the argument *against* an enum: 0.1 ships linear, log and symlog, and every one of the other seven is a forward/inverse pair a user can supply |
| Rescale: Manual, Normal, Auto, Fixed From, Fixed To | **0.2** | the autoscale cluster; Fixed From and Fixed To are a one-ended autoscale, worth having when it arrives |
| Increment, or #Major Ticks, or #Minor Ticks | **0.1** | `Multiple(step)` versus `MaxN(n)` — the same choice, and the reason both ship |
| Line and Ticks: direction, style, length, colour, thickness, per side (Bottom/Top, Left/Right) | **0.1** | per-level, per-side tick styling |
| Axis position: default, percent offset, or at a specific value | **0.1** | a superset of the gnuplot `axis` / `border` pair, and the shape our `position` parameter takes |
| Arrows at axis begin and end | **0.1** | the Manim `include_tip`, except that the arrow must not change the tick range or the mapping (defect 2) |
| Tick labels: numeric, text from a dataset, date-time, month, day-of-week, column name | **0.1** numeric, **0.2** the rest | explicit text attached to a *numeric* position is `Fixed` and ships in 0.1; a label drawn from a dataset means the coordinate is a category, which is the 0.2 categorical axis (`F-415`), and date-time, month and day-of-week are the 0.2 temporal axis |
| `Decimal:1000` versus `Scientific:10^3` | **0.1** | formatter presets |
| Prefix, suffix, divide by a factor, custom formula | **0.1** | all four are the callable formatter |
| Rotation, with auto 45 and 90 degrees; text wrapping | **0.1** rotation, **0.2** wrapping | rotation is overlap answer number two |
| **Hide overlapping labels** | **0.1** | overlap answer number three, and the one Manim lacks entirely (defect 11) |
| Special Ticks: add or hide an individual tick at any value, with a custom label and its own style | **0.1** | exactly what keyed identity (D10) buys — `ax.x.numbers.at(2.0)` — plus explicit add and hide |
| Grids: major, minor, opposite side, colour | **0.1** | |
| Reference Lines | **0.2** | the drop-line and `axhline` cluster |
| Breaks | **0.2** | broken axes, already deferred |
| Rug | **0.2** | with `eventplot` |
| Tick label table, up to 10 rows with merged cells | **non-goal** | a table under an axis is a table, not an axis |
| Apply To..., copying settings between axes | **non-goal** | `ax.y.copy_style_from(ax.x)` is a two-line user function |

### 3.4 What the third axis changed

- **A tick level belongs in the explicit list.** `Fixed` takes `(value, label, level)`,
  because a gnuplot list can place a minor tick and ours must too (`F-404`).
- **Explicit ticks compose with generated ones** (`add`) rather than replacing them
  (`F-405`).
- **Three distinct answers to label overlap**, all 0.1: rotate, hide, and de-conflict by
  dropping candidates. Origin ships all three; the plan named only the third.
- **Axis position is a value, not an enum** — Origin places an axis at an arbitrary data
  value or a percentage offset, and the collaborator asked for the same thing.
- **Ten scale types in a commercial product is an argument for the pair-based contract**,
  not against it.
