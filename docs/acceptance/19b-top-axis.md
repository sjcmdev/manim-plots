# Acceptance table — task 19b, any pair of axes and an independent top axis

**Status: Living until task 19b merges, then Record.** Written 2026-10-29 before any
code, per ADR 0003 §9. Rows marked *(default taken)* were settled here without the
maintainer and stand unless vetoed. Contracts: ADR 0005 §1 (ticks at a border point
inward), §2 (an independent top axis), §3 (any pair of axes); ADR 0004 §5 (matplotlib's
names), §8 (no tip), §9 (customisation); `docs/scope.md` F-112, F-605, F-606 and F-610
(both amended here), F-1009; `docs/acceptance/19-twin-axes.md` (TW-1's twin of a twin,
superseded by PA-1). Builds on tasks 06-20.

Modules: `src/manim_plots/mobjects/system.py`, `mobjects/axis.py`.

```python
class CartesianAxes:
    def twin(self, x=None, y=None) -> CartesianAxes: ...
    def secondary_xaxis(
        self, location="top", functions=None, *, offset=None, **axis_config
    ) -> Axis: ...
    def secondary_yaxis(
        self, location="right", functions=None, *, offset=None, **axis_config
    ) -> Axis: ...


class Axis:
    def mirror(self, **axis_config) -> Axis: ...
```

The four corners, the case this task exists for:

```python
right = ax.twinx(y_range=(0, 1))  # bottom x, right y
top = ax.twiny(x_range=(0, 50))  # top x, left y
corner = ax.twin(x=top, y=right)  # top x, right y
corner.plot(f)
```

## PA — any pair of axes (ADR 0005 §3)

| ID | Row |
|---|---|
| PA-1 | A twin's `twinx` and `twiny` share the calling system's other axis, matplotlib's meaning: `right.twiny(...)` shares `right.y` and adds a top axis, so it is the system of the top and the right axis; `top.twinx(...)` shares `top.x` and adds a right axis. The same direction is unchanged: `right.twinx()` shares `right.x`, which is `ax.x` (TW-1). Every twin's `parent` is the root and `ax.twins` lists them in creation order; the new axis goes after the axes already on its side (TW-2) |
| PA-2 | `ax.twin(x=None, y=None)` returns the system of one x axis and one y axis of `ax`'s family. Each argument is an `Axis` that is some system's own x (y) axis, or a system, standing for its `x` (`y`); `None` keeps the calling system's. The system of a pair is unique: when a system of the family already has exactly those two axes, that one is returned (`ax.twin()` is `ax`, `ax.twin(y=right)` is `right`, `right.twin(x=top)` is the corner), else a new one is made, once, and the same call returns it again |
| PA-3 | Errors: an axis or a system from another root's family, a y axis passed as `x` or an x axis as `y`, a mirror, a secondary axis (neither has a map of its own) raise `ValueError` naming `x` or `y`; any other type raises `TypeError` naming it |
| PA-4 | A system made by `twin` is a twin: in `ax.twins`, its `parent` the root. It draws nothing of its own, so making it adds no points to the family. Everything else of task 19 holds for it: artists bind to it (TW-5) and map through its two axes (`c2p`, `p2c`); they follow each axis's range, by a call or `.animate`, on every frame, and the root's geometry (TW-6, TW-7); its labelled artists join the root's legend and its uncoloured ones the colour cycle (TW-9, TW-10); it clips per pair (TW-8), copies and transforms as a twin (TW-11). A range call on it changes the axis it shares: `corner.set_x_range(r)` is `top.set_x_range(r)` and moves everything bound to `top` |
| PA-5 | Every combination: with two x axes and three y axes, all six pairs are one `twin` call each, six distinct systems, each mapping through its own axes |
| PA-6 | Customisation (ADR 0004 §9): a pair system styles nothing itself; its axes are the paired ones (`corner.x is top.x`) and take their decoration calls there |

## SA — secondary axes (ADR 0005 §2)

