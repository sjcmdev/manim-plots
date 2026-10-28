import logging
from collections.abc import Iterator

import pytest

import manim_plots


@pytest.fixture
def log(request: pytest.FixtureRequest) -> Iterator[logging.Logger]:
    logger = logging.getLogger(f"tests.logging.{request.node.name}")
    yield logger
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()


def test_the_package_logger_only_has_a_null_handler_by_default():
    handlers = logging.getLogger("manim_plots").handlers
    assert isinstance(handlers[0], logging.NullHandler)


def test_no_environment_attaches_nothing(log):
    manim_plots._configure_logging(log, {})
    assert log.handlers == []
    assert log.level == logging.NOTSET
    assert log.propagate


def test_the_environment_turns_on_console_and_file_sinks(log):
    environ = {"MANIM_PLOTS_LOG": "info", "MANIM_PLOTS_LOG_FILE": "never-written.log"}
    manim_plots._configure_logging(log, environ)
    console, file = log.handlers
    assert type(console) is logging.StreamHandler
    assert isinstance(file, logging.FileHandler)
    assert file.stream is None  # delayed: no file until the first record
    assert log.level == logging.INFO
    assert not log.propagate


def test_a_file_alone_logs_at_debug(log):
    manim_plots._configure_logging(log, {"MANIM_PLOTS_LOG_FILE": "never-written.log"})
    (file,) = log.handlers
    assert isinstance(file, logging.FileHandler)
    assert log.level == logging.DEBUG


def test_an_unknown_level_raises(log):
    with pytest.raises(ValueError, match="Unknown level"):
        manim_plots._configure_logging(log, {"MANIM_PLOTS_LOG": "loud"})
