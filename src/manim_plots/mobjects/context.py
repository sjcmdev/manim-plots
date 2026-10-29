"""Inventory and source pins for the Manim internals used by the library."""

import ast
import hashlib
import inspect
import sys
import textwrap
import warnings
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import FrameType
from typing import Any, cast

import manim
import numpy as np
from manim import (
    Animation,
    AnimationGroup,
    FadeOut,
    Mobject,
    MoveAlongPath,
    NumberPlane,
    PhaseFlow,
    Scene,
    ShowIncreasingSubsets,
    ShowPassingFlash,
    Succession,
    Transform,
    TransformFromCopy,
    VGroup,
    VMobject,
    Wiggle,
    always_redraw,
)
from manim.animation.creation import DrawBorderThenFill, ShowPartial
from manim.animation.growing import GrowFromCenter, GrowFromPoint
from manim.animation.transform import ShrinkToCenter, _MethodAnimation
from manim.camera.camera import Camera
from manim.mobject.mobject import _AnimationBuilder
from manim.renderer.cairo_renderer import CairoRenderer

from manim_plots.core import FloatArray, ManimPlotsWarning

SYMBOLS: tuple[Callable[..., object], ...] = (
    Mobject.rotate,
    Mobject.scale,
    Mobject.stretch,
    Mobject.apply_matrix,
    Animation.create_starting_mobject,
    Animation.clean_up_from_scene,
    Animation.is_remover,
    Animation.is_introducer,
    Transform.interpolate_submobject,
    Transform.get_all_families_zipped,
    GrowFromCenter.__init__,
    GrowFromPoint.create_starting_mobject,
    ShrinkToCenter.__init__,
    NumberPlane.prepare_for_nonlinear_transform,
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
    DrawBorderThenFill.begin,
    Mobject.get_family_updaters,
    Mobject.__getattr__,
    VMobject.set_fill,
    VMobject.set_stroke,
    VMobject.interpolate_color,
    VMobject.pointwise_become_partial,
    VGroup.add,
    Mobject.remove,
    Mobject.reduce_across_dimension,
)

