from __future__ import annotations

from PIL import Image
import pyvista as pv

from pyvista_tui.effects import THEME_REGISTRY
from pyvista_tui.renderer import OffScreenRenderer, PreparedMesh, prepare_mesh

# --- prepare_mesh ---


def test_prepare_mesh_returns_prepared_mesh():
    result = prepare_mesh(mesh_or_path=pv.Sphere())
    assert isinstance(result, PreparedMesh)


def test_prepare_mesh_default_wireframe_false():
    result = prepare_mesh(mesh_or_path=pv.Sphere())
    assert result.wireframe is False


def test_prepare_mesh_rainbow_sets_wireframe():
    result = prepare_mesh(mesh_or_path=pv.Sphere(), rainbow=True)
    assert result.wireframe is True
    assert result.mesh_kwargs.get('scalars') == '_rainbow'
    assert result.mesh_kwargs.get('cmap') == 'gist_rainbow'


def test_prepare_mesh_rainbow_adds_scalars_array():
    result = prepare_mesh(mesh_or_path=pv.Sphere(), rainbow=True)
    assert '_rainbow' in result.mesh.point_data


def test_prepare_mesh_center_moves_to_origin():
    result = prepare_mesh(
        mesh_or_path=pv.Sphere(center=(10, 20, 30)),
        center=True,
    )
    assert abs(result.mesh.center[0]) < 1e-6
    assert abs(result.mesh.center[1]) < 1e-6
    assert abs(result.mesh.center[2]) < 1e-6


def test_prepare_mesh_default_theme_no_terminal_theme():
    result = prepare_mesh(mesh_or_path=pv.Sphere(), theme='default')
    assert result.use_terminal_theme is False


def test_prepare_mesh_retro_theme_uses_terminal_theme():
    result = prepare_mesh(mesh_or_path=pv.Sphere(), theme='retro')
    assert result.use_terminal_theme is True


def test_prepare_mesh_scalars_passed_through():
    mesh = pv.Sphere()
    mesh.point_data['temp'] = range(mesh.n_points)
    result = prepare_mesh(mesh_or_path=mesh, scalars='temp')
    assert result.mesh_kwargs.get('scalars') == 'temp'


def test_prepare_mesh_color_passed_through():
    result = prepare_mesh(mesh_or_path=pv.Sphere(), color='red')
    assert result.mesh_kwargs.get('color') == 'red'


def test_prepare_mesh_from_file_path(tmp_path):
    path = str(tmp_path / 'sphere.vtk')
    pv.Sphere().save(path)
    result = prepare_mesh(mesh_or_path=path)
    assert result.mesh.n_points > 0


def test_prepare_mesh_all_themes_valid():
    mesh = pv.Sphere()
    for theme_name in THEME_REGISTRY:
        result = prepare_mesh(mesh_or_path=mesh, theme=theme_name)
        assert isinstance(result, PreparedMesh)


def test_prepare_mesh_multiblock():
    mb = pv.MultiBlock([pv.Sphere(), pv.Cube()])
    result = prepare_mesh(mesh_or_path=mb)
    assert isinstance(result, PreparedMesh)
    assert result.mesh is mb


# --- MultiBlock rendering ---


def test_multiblock_renders_frame():
    mb = pv.MultiBlock([pv.Sphere(), pv.Cube()])
    with OffScreenRenderer(mb, window_size=(100, 100)) as r:
        frame = r.render_frame()
        assert isinstance(frame, Image.Image)
        assert frame.size == (100, 100)


def test_multiblock_mesh_info():
    mb = pv.MultiBlock([pv.Sphere(), pv.Cube()])
    with OffScreenRenderer(mb, window_size=(100, 100)) as r:
        info = r.mesh_info()
        assert 'blocks:2' in info


def test_multiblock_set_view():
    mb = pv.MultiBlock([pv.Sphere(), pv.Cube()])
    with OffScreenRenderer(mb, window_size=(100, 100)) as r:
        for axis in ('x', '-x', 'y', '-y', 'z', '-z'):
            r.set_view(axis)
            r.render_frame()


def test_multiblock_cycle_scalars_is_noop():
    mb = pv.MultiBlock([pv.Sphere(), pv.Cube()])
    with OffScreenRenderer(mb, window_size=(100, 100)) as r:
        r.cycle_scalars()
        assert r._scalars_index == -1
