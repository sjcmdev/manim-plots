# Acceptance table — task 27, fields in 3D

**Status: Living until task 27 merges, then Record.** Written 2026-10-30 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: ADR 0006 §5 (coordinates), §8 (flat camera-facing
arrows by default, `arrow="3d"` for Manim's 3D arrows, plain lines by default,
`line="3d"` for `Line3D`, `Flow` in 3D); task 21 (FS, VF, SL, FL, GV rows: every 2D rule
holds in 3D unless a row here says otherwise); task 24 (the box, the camera, facing);
task 26 (CO: the coordinate formulas).

Modules: `core/sources.py` (`FieldSource` and `rk4_step` by dimension),
`mobjects/fields.py` (the fields by dimension, flat facing arrows, `arrow=`, `line=`,
`coords=`), `mobjects/three_d.py` (the methods; the camera read for facing).

```python
# on ThreeDAxes; Manim's signatures (z_range and three_dimensions included)
def get_vector_field(
    self, func, *, three_dimensions=True, arrow="flat", coords=None, **kwargs
) -> ArrowVectorField: ...
def get_stream_lines(
    self, func, *, three_dimensions=True, line="flat", coords=None, **kwargs
) -> StreamLines: ...
def get_vector(self, coords, **kwargs) -> HelperGroup: ...  # .line .tip, flat, facing


# Flow(field, *mobjects, ...) and the nudge family take 3D fields unchanged
```

## VT — vector fields in 3D

| ID | Row |
|---|---|
| VT-1 | `ax.get_vector_field(func)` on a `ThreeDAxes` samples a grid over x, y and z, both ends of each range included (FS-4), in Manim's order: x outer, y, z inner. Its step defaults to twice each axis's range step, so the default box holds 7 × 6 × 5 = 210 arrows *(default taken: in 2D it is half the step; in 3D half would be thousands)*; `x_range`, `y_range`, `z_range` set it as in Manim. `func` takes one data point `np.array([x, y, z])` and returns three components (FS-2, `use_vectorized` as in 2D) |
| VT-2 | `three_dimensions=True` by default on a `ThreeDAxes` *(default taken: Manim's default is False, a flat grid at z = 0)*; `three_dimensions=False` gives Manim's single layer at `z = 0` with the vectors' three components |
| VT-3 | Each arrow starts at its grid point, along the data vector mapped through the system (its direction `c2p(p + ε v) − c2p(p)`), scene length `length_func(norm)`, as VF-1 |
| VT-4 | `arrow="flat"` (default): the 2D arrow's shape (shaft and `ArrowTriangleFilledTip`), every point in one plane through the arrow's axis, the plane that faces the camera most: its normal is the view direction's part perpendicular to the arrow. It is turned again on every frame where the camera moved (task 24's camera read; with no `ThreeDCamera`, the view straight down `z`) and costs nothing on a still frame. An arrow along the view direction keeps its last plane |
| VT-5 | `arrow="3d"`: each arrow is Manim's `Arrow3D` from the start to the end, Manim's `thickness`, `height` and `base_radius` *(default taken: the cone stays Manim's size; arrows shorter than the cone's height draw only the cone)*, styled through `vector_config`; it does not turn with the camera. Any other `arrow` raises `ValueError` naming `arrow` |
| VT-6 | Colour (VF-2), `arrows[i]` addressable and styled on its own and kept through re-derivation (VF-3), drawn when the start lies in the box by the clip rule per axis (VF-4, TK-2), following ranges (animated), moves and the field's parameters, all as in 2D |
| VT-7 | `coords="spherical"`: `func` receives the grid point as `np.array([r, θ, φ])` (CO-2) and returns `(v_r, v_θ, v_φ)` on the local unit vectors `r̂ = (sin θ cos φ, sin θ sin φ, cos θ)`, `θ̂ = (cos θ cos φ, cos θ sin φ, −sin θ)`, `φ̂ = (−sin φ, cos φ, 0)`; on the z axis φ = 0 and at the origin θ = 0 (CO-2's values), so the basis is always defined. `coords="cylindrical"`: `np.array([ρ, φ, z])` in, `(v_ρ, v_φ, v_z)` out on `ρ̂ = (cos φ, sin φ, 0)`, `φ̂`, `ẑ`. The grid stays cartesian. Any other `coords` raises `ValueError` naming `coords` |

## ST — stream lines in 3D

| ID | Row |
|---|---|
| ST-1 | `ax.get_stream_lines(func)` on a `ThreeDAxes`: start points on VT-1's grid (VT-2's `three_dimensions`) with `n_repeats` and seeded `noise_factor` noise in three dimensions (SL-1), each integrated by RK4 in three dimensions (FS-3) for `virtual_time` in steps of `dt`, stopping when it leaves the box grown by `padding` steps on every side |
| ST-2 | `line="flat"` (default): each line is one stroked path as in 2D, coloured along its length by `color_scheme` (SL-2), clipped to the box, `stream_lines[i]` styleable; `create`, `start_animation`, `end_animation` as SL-3 |
| ST-3 | `line="3d"`: each line is a `VGroup` of Manim `Line3D` segments between consecutive anchors (`max_anchors_per_line` bounds them), Manim's `thickness`, each coloured by `color_scheme` at its midpoint; `create` works; `start_animation` raises `NotImplementedError` naming `line` *(default taken: a passing flash on cylinders is not defined)*. Any other `line` raises `ValueError` naming `line` |
| ST-4 | The lines follow ranges, moves and parameters (SL-4); `coords=` as VT-7 |

## FT — motion and single vectors in 3D

| ID | Row |
|---|---|
| FT-1 | `nudge`, `nudge_submobjects`, `get_nudge_updater`, `start_submobject_movement`, `stop_submobject_movement` and `Flow` move points in three dimensions: scene to data by `p2c`, RK4 in data, back by `c2p` (FL-1, FL-2, FL-3) |
| FT-2 | `ax.get_vector(coords)` on a `ThreeDAxes`: a flat arrow from the data origin to the data point `coords` (three entries, trackers allowed, GV-1), facing the camera as VT-4, a `HelperGroup` of `.line` and `.tip` |
| FT-3 | `plot_implicit_curve` stays refused on a `ThreeDAxes` (an implicit surface is an isosurface, after the release) |

## Frame cost

Readings (p95 of `update`, ms) for the report: the default 210-arrow field under
`move_camera`; the same field under `ax.animate.set_z_range`; default 3D stream lines
under `start_animation`; `arrow="3d"` under `move_camera` (nothing to turn: near zero).
F-1001 is unchanged.