PINS: Mapping[str, Mapping[str, str]] = {
    "0.21.0": {
        "Mobject.reduce_across_dimension": (
            "ab90aae167a0147ef3ef80088f6ad58518da78650f1d9b9d9bad12dfdf1a7b47"
        ),
        "Mobject.remove": (
            "b57f7a7caadb6f17c0e9a2211a2b3ed39f43c48949238387901aba2ab78b4aa8"
        ),
        "Mobject.rotate": (
            "d8654a36c8cb817b8341eda2498230b26a1f9d010fc1c2d8f9383057134d8ae8"
        ),
        "Mobject.scale": (
            "1d0aea25b5972bd6c5c5d97920630f9a2895785375cde30e4b2592c26696e9ff"
        ),
        "Mobject.stretch": (
            "9b3b0d4a2f31648728f6b517436ce7fe1041e1f14b6adf9a733a54bf6ff04612"
        ),
        "Mobject.apply_matrix": (
            "2b3bde85e4a300231fa471a7e64c9233cd1fdee96b71d9a42ae86ab9f90dee97"
        ),
        "Animation.create_starting_mobject": (
            "fe0863e67d120ef6082b445efa8936594aa29cb264b10ba568656e97057295ba"
        ),
        "Animation.clean_up_from_scene": (
            "055f70240b012325e907d4b1a1b100902cab25470d23461dfa27880cace73a08"
        ),
        "Animation.is_remover": (
            "77ac7ad2318b0009e4d9acb4dff085dcc2427d3d56f37a8e7619cc53ce28fa63"
        ),
        "Animation.is_introducer": (
            "7e93728ee70a1eb1657d09595443bd48b6465864b7924f3d9fa49b1240d2f9b0"
        ),
        "Transform.interpolate_submobject": (
            "cb3c7233b8c1b8984279be518952b174d5c4560432dc70957a4b8857605089eb"
        ),
        "Transform.get_all_families_zipped": (
            "cf5fcb6ffe0afe4b4a282dd2931caa46b8af493e6ef68437028a9e319c683f92"
        ),
        "GrowFromCenter.__init__": (
            "3fd32eff781147b363c628178bd0032bdd4c6aca7d91cbd53547e1bfa3bfbb3b"
        ),
        "GrowFromPoint.create_starting_mobject": (
            "b24d2fdf31e9e91d4dfcfe71a4501e3c71aa2e4257a69d7bcffc1bd6b9d9807a"
        ),
        "ShrinkToCenter.__init__": (
            "08f570bb39d7725fc28d0c1a1f96385e2fb15940058eb6cace80d8a74b8664aa"
        ),
        "NumberPlane.prepare_for_nonlinear_transform": (
            "51cc9eb09a6381171721c581f1c2e34af49e1c718e57e1bdb17bc93420037185"
        ),
        "Mobject.shift": (
            "97ca5b9d0d14d3af137ba3b5a1a200df62b18b3ed1858bbd15e154745aaeb6bb"
        ),
        "Mobject.apply_points_function_about_point": (
            "f2b6e32d3786c133abd3bfe2aede34deef497b751fec09a3486e95ec9852aea9"
        ),
        "VMobject.apply_function": (
            "5d9a613d12cb0f4f5d42fe457cda427a1b6a667904894a2c42b80992e58fa211"
        ),
        "VMobject.scale_handle_to_anchor_distances": (
            "b688e7c2b3c6f2b6657ddc4584cf055f89301d1ece78cf7c2927b50ba35bc5eb"
        ),
        "VMobject.get_anchors": (
            "570aac67257a511caf8e9a34e11a649bd4de323f0e5cd1264cbe5fc3ea1a9083"
        ),
        "VMobject.get_points_defining_boundary": (
            "13057979b204e9b663c283c3d37e857b9db75500b0d4db15b8335acb55dae0ad"
        ),
        "VMobject.set_anchors_and_handles": (
            "9f613d1c80c2b15d6b05de012d4e54318aa92e2bbe0f9a2fa3abe56d2065c91d"
        ),
        "Mobject.__deepcopy__": (
            "8a1349b6fc8ab459e17e26106fb1c7595853e3369231f936624170f283ea8ab1"
        ),
        "Mobject.copy": (
            "a22dc312aed0c05826bb8075283239e1be2bc7932f4f9089dbfebf46a1dafef0"
        ),
        "Mobject.suspend_updating": (
            "7b3bd9c5a1074658788a96e5a1bd87be7d7b2595d2cdf36dd911d8ba3e23c707"
        ),
        "Mobject.resume_updating": (
            "19c067227bfac76acdd307a0a6a534e36a2dd7a6cda754a137af2033a437bb27"
        ),
        "Mobject.become": (
            "c3f4317909fdc29b4606604409498fdc9100aef5c71cab2b3166a15e8685af9a"
        ),
        "Mobject.align_data": (
            "2cd75be4af9373f3675f5b65a99cb2099c8f7abf7f871770fda8c9f737e81ae9"
        ),
        "Mobject.align_submobjects": (
            "9fbf260aba9889e49b55bde0143a81bdb620ee82d926f8f712814f0f618f1662"
        ),
        "Mobject.add_n_more_submobjects": (
            "24032de9fc777929e32fa9216077b21f493ed395e3e689605840cb59a850848c"
        ),
        "Mobject.interpolate": (
            "398eaf3ece840bb3cd5b6f4edbd30457a6a5113498428b7013002b044b88338e"
        ),
        "VMobject.align_points": (
            "a89a89c591626d9bff406d393490b335440c03680280711b7ba448d37751dbce"
        ),
        "Animation.begin": (
            "fbc294d3275d1b3d00ca4124de1cb8c61449c0fb09968b1fbf5b5b853a47537e"
        ),
        "Animation.finish": (
            "d2cb9ad54830c1d4e55cebc699e92d01b61ff78ba3e243246c8bdaedffa6bbf5"
        ),
        "Animation.get_all_families_zipped": (
            "dbbf81642ac72debb5e3f9f85cb7ca102c4970bbe374060d8d994254aa8ec67d"
        ),
        "Animation.get_sub_alpha": (
            "0e40f96921a785d4543640f55db12b0a1022222e6b4dfd1444fc1a03bf008ecb"
        ),
        "AnimationGroup.begin": (
            "10edfa32b8d2f3cdf154b03e7557f3de9377c8940c3194a4f68c8eb7bfd0f101"
        ),
        "AnimationGroup.finish": (
            "8066d4d0dcc90d1c20e48043acd08ba59f3fb1dad0964738637667ded27e6885"
        ),
        "AnimationGroup.clean_up_from_scene": (
            "84ffb0311bb261733d8cc04c8d1c30955620ef5f8a5a2cbc57525773249b67cc"
        ),
        "Succession.begin": (
            "bfd139ca7f5f5cf638caedd34a03fea95a20182d515f69c361040bbf61d9139b"
        ),
        "Succession.finish": (
            "78ee18e9ad1f6fe34bd241e6861caf612e5855490769980ca0a6893dafd04e30"
        ),
        "Succession.update_active_animation": (
            "dbc7d5bf8ce748044ce7ce7bb99d2054cd74de5a21cc495988795eab78ae869c"
        ),
        "ShowPartial.interpolate_submobject": (
            "3417be750ae2aa25996ed01eb325ecc343503124fbdb46b5899e9daeb371b0e5"
        ),
        "DrawBorderThenFill.interpolate_submobject": (
            "00247978857bbd07703afcb2fb42119463cba177d07bae8ec18c347c75b84444"
        ),
        "Wiggle.interpolate_submobject": (
            "288d509867cc4f263f070c757c23cf112d39f0bf79835df649739fc34fc903af"
        ),
        "Transform.begin": (
            "b9563496ce8c5e8b1641008f4952fc8ccfa36cb184f4bb8e5d89d3c001713ede"
        ),
        "Transform.clean_up_from_scene": (
            "9c000453019af523c2c179666b51f83732bfe085616b0f46e6e1a0c036aea4e1"
        ),
        "TransformFromCopy.__init__": (
            "1e896249051c4f3de525f228c9a79be8df2be1aa5abb6c0a03a67e148cf7ae3c"
        ),
        "TransformFromCopy.interpolate": (
            "5ffff83ca927ff6bcf07bdb331f08903d62b3135ec13e11839e54da67ece6cb4"
        ),
        "_MethodAnimation.finish": (
            "f72a27b80c7a9f252827ba1ca0a9eff70d132e019d648625eddb0a7e4423dcc1"
        ),
        "FadeOut.clean_up_from_scene": (
            "f4e88d8794e885384b0b18b259c715a37c53e440017ba405eb7225b573d1d709"
        ),
        "ShowPassingFlash.clean_up_from_scene": (
            "eceffc730400765bbb9e56e46b00ff1955a5fb28f21997786f9e1dd484172e9f"
        ),
        "MoveAlongPath.__init__": (
            "c0f57d41170cce6475933edf1c316f49c69be56461710564b98b402d4aa2a602"
        ),
        "MoveAlongPath.interpolate_mobject": (
            "1284e87007a053ddb9ff46d22f5e80780b2bbb2816f11e777762c286422f280f"
        ),
        "PhaseFlow.__init__": (
            "550a9d92bd1e1ebbfa4ef514b528465b302a3bf93ab52090b076c8fc7f1c0fac"
        ),
        "PhaseFlow.interpolate_mobject": (
            "4ffc3cb74f4e4056f45330adb4a1c80740e54f5b067320ed4594b952bb0c6a2c"
        ),
        "ShowIncreasingSubsets.__init__": (
            "bcdfc0aa8ec20603f35a37b3012d8ce77370da1c078bece81aef0ecc32af68f3"
        ),
        "ShowIncreasingSubsets.interpolate_mobject": (
            "a45a8d8693f0e09d464eac40962a5b17d0fb5cbbcb924084d6b05cf62a9593fe"
        ),
        "_AnimationBuilder.__init__": (
            "66e570764c551d4b7f2b70ab21ca397df8a931071c50977c2cd77288a4204966"
        ),
        "_AnimationBuilder.__getattr__": (
            "6b7caeec3a7b73f27b49e5f2576ae99809d7b956468ed1947d0dace317510e03"
        ),
        "always_redraw": (
            "f725d6d9c3fbbe1ec63f06926d17055b8946d171e7e71b6bf9e7cc069a7317cf"
        ),
        "Scene.get_moving_mobjects": (
            "26646c79589a5fe64a66bb69a6fbe5437d367490f871ae156a7a651ca0a194c9"
        ),
        "Scene.should_update_mobjects": (
            "28c43743dc124aaaf3008b756eca0e42c64efcfa4faaba29ecf00afad9f74d4c"
        ),
        "Scene.update_to_time": (
            "c554748b52bb38f61efaa8b973568bcfc69069b8c51a065e8ce24745af118836"
        ),
        "Scene.play_internal": (
            "c83eff575fd7732171dbc37a99b443b03f577361efe2f528375da418783639c5"
        ),
        "Scene.add": (
            "5b1b4b7970420ce937cb5e6117f510314cf35275a249051ec9e33fadc5cdd923"
        ),
        "Scene.add_mobjects_from_animations": (
            "a236f35c5ee7b1231fd9d70d04fd4c4e4150022068f7ae92d48db565af37c4e7"
        ),
        "CairoRenderer.play": (
            "4cad6da1e0bcec34dacad1b8c35388d3df6a8e787e5a27544e6a0fa6deb4a4b3"
        ),
        "Camera.set_cairo_context_path": (
            "0e53e5837e78857d20178931c265487d10db6d8eb57c6784b6dee9feb4375dbf"
        ),
        "DrawBorderThenFill.begin": (
            "a4a73c4ecb61734d10a94bfad4a53f0e7cd135ebd9653065820e90ca1f76d720"
        ),
        "Mobject.__getattr__": (
            "4b63b7f9c1e9a41087e93e3c5c9fea4413523b5511af51caf4f06d8f2c6d451b"
        ),
        "VMobject.set_fill": (
            "e325766f129f638c59186f1b32ff63d4601a653a20744467f62db4713772f49e"
        ),
        "VMobject.set_stroke": (
            "1ee05806ebe6f8558b037e760bdcfac0ad9595bced1d993a85c8abee95772595"
        ),
        "VMobject.interpolate_color": (
            "1f9f95a1383f72ba1576bb0177cb81b32b95dc115b337b36b152c3c521b2d72d"
        ),
        "VMobject.pointwise_become_partial": (
            "c78b17aeb714c07dc36e800a54c642f1226503698ed9a38224322eb45ac1f21d"
        ),
        "VGroup.add": (
            "0c23544a19789dd871a576725ac0832fe2a0af89a75dac8c7c26eb598edd515a"
        ),
        "Mobject.get_family_updaters": (
            "37cd7d253aa5e9d4ccfaddd4e81677fadaf99600f4b9ba7b6d9d5717f71e86c8"
        ),
    },
    "0.22.0": {
        "Mobject.reduce_across_dimension": (
            "ab90aae167a0147ef3ef80088f6ad58518da78650f1d9b9d9bad12dfdf1a7b47"
        ),
        "Mobject.remove": (
            "0de58573f90f6468ac258de89cad2eae2b84cdeddc859a67f492333259864f5d"
        ),
        "Mobject.rotate": (
            "d8654a36c8cb817b8341eda2498230b26a1f9d010fc1c2d8f9383057134d8ae8"
        ),
        "Mobject.scale": (
            "1d0aea25b5972bd6c5c5d97920630f9a2895785375cde30e4b2592c26696e9ff"
        ),
        "Mobject.stretch": (
            "9b3b0d4a2f31648728f6b517436ce7fe1041e1f14b6adf9a733a54bf6ff04612"
        ),
        "Mobject.apply_matrix": (
            "2b3bde85e4a300231fa471a7e64c9233cd1fdee96b71d9a42ae86ab9f90dee97"
        ),
        "Animation.create_starting_mobject": (
            "fe0863e67d120ef6082b445efa8936594aa29cb264b10ba568656e97057295ba"
        ),
        "Animation.clean_up_from_scene": (
            "055f70240b012325e907d4b1a1b100902cab25470d23461dfa27880cace73a08"
        ),
        "Animation.is_remover": (
            "77ac7ad2318b0009e4d9acb4dff085dcc2427d3d56f37a8e7619cc53ce28fa63"
        ),
        "Animation.is_introducer": (
            "7e93728ee70a1eb1657d09595443bd48b6465864b7924f3d9fa49b1240d2f9b0"
        ),
        "Transform.interpolate_submobject": (
            "cb3c7233b8c1b8984279be518952b174d5c4560432dc70957a4b8857605089eb"
        ),
        "Transform.get_all_families_zipped": (
            "cf5fcb6ffe0afe4b4a282dd2931caa46b8af493e6ef68437028a9e319c683f92"
        ),
        "GrowFromCenter.__init__": (
            "3fd32eff781147b363c628178bd0032bdd4c6aca7d91cbd53547e1bfa3bfbb3b"
        ),
        "GrowFromPoint.create_starting_mobject": (
            "b24d2fdf31e9e91d4dfcfe71a4501e3c71aa2e4257a69d7bcffc1bd6b9d9807a"
        ),
        "ShrinkToCenter.__init__": (
            "08f570bb39d7725fc28d0c1a1f96385e2fb15940058eb6cace80d8a74b8664aa"
        ),
        "NumberPlane.prepare_for_nonlinear_transform": (
            "51cc9eb09a6381171721c581f1c2e34af49e1c718e57e1bdb17bc93420037185"
        ),
        "Mobject.shift": (
            "97ca5b9d0d14d3af137ba3b5a1a200df62b18b3ed1858bbd15e154745aaeb6bb"
        ),
        "Mobject.apply_points_function_about_point": (
            "f2b6e32d3786c133abd3bfe2aede34deef497b751fec09a3486e95ec9852aea9"
        ),
        "VMobject.apply_function": (
            "5d9a613d12cb0f4f5d42fe457cda427a1b6a667904894a2c42b80992e58fa211"
        ),
        "VMobject.scale_handle_to_anchor_distances": (
            "b688e7c2b3c6f2b6657ddc4584cf055f89301d1ece78cf7c2927b50ba35bc5eb"
        ),
        "VMobject.get_anchors": (
            "570aac67257a511caf8e9a34e11a649bd4de323f0e5cd1264cbe5fc3ea1a9083"
        ),
        "VMobject.get_points_defining_boundary": (
            "13057979b204e9b663c283c3d37e857b9db75500b0d4db15b8335acb55dae0ad"
        ),
        "VMobject.set_anchors_and_handles": (
            "9f613d1c80c2b15d6b05de012d4e54318aa92e2bbe0f9a2fa3abe56d2065c91d"
        ),
        "Mobject.__deepcopy__": (
            "8a1349b6fc8ab459e17e26106fb1c7595853e3369231f936624170f283ea8ab1"
        ),
        "Mobject.copy": (
            "a22dc312aed0c05826bb8075283239e1be2bc7932f4f9089dbfebf46a1dafef0"
        ),
        "Mobject.suspend_updating": (
            "7b3bd9c5a1074658788a96e5a1bd87be7d7b2595d2cdf36dd911d8ba3e23c707"
        ),
        "Mobject.resume_updating": (
            "19c067227bfac76acdd307a0a6a534e36a2dd7a6cda754a137af2033a437bb27"
        ),
        "Mobject.become": (
            "c3f4317909fdc29b4606604409498fdc9100aef5c71cab2b3166a15e8685af9a"
        ),
        "Mobject.align_data": (
            "2cd75be4af9373f3675f5b65a99cb2099c8f7abf7f871770fda8c9f737e81ae9"
        ),
        "Mobject.align_submobjects": (
            "9fbf260aba9889e49b55bde0143a81bdb620ee82d926f8f712814f0f618f1662"
        ),
        "Mobject.add_n_more_submobjects": (
            "24032de9fc777929e32fa9216077b21f493ed395e3e689605840cb59a850848c"
        ),
        "Mobject.interpolate": (
            "398eaf3ece840bb3cd5b6f4edbd30457a6a5113498428b7013002b044b88338e"
        ),
        "VMobject.align_points": (
            "a89a89c591626d9bff406d393490b335440c03680280711b7ba448d37751dbce"
        ),
        "Animation.begin": (
            "fbc294d3275d1b3d00ca4124de1cb8c61449c0fb09968b1fbf5b5b853a47537e"
        ),
        "Animation.finish": (
            "d2cb9ad54830c1d4e55cebc699e92d01b61ff78ba3e243246c8bdaedffa6bbf5"
        ),
        "Animation.get_all_families_zipped": (
            "dbbf81642ac72debb5e3f9f85cb7ca102c4970bbe374060d8d994254aa8ec67d"
        ),
        "Animation.get_sub_alpha": (
            "0e40f96921a785d4543640f55db12b0a1022222e6b4dfd1444fc1a03bf008ecb"
        ),
        "AnimationGroup.begin": (
            "10edfa32b8d2f3cdf154b03e7557f3de9377c8940c3194a4f68c8eb7bfd0f101"
        ),
        "AnimationGroup.finish": (
            "8066d4d0dcc90d1c20e48043acd08ba59f3fb1dad0964738637667ded27e6885"
        ),
        "AnimationGroup.clean_up_from_scene": (
            "84ffb0311bb261733d8cc04c8d1c30955620ef5f8a5a2cbc57525773249b67cc"
        ),
        "Succession.begin": (
            "bfd139ca7f5f5cf638caedd34a03fea95a20182d515f69c361040bbf61d9139b"
        ),
        "Succession.finish": (
            "78ee18e9ad1f6fe34bd241e6861caf612e5855490769980ca0a6893dafd04e30"
        ),
        "Succession.update_active_animation": (
            "dbc7d5bf8ce748044ce7ce7bb99d2054cd74de5a21cc495988795eab78ae869c"
        ),
        "ShowPartial.interpolate_submobject": (
            "3417be750ae2aa25996ed01eb325ecc343503124fbdb46b5899e9daeb371b0e5"
        ),
        "DrawBorderThenFill.interpolate_submobject": (
            "00247978857bbd07703afcb2fb42119463cba177d07bae8ec18c347c75b84444"
        ),
        "Wiggle.interpolate_submobject": (
            "288d509867cc4f263f070c757c23cf112d39f0bf79835df649739fc34fc903af"
        ),
        "Transform.begin": (
            "b9563496ce8c5e8b1641008f4952fc8ccfa36cb184f4bb8e5d89d3c001713ede"
        ),
        "Transform.clean_up_from_scene": (
            "9c000453019af523c2c179666b51f83732bfe085616b0f46e6e1a0c036aea4e1"
        ),
        "TransformFromCopy.__init__": (
            "1e896249051c4f3de525f228c9a79be8df2be1aa5abb6c0a03a67e148cf7ae3c"
        ),
        "TransformFromCopy.interpolate": (
            "5ffff83ca927ff6bcf07bdb331f08903d62b3135ec13e11839e54da67ece6cb4"
        ),
        "_MethodAnimation.finish": (
            "f72a27b80c7a9f252827ba1ca0a9eff70d132e019d648625eddb0a7e4423dcc1"
        ),
        "FadeOut.clean_up_from_scene": (
            "f4e88d8794e885384b0b18b259c715a37c53e440017ba405eb7225b573d1d709"
        ),
        "ShowPassingFlash.clean_up_from_scene": (
            "eceffc730400765bbb9e56e46b00ff1955a5fb28f21997786f9e1dd484172e9f"
        ),
        "MoveAlongPath.__init__": (
            "c0f57d41170cce6475933edf1c316f49c69be56461710564b98b402d4aa2a602"
        ),
        "MoveAlongPath.interpolate_mobject": (
            "1284e87007a053ddb9ff46d22f5e80780b2bbb2816f11e777762c286422f280f"
        ),
        "PhaseFlow.__init__": (
            "550a9d92bd1e1ebbfa4ef514b528465b302a3bf93ab52090b076c8fc7f1c0fac"
        ),
        "PhaseFlow.interpolate_mobject": (
            "4ffc3cb74f4e4056f45330adb4a1c80740e54f5b067320ed4594b952bb0c6a2c"
        ),
        "ShowIncreasingSubsets.__init__": (
            "bcdfc0aa8ec20603f35a37b3012d8ce77370da1c078bece81aef0ecc32af68f3"
        ),
        "ShowIncreasingSubsets.interpolate_mobject": (
            "a45a8d8693f0e09d464eac40962a5b17d0fb5cbbcb924084d6b05cf62a9593fe"
        ),
        "_AnimationBuilder.__init__": (
            "66e570764c551d4b7f2b70ab21ca397df8a931071c50977c2cd77288a4204966"
        ),
        "_AnimationBuilder.__getattr__": (
            "6b7caeec3a7b73f27b49e5f2576ae99809d7b956468ed1947d0dace317510e03"
        ),
        "always_redraw": (
            "f725d6d9c3fbbe1ec63f06926d17055b8946d171e7e71b6bf9e7cc069a7317cf"
        ),
        "Scene.get_moving_mobjects": (
            "d78d2af73679041f74533e42fea88d80c16ae9bf954de2216106b7f1fa69e0b2"
        ),
        "Scene.should_update_mobjects": (
            "28c43743dc124aaaf3008b756eca0e42c64efcfa4faaba29ecf00afad9f74d4c"
        ),
        "Scene.update_to_time": (
            "c554748b52bb38f61efaa8b973568bcfc69069b8c51a065e8ce24745af118836"
        ),
        "Scene.play_internal": (
            "c83eff575fd7732171dbc37a99b443b03f577361efe2f528375da418783639c5"
        ),
        "Scene.add": (
            "5b1b4b7970420ce937cb5e6117f510314cf35275a249051ec9e33fadc5cdd923"
        ),
        "Scene.add_mobjects_from_animations": (
            "a236f35c5ee7b1231fd9d70d04fd4c4e4150022068f7ae92d48db565af37c4e7"
        ),
        "CairoRenderer.play": (
            "5affbe0f311d60998ea09f67f9bf8c9b5355c04df1aff90808c3be85ea64e4a8"
        ),
        "Camera.set_cairo_context_path": (
            "0e53e5837e78857d20178931c265487d10db6d8eb57c6784b6dee9feb4375dbf"
        ),
        "DrawBorderThenFill.begin": (
            "a4a73c4ecb61734d10a94bfad4a53f0e7cd135ebd9653065820e90ca1f76d720"
        ),
        "Mobject.__getattr__": (
            "4b63b7f9c1e9a41087e93e3c5c9fea4413523b5511af51caf4f06d8f2c6d451b"
        ),
        "VMobject.set_fill": (
            "e325766f129f638c59186f1b32ff63d4601a653a20744467f62db4713772f49e"
        ),
        "VMobject.set_stroke": (
            "1ee05806ebe6f8558b037e760bdcfac0ad9595bced1d993a85c8abee95772595"
        ),
        "VMobject.interpolate_color": (
            "1f9f95a1383f72ba1576bb0177cb81b32b95dc115b337b36b152c3c521b2d72d"
        ),
        "VMobject.pointwise_become_partial": (
            "c78b17aeb714c07dc36e800a54c642f1226503698ed9a38224322eb45ac1f21d"
        ),
        "VGroup.add": (
            "0c23544a19789dd871a576725ac0832fe2a0af89a75dac8c7c26eb598edd515a"
        ),
        "Mobject.get_family_updaters": (
            "37cd7d253aa5e9d4ccfaddd4e81677fadaf99600f4b9ba7b6d9d5717f71e86c8"
        ),
    },
}

