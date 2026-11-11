"""Read actual Manim objects from known implementation frames; never retain frames."""

import sys

from manim import (
    Animation,
    AnimationGroup,
    Mobject,
    Scene,
    Succession,
    Transform,
    VMobject,
)

BEGIN_CODES = {
    Animation.begin.__code__,
    AnimationGroup.begin.__code__,
    Succession.begin.__code__,
    Transform.begin.__code__,
}
FINISH_CODES = {
    Animation.finish.__code__,
    AnimationGroup.finish.__code__,
    Succession.finish.__code__,
}


def animation_context(finishing=False, transform_only=False):
    codes = FINISH_CODES if finishing else BEGIN_CODES
    if transform_only:
        codes = {Transform.begin.__code__}
    frame = sys._getframe(1)
    try:
        while frame is not None:
            if frame.f_code in codes:
                return frame.f_locals["self"], frame.f_lineno
            frame = frame.f_back
        return None, None
    finally:
        del frame


def writer_context():
    frame = sys._getframe(1)
    result = None
    application = None
    try:
        while frame is not None:
            values = frame.f_locals
            if frame.f_code is VMobject.apply_function.__code__:
                application = (values["self"], values["function"])
            if result is None and frame.f_code is Mobject.shift.__code__:
                result = {
                    "container": values["self"],
                    "kind": "shift",
                    "last": frame.f_lineno == 1283,
                    "vector": values["total_vector"],
                    "line": frame.f_lineno,
                }
            if (
                result is None
                and frame.f_code is Mobject.apply_points_function_about_point.__code__
            ):
                result = {
                    "container": values["self"],
                    "kind": "function",
                    "last": frame.f_lineno == 1584,
                    "func": values["func"],
                    "pivot": values["about_point"].copy(),
                    "line": frame.f_lineno,
                }
            frame = frame.f_back
        if result is not None:
            result["application"] = application
        return result
    finally:
        del frame


def handle_write():
    return sys._getframe(2).f_code is VMobject.set_anchors_and_handles.__code__


def playback_context():
    frame = sys._getframe(1)
    boundary = None
    try:
        while frame is not None:
            if frame.f_code is Scene.update_to_time.__code__:
                return id(frame.f_locals["self"]), frame.f_locals["t"]
            if frame.f_code is Scene.play_internal.__code__:
                scene = frame.f_locals["self"]
                boundary = (id(scene), "finish", scene.renderer.num_plays)
            frame = frame.f_back
        return boundary
    finally:
        del frame
