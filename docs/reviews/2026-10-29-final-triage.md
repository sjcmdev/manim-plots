# Final reviews — triage

Every finding of `docs/reviews/2026-10-28-final-codex.md` (27) and
`docs/reviews/2026-10-28-final-claude.md` (4 blockers, 51 findings), and where it was
closed. Both reviewed commit `f129014`; their line numbers refer to it.

- `2527615` — the test infrastructure fixed after the reviews (ADR 0002 amended).
- `038c570` — the living documents fixed.
- **ADR 0003 §n** — a decision changing a frozen document, amended in place and marked
  *(ADR 0003)*.
- **task/nn** — closed by the task that owns it (`TODO.md`, *Stage 2*), usually through
  the acceptance table of ADR 0003 §9.

Where the two reviewers disagreed, the maintainer's check of the sources decided:

| Point | Outcome | Evidence |
|---|---|---|
| Is `scope.md:78` against ADR 0001:226 open (Codex) or closed (Claude)? | open; closed now by ADR 0003 §1 | `:78` "carries the other four through untouched" against `:226` "`Map` owns validity" |
| Does a frozen `wait` make the visual harness draw twice (Codex) or is the end frame correct (Claude)? | it drew twice | a translucent square, `Create`, `wait`: 11 316 differing values in an all-frames grid, 42 222 in a last frame |
| Is `.hypothesis/` worth a `.gitignore` line (Codex A3)? | no | Hypothesis writes `*` into `.hypothesis/.gitignore` itself (Claude, section A) |
| Render tests in the merge gate (Claude) or opt-in (Codex)? | in the gate | the maintainer's choice; `tools/check.py --fast` leaves them out |

## Codex

| ID | Severity | Finding | Closed by |
|---|---|---|---|
| C1 | blocker | `Map` must and must not change validity | ADR 0003 §1 |
| E1 | blocker | `contains` lacks the density `values` has | ADR 0003 §2 |
| E2 | blocker | finishing rows overlap, no precedence | ADR 0003 §5 |
| A1 | minor | TODO: "all 18", "NumPy-only core" | `038c570` |
| A2 | minor | CONTRIBUTING's stability rule narrower than the frozen documents | `2527615` |
| A3 | minor | `.hypothesis/` not ignored | not needed: see the disagreements above |
| A4 | minor | 85 PoC 2 JSON files the frozen suite no longer writes | `038c570`, in `poc/README.md` |
| A5 | major | PoC 4's `summary.json` not generated from the committed inputs | `038c570`, in `poc/README.md`: a snapshot of an earlier run; the 4.04 ms raw figure is stated |
| B1 | major | a frozen `wait` makes the end frame draw twice | `2527615`, with two regression tests |
| B2 | major | "all frames" ignores repeats; tolerance over the whole grid | `2527615` |
| B3 | major | the benchmark's `update` is a proxy for the camera's reads | `2527615`: one read per family member, setup recorded; timing the getter itself is left to F-1001's task (ADR 0002 §2) |
| B4 | major | `LICENSE` missing from the sdist | `2527615`, checked in the sdist and the wheel |
| B5 | minor | the citation guard skips the ADRs | `2527615` |
| C2 | major | warn once per data change against once per rebuild | ADR 0003 §3 |
| C3 | major | the README promises fewer differences than the scope | `038c570` |
| C4 | minor | MaxN called the default; `ax.x.labels.at` | `038c570` |
| C5 | minor | "four" surfaces above five rows | ADR 0003 §9 |
| D1 | major | `Node`, `Payload`, `Shape` untyped | ADR 0003 §1; `Node` in task/06's code |
| D2 | major | filtering, smoothing and clipping have no order | ADR 0003 §1 |
| D3 | major | scale and frame tolerances, inverse branch | ADR 0003 §3 for tolerances; branch and extrapolation examples in task/06's acceptance table |
| D4 | major | built-in locators, formatters and sources lack edge behaviour | ADR 0003 §9: acceptance tables of tasks 06-08 |
| E3 | major | protocol members writable | ADR 0003 §2 |
| E4 | major | own transform and adoption through a singular frame | ADR 0003 §6 |
| F1 | minor | defaults rows that need their conditions | ADR 0003 §7 for tick positions; import-time defaults and the `LogBase` crossing tick in task/10's acceptance table, tested under a changed `tempconfig` |
| F2 | major | end states do not close D17; the frame's lag slot | ADR 0003 §7 |
| F3 | major | NumberPlane parity unspecified | ADR 0003 §7 |
| H1 | major | the order measures the two risks late | `TODO.md` *Stage 2*: pins in task/06, a core benchmark in task/07, an end-to-end F-1001 spike in task/09 |

## Claude

