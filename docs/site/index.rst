manim-plots
===========

manim-plots draws plots for `Manim <https://www.manim.community/>`_ animations. It keeps
Manim's names — ``Axes``, ``plot``, ``axis_config``, ``NumberPlane``, ``get_graph_label``
— and fixes what goes wrong with them: a curve that leaves its axes, a pole drawn as a
vertical line, a graph that stays behind when its axes move, ticks that cannot be
animated.

.. toctree::
   :maxdepth: 1

   coming-from-manim
   differences
   gallery
   animations
   api


Install
-------

manim-plots needs Python 3.12 or newer, Manim 0.21.0 or 0.22.0 and the Cairo renderer.
It is not on PyPI yet; install it from the repository:

.. code-block:: text

   pip install "git+https://github.com/sjcmdev/manim-plots@dev"

A first plot
------------

.. code-block:: python

   import numpy as np
   from manim import BLUE, RIGHT, Create, Scene

   import manim_plots as mp


   class FirstPlot(Scene):
       def construct(self):
           ax = mp.Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1))
           curve = ax.plot(np.sin, color=BLUE)
           self.play(Create(ax), Create(curve))
           self.play(ax.animate.shift(2 * RIGHT))

``mp.Axes`` keeps Manim's constructor arguments and axis defaults. ``ax.plot`` returns
a curve that belongs to the axes: it follows permanent moves, rotations, scaling and
range changes on every frame, without a ``VGroup`` or an updater. Temporary indications
leave the curve still; see :doc:`differences` for the exact rules and fixed defaults.

Animating the data
------------------

A range is a parameter. Set it, bind it to a tracker, or animate it with Manim's own
``.animate``:

.. code-block:: python

   import numpy as np
   from manim import Scene, ValueTracker

   import manim_plots as mp


   class Ranges(Scene):
       def construct(self):
           ax = mp.Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1))
           curve = ax.plot(np.sin)
           self.add(ax, curve)
           self.play(ax.animate.set_x_range((0, 10)))
           right = ValueTracker(10.0)
           ax.x.range.bind(lambda: (0.0, right.get_value()))
           self.play(right.animate.set_value(4.0))

The ticks, the numbers and every curve on the axes are rebuilt for each frame's range.
A function's own parameters work the same way:

.. code-block:: python

   import numpy as np
   from manim import Scene

   import manim_plots as mp


   class Parameters(Scene):
       def construct(self):
           ax = mp.Axes(x_range=(-3, 3, 1), y_range=(-3, 3, 1))
           wave = ax.plot(lambda x, a=1.0: a * np.sin(x))
           self.add(ax, wave)
           self.play(wave.animate.set_parameters(a=2.5))
