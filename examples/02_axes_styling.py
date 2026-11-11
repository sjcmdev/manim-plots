"""Style the axes part by part: position, locators, tick direction, grid, a mirror.

Every part of an axis — line, ticks, numbers, grid — is addressable and styleable on
its own. Each call is shown on screen as it is made; the curve stays where its data is.

    manim -pql examples/02_axes_styling.py AxesStyling
"""

from manim import *

import manim_plots as mp


class AxesStyling(Scene):
    def show(self, code):
        """Put the call being made at the top of the frame."""
        self.remove(*[m for m in self.mobjects if isinstance(m, Text)])
        self.add(Text(code, font="Consolas", font_size=22).to_edge(UP, buff=0.35))

    def construct(self):
        ax = mp.Axes(
            x_range=(-2, 10, 2),
            y_range=(-1, 5, 1),
            x_length=10,
            y_length=5,
            axis_config={"include_numbers": True},
        ).shift(0.4 * DOWN)
        curve = ax.plot(lambda x: 2.5 + 2 * np.sin(x), color=RED)
        self.play(Create(ax), Create(curve))

        self.show('ax.x.set_position("bottom"); ax.y.set_position("left")')
        ax.x.set_position("bottom")
        ax.y.set_position("left")
        self.wait(1.5)

        self.show(
            "ax.x.set_locator(mp.MultipleLocator(2), minor=mp.MultipleLocator(1))"
        )
        ax.x.set_locator(mp.MultipleLocator(2), minor=mp.MultipleLocator(1))
        self.wait(1.5)

        self.show("ax.x.set_tick_style(direction=mp.TickDirection.OUT)")
        ax.x.set_tick_style(direction=mp.TickDirection.OUT)
        ax.y.set_tick_style(direction=mp.TickDirection.OUT)
        self.wait(1.5)

        self.show('ax.x.set_grid("major", stroke_opacity=0.5)')
        ax.x.set_grid("major", stroke_opacity=0.5)
        ax.y.set_grid("major", stroke_opacity=0.5)
        self.wait(1.5)

        self.show("ax.x.mirror(); ax.y.mirror()")
        ax.x.mirror()
        ax.y.mirror()
        self.wait(1.5)

        self.show('ax.x.set_tick_style("minor", length=0.25, color=YELLOW)')
        ax.x.set_tick_style("minor", length=0.25, color=YELLOW)
        self.wait(1.5)

        self.show("self.play(ax.animate.set_x_range((0, 20)))")
        self.play(ax.animate.set_x_range((0, 20)), run_time=2)
        self.wait()
