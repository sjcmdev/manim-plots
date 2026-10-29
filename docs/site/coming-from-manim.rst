Coming from Manim
=================

Most Manim plotting code runs after one change: import ``manim_plots as mp`` and build
the axes with ``mp.Axes`` instead of ``Axes``.

.. code-block:: python

   import numpy as np
   from manim import RED, Scene

   import manim_plots as mp


   class Ported(Scene):
       def construct(self):
           ax = mp.Axes(
               x_range=[0, 10, 1],
               y_range=[-2, 2, 0.5],
               axis_config={"include_numbers": True},
           )
           graph = ax.plot(lambda x: np.sin(x), color=RED)
           label = ax.get_graph_label(graph, "y", x_val=8)
           self.add(ax, graph, label)

What keeps Manim's name and meaning
-----------------------------------

- ``mp.Axes(x_range, y_range, x_length, y_length, axis_config, x_axis_config,
  y_axis_config, tips)`` — Manim's defaults, read from the frame when a range is left
  out. ``from manim_plots import *`` exports the class as ``CartesianAxes``; ``mp.Axes``
  is the same class, so a star import never hides Manim's ``Axes``.
- The ``axis_config`` keys of ``NumberLine``: ``include_numbers``,
  ``numbers_to_include``, ``numbers_to_exclude``, ``decimal_number_config``,
  ``font_size``, ``include_ticks``, ``tick_size``, ``longer_tick_multiple``,
  ``numbers_with_elongated_ticks``, ``exclude_origin_tick``, ``include_tip``,
  ``tip_shape``, ``tip_width``, ``tip_height``, ``label_direction``,
  ``line_to_number_buff``, ``unit_size``, ``scaling`` (``LogBase`` with ranges in
  exponents, as in Manim), ``stroke_width`` and ``color``. Any other key raises a
  ``ValueError`` that names it.
- ``plot(function, x_range=None, use_vectorized=False, **kwargs)`` with Manim's
  keywords, ``plot_parametric_curve``, ``plot_line_graph``, ``c2p`` / ``p2c``,
  ``coords_to_point`` / ``point_to_coords``, ``i2gp`` / ``input_to_graph_point``,
  ``get_axis_labels``, ``get_x_axis_label``, ``get_y_axis_label``,
  ``get_graph_label``, ``add_coordinates``, ``get_origin``, ``get_x_unit_size``.
- On an axis: ``n2p`` / ``p2n``, ``get_tick``, ``get_tick_range``, ``add_numbers``,
  ``add_labels``, ``get_number_mobject``.
- ``mp.NumberPlane`` with Manim's background and faded lines.

What to change in ported code
-----------------------------

- **Drop the groups and updaters that kept a graph on its axes.** A curve made by
  ``ax.plot`` follows its axes on its own. ``VGroup(ax, graph).shift(v)`` still works
  and moves the graph once; ``ax.animate.shift(v)`` together with
  ``graph.animate.shift(v)`` moves it twice, as it would move a second time in Manim
  if Manim moved graphs with their axes.
- **Animate data with ``.animate``.** ``self.play(ax.animate.set_x_range((0, 10)))``
  changes the range over the animation; ``curve.animate.set_parameters(a=2)`` changes a
  parameter of the plotted function. Bind a range or a parameter to a ``ValueTracker``
  when another animation should drive it.
- **Replace ``always_redraw(lambda: ax.plot(...))`` by a parameter** where you can:
  ``ax.plot(lambda x, a=1.0: a * np.sin(x), a=tracker)`` resamples the same curve on
  every frame. ``always_redraw`` still works; it builds a new curve on every frame.
- **Expect conversions to raise.** ``c2p`` and ``p2c`` raise a ``ValueError`` where
  Manim returns ``NaN``: a ``NaN`` input, a value outside a logarithmic axis, or axes
  scaled to nothing.
- **Use the library's own scales for data ranges.** ``x_scale="log"`` takes data
  values (``x_range=(0.1, 1000)``); Manim's ``LogBase`` keeps its exponent ranges.

The full list of differences, each with an example, is :doc:`differences`.
