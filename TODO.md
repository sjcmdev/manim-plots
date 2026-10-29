# TODO

Project plan and task tracker. Each task gets one branch; each branch is merged into
`dev`. Nothing is merged into `main` except a finished stage.

## Branch policy

```
main          release-ready only; one merge per finished stage
 └── dev      integration branch; every task lands here
      └── task/01-short-title
      └── task/02-short-title
```

- Every task branches off `dev` and merges back into `dev`. Branch name:
  `task/xx-short-title`, where `xx` is the task number below.
- `dev` merges into `main` only when a stage is complete and ships a coherent package
  of functionality. That merge is tagged.
- All four checks (`ruff check`, `ruff format --check`, `mypy`, `pytest`) pass across
  the supported matrix before a task branch merges: `uv run python tools/check.py`.
- Exceptions to the branch rule: a one-line typo fix in a document may go straight to
  `dev`.
- Commits follow Conventional Commits, as described in `CONTRIBUTING.md`.

## Stage 0 — foundations

Infrastructure and knowledge needed before any design decision is made.

### task/01-revalidate-defects

Re-run the ManimCE defect audit against 0.21.0. The original audit ran against
0.19.2; every finding below is unconfirmed on the version we actually target.
Each confirmed defect becomes a requirement in task 03; each defect that no longer
reproduces is dropped with a note.

- [x] Float accumulation in `NumberLine` tick generation via `np.arange`
- [x] `include_tip` alters tick range and coordinate mapping inconsistently
- [x] Plot curves escape the axes viewport; no clipping for asymptotic functions
- [x] Axes aspect ratio distortion from independent length parameterisation
- [x] `unit_size` ignored when passed through `axis_config`
- [x] Mutating `x_range` after construction leaves ticks stale
- [x] No legend primitive; users assemble legends by hand
- [x] `LogBase.inverse_function` ndarray guard broken; negatives become NaN silently
- [x] `LogBase` has no minor ticks between decades
- [x] `LogBase` naming: `function()` is exponential, not logarithmic
- [x] Label overlap: no de-confliction at high label density
- [x] Ticks centred on the axis line; cannot be directed outward only
- [x] `_origin_shift` clamps to the range minimum when the range excludes zero
- [x] Geometric ops on `NumberLine` (inherits `Line`) corrupt coordinate mapping
      — no longer reproduces on 0.21.0; dropped with a note
- [x] Sweep the audit notes for any finding not listed above — six new findings, 15a-15f
- [x] Write up the result as `docs/defect-audit-0.21.md`

### task/02-testing-infrastructure

- [x] Register the `render` marker in `pyproject.toml` (`--strict-markers` is already
      on, so the first marked test fails without it)
- [x] Exclude render tests from the default run; keep them runnable explicitly
      — `pytest -m render` overrides the default `-m 'not render'`
- [x] Run the four checks across the matrix — locally, not in hosted CI:
      `tools/check.py`. A GitHub Actions workflow ran green once and was dropped in
      favour of a local gate
- [x] Decide the matrix: Python versions and Manim versions — Python 3.12 and 3.13
      against Manim 0.21.0 and 0.22.0; the pin is `manim>=0.21,<0.23`
- [x] Branch protection on `main` and `dev` — dropped with hosted CI: there is no
      status for it to require

## Stage 1 — scope

### task/03-functional-scope

Requirements come before architecture. No module layout is decided until this task
closes.

- [x] Turn each confirmed defect from task 01 into a functional requirement
      — the traceability table in `docs/scope.md` traces all 20 audit rows, the dropped
        14 included, to `F-*`
- [x] Collect the requirements list from collaborators — answered inline in
      `docs/api-sketch.md` and placed in D9; traced to `F-*` in `docs/scope.md`
- [x] Parity survey: what matplotlib, gnuplot and OriginPro offer that Manim does not
      — `docs/parity-survey.md`, three sections, Manim guarded by a drift test
- [x] Split into must-have for 0.1, later, and explicit non-goals
- [x] Write up as `docs/scope.md`
- [x] Paper-check the 0.1 contracts against date/time axes, the calculus toolkit and
      region sampling — the third one forced `F-114`

### task/04-architecture

- [x] Public contracts: scale, locator, formatter — the extension points third
      parties implement against — `typing.Protocol`s, ADR 0001 section 3
