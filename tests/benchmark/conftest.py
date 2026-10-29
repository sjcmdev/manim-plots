"""Frame-cost benchmarks: F-1001 measured end to end (ADR 0002).

A test marked ``benchmark`` takes the ``measure_frames`` fixture and hands it a
``construct`` function. The scene plays at 1080p60 with Cairo in a dry run; TeX caches
go to ``.benchmarks/media``. Each frame is timed twice. ``update`` is
``Scene.update_to_time`` plus one read of the points of every moving family member,
which runs the lazy rebuilds the camera would trigger: the quantity F-1001 gates. The
camera's own later reads of those cached points fall in ``frame``, which adds
rasterisation: the quantity of F-1001's comparison with plain Manim. ``setup`` is each
play's ``compile_animation_data`` and ``begin_animations``, where keyed alignment and
simulation run: recorded, not gated. Each result goes to the terminal summary and to
``.benchmarks/``, with the machine it ran on.
"""

from __future__ import annotations

import json
import os
import platform
import re
import statistics
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from time import perf_counter_ns
from typing import Any

import pytest
from manim import Mobject, Scene, tempconfig
from manim.renderer.cairo_renderer import CairoRenderer

ROOT = Path(__file__).parents[2]
OUT = ROOT / ".benchmarks"
# The readings the release ships with (row PF-4 of task 13), written with --record.
RECORD = ROOT / "docs" / "benchmarks" / "0.1.json"
CONFIG = {
    "pixel_width": 1920,
    "pixel_height": 1080,
    "frame_rate": 60,
    "dry_run": True,
    "disable_caching": True,
    "progress_bar": "none",
    "media_dir": str(OUT / "media"),
}

Construct = Callable[[Scene], None]


@dataclass(frozen=True)
class Timing:
    """Milliseconds per frame."""

    median: float
    p95: float
    max: float

    @classmethod
    def of(cls, ns: list[int]) -> Timing:
        if len(ns) < 20:
            raise ValueError(f"{len(ns)} frames are too few for a p95")
        ms = [x / 1e6 for x in ns]
        p95 = statistics.quantiles(ms, n=20, method="inclusive")[-1]
        return cls(*(round(v, 4) for v in (statistics.median(ms), p95, max(ms))))


@dataclass(frozen=True)
class FrameStats:
    frames: int
    update: Timing
    frame: Timing
    setup_ms: tuple[float, ...]  # one per play


class _TimedRenderer(CairoRenderer):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.render_ns: list[int] = []

    def render(
        self, scene: Scene, time: float, moving: Iterable[Mobject] | None = None
    ) -> None:
        start = perf_counter_ns()
        super().render(scene, time, moving)
        self.render_ns.append(perf_counter_ns() - start)


def _measure(construct: Construct) -> FrameStats:
    update_ns: list[int] = []
    setup_ns: list[int] = []

    class BenchmarkScene(Scene):
        def construct(self) -> None:
            construct(self)

        def compile_animation_data(self, *args: Any, **kwargs: Any) -> Any:
            start = perf_counter_ns()
            result = super().compile_animation_data(*args, **kwargs)
            setup_ns.append(perf_counter_ns() - start)
            return result

        def begin_animations(self) -> None:
            start = perf_counter_ns()
            super().begin_animations()
            setup_ns[-1] += perf_counter_ns() - start

        def update_to_time(self, t: float) -> None:
            start = perf_counter_ns()
            super().update_to_time(t)
            # Already the flat family list: one read each runs the lazy rebuild.
            for member in self.moving_mobjects:
                _ = member.points
            update_ns.append(perf_counter_ns() - start)

    with tempconfig(CONFIG):
        renderer = _TimedRenderer()
        BenchmarkScene(renderer=renderer).render()
    frame_ns = [u + r for u, r in zip(update_ns, renderer.render_ns, strict=True)]
    setup = tuple(round(ns / 1e6, 4) for ns in setup_ns)
    return FrameStats(len(frame_ns), Timing.of(update_ns), Timing.of(frame_ns), setup)


def _machine() -> dict[str, Any]:
    return {
        "node": platform.node(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "cpus": os.cpu_count(),
        "python": platform.python_version(),
        "manim": version("manim"),
        "numpy": version("numpy"),
    }


@pytest.fixture
def measure_frames(
    request: pytest.FixtureRequest, report: list[str]
) -> Callable[[Construct], FrameStats]:
    """Time every frame of a scene; see the module docstring."""
    if request.node.get_closest_marker("benchmark") is None:
        pytest.fail("a benchmark needs @pytest.mark.benchmark", pytrace=False)

    def measure(construct: Construct) -> FrameStats:
        stats = _measure(construct)
        now = datetime.now(UTC)
        name = re.sub(r"[^\w.-]+", "_", request.node.name)
        out = OUT / f"{now:%Y%m%dT%H%M%S}-{name}.json"
        out.parent.mkdir(exist_ok=True)
        record = {
            "test": request.node.nodeid,
            "when": now.isoformat(timespec="seconds"),
            "machine": _machine(),
            **asdict(stats),
        }
        out.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        if request.config.getoption("--record"):
            kept = (
                json.loads(RECORD.read_text(encoding="utf-8"))
                if RECORD.exists()
                else {"readings": {}}
            )
            kept["machine"] = record["machine"]
            kept["when"] = record["when"]
            kept["readings"][request.node.nodeid] = asdict(stats)
            RECORD.parent.mkdir(parents=True, exist_ok=True)
            RECORD.write_text(json.dumps(kept, indent=2) + "\n", encoding="utf-8")
        report.append(
            f"{request.node.name}: {stats.frames} frames, update p95 "
            f"{stats.update.p95:.2f} ms, frame p95 {stats.frame.p95:.2f} ms, setup "
            f"max {max(stats.setup_ms):.2f} ms ({out.relative_to(ROOT).as_posix()})"
        )
        return stats

    return measure
