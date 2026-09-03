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
```

All four checks must pass before a change is merged.

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
- **Naming:** prefer terms already established in the plotting world — `scale`,
  `locator`, `formatter`, `tick`, `spine`, `frame`, `artist`. Do not invent new names
  for concepts that matplotlib or gnuplot already named.
- **Comments:** explain *why*, never *what*. Code that needs a comment to explain what
  it does should be rewritten instead.

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

## Public API stability

Until 1.0 the public API may change in any release. After 1.0 it follows semantic
versioning. Anything that a third party can implement against — scale, locator and
formatter contracts in particular — is public API from the moment it ships, so it gets
reviewed as such.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`,
`docs:`, `test:`, `refactor:`, `chore:`. Keep the subject under 72 characters and
explain the reasoning in the body when it is not obvious.

## Architecture decisions

Consequential design decisions are recorded as ADRs in `docs/adr/`. A decision that
shapes how modules depend on each other belongs in an ADR, not only in a pull request
description.
