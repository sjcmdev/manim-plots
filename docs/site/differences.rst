Differences from Manim
======================

manim-plots keeps Manim's names and meanings, except where Manim's picture is a defect
or where following the axes needs a different rule. Each difference is listed here and
in the documentation of the object where you meet it.

The fixed defaults
------------------

- **A curve is clipped to its axes.** Manim draws a curve outside the axes; pass
  ``clip=False`` for Manim's picture, or a number for a margin in scene units.
- **A pole splits the curve.** Manim joins the two sides of ``1 / x`` with a vertical
  line, or draws nothing when the samples near the pole are huge.
- **Plots without a colour take a colour cycle** whose first colour is Manim's white.
- **Labels that collide are hidden**, the later one; Manim overlaps them.
- **A step written in scientific notation counts its exponent** for the decimal places:
  ``1e-05`` gives five places where Manim gives none.

.. code-block:: python

   import manim_plots as mp

   ax = mp.Axes(x_range=(-1, 10, 1), y_range=(-2, 2, 0.5))
   curve = ax.plot(lambda x: x / 4, clip=0.3)  # may leave the axes by 0.3

.. code-block:: python

   import numpy as np

   import manim_plots as mp

   ax = mp.Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1))
   first = ax.plot(np.sin)  # white, the cycle's first colour
   second = ax.plot(np.cos)  # blue, the next one

   dense = mp.Axes(
       x_range=(0, 1000, 50),
       x_length=6,
       axis_config={"include_numbers": True},
   )
   dense.x.set_label_style(overlap="hide")  # the default
   small = mp.Axes(
       x_range=(0, 0.00005, 1e-5),
       axis_config={"include_numbers": True},
   )  # x numbers have five decimal places

The tick under a tip
--------------------

As in Manim, an end with an arrow tip has no tick and no number. Pass
``tick_under_tip=True`` to keep them; an end without a tip always keeps them.

.. code-block:: python

   import manim_plots as mp

   ax = mp.Axes(x_range=(0, 10, 1), y_range=(-2, 2, 1))
   ax.x.set_tips(end=True, tick_under_tip=True)  # keeps the tick at 10

Ticks at multiples of the step
------------------------------

Ticks sit at integer multiples of the step, ``k * step``. Manim anchors them at
``x_min`` when the range does not contain 0, so ``x_range=[0.001, 6, 1]`` ticks at
0.001, 1.001, … in Manim and at 1, 2, … here. Ticks at fixed multiples keep their
identity while a range is animated.

.. code-block:: python

   import manim_plots as mp

   ax = mp.Axes(x_range=(0.001, 6, 1), tips=False)
   assert list(ax.x.get_tick_range()) == [1, 2, 3, 4, 5, 6]

Create after Uncreate
---------------------

After ``Uncreate(curve)`` the curve is detached, as in Manim. A later ``Create(curve)``
draws the current curve, where Manim would draw nothing.

.. code-block:: python

   import numpy as np
   from manim import Create, Scene, Uncreate

   import manim_plots as mp


   class CreateAgain(Scene):
       def construct(self):
           ax = mp.Axes()
           curve = ax.plot(np.sin)
           self.add(ax, curve)
           self.play(Uncreate(curve), run_time=0.5)
           ax.set_x_range((0, 10))
           self.play(Create(curve), run_time=0.5)

Curves follow only permanent changes
------------------------------------

A curve follows a change of its axes that lasts: ``ax.animate.shift``, ``Rotate(ax,
PI / 4)``, ``ax.scale(2)``. An animation that leaves the axes where it found them —
``Indicate(ax)``, ``Wiggle(ax)``, and ``Rotate(ax, TAU)`` — does not move the curve on
any frame.

.. code-block:: python

   import numpy as np
   from manim import PI, TAU, Indicate, Rotate, Scene

   import manim_plots as mp


   class PermanentChanges(Scene):
       def construct(self):
           ax = mp.Axes(x_length=6, y_length=4)
           curve = ax.plot(np.sin)
           self.add(ax, curve)
           self.play(Rotate(ax, PI / 4), run_time=0.5)  # curve follows
           self.play(Indicate(ax), run_time=0.5)  # curve stays still
           self.play(Rotate(ax, TAU), run_time=0.5)  # curve stays still

