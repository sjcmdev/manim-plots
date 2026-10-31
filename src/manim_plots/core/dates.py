"""Calendar adapters above the float-days coordinate pipeline."""

from datetime import UTC, date, datetime, timedelta
from typing import overload

import numpy as np
from numpy.typing import ArrayLike

from manim_plots.core import FloatArray
from manim_plots.core.formatters import Labels, _values
from manim_plots.core.scales import Scale
from manim_plots.core.ticks import _LocatorBase

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


@overload
def date2num(d: date | np.datetime64) -> float: ...
@overload
def date2num(d: object) -> float | FloatArray: ...


def date2num(d: object) -> float | FloatArray:
    """Convert dates to float days since 1970-01-01 UTC.

    Parameters
    ----------
    d
        Date, datetime, datetime64, or an array of dates. Naive dates use UTC.

    Returns
    -------
    float or FloatArray
        Epoch days with the input shape.
    """
    if isinstance(d, np.datetime64):
        if np.isnat(d):
            raise ValueError("date must not be NaT")
        return float(d.astype("datetime64[us]").astype(np.int64)) / 86400000000
    if isinstance(d, date):
        dt = d if isinstance(d, datetime) else datetime.combine(d, datetime.min.time())
        dt = dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)
        return (dt - _EPOCH) / timedelta(days=1)
    entries = np.asarray(d)
    if entries.dtype.kind == "M":
        if np.isnat(entries).any():
            raise ValueError("date must not contain NaT")
        return np.asarray(
            entries.astype("datetime64[us]").astype(np.float64) / 86400000000
        )
    if entries.ndim == 0:
        raise TypeError("date must be a date, datetime or datetime64")
    return np.array([date2num(v) for v in entries.flat], dtype=float).reshape(
        entries.shape
    )


@overload
def num2date(x: float) -> datetime: ...
@overload
def num2date(x: ArrayLike) -> list[datetime]: ...


def num2date(x: ArrayLike) -> datetime | list[datetime]:
    """Convert epoch days to UTC-aware datetimes.

    Parameters
    ----------
    x
        Finite epoch days, scalar or array.

    Returns
    -------
    datetime or list of datetime
        Dates rounded to the nearest microsecond, flattened for arrays.
    """
    values = np.asarray(x, dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("date numbers must be finite")
    dates = [
        _EPOCH
        + timedelta(
            days=int(np.floor(v)),
            microseconds=round(float(v - np.floor(v)) * 86400000000),
        )
        for v in values.flat
    ]
    return dates[0] if values.ndim == 0 else dates


class AutoDateLocator(_LocatorBase):
    """Locate calendar boundaries using matplotlib's default frequency tables."""

    _rounded_keys = False

    def key(self, value: float) -> datetime:
        """Return the UTC date rounded to a microsecond.

        Parameters
        ----------
        value
            Epoch days.

        Returns
        -------
        datetime
            Range-independent tick identity.
        """
        return num2date(value)

    def _values(self, lo: float, hi: float, scale: Scale, max_ticks: int) -> FloatArray:
        start, end = num2date(min(lo, hi)), num2date(max(lo, hi))
        seconds = (end - start).total_seconds()
        spans = [
            end.year - start.year + (end.month - start.month) / 12,
            (end.year - start.year) * 12 + end.month - start.month,
            seconds / 86400,
            seconds / 3600,
            seconds / 60,
            seconds,
        ]
        tables = [
            [1, 2, 4, 5, 10, 20, 40, 50, 100, 200, 400, 500, 1000, 2000, 4000],
            [1, 2, 3, 4, 6],
            [1, 2, 3, 7, 14, 21],
            [1, 2, 3, 4, 6, 12],
            [1, 5, 10, 15, 30],
            [1, 5, 10, 15, 30],
        ]
        level = next((i for i, n in enumerate(spans) if n >= 5), 5)
        maximum = [11, 12, 11, 12, 11, 11][level]
        interval = next(
            (n for n in tables[level] if spans[level] <= n * (maximum - 1)),
            tables[level][-1],
        )
        ticks = []
        if level == 0:
            for year in range(
                (start.year // interval) * interval, end.year + 1, interval
            ):
                if year >= 1:
                    ticks.append(datetime(year, 1, 1, tzinfo=UTC))
        elif level == 1:
            for year in range(start.year, end.year + 1):
                ticks.extend(
                    datetime(year, m, 1, tzinfo=UTC) for m in range(1, 13, interval)
                )
        else:
            day = start.replace(hour=0, minute=0, second=0, microsecond=0)
            while day <= end:
                if level == 2:
                    allowed = (day.day - 1) % interval == 0
                    if interval == 14:
                        allowed = day.day in (1, 15)
                    elif interval == 7:
                        allowed = day.day in (1, 8, 15, 22)
                    if allowed:
                        ticks.append(day)
                elif level == 3:
                    ticks.extend(
                        day + timedelta(hours=h) for h in range(0, 24, interval)
                    )
                elif level == 4:
                    ticks.extend(
                        day + timedelta(hours=h, minutes=m)
                        for h in range(24)
                        for m in range(0, 60, interval)
                    )
                else:
                    first = max(day, start.replace(microsecond=0))
                    cursor = first.replace(second=(first.second // interval) * interval)
                    while cursor < min(
                        day + timedelta(days=1), end + timedelta(seconds=1)
                    ):
                        ticks.append(cursor)
                        cursor += timedelta(seconds=interval)
                day += timedelta(days=1)
        return np.array([date2num(t) for t in ticks if start <= t <= end], dtype=float)


class ConciseDateFormatter:
    """Format complete date tick lists with concise calendar labels and an offset."""

    def format_ticks(self, values: FloatArray) -> Labels:
        """Return concise text labels and their shared date context.

        Parameters
        ----------
        values
            Finite epoch-day tick positions.

        Returns
        -------
        Labels
            Text-mode dates and optional shared offset.
        """
        dates = num2date(_values(values))
        if not dates:
            return Labels([], [], None)
        parts = [(d.year, d.month, d.day, d.hour, d.minute, d.second) for d in dates]
        level = next((i for i in range(5, -1, -1) if len({p[i] for p in parts}) > 1), 0)
        formats = ["%Y", "%b", "%d", "%H:%M", "%H:%M", "%S.%f"]
        zeros = ["", "%Y", "%b", "%b-%d", "%H:%M", "%H:%M"]
        offsets = ["", "%Y", "%Y-%b", "%Y-%b-%d", "%Y-%b-%d", "%Y-%b-%d %H:%M"]
        labels = [
            d.strftime(
                zeros[level]
                if p[level] == (1 if level in (1, 2) else 0)
                else formats[level]
            )
            for d, p in zip(dates, parts, strict=True)
        ]
        if level == 5:
            labels = [s.rstrip("0").rstrip(".") if "." in s else s for s in labels]
        offset = dates[-1].strftime(offsets[level])
        if level <= 1 and any(p[level] == 1 for p in parts):
            offset = ""
        return Labels(labels, [True] * len(labels), offset or None)
