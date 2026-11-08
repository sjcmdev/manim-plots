# Acceptance table — task 23, invalid input on the new surfaces

Draft, written 2026-11-08 for task 23, per ADR 0003 §9

Contract: [scope, F-1006](../scope.md#invalid-input-one-rule-surface-by-surface),
[ADR 0003 §3](../adr/0003-final-review-closure.md), and
[task 13 IV-1–IV-5](13-hardening.md). This is a specification, not a change to the
implementation. No failures are waived or marked xfail.

Construction means validating structure and configuration, before deriving geometry.
Wrong types raise `TypeError`; malformed values raise `ValueError`. No library warning
accompanies rejection. Messages name the public parameter, the first invalid array
index, and both actual lengths for a length mismatch. Indices are zero based; punctuation
is unrestricted *(default taken)*. Shape diagnostics name the public argument rather
than an internal temporary such as `values` or `samples` *(default taken)*.

Source values are distinguished from configuration: a bar's height (`barh`'s width),
surface heights, errors and image values may arrive at use already non-finite. They
are masked, not repaired. Negative error magnitudes and negative pie weights remain
construction errors. A non-finite geometric width, range or position remains an error.
For an aggregate, one box or violin dataset, one wedge, one bar and one voxel constitute
one sample; invalidating an aggregate never silently recomputes its statistics from
only the good observations. The box/violin interpretation is *(default taken)*.

At use, each invalid artist warns exactly once on initial derivation and once on its
next data/range change; repeated geometry reads and colour changes warn zero times.
Counts belong to the user-facing container, not each generated face, marker or cap
*(default taken: container boundary)*. A partially valid artist keeps its good geometry.
Every drawn point is finite. A region cell with any invalid corner is absent; an empty
source draws nothing and warns once. Explicit masks intentionally exclude data and do
not themselves warn *(default taken)*.

The test helpers `counted` and `library` are copied from task 13. Artists are retained
in variables. No test renders. The autouse font fixture substitutes a rectangle only
for `_glyph` font outlines used by density estimation; polar numbers are disabled.
Neither text appearance nor tick density is an oracle here. This fixture is necessary
because even unnumbered Cartesian axes currently measure a TeX digit. It does not
replace validation, mapping, sampling, masks, or geometry.

## HL — bound helpers, calculus, regions and 2D helpers

Earlier coverage: [16 HB-4, HB-7, HB-8, DL-3](16-helpers-lines.md) owns foreign graphs,
initial domain refusal/transient collapse, line types and positive line counts;
[17 FB-4, RR-7](17-helpers-regions.md) owns array rejection and Riemann choices.
[35](35-helpers-2d.md) supplies annotation/crosshair/end-label parameters.
Those rejection policies are retained; diagnostics and warning counts below fill gaps.

| ID | Row |
|---|---|
| HL-1 | NaN and either infinity in `axhline.y`, `axvline.x`, `axhspan.ymin`, `axvspan.xmin` raise, naming those public parameters. |
| HL-2 | Tangent `length=inf`, secant `dx=NaN` raise ValueError; an object as tangent `x` raises TypeError. |
| HL-3 | `fill_between` mismatched x/y1 arrays name y1 and both lengths (3, 2); a matrix x names x. Supplements FB-4. |
| HL-4 | With x=0,1,2,3 and top=1,1,bad,1, lower=0, only the cell [0,1] survives, for NaN and infinity. One warning per region per change; style/read deduplication as IV-1. |
| HL-5 | Empty x/y1 yields no region geometry and one warning. |
| HL-6 | A two-component scene point passed to either drop-line verb raises naming point *(default taken: scene points must be triples)*. |
| HL-7 | Annotation `xy[1]=NaN`, crosshair `x=inf`, end-label `buff=inf` raise naming the public input (and annotation index 1). Dot mobjects avoid text. |
| HL-8 | On a Cartesian log-x range crossing zero, derivative, area and Riemann artists see the positive normalised range and draw finite geometry without warnings; the positive explicit area/rectangle interval lies inside it. |
| HL-9 | Domain-column matrix: a log-y region with top 1,1,-1,1 drops the adjacent cells; negative-centred error sample, field grid tails outside log-y, wholly negative bar/box, log-crossing heatmap cells and step samples are invalid. A surface wholly below log-z and a voxel with a z=0 corner are empty. Exactly one warning per container. Shared by EB, FF, TD, BA, HI, HM, ST, VO below; log bar *baseline* exception BA-5 remains. |

