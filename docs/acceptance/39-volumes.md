# Acceptance table — task 39, voxels and isosurfaces

**Status: Living until task 39 merges, then Record.** Written 2026-10-31 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: ADR 0007 §1 (voxels, isosurfaces by marching cubes in
NumPy, no new dependency); task 25 (`SurfacePlot`, colorscales, `ColorMapping`); task 29
(BR-1, BR-2: box faces and matplotlib's shading; `plot_trisurf`'s triangle surfaces);
task 30 (occlusion); task 33 (colour by value on 3D bars).

Modules: `core/shape.py` (`marching_cubes`), `mobjects/plots3d.py` (`VoxelPlot`),
`mobjects/three_d.py` (`voxels`, `plot_isosurface`), `src/manim_plots/__init__.py`.

```python
# on ThreeDAxes
def voxels(
    self,
    *args,  # filled, or x, y, z, filled (corner arrays, matplotlib's)
    facecolors=None,
    edgecolors=None,
    shade=True,
    c=None,
    colorscale=None,
    vmin=None,
    vmax=None,
    norm=None,
    **style,
) -> VoxelPlot: ...
def plot_isosurface(
    self,
    F,  # f(x, y, z) vectorised, or a 3D array of samples
    level=0.0,
    *,
    x_range=None,
    y_range=None,
    z_range=None,
    resolution=24,
    colorscale=None,
    colorscale_axis=2,
    vmin=None,
    vmax=None,
    norm=None,
    **style,
) -> SurfacePlot: ...


class VoxelPlot(VGroup):  # mp.VoxelPlot
    def at(self, key: tuple[int, int, int]) -> VGroup: ...  # the voxel's drawn faces

    color_mapping: ColorMapping | None
```

## VX — `voxels`

| ID | Row |
|---|---|
| VX-1 | `ax.voxels(filled)` with `filled` a 3D boolean array (truthy values) draws voxel `(i, j, k)` as the box `[i, i+1] × [j, j+1] × [k, k+1]` in data; `ax.voxels(x, y, z, filled)` takes corner arrays of shape `filled.shape + 1` per axis (matplotlib's), voxel `(i, j, k)` spanning the corners `[i:i+2, j:j+2, k:k+2]`. Only faces between a filled voxel and an empty one (or the array's outside) are drawn, so two touching voxels share no face *(matplotlib's)* |
| VX-2 | `plot.at((i, j, k))` is a `VGroup` of that voxel's drawn faces (empty for an inner or an unfilled voxel), each face styleable on its own and kept through re-derivation; faces are bound to ranges, moves and the camera, cut to the box (BR-3), drawn far to near as task 33's H3-4 asks of bar faces, and take part in occlusion (task 30) *(review: the voxel faces were not sorted)* |
| VX-3 | Colour: `facecolors` one colour or an array of `filled.shape` colours; or `c=` an array of values of `filled.shape` mapped through a `ColorMapping` (default `"viridis"`, `vmin`/`vmax` from the filled voxels' values), `plot.color_mapping` making `ax.colorbar(plot)` work; neither: the cycle's next colour. `shade=True` multiplies each face by BR-2's factor for its normal; `edgecolors` strokes the faces (no stroke by default) |

## IS — isosurfaces

| ID | Row |
|---|---|
| IS-1 | `core.shape.marching_cubes(volume, level, spacing, origin)` is Lorensen and Cline's marching cubes in NumPy: for a 3D array of samples it returns `(vertices, triangles)`, vertices placed on cube edges by linear interpolation of the level, shared between adjacent cubes (one vertex per crossed edge), triangles oriented so their normals point towards increasing values; the ambiguous faces are resolved consistently, so a surface that does not reach the array's boundary is closed (every edge in exactly two triangles) |
| IS-2 | `ax.plot_isosurface(F, level)` samples `F` on a `resolution + 1` grid per axis over the ranges (default the axes' ranges) when it is callable, or takes the array as samples spanning the ranges, and draws the triangles as a `SurfacePlot` (the triangle path of `plot_trisurf`: colorscale along `colorscale_axis`, BR-2-like shading, clipping, occlusion). A level the samples never cross gives a plot with no faces, without error |
| IS-3 | Accuracy, the test: for `x² + y² + z²` at level 1 on `[−1.5, 1.5]³` at resolution 24, every vertex lies within 0.02 of the unit sphere, the area is `4π` within 2 % and the enclosed volume `4π/3` within 3 % |

## Frame cost

Readings (p95 of `update`, ms) for the report: a 10 × 10 × 10 voxel block under
`move_camera`; a resolution-24 sphere isosurface under `move_camera`. F-1001 is unchanged.
