from __future__ import annotations

import pytest
import pyvista as pv

from pyvista_tui.renderer import OffScreenRenderer, apply_rainbow, build_mesh_kwargs, resolve_mesh

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