## EB — error bars

[18 EB-2, EB-3, ED-2](18-errorbar.md) already owns negative errors, bad sample hiding,
log endpoint truncation without that cap, and animated point-count refusal. In
particular, an error end beyond a log domain reaches the viewport edge; it does not
invalidate an otherwise valid centre. This recorded exception is unchanged.

| ID | Row |
|---|---|
| EB-1 | Negative xerr/yerr at indices 1 and 2 reports the parameter and first index 1; supplements EB-2's rejection policy. |
| EB-2 | x/y length mismatch names y and lengths 3,2; yerr shape (3,2) for two samples raises naming yerr. |
| EB-3 | Non-finite capsize, elinewidth and capthick raise naming the parameter. |
| EB-4 | Multiple invalid parts of the same sample warn once for the ErrorBars container, not once per part; a repeated read or colour change is silent, a set_data change warns once more. Supplements EB-2's first warning. |
| EB-5 | Empty coordinates/errors draw no markers, stems or caps and warn once overall. Domain column: HL-9; normalised range: TW-6. |

## TW — twin, secondary and inset axes

[19 PO-1](19-twin-axes.md) owns offset validation;
[19b PA-3, SA-3](19b-top-axis.md) owns incompatible axis pairs and sampled finite,
monotonic inverse-pair checks. Inset placement uses the existing InsetAxes bounds API; task 29 has no inset rows
despite the task pointer.
Twins/insets are mappings, not sources; empty-source behaviour is that of their artist.

| ID | Row |
|---|---|
| TW-1 | Non-finite twin y_range/x_range endpoint raises naming range and index 1. |
| TW-2 | A noncallable member of secondary_xaxis.functions raises TypeError naming functions (SA-3 already covers malformed callable pairs). |
| TW-3 | Inset bounds [0,0,NaN,.5] raises naming bounds and first invalid index 2. |
| TW-4 | twinx, twiny, twin and inset conversions reject non-finite data/scene points; none returns NaN or clamps. |
| TW-5 | A twinx log-y range (-1,10) is normalised to a positive lower end before a finite constant graph is sampled; no warning. |
| TW-6 | Range-column matrix: helpers, errors, fields, bars, histograms, heatmaps, boxes and AppendData with autoscale on a log-y twin all draw finite geometry from a normalised positive range without warnings. The data themselves are positive and inside the viewport. |

## TH — themes

[20 TH-6](20-themes.md) already owns unknown preset/field/cycle rejection. Themes
configure defaults, have no source, domain, sample mask or empty-payload column.
get_theme takes no arguments; its observable state is checked after failed setters.

| ID | Row |
|---|---|
| TH-1 | Integer theme at set_theme and Axes raises TypeError naming theme, without changing get_theme's default. |
| TH-2 | An unknown preset fails atomically: after TH-6's ValueError, get_theme still returns the original theme. Tests restore the global default in finally. |

## FF — 2D/3D fields, flow and implicit curves

[21 FS-1, FL-3](21-fields-flow.md) owns field validity and stopping at a non-finite
velocity; [27 VT-5, VT-7, ST-3](27-fields-3d.md) owns arrow/coordinate/line choices;
[43 GF-5](43-spatial-animations.md) owns solid-arrow zero/non-finite degeneracy.

| ID | Row |
|---|---|
| FF-1 | Non-finite explicit x_range endpoint in 2D/3D fields raises naming x_range and index 1. |
| FF-2 | Stream dt=inf and max_anchors_per_line=1 raise ValueError; fractional n_repeats raises TypeError, each naming the parameter. |
| FF-3 | Entirely NaN/infinite 2D/3D vector grids have no extended drawable arrow, finite retained geometry, one warning at creation and per range change, none for reads/style. Supplements FS-1/GF-5. |
| FF-4 | The implicit zero contour of constant 1 has no geometry and warns once *(default taken: empty contour follows the empty-path rule)*. |
| FF-5 | Flow speed=inf raises naming speed; get_vector with one component raises naming coords. |
| FF-6 | Streamlines in an everywhere-NaN field stop at their seeds, with no extended path and one warning for the container. Domain samples: HL-9; configured ranges: TW-6. |

