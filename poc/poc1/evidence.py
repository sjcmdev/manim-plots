"""Print the installed Manim symbols quoted in the report, with their real lines."""

import inspect

from manim import (
    AddTextLetterByLetter,
    Animation,
    DecimalNumber,
    Homotopy,
    Indicate,
    Mobject,
    MoveAlongPath,
    PhaseFlow,
    RemoveTextLetterByLetter,
    ShowIncreasingSubsets,
    ShowPassingFlash,
    VMobject,
    Wiggle,
)
from manim.animation.transform import _MethodAnimation
from manim.camera.camera import Camera
from manim.mobject.mobject import _AnimationBuilder
from manim.utils.tex_file_writing import print_all_tex_errors

SYMBOLS = [
    Mobject.__init__,
    Mobject.reset_points,
    Mobject.__deepcopy__,
    Mobject.copy,
    Mobject.generate_target,
    Mobject.suspend_updating,
    Mobject.resume_updating,
    Mobject.interpolate,
    VMobject.apply_function,
    VMobject.scale_handle_to_anchor_distances,
    Animation.begin,
    Animation.finish,
    Animation.create_starting_mobject,
    Wiggle.interpolate_submobject,
    Homotopy.interpolate_submobject,
    Indicate.create_target,
    ShowPassingFlash.clean_up_from_scene,
    ShowIncreasingSubsets.__init__,
    AddTextLetterByLetter.__init__,
    RemoveTextLetterByLetter.__init__,
    MoveAlongPath.__init__,
    MoveAlongPath.interpolate_mobject,
    PhaseFlow.__init__,
    PhaseFlow.interpolate_mobject,
    _MethodAnimation.finish,
    _AnimationBuilder.__init__,
    _AnimationBuilder.__getattr__,
    Camera.set_cairo_context_path,
    DecimalNumber._string_to_mob,
    print_all_tex_errors,
]

if __name__ == "__main__":
    for symbol in SYMBOLS:
        print(f"\n{inspect.getfile(symbol)}::{symbol.__qualname__}")
        lines, first = inspect.getsourcelines(symbol)
        print("".join(f":{number} {line}" for number, line in enumerate(lines, first)))