The double move
---------------

Code ported from Manim that animates the axes and the graph together moves the graph
twice: ``ax.animate.shift(v)`` already moves it. Animate the axes alone.

.. code-block:: python

   import numpy as np
   from manim import RIGHT, Scene

   import manim_plots as mp


   class MoveTogether(Scene):
       def construct(self):
           ax = mp.Axes(x_length=8, y_length=4)
           curve = ax.plot(np.sin)
           self.add(ax, curve)
           self.play(ax.animate.shift(RIGHT), run_time=0.5)

Bound helper labels
-------------------

``get_graph_label`` and ``get_axis_labels`` return decorations bound to the axes:
they follow the axes and, for a graph label, the graph's range changes.
``add_coordinates`` attaches bound numbers or labels and returns the axes themselves.

.. code-block:: python

   import numpy as np
   from manim import RIGHT, Scene

   import manim_plots as mp


   class BoundLabels(Scene):
       def construct(self):
           ax = mp.Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1), x_length=8)
           ax.add_coordinates()
           curve = ax.plot(np.sin)
           titles = ax.get_axis_labels()
           label = ax.get_graph_label(curve, "f", x_val=2)
           self.add(ax, curve, titles, label)
           self.play(ax.animate.shift(RIGHT), run_time=0.5)

Conversions raise
-----------------

``c2p`` and ``p2c`` raise a ``ValueError`` where Manim returns ``NaN``: a ``NaN`` or
infinite coordinate, a value outside a scale's domain, a point off the plane.

.. code-block:: python

   import numpy as np

   import manim_plots as mp

   ax = mp.Axes()
   try:
       ax.c2p(np.nan, 0)
   except ValueError as error:
       print(error)

A singular frame
----------------

After ``ax.scale(0)`` the axes have no inverse: ``p2c`` raises a ``ValueError`` saying
the frame is singular, and so does an operation on a curve that needs the inverse.

.. code-block:: python

   import numpy as np
   from manim import UP

   import manim_plots as mp

   ax = mp.Axes()
   curve = ax.plot(np.sin)
   ax.scale(0)
   for operation in (lambda: ax.p2c([0, 0, 0]), lambda: curve.shift(UP)):
       try:
           operation()
       except ValueError as error:
           print(error)

Late binding of loop variables
------------------------------

A plot's function is called again whenever the curve is resampled — when its range,
a parameter or its axes' data change. A ``lambda`` made in a loop sees the loop
variable's last value then; bind it as a default argument, ``lambda x, k=k: ...``, which
also makes ``k`` a plot parameter.

.. code-block:: python

   import numpy as np

   import manim_plots as mp

   ax = mp.Axes()
   curves = [ax.plot(lambda x, k=k: np.sin(k * x)) for k in (1, 2, 3)]
   ax.set_x_range((0, 10))  # each curve keeps its own k on resampling

Callbacks run once more
-----------------------

To decide whether an animation of the axes is permanent, the library plays it once on
a copy. An animation's callback with side effects — an ``UpdateFromFunc`` that prints,
counts or creates objects — runs once more than in Manim.

.. code-block:: python

   import numpy as np
   from manim import RIGHT, Scene, UpdateFromFunc

   import manim_plots as mp


   class CallbackSimulation(Scene):
       def construct(self):
           ax = mp.Axes(x_length=6, y_length=4)
           curve = ax.plot(np.sin)
           calls = []

           def move(mobject):
               calls.append("called")  # simulation also calls this closure
               mobject.shift(0.05 * RIGHT)

           self.add(ax, curve)
           self.play(UpdateFromFunc(ax, move), run_time=0.5)

refresh() after a bare point edit
---------------------------------

Writing into ``curve.points`` directly lasts until the next rebuild. Call
``curve.refresh()`` to replace it with the derived points at once.

.. code-block:: python

   import numpy as np
   from manim import UP

   import manim_plots as mp

   ax = mp.Axes()
   curve = ax.plot(np.sin)
   original = curve.points.copy()
   curve.points[:] += UP
   curve.refresh()
   np.testing.assert_allclose(curve.points, original)

