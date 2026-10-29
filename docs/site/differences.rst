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

Create after Uncreate
---------------------

After ``Uncreate(curve)`` the curve is detached, as in Manim. A later ``Create(curve)``
draws the current curve, where Manim would draw nothing.

Curves follow only permanent changes
------------------------------------

A curve follows a change of its axes that lasts: ``ax.animate.shift``, ``Rotate(ax,
PI / 4)``, ``ax.scale(2)``. An animation that leaves the axes where it found them —
``Indicate(ax)``, ``Wiggle(ax)``, and ``Rotate(ax, TAU)`` — does not move the curve on
any frame.

The double move
---------------

Code ported from Manim that animates the axes and the graph together moves the graph
twice: ``ax.animate.shift(v)`` already moves it. Animate the axes alone.

Bound helper labels
-------------------

``get_graph_label``, ``get_axis_labels`` and ``add_coordinates`` return decorations
bound to the axes: they follow the axes and, for a graph label, the graph's range.

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

Late binding of loop variables
------------------------------

A plot's function is called again whenever the curve is resampled — when its range,
a parameter or its axes' data change. A ``lambda`` made in a loop sees the loop
variable's last value then; bind it as a default argument, ``lambda x, k=k: ...``, which
also makes ``k`` a plot parameter.

Callbacks run once more
-----------------------

To decide whether an animation of the axes is permanent, the library plays it once on
a copy. An animation's callback with side effects — an ``UpdateFromFunc`` that prints,
counts or creates objects — runs once more than in Manim.

refresh() after a bare point edit
---------------------------------

Writing into ``curve.points`` directly lasts until the next rebuild. Call
``curve.refresh()`` to replace it with the derived points at once.

Approximate non-affine frames
-----------------------------

After ``ax.apply_function`` of a non-linear map, curves follow a bilinear frame:
exact at the grid and close between its nodes, not exact everywhere.

PhaseFlow-like callbacks
------------------------

An animation that moves a curve by a function of time on every frame, as ``PhaseFlow``
does, adds a step to the curve's own transform per frame.

The frame's lag slot in Create(ax)
----------------------------------

The axes carry an invisible frame as their last member. ``Create(ax)`` gives it a lag
slot like any member, so the visible parts finish at 24/25 of the run. ``DrawAxes(ax)``
draws without that slot.

Partial drawing paced by sample
-------------------------------

``Create`` on an adaptively sampled curve paces the drawing by sample, not by ``x``:
where the curve bends, the samples crowd and the drawing slows down. ``TraceCurve``
draws in data order at a steady speed in ``x``.

Transform pairs ticks by key
----------------------------

``Transform(ax, other_ax)`` pairs the ticks of the two axes by their value's key, so a
tick at 2 turns into the tick at 2, and ticks without a partner fade in or out. A change
of scale type raises a ``ValueError`` that suggests ``FadeTransform``.

ax.add registers
----------------

``ax.add(curve)`` registers a curve with the axes; it does not make it a submobject, as
Manim's ``add`` would. Registered curves follow the axes; add them to the scene yourself.

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
