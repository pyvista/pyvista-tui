"""Tests for OffScreenRenderer context manager and resource cleanup."""

from __future__ import annotations

import pyvista as pv

from pyvista_tui.renderer import OffScreenRenderer


def test_context_manager_closes():
    mesh = pv.Sphere()
    with OffScreenRenderer(mesh, window_size=(100, 100)) as renderer:
        frame = renderer.render_frame()
        assert frame is not None

    assert renderer._plotter._closed


def test_context_manager_on_exception():
    mesh = pv.Sphere()
    try:
        with OffScreenRenderer(mesh, window_size=(100, 100)) as renderer:
            renderer.render_frame()
            msg = 'test error'
            raise RuntimeError(msg)
    except RuntimeError:
        pass

    assert renderer._plotter._closed