Approximate non-affine frames
-----------------------------

After ``ax.apply_function`` of a non-linear map, curves follow a bilinear frame:
exact at the grid and close between its nodes, not exact everywhere.

.. code-block:: python

   import numpy as np
   from manim import Scene

   import manim_plots as mp


   class DeformedFrame(Scene):
       def construct(self):
           ax = mp.Axes(x_length=8, y_length=4)
           curve = ax.plot(np.sin)
           ax.apply_function(lambda p: p + np.array([0, 0.1 * np.sin(p[0]), 0]))
           self.add(ax, curve)

PhaseFlow-like callbacks
------------------------

An animation that moves a curve by a function of time on every frame, as ``PhaseFlow``
does, adds a step to the curve's own transform per frame.

.. code-block:: python

   import numpy as np
   from manim import PhaseFlow, Scene

   import manim_plots as mp


   class FlowingCurve(Scene):
       def construct(self):
           ax = mp.Axes(x_length=8, y_length=4)
           curve = ax.plot(np.sin)
           self.add(ax, curve)
           self.play(
               PhaseFlow(lambda p: np.array([0, 0.05 * np.sin(p[0]), 0]), curve),
               run_time=0.5,
           )

The frame's lag slot in Create(ax)
----------------------------------

The axes carry an invisible frame as their last member. ``Create(ax)`` gives it a lag
slot like any member, so the visible parts finish at 24/25 of the run. ``DrawAxes(ax)``
draws without that slot.

.. code-block:: python

   from manim import Scene

   import manim_plots as mp


   class VisibleAxesOnly(Scene):
       def construct(self):
           ax = mp.Axes()
           self.play(mp.DrawAxes(ax), run_time=0.5)

Partial drawing paced by sample
-------------------------------

``Create`` on an adaptively sampled curve paces the drawing by sample, not by ``x``:
where the curve bends, the samples crowd and the drawing slows down. ``TraceCurve``
draws in data order; pass a linear rate function for steady progress in ``x`` over time.

.. code-block:: python

   import numpy as np
   from manim import Scene, linear

   import manim_plots as mp


   class TraceByX(Scene):
       def construct(self):
           ax = mp.Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1))
           curve = ax.plot(lambda x: np.tanh(8 * x))
           self.add(ax)
           self.play(mp.TraceCurve(curve, rate_func=linear), run_time=0.5)

Transform pairs ticks by key
----------------------------

``Transform(ax, other_ax)`` pairs the ticks of the two axes by their value's key, so a
tick at 2 turns into the tick at 2, and ticks without a partner fade in or out. A change
of scale type raises a ``ValueError`` that suggests ``FadeTransform``.

.. code-block:: python

   import numpy as np
   from manim import Scene, Transform

   import manim_plots as mp


   class TicksByKey(Scene):
       def construct(self):
           ax = mp.Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1))
           curve = ax.plot(np.sin)
           target = mp.Axes(x_range=(-1, 5, 1), y_range=(-2, 2, 1))
           self.add(ax, curve)
           self.play(Transform(ax, target), run_time=0.5)

ax.add registers
----------------

``ax.add(curve)`` registers a curve with the axes; it does not make it a submobject, as
Manim's ``add`` would. Registered curves follow the axes; add them to the scene yourself.

.. code-block:: python

   import numpy as np
   from manim import Scene

   import manim_plots as mp


   class RegisteredCurve(Scene):
       def construct(self):
           ax = mp.Axes()
           curve = ax.plot(np.sin)  # plot already registers it
           ax.add(curve)  # registering it again has no effect
           assert curve in ax.artists
           assert curve not in ax.submobjects
           self.add(ax, curve)

An unknown axis_config key raises
---------------------------------

Manim ignores or passes on an ``axis_config`` key it does not know; manim-plots raises a
``ValueError`` that names it, so a misspelt key cannot go unnoticed.

.. code-block:: python

   import manim_plots as mp

   try:
       mp.Axes(axis_config={"include_number": True})
   except ValueError as error:
       print(error)


Clipping each coordinate separately
-----------------------------------

