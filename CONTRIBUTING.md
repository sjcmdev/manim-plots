# Contributing

## Environment

The project uses [uv](https://docs.astral.sh/uv/). All commands run through it.

```sh
uv sync                     # create/refresh the environment
uv run pytest               # full test suite
uv run pytest tests/x.py::test_name   # a single test
uv run ruff check . --fix   # lint
uv run ruff format .        # format
uv run mypy                 # type check
uv run python tools/check.py   # all four, across Python 3.12/3.13 x Manim 0.21/0.22
uv run python tools/check.py --render   # the same, plus the render tests
```

All four checks must pass across the matrix before a change is merged. There is no
hosted CI; `tools/check.py` is the gate.

## Branches

`main` holds release-ready code only. `dev` is the integration branch. Work happens on
`task/xx-short-title` branches, cut from `dev` and merged back into `dev`; `dev` merges
into `main` when a stage is finished. Task numbers and the full plan live in `TODO.md`.

## Code style

- **Formatting and linting:** `ruff`, configured in `pyproject.toml`. Do not
  hand-format around it.
- **Typing:** `mypy --strict`. Every public function is annotated. `Any` requires a
  comment explaining why it cannot be avoided.
- **Docstrings:** numpydoc convention, matching Manim Community. Every public class
  and function has one. Docstrings describe behaviour and parameters, not
  implementation history.
- **Naming:** Manim's name wins wherever Manim has the concept with the same meaning
  (D17, F-1009). For a concept Manim lacks, prefer terms already established in the
  plotting world — `scale`, `locator`, `formatter`, `artist`. Do not invent new names for
  concepts that Manim, matplotlib or gnuplot already named.
- **Comments:** explain *why*, never *what*. Code that needs a comment to explain what
  it does should be rewritten instead.
- **Logging:** `log = logging.getLogger(__name__)` in each module, with %-style
  arguments and never an f-string (ruff `G`, `LOG`). Nothing is logged inside a
  per-sample loop. An argument that is costly to build goes behind
  `log.isEnabledFor(logging.DEBUG)`. To see the log, set `MANIM_PLOTS_LOG=DEBUG` for the
  console or `MANIM_PLOTS_LOG_FILE=<path>` for a file, or use pytest's
  `--log-cli-level=DEBUG` (ADR 0002).

## Testing

- `pytest` for tests, `hypothesis` for numerical code.
- Numerical logic must be tested without rendering. Tests that require a Manim render
  are slower and belong in a separate module, marked accordingly.
- Every bug fix adds a regression test that fails before the fix.
- Property-based tests are expected wherever a function maps floats to floats: tick
  placement, coordinate transforms and scale inverses are all easier to break at the
  edges than in the middle.
- Prefer a mathematical property as the oracle over a golden value: `p2c(c2p(x)) == x`,
  monotonicity, idempotence. A golden value copied from the current output tests that
  the code still does what it does, which is how the defects this library exists to
  avoid survived for years.
- A visual baseline (ADR 0002) shows what the library draws and catches a change to it.
  It never replaces an oracle. Add or change one only after looking at the picture:

  ```sh
  uv run pytest -m render                               # compare; a failure writes
                                                        # tests/visual/_out/*.actual.png
                                                        # and *.diff.png
  uv run pytest -m render -k <name> --update-baselines  # accept a new or changed picture
  ```

- Benchmarks (`tests/benchmark/`, F-1001) run only on request: `uv run pytest -m
  benchmark`. Each result goes to the terminal summary and to `.benchmarks/`.

## Public API stability

Until 1.0 the public API may change in any release, with one exception: the contracts
frozen in ADR 0001 — scale, locator, formatter, source and payload. Changing one of them
needs a new ADR, and 0.2 may not break them (`docs/scope.md`, tier 0.2). After 1.0 the
whole API follows semantic versioning.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`,
`docs:`, `test:`, `refactor:`, `chore:`. Keep the subject under 72 characters and
explain the reasoning in the body when it is not obvious.

## Architecture decisions

Consequential design decisions are recorded as ADRs in `docs/adr/`. A decision that
shapes how modules depend on each other belongs in an ADR, not only in a pull request
description.