## PO — polar

[22 PX-2, PX-4, PX-7](22-polar.md) owns strict radial construction domains, radial
clipping/invalid points and radial updates. A log radius range starting at zero is
deliberately refused, unlike Cartesian F-311; no new normalisation rule is introduced.

| ID | Row |
|---|---|
| PO-1 | Non-finite size or azimuth_offset on either PolarAxes or PolarPlane raises naming the supplied parameter. |
| PO-2 | Both polar conversion directions reject NaN/infinity rather than returning it. |
| PO-3 | Everywhere-NaN radial function gives an empty polar path and exactly one warning; changing r_range warns once more, not once per read. |
| PO-5 | A radius-zero scatter sample on log-r is hidden and warns once, while its radius-one neighbour remains visible (PX-4 domain policy). |
| PO-4 | Exercise PX-2's exception: r_range=(0,3) with r_scale=log raises naming r_range. |

## TD — 3D systems, surfaces, geometry and slices

[24 TF-4](24-three-d.md) explicitly refuses out-of-domain configured 3D ranges.
[25 SF-7](25-surfaces.md) owns stable empty hole faces; [26 PL-3/4, LN-2, CO-7](26-geometry.md)
owns degenerate plane/line/coordinate choices; [28 SC-3, PS-3, ZD-3](28-slices.md) and
[28b PV-2, SV-4](28b-slice-view.md) own slice selection and placement refusals.
Camera/occlusion ([30](30-occlusion.md)) does not make invalid data drawable.

| ID | Row |
|---|---|
| TD-1 | Non-finite z_range and z_length raise naming the public parameter. |
| TD-2 | Triangle topology with out-of-bounds or repeated corners raises ValueError naming triangles and offending cell 0, before deriving faces. |
| TD-3 | c2p, cy2pt and sp2pt reject NaN/infinite coordinates. |
| TD-4 | Two-cell height, parametric and explicit triangle surfaces retain exactly two face slots: the face touching the NaN corner is empty, the other drawn. One warning per surface/change, none on colour/read. Supplements SF-7. |
| TD-5 | Non-finite u_range (index 1), zero wireframe resolution, infinite profile x, NaN slice_view x, and non-finite plane point (index 1) raise naming their inputs. |
| TD-7 | Triangle coordinate arrays with x length 3 and y length 2 report y and both lengths. |
| TD-8 | A singular 3D frame refuses p2c with ValueError mentioning singular. |
| TD-9 | Explicit empty triangle input draws nothing and warns once. |
| TD-6 | TF-4 exception: a log-z range (-1,10) raises naming z_range. Domain samples/empty whole surface: HL-9. |

## BA — bars and categorical axes

[31 BA-5](31-bars.md) deliberately maps a nonpositive log baseline to the viewport
edge. [31 CA-2](31-bars.md) already owns unknown fixed category rejection; category
labels are not rendered here. [33](33-histograms-3d.md) supplies bar3d geometry.

| ID | Row |
|---|---|
| BA-1 | bar/barh mismatched data arrays name height/width and lengths 3,2; matrix positions raise naming x/y. |
| BA-2 | Non-finite grouped_bar group_spacing and bar_label padding raise naming the parameter. |
| BA-3 | NaN/infinite bar heights (barh data widths, bar3d dz) hide the entire corresponding bar, leave the finite bar drawn and warn once per container/change; style/read silent. |
| BA-4 | Empty bar, barh and bar3d inputs draw nothing and warn once. |
| BA-5 | Exercise the baseline exception: bottom=0 on log-y [.1,10] starts at c2p(1,.1), without an invalid-sample warning. Negative samples elsewhere still follow HL-9. |
| BA-6 | Non-finite bar.width, barh.height and histogram bin count raise naming width, height, bins. Configured range: TW-6. |

