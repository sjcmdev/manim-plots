"""Render short demo videos of the library, beside plain Manim, for review.

    uv run python tools/demos.py            # every demo
    uv run python tools/demos.py follow     # the demos whose name contains "follow"

Each demo is a function below; its docstring is its caption in the gallery
(`tools/gallery.py`). The videos go to ``tests/visual/_out/demos/``, which git ignores.
They are for the eye only: the tests, not these, check the behaviour.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

import numpy as np
from manim import (
    BLUE,
    DOWN,
    LEFT,
    PI,
    RIGHT,
    UP,
    YELLOW,
    Axes,
    Create,
    FadeIn,
    FadeOut,
    Indicate,
    Rotate,
    Scene,
    Text,
    Uncreate,
    ValueTracker,
    Wiggle,
    always_redraw,
    tempconfig,
)

import manim_plots as mp

OUT = Path(__file__).parents[1] / "tests" / "visual" / "_out"
DEMOS = OUT / "demos"
SMALL = {"x_range": (-3, 3, 1), "y_range": (-2, 2, 1), "x_length": 5.5, "y_length": 3.5}


def pair(scene: Scene, **kwargs: object) -> tuple[mp.Axes, Axes]:
    """Add titles; return the library's axes on the left and Manim's on the right."""
    ours = mp.Axes(**kwargs).to_edge(LEFT, buff=0.6)
    theirs = Axes(**kwargs).to_edge(RIGHT, buff=0.6)
    for ax, title in ((ours, "manim-plots"), (theirs, "plain Manim")):
        scene.add(Text(title, font_size=28).next_to(ax, UP, buff=0.4))
    return ours, theirs


def create_sine(scene: Scene) -> None:
    """`Create(ax)` and then `Create(ax.plot(np.sin))` on the default `mp.Axes()`."""
    ax = mp.Axes()
    curve = ax.plot(np.sin, color=BLUE)
    scene.play(Create(ax))
    scene.play(Create(curve), run_time=2)
    scene.wait(0.5)


def follow(scene: Scene) -> None:
    """Shift, rotate and scale the axes: the library's curve follows, Manim's stays.

    `ax.animate.shift`, `Rotate(ax)`, `ax.animate.scale`, on the left with the library's
    axes and on the right with plain Manim's.
    """
    ours, theirs = pair(scene, **SMALL)
    scene.add(ours, ours.plot(np.sin, color=BLUE))
    scene.add(theirs, theirs.plot(np.sin, color=BLUE))
    scene.wait(0.5)
    scene.play(ours.animate.shift(DOWN), theirs.animate.shift(DOWN))
    scene.play(Rotate(ours, PI / 6), Rotate(theirs, PI / 6))
    scene.play(ours.animate.scale(0.6), theirs.animate.scale(0.6))
    scene.wait(0.5)


def pan_and_zoom(scene: Scene) -> None:
    """Pan and zoom by trackers: the ticks and the curve follow on every frame.

    The x range is bound to a centre and a half width; the curve stays clipped to the
    axes.
    """
    centre, half = ValueTracker(0.0), ValueTracker(3.0)
    ax = mp.Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1), x_length=11, y_length=5)
    c, h = centre.get_value, half.get_value
    ax.x.range.bind(lambda: (c() - h(), c() + h()))
    curve = ax.plot(lambda x: np.sin(x) + 0.4 * np.sin(3 * x), color=BLUE)
    scene.add(ax, curve)
    scene.play(centre.animate.set_value(6), run_time=2)
    scene.play(half.animate.set_value(10), run_time=2)
    scene.play(centre.animate.set_value(0), half.animate.set_value(1.5), run_time=2)
    scene.wait(0.5)


def pole(scene: Scene) -> None:
    """Draw `1 / (x - 4.5)`: the library splits the curve at the pole.

    On axes whose x range excludes 0 the library's curve also stays inside the axes.
    Plain Manim's samples beside the pole reach about 1e15 scene units, and Cairo
    draws nothing of its curve.
    """
    ours, theirs = pair(
        scene, x_range=(-1, 10, 1), y_range=(-2, 2, 0.5), x_length=5.5, y_length=4
    )
    scene.add(ours, theirs)
    scene.play(
        Create(ours.plot(lambda x: 1 / (x - 4.5), color=YELLOW)),
        Create(theirs.plot(lambda x: 1 / (x - 4.5), color=YELLOW)),
        run_time=2,
    )
    scene.wait(0.5)


def lifecycle(scene: Scene) -> None:
    """Play Manim's animations on a bound curve.

    `Wiggle`; `Uncreate`, a range change, and `Create` drawing the current curve (Manim
    would draw nothing); `Indicate(ax)` with the curve still; `FadeOut` and `FadeIn`.
    """
    ax = mp.Axes(**SMALL)
    curve = ax.plot(np.cos, color=BLUE)
    scene.add(ax, curve)
    scene.play(Wiggle(curve))
    scene.play(Uncreate(curve))
    ax.x.range = (-1, 5)
    scene.wait(0.5)
    scene.play(Create(curve))
    scene.play(Indicate(ax))
    scene.play(FadeOut(curve))
    scene.play(FadeIn(curve))
    scene.wait(0.5)


def redraw(scene: Scene) -> None:
    """Redraw `sin(x + t)` on every frame with Manim's `always_redraw` idiom."""
    t = ValueTracker(0.0)
    ax = mp.Axes(**SMALL)
    wave = always_redraw(
        lambda: ax.plot(lambda x: np.sin(x + t.get_value()), color=BLUE)
    )
    scene.add(ax, wave)
    scene.play(t.animate.set_value(2 * PI), run_time=3)


