"""Options and the terminal summary shared by the visual and benchmark harnesses."""

from __future__ import annotations

import os

import pytest
from hypothesis import settings

REPORT = pytest.StashKey[list[str]]()

# The gate must not depend on luck or on a database left by an earlier run:
# derandomised, and no example database, whose files a sandboxed agent could lock.
settings.register_profile("gate", derandomize=True, database=None, deadline=None)
settings.register_profile("explore", max_examples=2000, database=None, deadline=None)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "gate"))


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-baselines",
        action="store_true",
        help="write a missing or changed visual baseline instead of failing",
    )
    parser.addoption(
        "--record",
        action="store_true",
        help="write each benchmark reading into docs/benchmarks/0.1.json",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.stash[REPORT] = []


def pytest_terminal_summary(
    terminalreporter: pytest.TerminalReporter, config: pytest.Config
) -> None:
    if lines := config.stash.get(REPORT, []):
        terminalreporter.section("manim-plots")
        for line in lines:
            terminalreporter.write_line(line)


@pytest.fixture
def report(request: pytest.FixtureRequest) -> list[str]:
    """Lines for the terminal summary: baselines written, benchmark results."""
    return request.config.stash[REPORT]
