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
- The bound helpers: ``get_vertical_line``, ``get_horizontal_line``,
  ``get_lines_to_point``, ``get_line_from_axis_to_point``,
  ``get_vertical_lines_to_graph``, ``get_T_label``, ``angle_of_tangent``,
  ``slope_of_tangent``, ``get_secant_slope_group``, ``plot_derivative_graph``,
  ``plot_antiderivative_graph``, ``get_area`` and ``get_riemann_rectangles``.
  Their arguments and named parts keep Manim's meaning, with the corrections in
  :doc:`differences`.
- ``mp.PolarPlane``, ``plot_polar_graph``, ``polar_to_point`` / ``pr2pt``,
  ``point_to_polar`` / ``pt2pr``, ``get_coordinate_labels`` and
  ``get_radian_label``. The Cartesian systems also have the polar conversions and
  ``plot_polar_graph``.
- ``get_vector`` (Manim's NumberPlane helper), ``get_vector_field`` and
  ``get_stream_lines`` (bound versions of Manim's ArrowVectorField and StreamLines),
  and ``plot_implicit_curve``. Field functions receive one point array; implicit
  functions receive ``x, y``.
- ``mp.ThreeDAxes`` with Manim's constructor arguments and defaults,
  ``get_z_axis``, ``get_z_axis_label``, ``get_axis_labels(x, y, z)``, ``c2p`` /
  ``p2c``, ``i2gp`` / ``input_to_graph_point``, ``plot`` in the ``z = 0`` plane,
  ``plot_parametric_curve`` with three components and ``plot_surface``.
- Native ``Create``, ``Uncreate``, ``FadeIn``, ``FadeOut``, ``Transform`` and
  ``ReplacementTransform`` still draw, remove and transform artists. Stream lines'
  ``create``, ``start_animation`` and ``end_animation`` keep Manim's meaning.
  The library's own Animation subclasses are listed in :doc:`animations`.
- ``mp.BarChart``, ``get_bar_labels`` and ``change_bar_values`` keep Manim's
  signatures, defaults and named bars; value labels follow later changes.

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
- **Keep helpers in variables and add them to the scene.** Drop lines, secants,
  areas and rectangles follow their axes and graph. Pass a ``ValueTracker`` for
  ``x``, ``x_val``, ``dx`` or a range endpoint and animate the tracker instead of
  rebuilding the helper with ``always_redraw``. Style named parts such as
  ``secant.dx_line`` directly; their styles survive updates.
- **Build fields on the axes.** Use ``ax.get_vector_field(func)`` and
  ``ax.get_stream_lines(func)``. Their functions and velocities are in data
  coordinates, so motion follows the scale and frame. ``vector_config={"center":
  True}`` restores Manim's centred arrows; noise is seeded here.
- **Use a ``ThreeDScene`` for a 3D camera.** Manim's
  ``set_camera_orientation`` and ``move_camera`` still control it;
  ``self.set_camera_orientation(**ax.view(30, -60))`` uses elevation and azimuth
  in degrees. ``ax.view`` returns camera keywords; it does not move the camera.
  ``frame="box"`` selects panes and edge axes from that camera. A 3D frame accepts
  affine moves; ``apply_function`` raises ``NotImplementedError``.
- **Check the coordinate convention.** ``mp.PolarPlane`` keeps Cartesian
  ``c2p(x, y)``; use ``pr2pt(r, theta)`` for polar input. ``mp.PolarAxes`` takes
  ``(r, theta)`` even in ``c2p``. Spherical input is ``(r, theta, phi)``, with
  ``theta`` measured from +z and ``phi`` the azimuth from +x, unlike Manim's
  spherical utility.
- **Check 3D and polar helper support.** Twins and secondary axes are 2D only.
  ``mp.PolarAxes`` rejects drop lines, calculus helpers, regions and error bars.
  On ``mp.ThreeDAxes``, ``get_lines_to_point``, fields and ``errorbar`` have 3D
  implementations; calculus helpers, ``get_area`` and Riemann rectangles remain
  unsupported. Its ``fill_between`` takes two data triples for a surface band.

The full list of differences is :doc:`differences`.
