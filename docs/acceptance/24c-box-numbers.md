# Acceptance table — task 24c, the box frame's numbers on screen

**Status: Living until task 24c merges, then Record.** Written 2026-10-30 after the
maintainer's review of the stage 4 pictures ("coś tam z liczbami lekko nie pasuje"):
in `frame="box"` a number can sit on its own tick or edge, and at a corner shared by two
edge axes their end numbers overlap. Rows marked *(default taken)* stand unless vetoed.
Contracts: task 24 (FR rows: the box, its edges chosen from the camera, numbers facing
the camera, FR-6).

Modules: `mobjects/three_d.py` (the placement in `_update_view`).

## FN — numbers on screen

| ID | Row |
|---|---|
| FN-1 | In `frame="box"`, each number of an edge axis is placed on screen from its tick along the edge's outward normal on screen — perpendicular to the projected edge, away from the projected centre of the box — so its nearest point is `buff` from the projected edge, `buff = 0.15` scene units *(default taken)*. It is placed again on every frame where the camera's angles changed, after FR-6's turn, and costs nothing on a still frame |
| FN-2 | No two numbers overlap on screen. Where two would — the end numbers of two edge axes at a shared corner — the number of the later axis (y after x, z after both) is hidden on that frame (opacity 0) and shown again when they no longer overlap *(default taken: matplotlib leaves them overlapping)* |
| FN-3 | Axis titles (`get_axis_labels`) of edge axes sit outside their axis's numbers along the same normal, `buff` beyond the numbers' far side, and overlap no number |
| FN-4 | `frame="origin"` is unchanged: Manim's placement |
