from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image
import pyvista as pv

from pyvista_tui.renderer import OffScreenRenderer


def _rendered_mesh_is_visible(frame: Image.Image) -> bool:
    """Return True if the rendered frame actually shows a mesh.

    A blank/solid-colour frame (e.g. camera pointing outside the view
    frustum, so only the background is drawn) has ~1 unique colour.
    A frame with a lit mesh has many unique colours from shading.
    """
    arr = np.array(frame)
    unique = np.unique(arr.reshape(-1, arr.shape[-1]), axis=0)
    return len(unique) > 5


def test_render_frame_returns_pil_image(renderer):
    frame = renderer.render_frame()
    assert isinstance(frame, Image.Image)


def test_render_frame_dimensions(renderer):
    frame = renderer.render_frame()
    assert frame.size == (200, 150)


def test_render_frame_shows_mesh(renderer):
    """Regression: camera must fit the mesh so pixels aren't all one colour."""
    frame = renderer.render_frame()
    assert _rendered_mesh_is_visible(frame)


def test_render_frame_shows_mesh_with_large_bounds(tmp_path):
    """Regression for mesh bounds far from VTK's default camera (1, 1, 1).

    A mesh with bounds in the thousands used to render as a single
    background colour because ``show()`` was called before
    ``add_mesh()``, consuming the plotter's first-time reset.
    """
    mesh = pv.Sphere(radius=1000.0, center=(5000.0, 5000.0, 5000.0))
    r = OffScreenRenderer(mesh, window_size=(100, 100))
    try:
        frame = r.render_frame()
        assert _rendered_mesh_is_visible(frame)
    finally:
        r.close()


def test_dirty_flag_after_render(renderer):
    assert renderer.is_dirty
    renderer.render_frame()
    assert not renderer.is_dirty


def test_cached_frame_when_clean(renderer):
    frame1 = renderer.render_frame()
    frame2 = renderer.render_frame()
    assert frame1 is frame2


def test_rotate_sets_dirty(renderer):
    renderer.render_frame()
    assert not renderer.is_dirty
    renderer.rotate(5, 0)
    assert renderer.is_dirty


def test_rotate_changes_camera_position(renderer):
    pos_before = tuple(renderer._plotter.camera.position)
    renderer.rotate(10, 0)
    pos_after = tuple(renderer._plotter.camera.position)
    assert pos_before != pos_after


def test_rotate_elevation_changes_camera(renderer):
    pos_before = tuple(renderer._plotter.camera.position)
    renderer.rotate(0, 10)
    pos_after = tuple(renderer._plotter.camera.position)
    assert pos_before != pos_after


def test_pan_sets_dirty(renderer):
    renderer.render_frame()
    renderer.pan(0.1, 0)
    assert renderer.is_dirty


def test_pan_translates_focal_and_position(renderer):
    camera = renderer._plotter.camera
    focal_before = tuple(camera.focal_point)
    pos_before = tuple(camera.position)
    renderer.pan(0.1, 0.1)
    focal_after = tuple(camera.focal_point)
    pos_after = tuple(camera.position)

    # Both focal point and position should move
    assert focal_before != focal_after
    assert pos_before != pos_after

    # Camera-to-focal distance should be preserved
    def dist(a, b):
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b, strict=True)))

    assert abs(dist(pos_before, focal_before) - dist(pos_after, focal_after)) < 1e-6


def test_zoom_sets_dirty(renderer):
    renderer.render_frame()
    renderer.zoom(-2)
    assert renderer.is_dirty


def test_zoom_changes_camera_distance(renderer):
    camera = renderer._plotter.camera
    focal = tuple(camera.focal_point)
    pos_before = tuple(camera.position)
    dist_before = math.sqrt(sum((p - f) ** 2 for p, f in zip(pos_before, focal, strict=True)))

    renderer.zoom(-2)  # Zoom in

    pos_after = tuple(camera.position)
    focal_after = tuple(camera.focal_point)
    dist_after = math.sqrt(sum((p - f) ** 2 for p, f in zip(pos_after, focal_after, strict=True)))

    assert dist_after < dist_before


def test_reset_camera(renderer):
    pos_initial = tuple(renderer._plotter.camera.position)

    renderer.rotate(20, 15)
    renderer.zoom(-5)
    pos_changed = tuple(renderer._plotter.camera.position)
    assert pos_initial != pos_changed

    renderer.reset_camera()
    assert renderer.is_dirty


def test_toggle_wireframe(renderer):
    assert not renderer.wireframe
    renderer.toggle_wireframe()
    assert renderer.wireframe
    assert renderer.is_dirty
    renderer.toggle_wireframe()
    assert not renderer.wireframe


def test_toggle_projection(renderer):
    camera = renderer._plotter.camera
    assert not camera.parallel_projection
    renderer.toggle_projection()
    assert camera.parallel_projection
    assert renderer.is_dirty
    renderer.toggle_projection()
    assert not camera.parallel_projection


def test_resize(renderer):
    renderer.render_frame()
    renderer.resize(400, 300)
    assert renderer.is_dirty
    frame = renderer.render_frame()
    assert frame.size == (400, 300)


def test_save_screenshot(renderer, tmp_path):
    path = str(tmp_path / 'screenshot.png')
    renderer.save_screenshot(path)
    assert Path(path).exists()


def test_wireframe_init(tmp_mesh):
    mesh = pv.read(tmp_mesh)
    r = OffScreenRenderer(mesh, wireframe=True)
    assert r.wireframe
    r.close()


def test_background_init(tmp_mesh):
    mesh = pv.read(tmp_mesh)
    r = OffScreenRenderer(mesh, background='white')
    frame = r.render_frame()
    assert isinstance(frame, Image.Image)
    r.close()
