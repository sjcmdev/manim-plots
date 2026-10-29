"""The tick pool's plan (F-920, D25).

Rows P-1 and P-2 of `docs/acceptance/08-ticks-formatters-lifecycle.md`: the union of
keys along a sampled parameter path, in order of first appearance, plus spare leaves.
Which alphas an animation renders is task 11's, against plain Manim.
"""

from __future__ import annotations

import pytest

from manim_plots.core.scales import LinearScale
from manim_plots.core.ticks import SPARES, MultipleLocator, Pool, axis_ticks, plan_pool


def ticks_of_range(start: tuple[float, float], end: tuple[float, float]):
    def ticks_at(alpha: float):
        lo = (1 - alpha) * start[0] + alpha * end[0]
        hi = (1 - alpha) * start[1] + alpha * end[1]
        return axis_ticks(
            MultipleLocator(1.0), MultipleLocator(0.5), lo, hi, LinearScale(), 10
        )

    return ticks_at


def test_p1_the_union_of_keys_along_the_path_plus_spares():
    pool = plan_pool(ticks_of_range((0, 2), (3, 5)), [k / 12 for k in range(13)])
    assert isinstance(pool, Pool)
    majors = [key for level, key in pool.keys if level == "major"]
    assert majors == [0, 1, 2, 3, 4, 5]
    minors = [key for level, key in pool.keys if level == "minor"]
    assert minors == [1, 3, 5, 7, 9]
    assert pool.spares == SPARES == 8


def test_p1_alphas_are_visited_in_order():
    seen = []

    def ticks_at(alpha):
        seen.append(alpha)
        return ()

    plan_pool(ticks_at, [0.5, 0.0, 1.0])
    assert seen == [0.5, 0.0, 1.0]


def test_p1_spares_are_configurable_and_not_negative():
    assert plan_pool(lambda a: (), [0.0], spares=0).spares == 0
    with pytest.raises(ValueError):
        plan_pool(lambda a: (), [0.0], spares=-1)


def test_p2_a_key_that_leaves_and_returns_keeps_its_first_place():
    there_and_back = ticks_of_range((0, 1), (5, 6))
    path = [0.0, 0.5, 1.0, 0.5, 0.0]
    pool = plan_pool(lambda a: there_and_back(a), path)
    majors = [key for level, key in pool.keys if level == "major"]
    assert majors == sorted(set(majors), key=majors.index)
    assert len(majors) == len(set(majors))
    assert majors[:2] == [0, 1]
