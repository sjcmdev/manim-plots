# Final review before implementation (Claude, 2026-10-28)

## 1. Header

- **Reviewer:** Claude (Opus 5.5), independent of the Codex review. I did not open
  `docs/reviews/2026-10-28-final-codex.md`. It appeared as an untracked file during my run.
- **Date:** 2026-10-28.
- **Reviewed commit:** `f129014c3729f01d2cbfefa75a5a3fb6317d2fc4` on `task/05-final-review`.
  `git status` before the run: clean.
- **Manim checked:** 0.21.0 (`.venv/Lib/site-packages/manim/`) and 0.22.0 (the uv cache at
  `archive-v0/4EyJTiZ3HPBhfsYn9Inoz/manim/`, plus isolated uv environments). The tools were
  Python 3.13.2 (`.venv`), 3.12.5 and 3.13.2 (matrix), NumPy 2.5.2, SciPy 1.18.1, ruff
  0.16.6, mypy 2.3.1, pytest 9.1.1, Hypothesis 6.167.1 and uv 0.6.16.
- **Citations:** Manim citations give the symbol, then the line, for 0.21.0 unless they say
  0.22.0. Repository citations are `path:line` on the reviewed commit.
- **Order:** I drafted sections A-F before I read the three 2026-10-24 reviews. Section G was
  written after them.
- **Side effects:** one probe that I ran from the repository root (`Axes().add_coordinates()`)
  wrote 16 TeX and SVG files into `./media/Tex`, which git ignores. That directory did not
  exist before, and I deleted it. The benchmark runs added two JSON files to the existing,
  git-ignored `.benchmarks/`, and Python wrote bytecode to `__pycache__/`. Nothing else in the
  tree changed.

**Commands run.** Probe scripts live in the session scratchpad,
`C:\Users\Franek\AppData\Local\Temp\claude\D--Programming-Python-manim-manim-plots\8f88bf2e-a639-4920-a45b-d277dd9e629c\scratchpad\review-claude-final\`.
The findings quote their essential lines.

```text
# repository
git rev-parse HEAD; git status; git ls-files; git ls-files -s (duplicate blobs)
git branch -a -vv; git log --oneline --graph -30 --all; git tag -l; git log --merges main
git check-ignore -v --no-index docs/images/frame-path.png docs/_static/videos/intro.mp4 tests/visual/images/x.png src/manim_plots/texts/a.txt
git show f57b286:tests/test_defect_audit_0_21.py | grep -n "# type: ignore"
python (regex scripts): F-* row and tier counts in docs/scope.md; parity-survey verdict counts;
  every F-*/D-* reference across tracked files; every Markdown link and backticked repo path

# the four checks (caches redirected: RUFF_CACHE_DIR, MYPY_CACHE_DIR to the scratchpad; pytest -p no:cacheprovider)
.venv/Scripts/python.exe -m ruff check .            -> All checks passed!
.venv/Scripts/python.exe -m ruff format --check .   -> 97 files already formatted
.venv/Scripts/python.exe -m mypy                    -> Success: no issues found in 14 source files
.venv/Scripts/python.exe -m pytest -p no:cacheprovider -q          -> 56 passed, 3 deselected
.venv/Scripts/python.exe -m pytest -p no:cacheprovider -m render   -> 2 passed in 0.94s
.venv/Scripts/python.exe -m pytest -p no:cacheprovider -m benchmark -> 1 passed (update p95 0.20 ms, frame p95 2.64 ms)
UV_OFFLINE=1 uv sync --locked --dry-run             -> Would make no changes
UV_OFFLINE=1 uv run --isolated --python {3.12,3.13} --with manim=={0.21.0,0.22.0} python -c "import manim; print(manim.__version__, manim.__file__)"
UV_OFFLINE=1 PYTEST_ADDOPTS="-p no:cacheprovider" uv run python tools/check.py --render  -> All checks passed. (58 passed per cell)
UV_OFFLINE=1 uv run --isolated --python 3.13 --with manim==0.22.0 python -m pytest -p no:cacheprovider -m benchmark -> 1 passed
UV_OFFLINE=1 uv build --sdist --wheel -o <scratchpad>/dist; tar -tzvf manim_plots-0.1.0.dev0.tar.gz; zipfile listing of the wheel

