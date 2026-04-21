"""Interactive 3D mesh visualization in the terminal using PyVista."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from pyvista_tui._plot import plot
from pyvista_tui.effects import Theme
from pyvista_tui.renderer import OffScreenRenderer

try:
    __version__: str = version('pyvista-tui')
except PackageNotFoundError:  # pragma: no cover
    try:
        # Written by setuptools_scm at build time; may be absent in editable
        # installs or a fresh checkout without a built distribution.
        from pyvista_tui._version import __version__  # type: ignore[no-redef]
    except ImportError:
        __version__ = '0.0.0'


def __getattr__(name: str):
    if name == 'TuiApp':
        from pyvista_tui.tui import TuiApp  # noqa: PLC0415

        return TuiApp
    msg = f'module {__name__!r} has no attribute {name!r}'
    raise AttributeError(msg)


__all__ = ['OffScreenRenderer', 'Theme', 'TuiApp', '__version__', 'plot']
