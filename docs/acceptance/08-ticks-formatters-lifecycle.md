# Acceptance table — task 08, ticks, formatters, lifecycle

**Status: Living until task 08 merges, then Record.** Written 2026-10-29 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: ADR 0001 §3 (`Locator`, `Formatter`, `Labels`) and §4
(the lifecycle table), ADR 0003 §2, §3, §5, §7, §8; `docs/scope.md` F-401-F-414,
F-501-F-507, F-903, F-905, F-907, F-919, F-920. Builds on tasks 06 and 07.

Modules: `src/manim_plots/core/ticks.py`, `core/formatters.py`, `core/lifecycle.py`.

## K — keys

```python
KEY_DIGITS = 12


def round_key(value: float) -> float: ...
```

| ID | Row |
|---|---|
| K-1 | `round_key(v)` rounds `v` to `KEY_DIGITS` significant digits (`float(f"{v:.11e}")`), so `0.1 + 0.2` and `0.3` share a key, and `-0.0` and `0.0` share one. A non-finite `v` raises `ValueError`. It is the key of `MaxNLocator`, `FixedLocator`, `NullLocator`, `MinorCountLocator` and wrapped callables (ADR 0003 §3) |

## L — locators (`core/ticks.py`)

```python
@runtime_checkable
class Locator(Protocol):
    def values(self, lo: float, hi: float, scale: Scale, max_ticks: int) -> FloatArray: ...
    def key(self, value: float) -> Hashable: ...
    def contains(self, value: float, lo: float, hi: float, scale: Scale, max_ticks: int) -> bool: ...

class MultipleLocator:   MultipleLocator(step: float = 1.0)
class MaxNLocator:       MaxNLocator(n: int | None = None, steps: Sequence[float] = (1, 2, 2.5, 5, 10))
class LogLocator:        LogLocator(base: float = 10.0, subs: Sequence[float] = (1.0,))
class SymLogLocator:     SymLogLocator(base: float = 10.0, linthresh: float = 1.0, subs: Sequence[float] = (1.0,))
class FixedLocator:      FixedLocator(entries: Iterable[float | tuple])
class NullLocator:       NullLocator()
class MinorCountLocator: MinorCountLocator(major: Locator, n: int = 4)
class FunctionLocator:   FunctionLocator(function: Callable[[float, float], Iterable[float]])

MAX_GENERATED = 10_000
def as_locator(obj: object) -> Locator: ...
```

Rules every locator follows:

| ID | Row |
|---|---|
| L-1 | `values(lo, hi, scale, max_ticks)` returns a new `float64` array in **axis order**: ascending for `lo < hi`, descending for `lo > hi` (F-209); empty for `lo == hi` — an empty range is the system's to refuse, and a transient state during an animation (ADR 0003 §6). `lo` or `hi` non-finite: `ValueError`. `max_ticks` not an `int` (or a `bool`): `TypeError`; negative: `ValueError` |
| L-2 | Only values inside the closed range are emitted (`Multiple` within `1e-9 × step` of an end, ADR 0003 §3), and only values the scale maps to a finite number: an out-of-domain candidate is dropped, never an error (F-410) |
| L-3 | No `np.arange` over a step and no accumulation (F-402): every value is computed from an integer index, `k * step` or `m * base ** k` |
| L-4 | `key(value)` depends on the value and the locator's configuration only, never on a range (F-401, D25); a non-finite value raises `ValueError` |
| L-5 | One call to `values` never returns two values with one key (F-413) |
| L-6 | `contains(value, lo, hi, scale, max_ticks)` is true exactly when `values(lo, hi, scale, max_ticks)` has a value with `value`'s key (ADR 0003 §2) |
| L-7 | A count above `MAX_GENERATED` raises `ValueError` naming the locator's parameter (a degenerate specification, F-409) *(default taken)* |

Each locator:

