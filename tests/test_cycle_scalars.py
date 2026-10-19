from __future__ import annotations

import numpy as np
import pyvista as pv

from pyvista_tui.renderer import OffScreenRenderer


def test_cycle_scalars_through_arrays():
    mesh = pv.Sphere()
    mesh.point_data['temp'] = np.arange(mesh.n_points, dtype=float)
    mesh.point_data['pressure'] = np.ones(mesh.n_points)
    with OffScreenRenderer(mesh, window_size=(100, 100)) as r:
        assert r._scalars_index == -1
        r.cycle_scalars()
        assert r._scalars_index == 0
        r.cycle_scalars()
        assert r._scalars_index == 1


def test_cycle_scalars_wraps_around():
    mesh = pv.Sphere()
    mesh.point_data['temp'] = np.arange(mesh.n_points, dtype=float)
    with OffScreenRenderer(mesh, window_size=(100, 100)) as r:
        r.cycle_scalars()  # index 0
        r.cycle_scalars()  # wraps to 0 (only 1 scalar)
        assert r._scalars_index == 0


def test_cycle_scalars_no_scalars_is_noop():
    mesh = pv.Sphere()
    with OffScreenRenderer(mesh, window_size=(100, 100)) as r:
        r.cycle_scalars()
        assert r._scalars_index == -1


def test_cycle_scalars_marks_dirty():
    mesh = pv.Sphere()
    mesh.point_data['temp'] = np.arange(mesh.n_points, dtype=float)
    with OffScreenRenderer(mesh, window_size=(100, 100)) as r:
        r.render_frame()
        assert not r.is_dirty
        r.cycle_scalars()
        assert r.is_dirty


def test_cycle_scalars_skips_multicomponent_arrays():
    mesh = pv.Sphere()
    # Normals are 3-component, should be skipped
    mesh.compute_normals(inplace=True)
    mesh.point_data['temp'] = np.arange(mesh.n_points, dtype=float)
    with OffScreenRenderer(mesh, window_size=(100, 100)) as r:
        # Only 'temp' should be in the list (normals are multi-component)
        assert 'temp' in r._scalars_names
        assert 'Normals' not in r._scalars_names


def test_cycle_scalars_uses_cell_field_data_for_cell_arrays():
    """Cycling to a cell array must make VTK look in the cell field data."""
    mesh = pv.Sphere()
    mesh.point_data['pdata'] = np.arange(mesh.n_points, dtype=float)
    mesh.cell_data['cdata'] = np.arange(mesh.n_cells, dtype=float)
    with OffScreenRenderer(mesh, window_size=(100, 100)) as r:
        mapper = r._actor.mapper
        r.cycle_scalars()  # 'pdata' -- point data
        assert mapper.scalar_map_mode == 'point_field'
        r.cycle_scalars()  # 'cdata' -- cell data
        assert mapper.scalar_map_mode == 'cell_field'


def test_cycle_scalars_keeps_cell_colormap_applied():
    """The cell colormap must survive the scalars cycle.

    Without ``lighting=False`` the shading hides the difference, so the
    mesh is rendered unlit to compare the actual colormap output.
    """
    mesh = pv.Sphere(theta_resolution=20, phi_resolution=20)
    mesh.cell_data['cdata'] = (np.arange(mesh.n_cells) % 2).astype(float)

    with OffScreenRenderer(
        mesh,
        window_size=(80, 80),
        mesh_kwargs={'lighting': False},
    ) as r:
        # PyVista colours by the only array it finds -- a cell array.
        reference = np.asarray(r.render_frame()).copy()
        r.cycle_scalars()  # cycles to 'cdata'
        cycled = np.asarray(r.render_frame())

        assert np.array_equal(reference, cycled)
