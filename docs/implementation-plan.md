# Implementation plan — Stage 2

**Status: Living.** Started 2026-10-29. Turns the Stage 2 task list of `TODO.md` into work
two agents can do in parallel without reading each other's code. It decides nothing that
the frozen documents decide: where it seems to, the ADRs and `docs/scope.md` win, in the
order `docs/README.md` gives.

## Who does what

| Role | Owns | Never touches |
|---|---|---|
| **Codex** — implementation | `src/manim_plots/` | `tests/`, `docs/`, `pyproject.toml`, `uv.lock` |
| **Claude** — tests, plan, review | `tests/`, `docs/acceptance/`, this plan, tooling (`pyproject.toml`, `tools/`), the merge | `src/manim_plots/`, except a one-line fix the gate needs at merge time |
| **Maintainer** | the vetoes on *(default taken)* rows; the visual review | — |

The two sides meet in one place: the task's **acceptance table** in `docs/acceptance/`,
written before either side starts. It gives the public and the internal signatures the
tests import, the behaviour row by row, the errors with their types, and the test list.
Tests are written from the table and never from the implementation: a black box. That is
ADR 0001's oracle rule, *no expected value computed by the code under test*, applied to
the process as well.

## The loop, per task

1. **Branch** `task/NN-short-title` off `dev`.
2. **Acceptance table** — Claude writes `docs/acceptance/NN-short-title.md` and commits
   it. Every under-specified choice is settled there by D17 (*as close to Manim as
   possible*, then matplotlib) and marked *(default taken)* for the maintainer's veto.
   A choice that would change a frozen meaning stops the task instead (ADR 0003 §9).
3. **In parallel:**
   - Codex implements `src/` from the table, with the proofs of concept under `poc/` as
     the reference for mechanism (PoC 4 is the latest). It may run `ruff`, `mypy` and any
     scratch check it wants, but writes no test file.
   - Claude writes the tests the table lists.
4. **Commit** the implementation (`feat:`) and the tests (`test:`) separately.
5. **Codex runs the tests** and corrects `src/` until they pass, on Manim 0.21.0
   (`.venv`) and 0.22.0 (`.venv-0.22`). It does not edit a test. A test it believes wrong
   is reported, with the table row it contradicts, in its final message; Claude decides,
   and fixes the test or sends the code back.
6. **Gate** — Claude runs `uv run python tools/check.py` (four cells, render tests
   included) and reads the implementation diff against the table. Visual baselines that
   did not exist are written with `--update-baselines` by Claude only, never by Codex: they
   are candidates until the maintainer has looked at them (ADR 0002 §1).
7. **Merge** `--no-ff` into `dev`; tick the task in `TODO.md`. No push.

A task that cannot pass the gate is not merged: its branch stays, and the blocker is
written at the top of its acceptance table.

## Rules both sides follow

- **Layers** (ADR 0001 §1): nothing under `core/` imports `manim` or `manim_plots.mobjects`;
  only `mobjects/context.py` touches `sys._getframe`, `inspect.currentframe`, `f_code`,
  `f_locals` or `f_back`. A static test parses the source (`tests/test_layers.py`), and
  ruff's TID251 bans `manim` imports from `core/` as well.
- **Errors** (ADR 0003 §3): a malformed value raises `ValueError`, a wrong type `TypeError`;
  the message names the parameter, and for an array the first invalid index. A warning at
  use is `manim_plots.ManimPlotsWarning`, deduplicated by the library; the test suite turns
  it into an error.
- **Arrays**: `FloatArray`, `BoolArray`, `IntArray` from `manim_plots.core`. An array
  stored in a payload, in `Bounds` or in a frozen value object is a view with
  `writeable=False`.
- **Tolerances** are the named constants of ADR 0003 §3. Tests use the ADR's numbers, not
  the constants, so a constant that drifts fails.
- **Manim internals**: never patched. The PoCs read them through `context.py`; production
  does the same, with the pin inventory of F-917.
