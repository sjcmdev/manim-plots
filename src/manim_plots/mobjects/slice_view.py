"""The independently styleable parts of a surface slice and its profile."""

from __future__ import annotations

from manim import VGroup

from manim_plots.mobjects.artists import FunctionPlot, ParametricPlot
from manim_plots.mobjects.geometry import PlanePlot
from manim_plots.mobjects.surfaces import ContourPlot
from manim_plots.mobjects.system import CartesianAxes


class SliceView(VGroup):
    """Hold a moving plane, surface cut, two-dimensional axes and profile.

    Parameters
    ----------
    plane, cut, axes, profile
        Ordinary artists, retained in this order and available as attributes.
    """

    def __init__(
        self,
        plane: PlanePlot,
        cut: ParametricPlot | ContourPlot,
        axes: CartesianAxes,
        profile: FunctionPlot,
    ) -> None:
        self.plane, self.cut, self.axes, self.profile = plane, cut, axes, profile
        super().__init__(plane, cut, axes, profile)