| ID | Row |
|---|---|
| L-10 | `MultipleLocator(step)`: `step` finite and `> 0`, else `ValueError` naming `step` (F-409). Values `k * step` for every integer `k` with `k * step` in range; `key` is `k`, the integer `round(value / step)`; `contains` needs `value` within `1e-9 × step` of `k * step` and inside the range. `Multiple(0.1)` over `[0, 1]` gives exactly `[k * 0.1 for k in range(11)]` (F-402). `max_ticks` is ignored |
| L-11 | `MaxNLocator(n, steps)`: matplotlib's `MaxNLocator` default steps (ADR 0003 §3). For the range's span it picks the smallest step `s = m * 10 ** e` (`m` in `steps`, `e` an integer) for which the multiples `k * s` inside the range number at most `min(n, max_ticks)` (`n=None` is `max_ticks`), and emits them, each `k * s`. `n < 1` or a step outside `[1, 10]`, an unsorted or empty `steps`: `ValueError`. `max_ticks == 0` emits nothing |
| L-12 | `LogLocator(base, subs)`: values `m * base ** k` for integer `k` and `m` in `subs`, inside the range and the scale's domain; `key` is `(k, i)` with `i` the index of `m` in `subs`, found from the value by `k = floor(log_base(value))` (with a `1e-9` guard at the decade edge). When there are more than `max_ticks` values, every `d`-th decade is kept, `d` the smallest integer that brings the count within `max_ticks`, decades with `k % d == 0` *(default taken)*. A positive value off that grid keys as `("off", round_key(value))`, which no emitted value has. `base` not `> 1`, `subs` empty or outside `[1, base)` or unsorted: `ValueError`. A value `<= 0` has no key: `ValueError` |
| L-13 | `SymLogLocator(base, linthresh, subs)`: `0` when inside the range, and `±m * base ** k` for each `base ** k >= linthresh`, `m` in `subs`; keys `0` → `(0,)`, else `(sign, k, i)`, an off-grid value `("off", round_key(value))`. Thinning as L-12, symmetric. Parameter checks as `SymLogScale`'s *(default taken: matplotlib's `SymmetricalLogLocator` without its linear-region ticks)* |
| L-14 | `FixedLocator(entries)`: an entry is a value, `(value,)`, `(value, label)` — a major tick (ADR 0003 §8) — or `(value, label, level)` with `level` `"major"` or `"minor"` (F-404). A wrong arity, an unknown level, a non-finite value, a label that is neither `str` nor `None`: `ValueError` (`TypeError` for a wrong type). Two entries with one key raise `ValueError` naming both (F-405). `values` emits the **major** entries in range; `fixed.minor` is a `FixedLocator` of the minor entries; `fixed.label(value)` returns an entry's label or `None`; `fixed.entries` is a tuple of `Tick` |
| L-15 | `NullLocator`: no values; `contains` is always false |
| L-16 | `MinorCountLocator(major, n)`: `n` minor values evenly between each two consecutive major values of `major` on the same arguments, the majors themselves excluded, plus as many of the same spacing as fit beyond the first and last major inside the range (matplotlib's `AutoMinorLocator` with a fixed count). `n < 1`: `ValueError`. Fewer than two majors: no minors |
| L-17 | `FunctionLocator(function)`: wraps a plain callable `(lo, hi) -> Iterable[float]` (F-406). Its values are filtered by L-2 and put in axis order; two values with one key raise `ValueError` (F-413: a defect in that locator) |
| L-18 | `as_locator(obj)`: an object with `values`, `key` and `contains` is returned as is; any other callable is wrapped in `FunctionLocator`; anything else raises `TypeError` |

## T — ticks along an axis (`core/ticks.py`)

```python
Level = Literal["major", "minor"]


@dataclass(frozen=True)
class Tick:
    value: float
    level: Level
    key: Hashable
    label: str | None = None


def axis_ticks(
    major: Locator,
    minor: Locator | None,
    lo: float,
    hi: float,
    scale: Scale,
    max_ticks: int,
    *,
    explicit: FixedLocator | None = None,
    mode: Literal["add", "replace"] = "add",
) -> tuple[Tick, ...]: ...
```

| ID | Row |
|---|---|
| T-1 | Majors from `major.values`, minors from `minor.values` with every minor value that `major.contains` dropped (F-407) — a membership check, not label overlap |
| T-2 | The forward images under `scale` of each level's values are strictly monotonic in the direction the scale declares (`increasing`, read along the axis's order), else `ValueError` naming the locator (F-306) |
| T-3 | A key repeated inside one level's values raises `ValueError` naming the locator (F-413) |
| T-4 | `explicit` with `mode="replace"`: the result is the explicit entries inside the range, at their levels, with their labels |
| T-5 | `mode="add"` (F-405): an explicit entry the generated locator of its level `contains` replaces the generated tick with that locator's key — its value, label and level all survive, even where the two values differ in the last bit; any other explicit entry is added. An added entry's key is `("fixed", round_key(value))`, so it cannot equal a generated key *(default taken)* |
| T-6 | The result is ordered along the axis — ascending for an ordinary range, descending for a reversed one, never input order — majors and minors interleaved by value; a generated tick's `key` is its locator's key, its `label` `None` |
| T-7 | `mode` other than the two: `ValueError` |