- **Logging**: `logging.getLogger(__name__)`, `DEBUG` only, %-style (ADR 0002 §4).
- **Docstrings**: numpy convention, every public name; ruff `D` is on for `src/`.
- **Sandbox hygiene**: no `tempfile.mkdtemp`, `TemporaryDirectory` or pytest's `tmp_path`
  (the sandbox gives the directories an ACL nobody else can open); run pytest with
  `-p no:cacheprovider`, mypy with `--cache-dir=nul`, ruff with `--no-cache`. The
  Hypothesis profile keeps no database.

## Visual review

Every render test that draws a library picture has a twin drawing the same scene in plain
Manim, with the same name and the suffix `__manim`, so each picture is reviewed next to
what Manim draws. `uv run python tools/gallery.py` collects the baselines, the twins, and
any `actual`/`diff` pair a failing run left in `tests/visual/_out/`, into
`tests/visual/_out/gallery.html`, one row per scene with the test's docstring as caption.
A baseline written during the night is marked *candidate* in the gallery until the
maintainer has reviewed it.

## Tasks

Each task lists its modules, what its acceptance table has to settle, and its tests. The
`F-*` lists are `TODO.md`'s.

### 06 — core contracts

**Modules.** `core/__init__.py` (array aliases, `ManimPlotsWarning`), `core/payload.py`,
`core/scales.py`, `core/nodes.py`; `mobjects/context.py` with the pin inventory only (the
stack readers arrive in 09); `manim_plots/__init__.py` with the 0.1 `__all__`.

**Settles.** The `Payload` constructor and its validation, row by row from the invalid-input
table; the segment helpers `Map` uses to rebuild a path after masking; the four scales and
`FunctionScale`'s falsification (F-305); `limit_range` at open and closed bounds; the
internal `Node` signature, affine collapse and the compiled chain with `Map`'s validity
rule; the frame map — affine solve, bilinear weights, inverse, the singular and off-plane
refusals; the pin inventory's format and the import-time version check; public names.

**Tests.** `tests/core/test_payload.py` (one test per invalid-input row, read-only arrays,
the segment helpers), `test_scales.py` (round trip and monotonicity by Hypothesis with fixed
anchors; symlog against matplotlib's formulas written out in the test; `limit_range`;
falsification failures by name), `test_nodes.py` (affine collapse, the two-node validity
case of ADR 0003 §1, frame round trip on random affine frames, singular and near-singular
frames, off-plane points, bilinear inversion and its refusal), `tests/test_layers.py`,
`tests/mobjects/test_manim_contract.py` (both pin sets, `Scene.get_moving_mobjects` with
both queries, the unpinned-version warning), `tests/test_public_api.py` (`__all__` against
Manim's namespace).

**Tooling first (Claude).** SciPy declared; TID251; the Hypothesis profile; the
`ManimPlotsWarning` error filter; `.venv-0.22` for Codex.

### 07 — sources, shape, parameters

**Modules.** `core/sources.py`, `core/shape.py`, `core/params.py`.

**Settles.** `Bounds` as a concrete class; the analytic source — Manim's `plot` keywords
(`x_range` with a step capping the spacing, `use_vectorized`, `discontinuities`, `dt`), the
adaptive sampler and its 0.5 px chord test through `to_screen`, sampling against bounds; the
array source — the two input shapes, bracketing samples kept, linear `at`, the non-monotone
refusal; the parametric source; `resample_like`; the `Shape` stages in ADR 0003 §1's order —
pole and sign-change split, smoothing, clipping on the final geometry, dash by arc length
with a phase restart per piece, densify for a non-affine frame; parameters as descriptors
with version counters, foreign snapshots compared NaN-aware, a callable binding dirty once
per token.

**Tests.** `tests/core/test_sources.py`, `test_shape.py` (a segment from outside to outside
across the viewport, a single point, a pole gap, `1/x`, dash phase per piece, a stage never
mutating its input), `test_params.py`; `tests/benchmark/test_core_pipeline.py` — four
artists of 2 000 samples through the core pipeline on both frame paths, the first reading
of the 4 ms margin.

### 08 — ticks, formatters, lifecycle

**Modules.** `core/ticks.py`, `core/formatters.py`, `core/lifecycle.py`.

**Settles.** The constructors and edge cases of the seven locators (MaxN, Multiple, Log
with subdivisions, SymLog, Fixed, Null, minor count) and of the callable wrapper; merge by
key (replace or add, order along the axis, collisions); minor-on-major removal; the
ordering assertion (F-306); out-of-domain filtering; the pool's plan; the formatters
(decimal with ADR 0003's decimal-places rule, format string, LaTeX/scientific, SI, fixed,
null) and the callable wrapper; the lifecycle's states, events, actions and precedence as a
pure reducer.

**Tests.** `tests/core/test_ticks.py` (keys stable across ranges and unique, by Hypothesis;
`Multiple(0.1)` exact; merge order on a reversed range; `contains` with `max_ticks`),
`test_formatters.py`, `test_pool.py`, `test_lifecycle.py` (every cell of ADR 0001 §4 and the
precedence cases of ADR 0003 §5).

### 09 — leaves, context, frame

**Modules.** `mobjects/leaves.py`, `mobjects/context.py` (stack readers), and enough of
`system.py`, `axis.py` and `artists.py` for two axis lines, ticks without labels and one
analytic artist.

**Settles.** The leaf base class and the `points` property; the hidden frame leaf; which
writes the getter and the setter see; the stack readers and what they return; the
synchronisation updater and its reporting through `.updaters` on both versions; copy.

**Tests.** `tests/mobjects/test_leaves.py` (leaf types, getter identity), `test_context.py`
(each Manim operation attributed as F-904 says), `test_copy.py`; render tests: F-914 (the
scene with and without the frame are pixel-identical), F-915 (middle frames on both
versions and in both insertion orders); the first visual pair — `mp.Axes` with
`plot(np.sin)` and its `__manim` twin; `tests/benchmark/test_f1001.py`, an end-to-end spike
without labels.

### 10 — axis decoration

**Modules.** `mobjects/axis.py`, `mobjects/system.py`.

**Settles.** Manim's `Axes` signature and every `axis_config` key of the defaults table;
the parts in `NumberLine`'s vocabulary (`ticks`, `minor_ticks`, `numbers`, `labels`,
`line`, `grid`, `at`); tick direction, axis position and crossing, mirrored axis, grid per
level, tips; numbers from the glyph cache; overlap (drop, rotate, hide); axis titles and
`get_axis_labels`; `mp.NumberPlane`.

