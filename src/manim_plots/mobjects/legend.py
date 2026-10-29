"""Legend handles and native text assembled entirely from library leaves."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from manim import ORIGIN, RIGHT, Mobject, Text, VGroup, VMobject

from manim_plots.core.payload import Payload
from manim_plots.core.shape import dash
from manim_plots.core.sources import Box
from manim_plots.mobjects.artists import ScatterPlot, _CurvePlot, _MarkerLeaf
from manim_plots.mobjects.errorbar import ErrorBars
from manim_plots.mobjects.leaves import Leaf


def _leaves(native: Mobject) -> VMobject:
    children = [_leaves(child) for child in native.submobjects]
    if len(native.points):
        leaf = Leaf(native.points)
        if isinstance(native, VMobject):
            leaf.match_style(native, family=False)
        else:
            leaf.set_color(native.get_color())
        leaf.submobjects = children
        return leaf
    group = VGroup(*children)
    if isinstance(native, VMobject):
        group.match_style(native, family=False)
    return group


def _handle(artist: _CurvePlot | ScatterPlot | ErrorBars) -> VMobject:
    if isinstance(artist, ErrorBars):
        parts: list[VMobject] = []
        if artist.line is not None:
            parts.append(_handle(artist.line))
        bar = artist.ybars if artist.ybars is not None else artist.xbars
        if bar is not None:
            points = np.column_stack(
                (np.zeros(4), np.linspace(-0.2, 0.2, 4), np.zeros(4))
            )
            parts.append(Leaf(points).match_style(bar, family=False))
        if artist.markers is not None:
            parts.append(_handle(artist.markers))
        return VGroup(*parts)
    if isinstance(artist, ScatterPlot):
        native = (
            artist.submobjects[0] if artist.submobjects else artist._marker_template
        )
        handle = _leaves(native).move_to(ORIGIN)
        for original, copied in zip(
            native.get_family(), handle.get_family(), strict=True
        ):
            if isinstance(original, _MarkerLeaf) and not original._visible:
                fill, stroke, background = original._opacities
                assert isinstance(copied, VMobject)
                copied.set_fill(opacity=fill, family=False)
                copied.set_stroke(opacity=stroke, family=False)
                copied.set_stroke(opacity=background, background=True, family=False)
        return handle
    points = np.column_stack((np.linspace(-0.25, 0.25, 4), np.zeros((4, 2))))
    if artist._dash is not None:
        payload = Payload("path", points, np.array([[0, 4]], dtype=np.intp))
        points = dash(
            payload,
            Box(np.array([-1.0, -1.0]), np.array([1.0, 1.0])),
            on=artist._dash[0],
            off=artist._dash[1],
        ).coords
    handle = Leaf(points)
    handle.match_style(artist, family=False)
    return handle


@dataclass(frozen=True)
class LegendEntry:
    """Keep an artist, its handle and its text together in display order.

    Parameters
    ----------
    artist, handle, label
        Original artist and the two displayed mobjects.
    """

    artist: _CurvePlot | ScatterPlot | ErrorBars
    handle: VMobject
    label: VMobject


class Legend(VGroup):
    """Lay out labelled artists from any coordinate systems.

    Parameters
    ----------
    *artists
        Artists with a label, retained in the supplied order.
    font_size
        Native Text font size.
    buff
        Horizontal and vertical space between entries, in scene units.
    """

    def __init__(
        self,
        *artists: _CurvePlot | ScatterPlot | ErrorBars,
        font_size: float = 24,
        buff: float = 0.25,
    ) -> None:
        super().__init__()
        self.font_size, self.buff = font_size, buff
        self.entries: list[LegendEntry] = []
        for artist in artists:
            if not isinstance(artist, (_CurvePlot, ScatterPlot, ErrorBars)):
                raise TypeError("artists must be plotting artists")
            text = artist.get_label()
            if text is None:
                raise ValueError("artist must have a label")
            handle = _handle(artist)
            label = _leaves(Text(text, font_size=font_size, color=handle.get_color()))
            self.entries.append(LegendEntry(artist, handle, label))
        self._layout()

    def _layout(self) -> None:
        rows = []
        for entry in self.entries:
            handle, label = entry.handle, entry.label
            # A fixed handle column keeps every label's left edge aligned.
            handle.move_to(np.array([0.25 - handle.width / 2, 0.0, 0.0]))
            label.next_to(np.array([0.25, 0.0, 0.0]), RIGHT, buff=self.buff)
            rows.append(VGroup(handle, label))
        self.submobjects = []
        self.add(*rows)
        cursor = 0.0
        for row in rows:
            row.shift(np.array([0.0, cursor - row.get_top()[1], 0.0]))
            cursor = row.get_bottom()[1] - self.buff
        self.move_to(ORIGIN)

    def _copy_entries(self, entries: list[LegendEntry]) -> Legend:
        result = Legend(font_size=self.font_size, buff=self.buff)
        result.entries = [
            LegendEntry(e.artist, e.handle.copy(), e.label.copy()) for e in entries
        ]
        result._layout()
        return result

    def merge(self, *others: Legend) -> Legend:
        """Return a new legend, omitting repeated artists.

        Parameters
        ----------
        *others
            Legends whose entries follow this legend's entries.

        Returns
        -------
        Legend
            Independent handles and labels in first-occurrence order.
        """
        entries: list[LegendEntry] = []
        for legend in (self, *others):
            if not isinstance(legend, Legend):
                raise TypeError("others must be Legend instances")
            for entry in legend.entries:
                if not any(e.artist is entry.artist for e in entries):
                    entries.append(entry)
        return self._copy_entries(entries)

    def split(self) -> list[Legend]:  # type: ignore[override]
        """Return one independent legend per entry, retaining display order."""
        return [self._copy_entries([entry]) for entry in self.entries]
