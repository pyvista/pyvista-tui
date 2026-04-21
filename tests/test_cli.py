from __future__ import annotations

import subprocess
import sys

import pyvista as pv


def test_help():
    result = subprocess.run(
        [sys.executable, '-m', 'pyvista_tui', '--help'],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert 'mesh' in result.stdout.lower() or 'MESH' in result.stdout


def test_missing_file():
    result = subprocess.run(
        [sys.executable, '-m', 'pyvista_tui', 'nonexistent.vtk'],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0


def test_version():
    result = subprocess.run(
        [sys.executable, '-m', 'pyvista_tui', '--version'],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    from importlib.metadata import version  # noqa: PLC0415

    assert version('pyvista-tui') in result.stdout


def test_multiple_meshes_default_grid_save(tmp_path):
    """Default multi-mesh mode composites into a single grid PNG."""
    cone_path = tmp_path / 'cone.vtk'
    cube_path = tmp_path / 'cube.vtk'
    pv.Cone().save(str(cone_path))
    pv.Cube().save(str(cube_path))

    result = subprocess.run(
        [
            sys.executable,
            '-m',
            'pyvista_tui',
            str(cone_path),
            str(cube_path),
            '--save',
        ],
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / 'multi_cone.png').exists()
    assert not (tmp_path / 'cone.png').exists()


def test_multiple_meshes_no_gallery_sequential_save(tmp_path):
    """``--no-gallery`` opts out of the grid into per-mesh sequential renders."""
    cone_path = tmp_path / 'cone.vtk'
    cube_path = tmp_path / 'cube.vtk'
    pv.Cone().save(str(cone_path))
    pv.Cube().save(str(cube_path))

    result = subprocess.run(
        [
            sys.executable,
            '-m',
            'pyvista_tui',
            str(cone_path),
            str(cube_path),
            '--no-gallery',
            '--save',
        ],
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / 'cone.png').exists()
    assert (tmp_path / 'cube.png').exists()
    assert not (tmp_path / 'multi_cone.png').exists()