**Tests.** `tests/mobjects/test_axis.py`, `test_defaults.py` (every row of both defaults
tables against Manim's own `Axes` and `NumberPlane`, style attributes included, under a
changed `tempconfig` too), `test_number_plane.py`; visual pairs for axes, labels, log axes,
the plane; F-1001 with labels from a warm glyph cache.

### 11 — artists and `.animate`

**Modules.** `mobjects/artists.py`, `mobjects/system.py`, `mobjects/leaves.py`.

**Settles.** The four artists and `plot`'s overloads; registration, `ax.add`, `ax.remove`,
single ownership; the own transform; the lifecycle applied to leaves; keyed alignment and
the tick pool; `Transform` between systems; `ReplacementTransform`; `i2gp`; the Manim-named
helpers of the parity survey's 0.1 rows.

**Tests.** `tests/mobjects/test_artists.py`, `test_registration.py`, `test_data_channel.py`,
and the F-906 matrix — end states and sampled intermediate frames against plain Manim run
live; F-922 with caching on; visual pairs for each artist and for an animated range.

### 12 — legend, style, animations

**Modules.** `mobjects/legend.py`, `mobjects/animations.py`, `mobjects/artists.py`.

**Settles.** Legend placement and merging; the colour cycle; marker and line-style enums;
dash units; `DrawAxes`, `TraceCurve`, `ShowPoints`, `Morph`.

**Tests.** `tests/mobjects/test_legend.py`, `test_style.py`, `test_animations.py`
(`TraceCurve` in data order, `Morph`'s pairs and refusals); visual pairs.

### 13 — hardening

F-1001 on both frame paths and the 1.5× check against `tests/benchmark/test_plain_manim.py`;
F-1002 (`mypy --strict` on the public surface, the annotations against the implementation);
F-1006 — the invalid-input table on every surface it lists; the full gate.

### 14 — documentation and release

Sphinx with numpydoc, F-1008's differences where users meet them, a changelog, packaging.
The merge of `dev` into `main` and its tag are the maintainer's.
