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
      — the traceability table in `docs/scope.md` maps all 18 to `F-*`
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
      — a NumPy-only `core/` and a `mobjects/` layer, ADR 0001 sections 1-2
- [x] How a coordinate system survives Manim's geometric transformations
      — by reference to `PLAN.md`, ADR 0001 section 4
- [x] Record as `docs/adr/0001-architecture.md` — accepted with the maintainer's
      answers to its five questions
- [ ] Proof of concept for the load-bearing hypotheses: the `points` property on a
      leaf, the transient-mode test under the eight restoring animations, leaf copy,
      rebuild cost against F-1001, and `MathTex` labels as library leaves — prompt in
      `docs/prompts/poc-points-property.md`, report in `docs/poc-points-property.md`.
      It falsified the shadow test, so a second one checks the replacement — a hidden
      frame grid, an animation lifecycle on the leaves, target adoption — prompt in
      `docs/prompts/poc2-frame-lifecycle.md`, report in `docs/poc2-frame-lifecycle.md`.
      A third reads the missing operation context from the call stack — prompt in
      `docs/prompts/poc3-stack-context.md`, report in `docs/poc3-stack-context.md`.
      A fourth makes the data channel native under `.animate` through keyed family
      alignment — prompt in `docs/prompts/poc4-keyed-alignment.md`, report in
      `docs/poc4-keyed-alignment.md`.
      Task 04 closes when the report is in and the ADR reflects it

## Stage 2 onward

Task numbering continues once task 03 closes. The coarse order is expected to be:
numeric core (scales, tick location, coordinate transforms) → axis and frame →
data plotting → annotations and legend → documentation and first release. This is a
guess until the scope document exists, and is not a commitment.
