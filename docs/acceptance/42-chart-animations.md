# Acceptance table — task 42, chart animations

**Status: Record (merged 2026-10-31).** Written 2026-10-31 before any code, per ADR 0003 §9.
Rows and API choices marked *(default taken)* are proposed here and stand unless
vetoed. Contracts: ADR 0008 §§3–6 (flags, lifecycle, chart families, task split),
ADR 0004 §9 (customisation), tasks 31–32 (bars and stacks), 34 (GrowBars and
F-915), 37 (cells and contours), 38 (statistics), F-706 (viewport clipping),
F-918 (sampling), and LB-1 (retired glyphs).

Modules: `manim_plots/animations/bars.py` (GrowBars, GrowStack, RevealCells,
RevealContours), `manim_plots/animations/statistics.py` (SweepPie, ExplodePie,
GrowBoxPlot, UnfoldViolin). All names are also exported from
`manim_plots.animations` and `manim_plots`. Task 40 supplies the package and
`_base`; the tests here inspect only public behaviour, never `_base`.
Implementation may need presentation hooks in the existing artists; this
specification changes no artist code, other documentation, or baselines.

```python
GrowBars(bars, lag_ratio=0.05, *, order="data", reverse=False, remover=None, **kwargs)
GrowStack(series, *, lag_ratio=0.15, reverse=False, remover=None, **kwargs)
RevealCells(plot, *, order="row", lag_ratio=0.02, reverse=False, remover=None, **kwargs)
RevealContours(contours, *, order="level", lag_ratio=0.15,
               reverse=False, remover=None, **kwargs)
SweepPie(pie, *, lag_ratio=0, reverse=False, remover=None, **kwargs)
ExplodePie(pie, *, amount=0.1, indices=None, rate_func=there_and_back, **kwargs)
GrowBoxPlot(plot, *, lag_ratio=0.15, box_ratio=0.5,
            reverse=False, remover=None, **kwargs)
UnfoldViolin(plot, *, lag_ratio=0.15, body_ratio=0.5,
             reverse=False, remover=None, **kwargs)
```

The order, lag, amount and selection defaults in these signatures follow the
design notes *(default taken)*; the box/body split keywords are additional
choices *(default taken)*.

Each is an `Animation` subclass (a native composition may subclass
`AnimationGroup`). Cells and other large collections use one progress driver,
not a child animation per cell (ADR 0008 §2). `**kwargs` accepts native animation
options, including `run_time` and `rate_func`. Entrance rate functions retain
Manim's `smooth` default *(default taken)*. ExplodePie is an emphasis, has no
entrance/exit flags, and always restores at cleanup, including with a custom
rate function. Its default is `there_and_back` (ADR 0008 §3).

## Frame and customisation conventions

Let `t` be elapsed time divided by run time, before easing. For `n` ordered parts,
rank `i`, and lag `L`, define `w_i(t) = clip(t*(1+(n-1)*L)-i*L, 0, 1)`.
Forward progress is `p_i = rate_func(w_i(t))`; reverse progress is
`p_i = rate_func(w_i(1-t))`, reversing the whole schedule, rather than merely
each child's direction. Easing is applied once per local window, as in task 34
GR-1. For zero lag all parts share a window. Lag is finite and nonnegative.
No data or canonical colour is interpolated merely to hide an artist.

Ordering extensions, callback arguments, and statistical stage fractions below
are *(default taken)*. Bar height order is ascending signed height, with stable
ties. A bar-order callback receives the existing addressable bar and returns a
sort key. Cell callbacks receive `(key, value)` as two arguments: a matrix
`(row, column)` key or hexbin integer key, and its canonical scalar value.
`row` sorts by `(row, column)`, `column` by `(column, row)`, `diagonal` by
`(row+column, row, column)`, and `value` by scalar, ties in row order. Invalid
cells remain empty and retain their source keys. Hexbins support `row` (spatial
`(y, x)` order), `column` (spatial `(x, y)`), `value`, and callable order; diagonal
is for matrix cells only *(default taken)*. Filled contour ordering uses ascending
band midpoint; callbacks receive that midpoint. Line contour ordering uses the
numeric level, also passed to a callable. Orders affect timing, never retained
container order or keys. Resolve data-dependent order at `begin` *(default taken)*.

