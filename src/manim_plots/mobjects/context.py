"""Inventory and source pins for the Manim internals used by the library."""

import ast
import hashlib
import inspect
import sys
import textwrap
import warnings
import weakref
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import FrameType
from typing import Any, cast

import manim
import numpy as np
from manim import (
    Animation,
    AnimationGroup,
    Axes,
    CoordinateSystem,
    DashedLine,
    DashedVMobject,
    DecimalNumber,
    FadeOut,
    Line,
    LogBase,
    Mobject,
    MoveAlongPath,
    NumberLine,
    NumberPlane,
    PhaseFlow,
    Scene,
    ShowIncreasingSubsets,
    ShowPassingFlash,
    Succession,
    TangentLine,
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
from manim.utils.color import color_gradient, invert_color
from manim.utils.hashing import (
    _CustomEncoder,
    _Memoizer,
    get_hash_from_play_call,
    get_json,
)

from manim_plots.core import FloatArray, ManimPlotsWarning

SYMBOLS: tuple[Callable[..., object], ...] = (
    get_json,
    get_hash_from_play_call,
    _CustomEncoder.default,
    _Memoizer._handle_already_processed,
    NumberLine.__init__,
    NumberLine.get_tick,
    NumberLine.get_tick_range,
    NumberLine.number_to_point,
    NumberLine.point_to_number,
    NumberLine.get_unit_size,
    NumberLine.get_unit_vector,
    NumberLine.get_number_mobject,
    NumberLine.add_numbers,
    NumberLine.add_labels,
    NumberLine._create_label_tex,
    NumberLine._decimal_places_from_step,
    Axes.__init__,
    Axes._create_axis,
    Axes._origin_shift,
    Axes.coords_to_point,
    Axes.point_to_coords,
    Axes.get_axis_labels,
    CoordinateSystem.add_coordinates,
    CoordinateSystem.get_x_axis_label,
    CoordinateSystem.get_y_axis_label,
    CoordinateSystem._get_axis_label,
    CoordinateSystem.get_graph_label,
    CoordinateSystem.get_line_from_axis_to_point,
    CoordinateSystem.get_vertical_line,
    CoordinateSystem.get_horizontal_line,
    CoordinateSystem.get_lines_to_point,
    CoordinateSystem.get_vertical_lines_to_graph,
    CoordinateSystem.get_T_label,
    CoordinateSystem.angle_of_tangent,
    CoordinateSystem.slope_of_tangent,
    CoordinateSystem.get_secant_slope_group,
    CoordinateSystem.plot_derivative_graph,
    CoordinateSystem.plot_antiderivative_graph,
    CoordinateSystem.get_area,
    CoordinateSystem.get_riemann_rectangles,
    color_gradient,
    invert_color,
    VMobject.set_color,
    DashedLine.__init__,
    DashedLine._calculate_num_dashes,
    DashedVMobject.__init__,
    TangentLine.__init__,
    Line.__init__,
    Line._account_for_buff,
    DecimalNumber._set_submobjects_from_number,
    DecimalNumber._get_num_string,
    DecimalNumber._get_formatter,
    NumberPlane.__init__,
    NumberPlane._init_background_lines,
    NumberPlane._get_lines,
    NumberPlane._get_lines_parallel_to_axis,
    LogBase.get_custom_labels,
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
    VMobject.scale,
    VMobject.split,
    Animation.interpolate_mobject,
    Mobject.family_members_with_points,
)

PINS: Mapping[str, Mapping[str, str]] = {
    "0.21.0": {
        "CoordinateSystem.get_area": (
            "4b24b4037cd9abe31a566691d25d1844e1e41f01a04da9d2b9f9ab17531af970"
        ),
        "CoordinateSystem.get_riemann_rectangles": (
            "0c7e7662dcc6a231c7f571c5e631324a2ad8eece108342758c48950ec05cce05"
        ),
        "color_gradient": (
            "c6b28da6e0eda69ca481272eabe9917bf50143c9bdcc4d549e28d31bab4b2fe3"
        ),
        "invert_color": (
            "7ac36a3cd0299d60d53fb2030eab37ba79b38478f1fc67dd4d433b722fe72a9d"
        ),
        "VMobject.set_color": (
            "2acb9bb456271e1b4451beee65b5c1ae692e775ff8538646fe3f11f6c6b7000b"
        ),
        "DashedVMobject.__init__": (
            "94025800226b238d2f97601266292fb00f4785049dc231d3387e063106b174d8"
        ),
        "CoordinateSystem.get_line_from_axis_to_point": (
            "a2aba1ee4fee10863c51ea03536a6650be0228d35b3d60d70d68be6302a12465"
        ),
        "CoordinateSystem.get_vertical_line": (
            "454572845bb8950b67337ebed2d3d07f125d6a617257f4c9a5bc6d0d02952488"
        ),
        "CoordinateSystem.get_horizontal_line": (
            "ff27b3c362ea3ba1bf52cf452afdae57f6af0f8757129c11a1e69e148879c59f"
        ),
        "CoordinateSystem.get_lines_to_point": (
            "a74430bffacac4937b316b806d97fa042bcbb72b756860489a1e62dfce1f4d49"
        ),
        "CoordinateSystem.get_vertical_lines_to_graph": (
            "21a720a4cb00aa75b6429530db11c368b1d7e0b2200ddb1117ba61530472f869"
        ),
        "CoordinateSystem.get_T_label": (
            "8c77bbb14a30496fc11cf0b230f36cd1796bb603f6b8ad819f2ca11682d7c48a"
        ),
        "CoordinateSystem.angle_of_tangent": (
            "9f35b1c8d595882ca436dc3211519187a78aa3dc66eb68042cb04a3bcfb9f6a6"
        ),
        "CoordinateSystem.slope_of_tangent": (
            "fcb9e995f09dfa7a9317d5fa7d520334f33deb22311e31b3fcad7f2e27417985"
        ),
        "CoordinateSystem.get_secant_slope_group": (
            "5ba9cba3d65e5bd56134349c4cd077e3319806104f5809471ee9fdc8597e641b"
        ),
        "CoordinateSystem.plot_derivative_graph": (
            "37b6974aedda180664cd7579b417bb0fdd5abd302cc5605b675245436c2b3e05"
        ),
        "CoordinateSystem.plot_antiderivative_graph": (
            "a98df77383cebe0f341393f2a95f7a20b209e1dca30783e9efcb71ba1e27bd2e"
        ),
        "DashedLine.__init__": (
            "9d507bbe97021a4a0a4125443d350ce428cbe556d9b928ffa4ccb9f3c2007fa8"
        ),
        "DashedLine._calculate_num_dashes": (
            "a7f096d1f0585ece460d84711c8ffb4cb6a11a620e8827bfa5dfcb2d6ed0a6c4"
        ),
        "TangentLine.__init__": (
            "135a555ebd431ad3d882fef073a8e17205418a4650808186c81ff8738989913f"
        ),
        "Line.__init__": (
            "f878f82eced744c5893e782dcf324b309266900bb948293a7313f701fe3ac0bf"
        ),
        "Line._account_for_buff": (
            "834ce9ce3971cc11fc7aec7b1747c432df83a49b6a572ab56c38bce9cff6908a"
        ),
        "get_json": (
            "dbe7d2639c78f2dcc702c9b4f325e59498789259aa738f5ac75c408ed5e4ae87"
        ),
        "get_hash_from_play_call": (
            "b7d5f2fe8ab3ab9c84dbe8ee9fbac4babaafbff8ec5c1408bb6d81b92b017373"
        ),
        "_CustomEncoder.default": (
            "39c83d428607292ace2ec8a2a2d1bd5e636d95cadf38da2b44d35dcfafac1125"
        ),
        "_Memoizer._handle_already_processed": (
            "717d612fcdd1a521fd45ba92f47cdfdc2e32c5c647090cfdf2aa40e17d208d5d"
        ),
        "NumberLine.__init__": (
            "009ac481d80c22e2859219dfb574bfb554c9dcb029980de5097076ca01098b8b"
        ),
        "NumberLine.get_tick": (
            "657a50c4eb02d7a777299f3797143fbf1d954cd19e962934f1fc7ee040bf3c98"
        ),
        "NumberLine.get_tick_range": (
            "038e6d4154a1459f85b5c3179c5dac62140687f499f464edcdb3131e6a662a64"
        ),
        "NumberLine.number_to_point": (
            "32c1849884ab85687754a14e6b0ed60b733f14e8ab7c3d5ec160406af03346a2"
        ),
        "NumberLine.point_to_number": (
            "afd72e45e8ed16aad8b45e60692f30f36e001e93f10b4ec9accfa00e036d6d6b"
        ),
        "NumberLine.get_unit_size": (
            "914414aea7e3ae8f81bdac76e2197a89e37b70040cae21f1e4f5228107aa031e"
        ),
        "NumberLine.get_unit_vector": (
            "9606242fc88ed1e75138f7ca2bcd2d3d4b71cc4f0fd566fae54356cdcd3d4d54"
        ),
        "NumberLine.get_number_mobject": (
            "27f88fb21d4212b024cc3718f5e0b20346ad67478c287b362a09860cca144be5"
        ),
        "NumberLine.add_numbers": (
            "14bfde7e479edcceae448457a60a1a2cc55e68d96b8d49bd0748fed6228d1dcd"
        ),
        "NumberLine.add_labels": (
            "42dc9735756061afaada6aae089d35f5d7c2aa787da6df5485b5df51ffee8028"
        ),
        "NumberLine._create_label_tex": (
            "786c70857fd0172d7da86c9ed8dc487174dc0cb8fac601427bd5a65efd51c190"
        ),
        "NumberLine._decimal_places_from_step": (
            "f0d11aaf66140c5b6c2c0f44d73d2105251d95cccab66532620b407715855633"
        ),
        "Axes.__init__": (
            "e28c172944e9412f15465f44684c6275381e395fc1b79ce1764c7a6599a6ce23"
        ),
        "Axes._create_axis": (
            "a2341426a116935894bedb7d649632bfc4897bcfa8a0f67e61c3be7eba5aab36"
        ),
        "Axes._origin_shift": (
            "09850bdcba2b1bb775dcae0f38ebb1d77cacf2ba0ef3618f34e013aef1dbd254"
        ),
        "Axes.coords_to_point": (
            "9ea620816d0ab8e55620fd277504fb3a2558a400afdb1c46ddb560111823139d"
        ),
        "Axes.point_to_coords": (
            "e26c9b825c9315b444ecb7ae755ee594d471b87d3c8d2e3c40d20015b7a4834f"
        ),
        "Axes.get_axis_labels": (
            "91b177522bb84d93481e3e5c9db628eb61f75247c6f77c85a047c05f9196061b"
        ),
        "CoordinateSystem.add_coordinates": (
            "114651538830075b663f08d5b49bc1597ad9e3d254e19d6d348f591b5f16bf11"
        ),
        "CoordinateSystem.get_x_axis_label": (
            "914e181b3fb7b98e75cfae4a7e46faa79628f0d14f2f857318388412ae7e6fe3"
        ),
        "CoordinateSystem.get_y_axis_label": (
            "2cdfc799f218b08f46e638e2cfbec45f3e22f060d592d0493399d2dec5d6a3a2"
        ),
        "CoordinateSystem._get_axis_label": (
            "7caef98d9da34e8068d0cacded98ed11d66afa87d62986ea6dc5373b5177404f"
        ),
        "CoordinateSystem.get_graph_label": (
            "85b36b3439d0f908acee5d2efa1b8a1d1901a06ef19088cbf4138e50a810cad3"
        ),
        "DecimalNumber._set_submobjects_from_number": (
            "70e08296f775e5f7585a3eb28a42717842812b2aafe8268c417584377b345609"
        ),
        "DecimalNumber._get_num_string": (
            "f4f4b1da599a62bade405dd85546db63377b9767364d4e82bd7f4903f8c41c11"
        ),
        "DecimalNumber._get_formatter": (
            "d16c844a43a9c5f8e569f7a1fbf8f3738361d043fbe85605f3f92181788fe9f6"
        ),
        "NumberPlane.__init__": (
            "ddf180e3a3253a7c68ac1bbf745bc5a30533cb6fbe5572c3fac0a19370fcd68c"
        ),
        "NumberPlane._init_background_lines": (
            "002687c99d845acab6a9b470c50260b81b8357c655552f2ec46d9a08e74339fd"
        ),
        "NumberPlane._get_lines": (
            "953654c1ac8bea9da7878170bd569cfb8604a5c4e178262b6b183d78b1da510b"
        ),
        "NumberPlane._get_lines_parallel_to_axis": (
            "03fde9988571dc6dc28ba3ff8ff4914e1774159e09040be502da40cc68e34c5b"
        ),
        "LogBase.get_custom_labels": (
            "d92f86ca4ffedbb5c4844c8657003d9d9f06c8ad66f76eb128e8a4a4f1415c36"
        ),
        "VMobject.scale": (
            "a49555af84f1592f2649dfc9bd89f8b91331b3193ff00162185d462b40a54a37"
        ),
        "VMobject.split": (
            "ed5b27ee300e1e74e5ad8a3d30b6c0ac0e60cbba3604d275577272f6c1d04371"
        ),
        "Animation.interpolate_mobject": (
            "6df42ab42e168d57a38584100dd57cc87b474fcee5a2531ca3d0c4465b28bb66"
        ),
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
        "Mobject.family_members_with_points": (
            "fc69ac2726f2d19db2e5785f72daa86622157cd1efbe74fc91bd25e51dc38c26"
        ),
    },
    "0.22.0": {
        "CoordinateSystem.get_area": (
            "4b24b4037cd9abe31a566691d25d1844e1e41f01a04da9d2b9f9ab17531af970"
        ),
        "CoordinateSystem.get_riemann_rectangles": (
            "0c7e7662dcc6a231c7f571c5e631324a2ad8eece108342758c48950ec05cce05"
        ),
        "color_gradient": (
            "c6b28da6e0eda69ca481272eabe9917bf50143c9bdcc4d549e28d31bab4b2fe3"
        ),
        "invert_color": (
            "7ac36a3cd0299d60d53fb2030eab37ba79b38478f1fc67dd4d433b722fe72a9d"
        ),
        "VMobject.set_color": (
            "2acb9bb456271e1b4451beee65b5c1ae692e775ff8538646fe3f11f6c6b7000b"
        ),
        "DashedVMobject.__init__": (
            "94025800226b238d2f97601266292fb00f4785049dc231d3387e063106b174d8"
        ),
        "CoordinateSystem.get_line_from_axis_to_point": (
            "a2aba1ee4fee10863c51ea03536a6650be0228d35b3d60d70d68be6302a12465"
        ),
        "CoordinateSystem.get_vertical_line": (
            "454572845bb8950b67337ebed2d3d07f125d6a617257f4c9a5bc6d0d02952488"
        ),
        "CoordinateSystem.get_horizontal_line": (
            "ff27b3c362ea3ba1bf52cf452afdae57f6af0f8757129c11a1e69e148879c59f"
        ),
        "CoordinateSystem.get_lines_to_point": (
            "a74430bffacac4937b316b806d97fa042bcbb72b756860489a1e62dfce1f4d49"
        ),
        "CoordinateSystem.get_vertical_lines_to_graph": (
            "21a720a4cb00aa75b6429530db11c368b1d7e0b2200ddb1117ba61530472f869"
        ),
        "CoordinateSystem.get_T_label": (
            "8c77bbb14a30496fc11cf0b230f36cd1796bb603f6b8ad819f2ca11682d7c48a"
        ),
        "CoordinateSystem.angle_of_tangent": (
            "9f35b1c8d595882ca436dc3211519187a78aa3dc66eb68042cb04a3bcfb9f6a6"
        ),
        "CoordinateSystem.slope_of_tangent": (
            "fcb9e995f09dfa7a9317d5fa7d520334f33deb22311e31b3fcad7f2e27417985"
        ),
        "CoordinateSystem.get_secant_slope_group": (
            "5ba9cba3d65e5bd56134349c4cd077e3319806104f5809471ee9fdc8597e641b"
        ),
        "CoordinateSystem.plot_derivative_graph": (
            "37b6974aedda180664cd7579b417bb0fdd5abd302cc5605b675245436c2b3e05"
        ),
        "CoordinateSystem.plot_antiderivative_graph": (
            "a98df77383cebe0f341393f2a95f7a20b209e1dca30783e9efcb71ba1e27bd2e"
        ),
        "DashedLine.__init__": (
            "9d507bbe97021a4a0a4125443d350ce428cbe556d9b928ffa4ccb9f3c2007fa8"
        ),
        "DashedLine._calculate_num_dashes": (
            "a7f096d1f0585ece460d84711c8ffb4cb6a11a620e8827bfa5dfcb2d6ed0a6c4"
        ),
        "TangentLine.__init__": (
            "135a555ebd431ad3d882fef073a8e17205418a4650808186c81ff8738989913f"
        ),
        "Line.__init__": (
            "f878f82eced744c5893e782dcf324b309266900bb948293a7313f701fe3ac0bf"
        ),
        "Line._account_for_buff": (
            "834ce9ce3971cc11fc7aec7b1747c432df83a49b6a572ab56c38bce9cff6908a"
        ),
        "get_json": (
            "dbe7d2639c78f2dcc702c9b4f325e59498789259aa738f5ac75c408ed5e4ae87"
        ),
        "get_hash_from_play_call": (
            "ac69107783b6cf4dc819baa833aed7ae323a8fb8180770642be74fa6300c21f5"
        ),
        "_CustomEncoder.default": (
            "39c83d428607292ace2ec8a2a2d1bd5e636d95cadf38da2b44d35dcfafac1125"
        ),
        "_Memoizer._handle_already_processed": (
            "717d612fcdd1a521fd45ba92f47cdfdc2e32c5c647090cfdf2aa40e17d208d5d"
        ),
        "NumberLine.__init__": (
            "009ac481d80c22e2859219dfb574bfb554c9dcb029980de5097076ca01098b8b"
        ),
        "NumberLine.get_tick": (
            "657a50c4eb02d7a777299f3797143fbf1d954cd19e962934f1fc7ee040bf3c98"
        ),
        "NumberLine.get_tick_range": (
            "038e6d4154a1459f85b5c3179c5dac62140687f499f464edcdb3131e6a662a64"
        ),
        "NumberLine.number_to_point": (
            "32c1849884ab85687754a14e6b0ed60b733f14e8ab7c3d5ec160406af03346a2"
        ),
        "NumberLine.point_to_number": (
            "82ad8de92c7eefc5be9a45b86bbc7056e302c05d516a2873f9e3ca7324b4d763"
        ),
        "NumberLine.get_unit_size": (
            "914414aea7e3ae8f81bdac76e2197a89e37b70040cae21f1e4f5228107aa031e"
        ),
        "NumberLine.get_unit_vector": (
            "9606242fc88ed1e75138f7ca2bcd2d3d4b71cc4f0fd566fae54356cdcd3d4d54"
        ),
        "NumberLine.get_number_mobject": (
            "27f88fb21d4212b024cc3718f5e0b20346ad67478c287b362a09860cca144be5"
        ),
        "NumberLine.add_numbers": (
            "14bfde7e479edcceae448457a60a1a2cc55e68d96b8d49bd0748fed6228d1dcd"
        ),
        "NumberLine.add_labels": (
            "42dc9735756061afaada6aae089d35f5d7c2aa787da6df5485b5df51ffee8028"
        ),
        "NumberLine._create_label_tex": (
            "786c70857fd0172d7da86c9ed8dc487174dc0cb8fac601427bd5a65efd51c190"
        ),
        "NumberLine._decimal_places_from_step": (
            "f0d11aaf66140c5b6c2c0f44d73d2105251d95cccab66532620b407715855633"
        ),
        "Axes.__init__": (
            "e28c172944e9412f15465f44684c6275381e395fc1b79ce1764c7a6599a6ce23"
        ),
        "Axes._create_axis": (
            "a2341426a116935894bedb7d649632bfc4897bcfa8a0f67e61c3be7eba5aab36"
        ),
        "Axes._origin_shift": (
            "09850bdcba2b1bb775dcae0f38ebb1d77cacf2ba0ef3618f34e013aef1dbd254"
        ),
        "Axes.coords_to_point": (
            "9ea620816d0ab8e55620fd277504fb3a2558a400afdb1c46ddb560111823139d"
        ),
        "Axes.point_to_coords": (
            "e26c9b825c9315b444ecb7ae755ee594d471b87d3c8d2e3c40d20015b7a4834f"
        ),
        "Axes.get_axis_labels": (
            "91b177522bb84d93481e3e5c9db628eb61f75247c6f77c85a047c05f9196061b"
        ),
        "CoordinateSystem.add_coordinates": (
            "114651538830075b663f08d5b49bc1597ad9e3d254e19d6d348f591b5f16bf11"
        ),
        "CoordinateSystem.get_x_axis_label": (
            "914e181b3fb7b98e75cfae4a7e46faa79628f0d14f2f857318388412ae7e6fe3"
        ),
        "CoordinateSystem.get_y_axis_label": (
            "2cdfc799f218b08f46e638e2cfbec45f3e22f060d592d0493399d2dec5d6a3a2"
        ),
        "CoordinateSystem._get_axis_label": (
            "7caef98d9da34e8068d0cacded98ed11d66afa87d62986ea6dc5373b5177404f"
        ),
        "CoordinateSystem.get_graph_label": (
            "85b36b3439d0f908acee5d2efa1b8a1d1901a06ef19088cbf4138e50a810cad3"
        ),
        "DecimalNumber._set_submobjects_from_number": (
            "70e08296f775e5f7585a3eb28a42717842812b2aafe8268c417584377b345609"
        ),
        "DecimalNumber._get_num_string": (
            "f4f4b1da599a62bade405dd85546db63377b9767364d4e82bd7f4903f8c41c11"
        ),
        "DecimalNumber._get_formatter": (
            "d16c844a43a9c5f8e569f7a1fbf8f3738361d043fbe85605f3f92181788fe9f6"
        ),
        "NumberPlane.__init__": (
            "ddf180e3a3253a7c68ac1bbf745bc5a30533cb6fbe5572c3fac0a19370fcd68c"
        ),
        "NumberPlane._init_background_lines": (
            "002687c99d845acab6a9b470c50260b81b8357c655552f2ec46d9a08e74339fd"
        ),
        "NumberPlane._get_lines": (
            "953654c1ac8bea9da7878170bd569cfb8604a5c4e178262b6b183d78b1da510b"
        ),
        "NumberPlane._get_lines_parallel_to_axis": (
            "03fde9988571dc6dc28ba3ff8ff4914e1774159e09040be502da40cc68e34c5b"
        ),
        "LogBase.get_custom_labels": (
            "d92f86ca4ffedbb5c4844c8657003d9d9f06c8ad66f76eb128e8a4a4f1415c36"
        ),
        "VMobject.scale": (
            "a49555af84f1592f2649dfc9bd89f8b91331b3193ff00162185d462b40a54a37"
        ),
        "VMobject.split": (
            "ed5b27ee300e1e74e5ad8a3d30b6c0ac0e60cbba3604d275577272f6c1d04371"
        ),
        "Animation.interpolate_mobject": (
            "6df42ab42e168d57a38584100dd57cc87b474fcee5a2531ca3d0c4465b28bb66"
        ),
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
        "Mobject.family_members_with_points": (
            "fc69ac2726f2d19db2e5785f72daa86622157cd1efbe74fc91bd25e51dc38c26"
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


def data_interpolation() -> bool:
    """Identify a Transform's simultaneous derived-data interpolation query."""
    frame: FrameType | None = sys._getframe(1)
    try:
        while frame is not None:
            if frame.f_code is Transform.get_all_families_zipped.__code__:
                return bool(frame.f_locals["self"].lag_ratio == 0)
            frame = frame.f_back
        return False
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


type _PlaybackToken = tuple[weakref.ReferenceType[Scene], float | str, int]


def playback_context() -> _PlaybackToken | None:
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
                    token = (
                        weakref.ref(scene),
                        values["t"],
                        int(scene.renderer.num_plays),
                    )
                    values["__manim_plots_playback"] = token
                return cast(_PlaybackToken, token)
            if frame.f_code is Scene.play_internal.__code__:
                scene = frame.f_locals["self"]
                boundary = (weakref.ref(scene), "finish", int(scene.renderer.num_plays))
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