## HI — histograms, step, stairs and stackplot

[32 HI-1](32-histograms.md) adopts NumPy counting; SP-1 already rejects unknown where;
HI-5 rejects incompatible color_by. [33](33-histograms-3d.md) adopts 2D binning for hist3d.
Source read: installed NumPy `lib/_histograms_impl.py`, `_get_outer_edges`,
`_get_bin_edges`, and `histogram`'s finite-range selection loop. Automatic ranges fail
on NaN/infinity; finite explicit bins omit such samples *(default taken)*. F-1006 still
requires a library warning when those samples are omitted. NumPy's internal exception
must gain the public input name/index at this boundary *(default taken)*.

| ID | Row |
|---|---|
| HI-1 | bins=0 or -1 raises ValueError naming bins in hist, hist2d and hist3d. |
| HI-2 | Step/stackplot data lengths 3,2 report both lengths and y/ys; stairs' insufficient edges name edges and the supplied/required edge counts 2,3 *(default taken: required edge count in this diagnostic)*. |
| HI-3 | hist([.25,bad]) with automatic bins raises naming x and index 1; explicit edges [0,1,2] on [.25,bad,1.25] give counts [1,1] and one library warning. NumPy choice above. |
| HI-4 | Step, stairs and stackplot accept a non-finite source value as a gap/hole and warn once; a colour/read causes no further warning. Their configuration (finite edges, baseline and where) is distinct from source heights. |
| HI-5 | Empty step/stairs/stackplot draws nothing and warns once. Domain: HL-9; range: TW-6. |

## DA — data animation

[34 SD/AP rows](34-data-animation.md) define keyed replacement and appending;
[40 LC-5](40-animation-package.md) owns concurrent-writer refusal. Non-finite data
do not become valid merely because an animation reveals them. Empty append to a
nonempty source is a no-op, not an empty artist *(default taken)*.

| ID | Row |
|---|---|
| DA-1 | AppendData rejects a Dot as TypeError naming artist. |
| DA-2 | Appended mismatched arrays report y and lengths 3,2; rank-3 coordinate input reports x. |
| DA-3 | AppendData on line/scatter with a NaN middle ordinate completes with one warning and an actual gap/hidden marker, never a bridge across x=1. |
| DA-4 | Empty append to a nonempty line is silent and preserves the exact geometry. |
| DA-5 | Native bars.animate.set_data rejects mismatched arrays naming height and both lengths, leaving the old bars intact. Range/autoscale: TW-6. |

## AK — dates, percent, logit and broken axes

[36 DT-1, LG-1, BK-2](36-axis-kinds.md) owns calendar types, logit domain and malformed
breaks. A wholly disjoint range cannot be repaired by F-311; this is the construction
range case tested below. Partial overhang retains scope F-311's normalisation; it is
not changed into a new logit exception. The conflict with the task's shorthand “logit
range outside (0,1)” is a maintainer question below.

| ID | Row |
|---|---|
| AK-1 | date2num arrays with NaT or a wrong object report public d and first invalid index 1, with ValueError/TypeError respectively. |
| AK-2 | PercentFormatter rejects xmax=0/inf and decimals=-1 naming the parameter *(default taken: decimals nonnegative)*. |
| AK-3 | Logit conversion rejects 0,1,-1,NaN; constructor range (2,3), wholly outside the domain, raises naming x_range. |
| AK-4 | BrokenScale's second malformed pair reports breaks and first bad row 1. Supplements BK-2. |
| AK-5 | Percent, logit and concise-date formatters give no labels for empty ticks; AutoDateLocator refuses non-finite configured bounds. Dropped candidates remain IV-2/IV-4's responsibility, before formatting. |

## HM — heatmaps, contours, colormaps and colorbars

