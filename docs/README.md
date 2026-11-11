# Documents

The documents about manim-plots under `docs/`. The root holds the rest: `README.md`,
`CONTRIBUTING.md` (conventions, the testing policy, API stability), `TODO.md` (the task
plan and the branch policy) and `LICENSE`; `poc/README.md` describes the proofs of
concept. Each document here has one status:

- **Frozen** — any change needs a new ADR that says what it supersedes.
- **Living** — kept current as decisions are made.
- **Record** — written once and kept as a record of what was done or found. Only file
  paths in it are updated when the repository moves; line numbers in it refer to the
  commit it was written against.

When two documents disagree, the ADRs and the 0.1 tier of `scope.md` win, then the
latest decision in `grill-log.md`. Between an ADR and `scope.md`, the ADR wins on
contracts and mechanism and `scope.md` on what is required. Between two ADRs, the later
one wins where it says it supersedes the earlier. A disagreement is a defect to fix, not
a choice.

## Read first

| Document | Status | What it holds |
|---|---|---|
| [`scope.md`](scope.md) | Frozen (tier 0.1) | Every requirement as an `F-*` with a tier, the defaults table, invalid-input rules, paper checks, traceability |
| [`adr/0001-architecture.md`](adr/0001-architecture.md) | Frozen | Layers, module layout, the public contracts, the leaf lifecycle |
| [`adr/0002-test-infrastructure.md`](adr/0002-test-infrastructure.md) | Frozen | Visual baselines, benchmarks, render tests in the gate, diagnostic logging |
| [`adr/0003-final-review-closure.md`](adr/0003-final-review-closure.md) | Frozen | The final reviews' decisions: payload and protocols, core numerics, lifecycle precedence, closeness to Manim; amends scope and ADR 0001 in place |
| [`adr/0004-one-first-release.md`](adr/0004-one-first-release.md) | Frozen | 0.1 and 0.2 joined into one release; what joins it, what stays after it, bound helpers, names |
| [`adr/0005-inward-ticks-and-top-axis.md`](adr/0005-inward-ticks-and-top-axis.md) | Accepted | Ticks at a border point inward unless set; an independent top axis (task 19b) |
| [`adr/0006-three-dimensions.md`](adr/0006-three-dimensions.md) | Accepted | 3D joins the first release: `ThreeDAxes` as the same system in three dimensions, frame styles, ISO spherical coordinates, an occlusion step (tasks 24-30) |
| [`adr/0007-stage-5-plot-types-and-data-animation.md`](adr/0007-stage-5-plot-types-and-data-animation.md) | Accepted | Bars, histograms in 2D and 3D coloured by value, data animation, 2D helpers, axis kinds, heatmaps, statistics, voxels and isosurfaces join the release (tasks 31-39) |
| [`grill-log.md`](grill-log.md) | Living | Decisions D1-D27 with reasoning and rejected alternatives; a later decision says which earlier one it supersedes |
| [`plan.md`](plan.md) | Living | The design rationale and mechanism in prose: pipeline, `.animate`, containers, API, the 0.1 gate, risks |

## Evidence

| Document | Status | What it holds |
|---|---|---|
| [`defect-audit-0.21.md`](defect-audit-0.21.md) | Record | Manim defects verified on 0.21.0; the probes are `tests/test_defect_audit_0_21.py` |
| [`parity-survey.md`](parity-survey.md) | Living | Manim, matplotlib and gnuplot/OriginPro surfaces; guarded by `tests/test_parity_surface.py` and `tools/mpl_surface.py` |
| [`api-sketch.md`](api-sketch.md) | Record | The first API draft with the maintainer's inline answers |
| [`poc/poc1-points-property.md`](poc/poc1-points-property.md) | Record | PoC 1: the `points` property on a leaf; falsified the shadow test. Code in `poc/poc1/` |
| [`poc/poc2-frame-lifecycle.md`](poc/poc2-frame-lifecycle.md) | Record | PoC 2: hidden frame grid, animation lifecycle, target adoption. Code in `poc/poc2/` |
| [`poc/poc3-stack-context.md`](poc/poc3-stack-context.md) | Record | PoC 3: operation context read from Manim's call stack. Code in `poc/poc3/` |
| [`poc/poc4-keyed-alignment.md`](poc/poc4-keyed-alignment.md) | Record | PoC 4: keyed family alignment, the native data channel under `.animate`. Code in `poc/poc4/` |

## Reviews

| Document | Status | What it holds |
|---|---|---|
| [`reviews/2026-09-05-plan-review-log.md`](reviews/2026-09-05-plan-review-log.md) | Record | Codex review rounds of the task/03 plan and scope, and what was accepted |
| [`reviews/2026-10-24-arch-crew.md`](reviews/2026-10-24-arch-crew.md) | Record | Architecture review with the arch-crew skills, with corrections from the freeze reviews |
| [`reviews/2026-10-24-codex.md`](reviews/2026-10-24-codex.md) | Record | Freeze review by Codex; its blockers closed by D22-D27 |
| [`reviews/2026-10-24-claude.md`](reviews/2026-10-24-claude.md) | Record | Freeze review by Claude, independent of the Codex one; blockers closed by D22-D27 |
| [`reviews/2026-10-28-final-codex.md`](reviews/2026-10-28-final-codex.md) | Record | Final review by Codex before implementation |
| [`reviews/2026-10-28-final-claude.md`](reviews/2026-10-28-final-claude.md) | Record | Final review by Claude, independent of the Codex one |
| [`reviews/2026-10-29-final-triage.md`](reviews/2026-10-29-final-triage.md) | Record | Every finding of the two final reviews and where it was closed |
