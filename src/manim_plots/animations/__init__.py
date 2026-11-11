"""Artist-aware animations and reversible presentation lifecycles."""

from .axes import BuildAxes, DrawAxes, HighlightTick, SweepPolar
from .bars import (
    GrowBars,
    GrowStack,
    HighlightBar,
    RebinHistogram,
    RevealCells,
    RevealContours,
    ShrinkBars,
    SortBars,
)
from .curves import AppendData, Morph, ShowPoints, TraceCurve
from .decorations import CloseInset, FillColorbar, OpenInset, RevealLegend
from .fields import Flow, GrowField
from .helpers import (
    ExtendReference,
    GrowErrorBars,
    GrowRegion,
    GrowRiemann,
    RefineRiemann,
    RevealAnnotation,
    RevealCrosshair,
    SweepRegion,
    SweepSpan,
)
from .statistics import ExplodePie, GrowBoxPlot, SweepPie, UnfoldViolin
from .surfaces import (
    GrowStems,
    GrowSurface,
    RevealWaterfall,
    RevealWireframe,
    ShrinkSurface,
    SweepSurface,
)
from .volumes import StackVoxels, SweepIsovalue, SweepSlice

__all__ = [
    "AppendData",
    "BuildAxes",
    "CloseInset",
    "DrawAxes",
    "ExplodePie",
    "ExtendReference",
    "FillColorbar",
    "Flow",
    "GrowBars",
    "GrowBoxPlot",
    "GrowErrorBars",
    "GrowField",
    "GrowRegion",
    "GrowRiemann",
    "GrowStack",
    "GrowStems",
    "GrowSurface",
    "HighlightBar",
    "HighlightTick",
    "Morph",
    "OpenInset",
    "RebinHistogram",
    "RefineRiemann",
    "RevealAnnotation",
    "RevealCells",
    "RevealContours",
    "RevealCrosshair",
    "RevealLegend",
    "RevealWaterfall",
    "RevealWireframe",
    "ShowPoints",
    "ShrinkBars",
    "ShrinkSurface",
    "SortBars",
    "StackVoxels",
    "SweepIsovalue",
    "SweepPie",
    "SweepPolar",
    "SweepRegion",
    "SweepSlice",
    "SweepSpan",
    "SweepSurface",
    "TraceCurve",
    "UnfoldViolin",
]
