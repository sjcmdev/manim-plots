"""Correct, extensible plotting primitives for Manim."""

import logging
import os
from collections.abc import Mapping
from importlib.metadata import version

from manim_plots.core import ManimPlotsWarning
from manim_plots.core.formatters import (
    AngleFormatter,
    DecimalFormatter,
    EngFormatter,
    FixedFormatter,
    FormatStrFormatter,
    Formatter,
    Labels,
    NullFormatter,
    ScientificFormatter,
)
from manim_plots.core.nodes import (
    AffineNode,
    CompiledMap,
    FunctionNode,
    Node,
    ScaleNode,
)
from manim_plots.core.payload import Payload
from manim_plots.core.scales import (
    FunctionScale,
    LinearScale,
    LogScale,
    Scale,
    SymLogScale,
)
from manim_plots.core.shape import Shape
from manim_plots.core.sources import (
    ArraySource,
    Bounds,
    FunctionSource,
    ParametricSource,
    Source,
)
from manim_plots.core.ticks import (
    FixedLocator,
    Locator,
    LogLocator,
    MaxNLocator,
    MinorCountLocator,
    MultipleLocator,
    NullLocator,
    SymLogLocator,
)
from manim_plots.mobjects.animations import DrawAxes, Morph, ShowPoints, TraceCurve
from manim_plots.mobjects.artists import (
    COLOR_CYCLE,
    FunctionPlot,
    LinePlot,
    LineStyle,
    Marker,
    ParametricPlot,
    ScatterPlot,
)
from manim_plots.mobjects.axis import TickDirection as TickDirection
from manim_plots.mobjects.bars import BarChart as BarChart
from manim_plots.mobjects.bars import BarPlot, GroupedBarPlot
from manim_plots.mobjects.colorbar import Colorbar
from manim_plots.mobjects.colormaps import Colormap, ColorMapping, colormaps
from manim_plots.mobjects.context import check_pins
from manim_plots.mobjects.errorbar import ErrorBars
from manim_plots.mobjects.fields import ArrowVectorField as ArrowVectorField
from manim_plots.mobjects.fields import Flow
from manim_plots.mobjects.fields import StreamLines as StreamLines
from manim_plots.mobjects.geometry import AxLinePlot, PlanePlot
from manim_plots.mobjects.heatmaps import ContourSetPlot, HeatmapPlot, HexbinPlot
from manim_plots.mobjects.helpers import FilledRegion as FilledRegion
from manim_plots.mobjects.helpers import HelperGroup as HelperGroup
from manim_plots.mobjects.helpers import HelperLine as HelperLine
from manim_plots.mobjects.histograms import HistPlot, StackPlot
from manim_plots.mobjects.inset import InsetAxes
from manim_plots.mobjects.legend import Legend
from manim_plots.mobjects.plots3d import (
    BarPlot3D,
    Hist3DPlot,
    StemPlot,
    VoxelPlot,
    WaterfallPlot,
)
from manim_plots.mobjects.polar import PolarAxes
from manim_plots.mobjects.polar import PolarPlane as PolarPlane
from manim_plots.mobjects.slice_view import SliceView
from manim_plots.mobjects.statistics import BoxPlot, PieChart, ViolinPlot
from manim_plots.mobjects.surfaces import (
    ContourPlot,
    GrowSurface,
    SurfacePlot,
    WireframePlot,
)
from manim_plots.mobjects.system import Axes as Axes
from manim_plots.mobjects.system import CartesianAxes
from manim_plots.mobjects.system import NumberPlane as NumberPlane
from manim_plots.mobjects.themes import CYCLES, THEMES, Theme, get_theme, set_theme
from manim_plots.mobjects.three_d import ThreeDAxes as ThreeDAxes

__version__ = version("manim-plots")

__all__ = [
    "COLOR_CYCLE",
    "CYCLES",
    "THEMES",
    "AffineNode",
    "AngleFormatter",
    "ArraySource",
    "AxLinePlot",
    "BarPlot",
    "BarPlot3D",
    "Bounds",
    "BoxPlot",
    "CartesianAxes",
    "ColorMapping",
    "Colorbar",
    "Colormap",
    "CompiledMap",
    "ContourPlot",
    "ContourSetPlot",
    "DecimalFormatter",
    "DrawAxes",
    "EngFormatter",
    "ErrorBars",
    "FixedFormatter",
    "FixedLocator",
    "Flow",
    "FormatStrFormatter",
    "Formatter",
    "FunctionNode",
    "FunctionPlot",
    "FunctionScale",
    "FunctionSource",
    "GroupedBarPlot",
    "GrowSurface",
    "HeatmapPlot",
    "HexbinPlot",
    "Hist3DPlot",
    "HistPlot",
    "InsetAxes",
    "Labels",
    "Legend",
    "LinePlot",
    "LineStyle",
    "LinearScale",
    "Locator",
    "LogLocator",
    "LogScale",
    "ManimPlotsWarning",
    "Marker",
    "MaxNLocator",
    "MinorCountLocator",
    "Morph",
    "MultipleLocator",
    "Node",
    "NullFormatter",
    "NullLocator",
    "ParametricPlot",
    "ParametricSource",
    "Payload",
    "PieChart",
    "PlanePlot",
    "PolarAxes",
    "Scale",
    "ScaleNode",
    "ScatterPlot",
    "ScientificFormatter",
    "Shape",
    "ShowPoints",
    "SliceView",
    "Source",
    "StackPlot",
    "StemPlot",
    "SurfacePlot",
    "SymLogLocator",
    "SymLogScale",
    "Theme",
    "TraceCurve",
    "ViolinPlot",
    "VoxelPlot",
    "WaterfallPlot",
    "WireframePlot",
    "__version__",
    "colormaps",
    "get_theme",
    "set_theme",
]


def _configure_logging(log: logging.Logger, environ: Mapping[str, str]) -> None:
    """Attach the sinks the environment asks for (ADR 0002).

    ``MANIM_PLOTS_LOG`` names a level and turns on the console sink.
    ``MANIM_PLOTS_LOG_FILE`` names a file and turns on the file sink, at that level or
    at ``DEBUG``; the file opens here, so a bad path fails at import, not mid-render.
    With neither set nothing is attached, and a disabled call costs one level check.
    """
    level = environ.get("MANIM_PLOTS_LOG", "")
    path = environ.get("MANIM_PLOTS_LOG_FILE", "")
    if not (level or path):
        return
    log.setLevel(level.upper() or logging.DEBUG)
    # Manim may put its console handler on the root logger; propagating would print
    # every record twice.
    log.propagate = False
    sinks: list[logging.Handler] = []
    if level:
        sinks.append(logging.StreamHandler())
    if path:
        sinks.append(logging.FileHandler(path, encoding="utf-8"))
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    for sink in sinks:
        sink.setFormatter(formatter)
        log.addHandler(sink)


_log = logging.getLogger(__name__)
_log.addHandler(logging.NullHandler())
_configure_logging(_log, os.environ)

check_pins()