Manim does not clip plots to their coordinate system. Here ``clip`` also accepts
``(x, y)`` or, in 3D, ``(x, y, z)``: each entry is a bool or a margin in scene units.
Each artist clips to its own pair of axes. ``clip=False`` restores Manim's unbounded
picture, but poles still split. This keeps independent scales and box plots honest.


Helpers stay bound to their inputs
----------------------------------

Manim constructs drop lines, secants, labels and filled regions once. Here they follow
the system's permanent moves, ranges and graph parameters, and accept trackers for
numeric inputs. Their geometry is derived in data space and mapped through the
system; secant legs follow rotated axes instead of staying horizontal and vertical
in the scene. Line helpers and regions clip like plots. This gives the same binding
rule to every helper, including on log scales and warped 2D frames.


Helper lines are artists
------------------------

Manim returns Line or DashedLine objects for line helpers. Here the line-like parts
are HelperLine artists, with the group's familiar named parts. ``line_func`` accepts
Manim's Line and DashedLine only; another constructor raises TypeError. Unknown
``line_config`` keys also raise. This preserves clipping and bindings while keeping
solid and dashed styling, including ``buff``, ``dash_length`` and ``dashed_ratio``.


The T label touches an offset axis
----------------------------------

Manim places the T label's triangle at data y = 0 even when the x axis is drawn
elsewhere. Here the triangle touches the drawn x axis. On ranges ``(1, 5)`` and
``(2, 10)``, Manim leaves it below the axis; the corrected placement follows the
axis crossing, border or chosen position.


A zero secant step gives the tangent
------------------------------------

Manim silently replaces ``dx=0`` with its default step. Here the secant legs collapse
and the secant becomes the tangent. A tracker animated down to zero therefore
reaches the mathematical limit rather than jumping back to a finite secant.


An antiderivative can start at the range boundary
-------------------------------------------------

Manim integrates from zero and uses ``samples`` to choose its quadrature. Here the
integral starts at zero when zero is inside the parent's range and domain; otherwise
it starts at the range's start. The ``y_intercept`` is the value there. Integration
is shared across the range on each re-derivation; ``samples`` remains accepted but
has no effect. This permits an antiderivative such as log(x) for 1/x on [1, 5]
without integrating through its pole.


Area follows the drawn boundary
-------------------------------

Manim builds get_area from the graph's Bezier control points and leaves the polygon
unclipped. Here the boundary follows the drawn curve and is clipped to the viewport.
This fixes fills that include control handles or extend past their axes.


Riemann sums count intervals exactly
------------------------------------

Manim's floating-point arange can add an extra rectangle: [1, 1.3] with dx = 0.1
produces four. Here the count uses an integer partition with a step-relative
tolerance, producing three. The last interval still has the full requested width;
it need not end at the range boundary.


Riemann baselines use the chosen sample
---------------------------------------

Manim evaluates bounded_graph at the left endpoint even for right or centre samples.
Here both boundaries use the chosen sample. Rectangles are built in data coordinates,
so rotated sides follow the axes and warped sides follow the frame. This corrects
the inconsistent baseline and scene-aligned construction.


Border ticks point inward
-------------------------

Manim's default ticks straddle their axis. Here an axis explicitly placed on a named
border, a mirror, a twin's own axis or a secondary axis points its ticks inward,
with numbers outside. Axes positioned through data retain Manim's straddling ticks,
even if an excluded zero puts them at an edge. An explicit direction always wins.
This makes a framed plot readable without a separate direction call for each side.


Mirrors and twins omit tips
---------------------------

Manim's ordinary axes have end tips by default. Here mirrored axes and a twin's own
axis have none unless set_tips enables them. A twin or secondary axis replaces the
mirror on its side, avoiding two lines drawn on top of each other. Mirrors can be
styled independently while sharing the range. A twin of a twin shares the calling
system's other axis, so a top/right pair really plots against top and right.


Field vectors and motion use data coordinates
---------------------------------------------

Manim's vector fields and nudges operate in scene coordinates. Here the field receives
a data point and returns a data vector, mapped through the axes for drawing and
motion. Arrows start at their grid points; Manim centres them there.
``vector_config={"center": True}`` restores that placement. get_vector returns a
bound group with line and tip rather than an unbound native arrow. These rules keep
direction and motion correct on unequal units, log scales and moving axes.


