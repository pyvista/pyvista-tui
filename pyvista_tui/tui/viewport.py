"""Textual widget for displaying the 3D viewport."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from textual.message import Message
from textual.strip import Strip
from textual.widget import Widget
from textual.widgets import Static
from textual_image._terminal import get_cell_size
from textual_image.widget import Image as ImageWidget

from pyvista_tui.effects import apply_theme_effect, text_mode_for_theme
from pyvista_tui.utils.text import image_to_ascii, image_to_braille, image_to_matrix

if TYPE_CHECKING:
    from PIL import Image
    from textual.events import Resize
    from textual.timer import Timer

    from pyvista_tui.renderer import OffScreenRenderer

logger = logging.getLogger(__name__)

# Radians per animation tick (~4 degrees)
_SPIN_STEP = 0.067

# Pan fraction per animation tick
_BOUNCE_STEP = 0.008

# Minimum render dimensions to avoid VTK/PIL errors during resize
_MIN_PX = 16


class _SafeImageWidget(
    ImageWidget,  # type: ignore[call-arg, misc, valid-type]
    Renderable=ImageWidget._Renderable,
):
    """ImageWidget subclass that never throws during Textual rendering.

    The upstream ``textual_image.widget.Image`` uses a metaclass that
    mypy cannot analyze.  The ``type: ignore`` on the class definition
    is required until textual-image ships ``py.typed`` with proper
    stubs.

    The upstream ``ImageWidget.render_line`` calls ``_render_content``
    outside a try/except.  If the widget size is zero or the image is
    stale during a resize transition, ``_render_content`` can throw,
    and the unhandled exception surfaces as an orange Textual error
    toast (and corrupts the terminal on exit).

    This subclass catches those errors and returns blank strips so the
    widget simply shows black for a frame instead of crashing.
    """

    def render_line(self, y: int) -> Strip:
        """Render one line, returning blank on error."""
        try:
            return super().render_line(y)
        except Exception:
            return Strip.blank(self.size.width, self.rich_style)

    def get_content_height(
        self,
        container: object,
        viewport: object,
        width: int,
    ) -> int:
        """Return container height without triggering layout churn."""
        try:
            return container.height  # type: ignore[attr-defined]
        except Exception:
            return 1


class ViewportWidget(Widget):
    """Display a PyVista rendered frame in the terminal.

    This widget manages rendering, animation (spin/bounce), theme
    switching, and FPS/depth overlays.  All state that
    :class:`~pyvista_tui.tui.app.TuiApp` needs is exposed through
    public properties and methods.
    """

    DEFAULT_CSS = """
    ViewportWidget {
        width: 1fr;
        height: 1fr;
        overflow: hidden;
        background: black;
    }
    ViewportWidget > * {
        width: 1fr;
        height: 1fr;
    }
    """

    def render(self) -> str:
        """Return empty string when no content is mounted yet.

        Returns
        -------
        str
            Empty string placeholder.

        """
        return ''

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._renderer: OffScreenRenderer | None = None
        self._interactive = False
        self._theme = 'default'
        self._text_mode = 'normal'
        self._spin = False
        self._spin_direction = -1.0
        self._bounce = False
        self._bounce_dx = _BOUNCE_STEP
        self._bounce_dy = _BOUNCE_STEP * 0.7
        self._bounce_cx = 0.0
        self._bounce_cy = 0.0
        self._image_widget: _SafeImageWidget | None = None
        self._text_widget: Static | None = None
        self._started = False
        self._show_depth: bool = False
        self._frame_times: list[float] = []
        self._resize_timer: Timer | None = None

    @property
    def spinning(self) -> bool:
        """Return whether auto-rotation is active.

        Returns
        -------
        bool
            ``True`` if spin animation is running.

        """
        return self._spin

    @property
    def show_depth(self) -> bool:
        """Return whether the depth buffer overlay is active.

        Returns
        -------
        bool
            ``True`` if showing the depth buffer.

        """
        return self._show_depth

    @show_depth.setter
    def show_depth(self, value: bool) -> None:
        self._show_depth = value
        self.mark_dirty()

    @property
    def text_mode(self) -> str:
        """Return the current text rendering mode.

        Returns
        -------
        str
            One of ``'normal'``, ``'ascii'``, ``'matrix'``, or ``'braille'``.

        """
        return self._text_mode

    def start(
        self,
        renderer: OffScreenRenderer,
        *,
        interactive: bool = False,
        theme: str = 'default',
        spin: bool = False,
        bounce: bool = False,
    ) -> None:
        """Initialize the viewport with a renderer and begin displaying.

        Parameters
        ----------
        renderer : OffScreenRenderer
            The renderer to display.

        interactive : bool, default: ``False``
            Enable interactive camera controls.

        theme : str, default: 'default'
            Initial rendering theme.

        spin : bool, default: ``False``
            Start with auto-rotation enabled.

        bounce : bool, default: ``False``
            Start with DVD-style bounce animation.

        """
        self._renderer = renderer
        self._interactive = interactive
        self._theme = theme
        self._text_mode = text_mode_for_theme(theme)
        self._spin = spin
        self._bounce = bounce
        self._started = True

        frame = self.render_themed_frame()

        if self._text_mode != 'normal':
            self._text_widget = Static(
                self.frame_to_text(frame),  # type: ignore[arg-type]
                markup=False,
            )
            self.mount(self._text_widget)
        else:
            self._image_widget = _SafeImageWidget(frame)
            self.mount(self._image_widget)

        if self._interactive or self._spin or self._bounce:
            self.set_interval(1 / 15, self._tick)

    def set_theme(self, theme: str) -> None:
        """Switch the rendering theme at runtime.

        Parameters
        ----------
        theme : str
            New theme name.

        """
        old_text_mode = self._text_mode
        self._theme = theme
        self._text_mode = text_mode_for_theme(theme)

        # Swap widget type if switching between text and image modes
        if (old_text_mode == 'normal') != (self._text_mode == 'normal'):
            if self._image_widget is not None:
                self._image_widget.remove()
                self._image_widget = None
            if self._text_widget is not None:
                self._text_widget.remove()
                self._text_widget = None

            if self._renderer is not None:
                frame = self.render_themed_frame()
                if self._text_mode != 'normal':
                    self._text_widget = Static(
                        self.frame_to_text(frame),  # type: ignore[arg-type]
                        markup=False,
                    )
                    self.mount(self._text_widget)
                else:
                    self._image_widget = _SafeImageWidget(frame)
                    self.mount(self._image_widget)

        self.mark_dirty()

    def toggle_spin(self) -> None:
        """Toggle auto-rotation on or off."""
        self._spin = not self._spin

    def reverse_spin(self) -> None:
        """Reverse the spin direction."""
        self._spin_direction *= -1

    def mark_dirty(self) -> None:
        """Mark the renderer as needing a re-render."""
        if self._renderer is not None:
            self._renderer.mark_dirty()

    def render_themed_frame(self) -> Image.Image:
        """Render the current scene with theme effects applied.

        Returns
        -------
        Image.Image
            The post-processed frame.

        Raises
        ------
        RuntimeError
            If the renderer has not been initialized.

        """
        if self._renderer is None:
            msg = 'Renderer not initialized.'
            raise RuntimeError(msg)
        if self._show_depth:
            return self._renderer.render_depth()
        return apply_theme_effect(self._renderer.render_frame(), self._theme)

    def frame_to_text(self, frame: Image.Image) -> object:
        """Convert a frame to a Rich Text object based on theme.

        Parameters
        ----------
        frame : Image.Image
            The rendered frame.

        Returns
        -------
        Text
            Rich Text renderable for terminal display.

        """
        size = self.app.size
        w = max(1, size.width)
        h = max(1, size.height - 1)

        if self._text_mode == 'matrix':
            return image_to_matrix(frame, width=w, height=h)
        if self._text_mode == 'braille':
            return image_to_braille(frame, width=w, height=h)
        return image_to_ascii(frame, width=w, height=h)

    def on_resize(self, event: Resize) -> None:
        """Resize the render window after a short debounce.

        Rapid resize events (e.g. dragging the window edge) are
        debounced so that VTK only re-creates the framebuffer once
        the resize settles, avoiding flicker and wasted renders.
        """
        if self._renderer is None:
            return

        # Cancel any pending resize
        if self._resize_timer is not None:
            self._resize_timer.stop()

        self._resize_timer = self.set_timer(
            0.1,
            lambda: self._apply_resize(event),
        )

    def _apply_resize(self, event: Resize) -> None:
        """Apply a debounced resize to the VTK render window."""
        self._resize_timer = None
        if self._renderer is None:
            return
        try:
            cell = get_cell_size()
            px_w = max(_MIN_PX, event.size.width * cell.width)
            px_h = max(_MIN_PX, event.size.height * cell.height)
            self._renderer.resize(px_w, px_h)
        except Exception:
            logger.debug('Resize error', exc_info=True)

    def _tick(self) -> None:
        """Handle spin, bounce, and dirty-check per animation frame."""
        if self._renderer is None:
            return

        if self._spin:
            self._renderer.rotate(self._spin_direction * _SPIN_STEP, 0)

        if self._bounce:
            self._renderer.pan(self._bounce_dx, self._bounce_dy)
            self._bounce_cx += self._bounce_dx
            self._bounce_cy += self._bounce_dy
            if abs(self._bounce_cx) > 0.35:
                self._bounce_dx = -self._bounce_dx
            if abs(self._bounce_cy) > 0.25:
                self._bounce_dy = -self._bounce_dy

        if not self._renderer.is_dirty:
            return

        frame = self.render_themed_frame()

        now = time.monotonic()
        self._frame_times.append(now)
        self._frame_times = self._frame_times[-10:]
        if len(self._frame_times) >= 2:
            elapsed = self._frame_times[-1] - self._frame_times[0]
            if elapsed > 0:
                fps = (len(self._frame_times) - 1) / elapsed
                self.post_message(self.FpsUpdate(fps))

        if self._text_mode != 'normal' and self._text_widget is not None:
            self._text_widget.update(
                self.frame_to_text(frame),  # type: ignore[arg-type]
            )
        elif self._image_widget is not None:
            self._image_widget.image = frame

    class FpsUpdate(Message):
        """Posted when a new FPS measurement is available."""

        def __init__(self, fps: float) -> None:
            super().__init__()
            self.fps = fps
