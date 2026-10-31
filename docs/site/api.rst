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

3D
--

.. autoclass:: ThreeDAxes
   :members:

.. autoclass:: manim_plots.mobjects.three_d.Pane
   :members:

Polar
-----

``PolarPlane`` is Manim's Cartesian plane with a polar grid, reached as
``mp.PolarPlane`` because Manim has the name. ``PolarAxes`` is a true polar system: its
data coordinates are ``(r, θ)``.

.. autoclass:: manim_plots.mobjects.polar.PolarPlane
   :members:

.. autoclass:: PolarAxes
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

.. autoclass:: PlanePlot
   :members:

.. autoclass:: AxLinePlot
   :members:

.. autoclass:: ErrorBars
   :members:

Fields
------

``ArrowVectorField`` and ``StreamLines`` share Manim's names, so like ``NumberPlane`` they
are reached as ``mp.ArrowVectorField`` and ``mp.StreamLines``, outside the star import.

.. autoclass:: manim_plots.mobjects.fields.ArrowVectorField
   :members:

.. autoclass:: manim_plots.mobjects.fields.StreamLines
   :members:

.. autoclass:: Flow

Legend and style
----------------

.. autoclass:: Legend
   :members:

.. autoclass:: LineStyle

.. autoclass:: Marker

.. autodata:: COLOR_CYCLE

Themes
------

.. autoclass:: Theme

.. autodata:: THEMES

.. autodata:: CYCLES

.. autofunction:: set_theme

.. autofunction:: get_theme

Animations
----------

.. autoclass:: AppendData

.. autoclass:: BuildAxes

.. autoclass:: DrawAxes

.. autoclass:: ExplodePie

.. autoclass:: GrowBars

.. autoclass:: GrowBoxPlot

.. autoclass:: GrowStack

.. autoclass:: GrowSurface

.. autoclass:: HighlightBar

.. autoclass:: HighlightTick

.. autoclass:: Morph

.. autoclass:: RebinHistogram

.. autoclass:: RefineRiemann

.. autoclass:: RevealCells

.. autoclass:: RevealContours

.. autoclass:: ShowPoints

.. autoclass:: ShrinkBars

.. autoclass:: ShrinkSurface

.. autoclass:: SortBars

.. autoclass:: StackVoxels

.. autoclass:: SweepIsovalue

.. autoclass:: SweepPie

.. autoclass:: SweepSlice

.. autoclass:: TraceCurve

.. autoclass:: UnfoldViolin

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

.. autoclass:: AngleFormatter

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

.. autoclass:: Node

.. autoclass:: AffineNode

.. autoclass:: ScaleNode

.. autoclass:: FunctionNode

Warnings
--------

.. autoclass:: ManimPlotsWarning

Surfaces and colour
-------------------

.. autoclass:: SurfacePlot

.. autoclass:: StemPlot

.. autoclass:: WaterfallPlot

.. autoclass:: BarPlot3D

.. autoclass:: Hist3DPlot
   :members:

.. autoclass:: VoxelPlot

.. autoclass:: HistPlot
   :members:

.. autoclass:: StackPlot
   :members:

.. autoclass:: BarPlot

.. autoclass:: GroupedBarPlot

.. autoclass:: BarChart

.. autoclass:: WireframePlot

.. autoclass:: ContourPlot

.. autoclass:: SliceView

.. autoclass:: Colormap

.. autoclass:: ColorMapping

.. autoclass:: InsetAxes
   :members:

.. autoclass:: Colorbar

.. autodata:: colormaps

.. autoclass:: HeatmapPlot
   :members:

.. autoclass:: HexbinPlot
   :members:

.. autoclass:: ContourSetPlot
   :members:

.. autoclass:: PieChart
   :members:

.. autoclass:: BoxPlot

.. autoclass:: ViolinPlot

Axis kinds
----------

.. autofunction:: date2num

.. autofunction:: num2date

.. autoclass:: AutoDateLocator
   :members:

.. autoclass:: ConciseDateFormatter
   :members:

.. autoclass:: PercentFormatter
   :members:

.. autoclass:: LogitFormatter
   :members:

.. autoclass:: LogitScale
   :members:

.. autoclass:: LogitLocator
   :members:

.. autoclass:: BrokenScale
   :members:
