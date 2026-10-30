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
    GREEN,
    LEFT,
    PI,
    RED,
    RIGHT,
    UP,
    WHITE,
    YELLOW,
    Axes,
    Create,
    FadeIn,
    FadeOut,
    Indicate,
    Rotate,
    Scene,
    Text,
    Transform,
    Uncreate,
    ValueTracker,
    Wiggle,
    always_redraw,
    tempconfig,
)

import manim_plots as mp
from manim_plots import MultipleLocator, TickDirection

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

    `Wiggle`; `Uncreate`, a range change by `ax.animate.set_x_range`, and `Create`
    drawing the current curve (Manim would draw nothing); `Indicate(ax)` with the curve
    still; `FadeOut` and `FadeIn`.
    """
    ax = mp.Axes(**SMALL)
    curve = ax.plot(np.cos, color=BLUE)
    scene.add(ax, curve)
    scene.play(Wiggle(curve))
    scene.play(Uncreate(curve))
    scene.play(ax.animate.set_x_range((-1, 5)))
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


def show_call(scene: Scene, shown: list[Text], code: str) -> None:
    """Put the call being made at the top of the frame, replacing the previous one."""
    new = Text(code, font="Consolas", font_size=22).to_edge(UP, buff=0.35)
    if shown:
        scene.remove(shown.pop())
    shown.append(new)
    scene.add(new)


def legend_placement(scene: Scene) -> None:
    """Place the legend: the default corner, the other three, and beside the axes.

    `ax.legend()` sits in the upper right corner of the axes; `location` picks another
    corner and `font_size` its size; each call replaces the axes' legend. The legend
    is a mobject: `next_to` puts it outside the axes, and it moves with them.
    """
    shown: list[Text] = []
    ax = mp.Axes(x_range=(-3, 3, 1), y_range=(-3, 3, 1), x_length=7, y_length=4.6)
    ax.shift(1.6 * LEFT + 0.4 * DOWN)
    curves = [
        ax.plot(np.sin, label="sin x"),
        ax.plot(np.cos, label="cos x", line_style=mp.LineStyle.DASHED),
    ]
    show_call(scene, shown, "ax.legend()")
    legend = ax.legend()
    scene.add(ax, *curves)
    scene.play(FadeIn(legend))
    scene.wait(1)
    show_call(scene, shown, 'ax.legend("upper left")')
    ax.legend("upper left")
    scene.wait(1)
    show_call(scene, shown, 'ax.legend("lower left")')
    ax.legend("lower left")
    scene.wait(1)
    show_call(scene, shown, 'ax.legend("lower right")')
    ax.legend("lower right")
    scene.wait(1)
    show_call(scene, shown, 'ax.legend("upper left", font_size=32)')
    ax.legend("upper left", font_size=32)
    scene.wait(1)
    show_call(scene, shown, "ax.legend().next_to(ax, RIGHT, aligned_edge=UP)")
    ax.legend().next_to(ax, RIGHT, aligned_edge=UP)
    scene.wait(1)
    show_call(scene, shown, "self.play(ax.animate.shift(0.8 * RIGHT))")
    scene.play(ax.animate.shift(0.8 * RIGHT))
    scene.wait(0.6)


def axis_controls(scene: Scene) -> None:
    """Restyle the axes one call at a time, each call shown on screen.

    The axes move to the borders, a locator adds minor ticks, the ticks point out, the
    grids appear and a mirrored x axis closes the box. The curve stays where its data
    is throughout.
    """
    shown: list[Text] = []
    ax = mp.Axes(
        x_range=(-2, 10, 2),
        y_range=(-1, 5, 1),
        x_length=10,
        y_length=5,
        axis_config={"include_numbers": True},
    ).shift(0.4 * DOWN)
    curve = ax.plot(lambda x: 2.5 + 2 * np.sin(x), color=RED)
    show_call(scene, shown, 'ax = mp.Axes(..., axis_config={"include_numbers": True})')
    scene.add(ax, curve)
    scene.wait(1)
    show_call(scene, shown, 'ax.x.set_position("bottom")')
    ax.x.set_position("bottom")
    scene.wait(1.2)
    show_call(scene, shown, 'ax.y.set_position("left")')
    ax.y.set_position("left")
    scene.wait(1.2)
    show_call(
        scene, shown, "ax.x.set_locator(MultipleLocator(2), minor=MultipleLocator(1))"
    )
    ax.x.set_locator(MultipleLocator(2), minor=MultipleLocator(1))
    scene.wait(1.2)
    show_call(scene, shown, "ax.x.set_tick_style(direction=TickDirection.OUT)")
    ax.x.set_tick_style(direction=TickDirection.OUT)
    scene.wait(1.2)
    show_call(scene, shown, "ax.y.set_tick_style(direction=TickDirection.OUT)")
    ax.y.set_tick_style(direction=TickDirection.OUT)
    scene.wait(1.2)
    show_call(scene, shown, 'ax.x.set_grid("major", stroke_opacity=0.5)')
    ax.x.set_grid("major", stroke_opacity=0.5)
    scene.wait(1.2)
    show_call(scene, shown, 'ax.x.set_grid("minor", stroke_opacity=0.2)')
    ax.x.set_grid("minor", stroke_opacity=0.2)
    scene.wait(1.2)
    show_call(scene, shown, 'ax.y.set_grid("major", stroke_opacity=0.5)')
    ax.y.set_grid("major", stroke_opacity=0.5)
    scene.wait(1.2)
    show_call(scene, shown, "ax.x.mirror()")
    ax.x.mirror()
    scene.wait(1.2)
    show_call(scene, shown, 'ax.x.set_tick_style("minor", length=0.25, color=YELLOW)')
    ax.x.set_tick_style("minor", length=0.25, color=YELLOW)
    scene.wait(1.2)


def animate_data(scene: Scene) -> None:
    """Animate the data with Manim's own `.animate`, each call shown on screen.

    `ax.animate.set_x_range` pans the range while the ticks and numbers keep their
    identity; a plot parameter animates through `curve.animate.set_parameters`; data and
    geometry chain into one animation; `Transform` turns one plot into another.
    """
    shown: list[Text] = []
    ax = mp.Axes(
        x_range=(-3, 3, 1),
        y_range=(-3, 3, 1),
        x_length=9,
        y_length=5,
        axis_config={"include_numbers": True},
    ).shift(0.3 * DOWN)
    wave = ax.plot(lambda x, a=1.0: a * np.sin(x), color=BLUE)
    scene.add(ax, wave)
    show_call(scene, shown, "self.play(ax.animate.set_x_range((0, 10)))")
    scene.play(ax.animate.set_x_range((0, 10)), run_time=2)
    show_call(scene, shown, "self.play(wave.animate.set_parameters(a=2.5))")
    scene.play(wave.animate.set_parameters(a=2.5), run_time=1.5)
    show_call(scene, shown, "self.play(ax.animate.scale(0.7).set_x_range((-6, 6)))")
    scene.play(ax.animate.scale(0.7).set_x_range((-6, 6)), run_time=2)
    parabola = ax.plot(lambda x: x**2 / 6 - 2, color=YELLOW)
    show_call(scene, shown, "self.play(Transform(wave, parabola))")
    scene.play(Transform(wave, parabola), run_time=1.5)
    scene.wait(0.6)


def clip_per_axis(scene: Scene) -> None:
    """Clip one axis only: `clip=(True, False)` cuts at the sides, not the top.

    The left curve clips on both axes, the right one on x only, so its peaks pass over
    the axes while its ends stop at their sides; both follow an animated range.
    """
    a = ValueTracker(1.5)
    small = {
        "x_range": (-3, 3, 1),
        "y_range": (-2, 2, 1),
        "x_length": 5,
        "y_length": 2.6,
    }
    for k, clip in enumerate([True, (True, False)]):
        ax = mp.Axes(**small).move_to((2 * k - 1) * 3.4 * RIGHT + 0.5 * DOWN)
        curve = ax.plot(
            lambda x, a=1.5: a * np.sin(x), x_range=(-6, 6), a=a, clip=clip, color=BLUE
        )
        title = Text(f"clip={clip}", font="Consolas", font_size=24)
        scene.add(ax, curve, title.next_to(ax, UP, buff=0.9))
    scene.play(a.animate.set_value(2.8), run_time=2)
    scene.play(a.animate.set_value(1.5), run_time=1.5)


def t_label_slides(scene: Scene) -> None:
    """Slide a T label and lines to the graph with a tracker, no `always_redraw`.

    `get_T_label(t, graph, label=...)` takes the tracker itself, and the label is a
    callable of the value; `get_lines_to_point` takes a callable point. Both follow the
    axes when their range animates.
    """
    shown: list[Text] = []
    ax = mp.Axes(x_range=(-1, 5, 1), y_range=(-1, 6, 1), x_length=9, y_length=5)
    ax.shift(0.4 * DOWN)
    graph = ax.plot(lambda x: x**2 / 4 + 0.5, color=BLUE)
    t = ValueTracker(1.0)
    label = ax.get_T_label(t, graph, label=lambda x: f"{x:.1f}")
    lines = ax.get_lines_to_point(lambda: ax.i2gp(t.get_value(), graph), color=YELLOW)
    scene.add(ax, graph, label, lines)
    show_call(scene, shown, "self.play(t.animate.set_value(4))")
    scene.play(t.animate.set_value(4.0), run_time=2.5)
    show_call(scene, shown, "self.play(ax.animate.set_x_range((-1, 8)))")
    scene.play(ax.animate.set_x_range((-1, 8)), run_time=2)
    show_call(scene, shown, "self.play(t.animate.set_value(0.5))")
    scene.play(t.animate.set_value(0.5), run_time=2)
    scene.wait(0.5)


def secant_to_tangent(scene: Scene) -> None:
    """Close a secant into the tangent as `dx` goes to 0, then slide it along.

    `get_secant_slope_group(x, graph, dx=dx)` takes trackers for `x` and `dx`; at
    `dx = 0` the secant is the tangent. Its parts keep Manim's names and their styles.
    """
    shown: list[Text] = []
    ax = mp.Axes(x_range=(-1, 5, 1), y_range=(-1, 6, 1), x_length=9, y_length=5)
    ax.shift(0.4 * DOWN)
    graph = ax.plot(lambda x: x**2 / 4 + 0.5, color=BLUE)
    x, dx = ValueTracker(1.0), ValueTracker(2.0)
    secant = ax.get_secant_slope_group(
        x, graph, dx=dx, dx_label="dx", dy_label="dy", secant_line_length=7
    )
    scene.add(ax, graph, secant)
    show_call(scene, shown, "self.play(dx.animate.set_value(0))")
    scene.play(dx.animate.set_value(0.0), run_time=3)
    show_call(scene, shown, "self.play(x.animate.set_value(3.5))")
    scene.play(x.animate.set_value(3.5), run_time=2.5)
    scene.wait(0.5)


def riemann_refines(scene: Scene) -> None:
    """Refine a Riemann sum as `dx` shrinks, over the area it approaches.

    `get_riemann_rectangles(graph, dx=dx)` takes a tracker, so rectangles are added as
    `dx` shrinks, with Manim's colours; `get_area` draws the exact area under them.
    """
    shown: list[Text] = []
    ax = mp.Axes(x_range=(-1, 5, 1), y_range=(-1, 6, 1), x_length=9, y_length=5)
    ax.shift(0.4 * DOWN)
    graph = ax.plot(lambda x: x**2 / 4 + 0.5, color=BLUE)
    dx = ValueTracker(1.0)
    rects = ax.get_riemann_rectangles(graph, x_range=(0, 4), dx=dx, fill_opacity=0.7)
    area = ax.get_area(graph, x_range=(0, 4), opacity=0.25)
    scene.add(ax, area, rects, graph)
    show_call(scene, shown, "self.play(dx.animate.set_value(0.05))")
    scene.play(dx.animate.set_value(0.05), run_time=4)
    scene.wait(0.5)


def derived_graphs(scene: Scene) -> None:
    """Let a derivative and an antiderivative follow their parent's parameter.

    `plot_derivative_graph` and `plot_antiderivative_graph` follow the parent when its
    amplitude, a parameter bound to a tracker, animates.
    """
    a = ValueTracker(1.0)
    ax = mp.Axes(x_range=(-4, 4, 1), y_range=(-3, 3, 1), x_length=10, y_length=5.5)
    parent = ax.plot(lambda x, a=1.0: a * np.sin(x), a=a, color=BLUE, label="a sin x")
    derivative = ax.plot_derivative_graph(parent, label="derivative")
    integral = ax.plot_antiderivative_graph(
        parent, color=YELLOW, label="antiderivative"
    )
    scene.add(ax, parent, derivative, integral, ax.legend(location="upper left"))
    scene.play(a.animate.set_value(2.0), run_time=2)
    scene.play(a.animate.set_value(0.6), run_time=2)


def twin_axes(scene: Scene) -> None:
    """Plot two quantities on two y axes, then pan the shared x range.

    `ax.twinx(y_range=...)` adds a y axis on the right with its own range; each plot
    belongs to its pair of axes, and an animated x range moves both.
    """
    shown: list[Text] = []
    ax = mp.Axes(
        x_range=(0, 10, 1),
        y_range=(0, 100, 20),
        x_length=9,
        y_length=4.8,
        axis_config={"include_numbers": True, "font_size": 22},
    ).shift(0.4 * DOWN)
    pressure = ax.twinx(
        y_range=(0, 2, 0.5), y_axis_config={"include_numbers": True, "font_size": 22}
    )
    temperature = ax.plot(lambda x: 50 + 30 * np.sin(x / 2), color=RED)
    drop = pressure.plot(lambda x: 1.8 * np.exp(-x / 6), color=BLUE)
    ax.y_axis.set_color(RED)
    pressure.y_axis.set_color(BLUE)
    show_call(scene, shown, "pressure = ax.twinx(y_range=(0, 2, 0.5))")
    scene.play(Create(ax), Create(temperature), Create(drop), run_time=2)
    show_call(scene, shown, "self.play(ax.animate.set_x_range((0, 20)))")
    scene.play(ax.animate.set_x_range((0, 20)), run_time=2.5)
    show_call(scene, shown, "self.play(pressure.animate.set_y_range((0, 1, 0.25)))")
    scene.play(pressure.animate.set_y_range((0, 1, 0.25)), run_time=2)
    scene.wait(0.5)


def four_corners(scene: Scene) -> None:
    """Bind one curve to each pair of a bottom or top x axis and a left or right y axis.

    `ax.twinx` and `ax.twiny` add the right and the top axis; `ax.twin(x=top, y=right)`
    is the pair of the two. A range animated on one axis moves only its curves.
    """
    shown: list[Text] = []
    numbers = {"include_numbers": True, "font_size": 22}
    ax = mp.Axes(
        x_range=(0, 10, 2),
        y_range=(0, 100, 20),
        x_length=8.5,
        y_length=4.4,
        axis_config=numbers,
        theme="origin",
    ).shift(0.5 * DOWN)
    right = ax.twinx(y_range=(0, 1, 0.2), y_axis_config=numbers)
    top = ax.twiny(x_range=(0, 50, 10), x_axis_config=numbers)
    corner = ax.twin(x=top, y=right)
    right.y_axis.set_color(BLUE)
    top.x_axis.set_color(GREEN)
    curves = [
        ax.plot(lambda x: 10 * x, color=WHITE),
        right.plot(lambda x: 1 - x / 10, color=BLUE),
        top.plot(lambda d: 50 + 40 * np.sin(d / 8), color=GREEN),
        corner.plot(lambda d: 0.5 + 0.4 * np.cos(d / 8), color=YELLOW),
    ]
    show_call(scene, shown, "corner = ax.twin(x=top, y=right)")
    scene.play(Create(ax), *(Create(c) for c in curves), run_time=2)
    show_call(scene, shown, "self.play(top.animate.set_x_range((0, 100)))")
    scene.play(top.animate.set_x_range((0, 100)), run_time=2)
    show_call(scene, shown, "self.play(right.animate.set_y_range((0, 2)))")
    scene.play(right.animate.set_y_range((0, 2)), run_time=2)
    scene.wait(0.5)


def secondary_axis(scene: Scene) -> None:
    """Show electronvolts above a spectrum in nanometres, then zoom the wavelengths.

    `ax.secondary_xaxis("top", functions=(forward, inverse))` puts ticks in `forward`'s
    units where the bottom axis has `inverse` of them; they follow the range. Both axes
    use `MaxNLocator(6)`, so their ticks thin and fill in as the range changes.
    """
    shown: list[Text] = []
    hc = 1239.84198
    ax = mp.Axes(
        x_range=(400, 800, 100),
        y_range=(0, 1, 0.25),
        x_length=9,
        y_length=4.6,
        axis_config={"include_numbers": True, "font_size": 22},
        theme="origin",
    ).shift(0.5 * DOWN)
    energy = ax.secondary_xaxis(
        "top", functions=(lambda nm: hc / nm, lambda ev: hc / ev), font_size=22
    )
    for axis in (ax.x, energy):
        axis.set_locator(mp.MaxNLocator(6))
    energy.set_color(YELLOW)
    peak = ax.plot(lambda nm: np.exp(-(((nm - 550) / 40) ** 2)), color=GREEN)
    show_call(scene, shown, 'ax.secondary_xaxis("top", functions=(nm_to_ev, ev_to_nm))')
    scene.play(Create(ax), Create(peak), run_time=2)
    show_call(scene, shown, "self.play(ax.animate.set_x_range((500, 600)))")
    scene.play(ax.animate.set_x_range((500, 600)), run_time=2.5)
    scene.wait(0.5)


def errorbar_data(scene: Scene) -> None:
    """Move measured points and their error bars with `.animate.set_data`.

    `ax.errorbar(x, y, yerr=..., xerr=...)` draws bars in data space and caps of a fixed
    size; `set_data` under `.animate` moves and stretches each bar to its new place.
    """
    shown: list[Text] = []
    ax = mp.Axes(x_range=(0, 6, 1), y_range=(0, 5, 1), x_length=9, y_length=5)
    ax.shift(0.4 * DOWN)
    xs = np.arange(1.0, 6.0)
    bars = ax.errorbar(xs, 1 + xs / 2, yerr=0.3, xerr=0.15, color=YELLOW, line=True)
    scene.add(ax, bars)
    show_call(scene, shown, "self.play(bars.animate.set_data(x, y, yerr=...))")
    scene.play(
        bars.animate.set_data(
            xs, 4 - xs / 2, yerr=[[0.2, 0.4, 0.2, 0.5, 0.3], [0.6, 0.2, 0.5, 0.2, 0.4]]
        ),
        run_time=2.5,
    )
    show_call(scene, shown, "self.play(ax.animate.set_y_range((0, 8)))")
    scene.play(ax.animate.set_y_range((0, 8)), run_time=2)
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
    legend_placement,
    axis_controls,
    animate_data,
    clip_per_axis,
    t_label_slides,
    secant_to_tangent,
    riemann_refines,
    derived_graphs,
    twin_axes,
    four_corners,
    secondary_axis,
    errorbar_data,
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
