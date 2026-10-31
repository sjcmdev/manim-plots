"""The public surface: star exports collide with nothing in Manim (D12, ADR 0003 §8).

Rows A-1 to A-3 and C-2 of `docs/acceptance/06-core-contracts.md`. ``EXPECTED`` is a
decision regression: each task that adds a public name adds it here too.
"""

from __future__ import annotations

import manim

import manim_plots
from manim_plots.core import ManimPlotsWarning
from manim_plots.core.nodes import CompiledMap

EXPECTED = {
    "__version__",
    "ManimPlotsWarning",
    "Scale",
    "LinearScale",
    "LogScale",
    "SymLogScale",
    "FunctionScale",
    "Payload",
    "CompiledMap",
    # task 07
    "Bounds",
    "Source",
    "Shape",
    "FunctionSource",
    "ArraySource",
    "ParametricSource",
    # task 08
    "Locator",
    "MaxNLocator",
    "MultipleLocator",
    "LogLocator",
    "SymLogLocator",
    "FixedLocator",
    "NullLocator",
    "MinorCountLocator",
    "Formatter",
    "Labels",
    "DecimalFormatter",
    "FormatStrFormatter",
    "ScientificFormatter",
    "EngFormatter",
    "FixedFormatter",
    "NullFormatter",
    # task 09
    "CartesianAxes",
    # task 11
    "FunctionPlot",
    "LinePlot",
    "ScatterPlot",
    "ParametricPlot",
    # task 12
    "Legend",
    "ErrorBars",
    "Theme",
    "THEMES",
    "CYCLES",
    "set_theme",
    "get_theme",
    "LineStyle",
    "Marker",
    "COLOR_CYCLE",
    "DrawAxes",
    "TraceCurve",
    "ShowPoints",
    "Morph",
    # task 21: ArrowVectorField and StreamLines are attributes only, as NumberPlane
    "Flow",
    # task 22: PolarPlane is an attribute only, as NumberPlane
    "PolarAxes",
    "AngleFormatter",
    "Node",
    "AffineNode",
    "ScaleNode",
    "FunctionNode",
    # task 24: ThreeDAxes is an attribute only, as NumberPlane
    # task 25
    "SurfacePlot",
    "WireframePlot",
    "ContourPlot",
    "Colormap",
    "colormaps",
    "ColorMapping",
    "Colorbar",
    # task 26
    "PlanePlot",
    "AxLinePlot",
    # task 29
    "StemPlot",
    "WaterfallPlot",
    "BarPlot3D",
    "GrowSurface",
    # task 28b
    "SliceView",
    # task 31: BarChart is an attribute only, as ThreeDAxes
    "BarPlot",
    "GroupedBarPlot",
    # task 32
    "HistPlot",
    "StackPlot",
    # task 33
    "Hist3DPlot",
    # task 34
    "GrowBars",
    "ShrinkBars",
    "SortBars",
    "AppendData",
    "BuildAxes",
    "HighlightTick",
    "HighlightBar",
    # task 35
    "InsetAxes",
    # task 36
    "date2num",
    "num2date",
    "AutoDateLocator",
    "ConciseDateFormatter",
    "PercentFormatter",
    "LogitScale",
    "LogitLocator",
    "LogitFormatter",
    "BrokenScale",
    # task 38
    "PieChart",
    "BoxPlot",
    "ViolinPlot",
    # task 37
    "HeatmapPlot",
    "HexbinPlot",
    "ContourSetPlot",
}


def test_a1_every_exported_name_exists_and_manim_lacks_it():
    manim_names = set(dir(manim))
    for name in manim_plots.__all__:
        assert hasattr(manim_plots, name), name
        if name != "__version__":
            assert name not in manim_names, f"{name} collides with manim.{name}"


def test_a1_a_star_import_works():
    namespace: dict[str, object] = {}
    exec("from manim_plots import *", namespace)
    assert set(manim_plots.__all__) <= set(namespace)


def test_a2_the_exports_so_far():
    assert set(manim_plots.__all__) == EXPECTED
    assert len(manim_plots.__all__) == len(EXPECTED)


def test_a3_compiled_map_is_a_runtime_checkable_protocol():
    assert manim_plots.CompiledMap is CompiledMap
    assert not isinstance(object(), CompiledMap)


def test_c2_the_warning_category():
    assert manim_plots.ManimPlotsWarning is ManimPlotsWarning
    assert issubclass(ManimPlotsWarning, UserWarning)
