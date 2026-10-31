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
