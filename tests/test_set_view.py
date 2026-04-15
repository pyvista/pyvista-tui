from __future__ import annotations

from PIL import Image
import pyvista as pv

from pyvista_tui.renderer import OffScreenRenderer


def test_set_view_x(renderer):
    renderer.set_view('x')
    cam = renderer._plotter.camera
    assert cam.position[0] > cam.focal_point[0]
    assert abs(cam.position[1] - cam.focal_point[1]) < 1e-6
    assert abs(cam.position[2] - cam.focal_point[2]) < 1e-6


def test_set_view_neg_x(renderer):
    renderer.set_view('-x')
    cam = renderer._plotter.camera
    assert cam.position[0] < cam.focal_point[0]


def test_set_view_y(renderer):
    renderer.set_view('y')
    cam = renderer._plotter.camera
    assert cam.position[1] > cam.focal_point[1]
    assert abs(cam.position[0] - cam.focal_point[0]) < 1e-6


def test_set_view_neg_y(renderer):
    renderer.set_view('-y')
    cam = renderer._plotter.camera
    assert cam.position[1] < cam.focal_point[1]


def test_set_view_z(renderer):
    renderer.set_view('z')
    cam = renderer._plotter.camera
    assert cam.position[2] > cam.focal_point[2]
    assert abs(cam.position[0] - cam.focal_point[0]) < 1e-6


def test_set_view_neg_z(renderer):
    renderer.set_view('-z')
    cam = renderer._plotter.camera
    assert cam.position[2] < cam.focal_point[2]


def test_set_view_z_up_vector_is_y(renderer):
    renderer.set_view('z')
    cam = renderer._plotter.camera
    up = cam.up
    assert abs(up[1]) > 0.9
    assert abs(up[0]) < 0.1
    assert abs(up[2]) < 0.1


def test_set_view_x_up_vector_is_z(renderer):
    renderer.set_view('x')
    cam = renderer._plotter.camera
    up = cam.up
    assert abs(up[2]) > 0.9


def test_set_view_side_views_are_all_z_up(renderer):
    for axis in ('x', '-x', 'y', '-y'):
        renderer.set_view(axis)
        up = renderer._plotter.camera.up
        assert abs(up[2]) > 0.9, f'{axis} is not Z-up: {up}'


def test_set_view_marks_dirty(renderer):
    renderer.render_frame()
    assert not renderer.is_dirty
    renderer.set_view('x')
    assert renderer.is_dirty


def test_set_view_all_views_produce_valid_frames():
    mesh = pv.Sphere()
    with OffScreenRenderer(mesh, window_size=(100, 100)) as r:
        for axis in ('x', '-x', 'y', '-y', 'z', '-z'):
            r.set_view(axis)
            frame = r.render_frame()
            assert isinstance(frame, Image.Image)
            assert frame.size == (100, 100)