Origins and directions come from the artist: bar `bottom`/barh `left`, stack
baselines and layer sequence, pie `startangle`, `counterclock` and `explode`, box
median, violin position/centre line, and statistical `orientation`. They are
semantic origins rather than an extra animation `origin` option *(default taken)*.
Stack input layer order may be chosen by the caller; there is no sorting keyword
that silently changes which layer supports which. `lag_ratio` controls dataset,
layer, band, wedge, cell or bar staggering as stated in each row.

For each box's local progress `p`, box expansion uses
`b=clip(p/box_ratio,0,1)`; whiskers and summary visibility use
`s=clip((p-box_ratio)/(1-box_ratio),0,1)`. For a violin use the same split with
`body_ratio`: its body width uses `b`, summaries use `s`. Defaults `0.5`, with
explicit ratios strictly between zero and one, are *(default taken)*. The default
two-stage schedule includes caps and markers in the second stage; it does not
invent new statistical samples.

Tests use `linear` and the house `probe` at six frames/second. At one second its
records are `t=0,1/6,...,5/6`; canonical end assertions read the artist after play.
RC-1 uses a `7/6`-second play, giving seven records at normalised times `i/7`
that include both partial opacity and exact lag boundaries.
The shared autouse fixture in `tests/animations/conftest.py` substitutes Pango
`Text` for `MathTex` only when no `latex` executable is on PATH; the merge gate
keeps real TeX. No animation, mapping,
geometry, statistic or moving-object query is mocked. Probes are dry runs and
write no movie or picture baselines.

## GB — bars, grouped bars, and step histograms

| ID | Row |
|---|---|
| GB-1 | `GrowBars(..., order="data" or "height")` preserves the existing signed data growth: a bar's endpoint is `bottom+p_i*height`, its bottom and width stay fixed. `barh` exchanges axes and uses `left`. Test heights `[6,-2,3]`, bottom `2`, lag `0.5`, both orientations, at every recorded frame. Height order ranks are `[2,0,1]`; retained identities, order and height-derived colours remain canonical throughout and at finish *(default taken: stable ascending signed height)*. |
| GB-2 | A callable order receives each existing bar. For heights `[4,4,2]`, key `-height`, lag `1`, the first bar is complete and the tied second not started at `t=1/3`; the second is complete and third not started at `t=2/3`. Source heights and original bar order are unchanged *(default taken: callable protocol and stable ties)*. |
| GB-3 | Grouped bars grow with existing `GrowBars` on each `group.bar_plots` member in a native `LaggedStart`; no new grouped-bar animation is needed. For heights `[[2,4],[3,1]]`, zero inner/outer lag and linear easing, tops at `t=1/2` are `[[1,2],[1.5,0.5]]`, final tops are the supplied data. `lag_ratio` on the composition can stagger series; each GrowBars controls bars within its series *(default taken: recipe instead of accepting the grouped wrapper directly)*. |
| GB-4 | A step histogram also accepts existing `GrowBars(hist, ...)`: at zero lag each bin's count-derived step height grows from its actual `bottom`; it is not path-length tracing. Samples `[.2,.4,1.2]`, edges `[0,1,2]`, bottom `2` yield heights `2+2p` and `2+p`, fixed x edges and closing baseline endpoints. `counts` remains NumPy's `[2,1]`; final top is `4` *(default taken: accept the HistPlot wrapper, bin order for nonzero lag)*. |

## GS — stacks

| ID | Row |
|---|---|
| GS-1 | `GrowStack(StackPlot)` grows thicknesses from animated support: layer `j`'s lower boundary is the configured base plus the preceding layers' current thicknesses, not their final thicknesses. Constant series `2,4`, lag `.5`, have boundaries `[base,base+2p_0]` and `[base+2p_0,base+2p_0+4p_1]` at every x. Both `baseline="zero"` (`base=0`) and `"sym"` (`base=-3`) retain their canonical origin through the play *(default taken: keep the final symmetric origin rather than recenter each temporary stack)*. |
| GS-2 | `GrowStack(VGroup(lower_barplot, upper_barplot))` supports signed bar stacks. Positive and negative supports remain separate; nonzero residual configured bottoms are retained. At zero lag, lower heights `[4,-2]`, upper heights `[3,-5]` with bottoms `[4,-2]`, give intervals `[[0,2],[-1,0]]`, `[[2,3.5],[-3.5,-1]]` at `t=1/2`, and upper ends `[7,-7]` at finish. A third layer of opposite signs `[-1,2]`, bottoms zero, grows independently to `[[-.5,0],[0,1]]` at halfway. The caller supplies the actual bound bar layers *(default taken: explicit VGroup input)*. |
| GS-3 | `GrowStack(hist)` accepts stacked histogram datasets without changing edges or samples. For samples `[[.2,.3,1.2],[.1,1.1,1.2]]`, edges `[0,1,2]`, zero lag, local counts are `[2,1]` and `[1,2]`; at halfway the upper layer sits on `[1,.5]` with tops `[1.5,1.5]`, and final total tops are `[3,3]`. Existing NumPy density/weight semantics supply each canonical layer thickness *(default taken: HistPlot wrapper)*. |

