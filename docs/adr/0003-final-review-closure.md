# ADR 0003 — Closing the final review

- **Status:** Frozen, 2026-10-29; a change needs a new ADR. Accepted with the
  maintainer's answers in the review session of 2026-10-28/29; items marked
  *(default taken)* were not asked and stand unless the maintainer vetoes them.
- **Task:** `task/05-final-review` in `TODO.md`.
- **Builds on:** `docs/reviews/2026-10-28-final-codex.md` and
  `docs/reviews/2026-10-28-final-claude.md`; every finding of both is dispositioned in
  `docs/reviews/2026-10-29-final-triage.md`.
- **Supersedes:** the rows and sections of `docs/scope.md` and ADR 0001 named below. They
  are amended in place and marked *(ADR 0003)*, so each frozen document reads as current.

## Context

Two independent reviews of commit `f129014` found the architecture sound and the scope
not yet implementable: six blockers once merged, each a contradiction or a gap in a frozen
document, and some twenty major findings of the same kind. This record closes every one
that changes a frozen document. Findings in living documents and in the test
infrastructure were fixed directly; the triage table says where.

## Decision

### 1. Payload, `Map` and the pipeline

- **`Map` owns validity** (blocker; Codex C1). Each node combines the incoming `valid`
  mask with its own domain and finite-output mask and rebuilds path segments, as ADR 0001
  §3 and D26 say. `docs/scope.md`'s rule that `Map` carries the other fields untouched is
  amended. Test: a two-node chain whose second node invalidates a sample the first found
  valid.
- **`Payload` and `Shape` are typed here** (Codex D1, Claude E3), completing ADR 0001 §3:

  ```python
  @dataclass(frozen=True)
  class Payload:
      kind: Literal["path", "points", "region"]
      coords: FloatArray  # (n, d)
      segments: IntArray  # (s, 2), half-open [start, stop); (0, 2) when empty
      topology: IntArray | tuple[int, int] | None = None  # region only
      valid: BoolArray | None = None  # (n,); None only when every sample is valid


  Shape = Callable[[Payload, Bounds], Payload]
  ```

  Arrays in a payload and in `Bounds` are views with `writeable=False`; a stage that
  changes one builds a new array. The invariants stay those of `docs/scope.md`, *The
  Source payload*. `Node` stays internal (ADR 0001, question 1) and gets its signature in
  task 06's code.
- **Later fields are optional** (Claude C3). Field values for contours and vector fields
  arrive in 0.2 as optional payload fields with defaults, which breaks no 0.1 consumer.
  The paper check's sentence that they must ship in 0.1 is amended to ADR 0001's position.
- **The pipeline's order is fixed** (Codex D2): an array source keeps the samples that
  bracket the range, so a segment crossing the viewport survives; `Map` (own transform,
  then frame) marks validity and splits; `Shape` smooths; clipping to the viewport works
  on the final geometry, so smoothing cannot leave the viewport; dashes restart their
  phase on each path piece. Tests: a segment from outside to outside across the viewport,
  a single point, a pole gap.

### 2. Protocols

- **Read-only members** (Codex E3, Claude E2). `Scale.domain`, `closed` and `increasing`,
  `CompiledMap.is_affine`, and `Bounds.lower` and `upper` are read-only `@property`
  members. A scale may then be a `@dataclass(frozen=True)`, and a source cannot change
  the map it is handed.
- **`Locator.contains` gets the density** (blocker; Codex E1):
  `contains(value, lo, hi, scale, max_ticks)`, the arguments of `values`, so a
  density-aware locator answers membership consistently.
- **`Formatter` has a named method** (blocker; Claude 1):
  `format_ticks(values) -> Labels`, matplotlib's name. Anything callable without it is a
  per-value function and is wrapped (F-504 unchanged).
- **`Scale.limit_range(lo, hi, minpos)`** (Claude E4), matplotlib's
  `limit_range_for_scale`, so 0.2's autoscale needs no breaking change. F-311's `eps` is
  `minpos`; an unknown `minpos` is `1e-300`. A range wholly outside the domain collapses
  and raises (F-409).

### 3. Core numerics

- **SymLog** is matplotlib's: `SymLog(base=10, linthresh=1, linscale=1)` (blocker;
  Claude 4). A `SymLog` locator ships with it (F-403), as matplotlib's
  `SymmetricalLogLocator` *(default taken)*.
- **MaxN** steps are 1, 2, 2.5, 5 and 10 times a power of ten, matplotlib's
  `MaxNLocator` default; it emits at most `min(n, max_ticks)` ticks, and `n` defaults to
  `max_ticks`.