- [x] Separation between the data model and the Manim geometry it produces
      — a `core/` free of Manim (NumPy, SciPy, the standard library) and a `mobjects/`
        layer, ADR 0001 sections 1-2
- [x] How a coordinate system survives Manim's geometric transformations
      — a hidden frame and a leaf lifecycle, ADR 0001 section 4 and D17-D21
- [x] Record as `docs/adr/0001-architecture.md` — accepted with the maintainer's
      answers to its five questions
- [x] Proof of concept for the load-bearing hypotheses: the `points` property on a
      leaf, the transient-mode test under the eight restoring animations, leaf copy,
      rebuild cost against F-1001, and `MathTex` labels as library leaves — report in
      `docs/poc/poc1-points-property.md`. It falsified the shadow test, so a second one
      checks the replacement — a hidden frame grid, an animation lifecycle on the
      leaves, target adoption — report in `docs/poc/poc2-frame-lifecycle.md`. A third
      reads the missing operation context from the call stack — report in
      `docs/poc/poc3-stack-context.md`. A fourth makes the data channel native under
      `.animate` through keyed family alignment — report in
      `docs/poc/poc4-keyed-alignment.md`. The code is in `poc/poc1/` to `poc/poc4/`.
      `docs/plan.md`, scope and ADR 0001 reflect all four (D17-D21)
- [x] Architecture review with the arch-crew skills —
      `docs/reviews/2026-10-24-arch-crew.md`
- [x] Two independent freeze reviews from one brief — `docs/reviews/2026-10-24-codex.md`,
      `docs/reviews/2026-10-24-claude.md`; their blockers closed by D22-D27
- [x] Freeze the 0.1 scope and the architecture — ADR 0001 and `docs/scope.md`, status
      *Frozen*

### task/05-final-review

One last review of the whole project before any library code, so implementation starts
from a repository with nothing ambiguous in it.

- [x] Relayout: the four proofs of concept under `poc/`, their reports under
      `docs/poc/`, every review under `docs/reviews/`, the plan as `docs/plan.md`, a
      document index in `docs/README.md`, a `LICENSE` file; internal prompts kept out of
      the repository
- [x] Finish the test infrastructure: visual baselines with `--update-baselines`, a
      frame-cost benchmark harness, render tests in the merge gate (`tools/check.py`),
      diagnostic logging with console and file sinks — ADR 0002
- [x] Two independent final reviews from one brief, by Codex and by Claude —
      `docs/reviews/2026-10-28-final-codex.md`, `docs/reviews/2026-10-28-final-claude.md`
- [x] Every finding closed or recorded — `docs/reviews/2026-10-29-final-triage.md`; the
      changes to frozen documents in ADR 0003

## Stage 2 — implementation

Merged from the task lists of both final reviews. It is an order, not a schedule, and it
retires the known risks first: the stack contract on both Manim versions in task 06, the
4 ms per-frame margin in tasks 07 and 09.

How the work is split and run is `docs/implementation-plan.md`. Every task starts with an
**acceptance table** for the under-specified rows it owns
(ADR 0003 §9): signatures, edge cases, errors, reviewed before code. Every task passes
`uv run python tools/check.py`, render tests included. A benchmark runs with
`uv run pytest -m benchmark` on one quiet machine.

### task/06-core-contracts

`core/payload.py`, `core/scales.py`, `core/nodes.py`, and the pin inventory of
`mobjects/context.py`. F-103, F-105, F-109, F-114, F-201-F-209 (numerics), F-301-F-307,
F-311, F-917 (pins), F-1003, F-1006 (payload rows).

- [x] Acceptance table: payload, scales, nodes — `docs/acceptance/06-core-contracts.md`
- [x] Tooling: TID251 for the layer rules (the core imports no Manim; only `context.py`
      reads frames), a derandomised Hypothesis profile for the gate, SciPy declared,
      `__all__`, `ManimPlotsWarning` turned into errors in the tests
- [x] `tests/core/test_payload.py` (one test per invalid-input row), `test_scales.py`
      (round trip and monotonicity by Hypothesis with fixed anchors, symlog,
      `limit_range`), `test_nodes.py` (affine round trip, singular and near-singular
      frames, off-plane points, non-affine inversion)
- [x] `tests/mobjects/test_manim_contract.py`: the pin sets of 0.21.0 and 0.22.0,
      `Scene.get_moving_mobjects` with both queries

