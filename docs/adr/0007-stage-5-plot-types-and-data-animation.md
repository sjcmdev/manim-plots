# ADR 0007 — Stage 5: bars, histograms, data animation and the rest of the list

- **Status:** Accepted, 2026-10-31, by the maintainer: "zdecydowanie należy dodać
  kolorowe histogramy 2d i 3d, bar-plot + wszystko co zaproponowałeś (może poza rurkami
  z prądem … to będzie część innej biblioteki)". Items marked *(default taken)* were not
  asked and stand unless vetoed.
- **Builds on:** ADR 0004 (one first release), ADR 0006 (3D, tasks 24-30, all merged).
- **Amends:** `docs/scope.md` *Deferred* and *Non-goals*: the rows named below move into
  the first release; each task amends its scope row in place, marked *(ADR 0007)*.

## Context

Stage 4 delivered 3D. The maintainer's review asked what is left and what could be
added; the answer listed bars and histograms coloured by value, data animations, 2D
helpers, further axis kinds, heatmaps, and, after the release, voxels, isosurfaces and
stream tubes. The maintainer took all of it into the release except stream tubes, which
belong in a separate library.

## Decision

### 1. What joins the first release

- **Bars**: `bar`, `barh`, matplotlib's `grouped_bar`, stacking through `bottom`,
  `bar_label`; categorical axes (strings as tick positions), which bars need.
- **Histograms in 2D**: `hist` (bins as a count, edges or a rule; `density`,
  `cumulative`, `histtype` bar / step / stepfilled, `stacked`, `orientation`, `weights`),
  `step`, `stairs`, `stackplot`. **Colour by value** on every bar-like artist: a
  colorscale over the bar's height, its count or its position, with `color_mapping`, so
  a colorbar follows it (task 25's `ColorMapping`).
- **Histograms and bars in 3D**: `hist3d` (a 2D histogram as `bar3d` columns), `bar3d`
  coloured by value, matplotlib's `Axes3D.bar` (2D bars laid in planes with `zs`,
  `zdir`), all with the colour-by-value rule.
- **Data animation**: bars and histograms grow from their base and shrink back, with a
  lag; `set_data` with a key so bars and bins move, enter and leave by identity; data
  appended live with the axes following (`autoscale`, `margins`, an animated rescale);
  bar-chart races (sorting with bars changing places); `Create` and `Uncreate` in data
  order; axes built step by step; a tick or a bar highlighted.
- **2D helpers**: `annotate` with an arrow in 2D, `axvspan` / `axhspan`, a crosshair with
  a coordinate readout following a tracker, a value label pinned to a curve's end,
  `fill_betweenx`, inset axes zooming a region with connector lines.
- **Axis kinds**: date and time axes (float days underneath, F-1xx's float pipeline
  kept), percent and logit formatters, broken axes.
- **Heatmaps**: `imshow`, `pcolormesh`, 2D `contourf`, `hist2d`, `hexbin`, heatmaps
  annotated with their values; each with `color_mapping` and a colorbar.
- **Statistics**: `pie`, `boxplot`, `violinplot` — previously non-goals, taken into
  "everything" *(default taken)*.
- **3D volumes**: `voxels` and isosurfaces (marching cubes in NumPy, no new dependency)
  *(default taken: stream tubes stay out)*.

### 2. Rules that hold for every new artist

ADR 0004 §9: every part addressable and styleable, defaults overridable, presets only set
defaults. Every artist is bound like the existing ones (ranges, moves, trackers), clipped
by F-706's rule, takes the cycle, has a legend handle where matplotlib has one, and works
on 2D and, where the row says so, 3D systems. Manim's names and meanings first where
Manim has them (`BarChart`'s parts and `change_bar_values` are the parity target of the
bar task), matplotlib's otherwise.

### 3. Tasks

Stage 5, before the release; each task gets its acceptance table and tests first, the
code is written by Codex from a brief, and Claude reviews, renders and merges:

- **31 — bars and categorical axes.**
- **32 — histograms in 2D, `step`, `stairs`, `stackplot`, colour by value.**
- **33 — histograms and bars in 3D.**
- **34 — data animation.**
- **35 — 2D helpers.**
- **36 — axis kinds: dates, percent, logit, broken axes.**
- **37 — heatmaps.**
- **38 — statistics: pie, box, violin.**
- **39 — voxels and isosurfaces.**
- **23 — the release**, last, as ADR 0006 left it.

31 comes first (32-34 build on its bars); 36, 37 and 39 do not depend on it and may run
beside it.

## Consequences

- The release moves back by tasks 31-39; its frozen API grows by these names.
- `docs/scope.md` loses most of its *Deferred* list and three *Non-goals*; date/time keeps
  the float pipeline decided in the paper-check (no datetime64 inside the core).
- F-1001 must still pass: none of these artists may add cost to a 2D system that does not
  use them.