def clip_margin(scene: Scene) -> None:
    """Grow `a sin x` past the axes with `clip=True`, `clip=0.4` and `clip=False`.

    The amplitude is a plot parameter bound to a tracker. `True` cuts the curve at the
    axes, a margin lets it pass by that much, `False` never cuts it, as Manim draws.
    """
    a = ValueTracker(1.5)
    small = {"x_range": (-3, 3, 1), "y_range": (-2, 2, 1), "x_length": 3.6}
    for k, (clip, title) in enumerate(
        [(True, "clip=True"), (0.4, "clip=0.4"), (False, "clip=False")]
    ):
        ax = mp.Axes(**small, y_length=2.4).move_to((k - 1) * 4.4 * RIGHT)
        curve = ax.plot(lambda x, a=1.5: a * np.sin(x), a=a, clip=clip, color=BLUE)
        scene.add(ax, curve, Text(title, font_size=26).next_to(ax, UP, buff=0.5))
    scene.play(a.animate.set_value(2.6), run_time=2)
    scene.play(a.animate.set_value(1.5), run_time=2)


def trace_and_morph(scene: Scene) -> None:
    """Trace `tanh(4x)` in data order, then morph a zigzag into a sine.

    `TraceCurve` moves at a steady speed in x although the samples crowd near 0;
    `Morph` turns a five-point zigzag into fifty samples of a sine without jitter.
    """
    ax = mp.Axes(**SMALL)
    scene.add(ax)
    curve = ax.plot(lambda x: np.tanh(4 * x), color=BLUE)
    scene.play(mp.TraceCurve(curve), run_time=2)
    scene.play(FadeOut(curve))
    zigzag = ax.line([-3, -1, 0, 1, 3], [0, 1.5, -1.5, 1.5, 0], color=YELLOW)
    xs = np.linspace(-3, 3, 50)
    sine = ax.line(xs, np.sin(xs), color=BLUE)
    scene.play(Create(zigzag))
    scene.play(mp.Morph(zigzag, sine), run_time=2)
    scene.wait(0.5)


def legend_and_styles(scene: Scene) -> None:
    """Draw three styled curves and their legend.

    Without colour keywords they take the colour cycle; dashed and dotted line styles;
    `ax.legend()` in the upper right corner, faded in with the curves.
    """
    ax = mp.Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1), x_length=10, y_length=5)
    curves = [
        ax.plot(np.sin, label="sin x"),
        ax.plot(np.cos, label="cos x", line_style=mp.LineStyle.DASHED),
        ax.plot(lambda x: x / 3, label="x / 3", line_style=mp.LineStyle.DOTTED),
    ]
    scene.play(mp.DrawAxes(ax))
    scene.play(*(Create(c) for c in curves), FadeIn(ax.legend()), run_time=2)
    scene.wait(0.5)


DEMO_LIST: list[Callable[[Scene], None]] = [
    create_sine,
    follow,
    pan_and_zoom,
    pole,
    lifecycle,
    redraw,
    clip_margin,
    trace_and_morph,
    legend_and_styles,
]


def render(demo: Callable[[Scene], None]) -> Path:
    """Render one demo at 720p30 and return the video's path."""

    class Demo(Scene):
        def construct(self) -> None:
            demo(self)

    with tempconfig(
        {
            "quality": "medium_quality",
            "disable_caching": True,
            "progress_bar": "none",
            "media_dir": str(OUT / "media"),
            "video_dir": str(DEMOS),
            "output_file": demo.__name__,
        }
    ):
        Demo().render()
    return DEMOS / f"{demo.__name__}.mp4"


def main() -> int:
    """Render the demos named on the command line, or all, and report failures."""
    wanted = sys.argv[1:]
    failed = []
    for demo in DEMO_LIST:
        if wanted and not any(w in demo.__name__ for w in wanted):
            continue
        try:
            print(render(demo), flush=True)
        except Exception as error:  # a demo is a probe: report it and go on
            failed.append(demo.__name__)
            print(f"{demo.__name__} FAILED: {error!r}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
