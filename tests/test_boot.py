from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pyvista as pv

from pyvista_tui.tui.boot import _advance_progress, _build_system_info

# --- _build_system_info ---


def test_build_system_info_returns_expected_keys(tmp_path: Path):
    path = str(tmp_path / 'test.vtk')
    pv.Sphere().save(path)
    info = _build_system_info(path)
    expected_keys = {
        'banner',
        'version',
        'os',
        'python',
        'pyvista',
        'gpu_vendor',
        'gpu_renderer',
        'gpu_api',
        'filename',
        'filesize',
    }
    assert set(info.keys()) == expected_keys


def test_build_system_info_filename_uppercase(tmp_path: Path):
    path = str(tmp_path / 'my_mesh.vtk')
    pv.Sphere().save(path)
    info = _build_system_info(path)
    assert info['filename'] == 'MY_MESH.VTK'


def test_build_system_info_gpu_info_failure_graceful(tmp_path: Path):
    path = str(tmp_path / 'test.vtk')
    pv.Sphere().save(path)
    with patch(
        'pyvista_tui.tui.boot._get_gpu_strings',
        side_effect=RuntimeError,
    ):
        info = _build_system_info(path)
    assert info['gpu_vendor'] == 'UNAVAILABLE'
    assert info['gpu_renderer'] == 'UNAVAILABLE'
    assert info['gpu_api'] == 'UNAVAILABLE'


# --- _advance_progress ---


def test_advance_progress_fast_when_loader_done():
    p = _advance_progress(0.5, loader_done=True)
    assert p == 0.65


def test_advance_progress_capped_at_one():
    p = _advance_progress(0.95, loader_done=True)
    assert p == 1.0


def test_advance_progress_slow_near_end():
    p = _advance_progress(0.91, loader_done=False)
    assert p < 0.96


def test_advance_progress_medium_speed_midway():
    p = _advance_progress(0.75, loader_done=False)
    assert 0.76 < p < 0.8


def test_advance_progress_monotonically_increasing():
    p = 0.0
    for _ in range(100):
        new_p = _advance_progress(p, loader_done=False)
        assert new_p >= p
        p = new_p
    # Should cap below 1.0 when loader is not done
    assert p < 1.0
