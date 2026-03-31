"""Background mesh loader."""

from __future__ import annotations

import sys
import threading
from typing import TYPE_CHECKING

import pyvista as pv

if TYPE_CHECKING:
    from types import TracebackType

    from pyvista import DataSet

__all__ = ['MeshLoader']


class MeshLoader:
    """Load a mesh file in a background thread.

    Parameters
    ----------
    mesh_path : str
        Path to a mesh file readable by :func:`pyvista.read`.

    """

    def __init__(self, mesh_path: str) -> None:
        self._path = mesh_path
        self._mesh: DataSet | None = None
        self._error: Exception | None = None
        self._traceback: TracebackType | None = None
        self._thread = threading.Thread(target=self._load, daemon=True)
        self._thread.start()

    @property
    def is_loading(self) -> bool:
        """Return whether the mesh is still being loaded.

        Returns
        -------
        bool
            ``True`` if the background thread is still running.

        """
        return self._thread.is_alive()

    def _load(self) -> None:
        """Load the mesh in the background."""
        try:
            self._mesh = pv.read(self._path)  # type: ignore[arg-type,assignment]
        except Exception as exc:
            self._error = exc
            self._traceback = sys.exc_info()[2]

    def result(self) -> DataSet:
        """Wait for loading to complete and return the mesh.

        Returns
        -------
        DataSet
            The loaded mesh.

        Raises
        ------
        Exception
            Re-raises the original exception with its full traceback
            if the mesh failed to load.

        """
        self._thread.join()
        if self._error is not None:
            raise self._error.with_traceback(self._traceback)
        if self._mesh is None:
            msg = 'Mesh was not loaded.'
            raise RuntimeError(msg)
        return self._mesh
