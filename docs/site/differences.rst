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