| ID | Row |
|---|---|
| SA-1 | `ax.secondary_xaxis(location="top", functions=None, *, offset=None, **axis_config)` and `ax.secondary_yaxis(location="right", ...)`, matplotlib's names: an `Axis` added to the calling system's family on `location` (`"top"` or `"bottom"`, `"left"` or `"right"`, else `ValueError` naming `location`), `offset` outward as PO-1, with the `axis_config` keys (F-1009) for itself and numbers on unless `include_numbers=False` *(default taken)*. Its base is the calling system's x (y) axis |
| SA-2 | `functions=(forward, inverse)`, two callables vectorised over arrays; `None` is the identity, a labelled mirror. The locator runs between `forward(lo)` and `forward(hi)` of the base range, in ascending order; the tick of value `v` is drawn where the base axis has `inverse(v)`, and its number shows `v` (`number` is `v`). `get_tick_range()` returns the values in `forward`'s units. The default locator is `MaxNLocator()` *(default taken: the base's step means nothing in `forward`'s units)*; no minor ticks unless `set_locator` gives them. A decreasing `forward` (nanometres to electronvolts) is valid: its values decrease along the axis |
| SA-3 | `forward` and `inverse` are checked on 64 points of the base range, at creation and before every range the axis is drawn for (a call, or an animation's target as it begins): finite, strictly monotonic, and `inverse(forward(x))` within `1e-9` of `x` relative to the range; otherwise `ValueError` naming `functions`, and the call changes nothing |
| SA-4 | It follows its base: the range, by a call or `.animate`, on every frame; the scale (on a log axis `inverse(v)` is placed through the log map); the root's geometry. It is a border axis: ticks inward (ADR 0005 §1), numbers outside, no tip (ADR 0004 §8) |
| SA-5 | Customisation (ADR 0004 §9): the returned `Axis` takes every decoration call (`set_locator`, `set_formatter`, `set_tick_style`, `set_ticks_direction`, `set_grid`, `set_color`, `set_tips`), in `forward`'s units, without changing its base |
| SA-6 | It is a decoration, not a map: plots go through the base system, and `ax.twin(x=secondary)` raises (PA-3) |

## MI — a mirror styled on its own (ADR 0005 §2)

| ID | Row |
|---|---|
| MI-1 | `axis.mirror(**axis_config)` takes the `axis_config` keys for the mirror alone: `ax.x.mirror(include_numbers=True)` numbers the top of a box *(default taken: still unnumbered by default, F-606)* |
| MI-2 | Every decoration call on a mirror (`set_tick_style`, `set_ticks_direction`, `set_locator`, `set_formatter`, `set_color`) changes the mirror only. What the mirror has not set keeps following its original: a later `ax.x.set_tick_style(width=4)` reaches a mirror that set only its length. The range is always shared |

## RP — a twin on a framed side (ADR 0005 §2)

| ID | Row |
|---|---|
| RP-1 | A mirror is not drawn while a twin's own axis or a secondary axis of its direction sits on its side at the border (no `offset`): one line there, the mirror's parts without points. It is drawn again when that axis moves away. The order of creation does not matter, and the hidden mirror keeps its style; a theme's box (task 20) follows the same rule |

## Defects fixed

From task 19, probed on 2026-10-29: `ax.twinx(...).twiny(...)` shares the root's y axis,
so a curve meant for the top and right axes lands against the left one, with no error;
`twiny` on a framed plot draws its axis over the top mirror, two lines at the top; a
mirror made after `ax.x.set_tick_style(width=4)` draws its ticks at width 2.

## Tests

`tests/mobjects/test_top_axis.py`:

- PA-1, PA-2, PA-3: a twin's `twiny` and `twinx`, the same direction unchanged, the
  offset after the axes on a side; `twin` by axis and by system, the existing systems it
  returns, the same object twice; every error.
- PA-4, PA-5: no points added; `c2p` and `p2c` against the root's map; each axis's
  range by a call and animated, frame by frame; the root's shift; the legend and the
  cycle; a copy; a range call on the pair; six pairs of five axes.
- SA: placement and errors; Celsius and kelvin with `MultipleLocator(20)`; nanometres and
  electronvolts, decreasing; the identity; the default locator; a log base; the three
  errors and a refused later range; an animated range frame by frame; inward ticks, no
  tip; styling apart from the base.
- MI, RP: a numbered mirror; a mirror styled alone and still following; one line at the
  top and at the right under `twiny`, `twinx`, a secondary axis and `theme="origin"`, in
  both orders; the mirror back when the twin moves out.
- Visual: `test_top_axis_twiny`, `test_secondary_axis` and `test_four_corners`, no Manim
  twin. A frame-cost reading: a secondary axis and the four corner pairs under an
  animated range, recorded here, not gated.
