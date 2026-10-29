"""Scales (F-301 to F-311).

Rows S-1 to S-15 of `docs/acceptance/06-core-contracts.md`. Oracles: closed-form values,
matplotlib's symlog formulas written out here independently, and the round-trip and
monotonicity invariants of F-305 under Hypothesis with fixed anchors.
"""

from __future__ import annotations

import math
import warnings
from typing import Any

import numpy as np
import pytest
from hypothesis import example, given
from hypothesis import strategies as st

from manim_plots.core.scales import (
    MINPOS_UNKNOWN,
    FunctionScale,
    LinearScale,
    LogScale,
    Scale,
    SymLogScale,
)

INF = math.inf
NAN = math.nan


def sqrt_scale(**kwargs: Any) -> FunctionScale:
    return FunctionScale(np.sqrt, np.square, (0.0, INF), closed=(True, False), **kwargs)


def all_scales() -> list[Scale]:
    return [LinearScale(), LogScale(), SymLogScale(), sqrt_scale()]


def assert_nan_where(result: np.ndarray, expected: list[float]) -> None:
    np.testing.assert_allclose(result, expected, rtol=1e-12, equal_nan=True)


# --- S-1, S-2: protocol and calling convention -------------------------------------


@pytest.mark.parametrize("scale", all_scales(), ids=lambda s: type(s).__name__)
def test_s1_every_scale_satisfies_the_protocol(scale):
    assert isinstance(scale, Scale)


@pytest.mark.parametrize("scale", all_scales(), ids=lambda s: type(s).__name__)
@pytest.mark.parametrize("member", ["domain", "closed", "increasing"])
def test_s1_members_are_read_only(scale, member):
    with pytest.raises(AttributeError):
        setattr(scale, member, getattr(scale, member))


@pytest.mark.parametrize("scale", all_scales(), ids=lambda s: type(s).__name__)
def test_s2_a_scalar_gives_a_zero_dimensional_float64_array(scale):
    for result in (scale.forward(4.0), scale.inverse(2.0)):
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float64
        assert result.shape == ()


@pytest.mark.parametrize("scale", all_scales(), ids=lambda s: type(s).__name__)
def test_s2_shape_is_kept_and_the_input_is_never_returned(scale):
    x = np.array([[1.0, 4.0], [9.0, 16.0]])
    before = x.copy()
    for direction in (scale.forward, scale.inverse):
        result = direction(x)
        assert result.shape == x.shape
        assert result is not x
        result[...] = 0.0
        np.testing.assert_array_equal(x, before)
    assert scale.forward([1, 4]).dtype == np.float64


@pytest.mark.parametrize("scale", all_scales(), ids=lambda s: type(s).__name__)
def test_s2_no_numpy_warning_escapes(scale):
    hostile = np.array([-1e308, -1.0, -0.0, 0.0, 1e-320, NAN, INF, -INF, 1e308])
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        scale.forward(hostile)
        scale.inverse(hostile)
        scale.inverse(np.array([1e6, -1e6, 1e308]))


# --- S-3: the NaN rule -------------------------------------------------------------


def test_s3_linear_maps_non_finite_input_to_nan():
    s = LinearScale()
    assert_nan_where(s.forward([NAN, INF, -INF, 2.5]), [NAN, NAN, NAN, 2.5])
    assert_nan_where(s.inverse([NAN, INF, -INF, -2.5]), [NAN, NAN, NAN, -2.5])


def test_s3_log_maps_the_open_bound_and_beyond_to_nan():
    s = LogScale()
    assert_nan_where(s.forward([-1.0, 0.0, NAN, INF, 100.0]), [NAN, NAN, NAN, NAN, 2.0])


def test_s3_log_inverse_is_nan_where_the_result_leaves_the_domain():
    # 10 ** 1e6 overflows to inf and 10 ** -1e6 underflows to the open bound 0.
    s = LogScale()
    result = s.inverse([NAN, INF, -INF, 2.0, 1e6, -1e6])
    assert_nan_where(result, [NAN, NAN, NAN, 100.0, NAN, NAN])


def test_s3_symlog_maps_only_non_finite_input_to_nan():
    s = SymLogScale()
    result = s.forward([NAN, INF, -INF, -1e300, 0.0, 1e300])
    assert np.isnan(result[:3]).all()
    assert np.isfinite(result[3:]).all()


