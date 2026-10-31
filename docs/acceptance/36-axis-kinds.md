# Acceptance table — task 36, axis kinds: dates, percent, logit, broken axes

**Status: Living until task 36 merges, then Record.** Written 2026-10-31 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: ADR 0007 §1 (axis kinds); `docs/scope.md` §1 of the
paper check (dates are an adapter above a float-only engine; locators key their ticks;
formatters see the whole tick list); task 08 (locators, formatters, `Labels.offset`);
task 31 (CA rows: the coordinate resolver for strings, which dates join).

Modules: `core/dates.py` (new: conversion, `AutoDateLocator`, `ConciseDateFormatter`),
`core/formatters.py` (`PercentFormatter`, `LogitFormatter`), `core/scales.py`
(`LogitScale`, `BrokenScale`), `core/ticks.py` (`LogitLocator`), `mobjects/axis.py` (date
axes, the offset label, breaks), `src/manim_plots/__init__.py`.

```python
def date2num(d) -> float | ndarray: ...   # mp.date2num
def num2date(x) -> datetime | list[datetime]: ...   # mp.num2date

class AutoDateLocator: ...              # mp.AutoDateLocator()
class ConciseDateFormatter: ...         # mp.ConciseDateFormatter()
class PercentFormatter:                 # mp.PercentFormatter(xmax=100, decimals=None, symbol="%")
class LogitScale(Scale): ...            # mp.LogitScale(); x_scale="logit"
class LogitLocator: ...                 # mp.LogitLocator()
class LogitFormatter: ...               # mp.LogitFormatter()
class BrokenScale(Scale): ...           # mp.BrokenScale(breaks, gap=0.05, base=None)

# on Axis
def set_breaks(self, breaks, gap=0.05) -> Self: ...
breaks: tuple[tuple[float, float], ...]
break_marks: VGroup
offset_label: Mobject | None
```

## DT — dates

| ID | Row |
|---|---|
| DT-1 | `mp.date2num(d)` is matplotlib's convention: float days since 1970-01-01T00:00 UTC. It takes a `datetime.datetime`, a `datetime.date`, a `numpy.datetime64` of any unit, or a sequence or array of them (returning an array); a naive datetime is UTC, an aware one is converted to UTC. `mp.num2date(x)` is the inverse, returning UTC-aware datetimes (a list for an array), exact to the microsecond for dates between 1900 and 2100 |
| DT-2 | Dates are accepted wherever a coordinate is: artist data (`line`, `scatter`, `bar`, …), `c2p`, `axvline`, and the range (`set_x_range((d0, d1))` or `(d0, d1, step_in_days)`); they pass through the same resolver as category names (CA-3), as `date2num`. The first date an axis sees makes it a **date axis**: its locator becomes `AutoDateLocator()` and its formatter `ConciseDateFormatter()`, and, when the dates came from data rather than a range, its range becomes the data's first and last date *(default taken, as CA-2)* |
| DT-3 | `AutoDateLocator` is matplotlib's frequency choice: for the span of the range it takes the first unit, from years down to seconds, in which the span counts at least 5 units, then the smallest interval of that unit's list (years 1, 2, 4, 5, 10, 20, 40, 50, 100, …; months 1, 2, 3, 4, 6; days 1, 2, 3, 7, 14, 21; hours 1, 2, 3, 4, 6, 12; minutes and seconds 1, 5, 10, 15, 30) giving at most that unit's maximum tick count (years 11, months 12, days 11, hours 12, minutes 11, seconds 11). Ticks sit on calendar boundaries: years divisible by the interval, months `1 + k·interval` on their first day, days of the month `1 + k·interval` (7 and 14: days 1, 8, 15, 22 / 1, 15), hours, minutes and seconds at multiples of the interval within their day / hour / minute, all at zero for the smaller units. Keys are the tick's date (F-413), so a tick keeps its identity while the range pans |
| DT-4 | `ConciseDateFormatter` is matplotlib's with its default tables: `formats = [%Y, %b, %d, %H:%M, %H:%M, %S.%f]`, `zero_formats = ['', %Y, %b, %b-%d, %H:%M, %H:%M]`, `offset_formats = ['', %Y, %Y-%b, %Y-%b-%d, %Y-%b-%d, %Y-%b-%d %H:%M]`; the level is the smallest unit (year … second) whose value differs among the ticks; a tick at that unit's zero (month 1, day 1, hour 0, …) takes the zero format; the offset is the last tick in the offset format, dropped when the level is years or months and some tick shows the year. Labels are text mode |
| DT-5 | An axis shows its formatter's `Labels.offset` as `axis.offset_label`: a `Text` (font size of the numbers) under the axis's far end (to the right of a y axis's top end), re-made when the string changes, `None` when there is none. This applies to every formatter that sets an offset *(default taken; no formatter did before)* |

## PC — percent

| ID | Row |
|---|---|
| PC-1 | `mp.PercentFormatter(xmax=100, decimals=None, symbol="%")` is matplotlib's: the label of `x` is `100·x/xmax` with `decimals` places, or, with `None`, the smallest shared precision that represents every scaled tick exactly (as `DecimalFormatter(None)`), followed by the symbol, escaped for math mode (`25\%`). `symbol=""` gives the bare number |

## LG — logit

| ID | Row |
|---|---|
| LG-1 | `mp.LogitScale()` maps `x` to `log10(x / (1 − x))` on the open domain (0, 1); `x_scale="logit"` (and `y_scale`, `z_scale`) selects it, with `LogitLocator()` and `LogitFormatter()` as the axis's defaults |
| LG-2 | `LogitLocator` puts ticks at `10^-k`, `1/2` and `1 − 10^-k` (k = 1, 2, …) inside the range; when more than the label budget would result, it keeps every second decade on both sides (matplotlib's thinning) |
| LG-3 | `LogitFormatter` writes `10^{-k}`, `\frac{1}{2}` and `1-10^{-k}` in math mode for those ticks, and the plain decimal for any other value |

## BK — broken axes

| ID | Row |
|---|---|
| BK-1 | `axis.set_breaks([(a1, b1), (a2, b2), …], gap=0.05)` on a linear axis removes the open intervals `(a_i, b_i)` from it: the remaining pieces of the range share `1 − n·gap` of the axis length in proportion to their extents, each break taking the fraction `gap`, through `mp.BrokenScale` (a piecewise-linear, invertible scale; a value inside a break maps linearly across the gap). Intervals must lie inside the range, be ordered and disjoint (else `ValueError` naming `breaks`); on a log or other non-linear axis it raises `ValueError` naming the scale *(default taken)*. `axis.breaks` reads them; `set_breaks([])` restores the plain axis |
| BK-2 | Ticks and numbers inside a break are dropped; the axis line is drawn as one segment per piece, interrupted over each gap; `axis.break_marks` holds two short parallel diagonal strokes (length 0.15, at 60° to the axis, the axis's colour) on each end of every gap *(default taken, the usual "//" marks)* |
| BK-3 | Artists are cut at the breaks as at the viewport (F-706): no drawn point lies strictly inside a break, so a curve crossing it becomes two pieces |

## Frame cost

Readings (p95 of `update`, ms) for the report: a date axis panning over two years with
a line of 1 000 dated points; a broken y axis under an animated range. F-1001 is
unchanged.
