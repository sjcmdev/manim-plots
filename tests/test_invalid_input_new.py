"""Task 23 invalid-input oracles; row contracts live in 23-invalid-input.md."""

from __future__ import annotations

import re
import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from typing import Any, cast

import numpy as np
import pytest
from manim import RED, Dot, Rectangle, Scene

import manim_plots as mp
from manim_plots.core import ManimPlotsWarning
from manim_plots.mobjects import axis as axis_module
from manim_plots.mobjects import leaves as leaves_module


@pytest.fixture(autouse=True)
def no_tex_metrics(monkeypatch):
    # Font outlines do not enter these oracles; avoid the density probe's TeX call.
    def metric_glyph(*args, **kwargs):
        return leaves_module.GlyphLeaf(Rectangle(width=0.1, height=0.2).points)

    monkeypatch.setattr(axis_module, "_glyph", metric_glyph)
    monkeypatch.setattr(leaves_module, "_glyph", metric_glyph)


def polar(constructor: Any = mp.PolarAxes, **kwargs: Any) -> Any:
    options = (
        {
            "r_axis_config": {"include_numbers": False},
            "azimuth_axis_config": {"include_numbers": False},
        }
        if constructor is mp.PolarAxes
        else {}
    )
    return constructor(**(options | kwargs))