## RC — cells

| ID | Row |
|---|---|
| RC-1 | `RevealCells` multiplies canonical per-cell fill/stroke opacity and annotation opacity by `p_i`, preserving scalar values, geometry, colours, keys and identities. Matrix `[[4,1,3],[2,3,5]]` tests row, column, diagonal, stable value ties and a descending-value callable, including lag `.5` boundaries and original fill opacity `.4`. `label_cells()` labels share their cell's window and retain their own canonical opacity *(default taken: callback and exact orders above)*. |
| RC-2 | Invalid cells (NaN) never acquire drawable points or labels during reveal or after finish. They do not become a fake zero-valued cell. A `2×2` image with one NaN retains that empty addressable cell throughout. |
| RC-3 | `pcolormesh` with unequal edges, `hist2d`, and `hexbin` share RevealCells; at zero lag their finite cells' opacities equal `t` from initial opacity one. Their full geometry, colours, mapping object and styles return unchanged. This is presentation only and must not change colorbar limits or scalar mapping *(default taken: hexbin inclusion)*. |
| RC-4 | A deliberately clipped pcolormesh cell spanning data x `-4..0` on an axis starting at `-2` retains only the rectangle `[-2,0] x [0,2]` at every opacity and after finish (F-706). Reveal never restores off-viewport geometry. |

## CT — contours

| ID | Row |
|---|---|
| CT-1 | `RevealContours(contourf, order="level")` fades each filled band with its own window. For two bands and lag `1`, the second is invisible when the first finishes at `t=.5`. Every band's points and closing edges remain canonical on every frame; do not trace triangulation or bookkeeping edges. |
| CT-2 | Filled contour bands with an inner excluded ring or disconnected islands keep every canonical subpath and its points at every partial alpha. Test the band `.3≤Z≤1.5` for `Z=(x-3)^2+(y-2)^2`, and for the minimum of two squared distances to `(1.5,2)` and `(4.5,2)`. No ring is bridged or hole filled by the reveal. |
| CT-3 | A contour-order callable receives numeric level/band midpoint; key `-level` reverses timing without replacing band keys. With two bands and lag `1`, at `t=.5` the upper band is fully opaque and lower is hidden *(default taken: callable protocol)*. |
| CT-4 | On line contours, draw each level independently using native Create semantics, with separate windows. For `Z=x`, levels `1,3`, y range `0..4`, and zero lag, each revealed line has fixed x equal to its level and visible data-y length `4t`. Completed lines span `0..4`; no connection is introduced between levels. Surface contours/projections belong to task 43 *(default taken: 2D line support here)*. |

## PS — pie entrance

| ID | Row |
|---|---|
| PS-1 | At zero lag SweepPie has one angular frontier through the pie's actual signed total angle; each wedge retains its canonical start angle and reveals `clip(t*sum(fractions)-sum(previous_fractions),0,fraction_i)` turns. With nonzero lag, wedge `i` reveals `fraction_i*p_i` turns. Test unequal fractions `[.2,0,.4]`, `normalize=False`, `startangle=30`, both clockwise and counterclockwise, lag `0` and `1`: the unused `.4` turn stays empty, the zero wedge stays zero, radius and actual arc endpoints match the data-derived angles. Fractions never change. |
| PS-2 | Wedge labels and percentage text fade by the wedge's revealed fraction of its canonical angle, with original text, placement and styles. For `[1,3]` at zero lag, progress is `clip(t/.25,0,1)` and `clip((t-.25)/.75,0,1)`; percentages remain `25%`, `75%`. A zero wedge's text uses its local window when lagged, and remains hidden until finish at zero lag *(default taken: proportional fade and zero-label policy)*. |

## PE — restoring pie emphasis