def test_s3_a_closed_bound_is_in_the_domain_and_an_open_one_is_not():
    closed = FunctionScale(np.log, np.exp, (1.0, 10.0), closed=(True, True))
    assert_nan_where(
        closed.forward([1.0, 10.0, 10.5, 0.5]), [0.0, math.log(10), NAN, NAN]
    )
    half = FunctionScale(np.log, np.exp, (1.0, 10.0), closed=(False, True))
    assert_nan_where(half.forward([1.0, 10.0]), [NAN, math.log(10)])


def test_s3_sqrt_is_defined_at_its_closed_zero():
    assert_nan_where(sqrt_scale().forward([-1.0, 0.0, 4.0]), [NAN, 0.0, 2.0])


# --- S-4 to S-6: the three built-in scales -----------------------------------------


def test_s4_linear():
    s = LinearScale()
    assert s.domain == (-INF, INF)
    assert s.closed == (False, False)
    assert s.increasing is True
    x = np.array([-3.5, 0.0, 1e200])
    np.testing.assert_array_equal(s.forward(x), x)
    np.testing.assert_array_equal(s.inverse(x), x)


@pytest.mark.parametrize(
    "base, x, u", [(10, 1000.0, 3.0), (2, 8.0, 3.0), (math.e, math.e**2, 2.0)]
)
def test_s5_log_values(base, x, u):
    s = LogScale(base)
    assert s.domain == (0.0, INF)
    assert s.closed == (False, False)
    assert s.increasing is True
    np.testing.assert_allclose(s.forward(x), u, rtol=1e-12)
    np.testing.assert_allclose(s.inverse(u), x, rtol=1e-12)


def test_s5_a_base_below_one_decreases():
    s = LogScale(0.5)
    assert s.increasing is False
    np.testing.assert_allclose(
        s.forward([1.0, 2.0, 4.0]), [0.0, -1.0, -2.0], atol=1e-15
    )


def test_s5_a_base_that_is_not_a_number_raises_type_error():
    with pytest.raises(TypeError, match="base"):
        LogScale("10")  # type: ignore[arg-type]


@pytest.mark.parametrize("base", [0.0, -2.0, 1.0, NAN, INF])
def test_s5_an_impossible_base_raises_value_error(base):
    with pytest.raises(ValueError, match="base"):
        LogScale(base)


def symlog_forward(x: Any, base: float, linthresh: float, linscale: float) -> Any:
    """matplotlib's ``SymmetricalLogTransform.transform_non_affine``, written out."""
    adj = linscale / (1.0 - 1.0 / base)
    x = np.asarray(x, dtype=float)
    out = np.empty_like(x)
    lin = np.abs(x) <= linthresh
    out[lin] = x[lin] * adj
    big = ~lin
    out[big] = (
        np.sign(x[big])
        * linthresh
        * (adj + np.log(np.abs(x[big]) / linthresh) / np.log(base))
    )
    return out


def symlog_inverse(u: Any, base: float, linthresh: float, linscale: float) -> Any:
    """matplotlib's ``InvertedSymmetricalLogTransform.transform_non_affine``."""
    adj = linscale / (1.0 - 1.0 / base)
    u = np.asarray(u, dtype=float)
    out = np.empty_like(u)
    lin = np.abs(u) <= linthresh * adj
    out[lin] = u[lin] / adj
    big = ~lin
    out[big] = (
        np.sign(u[big]) * linthresh * np.power(base, np.abs(u[big]) / linthresh - adj)
    )
    return out


SYMLOG_PARAMETERS = [(10.0, 1.0, 1.0), (2.0, 0.5, 0.3), (math.e, 3.0, 2.0)]


@pytest.mark.parametrize("params", SYMLOG_PARAMETERS, ids=str)
def test_s6_symlog_is_matplotlibs_transform(params):
    s = SymLogScale(*params)
    linthresh = params[1]
    x = np.array(
        [
            -1e6,
            -50.0,
            -linthresh,
            -0.3 * linthresh,
            0.0,
            0.7 * linthresh,
            linthresh,
            7.0,
            1e9,
        ]
    )
    np.testing.assert_allclose(s.forward(x), symlog_forward(x, *params), rtol=1e-12)
    u = symlog_forward(x, *params)
    np.testing.assert_allclose(s.inverse(u), symlog_inverse(u, *params), rtol=1e-12)