_WARNED: set[tuple[str, str]] = set()


def symbol_name(symbol: Callable[..., object]) -> str:
    """Return the qualified name used as a symbol's pin key.

    Parameters
    ----------
    symbol
        A callable from the Manim inventory.

    Returns
    -------
    str
        The callable's qualified name.
    """
    return symbol.__qualname__


def source_hashes() -> dict[str, str]:
    """Hash the exact UTF-8 source lines of every inventoried symbol.

    Returns
    -------
    dict of str to str
        Qualified names mapped to SHA-256 hexadecimal digests.
    """
    return {
        symbol_name(symbol): hashlib.sha256(
            "".join(inspect.getsourcelines(symbol)[0]).encode("utf-8")
        ).hexdigest()
        for symbol in SYMBOLS
    }


def check_pins(version: str | None = None) -> None:
    """Warn once for an unsupported Manim version or changed source symbol.

    Parameters
    ----------
    version
        Version whose pins to compare, defaulting to the installed Manim version.
    """
    version = manim.__version__ if version is None else version
    if version not in PINS:
        key = (version, "")
        message = f"Manim {version} is unpinned; supported versions: {', '.join(PINS)}"
    else:
        expected = PINS[version]
        try:
            actual = source_hashes()
        except (OSError, TypeError) as exc:
            key = (version, "source")
            message = f"Manim {version} source pins could not be checked: {exc}"
        else:
            differing = next(
                (name for name in expected if actual.get(name) != expected[name]), None
            )
            if differing is None:
                differing = next(
                    (name for name in actual if name not in expected), None
                )
            if differing is None:
                return
            key = (version, differing)
            message = f"Manim {version} source pin differs for {differing}"
    if key not in _WARNED:
        _WARNED.add(key)
        warnings.warn(message, ManimPlotsWarning, stacklevel=2)


