from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import pyvista as pv

from pyvista_tui.renderer import OffScreenRenderer

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

pv.OFF_SCREEN = True


@pytest.fixture
def tmp_mesh(tmp_path: Path) -> str:
    """Create a temporary VTK file with a sphere mesh."""
    path = str(tmp_path / 'sphere.vtk')
    pv.Sphere().save(path)
    return path


@pytest.fixture
def renderer(tmp_mesh: str) -> Generator[OffScreenRenderer]:
    """Create an OffScreenRenderer with a sphere mesh."""
    mesh = pv.read(tmp_mesh)
    r = OffScreenRenderer(mesh, window_size=(200, 150))
    yield r
    r.close()