| ID | Severity | Finding | Closed by |
|---|---|---|---|
| Blocker 1 | blocker | a plain callable passes as a `Formatter` | ADR 0003 §2 |
| Blocker 2 | blocker | `FadeOut` matches two rows; an introducer's start is taken too early | ADR 0003 §5 |
| Blocker 3 | blocker | F-110's "always dirty" | ADR 0003 §4 |
| Blocker 4 | blocker | SymLog, MaxN, keys, `eps`, tolerances, exception type, warning channel | ADR 0003 §3 |
| A1 | minor | three byte-identical model files | `038c570`, in `poc/README.md` |
| A2 | minor | PoC 1 cites untracked images | `038c570`, in `poc/README.md` |
| A3 | minor | the index omits the root documents | `038c570` |
| A4 | minor | grill-log and plan headers out of date | `038c570` |
| A5 | minor | precedence between ADR and scope; Frozen defined elsewhere | `038c570` for Frozen; ADR 0003 §9 for the precedence |
| A6 | minor | the gate lints the frozen PoCs | `2527615` |
| A7 | minor | unanchored ignore patterns | `2527615` |
| A8 | minor | branch policy against history | `2527615` aligns CONTRIBUTING with TODO: `main` takes the first stage that ships functionality, tagged. Pushing is the maintainer's call |
| B1 | major | misspelt attributes pass mypy and write silently | ADR 0003 §7 |
| B2 | major | render tests outside the merge gate | `2527615`, the maintainer's choice |
| B3 | major | the benchmark reads a leaf once per ancestor | `2527615` |
| B4 | major | the benchmark records no setup | `2527615` |
| B5 | minor | visual tolerance per grid, repeats, case collisions, ADR wording | `2527615` |
| B6 | minor | library INFO prints with logging "off" | `2527615`: library diagnostics log at DEBUG only (ADR 0002 §4) |
| B7 | minor | a file sink changes behaviour; a bad path fails mid-render | `2527615`: the file opens at import; the file sink's effect on warnings is documented |
| B8 | minor | add `D417` | `2527615` |
| B9 | minor | `LICENSE` in neither distribution | `2527615` |
| B10 | minor | the version in two places | `2527615` |
| B11 | minor | packaging work for the release | task/14 for links, URLs and a changelog; task/06 declares SciPy |
| B12 | minor | `pytest-cov` unused | `2527615`, removed |
| B13 | minor | TeX caches written into the working directory | `2527615` |
| C1 | major | F-705 against the invalid-input table | ADR 0003 §3 |
| C2 | major | F-203 against the defaults table and D23 | ADR 0003 §6 |
| C3 | major | the paper check against ADR 0001 on extending `Payload` | ADR 0003 §1 |
| C4 | minor | two silent supersessions | `038c570` |
| C5 | minor | `ax.x.labels.at(2.0)` in living documents | `038c570` |
| C6 | minor | parity rows promising 0.1 without an `F-*` | `SymLog` by ADR 0003 §3; the rest retagged in `docs/parity-survey.md` with ADR 0003 |
| C7 | minor | F-912's data-channel class has no home | ADR 0003 §8: dropped |
| C8 | minor | wrong counts | TODO in `038c570`; ADR 0001's "seventeen frames" by ADR 0003 §5; `docs/defect-audit-0.21.md` is a Record and stays as written — its "seven suppressions" are six, and 15e has no probe either |
| C9 | minor | sources outside the scope's legend; F-112 cites D5 | ADR 0003 §9 |
| C10 | minor | ADR 0002 misdescribes Manim's logger; unguarded citation | `2527615` |
| D2 | major | no warning mechanism named | ADR 0003 §3 |
| D3 | major | `Transform` between different systems | ADR 0003 §8: a cross-fade of unmatched ticks, the maintainer's choice; a scale-type change raises |
| D4 | major | `ax.plot(f, a=tracker)` against Manim's `**kwargs` | ADR 0003 §4 |
| D5 | major | an animated flip passes through an empty range | ADR 0003 §6 |
| D6 | major | the aspect lock is over-determined | ADR 0003 §6: `adjustable`, the maintainer's design |
| D7 | minor | no API removes an artist from its system | ADR 0003 §8 |
| D8 | minor | `set_ticks` pairs | ADR 0003 §8 |
| D9 | minor | only one star-exported name | ADR 0003 §8; the list in task/06 |
| D10 | minor | `unit_size` against the default length | ADR 0003 §6 |
| D11 | minor | the decimal-places rule | ADR 0003 §7 |
| E2 | major | protocols reject frozen value objects | ADR 0003 §2 |
| E3 | major | `Payload` has no type | ADR 0003 §1 |
| E4 | major | 0.2's autoscale would break `Scale` | ADR 0003 §2 |
| E6 | major | F-915's frame changed in 0.22.0 | ADR 0003 §5 |
| E7 | minor | region topology validation and log sinks larger than needed | kept: a third-party `Source` can return a region payload in 0.1, and the validator is the trust boundary; the sinks were asked for |
| F1 | major | the tick-position row misstates Manim | ADR 0003 §7 |
| F2 | minor | missing default rows; raising keys unlisted | ADR 0003 §7 |
| F3 | minor | `p2n` signature changed in 0.22.0 | ADR 0003 §7 |
| F4 | major | four visible differences not in F-1008 | ADR 0003 §7 |
| H1 | major | the order measures the risks after the Manim layer | `TODO.md` *Stage 2*, as Codex H1 |

The tables of under-specified rows (Codex section D, Claude Table D) are closed as a
whole by ADR 0003 §9: each row goes into the acceptance table of the task that owns it.
The staged tooling of both section B tables (TID251 for the layer rules, a derandomised
Hypothesis profile, Sphinx) is scheduled in task/06 and task/14.