### task/07-sources-shape-params

`core/sources.py`, `core/shape.py`, `core/params.py`. F-104, F-106-F-108, F-110, F-113,
F-703-F-707, F-710 (`resample_like`), F-806, F-911 and F-918 (numerics).

- [x] Acceptance table: sources, shape, parameters — `docs/acceptance/07-sources-shape-params.md`
- [x] `tests/core/test_sources.py`, `test_shape.py` (the pipeline order of ADR 0003 §1:
      a segment crossing the viewport, a single point, a pole gap, dash phase),
      `test_params.py` (snapshots, a callable binding dirty once per frame)
- [x] `tests/benchmark/test_core_pipeline.py`: four artists of 2 000 samples on both
      frame paths — the first reading of the 4 ms margin: p95 3.4 ms affine, 4.7 ms
      warped, for the core alone, after one optimisation pass

### task/08-ticks-formatters-lifecycle

`core/ticks.py`, `core/formatters.py`, `core/lifecycle.py`. F-401-F-414, F-501-F-507,
F-920 (plan), F-903, F-905, F-907, F-919 (transitions).

- [x] Acceptance table: locators, formatters
- [x] `tests/core/test_ticks.py` (keys stable across ranges and unique, `Multiple(0.1)`
      exact, merge order on a reversed range, `contains` with `max_ticks`),
      `test_formatters.py` (`format_ticks` and wrapped callables), `test_pool.py`,
      `test_lifecycle.py` (every cell, and the precedence cases of ADR 0003 §5)

### task/09-leaves-context-frame

`mobjects/leaves.py`, `mobjects/context.py`, and enough of `system.py`, `axis.py` and
`artists.py` for one axis and one analytic artist. F-101, F-102, F-111, F-112,
F-901-F-905, F-914-F-917, F-1004, F-1007; F-701 and F-702 begun.

- [x] `tests/mobjects/test_leaves.py` (cache identity, leaf types), `test_context.py`,
      `test_system.py`, `test_animations_basic.py` (copies: LF-6 in `test_leaves.py`)
- [x] Render tests: F-914 against the same scene without the frame; F-915 middle frames
      on both versions and in both insertion orders
- [x] `tests/benchmark/test_f1001.py`: an end-to-end spike without labels — the first
      reading of the real gate

### task/10-axis-decoration

`mobjects/axis.py`, `mobjects/system.py`. F-408, F-411-F-413, F-505-F-508, F-601-F-609,
F-921, F-1009 (constructor, `axis_config`, defaults).

- [x] Acceptance table: axis parts, label layout, `NumberPlane`
- [x] `tests/mobjects/test_axis.py`, `test_defaults.py` (every row of both defaults
      tables against Manim's own `Axes` and `NumberPlane`, style attributes included,
      under a changed `tempconfig` too), `test_number_plane.py`; visual baselines of
      axes and label layout
- [x] F-1001 with labels from a warm glyph cache — measured with task 13's benchmark

### task/11-artists-animate

`mobjects/artists.py`, `mobjects/system.py`, `mobjects/leaves.py`. F-701-F-709,
F-903-F-911, F-915-F-920, F-922, F-1005: keyed `.animate`, `Transform` between systems,
the `ReplacementTransform` transfer, `ax.remove`.

- [x] Acceptance table: artists, registration, the data channel (parts A and B; RG-1,
      MX-4 and MX-5 added after probes)
- [x] `tests/mobjects/test_artists.py`, `test_registration.py`, `test_data_channel.py`
- [x] The F-906 matrix: end states and sampled intermediate frames against plain Manim
      run live (ADR 0003 §7); F-922 with caching on

### task/12-legend-style-animations

`mobjects/legend.py`, `mobjects/animations.py`, `mobjects/artists.py`. F-710, F-801-F-807,
F-912.

- [x] Acceptance table: legend placement and merging, the colour cycle, markers, dashes, the
      `clip` keyword with a margin (asked for on 2026-10-29)