- **Keys** of `MaxN` and of wrapped callables round the value to 12 significant digits.
- **Tolerances** are named constants of the core, not public API:

  | Where | Tolerance |
  |---|---|
  | `p2c(c2p(x)) == x` (F-201, F-207) | 1e-9 × the range span |
  | `scale.inverse(scale.forward(x)) == x` (F-305) | 1e-9 relative |
  | F-305's falsification | 64 samples, log-spaced over `[1e-6, 1e6]` on an infinite domain, plus each closed bound |
  | the frame is affine (F-914) | residual ≤ 1e-9 × the frame's size |
  | adaptive sampling (F-704, F-108) | chord deviation ≤ 0.5 px at 1080p, 1 px = 8/1080 scene units |
  | `Multiple`'s range ends (F-402) | `k * step` inside `[lo, hi]` within 1e-9 × step; the values themselves are exact |

- **Errors and warnings** (blocker; Claude 4, D2). A malformed value raises `ValueError`
  and a wrong type `TypeError`; the message names the parameter and, for an array, the
  first invalid index. User-facing warnings go through `warnings.warn` with the category
  `ManimPlotsWarning(UserWarning)`; the library itself deduplicates them (F-705: once
  per artist per data change), and the test suite turns the category into errors, which
  is how "tests raise" in F-920 works.

### 4. Bindings

- **A callable binding is dirty once per frame** (blocker; Claude 3): once per token of
  the synchronisation updater, not on every read of `points`, which PoC 3 rejected. F-918's
  list of per-frame cases gains "a parameter bound to a callable", and F-915's "live
  function" means exactly F-918's cases. F-110 is amended.
- **`ax.plot(f, **kwargs)`** (Claude D4): the parameters of `f` are the names in
  `inspect.signature(f)` after the first; every other keyword is style, as in Manim. A
  parameter whose name is also a `VMobject` style keyword, such as `color`, raises at
  `plot`.

### 5. Lifecycle (ADR 0001 §4)

- **Finishing has a precedence** (blocker; Codex E2, Claude 2a). When the last owner
  finishes, the first matching rule applies:
  1. the owner was a remover: **R**. A remover never adopts its target, so `FadeOut`
     leaves no artist at opacity 0;
  2. the pending target was cancelled by `become`: the target is ignored, go on;
  3. it ended on an artist target: **A**, adopting it;
  4. it ended on a plain target: **S**, with the target's shape;
  5. it ended on its start: back to the origin state, rebuilt;
  6. otherwise (`Homotopy`): **S**, with the final shape.

  Deferred actions — `refresh()`, data changes — then apply in the order they were made.
- **An introducer re-takes its start** (blocker; Claude 2b). `Animation.begin` copies
  `starting_mobject` before it suspends, so `Create` after `Uncreate` would draw from the
  degenerate copy. Re-attaching at an introducer's begin rebuilds the artist and then
  re-takes `starting_mobject`, and `outline` for `Write` and `DrawBorderThenFill`. Both
  attributes join F-917's inventory of assigned animation attributes.
- **F-915 on 0.22.0** (Claude E6). `Scene.get_moving_mobjects` asks
  `get_family_updaters()` on 0.21.0 and reads `.updaters` recursively on 0.22.0. The
  frame joins F-917's inventory with both queries, and the library reports its
  synchronisation updater through `.updaters`, which both read *(default taken)*.
  ADR 0001's claim that every frame the mechanism reads is byte-identical holds for PoC
  4's seventeen, not for this one; it is corrected.

### 6. Mapping

- **F-203: the axes cross where Manim puts them** (Claude C2). By default an axis whose
  range excludes 0 sits at the range edge, as in Manim and the defaults table; where the
  axes cross is a parameter. Defect 13 is "kept by default, fixable by a parameter".
- **The aspect lock says what yields** (Claude D6). `adjustable="length"` (the default)
  keeps the ranges and adapts the length the user did not give; `adjustable="range"`
  keeps the lengths and widens a range. Both lengths, a lock and `adjustable="length"`
  together raise. matplotlib's `adjustable`, in Manim's vocabulary of lengths and ranges.
- **A singular frame refuses atomically** (Codex E4). An operation that needs an inverse
  the frame does not have — an artist's own transform or an adoption into **S** after
  `ax.scale(0)` — raises `ValueError` naming the system and changes nothing. Listed in
  F-1008; tested on a singular and a near-singular frame.
- **An empty range is transient during an animation** (Claude D5). Flipping (0, 10) to
  (10, 0) passes through `lo == hi`: that frame has no ticks, artists collapse as Manim's
  do at scale 0, and `p2c` raises. F-409 raises only when such a range is set outside an
  animation.
- **`unit_size`** in `axis_config` without a length wins over the default length, and the
  length follows; with an explicit length it raises (F-204, defect 5) *(default taken)*.

### 7. Closeness to Manim (D17)

