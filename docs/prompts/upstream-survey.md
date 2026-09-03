# Prompt: upstream survey of ManimCommunity/manim

Paste the block below into ChatGPT with GitHub access. The result is saved to
`docs/upstream-survey.md`, and feeds task 01 in `TODO.md`.

---

You have GitHub access. Survey the issues and pull requests of
`ManimCommunity/manim` and report everything that bears on a third-party
plotting library being written against Manim. Follow every instruction below
exactly.

## What the library is

An independent plotting library for Manim, built on Manim's primitives
(`Line`, `MathTex`, `VGroup`) but deliberately **not** subclassing Manim's
`Axes`, `NumberLine`, `NumberPlane` or `ParametricFunction`. It supplies its own
coordinate systems, scales, tick locators, formatters and data plotting. It
targets Manim Community Edition 0.21 and declares a floor of 0.19.

Two things therefore matter to us, and nothing else does:

1. **Upstream knowledge about the graphing stack** — known defects, their
   status, and the reasoning maintainers have applied to them.
2. **Upstream constraints on us as a downstream consumer** — changes to the
   primitives we build on, or to the rendering pipeline, that would break a
   library that does not inherit from Manim's graphing classes.

Ignore everything unrelated: 3D scenes, video encoding, OpenGL renderer work
that does not touch mobject geometry, CI, packaging, documentation typos.

## Scope of the sweep

Cover **both open and closed** issues and pull requests, with no date floor.
A closed-as-wontfix issue is often the most valuable result, because it carries
the maintainers' reasoning.

Source files in scope:

- `manim/mobject/graphing/coordinate_systems.py`
- `manim/mobject/graphing/number_line.py`
- `manim/mobject/graphing/scale.py`
- `manim/mobject/graphing/functions.py`
- `manim/mobject/graphing/probability.py`
- `manim/mobject/geometry/line.py` — only where it affects `NumberLine`
- `manim/mobject/mobject.py` — only `apply_points_function_about_point` and the
  transformation methods that funnel through it

Run at least these searches, and any others the results suggest:

- `repo:ManimCommunity/manim is:issue NumberLine`
- `repo:ManimCommunity/manim is:issue Axes`
- `repo:ManimCommunity/manim is:issue LogBase OR log scale OR semilog`
- `repo:ManimCommunity/manim is:issue tick`
- `repo:ManimCommunity/manim is:issue legend`
- `repo:ManimCommunity/manim is:issue plot clipping OR asymptote OR discontinuity`
- `repo:ManimCommunity/manim is:pr coordinate_systems.py`
- `repo:ManimCommunity/manim is:pr number_line.py`
- `repo:ManimCommunity/manim is:pr scale.py`
- Whatever the repository's own labels offer for this area — check the label
  list rather than guessing label names.

## Our defect list

Thirteen defects were found by direct experiment against Manim 0.19.2. They have
**not** been re-verified against 0.21. For each one, determine what upstream
knows: is it reported, fixed, rejected, or unknown?

1. Float accumulation in `NumberLine` tick generation via `np.arange`
2. `include_tip` alters tick range and coordinate mapping inconsistently
3. Plot curves escape the axes viewport; no clipping for asymptotic functions
4. Axes aspect ratio distortion from independent length parameterisation
5. `unit_size` ignored when passed through `axis_config`
6. Mutating `x_range` after construction leaves ticks stale
7. No legend primitive; users assemble legends by hand
8. `LogBase.inverse_function` ndarray guard broken; negatives become NaN silently
9. `LogBase` has no minor ticks between decades
10. `LogBase` naming: `function()` is exponential, not logarithmic
11. Label overlap: no de-confliction at high label density
12. Ticks centred on the axis line; cannot be directed outward only
13. `_origin_shift` clamps to the range minimum when the range excludes zero

Also report anything in scope that is **not** on this list — an upstream defect,
feature request or design discussion we have not accounted for. Those are the
most valuable results, so search for them deliberately rather than only matching
against the thirteen.

## Output document

Produce a single Markdown document, exactly in this shape.

```markdown
# Upstream survey: ManimCommunity/manim

Surveyed on: <date>
Manim versions referenced: <latest release at time of survey, and the versions
the findings concern>

## Coverage

| Search | Results | Reviewed | In scope |
|---|---|---|---|
| <query> | <n> | <n> | <n> |

Searches that returned nothing are listed too.

## Findings

### UP-01 — <short title>

- **Type:** bug | feature-request | design-discussion | breaking-change
- **Upstream:** #<number> — <url> (plus any linked issue or PR)
- **Status:** open | merged | closed-unmerged | closed-wontfix | stale
- **Last activity:** <date>
- **Versions:** reported on <version>; fixed in <version or "not fixed">
- **Maintainer position:** <shortest decisive quote, verbatim, with who said it;
  "none" if no maintainer responded>
- **Our defect:** <number from our list, or "new">
- **Implication:** adopt-fix | avoid-approach | add-requirement | monitor | no-action
- **Why:** <two sentences at most>
- **Confidence:** verified — I opened the thread and read it | inferred — <what
  the inference rests on>

### UP-02 — ...

## Our defects with no upstream trace

| # | Defect | Searched | Interpretation |
|---|---|---|---|

Interpretation is one of: nobody has reported it; it is reported under wording I
could not find; it may not reproduce on current `main`.

## Constraints on a downstream library

Anything found that changes what a library outside Manim's class hierarchy can
rely on: deprecations, renames, signature changes, altered transformation
semantics, renderer differences between cairo and OpenGL.

## Open questions

Things the survey could not settle, each with what evidence would settle it.
```

## Rules

- Open every thread you cite and read it. Do not report from search-result
  snippets or from memory of the codebase.
- Quote the shortest decisive line rather than summarising a maintainer's
  position in your own words.
- Every finding carries a real URL. If you cannot produce the URL, the finding
  does not go in the document.
- Never guess an issue number, a version or a date. Write `unknown` and say what
  you tried.
- State result counts honestly. If a search returned more results than you
  reviewed, say so in the coverage table — an incomplete survey that admits it
  is useful; one that hides the gap is not.
- Distinguish what the thread says from what you concluded. The
  `Confidence` field is not decoration.
- Absence of evidence is a finding. A defect nobody has reported in six years of
  the project's history tells us something.
- Do not propose fixes, designs or code for our library. Report what upstream
  knows and stop there.
