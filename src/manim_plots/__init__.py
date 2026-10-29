"""Correct, extensible plotting primitives for Manim."""

import logging
import os
from collections.abc import Mapping
from importlib.metadata import version

from manim_plots.core import ManimPlotsWarning
from manim_plots.core.nodes import CompiledMap
from manim_plots.core.payload import Payload
from manim_plots.core.scales import (
    FunctionScale,
    LinearScale,
    LogScale,
    Scale,
    SymLogScale,
)
from manim_plots.core.shape import Shape
from manim_plots.core.sources import (
    ArraySource,
    Bounds,
    FunctionSource,
    ParametricSource,
    Source,
)
from manim_plots.mobjects.context import check_pins

__version__ = version("manim-plots")

__all__ = [
    "ArraySource",
    "Bounds",
    "CompiledMap",
    "FunctionScale",
    "FunctionSource",
    "LinearScale",
    "LogScale",
    "ManimPlotsWarning",
    "ParametricSource",
    "Payload",
    "Scale",
    "Shape",
    "Source",
    "SymLogScale",
    "__version__",
]


def _configure_logging(log: logging.Logger, environ: Mapping[str, str]) -> None:
    """Attach the sinks the environment asks for (ADR 0002).

    ``MANIM_PLOTS_LOG`` names a level and turns on the console sink.
    ``MANIM_PLOTS_LOG_FILE`` names a file and turns on the file sink, at that level or
    at ``DEBUG``; the file opens here, so a bad path fails at import, not mid-render.
    With neither set nothing is attached, and a disabled call costs one level check.
    """
    level = environ.get("MANIM_PLOTS_LOG", "")
    path = environ.get("MANIM_PLOTS_LOG_FILE", "")
    if not (level or path):
        return
    log.setLevel(level.upper() or logging.DEBUG)
    # Manim may put its console handler on the root logger; propagating would print
    # every record twice.
    log.propagate = False
    sinks: list[logging.Handler] = []
    if level:
        sinks.append(logging.StreamHandler())
    if path:
        sinks.append(logging.FileHandler(path, encoding="utf-8"))
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    for sink in sinks:
        sink.setFormatter(formatter)
        log.addHandler(sink)


_log = logging.getLogger(__name__)
_log.addHandler(logging.NullHandler())
_configure_logging(_log, os.environ)

check_pins()
