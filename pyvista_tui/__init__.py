"""Interactive 3D mesh visualization in the terminal using PyVista."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

# Public attributes are resolved on first access via ``__getattr__`` so
# ``import pyvista_tui`` stays cheap (~1 ms).  Eagerly importing
# ``OffScreenRenderer`` / ``plot`` pulls the full ``pyvista.plotting``
# tree at package-import time and adds ~440 ms to every ``pvtui --help``.
# See ``profiling/STARTUP_PROFILE.md``.

if TYPE_CHECKING:
    # Exposed for static analysis; at runtime ``__getattr__`` resolves
    # these lazily to keep import cost off the ``pvtui --help`` path.
    from pyvista_tui._plot import plot as plot
    from pyvista_tui.effects import Theme as Theme
    from pyvista_tui.renderer import OffScreenRenderer as OffScreenRenderer
    from pyvista_tui.tui import TuiApp as TuiApp

    __version__: str


def __getattr__(name: str) -> Any:
    if name == 'TuiApp':
        from pyvista_tui.tui import TuiApp  # noqa: PLC0415

        return TuiApp
    if name == 'plot':
        from pyvista_tui._plot import plot  # noqa: PLC0415

        return plot
    if name == 'Theme':
        from pyvista_tui.effects import Theme  # noqa: PLC0415

        return Theme
    if name == 'OffScreenRenderer':
        from pyvista_tui.renderer import OffScreenRenderer  # noqa: PLC0415

        return OffScreenRenderer
    if name == '__version__':
        from importlib.metadata import PackageNotFoundError, version  # noqa: PLC0415

        try:
            return version('pyvista-tui')
        except PackageNotFoundError:  # pragma: no cover
            try:
                from pyvista_tui._version import __version__  # noqa: PLC0415

                return __version__
            except ImportError:
                return '0.0.0'
    msg = f'module {__name__!r} has no attribute {name!r}'
    raise AttributeError(msg)


__all__ = ['OffScreenRenderer', 'Theme', 'TuiApp', '__version__', 'plot']
