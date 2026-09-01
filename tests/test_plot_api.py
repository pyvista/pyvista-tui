from __future__ import annotations

import numpy as np
import pytest
import pyvista as pv

from pyvista_tui.renderer import (
    OffScreenRenderer,
    apply_rainbow,
    build_mesh_kwargs,
    prepare_mesh,
    resolve_mesh,
)


def _n_colors(frame):
    """Return the number of distinct colors in a rendered frame."""
    return len(frame.convert('RGB').getcolors(maxcolors=1_000_000))


# --- build_mesh_kwargs ---


def test_build_mesh_kwargs_defaults():
    kwargs = build_mesh_kwargs()
    assert kwargs == {'show_scalar_bar': False}


def test_build_mesh_kwargs_scalars():
    kwargs = build_mesh_kwargs(scalars='temperature')
    assert kwargs['scalars'] == 'temperature'


def test_build_mesh_kwargs_none_values_excluded():
    kwargs = build_mesh_kwargs(color=None, cmap=None)
    assert 'color' not in kwargs
    assert 'cmap' not in kwargs


def test_build_mesh_kwargs_bool_flags():
    kwargs = build_mesh_kwargs(
        show_edges=True,
        smooth_shading=True,
        log_scale=True,
    )
    assert kwargs['show_edges'] is True
    assert kwargs['smooth_shading'] is True
    assert kwargs['log_scale'] is True


def test_build_mesh_kwargs_bool_flags_false():
    kwargs = build_mesh_kwargs(show_edges=False)
    assert 'show_edges' not in kwargs


def test_build_mesh_kwargs_numeric_values():
    kwargs = build_mesh_kwargs(
        opacity=0.5,
        point_size=10.0,
        line_width=2.0,
    )
    assert kwargs['opacity'] == 0.5
    assert kwargs['point_size'] == 10.0
    assert kwargs['line_width'] == 2.0


def test_build_mesh_kwargs_forwards_unknown_kwargs():
    kwargs = build_mesh_kwargs(rgb=True, ambient=0.3)
    assert kwargs['rgb'] is True
    assert kwargs['ambient'] == 0.3


def test_build_mesh_kwargs_unknown_kwargs_override_defaults():
    kwargs = build_mesh_kwargs(show_scalar_bar=True)
    assert kwargs['show_scalar_bar'] is True


# --- apply_rainbow ---


def test_apply_rainbow_sets_scalars_and_cmap():
    kwargs: dict[str, object] = {}
    apply_rainbow(kwargs)
    assert kwargs['scalars'] == '_rainbow'
    assert kwargs['cmap'] == 'gist_rainbow'


def test_apply_rainbow_returns_same_dict():
    kwargs: dict[str, object] = {}
    result = apply_rainbow(kwargs)
    assert result is kwargs


# --- resolve_mesh ---


def test_resolve_mesh_from_path(tmp_path):
    path = str(tmp_path / 'sphere.vtk')
    pv.Sphere().save(path)
    mesh = resolve_mesh(path)
    assert mesh.n_points > 0


def test_resolve_mesh_from_object():
    sphere = pv.Sphere()
    mesh = resolve_mesh(mesh=sphere)
    assert mesh is sphere


def test_resolve_mesh_center():
    sphere = pv.Sphere(center=(10, 20, 30))
    mesh = resolve_mesh(mesh=sphere, center=True)
    assert abs(mesh.center[0]) < 1e-6
    assert abs(mesh.center[1]) < 1e-6
    assert abs(mesh.center[2]) < 1e-6


def test_resolve_mesh_rainbow():
    sphere = pv.Sphere()
    mesh = resolve_mesh(mesh=sphere, rainbow=True)
    assert '_rainbow' in mesh.point_data


# --- Renderer mark_dirty ---


def test_renderer_mark_dirty():
    mesh = pv.Sphere()
    with OffScreenRenderer(mesh, window_size=(100, 100)) as r:
        r.render_frame()
        assert not r.is_dirty
        r.mark_dirty()
        assert r.is_dirty


# --- Renderer edges ---


def test_renderer_toggle_edges():
    mesh = pv.Sphere()
    with OffScreenRenderer(mesh, window_size=(100, 100)) as r:
        assert not r.show_edges
        r.toggle_edges()
        assert r.show_edges
        assert r.is_dirty
        r.toggle_edges()
        assert not r.show_edges


# --- Renderer mesh_info ---


def test_renderer_mesh_info_format():
    mesh = pv.Sphere()
    with OffScreenRenderer(mesh, window_size=(100, 100)) as r:
        info = r.mesh_info()
        assert 'pts:' in info
        assert 'cells:' in info
        assert 'arrays:' in info


# --- Renderer rainbow ---


def test_renderer_rainbow_with_resolve_mesh():
    mesh_kwargs: dict[str, object] = {}
    apply_rainbow(mesh_kwargs)
    prepared = resolve_mesh(mesh=pv.Sphere(), rainbow=True)
    with OffScreenRenderer(
        prepared,
        window_size=(100, 100),
        wireframe=True,
        mesh_kwargs=mesh_kwargs,
    ) as r:
        frame = r.render_frame()
        assert frame.size == (100, 100)


