from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import pyvista as pv

from pyvista_tui.utils.loader import MeshLoader

if TYPE_CHECKING:
    from pathlib import Path


def test_mesh_loader_loads_mesh(tmp_path: Path):
    path = str(tmp_path / 'sphere.vtk')
    pv.Sphere().save(path)
    loader = MeshLoader(path)
    mesh = loader.result()
    assert mesh.n_points > 0
    assert mesh.n_cells > 0


def test_mesh_loader_bad_path_raises():
    loader = MeshLoader('/nonexistent/file.vtk')
    with pytest.raises(FileNotFoundError):
        loader.result()
