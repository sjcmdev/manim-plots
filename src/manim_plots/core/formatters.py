"""Format complete tick lists as numeric or user-supplied LaTeX labels."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from math import floor, isfinite, log10
from numbers import Real
from typing import Protocol, runtime_checkable

import numpy as np

from manim_plots.core import FloatArray
from manim_plots.core.ticks import round_key


@dataclass(frozen=True)
class Labels:
    """Hold ordered labels, optional text-mode flags and an axis offset.

    Parameters
    ----------
    text
        One label per tick, in the input values' order.
    text_mode
        Optional flags selecting text rather than math mode for each label.
    offset
        Shared axis annotation; built-in formatters leave this as None.
    """

    text: Sequence[str]
    text_mode: Sequence[bool] | None = None
    offset: str | None = None

    def __post_init__(self) -> None:
        for i, label in enumerate(self.text):
            if not isinstance(label, str):
                raise TypeError(f"text[{i}] must be str")
        if self.text_mode is not None:
            if len(self.text_mode) != len(self.text):
                raise ValueError("text_mode must have the same length as text")
            for i, mode in enumerate(self.text_mode):
                if not isinstance(mode, bool):
                    raise TypeError(f"text_mode[{i}] must be bool")
        if self.offset is not None and not isinstance(self.offset, str):
            raise TypeError("offset must be str or None")


@runtime_checkable
class Formatter(Protocol):
    """Describe a formatter receiving all tick values at once."""

    def format_ticks(self, values: FloatArray) -> Labels:
        """Return one label for every tick value in input order.

        Parameters
        ----------
        values
            One-dimensional array of finite data positions.

        Returns
        -------
        Labels
            Ordered strings with optional rendering metadata.
        """
        ...


def _places(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an int")
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")


def _values(values: FloatArray) -> FloatArray:
    with np.errstate(all="ignore"):
        result = np.asarray(values, dtype=np.float64)
    if result.ndim != 1:
        raise ValueError("values must be one-dimensional")
    bad = ~np.isfinite(result)
    if np.any(bad):
        i = int(np.flatnonzero(bad)[0])
        raise ValueError(f"values[{i}] must be finite")
    return result


def decimal_places(step: float) -> int:
    """Count decimal places as Manim does, accounting for scientific exponents.

    Parameters
    ----------
    step
        Finite real spacing whose string representation determines precision.

    Returns
    -------
    int
        Number of fractional decimal digits, including a negative exponent.
    """
    if not isinstance(step, Real) or isinstance(step, bool):
        raise TypeError("step must be a real number")
    if not isfinite(step):
        raise ValueError("step must be finite")
    mantissa, _, exponent = str(step).lower().partition("e")
    fraction = mantissa.partition(".")[2]
    return max(0, len(fraction) - (int(exponent) if exponent else 0))


def _decimal(value: float, places: int, commas: bool = False) -> str:
    text = format(value, f"{',' if commas else ''}.{places}f")
    # DecimalNumber decides sign suppression using NumPy's rounded value.
    with np.errstate(all="ignore"):
        zero = bool(np.round(value, places) == 0)
    if text.startswith("-") and (zero or not text.strip("-0,.")):
        return text[1:]
    return text


class AngleFormatter:
    """Format radian angles as fractions of pi, tau, degrees or turns.

    Parameters
    ----------
    units
        ``"PI radians"``, ``"TAU radians"``, ``"degrees"``, ``"gradians"``,
        or None for fractions of a turn.
    compact_fraction
        Include the angular constant inside a fractional numerator.
    max_denominator
        Positive maximum denominator for rational approximations.
    """

    def __init__(
        self,
        units: str | None = "PI radians",
        compact_fraction: bool = True,
        max_denominator: int = 100,
    ) -> None:
        if units not in ("PI radians", "TAU radians", "degrees", "gradians", None):
            raise ValueError(
                "units must be PI radians, TAU radians, degrees, gradians or None"
            )
        if not isinstance(compact_fraction, bool):
            raise TypeError("compact_fraction must be bool")
        _places(max_denominator, "max_denominator")
        if max_denominator == 0:
            raise ValueError("max_denominator must be positive")
        self.units = units
        self.compact_fraction = compact_fraction
        self.max_denominator = max_denominator

    def format_ticks(self, values: FloatArray) -> Labels:
        """Return math-mode labels for angles in radians.

        Parameters
        ----------
        values
            Finite radian angles in input order.

        Returns
        -------
        Labels
            LaTeX strings, with a leading sign for negative angles.
        """
        values = _values(values)
        if self.units not in ("PI radians", "TAU radians"):
            factor, suffix = {
                "degrees": (360, r"^{\circ}"),
                "gradians": (400, r"^{g}"),
                None: (1, ""),
            }[self.units]
            return Labels([f"{v / (2 * np.pi) * factor:g}" + suffix for v in values])
        constant = r"\pi" if self.units == "PI radians" else r"\tau"
        divisor = np.pi if self.units == "PI radians" else 2 * np.pi
        labels = []
        for value in values:
            fraction = Fraction(float(value / divisor)).limit_denominator(
                self.max_denominator
            )
            numerator, denominator = abs(fraction.numerator), fraction.denominator
            sign = "-" if fraction.numerator < 0 else ""
            if numerator == 0:
                label = "0"
            elif denominator == 1:
                label = (str(numerator) if numerator != 1 else "") + constant
            elif self.compact_fraction:
                top = (str(numerator) if numerator != 1 else "") + constant
                label = rf"\tfrac{{{top}}}{{{denominator}}}"
            else:
                label = rf"\tfrac{{{numerator}}}{{{denominator}}}" + constant
            labels.append(sign + label)
        return Labels(labels)


class DecimalFormatter:
    """Produce Manim-style fixed-point numbers with shared precision.

    Parameters
    ----------
    num_decimal_places
        Nonnegative precision, or None to infer up to twelve decimal places.
    group_with_commas
        Whether thousands groups are separated by commas, as in Manim.
    """

    def __init__(
        self, num_decimal_places: int | None = None, *, group_with_commas: bool = True
    ) -> None:
        if num_decimal_places is not None:
            _places(num_decimal_places, "num_decimal_places")
        if not isinstance(group_with_commas, bool):
            raise TypeError("group_with_commas must be bool")
        self.num_decimal_places = num_decimal_places
        self.group_with_commas = group_with_commas

    def format_ticks(self, values: FloatArray) -> Labels:
        """Format ticks at an explicit or inferred common precision.

        Parameters
        ----------
        values
            Finite tick positions in any order.

        Returns
        -------
        Labels
            Fixed-point math-mode strings without negative zero.
        """
        checked = _values(values)
        places = self.num_decimal_places
        if places is None:
            canonical = [round_key(float(value)) for value in checked]
            places = next(
                (p for p in range(13) if all(round(v, p) == v for v in canonical)),
                12,
            )
            checked = np.array(canonical, dtype=np.float64)
        return Labels(
            [
                _decimal(float(value), places, self.group_with_commas)
                for value in checked
            ]
        )


class FormatStrFormatter:
    """Apply a printf-style format string to each tick.

    Parameters
    ----------
    fmt
        Format accepting a single float through the percent operator.
    """

    def __init__(self, fmt: str) -> None:
        if not isinstance(fmt, str):
            raise TypeError("fmt must be str")
        try:
            fmt % 1.0
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("fmt must accept a float") from exc
        self.fmt = fmt

    def format_ticks(self, values: FloatArray) -> Labels:
        """Format every value with the configured printf expression.

        Parameters
        ----------
        values
            Finite tick positions.

        Returns
        -------
        Labels
            Formatted math-mode strings.
        """
        return Labels([self.fmt % float(value) for value in _values(values)])


class ScientificFormatter:
    """Produce normalized mantissas and powers of ten as LaTeX.

    Parameters
    ----------
    decimals
        Nonnegative number of places in a mantissa.
    """

    def __init__(self, decimals: int = 1) -> None:
        _places(decimals, "decimals")
        self.decimals = decimals

    def _format(self, value: float) -> str:
        if value == 0:
            return "0"
        mantissa, exponent = f"{value:.{self.decimals}e}".split("e")
        power = f"10^{{{int(exponent)}}}"
        if abs(float(mantissa)) == 1:
            return ("-" if value < 0 else "") + power
        return rf"{mantissa} \times {power}"

    def format_ticks(self, values: FloatArray) -> Labels:
        """Format ticks independently, carrying a rounded mantissa of ten.

        Parameters
        ----------
        values
            Finite tick positions.

        Returns
        -------
        Labels
            Scientific math-mode strings; zero is printed as zero.
        """
        return Labels([self._format(float(value)) for value in _values(values)])


_PREFIXES = (
    "y",
    "z",
    "a",
    "f",
    "p",
    "n",
    r"\mu",
    "m",
    "",
    "k",
    "M",
    "G",
    "T",
    "P",
    "E",
    "Z",
    "Y",
)


class EngFormatter:
    """Produce engineering notation using SI prefixes from yocto to yotta.

    Parameters
    ----------
    unit
        Unit appended to the SI prefix in upright math text.
    places
        Nonnegative decimal precision, or None for twelve significant digits.
    """

    def __init__(self, unit: str = "", places: int | None = None) -> None:
        if not isinstance(unit, str):
            raise TypeError("unit must be str")
        if places is not None:
            _places(places, "places")
        self.unit, self.places = unit, places

    def _format(self, value: float) -> str:
        exponent = max(-24, min(24, floor(log10(abs(value)) / 3) * 3)) if value else 0
        mantissa = value / 10.0**exponent
        if self.places is None:
            text = f"{mantissa:.12g}"
        else:
            text = _decimal(mantissa, self.places)
        if abs(float(text)) >= 1000 and exponent < 24:
            exponent += 3
            mantissa = value / 10.0**exponent
            text = (
                f"{mantissa:.12g}"
                if self.places is None
                else _decimal(mantissa, self.places)
            )
        if value == 0:
            text = "0"
        prefix = _PREFIXES[exponent // 3 + 8]
        if prefix == r"\mu":
            suffix = prefix + (rf"\mathrm{{{self.unit}}}" if self.unit else "")
        else:
            unit = prefix + self.unit
            suffix = rf"\mathrm{{{unit}}}" if unit else ""
        return text + (r"\," + suffix if suffix else "")

    def format_ticks(self, values: FloatArray) -> Labels:
        """Format ticks with individual SI prefixes and the configured unit.

        Parameters
        ----------
        values
            Finite tick positions.

        Returns
        -------
        Labels
            Engineering math-mode strings.
        """
        return Labels([self._format(float(value)) for value in _values(values)])


class FixedFormatter:
    """Look up labels by a tick's canonical data value.

    Parameters
    ----------
    labels
        Mapping from finite positions to label strings.
    """

    def __init__(self, labels: Mapping[float, str]) -> None:
        if not isinstance(labels, Mapping):
            raise TypeError("labels must be a mapping")
        self.labels: dict[float, str] = {}
        for value, label in labels.items():
            if not isinstance(label, str):
                raise TypeError(f"labels[{value!r}] must be str")
            try:
                key = round_key(value)
            except (TypeError, ValueError) as exc:
                raise type(exc)(f"labels key {value!r}: {exc}") from exc
            self.labels[key] = label

    def format_ticks(self, values: FloatArray) -> Labels:
        """Return stored labels, using an empty string for unknown positions.

        Parameters
        ----------
        values
            Finite tick positions.

        Returns
        -------
        Labels
            Lookup results in input order.
        """
        return Labels(
            [self.labels.get(round_key(float(v)), "") for v in _values(values)]
        )


class NullFormatter:
    """Hide every numeric tick label."""

    def format_ticks(self, values: FloatArray) -> Labels:
        """Return an empty string for each position.

        Parameters
        ----------
        values
            Finite tick positions.

        Returns
        -------
        Labels
            Empty math-mode strings, one per tick.
        """
        return Labels([""] * len(_values(values)))


class FuncFormatter:
    """Wrap a per-value formatting callable.

    Parameters
    ----------
    function
        Callable accepting a float and returning a label string.
    """

    def __init__(self, function: Callable[[float], str]) -> None:
        if not callable(function):
            raise TypeError("function must be callable")
        self.function = function

    def format_ticks(self, values: FloatArray) -> Labels:
        """Call the function for every tick and validate its string output.

        Parameters
        ----------
        values
            Finite tick positions.

        Returns
        -------
        Labels
            Callable results in math mode and input order.
        """
        text: list[str] = []
        for i, value in enumerate(_values(values)):
            label = self.function(float(value))
            if not isinstance(label, str):
                raise TypeError(f"function output[{i}] must be str")
            text.append(label)
        return Labels(text)


def as_formatter(obj: object) -> Formatter:
    """Accept a formatter protocol object or wrap a per-value callable.

    Parameters
    ----------
    obj
        Object with format_ticks, or a callable returning a string.

    Returns
    -------
    Formatter
        Original formatter or a FuncFormatter wrapper.
    """
    if isinstance(obj, Formatter):
        return obj
    if callable(obj):
        return FuncFormatter(obj)
    raise TypeError("obj must be a formatter or callable")
