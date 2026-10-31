"""Artist-aware animations and reversible presentation lifecycles."""

from .axes import BuildAxes, DrawAxes, HighlightTick
from .bars import (
    GrowBars,
    GrowStack,
    HighlightBar,
    RevealCells,
    RevealContours,
    ShrinkBars,
    SortBars,
)
from .curves import AppendData, Morph, ShowPoints, TraceCurve
from .decorations import FillColorbar, RevealLegend
from .fields import Flow
from .helpers import (
    ExtendReference,
    GrowErrorBars,
    GrowRegion,
    GrowRiemann,
    RevealAnnotation,
    RevealCrosshair,
    SweepRegion,
    SweepSpan,
)
from .statistics import ExplodePie, GrowBoxPlot, SweepPie, UnfoldViolin
from .surfaces import GrowSurface, ShrinkSurface

__all__ = [
    "AppendData",
    "BuildAxes",
    "DrawAxes",
    "ExplodePie",
    "ExtendReference",
    "FillColorbar",
    "Flow",
    "GrowBars",
    "GrowBoxPlot",
    "GrowErrorBars",
    "GrowRegion",
    "GrowRiemann",
    "GrowStack",
    "GrowSurface",
    "HighlightBar",
    "HighlightTick",
    "Morph",
    "RevealAnnotation",
    "RevealCells",
    "RevealContours",
    "RevealCrosshair",
    "RevealLegend",
    "ShowPoints",
    "ShrinkBars",
    "ShrinkSurface",
    "SortBars",
    "SweepPie",
    "SweepRegion",
    "SweepSpan",
    "TraceCurve",
    "UnfoldViolin",
]