- [x] `tests/mobjects/test_legend.py`, `test_style.py`, `test_animations.py`
      (`TraceCurve` in data order, `Morph`'s pairs); visual baselines

### task/13-hardening

F-1001 final, F-1002, F-1003, F-1005, F-1006 on every surface.

- [x] F-1001 on both frame paths, the 1.5x check against
      `tests/benchmark/test_plain_manim.py`, setup recorded; the JSON kept with the release
      — after a third performance pass, `update` p95 on a quiet machine 2026-10-29:
      tracker 2.7 / 3.1 ms, `.animate` 2.9 / 3.4 ms (affine / bilinear) against 4 ms;
      1.5x passes; recorded in `docs/benchmarks/0.1.json`
- [x] The full gate on both Manim versions
- [x] Types resolve at runtime (TY-1 to TY-3); invalid input per F-1006 (IV-1 to IV-5)

### task/14-docs-release

F-1008, F-1009 in the documentation; packaging.

- [x] Sphinx with numpydoc, warnings as errors; F-1008's differences and the migration
      notes where users meet them
- [x] A changelog, absolute links in the README, Documentation and Issues URLs
- [x] `uv build` with `LICENSE` in the sdist and the wheel; install and import from an
      environment outside the repository
- [x] `dev` into `main`, tagged: the first release — moved to task 23 (ADR 0004)

## Stage 3 — the rest of the first release

ADR 0004 joins 0.1 and 0.2 into one release, `0.1.0`. Each task is run as in stage 2,
acceptance table first; modules, settled points and the Manim defects each task fixes
are in `docs/implementation-plan.md`. Task 13's F-1001 closes before task 16.

### task/15-clip-per-axis

F-706 amended: `clip=(x, y)`, each a bool or a margin.

- [x] Acceptance table, scope row amended — `docs/acceptance/15-clip-per-axis.md`
- [x] Implementation, tests, gate — CP-1 to CP-6 in `tests/mobjects/test_style.py`, a
      candidate baseline `test_clip_per_axis`

### task/16-helpers-lines

Manim's drop lines and calculus helpers, bound: `get_vertical_line`,
`get_horizontal_line`, `get_lines_to_point`, `get_line_from_axis_to_point`,
`get_vertical_lines_to_graph`, `axvline`, `axhline`, `get_T_label`, `slope_of_tangent`,
`angle_of_tangent`, `get_tangent_line`, `get_tangent_vector`, `get_secant_slope_group`,
`plot_derivative_graph`, `plot_antiderivative_graph`.

- [x] Acceptance table: the bound-helper base, each helper's signature, the defects fixed
      — `docs/acceptance/16-helpers-lines.md`
- [x] Implementation, tests against Manim's helpers, visual pairs, gate — 62 tests in
      `tests/mobjects/test_helpers_lines.py`, three candidate pairs; 17 Manim symbols
      pinned

### task/17-helpers-regions

`fill_between`, `get_area`, `get_riemann_rectangles`; clipping a filled region.

- [x] Acceptance table — `docs/acceptance/17-helpers-regions.md`
- [x] Implementation, exact-area tests, visual pairs, gate — a frame with a tracker-bound
      area and Riemann sum costs 10.4 ms, for task 23's performance pass

### task/18-errorbar

`ax.errorbar` with x and y errors, symmetric and asymmetric, correct on log scales.

- [x] Acceptance table — `docs/acceptance/18-errorbar.md`
- [x] Implementation, tests, visual pair, gate — 200 points under an animated range cost
      36.7 ms a frame, the scatter's markers: for task 23's performance pass

### task/19-twin-axes

F-610: `twinx`, `twiny`, further offset axes; plots bound to their pair.

- [ ] Acceptance table, scope row amended
- [ ] Implementation, tests, visual baselines, gate

### task/20-themes

Named axis themes and colour cycles, the maintainer's Origin themes among them.

- [ ] Acceptance table with the names for the maintainer's review
- [ ] Implementation, a baseline per theme, gate

### task/21-fields-flow

The field source and the `region` payload; `ArrowVectorField`, `StreamLines`,
`get_vector`, one integrator and a `Flow` animation; `plot_implicit_curve` if it fits.

- [ ] Acceptance table
- [ ] Implementation, tests, visual pairs, gate

### task/22-polar

`mp.PolarPlane`, `plot_polar_graph` and Manim's polar conversions; `Node` public.

- [ ] Acceptance table
- [ ] Implementation, tests, visual pairs, gate

### task/23-release

- [ ] F-1001 read again; invalid input and types on the new surfaces
- [ ] Documentation, gallery and parity survey for every new name; changelog
- [ ] `dev` into `main`, tagged `v0.1.0` — the maintainer's call
