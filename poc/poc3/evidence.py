"""Print the installed Manim implementation, symbol before numbered lines."""

import hashlib
import inspect
import json
import sys

from manim import (
    Animation,
    AnimationGroup,
    FadeOut,
    Mobject,
    MoveAlongPath,
    PhaseFlow,
    Scene,
    ShowIncreasingSubsets,
    ShowPassingFlash,
    Succession,
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

from poc3.model import ROOT

SYMBOLS = [
    Mobject.shift,
    Mobject.apply_points_function_about_point,
    VMobject.apply_function,
    VMobject.scale_handle_to_anchor_distances,
    VMobject.get_anchors,
    VMobject.get_points_defining_boundary,
    VMobject.set_anchors_and_handles,
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
    Animation.get_all_families_zipped,
    Animation.get_sub_alpha,
    AnimationGroup.begin,
    AnimationGroup.finish,
    AnimationGroup.clean_up_from_scene,
    Succession.begin,
    Succession.finish,
    Succession.update_active_animation,
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
    PhaseFlow.__init__,
    PhaseFlow.interpolate_mobject,
    ShowIncreasingSubsets.__init__,
    ShowIncreasingSubsets.interpolate_mobject,
    _AnimationBuilder.__init__,
    _AnimationBuilder.__getattr__,
    always_redraw,
    Scene.get_moving_mobjects,
    Scene.should_update_mobjects,
    Scene.update_to_time,
    Scene.play_internal,
    Scene.add,
    Scene.add_mobjects_from_animations,
    CairoRenderer.play,
    Camera.set_cairo_context_path,
]


def contract():
    result = {}
    for symbol in SYMBOLS:
        lines, first = inspect.getsourcelines(symbol)
        result[symbol.__qualname__] = {
            "first": first,
            "sha256": hashlib.sha256("".join(lines).encode()).hexdigest(),
        }
    return result


if __name__ == "__main__":
    output = []
    for symbol in SYMBOLS:
        output.append(f"\n{inspect.getfile(symbol)}::{symbol.__qualname__}\n")
        lines, first = inspect.getsourcelines(symbol)
        output.append("".join(f":{n} {line}" for n, line in enumerate(lines, first)))
    text = "".join(output)
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "manim_sources.txt").write_text(text, encoding="utf-8")
    if "--freeze" in sys.argv:
        (ROOT / "manim_contract.json").write_text(
            json.dumps(contract(), indent=2) + "\n", encoding="utf-8"
        )
    else:
        print(text)