def _last_write(method: Callable[..., Any]) -> int:
    lines, first = inspect.getsourcelines(method)
    tree = ast.parse(textwrap.dedent("".join(lines)))
    writes: list[int] = []
    for node in ast.walk(tree):
        targets = (
            node.targets
            if isinstance(node, ast.Assign)
            else [node.target]
            if isinstance(node, (ast.AugAssign, ast.AnnAssign))
            else []
        )
        if any(isinstance(t, ast.Attribute) and t.attr == "points" for t in targets):
            writes.append(first + cast(ast.stmt, node).lineno - 1)
    return max(writes)


_WRITERS = {
    Mobject.shift.__code__: _last_write(Mobject.shift),
    Mobject.apply_points_function_about_point.__code__: _last_write(
        Mobject.apply_points_function_about_point
    ),
}
_BEGIN = frozenset(
    m.__code__
    for m in (Animation.begin, AnimationGroup.begin, Succession.begin, Transform.begin)
)
_FINISH = frozenset(
    m.__code__ for m in (Animation.finish, AnimationGroup.finish, Succession.finish)
)


def affine_context() -> FloatArray | None:
    """Return the native operation's exact row-vector linear matrix, if any."""
    frame: FrameType | None = sys._getframe(1)
    try:
        while frame is not None:
            code, values = frame.f_code, frame.f_locals
            if code is Mobject.rotate.__code__:
                return cast(FloatArray, values["rot_matrix"].T.copy())
            if code is Mobject.scale.__code__:
                return np.eye(3) * float(values["scale_factor"])
            if code is Mobject.stretch.__code__:
                matrix = np.eye(3)
                matrix[values["dim"], values["dim"]] = values["factor"]
                return matrix
            if code is Mobject.apply_matrix.__code__:
                return cast(FloatArray, values["full_matrix"].T.copy())
            frame = frame.f_back
        return None
    finally:
        del frame