@contextmanager
def counted() -> Iterator[list[warnings.WarningMessage]]:
    """Record every library warning, so a test can count them."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ManimPlotsWarning)
        yield caught


def library(caught: list[warnings.WarningMessage]) -> int:
    return sum(issubclass(w.category, ManimPlotsWarning) for w in caught)


def axes(**kwargs: Any) -> Any:
    options: dict[str, Any] = dict(x_range=(-2, 4, 1), y_range=(-2, 8, 1), tips=False)
    return mp.Axes(**(options | kwargs))


def three(**kwargs: Any) -> Any:
    options: dict[str, Any] = dict(
        x_range=(-2, 4, 1),
        y_range=(-2, 4, 1),
        z_range=(-2, 8, 1),
        tips=False,
        occlusion=False,
    )
    return mp.ThreeDAxes(**(options | kwargs))


def touch(artist: Any) -> None:
    for member in artist.get_family():
        assert np.isfinite(member.points).all()


def empty(artist: Any) -> None:
    touch(artist)
    assert not any(m.has_points() for m in artist.get_family())


def rejects(make, parameter, *, kind=ValueError, index=None, lengths=()):
    with counted() as caught, pytest.raises(kind) as exc:
        make()
    assert library(caught) == 0
    message = str(exc.value)
    assert re.search(rf"(?<!\w){re.escape(parameter)}(?!\w)", message), message
    if index is not None:
        # Do not prescribe brackets versus '(row, col)' in diagnostic prose.
        assert re.search(rf"(?<!\d){index}(?!\d)", message), message
    for length in lengths:
        assert re.search(rf"(?<!\d){length}(?!\d)", message), message


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
@pytest.mark.parametrize(
    "method,parameter",
    [
        ("axhline", "y"),
        ("axvline", "x"),
        ("axhspan", "ymin"),
        ("axvspan", "xmin"),
    ],
)
def test_hl1_nonfinite_positions(method, parameter, bad):
    ax = axes()
    args = (bad, 1) if "span" in method else (bad,)
    rejects(lambda: getattr(ax, method)(*args), parameter)


@pytest.mark.parametrize(
    "method,options,parameter",
    [
        ("get_tangent_line", {"length": np.inf}, "length"),
        ("get_secant_slope_group", {"dx": np.nan}, "dx"),
        ("get_tangent_line", {"x": object()}, "x"),
    ],
)
def test_hl2_helper_numeric_contract(method, options, parameter):
    ax = axes()
    graph = ax.plot(lambda x: x * x, x_range=(0, 2))
    kwargs = dict(x=1, graph=graph) | options
    rejects(
        lambda: getattr(ax, method)(**kwargs),
        parameter,
        kind=TypeError if parameter == "x" else ValueError,
    )


def test_hl3_region_shape_diagnostic():
    ax = axes()
    rejects(lambda: ax.fill_between([0, 1, 2], [1, 2]), "y1", lengths=(3, 2))
    rejects(lambda: ax.fill_between([[0, 1]], [1, 2]), "x")


@pytest.mark.parametrize("bad", [np.nan, np.inf])
def test_hl4_region_drops_adjacent_cells_and_deduplicates(bad):
    ax = axes()
    with counted() as caught:
        region = ax.fill_between([0, 1, 2, 3], [1, 1, bad, 1])
        touch(region)
        touch(region)
    assert library(caught) == 1
    paths = region.get_subpaths()
    assert paths
    for path in paths:
        assert ax.p2c(path)[:, 0].max() <= 1 + 1e-8
    with counted() as caught:
        region.set_color(RED)
        touch(region)
    assert library(caught) == 0
    with counted() as caught:
        ax.x.range = (-1, 4)
        touch(region)
    assert library(caught) == 1


def test_hl5_empty_region():
    ax = axes()
    with counted() as caught:
        region = ax.fill_between([], [])
        empty(region)
        touch(region)
    assert library(caught) == 1


@pytest.mark.parametrize("method", ["get_vertical_line", "get_horizontal_line"])
def test_hl6_drop_point_dimension(method):
    ax = axes()
    rejects(lambda: getattr(ax, method)([0, 1]), "point")


@pytest.mark.parametrize("method", ["annotate", "crosshair", "end_label"])
def test_hl7_2d_helper_parameters(method):
    ax = axes()
    graph = ax.plot(lambda x: x)
    if method == "annotate":
        rejects(lambda: ax.annotate(Dot(), (0, np.nan)), "xy", index=1)
    elif method == "crosshair":
        rejects(lambda: ax.crosshair(np.inf, 0, readout=False), "x")
    else:
        rejects(lambda: ax.end_label(graph, Dot(), buff=np.inf), "buff")


def test_hl8_derived_range_and_domain():
    ax = axes(x_range=(-1, 10), x_scale="log")
    with counted() as caught:
        graph = ax.plot(lambda x: x)
        derivative = ax.plot_derivative_graph(graph)
        area = ax.get_area(graph, x_range=(1, 2))
        rectangles = ax.get_riemann_rectangles(graph, x_range=(1, 2), dx=0.5)
        for artist in (derivative, area, rectangles):
            touch(artist)
    assert library(caught) == 0
    assert ax.x.range.value[0] > 0


@pytest.mark.parametrize("parameter", ["xerr", "yerr"])
def test_eb1_negative_error_first_index(parameter):
    ax = axes()
    # EB-2 already owns rejection; this adds the first-index diagnostic.
    rejects(
        lambda: ax.errorbar([0, 1, 2], [1, 2, 3], **{parameter: [0.1, -0.2, -0.3]}),
        parameter,
        index=1,
    )


def test_eb2_shapes_and_lengths():
    ax = axes()
    rejects(lambda: ax.errorbar([0, 1, 2], [1, 2]), "y", lengths=(3, 2))
    rejects(lambda: ax.errorbar([0, 1], [1, 2], yerr=np.ones((3, 2))), "yerr")


@pytest.mark.parametrize("parameter", ["capsize", "elinewidth", "capthick"])
def test_eb3_nonfinite_style_size(parameter):
    ax = axes()
    rejects(lambda: ax.errorbar([0], [1], yerr=0.1, **{parameter: np.inf}), parameter)


def test_eb4_warning_per_container_change():
    ax = axes()
    with counted() as caught:
        artist = ax.errorbar([0, 1], [2, 3], yerr=[0.2, np.nan], xerr=[0.1, 0.2])
        touch(artist)
        touch(artist)
    assert library(caught) == 1
    with counted() as caught:
        artist.set_color(RED)
        touch(artist)
    assert library(caught) == 0
    with counted() as caught:
        artist.set_data([0, 1], [2, 4], yerr=[0.3, np.nan], xerr=[0.2, 0.2])
        touch(artist)
    assert library(caught) == 1


def test_eb5_empty_container():
    ax = axes()
    with counted() as caught:
        artist = ax.errorbar([], [], yerr=[])
        empty(artist)
    assert library(caught) == 1


@pytest.mark.parametrize(
    "method,parameter", [("twinx", "y_range"), ("twiny", "x_range")]
)
def test_tw1_nonfinite_range(method, parameter):
    ax = axes()
    rejects(lambda: getattr(ax, method)(**{parameter: (0, np.inf)}), parameter, index=1)


def test_tw2_secondary_wrong_type():
    ax = axes()
    rejects(
        lambda: ax.secondary_xaxis(functions=(42, lambda x: x)),
        "functions",
        kind=TypeError,
    )


def test_tw3_inset_first_bad_bound():
    ax = axes()
    rejects(lambda: ax.inset((0, 0, np.nan, 0.5), (0, 1), (0, 1)), "bounds", index=2)


@pytest.mark.parametrize("method", ["twinx", "twiny", "twin", "inset"])
def test_tw4_conversion_never_clamps(method):
    ax = axes()
    child = (
        ax.inset((0.5, 0.5, 0.4, 0.4), (0, 2), (0, 2))
        if method == "inset"
        else getattr(ax, method)()
    )
    with pytest.raises(ValueError):
        child.c2p(np.nan, 0)
    with pytest.raises(ValueError):
        child.p2c([0, np.inf, 0])


def test_tw5_twin_range_normalised_before_sampling():
    ax = axes()
    with counted() as caught:
        twin = ax.twinx(y_range=(-1, 10), y_scale="log")
        graph = twin.plot(lambda x: 1.0)
        touch(graph)
    assert library(caught) == 0
    assert twin.y.range.value[0] > 0


@pytest.mark.parametrize("entry", ["set_theme", "Axes"])
def test_th1_wrong_theme_type(entry):
    old = mp.get_theme()
    try:
        rejects(lambda: getattr(mp, entry)(**{"theme": 42}), "theme", kind=TypeError)
        assert mp.get_theme() == old
    finally:
        mp.set_theme(old)


def test_th2_failed_theme_keeps_default():
    old = mp.get_theme()
    try:
        # TH-6 owns unknown-name rejection; this adds state preservation.
        rejects(lambda: mp.set_theme("missing-task23-theme"), "theme")
        assert mp.get_theme() == old
    finally:
        mp.set_theme(old)


@pytest.mark.parametrize("dimension", [2, 3])
def test_ff1_nonfinite_grid_range(dimension):
    ax = axes() if dimension == 2 else three()
    rejects(
        lambda: ax.get_vector_field(lambda p: p, x_range=(0, np.inf, 1)),
        "x_range",
        index=1,
    )


@pytest.mark.parametrize(
    "options,parameter,kind",
    [
        ({"dt": np.inf}, "dt", ValueError),
        ({"n_repeats": 1.5}, "n_repeats", TypeError),
        ({"max_anchors_per_line": 1}, "max_anchors_per_line", ValueError),
    ],
)
def test_ff2_stream_parameters(options, parameter, kind):
    ax = axes()
    rejects(lambda: ax.get_stream_lines(lambda p: p, **options), parameter, kind=kind)


@pytest.mark.parametrize("dimension", [2, 3])
@pytest.mark.parametrize("bad", [np.nan, np.inf])
def test_ff3_invalid_field_warns_per_data_change(dimension, bad):
    ax = axes() if dimension == 2 else three()
    options: dict[str, Any] = dict(x_range=(0, 1, 1), y_range=(0, 1, 1))
    if dimension == 3:
        options["z_range"] = (0, 1, 1)
    with counted() as caught:
        field = ax.get_vector_field(lambda p: np.full(3, bad), **options)
        touch(field)
        touch(field)
    assert library(caught) == 1
    for arrow in field:
        points = arrow.get_all_points()
        assert not len(points) or np.ptp(points, axis=0).max() < 1e-8
    with counted() as caught:
        field.set_color(RED)
        touch(field)
    assert library(caught) == 0
    with counted() as caught:
        ax.x.range = (-1, 4)
        touch(field)
    assert library(caught) == 1


def test_ff4_empty_implicit_contour():
    ax = axes()
    with counted() as caught:
        curve = ax.plot_implicit_curve(lambda x, y: 1.0, min_depth=1, max_quads=4)
        empty(curve)
    assert library(caught) == 1


def test_ff5_flow_speed_and_vector_dimension():
    ax = axes()
    field = ax.get_vector_field(
        lambda p: np.array([1, 0, 0]), x_range=(0, 1, 1), y_range=(0, 1, 1)
    )
    rejects(lambda: mp.Flow(field, Dot(), speed=np.inf), "speed")
    rejects(lambda: ax.get_vector([1]), "coords")


@pytest.mark.parametrize("constructor", [mp.PolarAxes, mp.PolarPlane])
@pytest.mark.parametrize("parameter", ["size", "azimuth_offset"])
def test_po1_nonfinite_configuration(constructor, parameter):
    rejects(lambda: polar(constructor, **{parameter: np.inf}), parameter)


@pytest.mark.parametrize("constructor", [mp.PolarAxes, mp.PolarPlane])
@pytest.mark.parametrize("bad", [np.nan, np.inf])
def test_po2_nonfinite_conversion(constructor, bad):
    ax: Any = polar(constructor)
    with pytest.raises(ValueError):
        ax.polar_to_point(1, bad)
    with pytest.raises(ValueError):
        ax.point_to_polar([bad, 0, 0])


def test_po3_invalid_radial_source_is_empty_once():
    ax: Any = polar(r_range=(0, 3))
    with counted() as caught:
        graph = ax.plot_polar_graph(lambda theta: np.nan, theta_range=(0, 1))
        empty(graph)
        touch(graph)
    assert library(caught) == 1
    with counted() as caught:
        ax.set_r_range((0, 4))
        touch(graph)
    assert library(caught) == 1


def test_po4_radial_domain_exception():
    # 22 PX-2 deliberately refuses rather than normalising this constructor.
    rejects(lambda: polar(r_range=(0, 3), r_scale="log"), "r_range")


@pytest.mark.parametrize("parameter", ["z_range", "z_length"])
def test_td1_nonfinite_system_configuration(parameter):
    rejects(
        lambda: three(**{parameter: (0, np.inf) if parameter == "z_range" else np.inf}),
        parameter,
    )


@pytest.mark.parametrize("triangles,index", [([[0, 1, 3]], 0), ([[0, 1, 1]], 0)])
def test_td2_invalid_triangle_cell(triangles, index):
    ax = three()
    rejects(
        lambda: ax.plot_trisurf([0, 1, 0], [0, 0, 1], [1, 1, 1], triangles=triangles),
        "triangles",
        index=index,
    )


@pytest.mark.parametrize("method", ["c2p", "cy2pt", "sp2pt"])
@pytest.mark.parametrize("bad", [np.nan, np.inf])
def test_td3_conversion_raises(method, bad):
    ax = three()
    with pytest.raises(ValueError):
        getattr(ax, method)(1, 1, bad)


@pytest.mark.parametrize("kind", ["height", "parametric", "triangles"])
def test_td4_surface_holes_warn_once(kind):
    ax = three()
    with counted() as caught:
        if kind == "height":
            surface = ax.plot_surface(
                lambda u, v: np.nan if u == 0 and v == 0 else 1,
                (0, 2),
                (0, 1),
                resolution=(2, 1),
            )
        elif kind == "parametric":
            surface = ax.plot_parametric_surface(
                lambda u, v: [u, v, np.nan if u == 0 and v == 0 else 1],
                (0, 2),
                (0, 1),
                resolution=(2, 1),
            )
        else:
            surface = ax.plot_trisurf(
                [0, 1, 0, 2, 3, 2],
                [0, 0, 1, 0, 0, 1],
                [np.nan, 1, 1, 1, 1, 1],
                triangles=[[0, 1, 2], [3, 4, 5]],
            )
        touch(surface)
        touch(surface)
    assert library(caught) == 1
    faces = list(surface.faces)
    assert len(faces) == 2
    assert not faces[0].has_points()
    assert faces[1].has_points()
    with counted() as caught:
        surface.set_color(RED)
        touch(surface)
    assert library(caught) == 0
    with counted() as caught:
        ax.x.range = (-1, 4)
        touch(surface)
    assert library(caught) == 1


def test_td5_surface_parameters():
    ax = three()
    rejects(
        lambda: ax.plot_surface(lambda u, v: 1, (0, np.inf), (0, 1), resolution=1),
        "u_range",
        index=1,
    )
    rejects(
        lambda: ax.plot_wireframe(lambda u, v: u + v, (0, 1), (0, 1), resolution=0),
        "resolution",
    )
    surface = ax.plot_surface(lambda u, v: u + v, (0, 1), (0, 1), resolution=1)
    rejects(lambda: axes().plot_slice(surface, x=np.inf), "x")
    rejects(lambda: ax.slice_view(surface, x=np.nan), "x")
    rejects(lambda: ax.plane(point=[0, np.nan, 0], normal=[1, 0, 0]), "point", index=1)


def test_td6_configured_domain_exception():
    # 24 TF-4 explicitly refuses a 3D range outside its scale's domain.
    rejects(lambda: three(z_range=(-1, 10), z_scale="log"), "z_range")


@pytest.mark.parametrize("method", ["bar", "barh"])
def test_ba1_lengths_and_dimensions(method):
    ax = axes()
    rejects(
        lambda: getattr(ax, method)([0, 1, 2], [1, 2]),
        "height" if method == "bar" else "width",
        lengths=(3, 2),
    )
    rejects(
        lambda: getattr(ax, method)([[0, 1]], [[1, 2]]), "x" if method == "bar" else "y"
    )


def test_ba2_group_and_label_parameters():
    ax = axes()
    rejects(lambda: ax.grouped_bar([[1, 2]], group_spacing=np.inf), "group_spacing")
    bars = ax.bar([0, 1], [1, 2])
    rejects(lambda: ax.bar_label(bars, padding=np.inf), "padding")


@pytest.mark.parametrize("method", ["bar", "barh", "bar3d"])
@pytest.mark.parametrize("bad", [np.nan, np.inf])
def test_ba3_invalid_bar_sample(method, bad):
    ax = three() if method == "bar3d" else axes()
    with counted() as caught:
        if method == "bar3d":
            bars = ax.bar3d([0, 2], [0, 0], [0, 0], [0.5, 0.5], [0.5, 0.5], [1, bad])
        else:
            bars = getattr(ax, method)([0, 2], [1, bad])
        touch(bars)
    assert library(caught) == 1
    parts = bars.bars if method == "bar3d" else bars  # BR-1: bar i is .bars[i]
    assert parts[0].get_all_points().size
    empty(parts[1])
    with counted() as caught:
        bars.set_color(RED)
        touch(bars)
    assert library(caught) == 0
    with counted() as caught:
        ax.x.range = (-1, 4)
        touch(bars)
    assert library(caught) == 1


@pytest.mark.parametrize("method", ["bar", "barh", "bar3d"])
def test_ba4_empty_bars(method):
    ax = three() if method == "bar3d" else axes()
    with counted() as caught:
        bars = getattr(ax, method)(*([[]] * (6 if method == "bar3d" else 2)))
        empty(bars)
    assert library(caught) == 1


def test_ba5_log_baseline_exception():
    ax = axes(y_range=(0.1, 10), y_scale="log")
    with counted() as caught:
        bars = ax.bar([1], [2], bottom=0)
        points = np.asarray(bars[0].get_anchors())
    assert library(caught) == 0
    np.testing.assert_allclose(points[:, 1].min(), ax.c2p(1, 0.1)[1])


@pytest.mark.parametrize("method", ["hist", "hist2d", "hist3d"])
@pytest.mark.parametrize("bins", [0, -1])
def test_hi1_nonpositive_bins(method, bins):
    ax = three() if method == "hist3d" else axes()
    args = ([0, 1],) if method == "hist" else ([0, 1], [0, 1])
    rejects(lambda: getattr(ax, method)(*args, bins=bins), "bins")


@pytest.mark.parametrize("method", ["step", "stairs", "stackplot"])
def test_hi2_mismatched_arrays(method):
    ax = axes()
    if method == "stairs":
        rejects(lambda: ax.stairs([1, 2], [0, 1]), "edges", lengths=(2, 3))
    else:
        rejects(
            lambda: getattr(ax, method)([0, 1, 2], [1, 2]),
            "y" if method == "step" else "ys",
            lengths=(3, 2),
        )


@pytest.mark.parametrize("bad", [np.nan, np.inf])
def test_hi3_numpy_autorange_exception(bad):
    ax = axes()
    # NumPy's _get_outer_edges rejects rather than silently choosing a range.
    rejects(lambda: ax.hist([0.25, bad]), "x", index=1)
    with counted() as caught:
        hist = ax.hist([0.25, bad, 1.25], bins=[0, 1, 2])
    np.testing.assert_array_equal(hist.counts, [1, 1])
    assert library(caught) == 1


@pytest.mark.parametrize("method", ["step", "stairs", "stackplot"])
def test_hi4_nonfinite_source_holes(method):
    ax = axes()
    with counted() as caught:
        if method == "stairs":
            artist = ax.stairs([1, np.nan, 1], [0, 1, 2, 3])
        else:
            artist = getattr(ax, method)([0, 1, 2, 3], [1, 1, np.nan, 1])
        touch(artist)
    assert library(caught) == 1
    with counted() as caught:
        artist.set_color(RED)
        touch(artist)
    assert library(caught) == 0


@pytest.mark.parametrize("method", ["step", "stairs", "stackplot"])
def test_hi5_empty_input(method):
    ax = axes()
    with counted() as caught:
        artist = ax.stairs([]) if method == "stairs" else getattr(ax, method)([], [])
        empty(artist)
    assert library(caught) == 1


def test_da1_wrong_artist_type():
    rejects(lambda: mp.AppendData(cast(Any, Dot()), [0], [1]), "artist", kind=TypeError)


def test_da2_append_lengths_and_dimensions():
    ax = axes()
    line = ax.line([0, 1], [1, 2])
    rejects(lambda: mp.AppendData(line, [2, 3, 4], [3, 4]), "y", lengths=(3, 2))
    rejects(lambda: mp.AppendData(line, np.ones((2, 2, 2))), "x")


@pytest.mark.parametrize("scatter", [False, True])
def test_da3_append_invalid_sample_keeps_gap(scatter):
    ax = axes()
    artist = ax.scatter([0], [1]) if scatter else ax.line([0], [1])
    with counted() as caught:
        animation = mp.AppendData(artist, [1, 2], [np.nan, 2])
        animation.begin()
        animation.interpolate(1)
        animation.finish()
        touch(artist)
    assert library(caught) == 1
    if scatter:
        assert artist[1].get_fill_opacity() == 0
    else:
        for path in artist.get_subpaths():
            xs = ax.p2c(path)[:, 0]
            assert not (xs.min() < 1 < xs.max())


def test_da4_empty_append_noop():
    ax = axes()
    artist = ax.line([0, 1], [1, 2])
    before = artist.points.copy()
    with counted() as caught:
        animation = mp.AppendData(artist, [], [])
        animation.begin()
        animation.interpolate(1)
        animation.finish()
    assert library(caught) == 0
    np.testing.assert_allclose(artist.points, before)


def test_da5_native_data_animation_wrong_shape():
    ax = axes()
    artist = ax.bar([0, 1], [1, 2])
    before = artist.get_all_points().copy()
    rejects(
        lambda: artist.animate.set_data(x=[0, 1, 2], height=[1, 2]),
        "height",
        lengths=(3, 2),
    )
    np.testing.assert_allclose(artist.get_all_points(), before)


def test_ak1_date_first_invalid_index():
    rejects(
        lambda: mp.date2num(
            np.array(["2026-01-01", "NaT", "NaT"], dtype="datetime64[D]")
        ),
        "d",
        index=1,
    )
    rejects(
        lambda: mp.date2num([date(2026, 1, 1), object()]), "d", kind=TypeError, index=1
    )


@pytest.mark.parametrize(
    "options,parameter",
    [
        ({"xmax": 0}, "xmax"),
        ({"xmax": np.inf}, "xmax"),
        ({"decimals": -1}, "decimals"),
    ],
)
def test_ak2_percent_configuration(options, parameter):
    rejects(lambda: mp.PercentFormatter(**options), parameter)


def test_ak3_logit_conversion_and_configured_range():
    ax = axes(x_range=(0.1, 0.9), x_scale="logit")
    for value in (0, 1, -1, np.nan):
        with pytest.raises(ValueError):
            ax.c2p(value, 0)
    # F-311 applies to configurations: a wholly disjoint range cannot be repaired.
    rejects(lambda: axes(x_range=(2, 3), x_scale="logit"), "x_range")


def test_ak4_broken_scale_first_bad_pair():
    rejects(lambda: mp.BrokenScale([(0, 1), (2, np.inf)]), "breaks", index=1)


def test_ak5_empty_formatters_and_date_locator():
    for formatter in (
        mp.PercentFormatter(),
        mp.LogitFormatter(),
        mp.ConciseDateFormatter(),
    ):
        assert list(formatter.format_ticks(np.array([])).text) == []
    locator = mp.AutoDateLocator()
    with pytest.raises(ValueError):
        locator.values(np.nan, 1, mp.LinearScale(), 5)


@pytest.mark.parametrize("method", ["imshow", "pcolormesh"])
def test_hm1_wrong_matrix_dimension(method):
    ax = axes()
    rejects(
        lambda: getattr(ax, method)(np.ones((2, 2, 2))),
        "Z" if method == "imshow" else "C",
    )


def test_hm2_mesh_and_hexbin_lengths():
    ax = axes()
    rejects(lambda: ax.pcolormesh([0, 1], [0, 1], np.ones((2, 3))), "C")
    rejects(lambda: ax.hexbin([0, 1, 2], [0, 1]), "y", lengths=(3, 2))


def test_hm3_colormap_and_colorbar_parameters():
    ax = axes()
    rejects(
        lambda: mp.Colormap(["red", "green", "blue"], [0, np.nan, 1]),
        "positions",
        index=1,
    )
    rejects(lambda: ax.colorbar(colorscale="viridis", vmin=0, vmax=np.inf), "vmax")


@pytest.mark.parametrize("method", ["imshow", "pcolormesh"])
@pytest.mark.parametrize("bad", [np.nan, np.inf])
def test_hm4_bad_cell_and_warning_changes(method, bad):
    ax = axes()
    with counted() as caught:
        image = getattr(ax, method)([[1, bad], [2, 3]])
        touch(image)
        touch(image)
    assert library(caught) == 1
    empty(image.cells.at((0, 1)))
    assert image.cells.at((1, 1)).has_points()
    with counted() as caught:
        image.set_color(RED)
        touch(image)
    assert library(caught) == 0
    with counted() as caught:
        image.set_data([[1, bad], [3, 4]])
        touch(image)
    assert library(caught) == 1


@pytest.mark.parametrize("method", ["contour", "contourf"])
def test_hm5_invalid_grid_cell_is_not_contoured(method):
    ax = axes()
    with counted() as caught:
        contour = getattr(ax, method)(
            [0, 1], [0, 1], [[-1, 1], [np.nan, 1]], levels=[0, 0.5]
        )
        empty(contour)
    assert library(caught) == 1


@pytest.mark.parametrize("method", ["imshow", "pcolormesh", "hexbin"])
def test_hm6_empty_input(method):
    ax = axes()
    with counted() as caught:
        artist = (
            ax.hexbin([], [], extent=(0, 1, 0, 1))
            if method == "hexbin"
            else getattr(ax, method)(np.empty((0, 0)))
        )
        empty(artist)
    assert library(caught) == 1


@pytest.mark.parametrize("method", ["boxplot", "violinplot"])
def test_st1_layout_width_and_dimensions(method):
    ax = axes()
    rejects(
        lambda: getattr(ax, method)([[1, 2], [2, 3]], positions=[1, 2, 3]),
        "positions",
        lengths=(2, 3),
    )
    rejects(lambda: getattr(ax, method)([1, 2], widths=np.inf), "widths")
    rejects(
        lambda: getattr(ax, method)(np.ones((2, 2, 2))),
        "x" if method == "boxplot" else "dataset",
    )


def test_st2_negative_wedge_first_index():
    # 38 PI-1 owns rejection; add parameter and first-index diagnostics.
    rejects(lambda: mp.PieChart([1, -0.1, -0.2]), "x", index=1)


@pytest.mark.parametrize("method", ["boxplot", "violinplot", "pie"])
@pytest.mark.parametrize("bad", [np.nan, np.inf])
def test_st3_invalid_sample_is_whole_box_or_wedge(method, bad):
    ax = axes()
    with counted() as caught:
        if method == "pie":
            artist = mp.PieChart([1, bad, 2])
            parts = artist.wedges
        elif method == "boxplot":
            artist = ax.boxplot([[1, 2, 3], [1, bad, 3]])
            parts = artist.boxes
        else:
            artist = ax.violinplot([[1, 2, 3], [1, bad, 3]], points=5)
            parts = artist.bodies
        touch(artist)
    assert library(caught) == 1
    assert parts[0].has_points()
    empty(parts[1])
    with counted() as caught:
        artist.set_color(RED)
        touch(artist)
    assert library(caught) == 0
    with counted() as caught:
        if method == "pie":
            artist.set_data([2, bad, 1])
        else:
            ax.x.range = (-1, 4)
        touch(artist)
    assert library(caught) == 1


@pytest.mark.parametrize("method", ["boxplot", "violinplot", "pie"])
def test_st4_empty_statistics(method):
    ax = axes()
    with counted() as caught:
        artist = mp.PieChart([]) if method == "pie" else getattr(ax, method)([])
        empty(artist)
    assert library(caught) == 1


def test_vo1_wrong_volume_dimensions():
    ax = three()
    rejects(lambda: ax.voxels(np.ones((2, 2), bool)), "filled")
    rejects(lambda: ax.plot_isosurface(np.ones((2, 2)), 0.5), "F")


def test_vo2_nonfinite_level_and_corner_index():
    ax = three()
    rejects(lambda: ax.plot_isosurface(np.ones((2, 2, 2)), np.inf), "level")
    x, y, z = np.indices((2, 2, 2), dtype=float)
    x[1, 0, 0] = np.nan
    rejects(lambda: ax.voxels(x, y, z, np.ones((1, 1, 1), bool)), "x", index=1)


def test_vo3_invalid_voxel_value_drops_whole_sample():
    ax = three()
    with counted() as caught:
        voxels = ax.voxels(
            np.ones((2, 1, 1), bool), c=np.array([1, np.nan]).reshape(2, 1, 1)
        )
        touch(voxels)
    assert library(caught) == 1
    empty(voxels.at((1, 0, 0)))
    # Removing the invalid neighbour exposes all six faces of voxel zero.
    assert len(voxels.at((0, 0, 0))) == 6
    expected = ax.c2p(np.array([[0, 0, 0], [1, 1, 1]]))
    points = voxels.at((0, 0, 0)).get_all_points()
    np.testing.assert_allclose(points.min(axis=0), expected.min(axis=0))
    np.testing.assert_allclose(points.max(axis=0), expected.max(axis=0))


def test_vo4_empty_voxels_warn_once():
    ax = three()
    with counted() as caught:
        voxels = ax.voxels(np.zeros((1, 1, 1), bool))
        empty(voxels)
    assert library(caught) == 1


def test_vo5_isosurface_misses_level_exception():
    ax = three()
    # 39 IS-2: a valid sampled field need not cross the requested level.
    with counted() as caught:
        surface = ax.plot_isosurface(np.zeros((2, 2, 2)), 2)
        empty(surface)
    assert library(caught) == 0


def animation_target(name: str) -> Any:
    ax = axes()
    solid = three()
    if name in ("BuildAxes", "DrawAxes"):
        return ax
    if name == "HighlightTick":
        return ax.x
    if name in ("GrowBars", "ShrinkBars", "SortBars", "HighlightBar"):
        return ax.bar([0, 1], [1, 2])
    if name in ("ShowPoints",):
        return ax.scatter([0, 1], [1, 2])
    if name in ("TraceCurve",):
        return ax.line([0, 1], [1, 2])
    if name == "ExtendReference":
        return ax.axhline(1)
    if name in ("GrowRegion", "SweepRegion", "SweepSpan"):
        return ax.axhspan(1, 2)
    if name in ("GrowRiemann", "RefineRiemann"):
        graph = ax.plot(lambda x: x, x_range=(0, 2))
        result = ax.get_riemann_rectangles(graph, x_range=(0, 2), dx=1)
        result.__dict__["_task23_graph"] = graph
        return result
    if name == "GrowErrorBars":
        return ax.errorbar([0, 1], [1, 2], yerr=0.1)
    if name == "RevealAnnotation":
        return ax.annotate(Dot(), (0, 1))
    if name == "RevealCrosshair":
        return ax.crosshair(0, 1, readout=False)
    if name == "RevealLegend":
        return mp.Legend()
    if name == "FillColorbar":
        return ax.colorbar(
            colorscale="viridis", vmin=0, vmax=1, axis_config={"include_numbers": False}
        )
    if name in ("OpenInset", "CloseInset"):
        return ax.inset((0.5, 0.5, 0.4, 0.4), (0, 1), (0, 1))
    if name == "GrowStack":
        return ax.stackplot([0, 1], [1, 2])
    if name == "RevealCells":
        return ax.imshow([[0, 1], [2, 3]])
    if name == "RevealContours":
        return ax.contour([0, 1], [0, 1], [[0, 1], [1, 2]], levels=[0.5, 1.5])
    if name in ("SweepPie", "ExplodePie"):
        return mp.PieChart([1, 2])
    if name == "GrowBoxPlot":
        return ax.boxplot([1, 2, 3])
    if name == "UnfoldViolin":
        return ax.violinplot([1, 2, 3], points=5)
    if name == "GrowField":
        return ax.get_vector_field(
            lambda p: np.array([1, 0, 0]), x_range=(0, 1, 1), y_range=(0, 1, 1)
        )
    if name == "GrowStems":
        return solid.stem([0, 1], [0, 1], [1, 2])
    if name == "RevealWireframe":
        return solid.plot_wireframe(lambda u, v: u + v, (0, 1), (0, 1), resolution=1)
    if name == "RevealWaterfall":
        return solid.waterfall([0, 1], [[1, 2]], positions=[0])
    if name == "SweepPolar":
        return polar(r_range=(0, 2))
    if name == "StackVoxels":
        return solid.voxels(np.ones((1, 1, 1), bool))
    if name == "RebinHistogram":
        return ax.hist([0.25, 1.25], bins=[0, 1, 2])
    if name == "SweepIsovalue":
        return solid.plot_isosurface(np.indices((2, 2, 2))[0], 0.5)
    if name == "Flow":
        return animation_target("GrowField")
    if name in ("GrowSurface", "ShrinkSurface", "SweepSurface", "SweepSlice"):
        surface = solid.plot_surface(lambda u, v: u + v, (0, 1), (0, 1), resolution=1)
        return solid.slice_view(surface, x=0.5) if name == "SweepSlice" else surface
    raise AssertionError(name)


LAG_CLASSES = [
    "BuildAxes",
    "GrowBars",
    "ShrinkBars",
    "ShowPoints",
    "GrowStack",
    "GrowRiemann",
    "GrowErrorBars",
    "RevealAnnotation",
    "RevealCrosshair",
    "RevealLegend",
    "FillColorbar",
    "OpenInset",
    "CloseInset",
    "RevealCells",
    "RevealContours",
    "SweepPie",
    "GrowBoxPlot",
    "UnfoldViolin",
    "GrowField",
    "GrowStems",
    "RevealWireframe",
    "RevealWaterfall",
    "SweepPolar",
    "StackVoxels",
    "RefineRiemann",
]


@pytest.mark.parametrize("name", LAG_CLASSES)
@pytest.mark.parametrize("bad", [-0.1, np.nan, np.inf])
def test_an1_invalid_lag_before_mutation(name, bad):
    target = animation_target(name)
    before = [m.points.copy() for m in target.get_family()]
    args = (0.5,) if name == "RefineRiemann" else ()
    rejects(lambda: getattr(mp, name)(target, *args, lag_ratio=bad), "lag_ratio")
    for member, original in zip(target.get_family(), before, strict=True):
        np.testing.assert_array_equal(member.points, original)


@pytest.mark.parametrize(
    "name",
    [
        "GrowBars",
        "ShrinkBars",
        "ShowPoints",
        "RevealCells",
        "RevealContours",
        "GrowField",
        "RefineRiemann",
    ],
)
def test_an2_order_wrong_type(name):
    target = animation_target(name)
    args = (0.5,) if name == "RefineRiemann" else ()
    rejects(lambda: getattr(mp, name)(target, *args, order=42), "order", kind=TypeError)


@pytest.mark.parametrize(
    "name", ["SweepRegion", "SweepSpan", "SweepSurface", "StackVoxels"]
)
def test_an3_direction_wrong_type(name):
    target = animation_target(name)
    rejects(
        lambda: getattr(mp, name)(target, direction="left"), "direction", kind=TypeError
    )


def test_an4_unknown_stage_index_and_key():
    ax = axes()
    rejects(lambda: mp.BuildAxes(ax, stages=["lines", "missing"]), "stage", index=1)
    bars = ax.bar([0, 1], [1, 2])
    rejects(lambda: mp.HighlightBar(bars, "missing"), "key")
    rejects(lambda: mp.SortBars(bars, key=cast(Any, "height")), "key", kind=TypeError)
    # 34 AX-2 explicitly keeps KeyError for a missing tick.
    with pytest.raises(KeyError):
        mp.HighlightTick(ax.x, 0.123)


@pytest.mark.parametrize("name", ["GrowSurface", "ShrinkSurface"])
def test_an5_wrong_growth_offset_type(name):
    target = animation_target(name)
    rejects(
        lambda: getattr(mp, name)(target, offset=object()), "offset", kind=TypeError
    )


def test_an6_nonfinite_stage_options():
    errors = animation_target("GrowErrorBars")
    rejects(lambda: mp.GrowErrorBars(errors, cap_lag=np.inf), "cap_lag")
    pie = animation_target("ExplodePie")
    rejects(lambda: mp.ExplodePie(pie, amount=np.inf), "amount")
    polar = animation_target("SweepPolar")
    rejects(lambda: mp.SweepPolar(polar, start_angle=np.inf), "start_angle")


def test_an7_empty_reveal_is_safe():
    legend = mp.Legend()
    scene = Scene()
    animation = mp.RevealLegend(legend)
    with counted() as caught:
        animation._setup_scene(scene)
        animation.begin()
        animation.interpolate(0.5)
        animation.finish()
        animation.clean_up_from_scene(scene)
    assert library(caught) == 0
    empty(legend)


@pytest.mark.parametrize(
    "family",
    [
        "helper",
        "errorbar",
        "field",
        "bar",
        "step",
        "heatmap",
        "box",
        "voxel",
        "surface",
    ],
)
def test_hl9_domain_samples_follow_surface_rule(family):
    """HL-9 cross-references the domain column for each participating family."""
    ax = (
        three(z_range=(0.1, 8), z_scale="log")
        if family in ("voxel", "surface")
        else axes(y_range=(0.1, 8), y_scale="log")
    )
    with counted() as caught:
        if family == "helper":
            artist = ax.fill_between([0, 1, 2, 3], [1, 1, -1, 1], y2=0.5)
        elif family == "errorbar":
            artist = ax.errorbar([0, 1], [1, -1], yerr=0.1)
        elif family == "field":
            artist = ax.get_vector_field(
                lambda p: np.array([0, 1, 0]), x_range=(0, 1, 1), y_range=(-1, 1, 1)
            )
        elif family == "bar":
            artist = ax.bar([0, 1], [1, -1], bottom=[0.5, -2])
        elif family == "step":
            artist = ax.step([0, 1, 2], [1, -1, 2])
        elif family == "heatmap":
            artist = ax.pcolormesh([0, 1, 2], [-1, 1, 2], [[1, 2], [3, 4]])
        elif family == "box":
            artist = ax.boxplot([[1, 2, 3], [-3, -2, -1]])
        elif family == "voxel":
            artist = ax.voxels(np.ones((1, 1, 1), bool))
        else:
            artist = ax.plot_surface(lambda u, v: -1, (0, 1), (0, 1), resolution=1)
        touch(artist)
    assert library(caught) == 1
    if family in ("voxel", "surface"):
        empty(artist)
    elif family == "bar":
        empty(artist[1])
    elif family == "heatmap":
        empty(artist.cells.at((0, 0)))
        assert artist.cells.at((1, 0)).has_points()
    elif family == "box":
        empty(artist.boxes[1])
    elif family == "helper":
        for path in artist.get_subpaths():
            assert ax.p2c(path)[:, 0].max() <= 1 + 1e-8
    elif family == "step":
        for path in artist.get_subpaths():
            values = ax.p2c(path)
            assert not (values[:, 0].min() < 1 < values[:, 0].max())
    elif family == "errorbar":
        assert artist.markers[1].get_fill_opacity() == 0


@pytest.mark.parametrize(
    "family", ["helper", "errorbar", "field", "bar", "hist", "heatmap", "box", "data"]
)
def test_tw6_configured_range_normalised_for_new_artists(family):
    """TW-6 supplies the shared F-311 column, including twins and insets."""
    with counted() as caught:
        root = axes()
        ax = root.twinx(y_range=(-1, 10), y_scale="log")
        if family == "helper":
            artist = ax.fill_between([0, 1], [1, 2], y2=0.5)
        elif family == "errorbar":
            artist = ax.errorbar([0, 1], [1, 2], yerr=0.1)
        elif family == "field":
            artist = ax.get_vector_field(
                lambda p: np.array([1, 0, 0]), x_range=(0, 1, 1), y_range=(1, 2, 1)
            )
        elif family == "bar":
            artist = ax.bar([0, 1], [1, 2], bottom=0.5)
        elif family == "hist":
            artist = ax.hist([0.2, 0.4, 1.2], bins=[0, 1, 2], bottom=0.5)
        elif family == "heatmap":
            artist = ax.imshow([[1, 2]], extent=(0, 2, 1, 2))
        elif family == "box":
            artist = ax.boxplot([1, 2, 3])
        else:
            artist = ax.line([0, 1], [1, 2])
            animation = mp.AppendData(artist, [2], [3], autoscale=True)
            animation.begin()
            animation.interpolate(1)
            animation.finish()
        touch(artist)
    assert library(caught) == 0
    assert ax.y.range.value[0] > 0


@pytest.mark.parametrize("parameter", ["width", "height", "bin_count"])
def test_ba6_nonfinite_geometry_controls(parameter):
    ax = axes()
    if parameter == "width":
        rejects(lambda: ax.bar([0], [1], width=np.inf), "width")
    elif parameter == "height":
        rejects(lambda: ax.barh([0], [1], height=np.inf), "height")
    else:
        rejects(lambda: ax.hist([0, 1], bins=np.inf), "bins")


def test_ff6_stream_nonfinite_source_stops_and_warns():
    ax = axes()
    with counted() as caught:
        streams = ax.get_stream_lines(
            lambda p: np.full(3, np.nan),
            x_range=(0, 1, 1),
            y_range=(0, 1, 1),
            noise_factor=0,
            dt=0.1,
            virtual_time=0.2,
        )
        touch(streams)
    assert library(caught) == 1
    for line in streams.stream_lines:
        points = line.get_all_points()
        assert not len(points) or np.ptp(points, axis=0).max() < 1e-8


def test_hm7_explicit_mask_hides_finite_cell_without_warning():
    ax = axes()
    values = np.ma.array([[1, 2], [3, 4]], mask=[[False, True], [False, False]])
    with counted() as caught:
        image = ax.imshow(values)
        empty(image.cells.at((0, 1)))
        assert image.cells.at((1, 1)).has_points()
    assert library(caught) == 0


def test_vo6_nonfinite_isosurface_corner_drops_cell():
    ax = three()
    values = np.indices((2, 2, 2))[0].astype(float)
    values[0, 0, 0] = np.nan
    with counted() as caught:
        surface = ax.plot_isosurface(values, 0.5)
        empty(surface)
    assert library(caught) == 1


def test_po5_radial_domain_sample():
    ax = polar(r_range=(0.1, 3), r_scale="log")
    with counted() as caught:
        points = ax.scatter([0, 1], [0.5, 0.5])
        touch(points)
    assert library(caught) == 1
    assert points[0].get_fill_opacity() == 0
    assert points[1].get_fill_opacity() > 0


def test_td7_triangle_lengths():
    ax = three()
    rejects(
        lambda: ax.plot_trisurf([0, 1, 2], [0, 1], [1, 2, 3], triangles=[[0, 1, 2]]),
        "y",
        lengths=(3, 2),
    )


def test_td8_singular_inverse():
    ax = three()
    ax.scale(0)
    with pytest.raises(ValueError, match="singular"):
        ax.p2c([0, 0, 0])


def test_td9_empty_triangle_input():
    ax = three()
    with counted() as caught:
        surface = ax.plot_trisurf([], [], [], triangles=np.empty((0, 3), int))
        empty(surface)
    assert library(caught) == 1