def test_s6_symlog_defaults_and_domain():
    s = SymLogScale()
    assert (s.base, s.linthresh, s.linscale) == (10.0, 1.0, 1.0)
    assert s.domain == (-INF, INF)
    assert s.increasing is True


@pytest.mark.parametrize(
    "kwargs",
    [
        {"base": 1.0},
        {"base": 0.5},
        {"linthresh": 0.0},
        {"linthresh": -1.0},
        {"linscale": 0.0},
        {"linscale": NAN},
        {"base": INF},
    ],
    ids=str,
)
def test_s6_symlog_refuses_impossible_parameters(kwargs):
    with pytest.raises(ValueError):
        SymLogScale(**kwargs)


# --- S-7, S-8: round trip and monotonicity -----------------------------------------

magnitudes = st.floats(min_value=1e-300, max_value=1e300)
signed = st.one_of(st.just(0.0), magnitudes, magnitudes.map(lambda v: -v))
bases = st.sampled_from([1.5, 2.0, math.e, 10.0, 0.5])
symlog_params = st.sampled_from(SYMLOG_PARAMETERS)


def assert_round_trip(scale: Scale, x: float) -> None:
    back = float(scale.inverse(scale.forward(x)))
    assert abs(back - x) <= 1e-9 * abs(x), (x, back)


@given(signed)
@example(1e300)
@example(-1e-300)
def test_s7_linear_round_trip(x):
    assert_round_trip(LinearScale(), x)


@given(magnitudes, bases)
@example(1e-300, 10.0)
@example(1e300, 10.0)
@example(1.0, 0.5)
def test_s7_log_round_trip(x, base):
    assert_round_trip(LogScale(base), x)


@given(signed, symlog_params)
@example(0.0, (10.0, 1.0, 1.0))
@example(1.0, (10.0, 1.0, 1.0))
@example(-1.0, (10.0, 1.0, 1.0))
@example(0.5, (2.0, 0.5, 0.3))
@example(-3.0, (math.e, 3.0, 2.0))
@example(1e300, (10.0, 1.0, 1.0))
def test_s7_symlog_round_trip(x, params):
    assert_round_trip(SymLogScale(*params), x)


@given(st.one_of(st.just(0.0), magnitudes))
def test_s7_function_scale_round_trip(x):
    assert_round_trip(sqrt_scale(), x)


ordered_pairs = st.tuples(signed, signed).map(sorted).filter(lambda p: p[0] < p[1])
positive_pairs = (
    st.tuples(magnitudes, magnitudes).map(sorted).filter(lambda p: p[0] < p[1])
)


def assert_ordered(scale: Scale, a: float, b: float) -> None:
    fa, fb = float(scale.forward(a)), float(scale.forward(b))
    if scale.increasing:
        assert fa <= fb, (a, b, fa, fb)
    else:
        assert fa >= fb, (a, b, fa, fb)


@given(ordered_pairs, symlog_params)
def test_s8_symlog_is_increasing(pair, params):
    assert_ordered(SymLogScale(*params), *pair)


@given(positive_pairs, bases)
def test_s8_log_follows_its_declared_direction(pair, base):
    assert_ordered(LogScale(base), *pair)


# --- S-9, S-10: limit_range ----------------------------------------------------------


def test_s9_a_range_inside_the_domain_is_unchanged_and_made_of_floats():
    lo, hi = LinearScale().limit_range(0, 10, MINPOS_UNKNOWN)
    assert (lo, hi) == (0.0, 10.0)
    assert type(lo) is float and type(hi) is float
    assert LogScale().limit_range(1, 10, 0.5) == (1.0, 10.0)
    assert SymLogScale().limit_range(-1e9, 1e9, 1.0) == (-1e9, 1e9)


@pytest.mark.parametrize(
    "lo, hi, minpos, expected",
    [
        (0.0, 10.0, 1e-300, (1e-300, 10.0)),
        (-5.0, 10.0, 0.5, (0.5, 10.0)),
        (10.0, -5.0, 1e-3, (10.0, 1e-3)),
        (0.0, 0.5, 0.1, (0.1, 0.5)),
    ],
)
def test_s9_log_replaces_an_end_at_or_below_zero_by_minpos(lo, hi, minpos, expected):
    assert LogScale().limit_range(lo, hi, minpos) == expected