def animation_context(
    finishing: bool = False, transform_only: bool = False
) -> Animation | None:
    """Read the nearest animation begin or finish boundary.

    Parameters
    ----------
    finishing
        Read a finish boundary instead of a begin boundary.
    transform_only
        Restrict the query to Transform.begin, before point alignment.
    """
    codes = (
        {Transform.begin.__code__}
        if transform_only
        else _FINISH
        if finishing
        else _BEGIN
    )
    frame: FrameType | None = sys._getframe(1)
    try:
        while frame is not None:
            if frame.f_code in codes:
                return cast(Animation, frame.f_locals["self"])
            frame = frame.f_back
        return None
    finally:
        del frame


@dataclass
class WriterContext:
    """Hold copied operation facts and a family memo, without retaining a frame.

    Parameters
    ----------
    container, family
        Native writer and its family, collected once per operation.
    vector
        Shift vector, or None for a points function.
    function, pivot, matrix
        Points function, pivot and optional exact row-vector linear matrix.
    application
        Original VMobject.apply_function invocation, if present.
    last
        Whether this assignment is the writer's final points assignment.
    """

    container: Mobject
    family: frozenset[Mobject]
    vector: FloatArray | None = None
    function: Callable[[FloatArray], FloatArray] | None = None
    pivot: FloatArray | None = None
    matrix: FloatArray | None = None
    application: tuple[VMobject, Callable[..., Any]] | None = None
    last: bool = False


