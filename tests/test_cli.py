from __future__ import annotations

import subprocess
import sys


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
    assert '0.1.0' in result.stdout
