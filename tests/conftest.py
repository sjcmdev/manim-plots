"""Options and the terminal summary shared by the visual and benchmark harnesses."""

from __future__ import annotations

import pytest

REPORT = pytest.StashKey[list[str]]()


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-baselines",
        action="store_true",
        help="write a missing or changed visual baseline instead of failing",
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
