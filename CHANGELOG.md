# Changelog

All notable changes to manim-plots are recorded here, following
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

This section prepares the first release, 0.1.0. The package version remains
`0.1.0.dev0`; the maintainer decides the version bump, release merge and tag.

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
- **Documentation and packaging:** Sphinx and numpydoc API documentation, a migration
  guide, documented differences from Manim, reviewed examples with runnable scenes,
  and the `py.typed` marker for the annotated public API.

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

[Unreleased]: https://github.com/sjcmdev/manim-plots/compare/main...dev