## P — the tick pool's plan (F-920)

```python
SPARES = 8


@dataclass(frozen=True)
class Pool:
    keys: tuple[tuple[Level, Hashable], ...]
    spares: int


def plan_pool(
    ticks_at: Callable[[float], Sequence[Tick]],
    alphas: Iterable[float],
    spares: int = SPARES,
) -> Pool: ...
```

| ID | Row |
|---|---|
| P-1 | `plan_pool` calls `ticks_at(alpha)` for every alpha given, in order, and returns the union of the `(level, key)` pairs in order of first appearance, plus `spares` hidden leaves (D25). `spares < 0`: `ValueError`. The alphas — four times the animation's frame density, through its rate function and composition — are the Manim layer's to choose (task 11) |
| P-2 | A key seen at two alphas appears once; a key that leaves and returns keeps its first position |

## F — formatters (`core/formatters.py`)

```python
@dataclass(frozen=True)
class Labels:
    text: Sequence[str]
    text_mode: Sequence[bool] | None = None
    offset: str | None = None

@runtime_checkable
class Formatter(Protocol):
    def format_ticks(self, values: FloatArray) -> Labels: ...

def decimal_places(step: float) -> int: ...

class DecimalFormatter:     DecimalFormatter(num_decimal_places: int | None = None, *, group_with_commas: bool = True)
class FormatStrFormatter:   FormatStrFormatter(fmt: str)
class ScientificFormatter:  ScientificFormatter(decimals: int = 1)
class EngFormatter:         EngFormatter(unit: str = "", places: int | None = None)
class FixedFormatter:       FixedFormatter(labels: Mapping[float, str])
class NullFormatter:        NullFormatter()
class FuncFormatter:        FuncFormatter(function: Callable[[float], str])

def as_formatter(obj: object) -> Formatter: ...
```

