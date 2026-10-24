"""Read actual Manim objects from known implementation frames; never retain frames."""

import ast
import inspect
import sys
import textwrap

import numpy as np
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


def last_points_write(source, first):
    tree = ast.parse(textwrap.dedent(source))
    writes = []
    for node in ast.walk(tree):
        targets = (
            node.targets
            if isinstance(node, ast.Assign)
            else [node.target]
            if isinstance(node, (ast.AugAssign, ast.AnnAssign))
            else []
        )
        if any(isinstance(t, ast.Attribute) and t.attr == "points" for t in targets):
            writes.append(first + node.lineno - 1)
    return max(writes)


LAST_WRITES = {
    method.__code__: last_points_write("".join(lines), first)
    for method in [Mobject.shift, Mobject.apply_points_function_about_point]
    for lines, first in [inspect.getsourcelines(method)]
}


def affine_context():
    """Exact row-vector matrix supplied by the actual native operation caller."""
    frame = sys._getframe(1)
    try:
        while frame is not None:
            code, values = frame.f_code, frame.f_locals
            if code is Mobject.rotate.__code__:
                return values["rot_matrix"].T.copy()
            if code is Mobject.scale.__code__:
                return np.eye(3) * values["scale_factor"]
            if code is Mobject.stretch.__code__:
                matrix = np.eye(3)
                matrix[values["dim"], values["dim"]] = values["factor"]
                return matrix
            if code is Mobject.apply_matrix.__code__:
                return values["full_matrix"].T.copy()
            frame = frame.f_back
        return None
    finally:
        del frame


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
                    "last": frame.f_lineno == LAST_WRITES[frame.f_code],
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
                    "last": frame.f_lineno == LAST_WRITES[frame.f_code],
                    "func": values["func"],
                    "pivot": values["about_point"].copy(),
                    "line": frame.f_lineno,
                }
            frame = frame.f_back
        if result is not None:
            result["application"] = application
            result["matrix"] = affine_context()
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