[37 HM-3](37-heatmaps.md) already owns empty retained NaN cells. Matplotlib source read:
[`_ImageBase._normalize_image_array`](https://github.com/matplotlib/matplotlib/blob/v3.10.7/lib/matplotlib/image.py)
masks invalids; [`Colormap`](https://github.com/matplotlib/matplotlib/blob/v3.10.7/lib/matplotlib/colors.py)
defaults bad colour to transparent. Preserving explicit masks without warning is
*(default taken)*; scope adds warnings for unmasked NaN/infinity. For contours, the
scope's entire-cell rule takes precedence over corner triangulation choices.

| ID | Row |
|---|---|
| HM-1 | Rank-3 scalar data raise ValueError naming public Z (imshow) or C (pcolormesh). |
| HM-2 | Incompatible pcolormesh corners/value dimensions name C; hexbin x/y lengths 3,2 name y and both lengths. |
| HM-3 | Colormap positions [0,NaN,1] reports positions and first index 1; colorbar vmax=inf reports vmax. |
| HM-4 | imshow/pcolormesh bad cell (0,1), for NaN/infinity, stays empty while cell (1,1) draws; exactly one warning on creation and set_data, none on reads/colour. Supplements HM-3's geometry policy. |
| HM-5 | contour/contourf on a single cell with one NaN corner draw no paths/polygons even though other corners cross a requested level; warn once. |
| HM-6 | Empty imshow, pcolormesh and hexbin payloads draw nothing and warn once. |
| HM-7 | Explicitly masked *finite* imshow cell is absent, other cells draw, no library warning *(default taken)*. Domain: HL-9; range: TW-6. |

## ST — box, violin and pie statistics

[38 PI-1](38-statistics.md) already owns negative wedge rejection and normalize=False
sum limits. BX-2 deliberately makes a no-outlier fliers part silently empty: this
internal empty part does not count as an empty BoxPlot. No axes pie method exists in
the current public code; the pie cases use the existing mp.PieChart entry point.

| ID | Row |
|---|---|
| ST-1 | Box/violin positions lengths 3 for 2 datasets report both lengths and positions; infinite widths name widths; rank-3 datasets name x/dataset. |
| ST-2 | Negative wedge x[1] reports x and first invalid index 1; supplements PI-1. |
| ST-3 | One NaN/infinite observation invalidates its entire box/violin dataset; a non-finite pie weight hides only that wedge and normalises the finite weights *(default taken: normalise valid wedges)*. Finite neighbours draw; exactly one container warning per range/data change, none for style/read. |
| ST-4 | Empty BoxPlot, ViolinPlot and PieChart draw nothing and warn once. Box domain/range columns: HL-9/TW-6. Pie has no axis scale/domain column. |

## VO — voxels and isosurfaces

[39 IS-2](39-volumes.md) explicitly allows a level the samples never cross; this is a
valid non-intersection, not an empty input warning. VX-1/2 defines voxel exterior faces.

| ID | Row |
|---|---|
| VO-1 | Rank-2 filled and isosurface F inputs raise naming filled/F. |
| VO-2 | Infinite level raises naming level; a non-finite voxel corner array reports public x and first invalid row 1. Corner positions are configuration, distinct from voxel scalar values. |
| VO-3 | Two adjacent occupied voxels with c=[1,NaN] leave only the first voxel's six exterior faces, not five; invalid scalar drops the whole neighbouring sample and warns once. The surviving box spans c2p of data corners [0,0,0] and [1,1,1]. |
| VO-4 | No occupied voxels draws nothing and warns once *(default taken: all-false occupancy is empty input)*. |
| VO-5 | Exercise IS-2's exception: finite zero volume at level 2 has no faces and no warning. |
| VO-6 | One NaN corner of the only isosurface cube drops the entire cube and warns once. Domain: HL-9; configured 3D ranges: TD-6. |

## AN — animations with order, key, direction, lag or stages

Existing invalid policies are not redefined: [40 TC-4, SP-5, SF-2, AX-1](40-animation-package.md);
[41 ER-4, BA-1](41-helpers-decorations-animations.md);
[42 CU-2](42-chart-animations.md); [43 SC-4](43-spatial-animations.md);
[44 RR-3, RH-3, SV-3, SI-4, SS-4](44-topology-transitions.md).
These cover unknown string choices, numeric direction values other than ±1, invalid
topology targets and non-finite scalar targets. Type distinction and diagnostic/lag
gaps are below. A wrong-type order/direction is distinct from an unknown valid-type
name/value *(default taken: existing ValueError rows concern valid argument types)*.
HighlightTick's missing tick remains KeyError per [34 AX-2](34-data-animation.md), the
recorded key exception. Other unknown animation key names raise ValueError.

| ID | Row |
|---|---|
| AN-1 | Every explicitly lag-configurable class rejects negative, NaN and infinite lag_ratio with ValueError naming lag_ratio before changing points. Classes: BuildAxes, GrowBars, ShrinkBars, ShowPoints, GrowStack, GrowRiemann, GrowErrorBars, RevealAnnotation, RevealCrosshair, RevealLegend, FillColorbar, OpenInset, CloseInset, RevealCells, RevealContours, SweepPie, GrowBoxPlot, UnfoldViolin, GrowField, GrowStems, RevealWireframe, RevealWaterfall, SweepPolar, StackVoxels, RefineRiemann. |
| AN-2 | Numeric order=42 raises TypeError naming order for GrowBars/ShrinkBars, ShowPoints, RevealCells, RevealContours, GrowField and RefineRiemann; unknown *strings* remain the cited earlier ValueErrors. |
| AN-3 | String direction='left' raises TypeError naming direction for SweepRegion, SweepSpan, SweepSurface, StackVoxels. |
| AN-4 | Unknown BuildAxes stage list entry reports stage and index 1; unknown HighlightBar key reports key with ValueError; noncallable SortBars key reports key with TypeError. Missing HighlightTick remains KeyError. |
| AN-5 | GrowSurface/ShrinkSurface offset=object() raises TypeError naming offset; supplements SF-2's finite/domain checks. |
| AN-6 | Invalid cap_lag, explode amount and polar start_angle rejection names cap_lag/amount/start_angle, rather than a generic option group. |
| AN-7 | A genuinely empty Legend is a silent safe RevealLegend lifecycle (begin, partial frame, finish, cleanup), per 41 LE-4; it does not create source data or a spurious warning. |

Animations do not own separate scale configuration or source masks. Their domain,
range and empty columns are inherited from the target artist and the cited earlier
tables (notably 40 SP-3/TC-3, 41 EB-5/LC-4, 42 RC-2, 43 SS-5, 44 SV-3/SI-2).
Flow is covered by FF-5; AppendData by DA. TraceCurve's pacing, ExtendReference's
origin, GrowRegion's axis and RevealWireframe's families are already validated in the
cited tables; these are not invented order/key options. RebinHistogram,
SweepIsovalue and SweepSlice have topology/scalar targets owned by task 44, not new
order/direction/stage parameters.

## Defaults and maintainer questions

Defaults taken are marked inline: zero-based diagnostic indices and free punctuation;
public argument names at adapter boundaries; whole-dataset box/violin validity;
container warning ownership; silent intentional masks; empty implicit contours;
NumPy automatic-range refusal versus explicit-bin omission (with a library warning);
stairs supplied/required edge counts; silent empty append; nonnegative percent
decimals; valid-only pie normalisation; all-false voxel warning; wrong-type animation
choices distinguished from earlier invalid-value rows.

Maintainer decisions needed before these oracles freeze:

- Does “logit range outside (0,1)” override F-311 for *partial* overhang? The tests
  preserve F-311 and test a wholly disjoint range; changing partial overhang needs an
  explicit exception like polar PX-2 or 3D TF-4.
- Confirm valid-only pie normalisation and one-dataset-per-box/violin masking. The
  scope specifies sample masking but does not define aggregate statistical units.
- Confirm the warning boundary for composite artists, and silent intentional masks.
  Counting each internal leaf would conflict with the artist-level release rule.

## Local verification, 2026-11-08

Results below will record the local interpreter/Manim cell, not the four-cell release
matrix. A row passes only when all its parametrised instances pass. Failed assertions
are implementation gaps unless explicitly identified as an environment limitation.


Interpreter: Python 3.13.2, Manim 0.21.0, NumPy 2.5.2;
absolute interpreter path and worktree-only PYTHONPATH as requested.

| ID | Result | Passing / failing instances | One-line reason |
|---|---|---|---|
| HL-1 | fail | 6 / 6 | Spans report internal minimum instead of ymin/xmin. |
| HL-2 | pass | 3 / 0 | All instances pass. |
| HL-3 | fail | 0 / 1 | Mismatch omits the actual lengths. |
| HL-4 | fail | 0 / 2 | Invalid region samples do not warn. |
| HL-5 | fail | 0 / 1 | Empty region does not warn. |
| HL-6 | pass | 2 / 0 | All instances pass. |
| HL-7 | fail | 1 / 2 | Annotation reports p1 instead of xy; end-label accepts infinite buff. |
| HL-8 | pass | 1 / 0 | All instances pass. |
| EB-1 | pass | 2 / 0 | All instances pass. |
| EB-2 | fail | 0 / 1 | Error-bar coordinates report internal xs/ys instead of public x/y. |
| EB-3 | pass | 3 / 0 | All instances pass. |
| EB-4 | pass | 1 / 0 | All instances pass. |
| EB-5 | pass | 1 / 0 | All instances pass. |
| TW-1 | pass | 2 / 0 | All instances pass. |
| TW-2 | pass | 1 / 0 | All instances pass. |
| TW-3 | fail | 0 / 1 | Bounds error omits first invalid index 2. |
| TW-4 | pass | 4 / 0 | All instances pass. |
| TW-5 | pass | 1 / 0 | All instances pass. |
| TH-1 | pass | 2 / 0 | All instances pass. |
| TH-2 | pass | 1 / 0 | All instances pass. |
| FF-1 | pass | 2 / 0 | All instances pass. |
| FF-2 | pass | 3 / 0 | All instances pass. |
| FF-3 | fail | 0 / 4 | Field warning state is not renewed for a range/data change. |
| FF-4 | pass | 1 / 0 | All instances pass. |
| FF-5 | pass | 1 / 0 | All instances pass. |
| PO-1 | fail | 1 / 3 | PolarPlane reports x_length for size; infinite azimuth_offset is accepted. |
| PO-2 | pass | 4 / 0 | All instances pass. |
| PO-3 | pass | 1 / 0 | All instances pass. |
| PO-4 | pass | 1 / 0 | All instances pass. |
| TD-1 | fail | 1 / 1 | Infinite z_length reaches tick integer conversion without a parameter diagnostic. |
| TD-2 | fail | 0 / 2 | Out-of-bounds triangle raises IndexError; repeated corner is accepted. |
| TD-3 | pass | 6 / 0 | All instances pass. |
| TD-4 | fail | 0 / 3 | Surface holes omit the required artist warning. |
| TD-5 | fail | 0 / 1 | Non-finite u_range is accepted. |
| TD-6 | pass | 1 / 0 | All instances pass. |
| BA-1 | fail | 0 / 2 | Broadcasting/shape errors omit public parameter diagnostics. |
| BA-2 | fail | 0 / 1 | Grouped spacing uses a generic spacing message. |
| BA-3 | fail | 0 / 6 | Non-finite bar data are rejected instead of masking the affected bar. |
| BA-4 | fail | 0 / 3 | Empty bar containers do not warn. |
| BA-5 | pass | 1 / 0 | All instances pass. |
| HI-1 | pass | 6 / 0 | All instances pass. |
| HI-2 | fail | 0 / 3 | Array mismatch diagnostics omit public parameter and/or lengths. |
| HI-3 | fail | 0 / 2 | Automatic-range exception omits public x and first invalid index. |
| HI-4 | fail | 1 / 2 | Stairs/stackplot reject non-finite source values instead of masking. |
| HI-5 | fail | 0 / 3 | Empty step/stairs reject; empty stackplot is silent. |
| DA-1 | pass | 1 / 0 | All instances pass. |
| DA-2 | fail | 0 / 1 | Append mismatch reports internal xs/ys instead of public x/y. |
| DA-3 | fail | 0 / 2 | AppendData rejects non-finite source values instead of retaining invalid samples. |
| DA-4 | pass | 1 / 0 | All instances pass. |
| DA-5 | fail | 0 / 1 | Native bar data mismatch lacks the public height diagnostic. |
| AK-1 | fail | 0 / 1 | Date rejection omits public d and first invalid index. |
| AK-2 | fail | 2 / 1 | Negative decimals error names internal num_decimal_places. |
| AK-3 | fail | 0 / 1 | Disjoint logit range error omits x_range. |
| AK-4 | fail | 0 / 1 | Broken interval rejection omits first invalid pair index. |
| AK-5 | pass | 1 / 0 | All instances pass. |
| HM-1 | fail | 0 / 2 | Matrix diagnostics use internal values instead of Z/C. |
| HM-2 | fail | 0 / 1 | Mesh shape error omits public C. |
| HM-3 | pass | 1 / 0 | All instances pass. |
| HM-4 | fail | 0 / 4 | Unmasked non-finite heatmap cells do not warn. |
| HM-5 | fail | 0 / 2 | Invalid contour cells do not warn. |
| HM-6 | fail | 0 / 3 | Empty image/mesh rejects; empty hexbin omits warning. |
| ST-1 | fail | 0 / 2 | Layout rejection omits both actual lengths. |
| ST-2 | fail | 0 / 1 | Negative wedge rejection omits public x and first invalid index. |
| ST-3 | fail | 0 / 6 | Statistics reject non-finite samples instead of masking the whole affected sample. |
| ST-4 | fail | 0 / 3 | Empty statistical inputs raise instead of drawing nothing and warning. |
| VO-1 | fail | 0 / 1 | Isosurface dimension error names internal samples instead of F. |
| VO-2 | fail | 0 / 1 | Voxel corner error omits public x and first invalid index. |
| VO-3 | fail | 0 / 1 | Non-finite voxel c is rejected instead of dropping that voxel. |
| VO-4 | fail | 0 / 1 | All-false occupancy omits the empty-source warning. |
| VO-5 | pass | 1 / 0 | All instances pass. |
| AN-1 | fail | 51 / 24 | Some explicitly lag-configurable constructors accept invalid lag_ratio. |
| AN-2 | fail | 0 / 7 | Wrong-type order raises ValueError instead of TypeError. |
| AN-3 | fail | 0 / 4 | Wrong-type direction raises ValueError instead of TypeError. |
| AN-4 | fail | 0 / 1 | Stage rejection omits first invalid list index. |
| AN-5 | fail | 0 / 2 | Offset TypeError omits the public parameter name. |
| AN-6 | fail | 0 / 1 | Polar angular rejection names an option group instead of start_angle. |
| AN-7 | pass | 1 / 0 | All instances pass. |
| HL-9 | fail | 2 / 7 | Several domain-invalid artists omit warnings; box parts warn separately (5 warnings). |
| TW-6 | pass | 8 / 0 | All instances pass. |
| BA-6 | fail | 0 / 3 | Geometry width diagnostics use internal bar coordinates; infinite bins raises TypeError. |
| FF-6 | fail | 0 / 1 | NaN streamline velocity reaches integer conversion instead of stopping safely. |
| HM-7 | fail | 0 / 1 | Explicit finite masked cell is drawn. |
| VO-6 | fail | 0 / 1 | Non-finite isosurface cube is rejected instead of masked. |
| PO-5 | pass | 1 / 0 | All instances pass. |
| TD-7 | fail | 0 / 1 | NumPy stacking error omits public y diagnostic. |
| TD-8 | pass | 1 / 0 | All instances pass. |
| TD-9 | fail | 0 / 1 | Empty triangle source omits the required warning. |

Total: 132 passed, 140 failed.

Collection: **pass**, 272 cases. Ruff check `--no-cache`: **pass**. Ruff format
`--check --no-cache`: **pass**. Mypy `--no-incremental --cache-dir=nul`: **pass**.
All 87 acceptance IDs match test function prefixes. Git status shows only the two
requested new files; no source, other tracked document, picture or baseline changed.

All table rows were executed. Rendering, glyph appearance, the full existing suite and
the other three Python/Manim matrix cells were not checked; no row is skipped or xfailed.
For rows with several assertions, execution stops at the first failure in that instance;
a passing count never implies that later assertions in a failed instance ran.
