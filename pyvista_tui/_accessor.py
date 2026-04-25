"""Register a ``.tui`` accessor on PyVista dataset classes.

Importing this module (which :mod:`pyvista_tui` does on package import)
attaches a :class:`TuiAccessor` to :class:`pyvista.DataObject` so every
dataset and every :class:`~pyvista.MultiBlock` instance exposes the
``.tui`` namespace.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import pyvista as pv

if TYPE_CHECKING:
    from pyvista import DataObject, DataSet, MultiBlock


@pv.register_dataset_accessor('tui', pv.DataObject)
class TuiAccessor:
    """Terminal-UI rendering accessor for PyVista datasets.

    Available on every :class:`~pyvista.DataObject` subclass
    (``PolyData``, ``UnstructuredGrid``, ``ImageData``, ``MultiBlock``,
    and so on) once :mod:`pyvista_tui` has been imported.

    Examples
    --------
    >>> import pyvista as pv
    >>> import pyvista_tui  # noqa: F401 — registers ``.tui``
    >>> pv.Sphere().tui.plot(theme='matrix')  # doctest: +SKIP

    """

    def __init__(self, mesh: DataObject) -> None:
        self._mesh = mesh

    def plot(self, **kwargs: Any) -> None:
        """Render the mesh inline in the terminal.

        Thin wrapper around :func:`pyvista_tui.plot`. Accepts the same
        keyword arguments; see that function's docstring for the full
        parameter list (``theme``, ``scalars``, ``cmap``, ``cpos``,
        ``interactive``, and so on).

        Examples
        --------
        >>> import pyvista as pv
        >>> import pyvista_tui  # noqa: F401
        >>> pv.Sphere().tui.plot(theme='matrix')  # doctest: +SKIP

        """
        from pyvista_tui._plot import plot as _plot  # noqa: PLC0415

        _plot(cast('DataSet | MultiBlock', self._mesh), **kwargs)
