# Changelog

All notable changes to manim-plots are recorded here, following
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.1.0] - 2026-11-08

The first release. It is installed from GitHub, not from PyPI:
`pip install "git+https://github.com/sjcmdev/manim-plots@v0.1.0"`. The README has a
tutorial and a gallery of eighteen example scenes, each in `examples/` with its video.

### Added

- **Pipeline and rebuild:** immutable sources and payloads, lazy rebuilds through
  Source → Map → Shape, clipping, smoothing, dashes and versioned parameter bindings.
- **Coordinate mapping:** `CartesianAxes` (`mp.Axes`), invertible coordinate
  conversions, reversed ranges, explicit axis crossings, unit sizes, aspect locks
  and a frame that carries plots through geometric changes. Non-affine frames use
  bilinear interpolation; invalid conversions and singular inverses raise errors.
- **Scales:** linear, logarithmic and symmetric logarithmic scales, user-supplied
  vectorized forward/inverse pairs, and domain normalization for configured ranges.
- **Tick location:** multiple, maximum-count, log, symlog, fixed, null and minor-count
  locators; callable locators; explicit ticks that replace or supplement generated
  ticks; stable tick identities through animated ranges.
- **Labels and formatters:** decimal, printf, scientific, SI, fixed and null
  formatters; callable formatters; cached math glyphs; label rotation, offsets,
  justification and overlap policies.
- **Axis decoration and grid:** addressable lines, ticks, numbers, labels and grid
  lines; tick directions; border and mirrored axes; tips at either end; bound helper
  labels; `mp.NumberPlane` with major and faded lines. Manim's supported NumberLine
  configuration keys keep their names; unknown keys raise.
- **Sources and artists:** analytic function plots, array lines, scatter markers and
  parametric curves; Manim's plotting helpers; exact or interpolated source queries;
  adaptive sampling, pole splitting and viewport clipping with optional margins.
- **Legend and style:** labelled artists, bound or independent legends, merging and
  splitting legends, a colour cycle beginning with white, named line styles and
  markers, custom marker mobjects and optional stroke scaling.
- **Animation and Manim integration:** native `.animate` for ranges and function
  parameters, permanent frame changes followed by bound curves, keyed system
  transforms, artist lifecycle and registration, and `DrawAxes`, `TraceCurve`,
  `ShowPoints` and `Morph`.
- **Clipping per axis:** `clip=(x, y)`, each a bool or a margin past the axes.
- **Manim's graphing helpers, bound to their axes:** `get_vertical_line`,
  `get_horizontal_line`, `get_lines_to_point`, `get_line_from_axis_to_point`,
  `get_vertical_lines_to_graph`, `get_T_label`, `slope_of_tangent`,
  `angle_of_tangent`, `get_tangent_line`, `get_tangent_vector`,
  `get_secant_slope_group`, `plot_derivative_graph`, `plot_antiderivative_graph`,
  `get_area` and `get_riemann_rectangles`. Each follows its axes, accepts a
  `ValueTracker` wherever a value can change, and names every part it draws.
- **2D helpers:** `axhline`, `axvline`, `axhspan`, `axvspan`, `fill_between`,
  `fill_betweenx`, `annotate`, `crosshair`, `end_label`, `margins` and `autoscale`.
- **Error bars:** `ax.errorbar` with symmetric or asymmetric x and y errors, correct on
  log scales.
- **More axes:** `twinx`, `twiny`, `twin(x=, y=)`, `secondary_xaxis` and
  `secondary_yaxis` with `functions=(forward, inverse)`, an independent top axis, and
  `ax.inset` with connectors.
- **Themes and colour cycles:** `theme=` on one system or `mp.set_theme` for all; the
  themes `manim`, `origin`, `base`, `paper` and `lab`; the cycles `manim`, `origin`,
  `fire`, `colorblind` and `gray`. Ticks at a border point inward unless a direction is
  set.
- **Fields and flow:** `get_vector_field`, `get_stream_lines`, `get_vector`,
  `plot_implicit_curve` and the `Flow` animation, in 2D and 3D.
