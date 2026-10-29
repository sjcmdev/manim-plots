# Acceptance table — task 13, hardening

**Status: Living until task 13 merges, then Record.** Written 2026-10-29 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: `docs/scope.md` F-1001-F-1006 and the invalid-input
tables; ADR 0002 (benchmarks on one quiet machine, not in the matrix). Builds on tasks
06-12.

This task adds no feature. It measures the gate F-1001 sets, makes the code meet it, and
closes the cross-cutting rows every earlier task touched: types, cited symbols,
navigability, invalid input on every surface.

## PF — performance (F-1001)

`update` and `setup` are the benchmark harness's quantities (`tests/benchmark/conftest.py`):
`Scene.update_to_time` plus one read of every moving leaf's points, and each play's
compile and begin. A reading is taken with no other agent or build on the machine.

| ID | Row |
|---|---|
| PF-1 | `tests/benchmark/test_f1001.py` measures the gate as F-1001 writes it: four `FunctionPlot`s of 2 000 samples (`use_vectorized=True`, an `x_range` step) on one `CartesianAxes` with `MaxNLocator` ticks and numbers on both axes from a warm glyph cache, the x range animated for one second at 1080p60 — once bound to a tracker that `play` animates, once by `ax.animate.set_x_range` — on the affine frame and after `ax.apply_function` of a smooth warp. Four readings |
| PF-2 | Each PF-1 reading has `update` p95 **<= 4 ms**; the test asserts it. `setup` is recorded, not asserted |
| PF-3 | `tests/benchmark/test_plain_manim.py`'s scene — four static plots under an unrelated `Rotate(Square())` — rebuilt with the library renders with `frame` p95 no more than **1.5 ×** plain Manim's on the same machine in the same session; the test asserts it |
| PF-4 | The readings are written to `docs/benchmarks/0.1.json` *(default taken: the path)* with the machine, the versions and the date, by `uv run pytest -m benchmark --record` *(default taken: the flag)*; the file in git is the reading the release ships with |

## TY — types and navigability (F-1002, F-1005)

| ID | Row |
|---|---|
| TY-1 | Every public callable — each name in `manim_plots.__all__`, `mp.Axes`, `mp.NumberPlane`, `Axis` (what `ax.x_axis` is), and every public method and property of the classes among them — has annotations on every parameter but `self`/`cls` and on its return; `typing.get_type_hints` resolves each of them without error on both Manim versions |
| TY-2 | `tests/usage/test_usage.py`, a test of typical calls with `typing.assert_type` on their results (`ax.plot(f)` is a `FunctionPlot`, `ax.plot(xs, ys)` a `LinePlot`, `ax.x.range.value` an array, `ax.x_axis.ticks.at(1.0)` a `TickLeaf`, `ax.c2p(x, y)` a float array, `ax.legend()` a `Legend`), passes `mypy --strict` in the gate on both Manim versions and passes under pytest |
| TY-3 | Navigability (F-1005): `plot` has its two overloads (AR-2); parameters are descriptors with a typed `value`; parts are reached by attribute and `.at(value)`, never only by a string key |

## SY — cited symbols (F-1003)

| ID | Row |
|---|---|
| SY-1 | `tests/test_cited_symbols.py` also reads `docs/acceptance/*.md` and `docs/parity-survey.md`; every Manim symbol cited there as `module.py::Symbol` or as a backticked Manim name in a parity row imports on both Manim versions |

## IV — invalid input on every surface (F-1006)

One test per cell of `docs/scope.md`'s *at use* table: five surfaces by four columns.
Where an earlier task already tests a cell, the test here names that test in its
docstring and adds the case the earlier one lacked, if any.

| ID | Row |
|---|---|
| IV-1 | Path sampling: a `NaN` or infinity splits the path and warns once per artist per data change, so a second range change warns once more and a style change does not; an argument outside a node's domain likewise; a range outside the scale's domain is normalised before sampling, so no warning; an empty source draws nothing and warns once |
| IV-2 | Tick generation: a candidate that is `NaN` or outside the domain is dropped with no warning; ticks come from the normalised range only; a zero or negative step raises `ValueError` naming the step |
| IV-3 | `c2p` / `p2c`: `NaN`, infinity, an argument outside the domain and a degenerate (singular) frame each raise `ValueError`; neither ever returns `NaN` |
| IV-4 | Formatting: a dropped tick never reaches the formatter (a formatter that raises on `NaN` is never called with it); an empty tick list gives an empty label list |
| IV-5 | Point drawing: an invalid scatter point is not drawn (opacity 0) and warns once per artist per data change; an empty scatter draws nothing and warns once |

## GT — the gate

| ID | Row |
|---|---|
| GT-1 | `uv run python tools/check.py` passes on the four cells, render tests included, with no test skipped or marked `xfail` |

## Tests

| File | Rows |
|---|---|
| `tests/benchmark/test_f1001.py`, `test_plain_manim.py` | PF-1 … PF-4 |
| `tests/test_public_types.py` | TY-1, TY-3 |
| `tests/usage/test_usage.py` | TY-2 |
| `tests/test_cited_symbols.py` | SY-1 |
| `tests/test_invalid_input.py` | IV-1 … IV-5 |