def writer_context() -> WriterContext | None:
    """Attribute a native geometric write and memoise its container family."""
    frame: FrameType | None = sys._getframe(1)
    try:
        while frame is not None:
            code = frame.f_code
            if code in _WRITERS:
                values = frame.f_locals
                result = values.get("__manim_plots_writer")
                if result is None:
                    container = values["self"]
                    result = WriterContext(container, frozenset(container.get_family()))
                    if code is Mobject.shift.__code__:
                        # Manim passes a tuple through when one tuple is given.
                        result.vector = np.array(values["total_vector"], dtype=float)
                    else:
                        result.function = values["func"]
                        result.pivot = np.array(values["about_point"], dtype=float)
                        result.matrix = affine_context()
                        outer = frame.f_back
                        try:
                            while outer is not None:
                                if outer.f_code is VMobject.apply_function.__code__:
                                    result.application = (
                                        outer.f_locals["self"],
                                        outer.f_locals["function"],
                                    )
                                    break
                                outer = outer.f_back
                        finally:
                            del outer
                    values["__manim_plots_writer"] = result
                result.last = frame.f_lineno == _WRITERS[code]
                return cast(WriterContext, result)
            frame = frame.f_back
        return None
    finally:
        del frame


def buffer_write() -> bool:
    """Return whether a getter is inside a multi-assignment native operation."""
    frame: FrameType | None = sys._getframe(2)
    try:
        while frame is not None:
            code = frame.f_code
            if code in _WRITERS or code is VMobject.set_anchors_and_handles.__code__:
                return True
            frame = frame.f_back
        return False
    finally:
        del frame


