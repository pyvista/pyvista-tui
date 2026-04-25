"""Tests for the ``.tui`` accessor registered on :class:`pyvista.DataObject`."""

from __future__ import annotations

from unittest.mock import patch

import pytest
import pyvista as pv

if not hasattr(pv, 'register_dataset_accessor'):
    pytest.skip(
        'pyvista.register_dataset_accessor is not available in this pyvista version',
        allow_module_level=True,
    )

import pyvista_tui  # noqa: F401 — import triggers the ``.tui`` accessor registration


def test_accessor_attached_on_polydata():
    assert hasattr(pv.Sphere(), 'tui')


def test_accessor_attached_on_image_data():
    # ImageData inherits from DataSet, which inherits from DataObject.
    assert hasattr(pv.ImageData(), 'tui')


def test_accessor_attached_on_multiblock():
    # MultiBlock inherits from DataObject (not DataSet).
    assert hasattr(pv.MultiBlock(), 'tui')


def test_accessor_cached_per_instance():
    sphere = pv.Sphere()
    assert sphere.tui is sphere.tui


def test_accessor_plot_forwards_to_pyvista_tui_plot():
    """``mesh.tui.plot(**kwargs)`` must call ``pyvista_tui.plot(mesh, **kwargs)``."""
    sphere = pv.Sphere()
    with patch('pyvista_tui._plot.plot') as mock_plot:
        sphere.tui.plot(theme='matrix', scalars='foo')
    mock_plot.assert_called_once_with(sphere, theme='matrix', scalars='foo')


def test_accessor_plot_passes_mesh_as_first_arg():
    """The accessor must pass its bound mesh as the mesh argument, not
    whatever the user has in a module-level variable."""
    mesh_a = pv.Sphere()
    mesh_b = pv.Cube()
    with patch('pyvista_tui._plot.plot') as mock_plot:
        mesh_a.tui.plot()
        mesh_b.tui.plot()
    assert mock_plot.call_args_list[0].args == (mesh_a,)
    assert mock_plot.call_args_list[1].args == (mesh_b,)


def test_accessor_registered_record_reports_pyvista_tui_as_source():
    records = [r for r in pv.registered_accessors() if r.name == 'tui']
    assert len(records) == 1
    record = records[0]
    assert record.target is pv.DataObject
    assert record.source.startswith('pyvista_tui._accessor')
