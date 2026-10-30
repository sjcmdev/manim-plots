# Acceptance table — task 28b, the slice view

**Status: Living until task 28b merges, then Record.** Written 2026-10-30 from the
maintainer's review: "powiązać intersection płaszczyzny z surface z wykresem obok …
oczywiście pełna customizacja". One call builds the moving plane, its cut on the
surface and the profile on 2D axes beside the 3D axes, all driven by one input. Rows
marked *(default taken)* stand unless vetoed. Contracts: ADR 0004 §9 (every part
addressable and styleable, defaults overridable); task 25 (CB-3: placement beside the
axes, fixed in the frame in 3D); task 26 (`plane`, IX-3); task 28 (`slice`,
`plot_slice`, HB-2 inputs).

Modules: `mobjects/surfaces.py` (`plot_slice` by plane), `mobjects/slice_view.py` (new),
`mobjects/three_d.py` (the method), `src/manim_plots/__init__.py`.

```python
# on CartesianAxes (2D), task 28's method extended
def plot_slice(
    self, surface, *, x=None, y=None, plane=None, **style
) -> FunctionPlot: ...


# on ThreeDAxes
def slice_view(
    self,
    surface,
    *,
    x=None,
    y=None,
    plane=None,
    axes=None,
    side="right",
    plane_config=None,
    cut_config=None,
    axes_config=None,
    profile_config=None,
) -> SliceView: ...


class SliceView(VGroup):  # mp.SliceView
    plane: PlanePlot
    cut: ParametricPlot | ContourPlot
    axes: CartesianAxes
    profile: FunctionPlot
```

## PV — `plot_slice` by a plane

| ID | Row |
|---|---|
| PV-1 | `plot_slice(surface, plane=p)` with `p` an axis-aligned `PlanePlot` (`ax.plane(x=c)`, `ax.plane(y=c)`) is task 28's `x=c` (`y=c`) profile, bound to the plane's own input: a tracker that moves the plane moves the profile on the same frame |
| PV-2 | With an oblique plane that is not horizontal (`point`, `normal` with a horizontal part), the profile's abscissa is `s = (q − p0) · h`, `h = ẑ × n / |ẑ × n|` the plane's horizontal direction, `p0` its point, and its ordinate the surface's `z` along the plane's trace in the `xy` plane: for a surface from `plot_surface`, `s ↦ f(p0 + s h)` exactly, over the `s` where the trace lies in the surface's domain. A horizontal plane raises `ValueError` naming `plane` (its cut is a contour, CT-1). Other surface kinds raise `TypeError` naming `plot_surface` (PS-3) |
| PV-3 | Exactly one of `x`, `y`, `plane`, else `ValueError` naming `plot_slice` |

## SV — the slice view

| ID | Row |
|---|---|
| SV-1 | `ax.slice_view(surface, x=c)` (or `y=c`, or `plane=p`) returns an `mp.SliceView` holding `.plane` (`ax.plane(x=c)`, or `p` itself), `.cut` (`ax.intersection(plane, surface)` for a plane, `surface.slice(x=c)` for `x`/`y`), `.axes` (2D axes) and `.profile` (`axes.plot_slice(surface, plane=plane)`). `c` takes HB-2's forms; one tracker drives all four |
| SV-2 | `.axes` defaults to `mp.Axes` with `x_range` the surface's range along the slice (the `y` range for `x=c`, the `x` range for `y=c`, the `s` range for a plane), `y_range` the system's `z` range, `x_length=4`, `y_length=3`, axis labels `"y"`, `"x"` or `"s"` and `"z"` *(default taken)*; `axes_config` updates those keywords; `axes=` passes axes the user built, used as they are |
| SV-3 | Style: the plane is task 26's (PL-6) unless `plane_config` restyles it; the cut and the profile share one colour, the next of the 3D system's cycle, and the cut's stroke *(default taken)*; `cut_config` and `profile_config` restyle each one. Every part stays an ordinary artist: styled, animated or removed on its own afterwards |
| SV-4 | Placement as CB-3: in 2D scenes the axes sit `side` of the 3D axes (`"right"`, `"left"`, `"up"`, `"down"`), `MED_LARGE_BUFF` away, and follow their bounding box; in a `ThreeDScene` they are fixed in the frame on the first frame, against that side of the frame, as the colorbar is; `side` other than those raises `ValueError` naming `side` |
| SV-5 | `scene.add(view)` adds all four parts; `Create(view)` draws them; removing the view removes them. The view itself holds no geometry of its own |
