"""Shared fixtures for the animation specs (tasks 40-44)."""

from __future__ import annotations

import shutil

import pytest
from manim import Text


@pytest.fixture(autouse=True)
def text_without_tex(monkeypatch):
    # A sandbox without TeX draws glyphs with Pango; the gate keeps real TeX.
    if shutil.which("latex") is None:
        monkeypatch.setattr("manim_plots.mobjects.leaves.MathTex", Text)
        monkeypatch.setattr("manim_plots.mobjects.polar.MathTex", Text)