| ID | Row |
|---|---|
| F-1 | `Labels`: `text` one string per tick in the values' order; `text_mode`, when given, one `bool` per tick (true: text mode, as Manim's `Tex`); `offset` the shared-exponent slot, `None` from every 0.1 formatter (F-503). A `text_mode` of another length raises `ValueError` |
| F-2 | Every formatter takes the whole tick list at once (F-501), returns one label per value, and an empty list gives empty labels. Order does not matter: a reversed list gives the reversed labels (F-209) |
| F-3 | `decimal_places(step)` — Manim's `NumberLine._decimal_places_from_step`, the characters after the point in `str(step)`, except that a step printed in scientific notation counts its exponent: `1e-05` gives 5, `2.5e-07` gives 8, `1e+20` gives 0 (ADR 0003 §7). Equal to Manim's rule for every step that `str` prints without an exponent |
| F-4 | `DecimalFormatter` is Manim's `DecimalNumber` text: `num_decimal_places` places, thousands grouped with commas by default (`group_with_commas=True`, Manim's), a minus sign as `-`, and no negative zero (`-0.04` with one place gives `0.0`). `None` places: the fewest places, at most 12, at which every value rounded by `round_key` prints exactly — `[0, 0.5, 1]` gives 1, `[0, 1, 2]` gives 0, `[0.25, 0.5]` gives 2 *(default taken; the axis passes Manim's `decimal_places(step)` explicitly, task 10)*. Math mode. Negative places: `ValueError` |
| F-5 | `FormatStrFormatter(fmt)`: printf style, `fmt % value` (gnuplot's `set format`, matplotlib's `FormatStrFormatter`); a format that fails on a float raises `ValueError` at construction. Math mode |
| F-6 | `ScientificFormatter(decimals)`: `m \times 10^{e}` with `1 <= abs(m) < 10` rounded to `decimals` places (a rounding that reaches 10 carries into `e`); a mantissa of exactly `±1` prints as `10^{e}` or `-10^{e}`; `0` prints `0`. Math mode. `decimals < 0`: `ValueError` |
| F-7 | `EngFormatter(unit, places)`: SI prefixes from `y` (1e-24) to `Y` (1e24) in steps of 1e3, matplotlib's `EngFormatter`: `1500` with `places=1` gives `1.5\,\mathrm{k}`, with `unit="Hz"` `1.5\,\mathrm{kHz}`, micro is `\mu` (`2\,\mu\mathrm{s}`); `places=None` prints the shortest exact form up to 12 significant digits; `0` gives `0` (and the unit). Math mode |
| F-8 | `FixedFormatter(labels)`: the label of each value by `round_key`, `""` for a value it does not have (matplotlib gives `""` too) *(default taken: by value, not by index, so labels stay on their ticks through an animated range)* |
| F-9 | `NullFormatter`: an empty string per value |
| F-10 | `FuncFormatter(function)` and `as_formatter(obj)`: an object with `format_ticks` is returned as is; any other callable is a per-value function `float -> str` (F-504, ADR 0003 §2), wrapped; anything else raises `TypeError`. A wrapped function returning a non-`str` raises `TypeError` |

## Y — the leaf lifecycle (`core/lifecycle.py`, F-919)

`transition(leaf, event) -> (leaf, actions)` is a pure function implementing ADR 0001 §4
and ADR 0003 §5; the Manim layer (tasks 09 and 11) reads Manim's call stack to build the
events and carries out the actions. Every cell of ADR 0001 §4's table is one row below.

```python
class State(Enum):   ATTACHED = "A"; TRANSIENT = "T"; REMOVED = "R"; SHAPED = "S"
class Writer(Enum):  FRAME = "frame"; OTHER = "other"; BARE = "bare"
class Ending(Enum):  ARTIST = "artist"; PLAIN = "plain"; START = "start"; ELSEWHERE = "elsewhere"

class Kind(Enum):
    REBUILD_IF_DIRTY; READ_BUFFER; READ_SHAPE; MARK_DIRTY; IGNORE; OWN_TRANSFORM
    KEEP_UNTIL_REBUILD; WRITE_BUFFER; TRANSFORM_SHAPE; TOGGLE_DIRECTION; REVERSE_BUFFER
    REVERSE_SHAPE; REATTACH; RETAKE_START; ADOPT; REBUILD; USE_SHAPE; FREEZE
    SHAPE_FROM_TARGET; SHAPE_FROM_BUFFER; CANCEL_TARGETS; PAUSE_UPDATERS; FOLLOW_FRAME
    COPIES_FOLLOW; REBIND; COPY_ATTACHED; COPY_REBUILT; COPY_REMOVED; COPY_SHAPED

@dataclass(frozen=True)
class Action:
    kind: Kind
    ref: Hashable | None = None        # the target, the other artist, or the system

@dataclass(frozen=True)
class Leaf:
    state: State = State.ATTACHED
    owners: tuple[Hashable, ...] = ()
    origin: State | None = None                       # the state before T
    target: tuple[Ending, Hashable] | None = None     # the latest target an owner ended on
    cancelled: bool = False                           # become() cancelled pending targets
    deferred: tuple[Event, ...] = ()                  # Refresh, DataChange, Rebind, in order

# Events, frozen dataclasses:
Read(); DataChange(); Write(writer: Writer); ReversePoints()
Begin(owner: Hashable, introducer: bool = False)
Finish(owner: Hashable, ending: Ending, target: Hashable | None = None, remover: bool = False)
Refresh(); Become(other: Hashable, artist: bool); Copy(); SuspendUpdating(); FrameMoved()
Rebind(system: Hashable)

def transition(leaf: Leaf, event: Event) -> tuple[Leaf, tuple[Action, ...]]: ...
```

| ID | Event | A | T | R | S |
|---|---|---|---|---|---|
| Y-1 | `Read` | `REBUILD_IF_DIRTY` | `READ_BUFFER` | `READ_BUFFER` | `READ_SHAPE` |
| Y-2 | `DataChange` | `MARK_DIRTY` | deferred, no action | `IGNORE` | `IGNORE` |
| Y-3 | `Write(FRAME)` | `IGNORE` | `WRITE_BUFFER` | `WRITE_BUFFER` | `IGNORE` |
| Y-4 | `Write(OTHER)` | `OWN_TRANSFORM` | `WRITE_BUFFER` | `WRITE_BUFFER` | `TRANSFORM_SHAPE` |
| Y-5 | `Write(BARE)` | `KEEP_UNTIL_REBUILD` | `WRITE_BUFFER` | `WRITE_BUFFER` | `KEEP_UNTIL_REBUILD` |
| Y-6 | `ReversePoints` | `TOGGLE_DIRECTION` | `WRITE_BUFFER` | `REVERSE_BUFFER` | `REVERSE_SHAPE` |
| Y-7 | `Begin(o)` | **T**, owners `(o,)`, origin A; no action | owners `+ (o,)`; no action | introducer: `REATTACH, RETAKE_START`, **T** with origin A; else **T** with origin R | introducer: `REATTACH, RETAKE_START`, **T** with origin A; else **T** with origin S |
| Y-8 | `Refresh` | `REBUILD` | deferred | `REATTACH` → **A** | `REATTACH` → **A** |
| Y-9 | `Become(x, artist=True)` | `ADOPT x` | `ADOPT x, CANCEL_TARGETS`; stays **T** with origin A, `cancelled`, `target` cleared; the owners keep the buffer | `ADOPT x` → **A** | `ADOPT x` → **A** |
| Y-10 | `Become(x, artist=False)` | `SHAPE_FROM_TARGET x` → **S** | `SHAPE_FROM_TARGET x`; stays **T** with origin S | `SHAPE_FROM_TARGET x` → **S** | `SHAPE_FROM_TARGET x` |
| Y-11 | `Copy` (the original is unchanged) | `COPY_ATTACHED` | `COPY_REBUILT` | `COPY_REMOVED` | `COPY_SHAPED` |
| Y-12 | `SuspendUpdating` (no animation on the stack) | `PAUSE_UPDATERS` | none | none | none |
| Y-13 | `FrameMoved` | `FOLLOW_FRAME` | `COPIES_FOLLOW` | none | `FOLLOW_FRAME` |
| Y-14 | `Rebind(s)` (`ReplacementTransform(ax, s)` finished) | `REBIND s` | deferred | none | `REBIND s` |

`Finish(o, ending, target, remover)`, only in **T**:

| ID | Row |
|---|---|
| Y-20 | Outside **T**, or `o` not an owner: `ValueError`. `Begin` with an `o` already an owner: `ValueError` |
| Y-21 | Others remain: `o` is dropped; if it ended on a target (`ARTIST` or `PLAIN`), `target` becomes `(ending, target)` — the latest wins (ADR 0001 §4 notes); no action |
| Y-22 | The last owner: the effective target is this finish's when it ended on one, else the recorded `target`. Then the first rule that matches (ADR 0003 §5): (1) `remover`: `FREEZE` → **R**; (2) `cancelled`: the target is ignored and the rules go on; (3) an `ARTIST` target: `ADOPT target` → **A**; (4) a `PLAIN` target: `SHAPE_FROM_TARGET target` → **S**; (5) `ending is START`: back to the origin state — `REBUILD` for A, `USE_SHAPE` for S, `FREEZE` for R; (6) otherwise: `SHAPE_FROM_BUFFER` → **S** |
| Y-23 | Then every deferred event applies in the order it was made, through `transition` from the new state, its actions appended; the leaf leaves **T** with no owners, no origin, no target, `cancelled` false and nothing deferred |
| Y-24 | An event of an unknown type: `TypeError` |

Overlap cases tested beside the cells (ADR 0003 *Consequences*): a remover that ended on an
artist target goes to **R**; `become(artist)` during **T** cancels a target an owner ended
on later; two owners ending on two targets, the last to finish wins; an earlier owner's
target is adopted when the last owner ended elsewhere; deferred `Refresh` and `DataChange`
apply in order after each kind of finish; a remover with a deferred `Refresh` ends
attached; `Create` after `Uncreate` (F-907): `Begin(introducer)` on **R** re-attaches and
re-takes the start.

## Tests

| File | Rows |
|---|---|
| `tests/core/test_ticks.py` | K-1, L-1 … L-18, T-1 … T-7; Hypothesis: keys stable across ranges and unique, `contains` agreeing with `values` |
| `tests/core/test_pool.py` | P-1, P-2 |
| `tests/core/test_formatters.py` | F-1 … F-10; F-3 against Manim's own `NumberLine._decimal_places_from_step` |
| `tests/core/test_lifecycle.py` | Y-1 … Y-24 and the overlap cases |