- **Ticks stay at integer multiples of the step** (both F1). Manim anchors them at 0 when
  the range contains 0 and at `x_min` otherwise; following it would change every key as
  an animated range stops containing 0, which breaks F-413. The defaults table's Manim
  column is corrected and the difference is listed in F-1008.
- **F-1008 gains five differences** (Claude F4, Codex F2, E4): the hidden frame takes one
  lag slot, so the visible leaves of `Create(ax)` finish at 24/25 of the run for a default
  `Axes`; an adaptively sampled curve's partial drawing (`Create`, `Uncreate`, `Write`,
  `ShowPassingFlash`) is paced by sample, not by `x`; `Transform` pairs ticks by key,
  where Manim pairs family members by index; `ax.add` registers, where Manim parents;
  and a singular frame refuses where Manim degenerates. Also listed: an unknown
  `axis_config` key raises.
- **Intermediate frames are compared with plain Manim** (Codex F2). F-906 compares end
  states; it now also samples intermediate frames of `Create`, `Write`, `Uncreate`,
  `FadeIn`, `Transform` and `Indicate` on artists and on axes against plain Manim run
  live, outside the differences F-1008 lists.
- **`mp.NumberPlane` follows Manim's `NumberPlane`** (Codex F3): ranges from the frame
  radius, lengths from a unit size of 1, no ticks, no tips, stroke width 2, numbers at
  font size 24 with label direction `DR`, background lines `BLUE_D` at width 2, and
  faded lines (`faded_line_ratio=1`), with its own rows in the defaults table and its own
  parity test. That it is a `CartesianAxes` inside stays an implementation detail.
- **The defaults table gains rows** *(default taken)*: the midpoint of each range sits at
  the scene origin; axis stroke width 2.0; tip 0.35 × 0.35; `line_to_number_buff` 0.25;
  the y axis rotated by 90°. The parity test compares style attributes as well as
  geometry.
- **Decimal places** follow Manim's rule, the characters after the point in `str(step)`,
  except that a step printed in scientific notation counts its exponent, so `1e-05` gives
  5 places where Manim gives 0 *(default taken)*.
- **`p2n` and `point_to_number`** take arrays, as 0.22.0's signature does
  *(default taken)*.
- **Misspelt attributes raise** (Claude B1). Manim types `Mobject.__getattr__` as
  returning `MethodType` and turns an unknown `set_*` into a silent write. The library's
  mobjects raise `AttributeError` for an unknown name, dropping Manim's deprecated
  `get_`/`set_` shim on library types, and the test suite turns that shim's
  `DeprecationWarning` into an error.

### 8. API

- **`Transform` between differently configured systems cross-fades** (Claude D3). When
  the locator configurations differ, the frame interpolates, ticks without a matching key
  fade out and in as the pool's births and deaths do, and the rest align by key. A change
  of scale type, such as linear to log, raises `ValueError` naming `FadeTransform`.
- **`ax.remove(artist)` unregisters** (Claude D7), the counterpart of `ax.add`; the
  artist may then be bound to another system. "Detached" names the states **R** and **S**
  only.
- **`set_ticks`**: a `(value, label)` pair places a major tick *(default taken)*.
- **`__all__`** star-exports only names Manim lacks, D12's rule; Manim-named classes are
  reached as `mp.Axes`, `mp.NumberPlane`. Task 06 fixes the list *(default taken)*.
- **F-912** drops "the data-channel animation as a public class": the native `.animate`
  of D21 is the data channel *(default taken)*.

### 9. Process and editorial

- **Precedence.** Where an ADR and `docs/scope.md` disagree, the ADR wins on contracts and
  mechanism and the scope on what is required (`docs/README.md`).
- **The rest of the under-specification** both reviews tabulated — constructors and edge
  cases of the built-in locators, formatters and sources, dash units, the label-space
  formula, legend placement — is settled by an acceptance table at the start of the task
  that owns it, reviewed before its code. A choice there that changes a frozen meaning
  needs an ADR.
- **Editorial corrections** in the frozen texts: "the four" surfaces of the invalid-input
  rule are five; the scope's source legend gains the tags it uses (stress case *n*, PLAN,
  round *n*, task/*nn*); F-112 cites D11.
- **Test oracles named** *(default taken)*: F-914's pixel test compares the scene
  captured with and without the frame; F-922 renders once with caching on.

## Consequences

- ADR 0001 §3 gains `Payload`, `Shape`, read-only members, `contains(..., max_ticks)`,
  `format_ticks` and `limit_range(..., minpos)`. These are public contract changes before
  any code exists, so nothing breaks.
- The lifecycle reducer of task 08 implements a precedence, not only a table, and its
  unit tests cover the overlapping cases as well as every cell.
- F-906's matrix grows by the intermediate-frame comparisons; the render gate of ADR 0002
  §3 runs them on every merge.
- The requirement count stays 121, with 108 at tier 0.1: every decision here amends an
  existing row.
