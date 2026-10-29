# manim-plots

Correct, extensible plotting primitives for [Manim](https://www.manim.community/).

> **Status: pre-alpha, 0.1.0.dev0.** The coordinate-system engine, four plot artists,
> axis decoration, legends and animations are implemented. The first release awaits
> maintainer review. The API may change before 1.0 except for the frozen
> [0.1 contracts](https://github.com/sjcmdev/manim-plots/blob/main/docs/scope.md).

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
- NumPy >= 2.5

OpenGL is not supported; constructing a library mobject with that renderer raises an
error naming Cairo. Other Manim versions require review of the library's integration.

## Install and draw a first plot

The package is not on PyPI yet. Install the development branch into an environment
with [Manim's system dependencies](https://docs.manim.community/en/stable/installation.html):

```sh
python -m pip install "git+https://github.com/sjcmdev/manim-plots@dev"
```

Save this as `first_plot.py`:

```python
import numpy as np
from manim import BLUE, RIGHT, Create, Scene

import manim_plots as mp


class FirstPlot(Scene):
    def construct(self):
        ax = mp.Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1))
        curve = ax.plot(np.sin, color=BLUE)
        self.play(Create(ax), Create(curve))
        self.play(ax.animate.shift(2 * RIGHT))
```

Render it with Cairo:

```sh
manim -ql --renderer cairo first_plot.py FirstPlot
```

The curve follows the axes when they move or their range changes. Add axes and curves
to a scene separately; `ax.add(curve)` registers a curve without parenting it.

## Documentation

The [user documentation](https://github.com/sjcmdev/manim-plots/blob/main/docs/site/index.rst)
contains a first plot, a
[Coming from Manim guide](https://github.com/sjcmdev/manim-plots/blob/main/docs/site/coming-from-manim.rst),
the [differences from Manim](https://github.com/sjcmdev/manim-plots/blob/main/docs/site/differences.rst),
a [gallery with runnable scenes](https://github.com/sjcmdev/manim-plots/blob/main/docs/site/gallery.rst)
and the [API reference source](https://github.com/sjcmdev/manim-plots/blob/main/docs/site/api.rst).
Until the site is hosted, build the rendered API and guides locally:

```sh
uv run --group docs sphinx-build -W --keep-going -b html docs/site docs/site/_build/html
```

Open `docs/site/_build/html/index.html`. Release preparation is recorded in the
[changelog](https://github.com/sjcmdev/manim-plots/blob/main/CHANGELOG.md).

## Development

```sh
uv sync                         # create the environment
uv run pytest                   # run the test suite
uv run ruff check .
uv run mypy
uv run python tools/check.py    # all checks, across the supported matrix
```

See [CONTRIBUTING.md](https://github.com/sjcmdev/manim-plots/blob/main/CONTRIBUTING.md)
for the project conventions and
[TODO.md](https://github.com/sjcmdev/manim-plots/blob/main/TODO.md) for the task plan.

## Repository layout

```
src/manim_plots/   the library
tests/             its test suite; visual baselines in tests/visual/baselines/
tools/             the local check gate and the parity-survey snapshot tool
docs/              scope, architecture, decisions, reviews — indexed in docs/README.md
poc/               four proofs of concept behind ADR 0001; frozen evidence, never shipped
```

## Licence

[MIT](https://github.com/sjcmdev/manim-plots/blob/main/LICENSE)
