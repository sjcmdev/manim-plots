"""Task 32: histograms in 2D, `step`, `stairs`, `stackplot`, rows HI and SP of
`docs/acceptance/32-histograms.md`.

The oracles: `numpy.histogram` for the counts, matplotlib's documented bar geometry and
step vertices written out, the colormap tables of task 25.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from manim import ManimColor

import manim_plots as mp

RNG = np.random.default_rng(11)
SAMPLE = RNG.normal(0, 1, 500)


def corners(mob: Any) -> np.ndarray:
    return np.asarray(mob.points)[::4]


def vertices(mob: Any) -> np.ndarray:
    points = np.asarray(mob.points)
    return np.vstack([points[::4], points[-1:]])


def data(ax: Any, points: np.ndarray) -> np.ndarray:
    return np.array([ax.p2c(p) for p in np.atleast_2d(points)])


def box(ax: Any, mob: Any) -> tuple[float, float, float, float]:
    d = data(ax, corners(mob))
    return (d[:, 0].min(), d[:, 0].max(), d[:, 1].min(), d[:, 1].max())


def fill_rgb(mob: Any) -> np.ndarray:
    return np.asarray(ManimColor(mob.get_fill_color()).to_rgb())


def axes(**kwargs: Any) -> Any:
    return mp.Axes(x_range=(-4, 4, 1), y_range=(0, 200, 50), **kwargs)


# --- HI -------------------------------------------------------------------------------


def test_hi1_counts_are_numpys():
    ax = axes()
    h = ax.hist(SAMPLE, bins=8, range=(-4, 4))
    assert isinstance(h, mp.HistPlot)
    counts, edges = np.histogram(SAMPLE, bins=8, range=(-4, 4))
    np.testing.assert_allclose(h.counts, counts)
    np.testing.assert_allclose(h.edges, edges)
    rule = ax.hist(SAMPLE, bins="sturges")
    np.testing.assert_allclose(rule.edges, np.histogram_bin_edges(SAMPLE, "sturges"))


def test_hi1_density_weights_cumulative():
    ax = axes()
    dense = ax.hist(SAMPLE, bins=8, range=(-4, 4), density=True)
    assert float(np.sum(dense.counts * np.diff(dense.edges))) == pytest.approx(1)
    w = np.full(500, 2.0)
    heavy = ax.hist(SAMPLE, bins=8, range=(-4, 4), weights=w)
    np.testing.assert_allclose(heavy.counts, 2 * np.histogram(SAMPLE, 8, (-4, 4))[0])
    cum = ax.hist(SAMPLE, bins=8, range=(-4, 4), cumulative=True)
    assert cum.counts[-1] == pytest.approx(np.sum((SAMPLE >= -4) & (SAMPLE <= 4)))
    back = ax.hist(SAMPLE, bins=8, range=(-4, 4), cumulative=-1)
    assert back.counts[0] == pytest.approx(cum.counts[-1])


def test_hi2_bars_from_the_edges():
    ax = axes()
    h = ax.hist(SAMPLE, bins=8, range=(-4, 4))
    assert isinstance(h.bars, mp.BarPlot)
    assert len(h.bars) == 8
    assert box(ax, h.bars[3]) == pytest.approx((-1, 0, 0, h.counts[3]), abs=1e-9)
    thin = ax.hist(SAMPLE, bins=8, range=(-4, 4), rwidth=0.5)
    assert box(ax, thin.bars[3])[:2] == pytest.approx((-0.75, -0.25), abs=1e-9)
    left = ax.hist(SAMPLE, bins=8, range=(-4, 4), align="left")
    assert box(ax, left.bars[3])[:2] == pytest.approx((-1.5, -0.5), abs=1e-9)


def test_hi3_datasets_side_by_side_and_stacked():
    ax = axes()
    a, b = SAMPLE[:250], SAMPLE[250:] + 1
    h = ax.hist([a, b], bins=8, range=(-4, 4))
    assert isinstance(h.bars, list) and len(h.bars) == 2
    dr, w, n = 0.8, 1.0, 2
    for k, bars in enumerate(h.bars):
        x0, x1, _, _ = box(ax, bars[3])
        centre = -1 + w / 2 - dr * w / 2 * (1 - 1 / n) + k * dr * w / n
        assert (x0 + x1) / 2 == pytest.approx(centre, abs=1e-9)
        assert x1 - x0 == pytest.approx(dr * w / n, abs=1e-9)
    assert fill_rgb(h.bars[0][3]) != pytest.approx(fill_rgb(h.bars[1][3]))
    s = ax.hist([a, b], bins=8, range=(-4, 4), stacked=True)
    low, high = box(ax, s.bars[0][4]), box(ax, s.bars[1][4])
    assert high[2] == pytest.approx(low[3], abs=1e-9)
    assert high[3] == pytest.approx(s.counts[0][4] + s.counts[1][4], abs=1e-9)


def test_hi4_step_and_stepfilled_outlines():
    ax = mp.Axes(x_range=(-4, 4, 1), y_range=(0, 400, 50))  # 4 bins: counts near 240
    h = ax.hist(SAMPLE, bins=4, range=(-4, 4), histtype="step")
    assert h.bars is None
    c, e = h.counts, h.edges
    expected = [(e[0], 0), (e[0], c[0])]
    for i in range(4):
        expected += [(e[i + 1], c[i])] + ([(e[i + 1], c[i + 1])] if i < 3 else [])
    expected += [(e[4], 0)]
    np.testing.assert_allclose(
        data(ax, vertices(h.outlines[0]))[:, :2], expected, atol=1e-9
    )
    filled = ax.hist(SAMPLE, bins=4, range=(-4, 4), histtype="stepfilled")
    assert filled.outlines[0].get_fill_opacity() == pytest.approx(1)


def test_hi5_colour_by_count_and_by_x():
    ax = axes()
    viridis = mp.colormaps["viridis"]
    h = ax.hist(SAMPLE, bins=8, range=(-4, 4), color_by="count")
    lo, hi = h.counts.min(), h.counts.max()
    for bar, count in zip(h.bars, h.counts, strict=True):
        np.testing.assert_allclose(
            fill_rgb(bar), viridis((count - lo) / (hi - lo)), atol=1.5 / 255
        )
    assert tuple(ax.colorbar(h).y_range[:2]) == pytest.approx((lo, hi))
    spectrum = ax.hist(SAMPLE, bins=8, range=(-4, 4), color_by="x", colorscale="plasma")
    plasma = mp.colormaps["plasma"]
    np.testing.assert_allclose(
        fill_rgb(spectrum.bars[0]), plasma((-3.5 + 4) / 8), atol=1.5 / 255
    )
    np.testing.assert_allclose(
        fill_rgb(spectrum.bars[7]), plasma((3.5 + 4) / 8), atol=1.5 / 255
    )
    with pytest.raises(ValueError, match="color_by"):
        ax.hist(SAMPLE, histtype="step", color_by="count")


def test_hi6_horizontal():
    ax = mp.Axes(x_range=(0, 200, 50), y_range=(-4, 4, 1))
    h = ax.hist(SAMPLE, bins=8, range=(-4, 4), orientation="horizontal")
    bars: Any = h.bars
    assert box(ax, bars[3]) == pytest.approx((0, h.counts[3], -1, 0), abs=1e-9)


def test_hi7_set_data_keeps_the_edges_and_the_bars():
    ax = mp.Axes(x_range=(-4, 4, 1), y_range=(0, 400, 50))  # the new counts reach 230
    h = ax.hist(SAMPLE, bins=8, range=(-4, 4), color_by="count")
    bar = h.bars[4]
    other = RNG.normal(1, 0.5, 500)
    h.set_data(other)
    assert h.bars[4] is bar
    np.testing.assert_allclose(h.counts, np.histogram(other, 8, (-4, 4))[0])
    assert box(ax, bar)[3] == pytest.approx(h.counts[4], abs=1e-9)
    h.set_data(other, bins=4)
    assert len(h.bars) == 4
    assert len(h.edges) == 5


def test_hi7_a_legend_entry_per_dataset():
    ax = axes()
    h = ax.hist([SAMPLE[:200], SAMPLE[200:]], bins=8, range=(-4, 4), label=["a", "b"])
    assert len(ax.legend().entries) == 2  # h held: the axes keep artists weakly
    assert h.counts.shape == (2, 8)


# --- SP -------------------------------------------------------------------------------


def test_sp1_step_vertices():
    ax = axes()
    x, y = [0, 1, 2], [10, 20, 15]
    pre = data(ax, vertices(ax.step(x, y)))[:, :2]
    np.testing.assert_allclose(pre, [(0, 10), (0, 20), (1, 20), (1, 15), (2, 15)])
    post = data(ax, vertices(ax.step(x, y, where="post")))[:, :2]
    np.testing.assert_allclose(post, [(0, 10), (1, 10), (1, 20), (2, 20), (2, 15)])
    mid = data(ax, vertices(ax.step(x, y, where="mid")))[:, :2]
    np.testing.assert_allclose(
        mid, [(0, 10), (0.5, 10), (0.5, 20), (1.5, 20), (1.5, 15), (2, 15)]
    )
    with pytest.raises(ValueError, match="where"):
        ax.step(x, y, where="end")


def test_sp2_stairs():
    ax = axes()
    st = ax.stairs([10, 30, 20], [0, 1, 2, 3])
    pts = data(ax, vertices(st))[:, :2]
    for e0, e1, v in ((0, 1, 10), (1, 2, 30), (2, 3, 20)):
        assert np.min(np.linalg.norm(pts - (e0, v), axis=1)) < 1e-9
        assert np.min(np.linalg.norm(pts - (e1, v), axis=1)) < 1e-9
    assert pts[0, 1] == pytest.approx(0) and pts[-1, 1] == pytest.approx(0)
    filled = ax.stairs([10, 30, 20], fill=True)
    assert filled.get_fill_opacity() > 0


def test_sp3_stackplot_regions():
    ax = mp.Axes(x_range=(0, 2, 1), y_range=(-40, 50, 10))
    x = np.array([0.0, 1.0, 2.0])
    st = ax.stackplot(x, [10, 20, 10], [5, 5, 30], labels=["a", "b"])
    assert isinstance(st, mp.StackPlot)
    assert len(st.regions) == 2
    top = data(ax, corners(st.regions[1]))
    assert top[:, 1].max() == pytest.approx(40)
    assert fill_rgb(st.regions[0]) != pytest.approx(fill_rgb(st.regions[1]))
    entries = ax.legend().entries
    assert len(entries) == 2
    handle = entries[1].handle
    assert handle.get_fill_opacity() > 0
    assert handle.width == pytest.approx(handle.height, rel=1e-6)
    np.testing.assert_allclose(fill_rgb(handle), fill_rgb(st.regions[1]), atol=1e-6)
    sym = ax.stackplot(x, [10, 20, 10], [10, 20, 10], baseline="sym")
    low = data(ax, corners(sym.regions[0]))
    assert low[:, 1].min() == pytest.approx(-20)
