from __future__ import annotations

from PIL import Image
import pytest
import pyvista as pv

from pyvista_tui.renderer import CPOS_STRINGS, OffScreenRenderer


def test_set_cpos_yz_places_camera_on_positive_x(renderer):
    renderer.set_cpos('yz')
    cam = renderer._plotter.camera
    assert cam.position[0] > cam.focal_point[0]
    assert abs(cam.position[1] - cam.focal_point[1]) < 1e-6
    assert abs(cam.position[2] - cam.focal_point[2]) < 1e-6


def test_set_cpos_zy_places_camera_on_negative_x(renderer):
    renderer.set_cpos('zy')
    cam = renderer._plotter.camera
    assert cam.position[0] < cam.focal_point[0]


def test_set_cpos_zx_places_camera_on_positive_y(renderer):
    renderer.set_cpos('zx')
    cam = renderer._plotter.camera
    assert cam.position[1] > cam.focal_point[1]
    assert abs(cam.position[0] - cam.focal_point[0]) < 1e-6


def test_set_cpos_xz_places_camera_on_negative_y(renderer):
    renderer.set_cpos('xz')
    cam = renderer._plotter.camera
    assert cam.position[1] < cam.focal_point[1]


def test_set_cpos_xy_places_camera_on_positive_z(renderer):
    renderer.set_cpos('xy')
    cam = renderer._plotter.camera
    assert cam.position[2] > cam.focal_point[2]
    assert abs(cam.position[0] - cam.focal_point[0]) < 1e-6


def test_set_cpos_yx_places_camera_on_negative_z(renderer):
    renderer.set_cpos('yx')
    cam = renderer._plotter.camera
    assert cam.position[2] < cam.focal_point[2]


def test_set_cpos_marks_dirty(renderer):
    renderer.render_frame()
    assert not renderer.is_dirty
    renderer.set_cpos('yz')
    assert renderer.is_dirty


def test_set_cpos_rejects_unknown_value(renderer):
    with pytest.raises(ValueError, match='Unknown cpos'):
        renderer.set_cpos('bogus')


def test_set_cpos_all_values_produce_valid_frames():
    mesh = pv.Sphere()
    with OffScreenRenderer(mesh, window_size=(100, 100)) as r:
        for cpos in CPOS_STRINGS:
            r.set_cpos(cpos)
            frame = r.render_frame()
            assert isinstance(frame, Image.Image)
            assert frame.size == (100, 100)


def test_renderer_cpos_constructor_arg():
    mesh = pv.Sphere()
    with OffScreenRenderer(mesh, window_size=(100, 100), cpos='xy') as r:
        cam = r._plotter.camera
        assert cam.position[2] > cam.focal_point[2]


def test_renderer_cpos_constructor_rejects_unknown_value():
    mesh = pv.Sphere()
    with pytest.raises(ValueError, match='Unknown cpos'):
        OffScreenRenderer(
            mesh,
            window_size=(100, 100),
            cpos='bogus',  # type: ignore[arg-type]  # intentional bad input
        )
