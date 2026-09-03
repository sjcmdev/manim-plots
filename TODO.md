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
- All four checks (`ruff check`, `ruff format --check`, `mypy`, `pytest`) pass before
  a task branch merges.
- Exceptions to the branch rule: a one-line typo fix in a document may go straight to
  `dev`.
- Commits follow Conventional Commits, as described in `CONTRIBUTING.md`.

## Stage 0 — foundations

Infrastructure and knowledge needed before any design decision is made.

### task/01-revalidate-defects

Re-run the ManimCE defect audit against 0.21.0. The original audit ran against
0.19.2; every finding below is unconfirmed on the version we actually target.
Each confirmed defect becomes a requirement in task 02; each defect that no longer
reproduces is dropped with a note.

- [ ] Float accumulation in `NumberLine` tick generation via `np.arange`
- [ ] `include_tip` alters tick range and coordinate mapping inconsistently
- [ ] Plot curves escape the axes viewport; no clipping for asymptotic functions
- [ ] Axes aspect ratio distortion from independent length parameterisation
- [ ] `unit_size` ignored when passed through `axis_config`
- [ ] Mutating `x_range` after construction leaves ticks stale
- [ ] No legend primitive; users assemble legends by hand
- [ ] `LogBase.inverse_function` ndarray guard broken; negatives become NaN silently
- [ ] `LogBase` has no minor ticks between decades
- [ ] `LogBase` naming: `function()` is exponential, not logarithmic
- [ ] Label overlap: no de-confliction at high label density
- [ ] Ticks centred on the axis line; cannot be directed outward only
- [ ] `_origin_shift` clamps to the range minimum when the range excludes zero
- [ ] Geometric ops on `NumberLine` (inherits `Line`) corrupt coordinate mapping
- [ ] Sweep the audit notes for any finding not listed above
- [ ] Write up the result as `docs/defect-audit-0.21.md`

### task/02-testing-infrastructure

- [ ] Register the `render` marker in `pyproject.toml` (`--strict-markers` is already
      on, so the first marked test fails without it)
- [ ] Exclude render tests from the default run; keep them runnable explicitly
- [ ] GitHub Actions workflow running the four checks
- [ ] Decide the CI matrix: Python versions and Manim versions
- [ ] Branch protection on `main` and `dev`: pull request plus green CI

## Stage 1 — scope

### task/03-functional-scope

Requirements come before architecture. No module layout is decided until this task
closes.

- [ ] Turn each confirmed defect from task 01 into a functional requirement
- [ ] Collect the requirements list from collaborators
- [ ] Parity survey: what matplotlib, gnuplot and OriginPro offer that Manim does not
- [ ] Split into must-have for 0.1, later, and explicit non-goals
- [ ] Write up as `docs/scope.md`

### task/04-architecture

- [ ] Public contracts: scale, locator, formatter — the extension points third
      parties implement against
- [ ] Separation between the data model and the Manim geometry it produces
- [ ] How a coordinate system survives Manim's geometric transformations
- [ ] Record as `docs/adr/0001-architecture.md`

## Stage 2 onward

Task numbering continues once task 03 closes. The coarse order is expected to be:
numeric core (scales, tick location, coordinate transforms) → axis and frame →
data plotting → annotations and legend → documentation and first release. This is a
guess until the scope document exists, and is not a commitment.
