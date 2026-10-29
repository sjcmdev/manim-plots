"""Run the four checks across the supported matrix, locally.

The matrix is F-1007's: Python 3.12 and 3.13 against Manim 0.21.0 and 0.22.0. There is
no hosted CI; this script is the gate a task branch passes before it merges into `dev`.

    uv run python tools/check.py           # the merge gate, render tests included
    uv run python tools/check.py --fast    # a quick local run without them
    uv run python tools/check.py --release # also build, install and import the package

The render-marked tests, the visual baselines among them, run in every cell: they are
the only check of the frame staying invisible (F-914) and of a bound artist not
freezing (F-915), so a merge must not skip them (ADR 0002). Benchmarks never run here:
they need one quiet machine, not a matrix.

mypy and pytest run as ``python -m ...`` on purpose. ``uv run --with`` overlays the
requested Manim only on the interpreter it starts, and a console script such as
``pytest`` resolves to the project venv's interpreter instead, which silently checks
the locked Manim. That mistake hid upstream's fix of defect 15c for a day.
"""

from __future__ import annotations

import itertools
import subprocess
import sys

PYTHONS = ("3.12", "3.13")
MANIMS = ("0.21.0", "0.22.0")


def run(label: str, *cmd: str) -> bool:
    """Run one command, echoing it, and report whether it passed."""
    print(f"\n== {label}: {' '.join(cmd)}", flush=True)
    return subprocess.run(cmd).returncode == 0


def main() -> int:
    """Run every check, keep going past failures, and list them at the end."""
    checks = [
        ("ruff check", ("uv", "run", "ruff", "check", ".")),
        ("ruff format", ("uv", "run", "ruff", "format", "--check", ".")),
    ]
    pytest_args = () if "--fast" in sys.argv[1:] else ("-m", "not benchmark")
    for python, manim in itertools.product(PYTHONS, MANIMS):
        env = (
            "uv",
            "run",
            "--isolated",
            "--python",
            python,
            "--with",
            f"manim=={manim}",
        )
        for tool, args in (("mypy", ()), ("pytest", pytest_args)):
            checks.append(
                (
                    f"py{python} manim {manim} {tool}",
                    (*env, "python", "-m", tool, *args),
                )
            )

    # The user documentation builds without a warning (row DO-1 of task 14).
    checks.append(
        (
            "docs",
            (
                "uv", "run", "--group", "docs", "python", "-m", "sphinx", "-W",
                "--keep-going", "-q", "-b", "html", "docs/site", "docs/site/_build/html",
            ),
        )
    )
    if "--release" in sys.argv[1:]:
        checks.append(("release", ("uv", "run", "python", "-m", "pytest", "-m", "release")))

    failed = [label for label, cmd in checks if not run(label, *cmd)]
    print("\n" + ("FAILED: " + ", ".join(failed) if failed else "All checks passed."))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