Stream lines share a reproducible integrator
--------------------------------------------

Manim integrates StreamLines with Euler steps, omits the grid's upper endpoints and
uses unseeded noise. Here stream lines, nudges and Flow share RK4 integration; both
field grids include both endpoints, noise defaults to seed 0, and padding is in
data steps on every side. The 2D default grid step is half each axis's range step,
rather than a fixed scene-unit density. After ``play(lines.create())`` the scene
holds the bound field, so start_animation remains visible. This makes repeated
renders agree and keeps the displayed paths consistent with the motion.


Implicit curves use the shared field source
-------------------------------------------

Manim's plot_implicit_curve uses its implicit-curve sampler. Here the same signature
builds a marching-squares zero set on the field source, with about max_quads cells
and min_depth refinements at sign changes. It follows function parameters and the
system like a plot. Sharing the source makes clipping and bindings consistent;
the sampling algorithm need not reproduce Manim's vertices.


Polar conversions follow the labelled spokes
--------------------------------------------

Manim's PolarPlane conversions ignore azimuth_offset and azimuth_direction. Here
pr2pt and pt2pr include both, so an angle lands on its labelled spoke. This fixes
inconsistent conversions; default angles retain Manim's convention.


Polar labels follow the plane
-----------------------------

Manim places PolarPlane labels relative to the scene origin and returns the entire
x axis as the radius-label group, adding it twice. Here labels follow the plane
and the first group contains just radius numbers. This fixes misplaced labels
on shifted and resized planes without duplicating the axis.


There is no zero-radius grid circle
-----------------------------------

Manim includes a circle of radius zero in PolarPlane's background lines. Here that
degenerate circle is omitted: the default major grid has twenty spokes and four
circles. This removes an empty grid element rather than giving it a styling slot.


The 3D frame accepts affine moves
---------------------------------

Manim permits apply_function on ThreeDAxes. Here apply_function raises
NotImplementedError; the 3D frame supports shifts, scales and rotations. Unlike the
approximate warped 2D frame, the 3D frame has an affine contract. Curves and surfaces
follow its affine moves and ranges, and clip to the three-coordinate box by default;
Manim leaves them behind and draws outside the box.


A box frame follows the camera
------------------------------

Manim's ThreeDAxes draws axes through the origin and leaves labels in their planes.
That is also the default here. With frame="box", far panes and near edge axes follow
the camera; labels and numbers face it by default. Numbers are offset perpendicular
to the projected edge and later overlapping numbers hide, then return when clear.
Titles sit beyond the numbers. This prevents corner collisions. A box in a plain
Scene warns because it lacks a 3D camera. Legends and colorbars in a ThreeDScene
are fixed in the frame. The view method returns camera keywords rather than moving
the camera itself.


Surface ranges may be omitted
-----------------------------

Manim raises TypeError when plot_surface is missing u_range or v_range. Here each
omitted range follows its corresponding axis range; an explicit range stays fixed.
This gives a surface the same live viewport default as a function plot.


Surface colours are sampled at face centres
-------------------------------------------

Manim colours a face from the midpoint of its outline, which is the cell's far
corner: a half-cell shift. Here a function surface uses its uv centre; triangle
and supplied-grid surfaces use the mean of their corners in data. Colour
normalisation follows the chosen axis's scale by default, rather than always
interpolating raw values. Callable values default to linear normalisation.
This puts the colour at the represented sample, including on logarithmic axes.


Three-dimensional drop lines go to the floor and walls
------------------------------------------------------

Manim's get_lines_to_point on ThreeDAxes returns two oblique lines from x and y.
Here it returns x_line, y_line and z_line: a vertical drop to the floor, then the
floor point's lines to the two walls. In a box the floor and walls are the far panes
and follow the camera. This makes all three coordinates visible.


Spherical coordinates put the polar angle first
-----------------------------------------------

