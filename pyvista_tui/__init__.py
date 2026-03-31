"""Interactive 3D mesh visualization in the terminal using PyVista."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from pyvista_tui._plot import plot
from pyvista_tui.effects import Theme
from pyvista_tui.renderer import OffScreenRenderer
from pyvista_tui.tui import TuiApp

try:
    __version__: str = version('pyvista-tui')
except PackageNotFoundError:
    __version__ = '0.0.0'

__all__ = ['OffScreenRenderer', 'Theme', 'TuiApp', '__version__', 'plot']
