"""Register a ``.tui`` component on PyVista plotters."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
import warnings

from PIL import Image
import pyvista as pv
from rich.console import Console

from pyvista_tui.display import display_frame
from pyvista_tui.effects import apply_theme_effect, text_mode_for_theme
from pyvista_tui.utils.text import image_to_ascii, image_to_braille, image_to_matrix

if TYPE_CHECKING:
    from pyvista import Plotter

    from pyvista_tui.effects import Theme


class TuiPlotterComponent:
    """Terminal-UI rendering component for PyVista plotters.

    Available as ``plotter.tui`` on :class:`pyvista.Plotter` instances
    once this plugin is registered.

    Examples
    --------
    >>> import pyvista as pv
    >>> pv.OFF_SCREEN = True
    >>> plotter = pv.Plotter()
    >>> _ = plotter.add_mesh(pv.Sphere())
    >>> plotter.tui.show(theme='matrix')  # doctest: +SKIP

    """

    def __init__(self, plotter: Plotter) -> None:
        self._plotter = plotter

    def show(
        self,
        *,
        theme: Theme | str = 'default',
        window_size: tuple[int, int] | None = None,
        transparent_background: bool | None = None,
        full_width: bool = False,
        filename: str = 'plotter.png',
        console: Console | None = None,
        display: bool = True,
        save: str | Path | None = None,
        export_ascii: str | Path | None = None,
        force_off_screen: bool = False,
    ) -> Image.Image:
        """Render the plotter's current scene in the terminal.

        Parameters
        ----------
        theme : Theme or str, default: 'default'
            Rendering theme to apply before display.

        window_size : tuple[int, int] or None, optional
            Temporary screenshot size ``(width, height)``.  The
            plotter's original window size is restored by PyVista after
            the screenshot.

        transparent_background : bool or None, optional
            Whether to request a transparent screenshot background.  If
            ``None``, PyVista uses the plotter theme default.

        full_width : bool, default: ``False``
            If ``True``, display image output using the full terminal
            width.

        filename : str, default: 'plotter.png'
            Display name used by terminal image protocols.

        console : rich.console.Console or None, optional
            Console used for terminal output.  If ``None``, a new
            console is created.

        display : bool, default: ``True``
            If ``True``, print the rendered frame in the terminal.

        save : str, Path, or None, optional
            Path to save the themed PNG frame.

        export_ascii : str, Path, or None, optional
            Path to save a text rendering of the themed frame.

        force_off_screen : bool, default: ``False``
            If ``True``, allow the component to set
            ``plotter.off_screen = True`` before the plotter's first
            render.  This enables ``plotter.tui.show()`` before
            ``plotter.show()`` for on-screen plotters.  The flag is
            intentionally not enabled by default because
            backend-specific native windows may already be configured at
            plotter construction time.

        Returns
        -------
        PIL.Image.Image
            The themed frame that was displayed or saved.

        """
        theme_name = _theme_name(theme)
        self._ensure_renderable(force_off_screen=force_off_screen)

        image = self._plotter.screenshot(
            return_img=True,
            transparent_background=transparent_background,
            window_size=window_size,
        )
        if image is None:
            msg = 'Plotter.screenshot(return_img=True) returned None.'
            raise RuntimeError(msg)

        frame = Image.fromarray(image)
        frame = apply_theme_effect(frame, theme_name)

        if display:
            display_frame(
                frame,
                console or Console(),
                theme=theme_name,
                full_width=full_width,
                filename=filename,
            )

        if export_ascii is not None:
            self._export_ascii(frame, theme_name, export_ascii)

        if save is not None:
            frame.save(str(save), format='PNG')

        return frame

    def _ensure_renderable(self, *, force_off_screen: bool) -> None:
        """Validate the plotter state before requesting a screenshot."""
        if getattr(self._plotter, '_closed', False):
            msg = 'Cannot render a closed Plotter.'
            raise RuntimeError(msg)

        if not getattr(self._plotter, '_first_time', True):
            return

        if getattr(self._plotter, 'off_screen', False):
            return

        if force_off_screen:
            warnings.warn(
                'force_off_screen=True sets plotter.off_screen before the '
                'first render. Prefer constructing the plotter with '
                'pv.OFF_SCREEN = True.',
                UserWarning,
                stacklevel=3,
            )
            self._plotter.off_screen = True
            return

        msg = (
            'Plotter.tui.show() before Plotter.show() requires '
            'off-screen rendering. Set pv.OFF_SCREEN = True before '
            'constructing the plotter, or pass force_off_screen=True to '
            'opt into setting plotter.off_screen before the first render.'
        )
        raise RuntimeError(msg)

    @staticmethod
    def _export_ascii(
        frame: Image.Image,
        theme: str,
        export_ascii: str | Path,
    ) -> None:
        """Write a text representation of a frame to disk."""
        text_mode = text_mode_for_theme(theme)
        if text_mode == 'braille':
            text = image_to_braille(frame, width=80, height=40)
        elif text_mode == 'matrix':
            text = image_to_matrix(frame, width=80, height=40)
        else:
            text = image_to_ascii(frame, width=80, height=40)
        Path(export_ascii).write_text(str(text), encoding='utf-8')


pv.register_plotter_component('tui')(TuiPlotterComponent)


def _theme_name(theme: Theme | str) -> str:
    """Return a concrete theme name from a theme enum or string."""
    value = getattr(theme, 'value', theme)
    return str(value)
