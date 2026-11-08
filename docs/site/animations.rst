Native animation recipes
========================

Every exposed part is a Manim mobject. Use Create for ticks and grid, FadeIn for
numbers, and Write for text. Call add_numbers before addressing numbers.
Add bound helpers and artists to the scene so their bindings can follow changes.
Animate their existing trackers to move a tangent or a crosshair.

.. code-block:: python

   from manim import Create, FadeIn, Scene, Text, ValueTracker, Write
   import manim_plots as mp


   class NativeParts(Scene):
       def construct(self):
           ax = mp.NumberPlane(x_range=(-2, 4, 1), y_range=(-2, 6, 1))
           curve = ax.plot(lambda x: x * x, x_range=(-1, 2))
           ax.x.add_numbers([0, 1, 2], label_constructor=Text)
           self.add(ax, curve)
           self.play(Create(ax.x.ticks))
           self.play(FadeIn(ax.x.numbers))
           self.play(Create(ax.x.grid))
           end = ax.end_label(curve, label=Text("curve"))
           self.add(end)
           self.play(Write(end))
           position = ValueTracker(0)
           tangent = ax.get_tangent_line(position, curve)
           self.add(tangent)
           self.play(position.animate.set_value(1.5))

Library entrances accept reverse=True to unwind their presentation and remove
the artist. Set remover=False to keep it in the scene, or remover=True on a
forward entrance to remove it after growing. Cleanup restores canonical data,
styles and bindings, so the same artist can be introduced again. ShrinkBars keeps
its original per-bar shrinking schedule; GrowBars(reverse=True) unwinds the
whole staggered schedule.

TraceCurve defaults to parameter pacing: x for a function, input index for a
line, and t for a parametric curve. pacing="arc_length" uses mapped scene length
without counting gaps. ShowPoints supports stable data, x, y, value or callable
ordering; pop=True also scales markers about their mapped centres.


The library's animations
------------------------

Import these from ``manim_plots.animations`` or from the top level, for example ``mp.TraceCurve``.
All accept Manim's ``run_time`` and ``rate_func``. Entrances accept ``reverse`` and
``remover`` as described above. Data transitions commit their target; supply the
previous target to undo them. Emphases restore the original presentation.

Existing animations
~~~~~~~~~~~~~~~~~~~

- ``TraceCurve`` traces a curve; ``pacing="parameter"`` or ``"arc_length"``.
- ``ShowPoints`` reveals scatter markers; ``order``, ``pop``, ``lag_ratio``.
- ``Morph`` changes one curve into another on a shared arc-length lattice; targets
  are the positional ``a`` and ``b``.
- ``AppendData`` appends ``x`` and ``y`` to a line or scatter; ``autoscale``.
- ``DrawAxes`` draws visible axes parts together; ``reverse``, ``remover``.
- ``BuildAxes`` draws axes in stages; ``lag_ratio``, ``stages``, ``stage_animations``.
- ``HighlightTick`` indicates a tick and its number; ``value``, ``color``, ``scale_factor``.
- ``GrowBars`` grows signed bars from their bases; ``lag_ratio``, ``order``.
- ``ShrinkBars`` removes bars with the original per-bar shrinking schedule; ``lag_ratio``.
- ``SortBars`` moves bars and category names into sorted slots; ``key``, ``reverse``
  (descending order, rather than an exit).
- ``HighlightBar`` emphasizes a bar and dims the others; ``key``, ``dim_opacity``.
- ``Flow`` advects mobjects through a field; ``speed``, ``pointwise``.
- ``GrowSurface`` grows a surface from a data plane; ``zdir``, ``offset``.
- ``ShrinkSurface`` reverses surface growth; ``zdir``, ``offset``, ``remover``.

2D helpers and decorations
~~~~~~~~~~~~~~~~~~~~~~~~~~

- ``ExtendReference`` extends a reference or drop line; ``origin="start"``, ``"end"``
  or ``"center"``.
- ``GrowRegion`` grows a filled region from its paired boundary; ``axis``.
- ``SweepRegion`` reveals a region by a moving data cut; ``axis``, ``direction``.
- ``SweepSpan`` sweeps a span along its interval; ``direction``.
- ``GrowRiemann`` grows rectangles from their bound baseline; ``lag_ratio``.
- ``GrowErrorBars`` grows stems then caps from each centre; ``lag_ratio``, ``cap_lag``.
- ``RevealAnnotation`` draws an annotation's arrow and text; ``text_first``, ``lag_ratio``.
- ``RevealCrosshair`` reveals lines, dot and readout; ``lag_ratio``.
- ``RevealLegend`` introduces legend entries; ``lag_ratio``, ``artist_animations``.
- ``FillColorbar`` fills the strip then reveals its axis; ``lag_ratio``.

``BuildAxes(stages=...)`` also belongs here: stages can select and group the parts
that native animations draw.

Chart families
~~~~~~~~~~~~~~

- ``GrowStack`` grows stacked series from each preceding boundary; ``lag_ratio``.
- ``RevealCells`` reveals heatmap or hexbin cells; ``order``, ``lag_ratio``.
- ``RevealContours`` reveals 2D contour levels independently; ``order``, ``lag_ratio``.
- ``SweepPie`` sweeps wedges in angular order; ``lag_ratio``.
- ``ExplodePie`` temporarily offsets wedges along their bisectors; ``indices``, ``amount``.
- ``GrowBoxPlot`` opens boxes from the median then whiskers and fliers; ``box_ratio``,
  ``lag_ratio``.
- ``UnfoldViolin`` opens density bodies from the centre line then summaries;
  ``body_ratio``, ``lag_ratio``.

``GrowBars(order=...)`` also belongs here: use data order, height order or a callable.

Spatial construction
~~~~~~~~~~~~~~~~~~~~

- ``GrowField`` grows arrows from mapped tails; ``order``, ``lag_ratio``.
- ``GrowStems`` grows stems from their bottom with markers following; ``lag_ratio``.
- ``RevealWireframe`` traces parameter-line families; ``families``, ``lag_ratio``.
- ``RevealWaterfall`` traces each waterfall curve; ``lag_ratio``.
- ``SweepSurface`` reveals a surface by a moving cut; ``axis``, ``direction``.
- ``SweepPolar`` reveals polar decorations by angle; ``start_angle``, ``angle``, ``lag_ratio``.
- ``OpenInset`` opens the viewport, connectors and mirrored artists; ``lag_ratio``.
- ``CloseInset`` reverses inset opening; ``lag_ratio``, ``remover``.

Topology-changing transitions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- ``RefineRiemann`` refines or coarsens a nested rectangle partition; ``dx``, ``order``,
  ``lag_ratio``.
- ``RebinHistogram`` changes histogram bins while conserving mass; ``bins``.
- ``StackVoxels`` reveals occupied layers with temporary exposed faces; ``axis``,
  ``direction``, ``lag_ratio``.
- ``SweepIsovalue`` extracts a volume at an animated scalar level; ``level``.
- ``SweepSlice`` moves an axis-aligned slice and its linked profile; ``stop``.

``RefineRiemann`` requires nested partitions. ``RebinHistogram`` requires common
outer endpoints and nonnegative weights; intermediate union pieces transport bin
mass rather than count samples at moving edges. ``SweepSlice`` accepts an x/y
SliceView or a coordinate slice; an oblique SliceView has no scalar stop.
