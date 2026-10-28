# ADR 0002 — Test infrastructure: visual baselines, benchmarks, diagnostic logging

- **Status:** Frozen, 2026-10-28; a change needs a new ADR. Amended the same day with the
  final reviews' findings on its harnesses, its gate and its logging
  (`docs/reviews/2026-10-28-final-codex.md`, `docs/reviews/2026-10-28-final-claude.md`).
- **Task:** `task/05-final-review` in `TODO.md`.
- **Supersedes:** in ADR 0001 *Consequences*, the sentence "No expected value is computed
  by the code under test", for visual baselines only; and the same section's "Render tests
  … stay out of the default run. They run with the per-version matrix before a release
  and on every Manim upgrade", which §3 strengthens. The rest of ADR 0001 stands.

## Context

ADR 0001 admits two kinds of test: a correctness oracle (analytic, an invariant, or
plain Manim) and a decision regression. It forbids an expected value computed by the
code under test, and that rules out golden images. The maintainer is then left with no
way to see the pictures the library draws, to keep them from changing unnoticed, or to
add a new one quickly. Manim itself tests with golden frames: `frames_comparison` in
`manim/utils/testing/` checks a render against control data that `--set_test` wrote
from an earlier render, and a person reviews that data by eye.

F-1001 also had no location, no command and no record format. ADR 0001 says render tests
run with the per-version matrix, but `tools/check.py` ran only the default `pytest`. And
the library had no diagnostics, although the mechanism reads Manim's call stack and
rebuilds lazily. Both are hard to debug without a trace.

## Decision

### 1. Visual baselines: a third kind of test, a reviewed change detector

- A visual test is marked `render`, lives in `tests/visual/` and passes a
  `construct(scene)` function to the `visual` fixture. The fixture renders it with Cairo
  in a dry run. It compares the last frame (or, with `frames="all"`, every frame tiled
  into one grid) with `tests/visual/baselines/<module>/<test>.png`.
- Resolution, frame rate and tolerance are Manim's own. A last frame renders at 854×480,
  all frames at 427×240 and 6 fps (`manim/utils/testing/*.cfg`). Within each frame, as
  in Manim, a pixel value may be off by one, and fewer than 0.001 % of the frame's values
  may differ by more (`_frames_testers.py`). A frozen frame, such as a static `wait`,
  appears once for every frame it lasts, so a changed duration changes the grid.
- On a mismatch the test fails and writes two files to `tests/visual/_out/<module>/`,
  which git ignores: `<test>.actual.png`, and `<test>.diff.png` with the differing pixels
  in red. A missing baseline, or one of another size, gets only the actual render. With
  `--update-baselines` the test writes the missing or changed baseline instead and lists
  it in the terminal summary. An unchanged baseline is never rewritten. Two test ids that
  differ only in case would share one file on Windows, so the second one fails.
- TeX and text caches go to `tests/visual/_out/media`, not the working directory.
- A baseline is a **change detector**, not a correctness oracle. It is accepted only when
  the maintainer looks at it in the commit that adds or changes it. A baseline alone closes
  no `F-*`: the oracles listed in ADR 0001 stay mandatory.
- Baselines are PNG files, so they open anywhere and diff as images. One set serves every
  supported Manim version. If a version renders differently, the set is split then.

```sh
uv run pytest -m render                                 # compare
uv run pytest -m render -k <name> --update-baselines    # accept a new or changed picture
```

### 2. Benchmarks

- A benchmark is marked `benchmark`, lives in `tests/benchmark/` and is excluded by
  default. It runs with `uv run pytest -m benchmark`. It is never part of `tools/check.py`,
  because a benchmark needs one quiet machine, not a matrix.
- The `measure_frames` fixture plays a scene at 1080p60 with Cairo in a dry run and
  times each frame twice:
  - `update` is `Scene.update_to_time` plus one read of the points of each entry of
    `Scene.moving_mobjects`, which is already the flat family list. The read runs the lazy
    rebuild the camera would run. This is the quantity F-1001 gates.
  - `frame` adds rasterisation, for F-1001's comparison with plain Manim. The camera's own
    reads of points that are already rebuilt fall here.
  It reports the median, the p95 and the maximum in milliseconds, and refuses fewer than
  20 frames. Whether the clean-getter checks of the camera's reads belong in `update` is
  settled when the getter exists (F-1001's task), by timing the getter itself.
- Each play's setup, `Scene.compile_animation_data` plus `Scene.begin_animations`, where
  keyed alignment and simulation run, is recorded per play and not gated, as F-1001
  requires.
- Each run writes `.benchmarks/<UTC time>-<test>.json` with the machine and the Python,
  Manim and NumPy versions, and adds one line to the terminal summary. Git ignores
  `.benchmarks/`, because a result belongs to one machine. Keeping results is up to whoever
  runs them until F-1001's relative gate starts after a first release. TeX caches go to
  `.benchmarks/media`.
- `tests/benchmark/test_plain_manim.py` measures plain Manim, the reference side of the
  1.5× check.

### 3. Render tests in the merge gate

`uv run python tools/check.py` runs the render-marked tests, the visual baselines among
them, in every cell of the matrix. They are the only check of the frame staying invisible
(F-914) and of a bound artist not freezing (F-915), so no merge skips them. `--fast`
leaves them out for a quick local run; the default `pytest` leaves them out too.

### 4. Diagnostic logging

- Each module logs to `logging.getLogger(__name__)`, under the package logger
  `manim_plots`. That logger carries only a `NullHandler`, so a disabled call costs one
  level check, 64 ns on the maintainer's machine.
- Library diagnostics log at `DEBUG` only. Once Manim is imported, the root logger may
  carry Manim's console handler at `INFO`, and a library `INFO` record would print in
  every user's render.
- Two environment variables, read once at import, attach sinks.
  `MANIM_PLOTS_LOG=<level>` turns on a console sink. `MANIM_PLOTS_LOG_FILE=<path>` turns on
  a file sink, at that level or at `DEBUG`. The file opens at import. An unknown level or
  a bad path raises at import, not in the middle of a render.
- With a sink attached, the package logger stops propagating. Manim gives its `manim`
  logger a console handler, and gives the root logger one too when the root has none
  (`_config/logger_utils.py::make_logger`), so a record could print twice. A file sink
  alone therefore also takes the library's warnings off the console. With no sink
  attached, warnings reach Manim's console handler like Manim's own warnings.
- Under pytest, its own options work unchanged: `--log-cli-level=DEBUG`, or
  `--log-file=<path> --log-file-level=DEBUG`.
- Arguments are %-style and lazy, never an f-string; the ruff groups `G` and `LOG`
  enforce this. Nothing is logged inside a per-sample loop. An argument that is costly to
  build goes behind `log.isEnabledFor(logging.DEBUG)`.

## Consequences

- There are now three kinds of test: correctness oracle, decision regression, visual
  baseline. Only the first two close a requirement.
- A baseline can encode a defect. Manim's own defects survived its golden tests that way.
  The review in the commit is the only guard against this, which is why a baseline never
  stands alone.
- The 16 modules of ADR 0001 §2 are unchanged. The logging setup is in
  `manim_plots/__init__.py`, and the harnesses are in `tests/`.
- **Still open:** pruning baselines that no test uses, and a quiet-machine protocol for
  F-1001 runs (background load, power plan). Both wait until they cost something.