def playback_context() -> tuple[int, float | str, int] | None:
    """Return a shared token for a rendered frame or a play's finish boundary."""
    frame: FrameType | None = sys._getframe(1)
    boundary = None
    try:
        while frame is not None:
            if frame.f_code is Scene.update_to_time.__code__:
                values = frame.f_locals
                token = values.get("__manim_plots_playback")
                if token is None:
                    scene = values["self"]
                    token = (id(scene), values["t"], int(scene.renderer.num_plays))
                    values["__manim_plots_playback"] = token
                return cast(tuple[int, float | str, int], token)
            if frame.f_code is Scene.play_internal.__code__:
                scene = frame.f_locals["self"]
                boundary = (id(scene), "finish", int(scene.renderer.num_plays))
            frame = frame.f_back
        return boundary
    finally:
        del frame


def moving_context() -> frozenset[Mobject] | None:
    """Read and memoise animated families during Cairo's moving-object query."""
    frame: FrameType | None = sys._getframe(1)
    try:
        while frame is not None:
            if frame.f_code is Scene.get_moving_mobjects.__code__:
                values = frame.f_locals
                result = values.get("__manim_plots_moving")
                if result is None:
                    result = frozenset(values["animation_mobjects"])
                    values["__manim_plots_moving"] = result
                return cast(frozenset[Mobject], result)
            frame = frame.f_back
        return None
    finally:
        del frame
