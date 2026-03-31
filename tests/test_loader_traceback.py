"""Tests for MeshLoader traceback preservation."""

from __future__ import annotations

import pytest

from pyvista_tui.utils.loader import MeshLoader


def test_loader_preserves_traceback():
    loader = MeshLoader('/nonexistent/file.vtk')
    with pytest.raises(FileNotFoundError) as exc_info:
        loader.result()
    # The traceback should point back to pv.read, not just loader.py
    tb = exc_info.traceback
    assert len(tb) > 1


def test_loader_error_message():
    loader = MeshLoader('/nonexistent/file.vtk')
    with pytest.raises(FileNotFoundError, match='nonexistent'):
        loader.result()
