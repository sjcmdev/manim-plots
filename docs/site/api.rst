API
===

.. currentmodule:: manim_plots

.. autodata:: __version__

Axes
----

.. autoclass:: CartesianAxes
   :members:

``Axes`` is ``CartesianAxes``: ``mp.Axes`` is the same class, left out of
``from manim_plots import *`` so that it never hides Manim's ``Axes``. ``NumberPlane``
is likewise reached as ``mp.NumberPlane``.

.. autoclass:: manim_plots.mobjects.system.NumberPlane

.. autoclass:: manim_plots.mobjects.axis.Axis
   :members:

Artists
-------

.. autoclass:: FunctionPlot
   :members:

.. autoclass:: LinePlot
   :members:

.. autoclass:: ScatterPlot
   :members:

.. autoclass:: ParametricPlot
   :members:

Legend and style
----------------

.. autoclass:: Legend
   :members:

.. autoclass:: LineStyle

.. autoclass:: Marker

.. autodata:: COLOR_CYCLE

Animations
----------

.. autoclass:: DrawAxes

.. autoclass:: TraceCurve

.. autoclass:: ShowPoints

.. autoclass:: Morph

Scales
------

.. autoclass:: Scale

.. autoclass:: LinearScale

.. autoclass:: LogScale

.. autoclass:: SymLogScale

.. autoclass:: FunctionScale

Ticks
-----

.. autoclass:: Locator

.. autoclass:: MaxNLocator

.. autoclass:: MultipleLocator

.. autoclass:: LogLocator

.. autoclass:: SymLogLocator

.. autoclass:: FixedLocator

.. autoclass:: NullLocator

.. autoclass:: MinorCountLocator

Labels
------

.. autoclass:: Formatter

.. autoclass:: Labels

.. autoclass:: DecimalFormatter

.. autoclass:: FormatStrFormatter

.. autoclass:: ScientificFormatter

.. autoclass:: EngFormatter

.. autoclass:: FixedFormatter

.. autoclass:: NullFormatter

Data
----

.. autoclass:: Bounds

.. autoclass:: Source

.. autoclass:: FunctionSource

.. autoclass:: ArraySource

.. autoclass:: ParametricSource

.. autoclass:: Shape

.. autoclass:: Payload

.. autoclass:: CompiledMap

Warnings
--------

.. autoclass:: ManimPlotsWarning
