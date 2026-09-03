# manim-plots

Correct, extensible plotting primitives for [Manim](https://www.manim.community/).

> **Status: pre-alpha.** Nothing is implemented yet. The scope is still being defined.
> The public API is unstable and will change without notice until 1.0.

## What this is

An independent library, written from scratch, that provides coordinate systems and
data plotting for Manim scenes. It builds on Manim's primitives (`Line`, `MathTex`,
`VGroup`) and follows Manim's usage philosophy, but does not subclass Manim's own
`Axes` / `NumberLine` / `NumberPlane`.

The goal is the feature range and customisation depth that users expect from
matplotlib, gnuplot and OriginPro, without inheriting the design problems of the
existing Manim graphing module.

## Requirements

- Python >= 3.11
- Manim Community Edition >= 0.19

## Development

```sh
uv sync            # create the environment
uv run pytest      # run the test suite
uv run ruff check .
uv run mypy
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the project conventions.

## Licence

MIT
