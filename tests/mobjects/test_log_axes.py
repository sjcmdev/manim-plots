"""Log axes, both spellings (D23, F-301, F-311, defects 8, 9, 10, 15c).

Rows AC-8 and AC-9 of `docs/acceptance/10-axis-decoration.md`. Manim's `LogBase` keeps
Manim's meaning (exponent ranges); the library's `x_scale="log"` takes data. The oracle
for the first is Manim's own `Axes` with `LogBase`; for the inverse it is the forward
map, because Manim 0.21's `p2c` is defect 15c.
"""

from __future__ import annotations

import manim
import numpy as np
import pytest
from manim import Axes, LogBase, tempconfig

import manim_plots as mp

from .helpers import RUN


# `axis_config` applies to both axes (AC-1), so y is logarithmic too: y = 1 is 10^0.
def log_axes(**axis_config):
    config = {"scaling": LogBase(), **axis_config}
    with tempconfig(RUN):
        return (
            mp.Axes(x_range=(-2, 6, 1), axis_config=config),
            Axes(x_range=(-2, 6, 1), axis_config=config),
        )


def test_ac8_logbase_ranges_are_in_exponents_and_c2p_is_manims():
    ours, theirs = log_axes()
    for x in (0.01, 1.0, 100.0, 1e6):
        np.testing.assert_allclose(ours.c2p(x, 1), theirs.c2p(x, 1), atol=1e-9)


def test_ac8_ticks_sit_at_manims_decades_plus_the_one_under_the_tip():
    ours, theirs = log_axes()
    our_x = sorted(t.get_center()[0] for t in ours.x_axis.ticks)
    their_x = sorted(t.get_center()[0] for t in theirs.x_axis.ticks)
    assert all(np.isclose(our_x, x, atol=1e-9).any() for x in their_x)
    assert len(our_x) == len(their_x) + 1


def test_ac8_custom_labels_are_powers_of_ten():
    # Manim puts LogBase's custom labels in `labels`, through add_labels.
    ours, theirs = log_axes(include_numbers=True)
    # Every one of Manim's, plus the one under the tip (F-411).
    assert len(ours.x_axis.labels) == len(theirs.x_axis.labels) + 1
    for manims in theirs.x_axis.labels:
        assert any(
            np.allclose(mine.get_center(), manims.get_center(), atol=1e-6)
            for mine in ours.x_axis.labels
        ), manims.get_center()


def test_ac8_p2c_inverts_c2p_where_manim_021_does_not():
    ours, theirs = log_axes()
    for x in (0.01, 3.0, 100.0, 5e4):
        point = ours.c2p(x, 1)
        np.testing.assert_allclose(ours.p2c(point)[0], x, rtol=1e-9)
    if manim.__version__ == "0.22.0":
        point = theirs.c2p(100.0, 1)
        np.testing.assert_allclose(ours.p2c(point), theirs.p2c(point), rtol=1e-9)


def test_ac9_the_librarys_log_scale_takes_data_values():
    # Without tips: Manim shortens a line by its tip.
    ax = mp.Axes(x_range=(0.1, 1000), x_scale="log", tips=False)
    left, right = ax.x_axis.line.get_start(), ax.x_axis.line.get_end()
    np.testing.assert_allclose(ax.c2p(0.1, 0)[0], left[0], atol=1e-9)
    np.testing.assert_allclose(ax.c2p(1000, 0)[0], right[0], atol=1e-9)
    mid = ax.c2p(np.sqrt(0.1 * 1000), 0)[0]
    np.testing.assert_allclose(mid, (left[0] + right[0]) / 2, atol=1e-9)


def test_ac9_minor_ticks_between_decades():
    ax = mp.Axes(x_range=(1, 100), x_scale="log")
    minors = sorted(ax.p2c(t.get_center())[0] for t in ax.x_axis.minor_ticks)
    np.testing.assert_allclose(minors, [*range(2, 10), *range(20, 100, 10)], rtol=1e-9)


def test_ac9_a_range_touching_zero_is_normalised_not_propagated():
    ax = mp.Axes(x_range=(0, 100), x_scale="log")
    lo, hi = ax.x.range.value
    assert 0 < lo < 1e-200 and hi == 100
    with pytest.raises(ValueError):
        ax.c2p(0, 0)