def test_renderer_rainbow_scalars_without_array_raises():
    mesh = pv.Sphere()
    with pytest.raises(ValueError, match='_rainbow'):
        OffScreenRenderer(
            mesh,
            window_size=(100, 100),
            mesh_kwargs={'scalars': '_rainbow'},
        )


# --- Renderer depth ---


def test_renderer_render_depth():
    mesh = pv.Sphere()
    with OffScreenRenderer(mesh, window_size=(100, 100)) as r:
        depth = r.render_depth()
        assert depth.mode == 'L'
        assert depth.size == (100, 100)


def test_renderer_honors_caller_supplied_style():
    """A ``style`` passed through to ``add_mesh`` is not overwritten."""
    mesh = pv.Sphere()
    with OffScreenRenderer(mesh, window_size=(100, 100), mesh_kwargs={'style': 'points'}) as r:
        assert r._actor.prop.style == 'Points'


def test_renderer_wireframe_overrides_caller_supplied_style():
    mesh = pv.Sphere()
    with OffScreenRenderer(
        mesh, window_size=(100, 100), wireframe=True, mesh_kwargs={'style': 'points'}
    ) as r:
        assert r._actor.prop.style == 'Wireframe'


def test_renderer_wireframe_toggle_restores_caller_style():
    """Toggling wireframe off returns to the caller's style, not surface."""
    mesh = pv.Sphere()
    with OffScreenRenderer(mesh, window_size=(100, 100), mesh_kwargs={'style': 'points'}) as r:
        r.toggle_wireframe()
        assert r._actor.prop.style == 'Wireframe'
        r.toggle_wireframe()
        assert r._actor.prop.style == 'Points'


def test_renderer_style_wireframe_syncs_toggle_state():
    """``style='wireframe'`` leaves the ``w`` hotkey in the on state."""
    mesh = pv.Sphere()
    with OffScreenRenderer(mesh, window_size=(100, 100), mesh_kwargs={'style': 'wireframe'}) as r:
        assert r.wireframe is True
        r.toggle_wireframe()
        assert r._actor.prop.style == 'Surface'


def test_renderer_show_edges_syncs_toggle_state():
    """``show_edges=True`` leaves the ``e`` hotkey in the on state."""
    mesh = pv.Sphere()
    with OffScreenRenderer(mesh, window_size=(100, 100), mesh_kwargs={'show_edges': True}) as r:
        assert r._show_edges is True
        r.toggle_edges()
        assert r._actor.prop.show_edges is False


@pytest.mark.parametrize('style', ['wireframe', 'Wireframe', 'WIREFRAME'])
def test_renderer_style_wireframe_case_insensitive(style):
    mesh = pv.Sphere()
    with OffScreenRenderer(mesh, window_size=(100, 100), mesh_kwargs={'style': style}) as r:
        assert r.wireframe is True


@pytest.mark.parametrize('style', ['points_gaussian', None])
def test_renderer_toggle_wireframe_normalizes_style(style):
    """Styles ``Property.style`` rejects survive a toggle round-trip."""
    mesh = pv.Sphere()
    with OffScreenRenderer(mesh, window_size=(100, 100), mesh_kwargs={'style': style}) as r:
        r.toggle_wireframe()
        assert r._actor.prop.style == 'Wireframe'
        r.toggle_wireframe()
        assert r._actor.prop.style == 'Surface'


def test_renderer_multiblock_wireframe_state():
    """MultiBlock ignores ``style``, so the toggle starts in the off state."""
    mb = pv.MultiBlock([pv.Sphere(), pv.Cube()])
    with OffScreenRenderer(mb, window_size=(100, 100), wireframe=True) as r:
        assert r.wireframe is False


def test_renderer_array_scalars_skip_name_validation():
    """Array-valued ``scalars`` is an ``add_mesh`` input, not a lookup name."""
    mesh = pv.Sphere()
    values = np.linspace(0.0, 1.0, mesh.n_points)
    with OffScreenRenderer(mesh, window_size=(100, 100), mesh_kwargs={'scalars': values}) as r:
        assert r.render_frame().size == (100, 100)


def test_plot_forwards_reset_camera():
    """``reset_camera`` is an ``add_mesh`` option, not a duplicate kwarg."""
    mesh = pv.Sphere()
    with OffScreenRenderer(mesh, window_size=(100, 100)) as r:
        # The default reset frames the mesh, so the frame is not blank.
        assert _n_colors(r.render_frame()) > 1
        default_cpos = r._plotter.camera_position
    with OffScreenRenderer(mesh, window_size=(100, 100), mesh_kwargs={'reset_camera': False}) as r:
        # Forwarding the option must not collide with the default, and
        # must actually change the camera the frame is rendered from.
        assert r._plotter.camera_position != default_cpos


def test_plot_forwards_rgb_to_vtk_mapper():
    """``rgb=True`` reaches the mapper as direct scalar coloring."""
    mesh = pv.Sphere()
    rng = np.random.default_rng(seed=0)
    mesh['colors'] = rng.integers(0, 255, (mesh.n_points, 3), dtype=np.uint8)
    prepared = prepare_mesh(mesh_or_path=mesh, scalars='colors', rgb=True)
    with OffScreenRenderer(
        prepared.mesh, window_size=(100, 100), mesh_kwargs=prepared.mesh_kwargs
    ) as r:
        assert r._actor.mapper.GetColorMode() == 2  # VTK_COLOR_MODE_DIRECT_SCALARS