| ID | Row |
|---|---|
| PE-1 | `ExplodePie(pie, indices=[0], amount=.3)` adds `radius*amount*rate_func(t)` along the selected wedge's canonical bisector, on top of its existing explode offset. For `[1,3]`, radius `2`, explode `[.1,.2]`, displacement is `.6*there_and_back(t)*(√.5,√.5,0)` for wedge 0; wedge 1 stays fixed. Exact original geometry and styles return after play. The chart remains in the scene. |
| PE-2 | ExplodePie is the same public class at top level, package and `statistics` module, and restores even when given `rate_func=linear`; cleanup never commits an exploded position. This is an emphasis with an inverse displacement, not an entrance or remover. |
| PE-3 | Default `indices=None` selects all wedges and default amount is `.1` radius. Wedges, `.texts` and `.autotexts` move together along each canonical bisector on every frame, then all restore exactly. Existing explode offsets remain the starting placement; labels are not independently recentered. |

## BX — box plot

| ID | Row |
|---|---|
| BX-1 | GrowBoxPlot expands Q1/Q3 from the median in data: endpoints `median+b*(Q1-median)` and `median+b*(Q3-median)`, category width fixed. Test both orientations and both a sample with a high flier and an all-equal zero-IQR sample. Quartiles, median and samples remain canonical. The median line stays at the actual median; it may fade with `b` *(default taken: box/median first stage)*. |
| BX-2 | In the second local stage, each whisker starts at its true quartile and ends at `quartile+s*(whisker_stat-quartile)`; caps follow those endpoints and fade by `s`. Mean/fliers fade by `s` at their true data coordinates, never move in from invented statistics. Test default `box_ratio=.5` and override `.25`, both orientations, mean `5.9`, whiskers `4,6`, flier `11`, all inside the axes (a clipped flier stays hidden, F-706). No change to `stats` occurs *(default taken: two-stage schedule and cap fade)*. |
| BX-3 | `lag_ratio` staggers whole datasets, including their internal two-stage schedule. Two samples `[1..5]`, `[9..13]` at positions `[1,3]` keep medians `3,11`; each box has half-height `clip(2*p_i,0,1)`. Test zero lag and lag `1`, including the second dataset's start boundary *(default taken: dataset windows)*. |

