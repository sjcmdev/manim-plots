"""Formatters (F-501-F-504).

Rows F-1 to F-10 of `docs/acceptance/08-ticks-formatters-lifecycle.md`. Oracles: Manim's
own `NumberLine._decimal_places_from_step` and `DecimalNumber` conventions, matplotlib's
`EngFormatter` prefixes, and strings written out by hand.
"""

from __future__ import annotations

import numpy as np
import pytest
from manim import NumberLine

from manim_plots.core.formatters import (
    DecimalFormatter,
    EngFormatter,
    FixedFormatter,
    FormatStrFormatter,
    Formatter,
    FuncFormatter,
    Labels,
    NullFormatter,
    ScientificFormatter,
    as_formatter,
    decimal_places,
)


def text(formatter, *values: float) -> list[str]:
    return list(formatter.format_ticks(np.array(values, dtype=float)).text)


ALL = [
    DecimalFormatter(1),
    FormatStrFormatter("%.2f"),
    ScientificFormatter(),
    EngFormatter(),
    FixedFormatter({1.0: "one"}),
    NullFormatter(),
    FuncFormatter(lambda v: f"<{v}>"),
]


# --- F-1, F-2 ----------------------------------------------------------------------


def test_f1_labels_carry_no_offset_in_0_1():
    labels = Labels(["a", "b"])
    assert labels.text_mode is None and labels.offset is None
    with pytest.raises(ValueError):
        Labels(["a", "b"], text_mode=[True])


@pytest.mark.parametrize("formatter", ALL, ids=lambda f: type(f).__name__)
def test_f2_every_formatter_takes_the_whole_list(formatter):
    assert isinstance(formatter, Formatter)
    values = np.array([1.0, 2.0, 3.5])
    labels = formatter.format_ticks(values)
    assert isinstance(labels, Labels)
    assert len(labels.text) == 3
    assert labels.offset is None
    assert list(formatter.format_ticks(values[::-1]).text) == list(labels.text)[::-1]
    assert list(formatter.format_ticks(np.array([])).text) == []


# --- F-3: decimal places -------------------------------------------------------------


@pytest.mark.parametrize(
    "step", [1, 2, 0.5, 0.25, 0.1, 0.125, 2.0, 1.5, 0.001, 10, 0.3333]
)
def test_f3_decimal_places_are_manims_rule(step):
    assert decimal_places(step) == NumberLine._decimal_places_from_step(step)


@pytest.mark.parametrize(
    "step, places", [(1e-05, 5), (2.5e-07, 8), (1e20, 0), (1e-10, 10)]
)
def test_f3_scientific_notation_counts_its_exponent(step, places):
    assert "e" in str(step)
    assert decimal_places(step) == places


# --- F-4: decimal ------------------------------------------------------------------


def test_f4_decimal_is_manims_decimal_number_text():
    assert text(DecimalFormatter(2), 3.14159, -2.5, 0.0) == ["3.14", "-2.50", "0.00"]
    assert text(DecimalFormatter(0), 1234567.0) == ["1,234,567"]
    assert text(DecimalFormatter(1, group_with_commas=False), 1234.5) == ["1234.5"]


def test_f4_no_negative_zero():
    assert text(DecimalFormatter(1), -0.04, -0.0) == ["0.0", "0.0"]


@pytest.mark.parametrize(
    "values, expected",
    [
        ((0.0, 0.5, 1.0), ["0.0", "0.5", "1.0"]),
        ((0.0, 1.0, 2.0), ["0", "1", "2"]),
        ((0.25, 0.5), ["0.25", "0.50"]),
        ((0.1 + 0.2, 0.6), ["0.3", "0.6"]),
        ((2.5,), ["2.5"]),
    ],
)
def test_f4_places_derived_from_the_values(values, expected):
    assert text(DecimalFormatter(), *values) == expected


def test_f4_math_mode_and_no_negative_places():
    assert DecimalFormatter(1).format_ticks(np.array([1.0])).text_mode in (
        None,
        [False],
        (False,),
    )
    with pytest.raises(ValueError):
        DecimalFormatter(-1)


# --- F-5 to F-9 ----------------------------------------------------------------------


def test_f5_printf_style():
    assert text(FormatStrFormatter("%.1f s"), 2.0, 3.25) == ["2.0 s", "3.2 s"]
    assert text(FormatStrFormatter("%d"), 7.9) == ["7"]


def test_f5_a_format_that_cannot_take_a_float_fails_at_construction():
    with pytest.raises(ValueError):
        FormatStrFormatter("%s %s")
    with pytest.raises(ValueError):
        FormatStrFormatter("no placeholder at all %q")


def test_f6_scientific_latex():
    f = ScientificFormatter(1)
    assert text(f, 1500.0, 0.00025, 0.0) == [
        r"1.5 \times 10^{3}",
        r"2.5 \times 10^{-4}",
        "0",
    ]
    assert text(f, 1000.0, -1000.0, 1.0) == ["10^{3}", "-10^{3}", "10^{0}"]
    assert text(f, 9.96) == ["10^{1}"]
    assert text(ScientificFormatter(2), 12345.0) == [r"1.23 \times 10^{4}"]
    with pytest.raises(ValueError):
        ScientificFormatter(-1)


def test_f7_si_prefixes():
    assert text(EngFormatter(places=1), 1500.0, -2_500_000.0) == [
        r"1.5\,\mathrm{k}",
        r"-2.5\,\mathrm{M}",
    ]
    assert text(EngFormatter(unit="Hz", places=1), 1500.0) == [r"1.5\,\mathrm{kHz}"]
    assert text(EngFormatter(unit="s"), 2e-6) == [r"2\,\mu\mathrm{s}"]
    assert text(EngFormatter(), 1000.0, 5.0) == [r"1\,\mathrm{k}", "5"]
    assert text(EngFormatter(unit="Hz"), 5.0, 0.0) == [
        r"5\,\mathrm{Hz}",
        r"0\,\mathrm{Hz}",
    ]
    assert text(EngFormatter(), 3e24, 4e-24) == [r"3\,\mathrm{Y}", r"4\,\mathrm{y}"]


def test_f8_fixed_labels_by_value():
    f = FixedFormatter({1.0: "one", 0.3: "third"})
    assert text(f, 0.1 + 0.2, 1.0, 2.0) == ["third", "one", ""]


def test_f9_null():
    assert text(NullFormatter(), 1.0, 2.0) == ["", ""]


# --- F-10: wrapping ----------------------------------------------------------------


def test_f10_a_per_value_callable_is_wrapped():
    f = as_formatter(lambda v: f"{v:g} m")
    assert isinstance(f, FuncFormatter)
    assert text(f, 1.0, 2.5) == ["1 m", "2.5 m"]


def test_f10_a_formatter_is_returned_as_is():
    f = DecimalFormatter(1)
    assert as_formatter(f) is f


def test_f10_anything_else_raises():
    with pytest.raises(TypeError):
        as_formatter("%.2f")


def test_f10_a_wrapped_function_must_return_strings():
    with pytest.raises(TypeError):
        text(FuncFormatter(lambda v: v), 1.0)  # type: ignore[arg-type, return-value]
