# Acceptance table — task 14, documentation and release

**Status: Living until task 14 merges, then Record.** Written 2026-10-29 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: `docs/scope.md` F-1008, F-1009; `TODO.md`, task 14.
Builds on tasks 06-13.

## DO — the documentation (F-1008, F-1009)

The user documentation is a Sphinx site in `docs/site/` *(default taken: the path; the
design documents in `docs/` stay as they are and are not part of the site)*, built with
`numpydoc` from the docstrings.

| ID | Row |
|---|---|
| DO-1 | `uv run --group docs sphinx-build -W --keep-going -b html docs/site docs/site/_build/html` builds with no warning on Python 3.13. The `docs` dependency group holds `sphinx` and `numpydoc`; `uv.lock` is relocked with uv 0.10.4 |
| DO-2 | The site has an index (what the library is, install, a first plot), a *Coming from Manim* page (the names that stay Manim's, `mp.Axes`, the `axis_config` keys, what to change in ported code), a *Differences from Manim* page, a *Gallery* page (the reviewed baselines as images, each with the code that draws it), and an *API* page documenting every name in `manim_plots.__all__`, `mp.Axes`, `mp.NumberPlane` and `Axis` through autodoc and numpydoc |
| DO-3 | *Differences from Manim* has one section per difference F-1008 lists, each with a short example; and each difference is also stated in the docstring of the public object where a user meets it (`Uncreate` after-effects on `FunctionPlot`, curves following only permanent changes on `CartesianAxes`, `refresh()` on `Leaf`, the raising `c2p`/`p2c`, the late binding of loop variables on `plot`, the tick placement on `MultipleLocator`, the frame's lag slot on `CartesianAxes`, partial drawing paced by sample on `FunctionPlot`) |
| DO-4 | Every `python` code block of the site runs: a test extracts each block from `docs/site/*.rst` and runs it in a dry-run Manim config; a block that is a scene defines a `Scene` subclass, which the test renders |

## RL — the release

| ID | Row |
|---|---|
| RL-1 | `CHANGELOG.md` in the *Keep a Changelog* form, with an `Unreleased` section that will become `0.1.0`: what 0.1 can do, grouped as the scope groups it, and the supported matrix (F-1007) |
| RL-2 | The README's links are absolute (`https://github.com/sjcmdev/manim-plots/blob/main/...`), so they work on PyPI; it shows one first plot and points to the documentation. `[project.urls]` has `Repository`, `Documentation` (the README's documentation section until the site is hosted *(default taken)*) and `Issues` (`https://github.com/sjcmdev/manim-plots/issues`) |
| RL-3 | `uv build` gives an sdist and a wheel; both contain `LICENSE` and `py.typed`; the wheel installed into a fresh virtual environment outside the repository imports, reports `manim_plots.__version__` equal to the project's version, and draws `mp.Axes().plot(np.sin)` in a dry run |
| RL-4 | The version stays `0.1.0.dev0` and nothing is tagged or merged into `main`: the release itself — `dev` into `main`, the tag `v0.1.0`, the version bump — is the maintainer's call, after review of the candidates *(default taken)* |

## Tests

| File | Rows |
|---|---|
| `tools/check.py` (a docs step) | DO-1 |
| `tests/test_docs.py` | DO-2, DO-3, DO-4 |
| `tests/test_packaging.py` (`release` marker, run by `tools/check.py --release`) | RL-1, RL-2, RL-3 |
