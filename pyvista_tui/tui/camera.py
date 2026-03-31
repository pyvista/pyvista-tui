"""Keyboard camera controller with vim-style keybindings."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyvista_tui.renderer import OffScreenRenderer

ROTATION_STEP = 0.084  # ~4.8 degrees in radians
PAN_STEP = 0.05  # Fraction of camera-to-focal distance
ZOOM_STEP = 2.0  # Dolly step


class KeyboardCameraController:
    """Translate keyboard events to camera operations.

    Parameters
    ----------
    renderer : OffScreenRenderer
        The renderer to control.

    """

    def __init__(self, renderer: OffScreenRenderer) -> None:
        self._renderer = renderer

    def handle_key(self, key: str) -> bool:
        """Dispatch a key event to the appropriate camera operation.

        Parameters
        ----------
        key : str
            Key name from Textual's ``Key`` event (e.g. ``'h'``,
            ``'H'``, ``'plus'``, ``'minus'``).

        Returns
        -------
        bool
            ``True`` if the key was handled.

        """
        r = self._renderer

        # Rotation (vim hjkl + arrow keys)
        if key in ('h', 'left'):
            r.rotate(-ROTATION_STEP, 0)
        elif key in ('l', 'right'):
            r.rotate(ROTATION_STEP, 0)
        elif key in ('k', 'up'):
            r.rotate(0, ROTATION_STEP)
        elif key in ('j', 'down'):
            r.rotate(0, -ROTATION_STEP)

        # Pan (shift + vim hjkl)
        elif key == 'H':
            r.pan(PAN_STEP, 0)
        elif key == 'L':
            r.pan(-PAN_STEP, 0)
        elif key == 'K':
            r.pan(0, PAN_STEP)
        elif key == 'J':
            r.pan(0, -PAN_STEP)

        # Zoom
        elif key in ('plus', 'equal', 'i'):
            r.zoom(-ZOOM_STEP)
        elif key in ('minus', 'o'):
            r.zoom(ZOOM_STEP)

        # Actions
        elif key == 'r':
            r.reset_camera()
        elif key == 'w':
            r.toggle_wireframe()
        elif key == 'p':
            r.toggle_projection()
        elif key == 'e':
            r.toggle_edges()
        elif key == 'n':
            r.cycle_scalars()

        # Axis-aligned views
        elif key == 'x':
            r.set_view('x')
        elif key == 'y':
            r.set_view('y')
        elif key == 'z':
            r.set_view('z')

        else:
            return False

        return True
