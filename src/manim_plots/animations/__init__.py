"""Artist-aware animations and reversible presentation lifecycles."""

from .axes import BuildAxes, DrawAxes, HighlightTick
from .bars import GrowBars, HighlightBar, ShrinkBars, SortBars
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
from .surfaces import GrowSurface, ShrinkSurface

__all__ = [
    "AppendData",
    "BuildAxes",
    "DrawAxes",
    "ExtendReference",
    "FillColorbar",
    "Flow",
    "GrowBars",
    "GrowErrorBars",
    "GrowRegion",
    "GrowRiemann",
    "GrowSurface",
    "HighlightBar",
    "HighlightTick",
    "Morph",
    "RevealAnnotation",
    "RevealCrosshair",
    "RevealLegend",
    "ShowPoints",
    "ShrinkBars",
    "ShrinkSurface",
    "SortBars",
    "SweepRegion",
    "SweepSpan",
    "TraceCurve",
]