def test_s9_a_closed_bound_replaces_an_end_beyond_it():
    assert sqrt_scale().limit_range(-4.0, 9.0, 0.5) == (0.0, 9.0)
    assert sqrt_scale().limit_range(9.0, -4.0, 0.5) == (9.0, 0.0)


def shifted_log() -> FunctionScale:
    return FunctionScale(
        lambda x: np.log(x - 1.0), lambda u: np.exp(u) + 1.0, (1.0, INF)
    )


def test_s9_an_open_bound_away_from_zero_takes_the_nearest_float_inside():
    lo, hi = shifted_log().limit_range(0.0, 10.0, MINPOS_UNKNOWN)
    assert lo == np.nextafter(1.0, INF)
    assert hi == 10.0
    assert shifted_log().limit_range(0.0, 10.0, 0.5) == (1.5, 10.0)


def test_s9_an_open_upper_bound_is_approached_from_below():
    s = FunctionScale(lambda x: -np.log(-x), lambda u: -np.exp(-u), (-INF, 0.0))
    assert s.limit_range(-10.0, 5.0, 1e-3) == (-10.0, -1e-3)


@pytest.mark.parametrize(
    "lo, hi", [(-5.0, 0.0), (-5.0, -1.0), (0.0, 0.0), (-1.0, -1.0)]
)
def test_s9_a_range_wholly_outside_the_domain_raises(lo, hi):
    with pytest.raises(ValueError):
        LogScale().limit_range(lo, hi, 1.0)


@pytest.mark.parametrize(
    "lo, hi, name", [(NAN, 1.0, "lo"), (0.0, INF, "hi"), (-INF, 1.0, "lo")]
)
def test_s9_a_non_finite_end_raises_naming_it(lo, hi, name):
    with pytest.raises(ValueError, match=name):
        LinearScale().limit_range(lo, hi, 1.0)


@pytest.mark.parametrize("minpos", [0.0, -1.0, NAN, INF])
def test_s9_minpos_must_be_finite_and_positive(minpos):
    with pytest.raises(ValueError, match="minpos"):
        LogScale().limit_range(1.0, 10.0, minpos)


def test_s10_unknown_minpos():
    assert MINPOS_UNKNOWN == 1e-300


# --- S-11: value objects -----------------------------------------------------------


def test_s11_built_in_scales_compare_and_hash_by_value():
    assert LogScale(10) == LogScale(10.0)
    assert hash(LogScale(10)) == hash(LogScale(10.0))
    assert LinearScale() == LinearScale()
    assert SymLogScale() == SymLogScale(10.0, 1.0, 1.0)
    assert LogScale(2) != LogScale(10)
    assert len({LinearScale(), LinearScale(), LogScale(), LogScale(10.0)}) == 2


# --- S-12 to S-15: FunctionScale -----------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"forward": "sqrt"},
        {"inverse": None},
        {"closed": (1, 0)},
        {"closed": (True,)},
        {"increasing": 1},
        {"domain": ("a", 1.0)},
        {"domain": (0.0,)},
    ],
    ids=str,
)
def test_s12_wrong_types_raise_type_error(kwargs):
    arguments: dict[str, Any] = {
        "forward": np.sqrt,
        "inverse": np.square,
        "domain": (0.0, INF),
        "closed": (True, False),
        "increasing": True,
    } | kwargs
    with pytest.raises(TypeError):
        FunctionScale(**arguments)


@pytest.mark.parametrize(
    "domain, closed",
    [
        ((NAN, 1.0), (False, False)),
        ((2.0, 1.0), (False, False)),
        ((1.0, 1.0), (True, True)),
        ((0.0, INF), (False, True)),
        ((-INF, 0.0), (True, False)),
    ],
    ids=["nan bound", "reversed", "empty", "closed inf", "closed -inf"],
)
def test_s12_a_malformed_domain_raises_value_error(domain, closed):
    with pytest.raises(ValueError, match=r"domain|closed"):
        FunctionScale(np.sqrt, np.square, domain, closed=closed)


def falsification(
    word: str, *args: Any, **kwargs: Any
) -> pytest.ExceptionInfo[ValueError]:
    with pytest.raises(ValueError, match=word) as excinfo:
        FunctionScale(*args, **kwargs)
    return excinfo


