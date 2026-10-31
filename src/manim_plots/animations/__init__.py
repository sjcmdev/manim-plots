"""Artist-aware animations and reversible presentation lifecycles."""

from .axes import BuildAxes, DrawAxes, HighlightTick, SweepPolar
from .bars import GrowBars, HighlightBar, ShrinkBars, SortBars
from .curves import AppendData, Morph, ShowPoints, TraceCurve
from .decorations import CloseInset, OpenInset
from .fields import Flow, GrowField
from .surfaces import (
    GrowStems,
    GrowSurface,
    RevealWaterfall,
    RevealWireframe,
    ShrinkSurface,
    SweepSurface,
)

__all__ = [
    "AppendData",
    "BuildAxes",
    "CloseInset",
    "DrawAxes",
    "Flow",
    "GrowBars",
    "GrowField",
    "GrowStems",
    "GrowSurface",
    "HighlightBar",
    "HighlightTick",
    "Morph",
    "OpenInset",
    "RevealWaterfall",
    "RevealWireframe",
    "ShowPoints",
    "ShrinkBars",
    "ShrinkSurface",
    "SortBars",
    "SweepPolar",
    "SweepSurface",
    "TraceCurve",
]
