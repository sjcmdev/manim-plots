# Acceptance table — task 30, occlusion

**Status: Living until task 30 merges, then Record.** Written 2026-10-30 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: ADR 0006 §7 (one occlusion step between the artists
and the renderer, a depth buffer on the GPU through `moderngl` or in NumPy, only on
frames where something changed, only for opaque artists, off by `occlusion=False`, one
module behind one interface); task 24 (the camera read); tasks 25-29 (the artists).

Modules: `mobjects/occlusion.py` (new: the step, both engines behind one interface),
`mobjects/three_d.py` (the keyword, the hook in the camera read).

```python
mp.ThreeDAxes(..., occlusion=True)  # True | False | "numpy" | "gpu"
```

## OC — the occlusion step

| ID | Row |
|---|---|
| OC-1 | `occlusion=True` (default) runs the step with the GPU engine when a `moderngl` standalone context opens and the NumPy engine otherwise; `"gpu"` and `"numpy"` force one (`"gpu"` raises `RuntimeError` naming `moderngl` when no context opens); `False` turns it off, Manim's picture. Any other value raises `ValueError` naming `occlusion` |
| OC-2 | Occluders are the faces of `SurfacePlot`, `BarPlot3D` and `PlanePlot` whose fill opacity is 1, as drawn on that frame (after clipping). A translucent face, a curve, a marker or text occludes nothing |
| OC-3 | Occludees are the system's curve artists — plots, parametric curves, lines, `axline`, segments, contours, wireframe lines, slices, shadows, flat stream lines, error bars, helper lines — and the axis lines of `frame="origin"`. A point of an occludee is hidden when, at its position on screen, an occluder lies nearer to the camera by more than `1e-3` scene units. An occludee is drawn as its visible pieces: its path is cut where visibility changes, within one render pixel of the true crossing; a hidden curve draws nothing; a curve with nothing in front of it keeps its path unchanged |
| OC-4 | A scatter marker and a field arrow are hidden whole (opacity 0, as TK-3) when their centre (an arrow: its start) is hidden *(default taken)*. Numbers, labels, titles, the legend and the colorbar are never occluded. Faces among themselves keep Manim's camera sort |
| OC-5 | The step runs only on frames where the camera's angles, the axes or an occluder or occludee changed; on a still frame it costs nothing. It changes only what Manim draws: an artist's data, its bound inputs and its later re-derivations are untouched, and with no `ThreeDScene` camera it never runs |
| OC-6 | Both engines decide visibility the same way: at every tested point their results agree, except within one render pixel of an occluder's edge |

## Frame cost

Readings (p95 of `update`, ms) for the report, both engines, at 1080p: a helix through an
opaque 32 × 32 surface under `move_camera`; the same scene still; 210 flat arrows and a
surface under `move_camera`. F-1001 is unchanged.
