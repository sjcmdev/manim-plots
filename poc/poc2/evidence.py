"""Print the installed Manim implementation, symbol before numbered lines."""

import inspect

from manim import (
    Animation,
    FadeOut,
    Mobject,
    MoveAlongPath,
    Scene,
    ShowPassingFlash,
    Transform,
    TransformFromCopy,
    VMobject,
    Wiggle,
    always_redraw,
)
from manim.animation.creation import DrawBorderThenFill, ShowPartial
from manim.animation.transform import _MethodAnimation
from manim.camera.camera import Camera
from manim.mobject.mobject import _AnimationBuilder
from manim.renderer.cairo_renderer import CairoRenderer

SYMBOLS = [
    Mobject.shift,
    Mobject.apply_points_function_about_point,
    VMobject.apply_function,
    VMobject.scale_handle_to_anchor_distances,
    VMobject.get_anchors,
    Mobject.__deepcopy__,
    Mobject.copy,
    Mobject.suspend_updating,
    Mobject.resume_updating,
    Mobject.become,
    Mobject.align_data,
    Mobject.align_submobjects,
    Mobject.add_n_more_submobjects,
    Mobject.interpolate,
    VMobject.align_points,
    Animation.begin,
    Animation.finish,
    ShowPartial.interpolate_submobject,
    DrawBorderThenFill.interpolate_submobject,
    Wiggle.interpolate_submobject,
    Transform.begin,
    Transform.clean_up_from_scene,
    TransformFromCopy.__init__,
    TransformFromCopy.interpolate,
    _MethodAnimation.finish,
    FadeOut.clean_up_from_scene,
    ShowPassingFlash.clean_up_from_scene,
    MoveAlongPath.__init__,
    MoveAlongPath.interpolate_mobject,
    _AnimationBuilder.__init__,
    _AnimationBuilder.__getattr__,
    always_redraw,
    Scene.get_moving_mobjects,
    Scene.should_update_mobjects,
    Scene.add,
    Scene.add_mobjects_from_animations,
    CairoRenderer.play,
    Camera.set_cairo_context_path,
]


if __name__ == "__main__":
    for symbol in SYMBOLS:
        print(f"\n{inspect.getfile(symbol)}::{symbol.__qualname__}")
        lines, first = inspect.getsourcelines(symbol)
        print("".join(f":{n} {line}" for n, line in enumerate(lines, first)))
