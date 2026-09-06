"""Check the matplotlib surface quoted in ``docs/parity-survey.md`` section 2.

matplotlib is not a dependency, so the survey's numbers cannot be guarded by a test the
way the Manim section is. This script is the next best thing: it enumerates the surface
and compares it, name by name, against the snapshot committed beside it.

    uv run --no-project --with matplotlib==3.11.1 python tools/mpl_surface.py

Add ``--update`` to rewrite the snapshot after deliberately surveying a new version, and
change ``SURVEYED_VERSION`` in the same commit.
"""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.scale as mscale
import matplotlib.ticker as mticker
from matplotlib.axes import Axes
from matplotlib.axes._base import _AxesBase
from matplotlib.axis import Axis

SURVEYED_VERSION = "3.11.1"
SNAPSHOT = Path(__file__).with_name("mpl_surface_snapshot.json")
GROUPS = ("axes", "axis", "locators", "formatters", "scales")


def own_public_callables(*classes: type) -> list[str]:
    """Public callables defined on the given classes themselves, not inherited."""
    names: set[str] = set()
    for cls in classes:
        names |= {
            name
            for name, value in vars(cls).items()
            if not name.startswith("_")
            and (
                inspect.isfunction(value)
                or isinstance(value, staticmethod | classmethod | property)
            )
        }
    return sorted(names)


def classes_named(suffix: str) -> list[str]:
    """Public classes in ``matplotlib.ticker`` whose name ends with ``suffix``.

    The class check matters: a release could replace a locator with a factory function
    of the same name, and a name-only sweep would not notice.
    """
    return sorted(
        name
        for name in dir(mticker)
        if name.endswith(suffix) and inspect.isclass(getattr(mticker, name))
    )


def surface() -> dict[str, Any]:
    """Enumerate the whole surveyed surface, version included."""
    return {
        "matplotlib": matplotlib.__version__,
        "axes": own_public_callables(Axes, _AxesBase),
        "axis": own_public_callables(Axis),
        "locators": classes_named("Locator"),
        "formatters": classes_named("Formatter"),
        "scales": sorted(mscale.get_scale_names()),
    }


def compare(live: dict[str, Any], snapshot: dict[str, Any]) -> list[str]:
    """Human-readable differences between the live surface and the snapshot."""
    problems: list[str] = []
    for group in GROUPS:
        added = sorted(set(live[group]) - set(snapshot[group]))
        removed = sorted(set(snapshot[group]) - set(live[group]))
        if added:
            problems.append(
                f"{group}: new in matplotlib, absent from the survey: {added}"
            )
        if removed:
            problems.append(f"{group}: in the survey, gone from matplotlib: {removed}")
    return problems


def main() -> None:
    """Compare the live surface against the snapshot, or rewrite the snapshot."""
    live = surface()
    if "--update" in sys.argv:
        SNAPSHOT.write_text(json.dumps(live, indent=1) + "\n", encoding="utf-8")
        print(f"snapshot rewritten from matplotlib {live['matplotlib']}")
        return

    if live["matplotlib"] != SURVEYED_VERSION:
        raise SystemExit(
            f"the survey quotes matplotlib {SURVEYED_VERSION}, this is "
            f"{live['matplotlib']}: rerun with "
            f"`uv run --no-project --with matplotlib=={SURVEYED_VERSION}`, or survey "
            f"the new version deliberately and rerun with --update"
        )

    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    if snapshot.get("matplotlib") != SURVEYED_VERSION:
        raise SystemExit(
            f"the snapshot was taken from matplotlib {snapshot.get('matplotlib')}, but "
            f"the survey quotes {SURVEYED_VERSION}: regenerate it with --update"
        )
    problems = compare(live, snapshot)
    if problems:
        raise SystemExit("\n".join(problems))

    counts = ", ".join(f"{group} {len(live[group])}" for group in GROUPS)
    print(f"matplotlib {live['matplotlib']} matches the snapshot: {counts}")


if __name__ == "__main__":
    main()