The independent whisker oracle follows
[Matplotlib 3.10.7 `cbook.boxplot_stats`](https://github.com/matplotlib/matplotlib/blob/v3.10.7/lib/matplotlib/cbook.py#L1161-L1199):
percentiles give Q1/median/Q3, extrema inside the 1.5-IQR fences give whiskers,
with quartile fallbacks; values outside are fliers. The tests do not call the
library's statistic helper or construct a second box plot as their oracle.

## VN — violin plot

| ID | Row |
|---|---|
| VN-1 | UnfoldViolin keeps the sample-axis coordinate fixed and multiplies each body's density half-width about its position by `b`. Test `[1,2,3,4,6]`, nine KDE grid points, width `.5`, both orientations. Independently compute Gaussian kernels with Scott bandwidth `n**(-1/5)*std(ddof=1)` and normalise by peak density; each anchor is at `position±b*.25*density/peak`. |
| VN-2 | `.cbars`, `.cmins`, `.cmaxes`, `.cmeans`, `.cmedians` reveal by opacity `s` after the body stage. `body_ratio=.5` and `.25` override control the split. A callable bandwidth hook is evaluated for initial construction and never again for reveal frames; canonical source/KDE and summary geometry are retained *(default taken: summary fade and configurable split)*. |
| VN-3 | Whole violins use dataset windows under `lag_ratio`; optional absent summary lists need no placeholder. For two symmetric samples `[1..5]`, `[9..13]` at positions `[1,3]`, no extrema, and lag `0` or `1`, body x limits are `position±.25*clip(2*p_i,0,1)` *(default taken: dataset windows)*. |

## LC — lifecycle matrix (one parametrized test for every entrance in every row)

The seven entrance targets are GrowBars/BarPlot, GrowStack/StackPlot,
RevealCells/HeatmapPlot, RevealContours/contourf, SweepPie/PieChart,
GrowBoxPlot/BoxPlot, and UnfoldViolin/ViolinPlot. Thus LC-1 is the exit row and
LC-2 the canonical-finish row for **each** of GB, GS, RC, CT, PS, BX, VN.

| ID | Row |
|---|---|
| LC-1 | Each entrance with `reverse=True` removes the target by default. The same object can be introduced again with its data, leaf identities and styles intact; removal does not unregister axes bindings. `reverse=True, remover=False` keeps it in the scene; forward `remover=True` removes it. Cleanup leaves canonical presentation geometry even for a kept reverse target *(default taken, inherited from task 40)*. Existing user/binding updaters survive; no animation-owned updater remains. |
| LC-2 | Each entrance's final state is its canonical bound state, with all original leaf styles and binding updaters. After play widen x/y ranges without clipping and compare data anchors under the new map. For scatter marker parts compare their centres rather than treating scene-unit marker width as data width. A standalone pie instead follows later `set_data([2,0,2])`, yielding a π first wedge. Read final state after play, not the last probe record. |
| LC-3 | For each entrance, `there_and_back` with zero lag produces equal geometry at times `.35` and `.65`, and revisiting `.35` after `.8` restores the same geometry and opacity. There is no accumulated transform, destructive clipping or repeat KDE/source sampling. |
| LC-4 | Each name is the same class object at top level, package and its specified family module; an instance is a native Animation (including compositions). Existing GrowBars retains its top-level identity under task 40's move. |
| LC-5 | Every entrance's reverse frames, with linear easing and lag `1`, satisfy the independent forward data formula at `1-t`, including start and lag boundaries. Upper stack layers, later cells/bands/wedges, and later statistical datasets leave before earlier ones; this is not `1-p_i(t)` in forward order. |

## MV — live maps, sampling, and F-915

| ID | Row |
|---|---|
| MV-1 | Every axes-bound entrance may run beside `ax.animate.set_x_range((-4,16,2))`. At each frame derive presentation geometry through that frame's mapping and satisfy the same numeric factory oracle (signed bar bottoms, stack support, cell/band opacity, box median, violin centre). Axis upper x limit is `12+4t`, final `16`; bar width edge remains data x `.6`. No animation captures scene-space geometry once and ignores the moving map. |
| MV-2 | GrowBars on a tracker-bound height runs beside tracker `4→8`, bottom `2`: endpoint is `2+t*(4+4t)`. Add the artist to the scene. After play a further tracker change to `6` gives endpoint `8`. An unrelated static FunctionPlot on another system has no additional source calls (F-918). |
| MV-3 | **F-915/LB-1, all seven entrances and ExplodePie:** use Cairo's actual `begin_animations` moving/static partition with caching enabled in a dry run. Every changing drawable leaf and linked label is moving before static compilation; an unrelated still line, inserted first, remains static. Axes-bound cases also animate x range: the tick at `2` participates in the moving set, follows the current map and moves during play. A bar's separately owned labels follow the visible bar endpoint with the configured `.1` scene-unit padding. On every frame no drawable retired glyph lies outside current scene families. Unchanged scalar maps need no colorbar animation; these effects must not mutate them. |

## CU — exposed parts and invalid options

| ID | Row |
|---|---|
| CU-1 | Every exposed leaf can keep its own stroke width, colour and partial fill/stroke opacity through the entrance. Addressable parts remain: bars via `.at(key)`, grouped `.bar_plots`, StackPlot `.regions`, cells `.cells.at(key)` and `label_cells()`, contours `.at(level_or_band_index)`, pie `.wedges/.texts/.autotexts`, box `.boxes/.medians/.whiskers/.caps/.means/.fliers`, violin `.bodies/.cbars/.cmins/.cmaxes/.cmeans/.cmedians`. Set distinct stroke widths and nondefault opacities, play, and verify exact style and identity restoration. No default paint overwrites a user style. |
| CU-2 | Unknown order strings, box/body split outside `(0,1)`, nonfinite explode amounts and out-of-range wedge indices raise `ValueError` in construction before any artist changes. Invalid origin/domain checks supplied by task 40 remain in force; these new effects add no explicit origin keyword *(default taken: validation timing and error type)*. |

## Maintainer review and limits

All row IDs above have tests in `tests/animations/test_chart_families.py`.
The shared lifecycle rows are expanded over every entrance rather than copied
seven times. No row is intentionally untested. Focused tests are deliberately red
until task 40 and task 42 implement the missing APIs; collection must succeed.

Maintainer-only decisions: accept or veto the defaults above, especially whether
step histograms take the HistPlot wrapper, cell callback arguments, hexbin and 2D
line-contour inclusion, fixed final symmetric-stack origin, and the configurable
two-stage box/violin schedule. None blocks drafting or testing the proposed API.
Task 43 owns surface contours; task 44 owns rebinning. Full render films, the
supported Python/Manim matrix, performance measurements and release gates remain
for implementation/review, not this specification-only change.
