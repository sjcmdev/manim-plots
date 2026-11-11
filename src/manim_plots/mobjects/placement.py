"""Shared placement beside axes and inside a three-dimensional camera frame."""

from __future__ import annotations

from typing import Any

from manim import DOWN, LEFT, RIGHT, UP, Mobject, ThreeDCamera, config

from manim_plots.mobjects.context import _scene_camera


def _place_beside(
    mob: Mobject,
    parent: Mobject,
    side: str,
    buff: float,
    *,
    anchor: Mobject | None = None,
    frame_offset: float | None = None,
) -> None:
    directions = {"right": RIGHT, "left": LEFT, "up": UP, "down": DOWN}
    if side not in directions:
        raise ValueError("side must be right, left, up or down")
    if mob.__dict__.get("_beside_fixed", False):
        return
    direction = directions[side]
    camera = _scene_camera()
    if isinstance(camera, ThreeDCamera):
        camera.add_fixed_in_frame_mobjects(mob)
        mob.__dict__["_beside_fixed"] = True
        if frame_offset is not None:
            mob.move_to(direction * frame_offset)
        else:
            index = 0 if side in ("right", "left") else 1
            half = (config.frame_width if index == 0 else config.frame_height) / 2
            target = direction * (half - buff)
            mob.shift(target - mob.get_critical_point(direction))
        return
    target = parent.get_critical_point(direction).copy()
    target[2] = 0
    box: Any = tuple(target)
    if mob.__dict__.get("_beside_box") != box:
        reference = mob if anchor is None else anchor
        current = reference.get_critical_point(-direction).copy()
        mob.shift(target + buff * direction - current)
        mob.__dict__["_beside_box"] = box