Manim's spherical_to_cartesian utility orders the angles differently. Here
spherical_to_point and sp2pt take (r, theta, phi): theta from +z, phi the azimuth
from +x, following ISO 80000-2. The same order applies to coords="spherical" on
curves, surfaces and fields. Cylindrical input is (rho, phi, z). Physics and
mathematics conventions take precedence over Manim's utility.


A 3D field samples a volume by default
--------------------------------------

Manim defaults three_dimensions to False, a single layer at z = 0. On ThreeDAxes
it defaults to True here; False requests Manim's single layer. The default step is
twice each axis's range step, rather than the 2D half-step, to avoid thousands of
arrows in a default box. Explicit x_range, y_range and z_range set the grid.


Short solid arrows keep their direction
---------------------------------------

Manim's Arrow3D can turn a too-short arrow's cone backwards. Here arrow="3d" scales
the cone's height and radius together to at most half the arrow length. Zero and
nonfinite vectors stay hidden or degenerate at their mapped tails, without a Cone
constructor division by zero. This keeps short and invalid field samples finite.


Solid stream lines have no passing flash
----------------------------------------

Manim's StreamLines can start a passing-flash animation on its flat paths. Here
line="3d" builds Line3D cylinders: create works, but start_animation raises
NotImplementedError. A passing flash on solid segments has no defined meaning;
use the default flat lines for it.


Opaque surfaces hide pieces of curves
-------------------------------------

Manim's Cairo camera sorts whole mobjects by depth, so a curve through a surface
can draw over it. Here occlusion is on by default in a ThreeDScene: opaque faces
hide curve segments and lines, and hidden scatter markers or arrows hide whole
by their centre or start point. Faces still use the camera sort among themselves;
labels and decorations are not occluded. The GPU engine is used when available,
with NumPy as fallback. occlusion=False restores Manim's picture. This corrects
curve/surface visibility without changing the artist's data.


Surface transforms adopt the target source
------------------------------------------

Manim aligns Surface families geometrically for Transform and ReplacementTransform.
Here the intermediate faces keep that meaning, but the source surface also adopts
the target function and colour rule when finished. A later range change therefore
derives the target surface instead of bringing the old function back. Native
Create, FadeIn and FadeOut retain their surface meanings.


A zero bar can grow again
-------------------------

Manim's change_bar_values scales by new / old, leaving an originally zero bar at
zero forever. Here the same bar mobject is rebuilt from its data value, and
chart.animate.change_bar_values interpolates those values. Labels follow values
and ranges. This fixes zero bars while retaining identities and user styling.


Bar faces sort across the collection
------------------------------------

Manim's Cairo sorting can draw a rear bar over a front one when bars are separate
families. Here bar3d and hist3d faces sort far to near by their camera-space face
centres whenever the camera or bars change. Camera shading is off; shade uses the
library's data-normal lighting. This fixes the reviewed 3D histogram draw order.


Rebuilt text leaves no ghosts
-----------------------------

Manim freezes a flat list of moving mobjects at the start of a play. Replacing a
label in its family can leave an old glyph in that list, still drawable. Here
replaced glyphs lose their drawable points, and bound parts changed by library
animations are declared moving before background compilation. End labels,
crosshair readouts, bar labels, axis numbers and colorbar numbers therefore update
without ghosts; unchanged functions are not sampled again merely for an animation.


A surface animation shares its scene camera
-------------------------------------------

Manim copies a starting mobject for an animation. Deep-copying a surface's linked
camera can try to pickle its graphics context and fail on a second play. Here the
copy shares the scene camera. This fixes repeated surface animations without
copying the renderer's context.


Some inherited helpers are refused outside 2D
---------------------------------------------

Manim exposes its inherited 2D helpers on ThreeDAxes. Here unsupported helpers
raise NotImplementedError rather than draw an ambiguous 2D construction in 3D.
get_vertical_line, get_horizontal_line and get_vertical_lines_to_graph are refused;
use get_line_from_axis_to_point or the three-part get_lines_to_point instead.
Calculus helpers, get_area, get_riemann_rectangles and plot_implicit_curve also
remain 2D. The true PolarAxes system refuses drop lines, calculus, regions and
errorbar; PolarPlane remains a Cartesian system with polar decorations.
