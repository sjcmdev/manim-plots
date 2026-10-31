"""Task 36: axis kinds, rows DT, PC, LG, BK of `docs/acceptance/36-axis-kinds.md`.

The oracles: day counts from `datetime`, matplotlib's documented `AutoDateLocator`
tables and `ConciseDateFormatter` formats written out, the logit function, and the
piecewise-linear lengths of a broken axis.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta, timezone
from typing import Any

import numpy as np
import pytest

import manim_plots as mp

EPOCH = datetime(1970, 1, 1)


def days(d: datetime) -> float:
    return (d - EPOCH) / timedelta(days=1)


def ticks(locator: Any, lo: datetime, hi: datetime) -> list[datetime]:
    values = locator.values(days(lo), days(hi), mp.LinearScale(), 50)
    return [EPOCH + timedelta(days=float(v)) for v in values]


def data(ax: Any, points: Any) -> np.ndarray:
    return np.array([ax.p2c(p) for p in np.atleast_2d(np.asarray(points))])


# --- DT -------------------------------------------------------------------------------


def test_dt1_date2num_and_back():
    assert mp.date2num(datetime(1970, 1, 2)) == pytest.approx(1)
    noon = datetime(2024, 1, 1, 12)
    assert mp.date2num(noon) == pytest.approx(days(noon))
    assert mp.date2num(date(2024, 1, 1)) == pytest.approx(days(datetime(2024, 1, 1)))
    assert mp.date2num(np.datetime64("2024-01-01T12:00")) == pytest.approx(days(noon))
    plus_one = datetime(2024, 1, 1, 12, tzinfo=timezone(timedelta(hours=1)))
    assert mp.date2num(plus_one) == pytest.approx(days(noon) - 1 / 24)
    many = mp.date2num([noon, datetime(1970, 1, 2)])
    np.testing.assert_allclose(many, [days(noon), 1])
    assert mp.num2date(1.5) == datetime(1970, 1, 2, 12, tzinfo=UTC)
    back = mp.num2date(mp.date2num(datetime(2031, 5, 6, 7, 8, 9, 123456)))
    assert back == datetime(2031, 5, 6, 7, 8, 9, 123456, tzinfo=UTC)


def test_dt2_dates_make_a_date_axis():
    ax = mp.Axes(y_range=(0, 1, 1))
    first, last = datetime(2024, 1, 1), datetime(2024, 12, 31)
    line = ax.line([first, datetime(2024, 6, 1), last], [0, 1, 0])
    assert isinstance(ax.x.locator, mp.AutoDateLocator)
    assert isinstance(ax.x.formatter, mp.ConciseDateFormatter)
    assert tuple(ax.x_range[:2]) == pytest.approx((days(first), days(last)))
    np.testing.assert_allclose(
        ax.c2p(datetime(2024, 6, 1), 1), line.points[len(line.points) // 2], atol=1e-6
    )
    ax.set_x_range((datetime(2024, 3, 1), datetime(2024, 4, 1)))
    assert ax.x_range[0] == pytest.approx(days(datetime(2024, 3, 1)))
    rule = ax.axvline(datetime(2024, 3, 15))
    assert data(ax, rule.points)[0, 0] == pytest.approx(days(datetime(2024, 3, 15)))


def test_dt3_months_hours_and_years():
    loc = mp.AutoDateLocator()
    months = ticks(loc, datetime(2024, 1, 1), datetime(2024, 12, 31))
    assert months == [datetime(2024, m, 1) for m in range(1, 13)]
    hours = ticks(loc, datetime(2024, 1, 1), datetime(2024, 1, 4))
    assert hours == [datetime(2024, 1, 1) + timedelta(hours=6 * k) for k in range(13)]
    years = ticks(loc, datetime(2000, 1, 1), datetime(2030, 1, 1))
    assert years == [datetime(y, 1, 1) for y in range(2000, 2030, 4)]


def test_dt3_ticks_keep_their_keys_while_panning():
    loc = mp.AutoDateLocator()
    a = datetime(2024, 3, 1)
    assert loc.key(days(a)) == loc.key(days(a) + 1e-12)  # below a microsecond


def test_dt4_concise_labels_and_offset():
    fmt = mp.ConciseDateFormatter()
    months = [days(datetime(2024, m, 1)) for m in range(1, 13)]
    out = fmt.format_ticks(np.array(months))
    assert list(out.text) == ["2024", "Feb", "Mar", "Apr", "May", "Jun", "Jul",
                              "Aug", "Sep", "Oct", "Nov", "Dec"]  # fmt: skip
    assert not out.offset
    hours = [days(datetime(2024, 1, 1) + timedelta(hours=6 * k)) for k in range(13)]
    out = fmt.format_ticks(np.array(hours))
    assert list(out.text[:3]) == ["Jan-01", "06:00", "12:00"]
    assert out.text[4] == "Jan-02"
    assert out.offset == "2024-Jan-04"
    assert out.text_mode is not None and all(out.text_mode)


def test_dt5_the_offset_label_is_shown():
    ax = mp.Axes(y_range=(0, 1, 1))
    hold = ax.line([datetime(2024, 1, 1), datetime(2024, 1, 4)], [0, 1])
    assert ax.x.offset_label is not None
    assert str(getattr(ax.x.offset_label, "text", "")) == "2024-Jan-04"
    assert ax.x.offset_label.get_top()[1] < ax.x.line.get_bottom()[1]
    assert mp.Axes().x.offset_label is None
    assert hold is not None


# --- PC -------------------------------------------------------------------------------


def test_pc1_percent():
    fmt = mp.PercentFormatter(xmax=1)
    assert list(fmt.format_ticks(np.array([0, 0.25, 0.5])).text) == [
        r"0\%",
        r"25\%",
        r"50\%",
    ]
    one = mp.PercentFormatter(xmax=1, decimals=1)
    assert one.format_ticks(np.array([0.25])).text[0] == r"25.0\%"
    assert mp.PercentFormatter().format_ticks(np.array([10.0])).text[0] == r"10\%"
    bare = mp.PercentFormatter(symbol="")
    assert bare.format_ticks(np.array([12.5])).text[0] == "12.5"


# --- LG -------------------------------------------------------------------------------


def test_lg1_logit_scale():
    scale = mp.LogitScale()
    np.testing.assert_allclose(
        scale.forward(np.array([0.5, 0.9, 0.01])), [0, np.log10(9), np.log10(1 / 99)]
    )
    np.testing.assert_allclose(scale.inverse(np.array([0.0, 1.0])), [0.5, 10 / 11])
    ax = mp.Axes(y_scale="logit", y_range=(0.001, 0.999))
    assert isinstance(ax.y.locator, mp.LogitLocator)
    assert isinstance(ax.y.formatter, mp.LogitFormatter)
    mid = (ax.c2p(0, 0.001)[1] + ax.c2p(0, 0.999)[1]) / 2
    assert ax.c2p(0, 0.5)[1] == pytest.approx(mid)


def test_lg2_lg3_logit_ticks_and_labels():
    values = mp.LogitLocator().values(0.001, 0.999, mp.LogitScale(), 20)
    np.testing.assert_allclose(values, [0.001, 0.01, 0.1, 0.5, 0.9, 0.99, 0.999])
    labels = mp.LogitFormatter().format_ticks(np.asarray(values)).text
    assert list(labels) == [
        "10^{-3}",
        "10^{-2}",
        "10^{-1}",
        r"\frac{1}{2}",
        "1-10^{-1}",
        "1-10^{-2}",
        "1-10^{-3}",
    ]
    assert mp.LogitFormatter().format_ticks(np.array([0.3])).text[0] == "0.3"


# --- BK -------------------------------------------------------------------------------


def broken() -> Any:
    ax = mp.Axes(x_range=(0, 10, 1), y_range=(0, 10, 1), y_length=6)
    ax.y.set_breaks([(2, 8)], gap=0.05)
    return ax


def test_bk1_lengths_of_the_pieces():
    ax = broken()
    assert ax.y.breaks == ((2.0, 8.0),)
    y0 = ax.c2p(0, 0)[1]
    assert ax.c2p(0, 2)[1] - y0 == pytest.approx(0.5 * 0.95 * 6)
    assert ax.c2p(0, 8)[1] - y0 == pytest.approx(0.5 * 0.95 * 6 + 0.3)
    assert ax.c2p(0, 10)[1] - y0 == pytest.approx(6)
    assert ax.p2c(ax.c2p(0, 9))[1] == pytest.approx(9)
    with pytest.raises(ValueError, match="breaks"):
        ax.y.set_breaks([(2, 12)])
    with pytest.raises(ValueError, match="scale"):
        mp.Axes(y_scale="log", y_range=(1, 1000)).y.set_breaks([(10, 100)])
    ax.y.set_breaks([])
    assert ax.c2p(0, 5)[1] - y0 == pytest.approx(3)


def test_bk2_ticks_line_and_marks():
    ax = broken()
    assert ax.y.ticks.at(1.0) is not None
    with pytest.raises(KeyError):
        ax.y.ticks.at(5.0)
    assert len(ax.y.line.get_subpaths()) == 2
    assert len(ax.y.break_marks) == 4


def test_bk3_artists_are_cut_at_the_break():
    ax = broken()
    g = ax.plot(lambda x: x)
    ys = data(ax, g.points)[:, 1]
    assert not np.any((ys > 2 + 1e-6) & (ys < 8 - 1e-6))
    assert len(g.get_subpaths()) >= 2