- **Polar:** `mp.PolarAxes` with data in `(r, θ)` and any radial scale,
  `mp.PolarPlane`, `plot_polar_graph` and Manim's polar conversions.
- **Axis kinds:** dates (`date2num`, `num2date`, `AutoDateLocator`,
  `ConciseDateFormatter`), `PercentFormatter`, `AngleFormatter`, `LogitScale` and
  broken axes (`BrokenScale`).
- **Bars and categories:** `bar`, `barh`, `grouped_bar`, `bar_label` and categorical
  axes whose ticks are the category names.
- **Histograms:** `hist`, `hist2d`, `step`, `stairs` and `stackplot`, with NumPy's
  binning rules.
- **Heatmaps and colour:** `imshow`, `pcolormesh`, `hexbin`, `contour`, `contourf`,
  `colorbar`, `Colormap` and the named `colormaps`.
- **Statistics:** `boxplot`, `violinplot` and `mp.PieChart`.
- **Three dimensions:** `mp.ThreeDAxes` with Manim's frame or matplotlib's box
  (`frame="box"`) and `ax.view(elev, azim)`; `plot_surface`,
  `plot_parametric_surface`, `plot_trisurf`, `plot_wireframe`,
  `plot_surface_of_revolution` and `waterfall`; points, segments, planes and
  cylindrical and spherical conversions; slices and `slice_view`; `hist3d`, `bar3d`,
  `stem`, `voxels` and `plot_isosurface`; faces drawn far to near as the camera turns.
- **Data animation:** `.animate.set_data(...)` on every data artist, `AppendData` with
  autoscaling, `SortBars`, `HighlightBar` and `HighlightTick`.
- **The animations package** `manim_plots.animations`: every entrance is also its exit
  with `reverse=True`; `BuildAxes(stages=…)`, `TraceCurve` paced by arc length or by
  parameter, `ShowPoints` in an order and with a pop; `ExtendReference`, `GrowRegion`,
  `SweepRegion`, `SweepSpan`, `GrowRiemann`, `GrowErrorBars`, `RevealAnnotation`,
  `RevealCrosshair`, `RevealLegend`, `FillColorbar`; `GrowBars(order=…)`,
  `ShrinkBars`, `GrowStack`, `RevealCells`, `RevealContours`, `SweepPie`, `ExplodePie`,
  `GrowBoxPlot`, `UnfoldViolin`; `GrowField`, `GrowStems`, `GrowSurface`,
  `ShrinkSurface`, `SweepSurface`, `RevealWireframe`, `RevealWaterfall`, `SweepPolar`,
  `OpenInset`, `CloseInset`; `RefineRiemann`, `RebinHistogram`, `StackVoxels`,
  `SweepIsovalue` and `SweepSlice`.
- **Invalid input, one rule everywhere:** a wrong type raises `TypeError` and a
  malformed value `ValueError`, naming the public parameter, the first invalid index
  and both lengths of a mismatch; a non-finite data sample is not drawn and raises one
  `ManimPlotsWarning` per artist per data change; an intentional mask is silent.
- **Documentation and packaging:** a README with installation, a tutorial and a gallery
  of eighteen example scenes with their videos (`examples/`, rendered by
  `tools/examples.py`); Sphinx and numpydoc API documentation, a migration guide,
  documented differences from Manim, reviewed pictures with runnable scenes, and the
  `py.typed` marker for the annotated public API.

### Supported environment

| Component | Supported for 0.1 |
|---|---|
| Python | 3.12 and newer; gate matrix: 3.12 and 3.13 |
| Manim Community Edition | 0.21.0 and 0.22.0 exactly |
| NumPy | 2.5 and newer |
| Renderer | Cairo |

Constructing a library mobject under OpenGL raises an error naming Cairo. Other
Manim versions require review of the pinned integration and issue a warning when
imported. See the user documentation for the differences from plain Manim.

[Unreleased]: https://github.com/sjcmdev/manim-plots/compare/v0.1.0...dev
[0.1.0]: https://github.com/sjcmdev/manim-plots/releases/tag/v0.1.0
