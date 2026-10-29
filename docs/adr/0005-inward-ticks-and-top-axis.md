# ADR 0005 — Inward ticks at the border; an independent top axis

- **Status:** Accepted, 2026-10-29. Asked for by the maintainer after the stage 3 page:
  "ticks inward automatically" and "an independent top axis". Items marked
  *(default taken)* were not asked and stand unless the maintainer vetoes them.
- **Builds on:** ADR 0004 §2 (what joins the first release), §4 (a contract change before
  the release goes through an ADR), §8 and §9.
- **Supersedes:** in `docs/acceptance/19-twin-axes.md`, TW-2's "ticks ... on the
  outside" (the numbers stay outside) and TW-1's twin of a twin for the axis it shares
  (§3); the outward default of an axis placed with an `offset` (task 10); in
  `docs/acceptance/20-themes.md`, `origin`'s "ticks outward". The scope defaults row
  *Tick shape* is amended by task 20.

## Context

An axis placed at a border straddles its ticks today, and one offset outward, a twin's
included, points them out. Origin, gnuplot and most printed figures point the ticks of a
framed plot into it, and the maintainer wants that without a call per axis.

`ax.twiny(...)` already gives a top axis with its own range and scale (F-610, task 19).
Three things around it are missing: a top axis computed from the bottom one (eV over nm,
kelvin over celsius), which the parity survey lists under matplotlib's
`secondary_xaxis(functions=(f, g))` and the 0.1 mirror does not yet do; a mirror styled
apart from its original, which shares the original's tick style and locator; and a twin
on a framed side, which a probe on 2026-10-29 shows drawn over the mirror there, two lines
at the top.

## Decision

### 1. Ticks at a border point inward

When no direction has been set, an axis at a border draws its major and minor ticks
`IN`, toward the data rectangle, on every side. An axis is at a border when it was placed
there: `set_position` with a named border (`"bottom"`, `"top"`, `"left"`, `"right"`),
with or without an `offset`, every mirror, a twin's own axis, a secondary axis (§2), and
the axes of a theme with `position="border"`. An axis placed through the data
(`"origin"`, a value, a `fraction`) keeps Manim's straddling ticks, also where a range
that excludes zero puts it on the rectangle's edge, so Manim's default picture is
unchanged *(default taken: the rule reads how the axis was placed, not where it ends up)*.

A set direction always wins: `set_ticks_direction`, `set_tick_style(direction=...)`, a
theme's `tick_direction`. `Theme.tick_direction` defaults to `None`, the rule above, and
every named theme takes it, so `origin` and `base` point their ticks in. Task 20
implements it; the baselines it changes are reviewed one by one.

### 2. An independent top axis

Task 19b, after task 20:

- `ax.secondary_xaxis(location="top", functions=None)` and `ax.secondary_yaxis(location=
  "right", functions=None)`, matplotlib's names and meaning (ADR 0004 §5): an axis on
  that side whose locator and formatter work in `forward(x)`, placed back on the shared
  map through `inverse`. It follows the system's range, animated included; `functions`
  must be monotonic on the range, else `ValueError`; `functions=None` is a labelled
  mirror. It returns the `Axis`, styleable as any other.
- A mirror styled on its own (ADR 0004 §9): its tick style, direction, locator and
  numbers set apart from its original's, which keeps sharing the range.
- A twin or a secondary axis on a side takes the place of that side's mirror: one line
  there, the mirror hidden while it stays *(default taken)*.
- `twiny` and the secondary axis shown in the gallery, a picture each and a film of an
  animated range carrying the top axis.

### 3. Any pair of axes

A plot binds to one x axis and one y axis, and every pair is one call away. Also task
19b:

- A twin's `twinx` and `twiny` share the calling system's other axis, matplotlib's
  meaning: `ax.twinx(...).twiny(...)` is the system of the top and the right axis. Today
  a twin of a twin shares the root's axis, so that call silently plots against the left
  axis (probed 2026-10-29). A twin's parent stays the root.
- `ax.twin(x=None, y=None)` returns the system of any existing x axis with any existing
  y axis of `ax`'s family, given as the axis or as a system whose axis it is; `None`
  keeps the calling system's. It is made once, draws nothing of its own, and binds
  artists, follows ranges and joins the legend and the colour cycle as a twin does
  *(default taken: the name, of the `twinx` family rather than `get_*`, because it
  returns a system)*.

```python
right = ax.twinx(y_range=(0, 1))       # bottom x, right y
top = ax.twiny(x_range=(0, 50))        # top x, left y
corner = ax.twin(x=top, y=right)       # top x, right y
corner.plot(f)                         # also: right.twiny(...) makes a new top axis
```

## Consequences

- Task 20 grows one row (TH-11) and a handful of changed baselines: the twin pictures and
  every border axis without a set direction.
- Task 19b adds `twin`, `secondary_xaxis` and `secondary_yaxis` to the public API and
  amends scope rows F-606 and F-610 and the parity survey's *Mirrored decoration* row.