# probes (scratchpad), 0.21.0 unless marked
mypy --config-file pyproject.toml mypy/probe_getattr.py        (Manim __getattr__ typing)
python -W default -c "... leaf.set_locater(5) ..."; ".animate.set_x_rnage" dry-run scene
static/probe_static*.py                                         (visual harness end frame)
pins/dump_pins.py on 0.21.0 and 0.22.0 + comparison             (stack contract, E.4)
moving/probe_moving.py on 0.21.0 and 0.22.0                     (Cairo moving-object test)
NumberLine(x_range=...).get_tick_range() for [0.001,6,1] [0.5,5,1] [-2.5,3,1] [-7,7,1] [-0.5,2.6,1] [10,0,-1] [10,0,1]
NumberLine._decimal_places_from_step(1, 1.0, 0.5, 0.25, 1e-05)
pointwise_become_partial(m, 0, 0.5) on uniform and refined samplings (Create pacing)
len(Axes().family_members_with_points()) and Animation.get_sub_alpha arithmetic (lag slot)
extract_mobject_family_members([Axes().add_coordinates()]) vs sum(len(m.get_family()))  (benchmark reads)
PIL size of tests/visual/baselines/test_harness/test_every_frame_of_create_circle.png    (tolerance dilution)
ruff-layers/ and numpydoc/ scratch projects with ruff 0.16.6   (TID251, D417)
logging/probe_log.py with no env, with MANIM_PLOTS_LOG_FILE, bad path, MANIM_PLOTS_LOG=10; caplog tests with MANIM_PLOTS_LOG=WARNING
hyp/ Hypothesis database location (passing and failing property)
proto/probe_proto.py                                            (frozen dataclass vs ADR Scale protocol, mypy)
Formatter dispatch probe (runtime_checkable Protocol of ADR 0001 section 3)
sigs/dump_sigs.py on 0.21.0 and 0.22.0                          (signatures of the 43 0.1 names)
sed/grep over the 0.21.0 and 0.22.0 sources: cairo_renderer.py, scene.py, animation.py, creation.py,
  vectorized_mobject.py, number_line.py, coordinate_systems.py, _config/logger_utils.py, utils/testing/*
```

## 2. Verdict

**Ready after the listed blockers.** The layering, the 17 stack frames and the four-cell gate
all hold on both Manim versions. The first implementation task, the numeric core, depends on
four things that are contradictory or undefined in the frozen documents: formatter dispatch,
two lifecycle cells, callable bindings, and a set of numeric definitions. Each needs a short
decision, not a redesign.

## 3. Blockers

### Blocker 1. A plain callable cannot be told apart from a `Formatter`

- **Problem.** ADR 0001 §3 types `Formatter` as a Protocol whose only member is
  `__call__(self, values) -> Labels` (`docs/adr/0001-architecture.md:179-180`). A third party
  implements it without inheriting from us (`:95-97`). F-504 and ADR `:192` accept "a plain
  callable `float -> str`", which is wrapped. A plain callable satisfies the Protocol
  structurally, so `set_formatter(x)` cannot decide whether to call `x(values)` once or wrap it
  per value. Trying a call does not decide it either, because a per-value callable may accept
  the whole array and return one string. `formatters.py` belongs to the first task.
- **Evidence.**
  - The Protocol as ADR 0001 writes it, made `@runtime_checkable`: both
    `isinstance(Decimal(), Formatter)` and `isinstance(lambda x: f'{x:.1f}', Formatter)` print
    `True`.
  - `per_value = lambda x: str(np.round(x, 2))` gives `'0.5'` for `0.5`, and
    `'[0.  0.5 1. ]'` for `np.array([0., .5, 1.])`, without an error.
  - Arch-crew pattern finding 2 (`docs/reviews/2026-10-24-arch-crew.md:110-113`) asked for an
    Adapter or `singledispatch`. No decision chose either (section G).
- **Fix.** A new ADR, or a D-number if `__call__` counts as one of the "proposed names" of ADR
  `:94`. Either give the Protocol a named method, such as `format_ticks(values) -> Labels`, so
  that a plain callable is anything without that method, or require plain callables to go
  through an explicit wrapper (`FuncFormatter(f)`) and say so in F-504. `Locator` has no such
  problem, because it has named methods.
- **Cost.** Small.

### Blocker 2. The lifecycle table has two indeterminate cells that the first task needs

- **Problem.**
  - **(a) Two rows apply to one event.** `FadeOut(curve)` is a `Transform` with an artist
    target copy and `remover=True`. When it finishes, the table offers both "The last owner
    finishes, ended on an artist target → adopts the target's source, own transform, style
    and system → **A**" (`docs/adr/0001-architecture.md:297`) and "The last owner was a
    remover, after its cleanup → **R**" (`:301`). If the target is adopted, its style comes
    with it, so the artist keeps FadeOut's opacity 0 for good. PoC 4 gave removers
    precedence: `poc/poc4/model.py:654-663` detaches on a remover's resume, and `:695-696`
    installs no target candidate for a remover. The table states no precedence.
  - **(b) The begin event comes too late for a non-Transform introducer.** F-907's own example
    is `Create` after `Uncreate` (`docs/scope.md:210`). The table's begin event is "a
    suspension from `Animation.begin`" (ADR `:295`). But `animation.py::Animation.begin` takes
    `self.starting_mobject = self.create_starting_mobject()` at `:205`, before it suspends at
    `:213`. That order holds in 0.21.0 and, with an identical body, in 0.22.0. The table makes
    a copy of an **R** artist an **R** (`:305`). So `Create` draws from the degenerate copy and
    shows nothing, while F-907 says "A later introducer draws the current curve".
    - PoC 4 rewrote `animation.starting_mobject` and `animation.outline` inside the leaf's
      `suspend_updating` (`poc/poc4/model.py:626-635`). Its review note calls this rewriting
      the animation object (`docs/poc/poc4-keyed-alignment.md:471-479`).
    - The notes under ADR §4 (`:312-319`) cover only points captured in a constructor.
  - `lifecycle.py` and its unit test per cell (`:320-322`) are in the first task.
- **Evidence.** The ADR lines and Manim lines above. `Animation.begin` is byte-identical in
  0.22.0 (E.4 table).
- **Fix.** A new ADR amending §4 with two rules:
  1. A remover's finish takes precedence, and a remover installs no target.
  2. Re-attaching at an introducer's begin re-takes `starting_mobject`, and `outline` for
     `Write` and `DrawBorderThenFill`, after the rebuild.

  List both attributes in F-917's inventory of assigned animation attributes
  (`docs/scope.md:220`).
- **Cost.** Small.

### Blocker 3. Callable bindings: F-110 contradicts F-918 and the PoC-validated mechanism

- **Problem.**
  - F-110 says "a callable binding is always dirty" (`docs/scope.md:50`, also
    `docs/plan.md:247`). That is D21's rule (`docs/grill-log.md:585-587`), which D22 revised
    (`:602-617`).
  - F-918 resamples every frame "only when a parameter is bound to a tracker or under
    `always_redraw`" (`docs/scope.md:221`). D8 lists a plain callable as a third kind of
    binding (`docs/grill-log.md:178-180`). F-915 relies on "hold a live function"
    (`docs/scope.md:218`), which no document defines.
  - With F-102, where the getter rebuilds when dirty (`docs/scope.md:42`), "always dirty"
    means a rebuild on every `points` read. PoC 3 K5 built the opposite and rejected exactly
    that: "Do not make every lazy read invalidate the callable"
    (`docs/poc/poc3-stack-context.md:400-403`).
  - `params.py` (F-110) is in the first task.
- **Evidence.** The rows and lines above.
- **Fix.** A new ADR, because both are 0.1 rows:
  - a callable binding is dirty once per frame token, that of the synchronisation updater,
    not once per read;
  - F-918's list gains "a parameter bound to a callable";
  - F-915's "live function" is defined as exactly F-918's cases.
- **Cost.** Small.

### Blocker 4. The numeric core's tests need values no document defines

- **Problem.** Table D lists the gaps. These seven make a test impossible to write without
  guessing:
  1. **SymLog:** no parameters and no formula anywhere (`docs/scope.md:108`,
     `docs/adr/0001-architecture.md:70`).
  2. **MaxN:** only "nice-number steps" (`docs/parity-survey.md:273`). The step set is not
     given, and neither is what `n` means against `max_ticks` (ADR `:147-149`).
  3. **Key rounding:** the digit count of the canonical key is not given (ADR `:155`).
  4. **F-311:** `eps` is undefined, and so is the policy for a range wholly outside the domain
     or reversed (`docs/scope.md:115`).
  5. **Tolerances:**
     - F-201's "floating-point tolerance" (`:94`) and F-207's tolerance (`:100`);
     - F-305's falsification: sample count, placement on infinite domains, and round-trip
       tolerance (`:112`);
     - the frame's affinity test (F-914);
     - F-108's "correct plot" (`:48`), which is the adaptive sampler's error criterion
       (F-704, `:177`).
  6. **Exception type:** the invalid-input rule names none. A grep for `[A-Z]\w*Error` over
     scope, the ADRs, the plan and the grill log finds only an `AttributeError` in D15.
  7. **Warning channel:** the one F-705, F-917 and F-920 use (D2).

  Codex's freeze review raised 1, 4 and 5 as its D1 on 2026-10-24
  (`docs/reviews/2026-10-24-codex.md:118-124`). D22-D27 did not close them.
- **Fix.** One page, as ADR 0003 "core numerics" or as D28 with scope edits. Proposals,
  for the maintainer to accept or replace:
  - SymLog is matplotlib's `(base, linthresh, linscale)` with stated defaults.
  - MaxN uses steps `[1, 2, 2.5, 5, 10]`, with `min(n, max_ticks)` as the bound.
  - Keys round to 12 significant digits.
  - `limit_range` takes `minpos` (E4); `eps` is `minpos` or a stated constant.
  - Conversions use a relative tolerance of 1e-12 of the span, and the sampler uses one in
    pixels at 1080p.
  - Invalid input raises one `ValueError` subclass.
  - One warning category (D2).
- **Cost.** Medium: about a dozen decisions, no code.

## 4. Findings

Counts: 4 blockers, 19 major, 32 minor.

### A. Repository hygiene and organisation

**A1 — minor. Three byte-identical model files.** `git ls-files -s` shows that
`poc/poc2/model.py`, `poc/poc3/baseline_model.py` and `poc/poc4/baseline_model.py` share one
blob. The copies are deliberate: PoC 3 explains `baseline_model.py`
(`docs/poc/poc3-stack-context.md:288-291`). `poc/README.md` does not say so. **Fix:** one line
in `poc/README.md`.

**A2 — minor. PoC 1 cites evidence images that are not on the tree.**
`docs/poc/poc1-points-property.md:50` names `poc/poc1/media/property.png` and `plain.png`.
`media/` is git-ignored (`.gitignore:21`), so neither file is tracked. That is the only
unresolved path in the Records apart from generated directories. **Fix:** commit the two PNGs
with a `!poc/poc1/media/*.png` negation, or reword the line to say the test regenerates them.

**A3 — minor. The document index omits the root documents.** `docs/README.md:3` says the index
covers "Everything about manim-plots that is not code". It does not list `README.md`,
`CONTRIBUTING.md` (the testing policy and the meaning of Frozen), `TODO.md` (the plan and the
branch policy), `poc/README.md` or `LICENSE`. **Fix:** add a "Root documents" table, or narrow
the sentence to `docs/`.

**A4 — minor. Two statuses do not match the documents' own headers.**
- `docs/grill-log.md` is *Living* and outranks `plan.md` in the precedence rule
  (`docs/README.md:11-12`). Its header still reads "Running record of decisions locked during
  the Act 1 interview … Not the deliverable. Feeds `docs/plan.md`"
  (`docs/grill-log.md:3-5`).
- `docs/plan.md` is *Living*. Its header says "Revised after … D17-D21" (`docs/plan.md:5-7`),
  yet its body carries D22-D26 (for example `:249`, `:264`). Its Goal and "Acceptance criteria
  for this task" (`:20-70`) are task/03's.

**Fix:** rewrite both headers to say what each document is now.

**A5 — minor. The precedence rule and the meaning of Frozen are incomplete.**
- `docs/README.md:11-13` ranks "the ADRs and the 0.1 tier of `scope.md`" together but does not
  order them against each other. C3 shows a real conflict between the two.
- `docs/README.md:5` defines Frozen by pointing to CONTRIBUTING's *Public API stability*
  (`CONTRIBUTING.md:75-80`). That section freezes only ADR 0001's five contracts. It does not
  cover the scope's 0.1 tier (`docs/scope.md:3-4`), the lifecycle table, `CompiledMap`,
  `Bounds`, `Labels`, or ADR 0002.

**Fix:** define Frozen in `docs/README.md` itself, and order the two documents, for example
"the ADR wins on contracts, scope on requirements".

**A6 — minor. The gate lints the frozen PoC code.** `tools/check.py:38-39` runs `ruff check .`
and `ruff format --check .` over `poc/`, and `pyproject.toml:69` ignores only `D` and `ANN`
there. A ruff upgrade that adds a rule or changes the formatter style fails the gate on code
that is "not maintained" (`poc/README.md:5`). It costs nothing until the next ruff upgrade.
**Fix:** add `extend-exclude = ["poc"]` to `[tool.ruff]`.

**A7 — minor. Four unanchored ignore patterns hide directories outside `media/`.**
`.gitignore:22-25` (`videos/`, `images/`, `Tex/`, `texts/`) match at any depth. `git check-ignore`
reports `docs/images/frame-path.png`, `docs/_static/videos/intro.mp4`,
`tests/visual/images/x.png` and `src/manim_plots/texts/a.txt` as ignored. Manim writes these
directories only under `{media_dir}` (`_config/default.cfg:80-93`), which line 21 already
covers. **Fix:** delete lines 22-25.

**A8 — minor. The branch policy and the history disagree.**
- `main` (44778fe) has never received a merge, and there are no tags (`git tag -l` is empty),
  although stages 0 and 1 are finished.
- `CONTRIBUTING.md:23-25` merges `dev` into `main` "when a stage is finished". `TODO.md:17-18`
  adds "and ships a coherent package of functionality". Neither rule has been followed.
- `95bb129` went straight to `dev`, outside the one-line exception for typos (`TODO.md:21-22`).
- Local `dev` is 19 commits ahead of `origin/dev`, and `task/04-architecture` 16 ahead of its
  remote, so the freeze, ADR 0001 and all four PoCs exist only on this machine.

**Fix:** state one rule in both files, for example "main receives the first release, tagged",
and push.

*Checked without a finding:*
- every other tracked file, including `poc/poc4/full-final.log`, the 693 PoC JSON files and
  the two `manim_sources.txt` files: all are evidence linked from the reports;
- `uv.lock` and `.python-version` (3.13 against a 3.12 floor);
- the `src/` layout with `py.typed`;
- `.gitignore` against `.benchmarks/`, `tests/visual/_out/`, `dist/`, Manim's `media/` and
  the caches;
- `.hypothesis/`: Hypothesis 6.167.1 writes its own `.gitignore` containing `*` when a
  property fails (probe), so no root entry is needed;
- `docs/reviews/2026-10-24-arch-crew.md:193`, which names `docs/architecture/decisions/` as
  deliberately not introduced, so that path is not broken.

### B. Tooling and engineering standards

**B1 — major. Manim ships type information, so misspelled attributes on any library mobject
pass mypy, and a misspelled `set_*` call is a silent write.** The brief's premise that "Manim
ships no types" is wrong.
- `.venv/Lib/site-packages/manim/py.typed` exists, and so does the 0.22.0 `py.typed` in the uv
  cache. The override `module = "manim.*"`, `ignore_missing_imports = true`
  (`pyproject.toml:76-78`) does nothing: mypy reads Manim's annotations, and
  `reveal_type(ax.plot)` prints Manim's full signature.
- What reaches the library as an unchecked type is mostly not `Any` but
  `mobject.py::Mobject.__getattr__ -> types.MethodType` (`:729`). Every unknown attribute on
  every Mobject subclass type-checks.
- Probe under the project's mypy configuration: `ax.this_attribute_does_not_exist`,
  `ax.plto(lambda x: x)` and `leaf.set_locater(5)` give
  `Revealed type is "types.MethodType"` and `Success: no issues found`.
  `_AnimationBuilder.__getattr__ -> Callable[..., _AnimationBuilder]` (`:3439`) does the same
  for `.animate`.
- At runtime, `leaf.set_locater(5)` returns the leaf and creates an attribute `locater`.
  `self.play(ax.animate.set_x_rnage([0, 20, 1]))` plays a no-op and leaves
  `ax.x_rnage == [0, 20, 1]`. The only signal is a DeprecationWarning ("This method is not
  guaranteed to stay around…"), which Python hides by default.
- The core contracts of ADR 0001 §3 are unaffected. F-1002 and F-1005 for the Manim layer are
  weakened.

**Fix:** two decisions, at stage 06 or with the first Manim-layer task:
1. The library's base mobject overrides `__getattr__` to raise `AttributeError` for unknown
   names, dropping Manim's deprecated `get_`/`set_` shim on library types.
2. pytest gets `filterwarnings = ["error:This method is not guaranteed to stay around:DeprecationWarning"]`.

**B2 — major. Render tests are outside the merge gate.**
- A task merges after `uv run python tools/check.py` without `--render` (`TODO.md:19-20`,
  `CONTRIBUTING.md:18-19`, `tools/check.py:41`).
- F-914's pixel test and F-915's middle-frame test (`docs/adr/0001-architecture.md:343-344`)
  are the only oracles for their failure modes. They run "before a release and on every Manim
  upgrade" (`:351-352`; ADR 0002 §3).
- A task that brings back Cairo's static-background freeze (PoC 2 G5: 1644 differing
  channels, `docs/poc/poc2-frame-lifecycle.md:372-377`) merges green.
- The render suite costs 0.94 s today.

**Fix:** make `--render` the merge gate, with an opt-out flag for quick local runs. Add it at
stage 06, before the first render test arrives.

**B3 — major. The benchmark's `update` reads each moving leaf once per ancestor.**
- `Scene.moving_mobjects` is already the flat, deduplicated family list:
  `scene.py::Scene.get_moving_and_static_mobjects`, `:948-965`, returns
  `extract_mobject_family_members(...)`, which calls `remove_list_redundancies`.
- The harness walks `mobject.get_family()` for each entry again
  (`tests/benchmark/conftest.py:90-92`).
- For `Rotate(Axes().add_coordinates())`: `extract_mobject_family_members([ax])` holds 142
  members, and `sum(len(m.get_family()) for m in ...)` is 741 reads per frame, 5.2 times as
  many.
- Each extra read of a library leaf is a clean-getter check inside the 4 ms gate.
  - PoC 1 measured 215 ns without a comparison and 4,291 ns with one
    (`docs/poc/poc1-points-property.md:317-320`).
  - A frame-grid comparison costs 4.5 µs per read at N = 33
    (`docs/poc/poc2-frame-lifecycle.md:441-446`).
  - The margin is thin: 3.07 and 3.73 ms (`docs/poc/poc4-keyed-alignment.md:353-354`).

**Fix:** `for member in self.moving_mobjects: _ = member.points`.

**B4 — major. The benchmark records no setup work.**
- F-1001 requires setup per play (keyed alignment, simulation) to be "recorded, not gated"
  (`docs/scope.md:231`; D26, `docs/grill-log.md:737-740`).
- The harness times only `update_to_time` and `render` (`tests/benchmark/conftest.py:72-98`),
  and its record has no setup field (`:128-133`).
- Setup runs in `scene.py::Scene.begin_animations`, `:1340-1353`, called from
  `cairo_renderer.py::CairoRenderer.play`, `:107`: outside both timers.

**Fix:** time `begin_animations` per play and write it to the JSON.

**B5 — minor. The visual harness is looser than Manim, and ADR 0002 describes its output
inaccurately.**
- *Tolerance.* The mismatch ratio covers the whole tiled sheet (`tests/visual/conftest.py:124-129`).
  Manim applies it per frame (`utils/testing/_frames_testers.py:59-66`). The committed sheet
  is 1289×728, 3×3 tiles. It tolerates 37.5 differing values, against Manim's 4.1 per frame,
  so one frame may differ 9.2 times more than Manim allows.
- *Frames.* `_Capture.add_frame` keeps one tile per call and ignores `num_frames`
  (`conftest.py:53-56`). A frozen `wait(n)` therefore adds one tile whatever `n` is
  (`cairo_renderer.py::CairoRenderer.freeze_current_frame`, `:197-209`).
- *Names.* Baseline names are sanitised node names (`:114`). On Windows' case-insensitive
  filesystem, ids that differ only in case share one PNG. That is the `rotate` / `Rotate`
  collision PoC 3 hit (`docs/poc/poc3-stack-context.md:265-266`).
- *ADR 0002.* `:34-36` says a failure writes two files to `tests/visual/_out/`. The harness
  writes to `_out/<module>/`, and writes no diff for a missing baseline or a size mismatch
  (`conftest.py:117-118`, `:138-152`).

**Fix:** compute the ratio per tile; repeat or count frozen frames; lower-case the names and
check for collisions; correct ADR 0002.

**B6 — minor. With logging "off", library INFO records still print.**
- `_config/logger_utils.py::make_logger`, `:104-106`, adds Manim's `RichHandler` to the root
  logger and sets the root to the verbosity (INFO) when the root has no handlers.
- Probe after `import manim`: `root level: INFO root handlers: ['RichHandler']` and
  `library effective level: INFO INFO enabled: True`. A `log.info` from
  `manim_plots.core.ticks` printed to the console.
- ADR 0002 `:77-79` says "a disabled call costs one level check". That is true for DEBUG
  only; I measured 60 ns.

**Fix:** set `logging.getLogger("manim_plots").setLevel(logging.WARNING)` when no sink is
attached, or adopt the rule "library code logs at DEBUG; WARNING is for users".

**B7 — minor. Turning a sink on changes behaviour.**
- With only `MANIM_PLOTS_LOG_FILE` set, propagation stops (`src/manim_plots/__init__.py:27`),
  and the library's warnings leave the console entirely. Probe: the handlers are
  `['NullHandler', 'FileHandler'] propagate: False`, the WARNING record appears only in the
  file, and nothing reaches the console.
- A bad path does not fail at import. Because the handler is delayed (`:32`), it raises out of
  the first library log call, which can happen mid-render. Probe:
  `raised from log.warning: FileNotFoundError [Errno 2] No such file or directory: 'Z:\\no\\such\\dir\\x.log'`.
- `MANIM_PLOTS_LOG=10` raises `ValueError: Unknown level: '10'`.
- Not a defect: under pytest 9.1.1, caplog still sees the records with `MANIM_PLOTS_LOG` set,
  because pytest attaches its handlers to the non-propagating logger (probe).

**Fix:** open the file at configuration time, so that a bad path fails at import like a bad
level; document that the file sink takes over the console's warnings.

**B8 — minor. Add now: `D417`.** `convention = "numpy"` (`pyproject.toml:64-65`) disables
`D417`. In a probe, a docstring whose Parameters section names a removed parameter `x` and
omits `x_value` and `y_value` passes `ruff check`. With `--extend-select D417` it reports
`D417 Missing argument descriptions in the docstring for c2p: x_value, y_value`. The defect
this prevents: a parameter renamed to Manim's spelling (D17) leaves a stale docstring.
**Fix:** add `extend-select = ["D417"]` now.

**B9 — minor. Fix now: `LICENSE` is in neither distribution.** `tar -tzvf` of the sdist lists
only `PKG-INFO`, `README.md`, `pyproject.toml` and `src/manim_plots/{__init__.py,py.typed}`.
The wheel's METADATA has `License-Expression: MIT` and no `License-File`. The MIT text requires
the notice "in all copies". **Fix:** add `license-files = ["LICENSE"]` to `[project]`
(`pyproject.toml:10`).

**B10 — minor. The version lives in two places.** `pyproject.toml:3` and
`src/manim_plots/__init__.py:7` both hold it, and `tests/test_smoke.py:4-5` only checks that it
is truthy. Bumping one at release leaves `__version__` wrong. **Fix:**
`__version__ = importlib.metadata.version("manim-plots")`, or a test that compares the two.

**B11 — minor. Packaging work due at the first release.**
- `README.md:37-38` and `:52` use relative links; they become the PyPI long description and
  break there.
- `tests/test_cited_symbols.py:17-21` and `tests/test_parity_surface.py:27` read `docs/`. If
  tests are ever shipped in the sdist, for conda-forge for example, those four documents must
  ship with them. Today neither does, which is right: `poc/` (1.3 MB of JSON) and `docs/` do
  not belong in the sdist.
- SciPy is imported by the core (`docs/adr/0001-architecture.md:37-39`) but not declared
  (`pyproject.toml:19-22`). It arrives only through Manim's `scipy>=1.13.0` (both versions'
  METADATA). Declare it at stage 06, so that the floor the core is tested against is stated.
- Release work: a changelog, and Documentation and Issues URLs (`pyproject.toml:24-25`).

**B12 — minor. `pytest-cov` is unused.** `pyproject.toml:32` declares it; no `--cov` appears
in the configuration or in `tools/check.py`. **Fix:** remove it.

**B13 — minor. Both harnesses write TeX into the working directory once labels exist.**
`Axes().add_coordinates()`, run from the repository root, wrote 16 files into `./media/Tex`
(see the header). The benchmark's docstring says "nothing is written to disk"
(`tests/benchmark/conftest.py:4-5`), yet F-1001's scenario has labels. **Fix:** set
`media_dir` in both `tempconfig`s to a git-ignored directory, for example
`tests/visual/_out/media` and `.benchmarks/media`.

#### Table B — tooling

| Item | Current state | Verdict | When |
|---|---|---|---|
| B.1 mypy | `strict`; `files = ["src", "tests"]`; `python_version = "3.12"` (the floor); the 3.13 cells therefore re-check 3.12 semantics, which is harmless; `tools/` is unchecked; the `manim.*` override is inert because Manim is typed. NumPy 2.5 stubs also yield `Any` (`np.log(x) / np.log(b)` → `no-any-return`, probe) | **fix now**: drop the inert override, and decide B1 (`__getattr__`) | B1 at stage 06 |
| B.2 ruff | E W F I UP B SIM NPY D ANN RUF G LOG; `poc/**` ignores D and ANN. Layer rules: `TID251` works, see below | **add at stage 06**: `TID251` in place of most of the planned static test | first core module |
| B.3 pytest, Hypothesis, coverage | markers registered, strict; no Hypothesis profile; `pytest-cov` unused; harnesses correct apart from B3, B4, B5 and B13 | **fix now**: remove `pytest-cov`; **add at stage 06**: a gate profile `derandomize=True`, which prevents a property failure that one of the four cells shows and the next cannot reproduce | stage 06 |
| B.4 gate | four cells, each importing the Manim it names (verified); passes with `--render`; benchmarks never run (they work on 0.22.0, my run); render tests outside the merge gate (B2); `uv build` not checked (B9) | **fix now**: B2 | now |
| B.5 docs | numpydoc through ruff `D`, but `D417` is off (B8); no Sphinx | **add now** `D417`; Sphinx **add at the stage "documentation and first release"**, where F-1008 and the migration notes need a home | release stage |
| B.6 packaging | PEP 621 complete; `license = "MIT"` matches `LICENSE`; classifiers fine under PEP 639; bounds match F-1007 (`manim>=0.21,<0.23` with the warning at import); `py.typed` is in the wheel; the version is in two places; no changelog | **fix now** B9; B10, B11 at the first release | — |
| B.7 visual and diagnostics | see the answers below | B3, B4, B5, B6, B7, B13 | stage 06 |

**B.2 against ruff's behaviour (ruff 0.16.6, scratch package).** A nested
`src/pkg/core/ruff.toml` with `extend = "../../../pyproject.toml"` and a `banned-api` of
`manim` and `pkg.mobjects` flags all of these in `core/`:
- `import manim`, `from manim import Axes` and `from manim.mobject import mobject`;
- `from pkg.mobjects import leaves`;
- the relative forms `from ..mobjects import leaves` and `from .. import mobjects`;
- `import pkg.mobjects.leaves`.

The root `banned-api` of `sys._getframe` and `inspect.currentframe`, with a per-file ignore
for `mobjects/context.py`, flags `from sys import _getframe`, `sys._getframe(1)` and
`inspect.currentframe()` in `mobjects/leaves.py`. Three limits showed up:
1. The child's `banned-api` table **replaces** the parent's. `sys._getframe()` in
   `core/scales.py` was not flagged, so the frame APIs must be repeated in the child.
2. Attribute reads such as `f.f_code` and `f.f_locals` cannot be banned.
3. `importlib.import_module("manim")` passes.

TID251 can therefore replace the import rule entirely and the frame rule for every API that
yields a frame: `sys._getframe`, `inspect.currentframe`, `inspect.stack`,
`inspect.getouterframes`, `inspect.trace` and `traceback.walk_stack`. A ten-line AST check
remains for `f_code` and `f_locals` outside `context.py`, if wanted.

#### B.7 — the five questions

1. **A failure only a rendered frame shows, with no planned render.**
   - **F-922.** Only a re-render with caching on shows a stale cached partial movie. Both
     harnesses force `disable_caching` (`tests/visual/conftest.py:37`,
     `tests/benchmark/conftest.py:36`), and ADR 0001's *Consequences* table has no F-922 row
     (`docs/adr/0001-architecture.md:328-346`).
   - **Style defaults.** The F-1009 parity test is "geometry-level"
     (`docs/adr/0001-architecture.md:342`), so the defaults table's style rows go unchecked:
     white `plot`, `PURE_YELLOW` `plot_line_graph`, stroke width 2.0.
   - **F-706 at the clip boundary.** Stroke overhang and smoothing bulge show only in pixels.
2. **Intermediate frames.** No planned test compares any intermediate frame with plain Manim.
   - F-906 compares end states (`docs/scope.md:209`).
   - F-909's "every rendered frame" is checked "against an independent reference"
     (`docs/adr/0001-architecture.md:345`), not Manim.
   - F-915 compares against fresh captures (`:344`).

   Three things go uncompared:
   - partial drawing of an adaptively sampled artist under
     `Create`/`Uncreate`/`Write`/`ShowPassingFlash` (F4a, pacing x = −4.49 against 0);
   - `Create(ax)`/`Write(ax)` against `Create(Axes())` (F4b, the lag slot: 0.96);
   - `Transform(ax, ax2)` keyed by tick value against Manim's pairing by index (F4c).

   For D17 this matters: pacing and timing are what a viewer sees, and none of the three is in
   F-1008 (`docs/scope.md:238`).
3. **Baselines.** Admitting reviewed baselines is sound; Manim does the same. The guard is
   stated: a baseline closes no `F-*` (ADR 0002 `:39-41` and `:95-99`; `CONTRIBUTING.md:62-63`).
   The harness cannot enforce it, because nothing links a visual test to an `F-*`. One
   obligation could slip into a baseline: F-914's "pixel comparison"
   (`docs/adr/0001-architecture.md:343`) names no oracle. PoC 2 used a capture with the frame
   against one without it (an invariant). State that.

   Other golden values:
   - F-917's source hashes. They are change detectors by design, paired with the F-906 matrix
     (`docs/plan.md:511-512`).
   - The count of 73 in `tests/test_parity_surface.py:91`.
   - The inverted defect probes.

   None closes a behavioural `F-*` on its own.
4. **The benchmark's `update`.** Mostly yes: it is `Scene.update_to_time` plus the reads that
   trigger the camera's lazy rebuilds. Static mobjects are drawn once, outside the per-frame
   timers, as in Cairo, and rasterisation is excluded. Three defects:
   - it reads each leaf once per ancestor (B3);
   - it records no setup (B4);
   - it writes TeX to `./media` (B13).

   The harness runs on 0.22.0 too (my run).
5. **Logging.**
   - **Off:** a disabled DEBUG call costs 60 ns, but INFO is not disabled (B6).
   - **On:** the file sink alone takes the console's warnings, and a bad path raises
     mid-render (B7).
   - **Manim's loggers:** untouched.
   - **pytest:** its options keep working (pytest 9.1.1).
   - **Import time:** an unknown level, or a numeric one, raises.

### C. Consistency across all documents

**C1 — major. F-705 and the invalid-input table set different warning frequencies.**
- F-705 says "warns once per artist per data change" (`docs/scope.md:178`), and so does D27
  (`docs/grill-log.md:757-758`).
- The table says "once per artist per rebuild" for paths (`docs/scope.md:300`) and for points
  and regions (`:304`), as does `docs/plan.md:286-287`.
- An animated range rebuilds every frame.

This is the residue of the 2026-10-24 Claude finding C11. **Fix:** change the scope table and
the plan to "per data change", and define what one data change is for an animated range, for
example one per play.

**C2 — major. F-203 contradicts the defaults table and D23.**
- F-203: "A range that excludes zero does not clamp the origin to the range boundary"
  (`docs/scope.md:96`).
- The defaults row: "An axis whose range excludes 0 | sits at the range edge | same"
  (`:263`). D23 keeps that placement "because they are defaults and not defects"
  (`docs/grill-log.md:631-634`).
- The audit calls the same clamp defect 13 (`docs/defect-audit-0.21.md:235-251`), and the
  traceability table maps defect 13 to F-203 (`docs/scope.md:441`).

**Fix:** a new ADR that rewords F-203 as "the axes cross where Manim puts them by default;
the crossing is a parameter", and reclassifies defect 13 as "kept by default, fixed by a
parameter".

**C3 — major. The scope's paper check and ADR 0001 disagree on extending `Payload`.**
- `docs/scope.md:391-394`: "The branch itself, and the payload fields it needs, ship in 0.1 …
  because adding a field to a frozen return type in 0.2 is exactly the breaking change this
  exercise exists to prevent."
- `docs/adr/0001-architecture.md:229-231` and D26 (`docs/grill-log.md:720-721`): the region
  branch is "declared, not complete", and "Adding an optional field with a default … is not a
  breaking change".

Both documents are frozen, and the precedence rule does not order them (A5). **Fix:** amend
the paper check to the ADR's position: the field values arrive in 0.2 as optional fields.

**C4 — minor. Two decisions are superseded silently.** D26's "Synchronisation updaters only
where something can move" (`docs/grill-log.md:741-745`) narrows D21's "Every library mobject
carries an updater without `dt`" (`:588-591`) without saying "Revises D21". `docs/README.md:22`
promises that a later decision names what it supersedes. D6's per-artist policy (`warn`,
`raise`, `ignore`; `docs/grill-log.md:125-126`) appears nowhere in scope, which fixes one
behaviour per surface (`docs/scope.md:298-304`). **Fix:** add both supersession notes.

**C5 — minor. `ax.x.labels.at(2.0)` survives in two living documents.** It appears at
`docs/plan.md:407` and `docs/parity-survey.md:418`. Since D27 (`docs/grill-log.md:763-766`),
`labels` names the custom labels of `add_labels` (`docs/scope.md:159`), so the example now
styles the wrong thing. **Fix:** change it to `ax.x.numbers.at(2.0)`.

**C6 — minor. The parity survey promises 0.1 capabilities that no `F-*` holds.**
- `SymmetricalLogLocator` "ships with symlog" (`docs/parity-survey.md:280`), but F-403
  (`docs/scope.md:124`) and ADR `:71-72` list no symlog locator. That leaves a symlog axis
  without a suitable default locator (Blocker 4).
- Legend "placement and a box in 0.1" (`:386`) disagrees with F-808 (0.2: "box styling",
  `docs/scope.md:198`) and with F-801 (no placement, `:191`).
- "set border" (`:382`), "Axis on/off" (`:246`) and "an optional generation window" (`:357`)
  have no `F-*`.

**Fix:** retag these survey rows, or add the `F-*` rows through a new ADR.

**C7 — minor. F-912's data-channel animation class has no home.** F-912 lists "the
data-channel animation as a public class" (`docs/scope.md:215`). `animations.py` lists
`DrawAxes, TraceCurve, ShowPoints, Morph` (`docs/adr/0001-architecture.md:85`). Codex's D1
raised this on 2026-10-24 (`docs/reviews/2026-10-24-codex.md:130`), and it is still open.
**Fix:** decide whether native `.animate` (D21) replaces the class, and drop it or add it.

**C8 — minor. Some counts are wrong.**
- `TODO.md:76` says "maps all 18". The table has 20 rows (`docs/scope.md:427-448`): 19
  confirmed defects plus the dropped 14.
- `docs/defect-audit-0.21.md:364` says "seven suppressions". `grep -n "# type: ignore"` finds
  six, at lines 99, 101, 103, 144, 163 and 179, and found six at f57b286 too.
- `:34` says "Defect 11 has no probe". 15e has none either; there is no `test_d15e` in
  `tests/test_defect_audit_0_21.py`.
- ADR `:360-361` says "all seventeen frames the mechanism reads". The frozen design reads more
  (E6).

These counts hold: 121 rows; 108 at tier 0.1 (106 plus F-503 and F-921); 16 modules (9 plus
7); D1-D27 with no gaps; 73 and 43 parity names; 20 defect rows; PoC 4's 296 tests (228
behavioural plus 68 guards).

**C9 — minor. Some sources sit outside the scope's own legend, and one is misattributed.**
`docs/scope.md:22-29` defines four kinds of tag. Several 0.1 rows cite others:
- F-114 cites only "stress case 3" (`:55`);
- F-1003 cites "PLAN, round 7", F-1004 "PLAN risk" and F-1006 "PLAN" (`:233-236`);
- F-1001 cites "PLAN gate", F-1007 "task/01, task/02", and F-105 "F-1001".

"PLAN" is the file name from before the relayout. F-112 cites D5 (`:52`), which says nothing
about ownership; the rule comes from D11's amendment (`docs/grill-log.md:322-324`). **Fix:**
add the tags to the legend (stress case n → paper check §n; PLAN → `docs/plan.md`; round n →
the plan review log) and cite D11 for F-112.

**C10 — minor. ADR 0002 misdescribes Manim's logger, and the citation test does not cover
it.**
- ADR 0002 `:83-85` says Manim puts its console handler on the root logger.
  `_config/logger_utils.py::make_logger`, `:99-106`, puts it on the `manim` logger, with
  propagation off, and on the root only when the root has no handlers.
- That citation is the ADRs' only `file.py::Symbol` citation, and it is unguarded:
  `tests/test_cited_symbols.py:17-21` scans `plan.md`, `scope.md` and `grill-log.md`, while
  F-1003 says "the design documents" (`docs/scope.md:233`).

**Fix:** correct the sentence; add the ADRs to `DOCS` and `logger_utils.py` to
`MODULE_OF_FILE`.

*Checked without a further finding:*
- every `F-*` referenced anywhere (121 distinct) is defined;
- every `D*` cited exists;
- the From column's D-numbers match their text, apart from F-112 (C9) and weak citations of
  D5 for F-103 and F-108, of D6 for F-305 and F-306, and of D4 for F-902, where the plan
  holds the rule;
- every Markdown link resolves. Six backticked paths do not: `tests/visual/_out/` (generated,
  intended); `poc/poc1/media` and `poc/media` (generated, known); the two PoC 1 PNGs (A2);
  and `docs/architecture/decisions/` (deliberate).

### D. Readiness of the frozen 0.1 scope

**D1.** See Blocker 4 and Table D.

**D2 — major. No document names the warning mechanism.**
- F-705 warns (`docs/scope.md:178`), F-917 warns at import (`:220`), and F-920 says "tests
  raise and a render warns once" (`:223`).
- No document says whether a warning is `warnings.warn`, with which category, or `logging`.
  A grep for `warnings.warn|UserWarning|log.warning` over scope, ADRs, the plan and the grill
  log finds nothing.
- F-920's "tests raise" needs a mechanism, for example a library warning category that the
  pytest configuration turns into an error.
- If the channel is `logging`, B7 applies.

**Fix:** one category, `ManimPlotsWarning(UserWarning)`, with
`filterwarnings = ["error::manim_plots.ManimPlotsWarning"]` in the tests.

**D3 — major. `Transform` between two different systems is undefined.**
- Keyed alignment (F-908, `docs/scope.md:211`) pairs ticks by `key`, and a key is a function
  of "the locator's configuration" (D25, `docs/grill-log.md:698-701`).
- Keys from `MaxN` and from `Multiple` are not comparable, and nothing interpolates a Linear
  scale into a Log one.
- PoC 4 established matching systems only ("Heterogeneous frames, locator replacement … are
  not established", `docs/poc/poc4-keyed-alignment.md:56-58`).
- `Transform(linear_ax, log_ax)` is a natural pedagogical idiom.

**Fix:** decide whether it raises, cross-fades or interpolates, before the keyed-alignment
task.

**D4 — major. `ax.plot(f, a=tracker)` collides with Manim's `**kwargs`.**
- The plan and D22 spell a live parameter as `ax.plot(f, a=tracker)` (`docs/plan.md:252`,
  `docs/grill-log.md:612-614`).
- Manim's `coordinate_systems.py::CoordinateSystem.plot`, `:640`, has the signature
  `(function, x_range=None, use_vectorized=False, colorscale=None, colorscale_axis=1, **kwargs)`.
  Its `**kwargs` go to the curve as style. F-1009 promises plot's keywords (`docs/scope.md:239`).
- Nothing says how a function parameter is told apart from a style keyword (a parameter named
  `color`, for example), or what `a=` binds when `f` has no `a`.

**Fix:** parameters are the names in `inspect.signature(f)` beyond the first; a collision with
a VMobject keyword raises.

**D5 — major. Animating a range into a reversed one passes through an empty range.**
- F-209 makes reversed ranges legal (`docs/scope.md:102`), and F-909 animates them (`:212`).
- Animating (0, 10) to (10, 0) interpolates linearly to lo = hi = 5 at alpha 0.5
  (`poc/poc4/model.py:379-382`).
- F-409 makes an empty range raise (`docs/scope.md:130`), and the conversion divides by the
  span (`poc/poc4/model.py:331`).
- A flip therefore raises at its midpoint, or not, depending on whether a rendered alpha hits
  0.5 exactly. The pool samples at four times the frame density, so it usually does.

**Fix:** define the transient empty range (no ticks; no conversion that frame), or reject the
animation at begin.

**D6 — major. The aspect lock (F-205) is over-determined.**
- `x_range`, `y_range`, `x_length` and `y_length` are four independent numbers
  (`docs/scope.md:98-99`; defect 4, `docs/defect-audit-0.21.md:117-128`).
- A locked aspect removes one degree of freedom, so one of the four must yield.
- No document says which, nor what happens when the user passes all four and a lock.

**Fix:** name the quantity that yields, as matplotlib's `adjustable='box'|'datalim'` does.

**D7 — minor. No 0.1 API removes an artist from its system.** F-112 raises on rebinding
(`docs/scope.md:52`), so moving an artist needs an unbind, and none exists. D11's
`attach`/`detach` "remain as the underlying contract" (`docs/grill-log.md:322-323`) but appear
nowhere in scope. "Detached" now also names the lifecycle states **R** and **S**
(`docs/adr/0001-architecture.md:274-277`). **Fix:** specify `ax.remove(artist)`, and keep
"detach" for one meaning only.

**D8 — minor. `set_ticks` pairs are undecided.** A3.3's approved spelling uses pairs:
`ax.x.set_ticks([(0, "start"), (5, r"\pi")])` (`docs/api-sketch.md:106-108`). F-404 makes an
entry a triple (`docs/scope.md:125`), and a wrong arity raises (`:284`). Codex raised this on
2026-10-24 (`docs/reviews/2026-10-24-codex.md:121`). **Fix:** say that a pair means the major
level, or that it raises.

**D9 — minor. Only one star-exported name is given.** F-1009 names `CartesianAxes` for
`from manim_plots import *` (`docs/scope.md:239`). D12's rule against collisions
(`docs/grill-log.md:341-344`) applies just as much to the plane (F-921, `docs/scope.md:224`)
and to the library's tracker, which "keeps `ValueTracker`'s API"
(`docs/grill-log.md:369-370`). Their star-exported names are not given. **Fix:** list `__all__`.

**D10 — minor. `unit_size` against the default length is undecided.** F-204 says a unit size
is "honoured … or rejected" (`docs/scope.md:97`). Manim's default `x_length` is 12
(`Axes.__init__`, `:1935`), and with a length set its `NumberLine` ignores `unit_size`
(`number_line.py::NumberLine.__init__`, `:231-235`). Nothing says whether
`axis_config={"unit_size": 3}` without `x_length` wins over the default length, or raises.
**Fix:** decide.

**D11 — minor. The decimal-places rule is not stated.** The defaults table says only "follow
the step" (`docs/scope.md:261`). Manim counts characters after the point in `str(step)`
(`number_line.py::NumberLine._decimal_places_from_step`, `:668-672`). Probe: `1` → 0,
`1.0` → 1, `0.25` → 2, `1e-05` → 0. A formatter that sees only values (ADR `:179-180`)
cannot reproduce `1.0` → `"1.0"` unless the axis configures it from the step string. **Fix:**
state the rule, and say whether `1e-05` → 0 places (every label "0") is copied or fixed.

**D.3 — what the implementation must settle that no `F-*` names:**
- the `__getattr__` shim on library mobjects (B1);
- the warning channel (D2);
- heterogeneous `Transform` (D3);
- how function parameters are declared (D4);
- the unbind API (D7);
- `__all__` (D9);
- where TeX caches go during tests (B13);
- the precedence rows of the lifecycle table (Blocker 2).

**D.4 — conflicting rows:**
- F-110 against F-918 and F-915 (Blocker 3);
- F-705 against the invalid-input table (C1);
- F-203 against the defaults table (C2);
- F-209 and F-909 against F-409 (D5);
- F-404 against A3.3 (D8);
- the paper check against ADR §3 (C3).

#### Table D — under-specified `F-*`

`core/`, the first task:

| F-* | What is missing (code or test) |
|---|---|
| F-114 payload | no `Payload` type in ADR §3: constructor, defaults (segments for an unsplit path), dtype, `kind` as a `Literal`, `d` (E3); the exception type |
| F-105, F-109 nodes | the `Node` signature (D6's prose against F-109's dimensionality); the affine-collapse tolerance |
| F-201, F-202, F-207 | the round-trip tolerance; Newton's convergence criterion and iteration cap; the rule for which branch is returned ("documents which branch" without a rule); the off-plane tolerance; the exception type and the message naming "the first invalid index" |
| F-203, F-205 | F-203 contradicts the defaults table (C2); which quantity yields under an aspect lock (D6) |
| F-209 + F-409 | a transiently empty animated range (D5); what "empty" means (exactly lo == hi?) |
| F-301 | the Log base: valid values, and whether a base below 1 (a decreasing scale) is allowed; **SymLog: parameters and formula** |
| F-302, F-305 | sample count, placement on an infinite domain, round-trip tolerance, exception |
| F-306 | strict or non-strict ordering; tolerance |
| F-311 | `eps`; both ends outside the domain; a reversed range; no `minpos` (E4) |
| F-402, F-403 | `Multiple`: the boundary tolerance, that is whether `3*0.1 = 0.30000000000000004` counts as inside `[0, 0.3]`; **MaxN's algorithm** and the meaning of `n` against `max_ticks`; `Log`: subs default, non-integer bases, thinning; `MinorCount`: meaning of `n`, ticks outside the outer majors, data space or scaled space |
| F-404, F-405 | pairs against triples (D8); which key function decides a collision between two explicit entries (the generated locator's or `Fixed`'s); the key namespace when `Fixed` feeds both levels (ADR `:163-164`) |
| F-408 | the formula from font size to `max_ticks` |
| F-413 | the digit count of the canonical key; whether a render raises too |
| F-501, F-504 | dispatch (Blocker 1) |
| F-502 | signatures: decimal (D11), format string (`str.format` or `%`), LaTeX/scientific form, SI prefixes (µ in math mode) and the unit parameter |
| F-506 | the tolerance at the range ends |
| F-704, F-108 | **the sampler's error criterion** (pixels at which resolution), initial count, maximum depth or count, cost under `use_vectorized=False` |
| F-705 | the space in which a "magnitude grows past the viewport" is measured; warning frequency (C1) |
| F-706, F-806 | the order of clipping and smoothing; the units of a dash pattern (local or scene; Manim counts dashes) |
| F-707 | `at(t)` shapes, and what it means for scatter and region sources |
| F-710 | the table of refused topology pairs |
| F-110, F-911 | callable bindings (Blocker 3); binding a scalar `ValueTracker` to a range pair |
| F-914 numerics | the affinity tolerance; the densify count |
| F-919 | the event and action vocabularies; a compound state (owners, origin, pending target, pending refresh, pending data); precedence (Blocker 2) |
| F-920 | the mechanism behind "tests raise" (D2) |

`mobjects/`, briefly:

| F-* | Missing |
|---|---|
| F-204 | `unit_size` against the default length (D10) |
| F-505, F-508 | the collision test (padding; which label is "later" on a reversed axis); parameter names |
| F-603 | `at(value)` for a value with no part: raise or `None` |
| F-605, F-606 | what a "fractional offset" is a fraction of; the API for the mirrored axis |
| F-702, F-918 | the overload set; function parameters (D4) |
| F-708 | unbinding (D7); legend membership after a `ReplacementTransform` transfer |
| F-801, F-803 | the legend's default placement and order; the cycle's colours after white |
| F-804 | the names of the line-style and marker enums |
| F-908, F-909 | heterogeneous systems (D3) |
| F-912 | the `DrawAxes` order; the data-channel class (C7) |
| F-915 | "live function" (Blocker 3); the query on 0.22.0 (E6) |
| F-921 | which keys of `background_line_style` map to what; Manim's faded lines (`faded_line_ratio`) |
| F-922 | the hash of derived state |
| F-1009 | Manim keys that raise, absent from F-1008 (F2) |

### E. Soundness of the frozen architecture for implementation

**E1.** Table E.1 below.

**E2 — major. The protocols' data members reject frozen value objects.** ADR 0001 §3 declares
`domain`, `closed` and `increasing` (`docs/adr/0001-architecture.md:103-105`), `is_affine`
(`:198`), and `lower` and `upper` (`:207-208`) as plain, settable attributes. Probe: a
`@dataclass(frozen=True) class Log` passed where `Scale` is expected gives
`error: Argument 1 to "use" has incompatible type "Log"; expected "Scale"` and
`Protocol member Scale.closed expected settable variable, got read-only attribute`. "A scale is
a value object" (`:129`) cannot be written as a frozen dataclass and pass `mypy --strict`.
**Fix:** a new ADR declaring these members as read-only `@property` members of the protocols.

**E3 — major. `Payload` has no type.** ADR §3 lists `Payload` among the frozen public
contracts and shows only the protocols that return it (`:194-234`). Its fields are in
`docs/scope.md:57-65` and its validation in `:278-293`, but its constructor, defaults, dtype
and the type of `kind` are given nowhere. **Fix:** add the dataclass signature to ADR §3.

**E4 — major. 0.2's autoscale would break `Scale`.**
- `limit_range(self, lo, hi)` (`:109`) drops the third argument of the method the survey
  quotes: `ScaleBase.limit_range_for_scale(vmin, vmax, minpos)`
  (`docs/parity-survey.md:260`).
- `minpos` is how a log axis autoscales to data containing zeros, and autoscale is 0.2
  (`docs/scope.md:404`). Adding the parameter then breaks every third-party scale written
  against the two-argument form.
- The scope promises "Nothing in 0.2 may require breaking a 0.1 contract"
  (`docs/scope.md:18`). F-311's `eps` is undefined for the same reason.

**Fix:** a new ADR changing the method to `limit_range(lo, hi, minpos)`.

**E5.** See Blocker 2. E.3 answer: the table determines every other cell I checked. For
example, Homotopy → **S**, a container moving an **R** artist writes once, and a copy of **T**
is an unregistered **A**. It agrees with F-903…F-907, F-919 and D24 apart from the two cells
of Blocker 2.

**E6 — major. The frame D26 adds to the stack contract changed in 0.22.0.**
- F-915 reports synchronisation updaters to Cairo's moving test "only when the play being
  compiled involves their system … The play's animations are read from that frame"
  (`docs/grill-log.md:741-745`). That frame is `scene.py::Scene.get_moving_mobjects`.
- In 0.21.0 its test calls `len(mob.get_family_updaters()) > 0` (`:937-946`). In 0.22.0 it
  reads `len(mob.updaters) > 0` and recurses into submobjects (`:963-974`, 0.22.0).
- Probe: a mobject whose `get_family_updaters()` returns a dt-free updater, while
  `.updaters` is empty, prints `moving=True` on 0.21.0 and `moving=False` on 0.22.0. A plain
  `add_updater` is moving on both.
- An F-915 built by overriding the 0.21.0 query therefore freezes bound artists on 0.22.0,
  which is the G5 defect.
- ADR 0001 `:360-361` and `docs/plan.md:525-527` claim byte-identical frames; that holds for
  PoC 4's 17, not for this one.
- In my comparison, 66 of PoC 4's 68 pinned symbols are identical. The two that differ are
  `Scene.get_moving_mobjects` and `CairoRenderer.play`. Of 20 further symbols the design relies
  on, only `CairoRenderer.add_frame` differs.

**Fix:** add the frame to F-917's inventory with both queries, and report through `updaters`,
which both versions read (0.21.0 through `get_updaters`).

**E7 — minor. Two parts are larger than their requirements.**
- The 0.1 invalid-input table demands full topology validation for regions: cell index range,
  repeated corners, winding consistency (`docs/scope.md:289`, `:293`). No 0.1 producer of a
  region exists; it is "implemented later" (`:55`).
- ADR 0002's sinks driven by environment variables (`src/manim_plots/__init__.py:12-36`)
  duplicate pytest's own options and bring the side effects of B6 and B7.

Keep `Bounds.contains` general, but clip boxes only in 0.1. **Fix:** a new ADR deferring the
topology rows; for the logging, keep only the `NullHandler` unless the sinks earn their cost.

**E.2, the 0.2 stress test.**
- Polar fits (`Node` is private).
- Date axes fit (adapter, keys, formatter over the whole list).
- Region sampling fits through optional fields, once C3 is resolved.
- A second scale fits (two Maps, one frame).
- 3D needs a volumetric frame; the frame is internal, so nothing public breaks.
- Autoscale **breaks** `Scale` (E4).

**E.4, stack frames.** All 17 PoC 4 frames are byte-identical between 0.21.0 and 0.22.0. The
method is PoC 4's own: `inspect.getsourcelines` and SHA-256, and my 0.21.0 recomputation equals
`poc/poc4/manim_contract.json`.

| Frame | First line 0.21.0 → 0.22.0 | Body |
|---|---|---|
| `Animation.begin`, `Transform.begin`, `AnimationGroup.begin`, `Succession.begin` | 197, 200, 86, 238 (unchanged) | identical |
| `Animation.finish`, `AnimationGroup.finish`, `Succession.finish` | 216, 102, 246 (unchanged) | identical |
| `Mobject.shift`, `apply_points_function_about_point`, `rotate`, `scale`, `stretch`, `apply_matrix` | 1262→1382, 1569→1689, 1344→1464, 1287→1407, 1443→1563, 1489→1609 | identical |
| `VMobject.apply_function`, `VMobject.set_anchors_and_handles` | 1218, 821 (unchanged) | identical |
| `Scene.update_to_time`, `Scene.play_internal` | 1700→1714, 1364→1384 | identical |
| **`Scene.get_moving_mobjects`** (D26) | 899→925 | **differs** (E6) |

**E.5 — least architecture.** Apart from E7, I found nothing larger than its requirement.
Sixteen modules, no layer of ports, Protocols rather than ABCs, and polling rather than
subscription all fit.

#### Table E.1 — module ↔ `F-*`

The `F-*` marked `†` are not named by number in ADR §2 (`docs/adr/0001-architecture.md:62-86`);
the owner shown is inferred from the module's description. ADR §2 annotates by family, as
`(F-4xx)`, `(F-5xx)` and `(F-7xx)` on `ticks.py`, `formatters.py` and `sources.py`. Read
literally, that puts Manim-layer rows such as F-408, F-411, F-412, F-505, F-508, F-701, F-702,
F-708 and F-709 in core modules. The table places them by what they need.

| Module | Owns |
|---|---|
| `core/payload.py` | F-114; F-1006's payload rows† |
| `core/nodes.py` | F-105, F-109, F-914 (frame numerics); F-201†, F-202†, F-203†, F-205†, F-207†, F-208†, F-209† |
| `core/scales.py` | F-301, F-302, F-303, F-304, F-305, F-307, F-311 |
| `core/ticks.py` | F-401, F-402, F-403, F-404, F-405, F-406, F-407, F-409, F-410, F-413, F-414, F-920 (plan); F-306† |
| `core/formatters.py` | F-501, F-502, F-503, F-504, F-507; F-506† |
| `core/sources.py` | F-703, F-704, F-707, F-710 (`resample_like`); F-104†, F-108†, F-113†, F-918† (sampling policy) |
| `core/shape.py` | F-106, F-705, F-706, F-806, F-914 (densify); F-107† |
| `core/params.py` | F-110, F-911; F-102† (dirty marking) |
| `core/lifecycle.py` | F-919; F-903†, F-904†, F-905†, F-907†, F-111† |
| `mobjects/leaves.py` | F-901, F-902; F-102† (the getter), F-807†, F-922† |
| `mobjects/context.py` | F-917; F-904†, F-915† (stack reads), F-1007† (pin check at import) |
| `mobjects/system.py` | F-908, F-909, F-914 (the grid), F-921; F-101†, F-103†, F-112†, F-204†, F-206†, F-702†, F-708†, F-709†, F-915†, F-916†, F-1009† |
| `mobjects/axis.py` | F-601…F-609; F-408†, F-411†, F-412†, F-505†, F-508† |
| `mobjects/artists.py` | F-701; F-802†, F-803†, F-804†, F-805† |
| `mobjects/legend.py` | F-801 |
| `mobjects/animations.py` | F-912 (missing the data-channel class, C7); F-710† (`Morph`) |
| tests and the gate | F-906 (matrix), F-1001 (`tests/benchmark/`), F-1003, F-1004, F-1006; F-1002 and F-1005 cut across every module |
| **no owner** | **F-1008**: no document or task produces "the docs" (H) |

Every module owns at least one `F-*`, and every tier-0.1 row has an owner except F-1008. No
module names the F-2xx family (mapping), most of F-1xx, or the Manim-layer mechanisms F-915,
F-916 and F-922.

### F. Closeness to Manim (D17)

#### Table F.1 — defaults

Values are from 0.21.0. Manim's default frame is 14.22 by 8.

| Setting | Our docs (`docs/scope.md`) | Manim 0.21.0 | Match |
|---|---|---|---|
| Ranges when omitted | `[-7,7,1]`, `[-4,4,1]` (`:252`) | `CoordinateSystem.__init__`, `:132-150` | yes |
| Lengths | `round(frame_width)-2`, `round(frame_height)-2` (`:253`) | `Axes.__init__`, `:1935-1936` (evaluated once, at import) | yes |
| `tips` | `True` (`:254`) | `Axes.__init__`, `:1940` | yes |
| Two-element range | step 1 (`:255`) | `CoordinateSystem.__init__`, `:132`, `:139-140` | yes |
| Tick positions | `x_min + k·step` (`:256`) | `NumberLine.get_tick_range`, `:345-353`: `x_min + k·step` only if the range excludes 0 (`:346`); otherwise anchored at 0 (`:352-353`) | **no** (F1) |
| End tick under a tip | dropped (`:257`) | `get_tick_range`, `:341-342` | yes |
| Tick and number at the crossing | none (`:258`) | `Axes.__init__`, `:1948`, `:1981`, `:1988`; a `LogBase` axis keeps it, `:1983` | yes (LogBase case unstated) |
| Tick shape | straddles, 0.1, ×2 (`:259`) | `NumberLine.__init__`, `:148`, `:150`; `get_tick`, `:322` | yes |
| Numbers | off, `font_size=36` (`:260`) | `NumberLine.__init__`, `:161-162` | yes |
| Decimal places | follow the step (`:261`) | `_decimal_places_from_step`, `:668-672`, by `str(step)` | rule unstated (D11) |
| Label direction | x `DOWN`, y `LEFT` (`:262`) | `NumberLine.__init__`, `:163`; `Axes.__init__`, `:1953` | yes |
| Range excluding 0 | axis at the range edge (`:263`) | `Axes._origin_shift`, `:2403-2408` | yes (F-203 says otherwise, C2) |
| Curve outside the viewport | drawn (`:264`) | `CoordinateSystem.plot`, `:640`: no clip | yes |
| Colour of `plot` | white (`:265`) | VMobject stroke `#FFFFFF` (probe) | yes |
| `plot_line_graph` | `PURE_YELLOW` (`:266`) | `Axes.plot_line_graph`, `:2308`; `#FFFF00` (`manim_colors.py:156`) | yes |
| Colliding labels | overlap (`:267`) | defect 11 | yes |
| Tick numbers | `DecimalNumber` (`:268`) | `NumberLine.get_number_mobject`, `:448-458` | yes |
| `add_labels` strings | `Tex`, text mode (`:269`) | `NumberLine.add_labels`, `:614-615`, only with the default `MathTex` constructor | yes |
| `scaling: LogBase()` | range in exponents (`:270`) | `NumberLine.__init__`, `:198` | yes |
| `axis_config` keys | `NumberLine.__init__` (`:271`) | `NumberLine.__init__`, `:141-169`, also accepts `rotation`, `length`, `label_constructor` and VMobject `**kwargs` | Manim column yes; "parity" no for the keys that raise (F2) |
| *missing:* centring | — | `Axes.__init__`, `:2002-2007`: the midpoint of each range sits at the scene origin | no row |
| *missing:* line and tip | — | `stroke_width` 2.0, `tip_width` and `tip_height` 0.35, `line_to_number_buff` 0.25 (`inspect.signature(NumberLine.__init__)`); y-axis rotation 90° (`:1952`) | no row |

**F1 — major. The tick-position row misstates Manim, and its "fix" is not an audited defect.**
- Probe: `[0.001, 6, 1]` → 0.001…5.001 and `[0.5, 5, 1]` → 0.5…4.5, but `[-2.5, 3, 1]` →
  −2, −1, 0, 1, 2, 3, and `[-7, 7, 1]` → integers.
- So Manim already ticks at integer multiples whenever the range contains 0, which is the
  default case (`number_line.py::NumberLine.get_tick_range`, `:345-353`).
- D23 lists "ticks are integer multiples of the step, not offsets from `x_min` (F-402)" among
  the defect fixes (`docs/grill-log.md:627-628`). But defect 1 is float accumulation
  (`docs/defect-audit-0.21.md:62-77`), and F-402 bans `np.arange` over a step
  (`docs/scope.md:123`). `x_min + k·step` with integer `k` accumulates nothing.
- The difference, for a range excluding 0 whose `x_min` is off the step grid, is therefore not
  a defect by D23's own rule (`docs/grill-log.md:623-625`). The table is the oracle of the
  parity test (`docs/scope.md:248`).

**Fix:** correct the Manim column. Then, through a new ADR, either keep Manim's anchor (and
give `Multiple` an `anchor`, which changes `ticks.py` in the first task) or record the
difference as deliberate in F-1008.

**F2 — minor. The defaults table lacks rows, and a raising key is not listed as a
difference.** The table has no rows for centring, stroke width, tips or the label buffer (see
Table F.1). The `axis_config` row is "parity", yet Manim keys outside the 20 honoured ones
(`rotation`, `label_constructor`, `stroke_color`, `stroke_opacity`) raise, and F-1008's list
(`docs/scope.md:238`) does not mention it. **Fix:** add the rows; list "unknown `axis_config`
keys raise" in F-1008.

**F3 — minor. The spelling holds, with one signature that changed.** All 43 0.1 names exist on
both versions: `tests/test_parity_surface.py` passed in all four cells. Their signatures are
identical (`sigs/dump_sigs.py` on both versions), except `NumberLine.p2n` and
`point_to_number`. Those changed from `(point: Point3DLike) -> float` in 0.21.0 to
`(point: Sequence[float] | Sequence[Sequence[float]] | np.ndarray) -> float | np.ndarray` in
0.22.0. The docs do not say which `mp` follows; D27's array rule implies 0.22.0's. **Fix:** say
so in F-1009.

**F4 — major. The mechanism differs visibly from Manim in four places F-1008 does not list.**
F-1008's list is at `docs/scope.md:238`.
- **(a) Create pacing.** `vectorized_mobject.py::VMobject.pointwise_become_partial` splits by
  curve index (`:2034`, `:2046-2047`), so `Create`, `Uncreate`, `Write` and
  `ShowPassingFlash` progress by sample count, not by x.
  - Probe: the same sine curve, refined on [−7, −3], is drawn to x = −4.49 at alpha 0.5,
    against x = 0.00 for Manim's uniform `ax.plot(np.sin)`.
  - Any adaptive sampler (F-704) shifts the pacing. Codex raised this as B3 on 2026-10-24
    (`docs/reviews/2026-10-24-codex.md:86`), and it is not closed.
- **(b) The hidden frame's lag slot.** `Create` has `lag_ratio=1.0` (`creation.py::Create.__init__`,
  `:170`) and `Animation.get_sub_alpha` spreads the run over the family (`:384-387`).
  - `Axes()` has 24 point-bearing members, so with the frame added the last visible leaf
    finishes at 0.96 of the run.
  - D27 places the frame last (`docs/grill-log.md:773-774`). The 2026-10-24 Claude B7 asked to
    record the slot in F-1008 (`docs/reviews/2026-10-24-claude.md:413-414`), and that was not
    done.
- **(c) `Transform(ax, ax2)`** pairs ticks by key (D21, `docs/grill-log.md:577-583`). Manim
  pairs family members by index.
- **(d) Registration is not parenting.** `ax.add(curve)` registers (F-708, F-709,
  `docs/scope.md:181-182`), whereas in Manim it makes `curve` a submobject. Ported code that
  ran `ax.add(graph)` and then `FadeOut(ax)` or `Create(ax)` leaves the graph untouched.

**Fix:** add (a)-(d) to F-1008. For (a), alternatively make an artist's partial drawing follow
its parameter, which is `TraceCurve`'s job (arch-crew's question in section G).

The answer to F.3 also includes E6: F-915 on 0.22.0.

### G. Closure of the earlier reviews

| Review / item | Status | Closed by | Missing |
|---|---|---|---|
| Codex B1: Map can produce a payload its validator forbids | closed | D26 "Map owns validity" (`docs/grill-log.md:722-724`); ADR §3 `:226-228`; `docs/scope.md:67-83` | — |
| Codex B2: field values absent | partially | D26 (`grill-log.md:720-721`); ADR `:229-231` (optional fields later) | the paper check still says the opposite (C3); `at(t)` shapes for point and region sources (Table D) |
| Codex B3: locator identity across operations | closed, with a residue | D25 (`grill-log.md:692-701`); F-401, F-413 (`scope.md:122`, `:134`); ADR `:151-162` | key namespaces when `Fixed` feeds both levels; the merge's key function (Table D, F-405); locator replacement (D3) |
| Codex B4: pool schedule, late keys | closed, with a residue | D25 (`grill-log.md:702-708`); F-920 (`scope.md:223`) | the mechanism by which "tests raise" (D2) |
| Codex B5: lifecycle ownership | partially | D24 (`grill-log.md:641-690`); ADR §4 (`:287-322`); F-919 | Blocker 2; legend membership after a replacement transfer; the transfer is untested (PoC 4 measured it absent, `docs/poc/poc4-keyed-alignment.md:162`) |
| Codex B6: inverse guarantee | closed, with a residue | D26 (`grill-log.md:725-728`); F-201, F-207 (`scope.md:94`, `:100`) | tolerances, Newton's criterion, the branch rule (Blocker 4) |
| Codex B7: exceptions to "same signature and defaults" | partially | D23 (`grill-log.md:621-639`); the defaults table (`scope.md:243-271`); F-1009 | F1 (tick-position row); C2 (F-203); F2 (missing rows; the raising keys) |
| Codex B8: what F-1001 measures | closed in the spec, partially in the harness | D26 (`grill-log.md:735-740`); F-1001 (`scope.md:231`); ADR 0002 §2 | B3, B4 |
| Claude B1: when plot functions are evaluated | partially | D22 (`grill-log.md:602-619`); F-704, F-918, F-1001, F-1008 | F-110 still says "always dirty" (Blocker 3); "live function" undefined |
| Claude B2: which Manim default survives | partially | D23; the defaults table | F1, C2, F2 |
| Claude B3: lifecycle state × event table | partially | D24; ADR §4; F-919 | Blocker 2; its seven failing cells are now decided (Homotopy → **S**; `reverse_points`; detached moves once; attached copies; unregistered copies; plain target → **S**; pool leaves out of bounds) |
| Claude B4: F-917's pins on both versions | closed | D26 (`grill-log.md:729-732`); F-917, F-1007 (`scope.md:220`, `:237`) | new: E6 (a D26 frame differs in 0.22.0) |
| Claude B5: pool schedule | closed, with a residue | D25; F-920 | "tests raise" (D2) |
| Claude B6: `Source` types undefined | partially | D26 (`grill-log.md:712-721`); ADR §3 `:196-231` | `Payload`'s own type (E3); settable members (E2); `at` for scatter and regions |
| arch-crew finding 1: only `context.py` reads internals | closed | ADR §1 `:54-58`; F-917 for the rest | — |
| arch-crew finding 2: lifecycle state machine | partially | ADR §4; D24 | Blocker 2 |
| arch-crew finding 3: a home for frame numerics | closed | ADR §2 `nodes.py` (`:67-69`) | — |
| arch-crew finding 4: pool schedule | closed | D25 (4× and spares; corrected in its *Corrections*) | D2 |
| arch-crew pattern finding 1: flags → State | partially | ADR §4 table | Blocker 2 |
| arch-crew pattern finding 2: wrapping callables (Adapter or singledispatch) | **open** | — | Blocker 1 |
| arch-crew pattern finding 3: descriptors | closed | F-911 | — |
| arch-crew "simplify away `TraceCurve`" | **open** | no decision; F-912 keeps it (`scope.md:215`) | decide; F4a gives it a purpose (pacing by parameter) |
| arch-crew least-architecture check: cut the non-affine path first if 0.1 slips | open by design | none needed | a schedule lever (H) |
| arch-crew portfolio: differential "at every rendered frame" | partially | F-906 compares end states (`scope.md:209`) | B.7 answer 2 |
| arch-crew primary recommendation: a differential test per lifecycle cell | closed | ADR §4 notes `:320-322` | — |

### H. The implementation plan

**H1 — major. TODO's order measures the two known risks only after the Manim layer
exists.**
- The order is core → axis and frame → data plotting → legend → release (`TODO.md:131-136`).
- F-1001's scenario needs adaptive sampling, clipping, labels and the pool. PoC 4's 3.07 and
  3.73 ms excluded all four (`docs/plan.md:533-538`), so the gate is first measured late.
- The stack contract waits for "axis and frame", although E6 and Blocker 2 sit in it.
- The `ReplacementTransform` transfer was decided after PoC 4 measured its absence, and has no
  tested mechanism.

**Fix:** the order below adds an early pipeline benchmark (task 08), an early stack reader
(task 10) and an early end-to-end spike (task 11).

#### Table H — tasks from 06 to the first release

| Task | Modules and `F-*` | Depends on | Closing evidence | Gate |
|---|---|---|---|---|
| 06 core: payload, scales, params | `payload.py` (F-114, F-1006 rows), `scales.py` (F-301…F-311), `params.py` (F-110); TID251 config (B.2); `D417`; `--render` merge gate (B2) | Blockers 3, 4; E2, E3, E4 | one test per payload row (`docs/scope.md:278-293`); Hypothesis round trip and monotonicity with fixed anchors (ADR `:330-331`); F-305 falsification cases | `uv run python tools/check.py --render` |
| 07 core: ticks, formatters | `ticks.py` (F-401…F-414, F-920 plan), `formatters.py` (F-501…F-507) | 06; Blockers 1, 4; D8, F1 | keys stable across ranges and unique (Hypothesis, ADR `:333`); `Multiple(0.1)` exact (`:332`); merge order on reversed ranges; pool plan per composition type (`:336`) | same |
| 08 core: nodes, sources, shape | `nodes.py` (F-105, F-109, F-201…F-209 numerics, F-914), `sources.py` (F-104, F-703, F-704, F-707, F-710), `shape.py` (F-106, F-107, F-705, F-706, F-806) | 06; Blocker 4; D5, D6 | `p2c(c2p(x))` on every scale, affine frame (ADR `:330`); non-affine inversion raises; validity propagation; sampler against an analytic tolerance; **core pipeline benchmark** of 4 × 2 000 samples, both frame paths, in `tests/benchmark/test_core_pipeline.py` | same, plus `uv run pytest -m benchmark` |
| 09 core: lifecycle | `lifecycle.py` (F-919, F-903…F-907 transitions) | Blocker 2 | one unit test per table cell (ADR `:320-322`) | same |
| 10 Manim: context, leaves | `context.py` (F-917: pin sets for 0.21.0 and 0.22.0, including E6's frame; F-1007 warning; OpenGL refusal), `leaves.py` (F-901, F-902, F-903…F-907 applied) | 09; E6; B1 decision | contract test per version (in each `tools/check.py` cell); identity test (F-902); the F-906 matrix on plain leaves, `render` marker, in `tests/mobjects/` | `tools/check.py --render` |
| 11 Manim: system and frame | `system.py` (F-914 grid, F-201…F-208 API, F-915 on both versions, F-916 simulation, F-208 regression) | 08, 10 | F-914 pixel invariant with and without the frame; F-915 middle frames on both versions (render); **end-to-end F-1001 spike** without labels, `tests/benchmark/test_f1001.py` | `--render`; `uv run pytest -m benchmark` |
| 12 Manim: axis decoration, keyed `.animate` | `axis.py` (F-601…F-609, F-408, F-411, F-412, F-505, F-508), the keyed pool (F-908, F-909, F-920), F-921, F-1009 `axis_config` | 07, 11; D3, D11, F2 | parity test against Manim's own `Axes` for every defaults row (ADR `:342`); every rendered frame of F-909 against an independent reference; F-1001 with labels and a warm glyph cache | `--render`; benchmark |
| 13 Manim: artists | `artists.py` (F-701…F-710, F-704 keywords, F-918), registration (F-708, F-709, F-112), styles (F-803…F-807); `ReplacementTransform` transfer | 08, 12; D4, D7, F4 | F-906 matrix on artists (`tests/mobjects/`, render); late binding (F-918); a differential test of the transfer against a plain `Axes` scene | `--render` |
| 14 Manim: legend, animations | `legend.py` (F-801, F-802), `animations.py` (F-912, F-710 `Morph`) | 13; C7 | merge and split; `Morph` refuses the listed pairs; `TraceCurve` order | `--render` |
| 15 hardening | F-922 caching (render with caching on), F-1002, F-1005 (overloads), F-1003 (the ADRs in `DOCS`), F-1004, F-1006 on every surface, final F-1001 on both frame paths and the 1.5× check against `tests/benchmark/test_plain_manim.py` | all | full gate on both versions; benchmark JSON kept with the release | `--render` plus a recorded benchmark run |
| 16 documentation and first release | Sphinx; F-1008 differences and migration notes (F4, D22's `lambda x, n=n:`); changelog; `license-files`, URLs, absolute README links (B9-B11) | 15 | the docs build; `uv build`, with the LICENSE inside the sdist | merge `dev` → `main`, tagged |

**Where tests live.**
- Render tests: `tests/visual/` (baselines) and `tests/mobjects/`, marked `render`. Run them
  with `uv run pytest -m render`, and in the gate with `uv run python tools/check.py --render`.
- Benchmarks: `tests/benchmark/`. Run them with `uv run pytest -m benchmark` on one quiet
  machine; results go to `.benchmarks/`.

**Risks the order retires first:**
- the 4 ms margin (tasks 08 and 11);
- the stack contract on both versions (task 10);
- the lifecycle precedence (task 09);
- the replacement transfer (task 13, with a spike in task 11 if the maintainer prefers);
- heterogeneous `Transform` (decided before task 12).

TODO's order retires none of the Manim-layer risks before "axis and frame". The order above
retires each in the first task that can measure it.

## 5. Sound as-is

- Two layers. The core can be kept free of Manim with ruff alone (B.2, verified).
- The 17 stack frames are byte-identical across versions, and PoC 4's pin file reproduces on
  0.21.0.
- The payload validation table: row by row, testable.
- The gate: four checks in four cells, each on the Manim it names; it passes with `--render`
  on both versions.
- The visual harness's end frame is correct (`Scene.play_internal` resets `static_image`,
  0.21.0 `:1395`, 0.22.0 `:1415`), and Manim's constants are copied exactly.
- The benchmark harness runs on 0.22.0.
- A disabled DEBUG log call costs 60 ns; pytest's log options work with a sink.
- The counts: 121, 108, 16, D1-D27, 73, 43.
- Every `F-*` and `D*` reference resolves.
- 18 of the defaults table's 20 rows match Manim 0.21.0.
- The signatures of the 43 0.1 names are unchanged, apart from `p2n`.
- `py.typed` ships in the wheel, and `.hypothesis/` ignores itself.

## 6. Self-check

- [x] **The header names a commit.** `f129014c3729f01d2cbfefa75a5a3fb6317d2fc4`. After my run,
  `git status` shows this report as new, and also `docs/reviews/2026-10-28-final-codex.md`,
  the other reviewer's file, which I did not open. The `media/` directory one of my probes
  created was deleted (header).
- [x] **Every finding has an ID, a severity, a fix, and evidence that resolves.** The
  repository lines were re-read at the reviewed commit, and the Manim lines in the installed
  0.21.0 and 0.22.0 sources. Blockers 1-4 and the findings that cite probes quote the command
  and its output.
- [x] **Sections A-H are all present**, each with findings, and A and C also list what was
  checked without a finding.
- [x] **Table G has one row for each of the 14 freeze blockers** (8 from Codex, 6 from Claude)
  and for each arch-crew finding: architecture findings 1-4, pattern findings 1-3, the
  `TraceCurve` simplification, the least-architecture check, the portfolio's every-frame
  differential and the primary recommendation.
- [x] **Every *add now* in section B names the defect it prevents.** B8, `D417`: a stale
  Parameters section passes the gate (probe). B9, a *fix now*: the MIT notice is missing from
  both distributions. The other additions are staged and also name a defect: TID251, the
  Hypothesis profile, SciPy, Sphinx.
- [x] **B.7 answers each of its five questions** (§4 B, "B.7 — the five questions").
- [x] **No finding reopens a frozen decision without evidence that it is a defect.**
  - Contradictions: Blocker 3, C1, C2, C3, D5.
  - Impossibilities: Blocker 1, Blocker 2, E2, E4.
  - Mismatches with Manim's actual behaviour: F1, E6, F4.

  Each fix to a frozen document reads "a new ADR". The rest are additions to unspecified rows,
  or to non-frozen documents.
