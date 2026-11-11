"""The core pipeline's share of F-1001's frame (row BM-1 of task 07's acceptance table).

Four artists of 2 000 samples go through sampling, `Map`, smoothing, clipping and the
frame on every frame of an animated range, on an affine and on a warped frame. This is
the first reading of the 4 ms margin, without Manim's mobjects: recorded, not gated.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from time import perf_counter_ns

import numpy as np
import pytest

from manim_plots.core.nodes import AffineNode, Chain, FrameMap, ScaleNode, SystemMap
from manim_plots.core.scales import LinearScale
from manim_plots.core.shape import clip, smooth
from manim_plots.core.sources import Box, FunctionSource

from .conftest import OUT, Timing, _machine

LOWER, UPPER = np.array([-5.0, -3.0]), np.array([5.0, 3.0])
FRAMES = 60


def frame(kind: str) -> FrameMap:
    nodes = FrameMap.lattice(LOWER, UPPER, 33)
    if kind == "warped":
        x, y = nodes[:, 0], nodes[:, 1]
        nodes = np.c_[x + 0.05 * np.sin(y), y + 0.05 * np.cos(x), nodes[:, 2]]
    return FrameMap(LOWER, UPPER, nodes)


def data_chain(lo: float, hi: float) -> Chain:
    sx = (UPPER[0] - LOWER[0]) / (hi - lo)
    sy = (UPPER[1] - LOWER[1]) / 4.0
    return Chain(
        [
            ScaleNode(LinearScale(), 0, 2),
            AffineNode.from_parts(
                np.diag([sx, sy]), np.array([LOWER[0] - lo * sx, LOWER[1] + 2.0 * sy])
            ),
        ]
    )


@pytest.mark.benchmark
@pytest.mark.parametrize("kind", ["affine", "warped"])
def test_core_pipeline_four_artists_of_2000_samples(kind, report):
    placement = frame(kind)
    bounds = Box(LOWER, UPPER)
    sources = [
        FunctionSource(
            lambda x, k=k: np.sin(x + k),
            x_range=(-8.0, 8.0, 16 / 1999),
            use_vectorized=True,
        )
        for k in range(4)
    ]
    ns = []
    for i in range(FRAMES):
        hi = 7.0 + i / FRAMES  # an animated range
        data = data_chain(-7.0, hi)
        system = SystemMap(data, placement)
        start = perf_counter_ns()
        for source in sources:
            payload = clip(
                smooth(data.apply_payload(source.sample(system, bounds)), bounds),
                bounds,
            )
            placement.forward(payload.coords)
        ns.append(perf_counter_ns() - start)
    timing = Timing.of(ns)
    now = datetime.now(UTC)
    name = re.sub(r"[^\w.-]+", "_", f"core_pipeline_{kind}")
    OUT.mkdir(exist_ok=True)
    (OUT / f"{now:%Y%m%dT%H%M%S}-{name}.json").write_text(
        json.dumps(
            {
                "test": name,
                "when": now.isoformat(),
                "machine": _machine(),
                "frame": timing.__dict__,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    report.append(
        f"core pipeline, {kind} frame: median {timing.median} ms, p95 {timing.p95} ms, "
        f"max {timing.max} ms per frame (4 artists x 2000 samples)"
    )
