# manim-plots

Correct, extensible plotting primitives for [Manim](https://www.manim.community/).

> **Status: pre-alpha.** No library code yet. The 0.1 scope and the architecture are
> frozen (`docs/scope.md`, `docs/adr/0001-architecture.md`); implementation starts next.
> The public API may change without notice until 1.0, except the contracts ADR 0001
> freezes.

## What this is

An independent library, written from scratch, that provides coordinate systems and
data plotting for Manim scenes. It builds on Manim's primitives (`Line`, `MathTex`,
`VGroup`) but does not subclass Manim's own `Axes` / `NumberLine` / `NumberPlane`.

From the user's side it behaves and is spelled like plain Manim: `mp.Axes`,
`axis_config`, `ax.plot`, `ax.add_coordinates`, `.animate`. It differs from Manim only
where Manim's behaviour is a defect, with those fixes on by default, and where binding
data to a coordinate system needs it; the documentation lists every difference. The
plotting features Manim lacks — scales, tick locators, label formatters, a legend —
follow what matplotlib and gnuplot established.

## Requirements

- Python >= 3.12
- Manim Community Edition 0.21.0 or 0.22.0, Cairo renderer

## Development

```sh
uv sync                         # create the environment
uv run pytest                   # run the test suite
uv run ruff check .
uv run mypy
uv run python tools/check.py    # all checks, across the supported matrix
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the project conventions and
[TODO.md](TODO.md) for the task plan.

## Repository layout

```
src/manim_plots/   the library
tests/             its test suite; visual baselines in tests/visual/baselines/
tools/             the local check gate and the parity-survey snapshot tool
docs/              scope, architecture, decisions, reviews — indexed in docs/README.md
poc/               four proofs of concept behind ADR 0001; frozen evidence, never shipped
```

## Licence

[MIT](LICENSE)