def test_s13_a_scalar_only_forward_is_not_vectorized():
    excinfo = falsification("vectorized", math.log, np.exp, (0.0, INF))
    assert excinfo.value.__cause__ is not None


def test_s13_a_guard_that_turns_an_array_into_nan_is_not_vectorized():
    # Defect 8's shape: right per value, NaN for an array.
    def guarded(x):
        return np.log10(x) if np.ndim(x) == 0 else np.full(np.shape(x), np.nan)

    falsification("vectorized", guarded, lambda u: 10.0**u, (0.0, INF))


def test_s13_a_forward_that_reduces_the_array_is_not_vectorized():
    falsification("vectorized", lambda x: np.sum(np.sqrt(x)), np.square, (0.0, INF))


def test_s13_a_scalar_only_inverse_is_not_vectorized():
    falsification("vectorized", np.log, math.exp, (0.0, INF))


def test_s13_a_forward_that_is_nan_inside_its_domain_is_not_finite():
    def forward(x):
        return np.where(x > 100.0, np.nan, np.log(x))

    falsification("finite", forward, np.exp, (0.0, INF))


def test_s13_each_closed_bound_is_sampled():
    def forward(x):
        return np.where(x == 0.0, np.nan, np.sqrt(np.maximum(x, 0.0)))

    falsification("finite", forward, np.square, (0.0, INF), closed=(True, False))
    FunctionScale(forward, np.square, (0.0, INF), closed=(False, False))


def test_s13_a_non_monotonic_forward_is_refused():
    falsification("monotonic", np.sin, np.arcsin, (0.0, 10.0), closed=(True, True))


def test_s13_the_declared_direction_is_checked():
    falsification("monotonic", np.log, np.exp, (0.0, INF), increasing=False)


def test_s13_a_wrong_inverse_fails_the_round_trip():
    falsification("round trip", np.log, lambda u: np.exp(u) * 1.001, (0.0, INF))


@pytest.mark.parametrize(
    "forward, inverse, domain, closed, increasing",
    [
        (np.sqrt, np.square, (0.0, INF), (True, False), True),
        (np.arcsinh, np.sinh, (-INF, INF), (False, False), True),
        (np.cbrt, lambda u: u**3, (-INF, INF), (False, False), True),
        (np.log, np.exp, (0.0, INF), (False, False), True),
        (lambda x: -x, lambda u: -u, (-INF, INF), (False, False), False),
        (lambda x: 1.0 / x, lambda u: 1.0 / u, (0.0, INF), (False, False), False),
        (np.log, np.exp, (1.0, 10.0), (True, True), True),
    ],
    ids=["sqrt", "asinh", "cbrt", "log", "negate", "reciprocal", "bounded log"],
)
def test_s13_honest_scales_pass(forward, inverse, domain, closed, increasing):
    s = FunctionScale(forward, inverse, domain, closed=closed, increasing=increasing)
    assert s.domain == domain
    assert s.closed == closed
    assert s.increasing is increasing


def test_s13_the_docstring_admits_the_heuristic():
    assert "heuristic" in (FunctionScale.__doc__ or "").lower()


def test_s14_the_users_function_never_sees_an_out_of_domain_value():
    seen: list[np.ndarray] = []

    def forward(x):
        seen.append(np.array(x, dtype=float, copy=True))
        return np.sqrt(x)

    s = FunctionScale(forward, np.square, (0.0, INF), closed=(True, False))
    seen.clear()
    assert_nan_where(s.forward([-1.0, 0.0, 4.0, NAN, INF]), [NAN, 0.0, 2.0, NAN, NAN])
    assert all((v >= 0).all() and np.isfinite(v).all() for v in seen)


def test_s14_the_users_inverse_sees_only_finite_input():
    seen: list[np.ndarray] = []

    def inverse(u):
        seen.append(np.array(u, dtype=float, copy=True))
        return np.exp(u)

    s = FunctionScale(np.log, inverse, (0.0, INF))
    seen.clear()
    assert_nan_where(s.inverse([NAN, INF, 0.0, -1000.0]), [NAN, NAN, 1.0, NAN])
    assert all(np.isfinite(v).all() for v in seen)


def test_s15_function_scales_compare_by_identity():
    a = sqrt_scale()
    b = sqrt_scale()
    assert a == a
    assert a != b
