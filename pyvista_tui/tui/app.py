"""Textual application for interactive 3D mesh viewing."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Vertical
from textual.widgets import Static

from pyvista_tui.effects import THEME_HOTKEYS
from pyvista_tui.renderer import OffScreenRenderer, resolve_mesh
from pyvista_tui.tui.camera import KeyboardCameraController
from pyvista_tui.tui.viewport import ViewportWidget

if TYPE_CHECKING:
    from pyvista import DataSet, MultiBlock
    from textual.events import Key

    from pyvista_tui.renderer import CposString
    from pyvista_tui.utils.loader import MeshLoader

logger = logging.getLogger(__name__)

CONTROLS_TITLE = 'hjkl:rotate  HJKL:pan  i/o:zoom  xyz:views  r:reset  q:quit'
CONTROLS_SUB = 'w:wire  e:edges  n:scalars  s:spin  m:info  d:depth  1-9:theme'


class TuiApp(App):
    """Terminal-based 3D mesh viewer application.

    Parameters
    ----------
    mesh_path : str, default: ''
        Path to a mesh file readable by :func:`pyvista.read`.

    interactive : bool, default: ``False``
        Enable interactive camera controls.

    window_size : tuple[int, int], default: (800, 600)
        Render resolution in pixels ``(width, height)``.

    wireframe : bool, default: ``False``
        Start in wireframe mode.

    background : str or None, optional
        Background color name or hex string.

    mesh_kwargs : dict[str, object] or None, optional
        Extra keyword arguments for :func:`pyvista.Plotter.add_mesh`.

    loader : MeshLoader or None, optional
        Background mesh loader.

    theme : str, default: 'default'
        Initial rendering theme.

    spin : bool, default: ``False``
        Start with auto-rotation.

    bounce : bool, default: ``False``
        Start with DVD-style bounce.

    show_boot : bool, default: ``False``
        Show the boot sequence screen.

    mesh : pyvista.DataSet or None, optional
        In-memory mesh object.

    cpos : CposString or None, optional
        Initial camera position string. See
        :meth:`~pyvista_tui.renderer.OffScreenRenderer.set_cpos` for
        the accepted values.

    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding('q', 'quit', 'Quit'),
    ]

    CSS = """
    #controls-bar {
        dock: top;
        height: 2;
        max-height: 2;
        background: $panel;
        color: $foreground;
    }
    #controls-bar Static {
        height: 1;
        text-wrap: nowrap;
        overflow-x: hidden;
    }
    """

    def __init__(
        self,
        mesh_path: str = '',
        *,
        interactive: bool = False,
        window_size: tuple[int, int] = (800, 600),
        wireframe: bool = False,
        background: str | None = None,
        use_terminal_theme: bool = False,
        mesh_kwargs: dict[str, object] | None = None,
        loader: MeshLoader | None = None,
        theme: str = 'default',
        spin: bool = False,
        bounce: bool = False,
        show_boot: bool = False,
        mesh: DataSet | MultiBlock | None = None,
        cpos: CposString | None = None,
    ) -> None:
        super().__init__()
        self._mesh_path = mesh_path
        self._mesh = mesh
        self._interactive = interactive
        self._window_size = window_size
        self._wireframe = wireframe
        self._background = background
        self._use_terminal_theme = use_terminal_theme
        self._mesh_kwargs = mesh_kwargs
        self._loader = loader
        self._theme = theme
        self._spin = spin
        self._bounce = bounce
        self._show_boot = show_boot
        self._cpos = cpos
        self._renderer: OffScreenRenderer | None = None
        self._controller: KeyboardCameraController | None = None

    def compose(self) -> ComposeResult:
        """Compose the application layout."""
        if self._interactive:
            with Vertical(id='controls-bar'):
                yield Static(CONTROLS_TITLE, id='controls-top')
                yield Static(CONTROLS_SUB, id='controls-bottom')
        yield ViewportWidget(id='viewport')

    def on_mount(self) -> None:
        """Show boot screen, then initialize the renderer."""
        if self._show_boot and self._mesh_path:
            from pyvista_tui.tui.boot import BootScreen  # noqa: PLC0415

            self.push_screen(
                BootScreen(self._mesh_path, loader=self._loader),
                callback=lambda _: self._init_renderer(),
            )
        else:
            self._init_renderer()

    def update_status(self, status: str) -> None:
        """Update the bottom controls bar with a status message.

        Parameters
        ----------
        status : str
            Short status text to display after the keybinding hints.

        """
        try:
            bar = self.query_one('#controls-bottom', Static)
            bar.update(f'{CONTROLS_SUB}  | {status}')
        except Exception:
            logger.debug('Failed to update status bar', exc_info=True)

    def on_viewport_widget_fps_update(
        self,
        message: ViewportWidget.FpsUpdate,
    ) -> None:
        """Handle FPS updates from the viewport."""
        try:
            bar = self.query_one('#controls-top', Static)
            bar.update(f'{CONTROLS_TITLE}  [{message.fps:.0f} FPS]')
        except Exception:
            logger.debug('Failed to update FPS display', exc_info=True)

    def on_key(self, event: Key) -> None:
        """Dispatch key events to the camera controller."""
        if not self._interactive or self._controller is None:
            return

        try:
            self._handle_key(event)
        except Exception:
            logger.debug('Key handler error for %r', event.key, exc_info=True)

    def on_unmount(self) -> None:
        """Clean up the renderer."""
        if self._renderer is not None:
            self._renderer.close()

    def _init_renderer(self) -> None:
        """Create the renderer and populate the viewport."""
        mesh = resolve_mesh(
            self._mesh_path,
            loader=self._loader,
            mesh=self._mesh,
        )
        self._renderer = OffScreenRenderer(
            mesh,
            window_size=self._window_size,
            wireframe=self._wireframe,
            background=self._background,
            use_terminal_theme=self._use_terminal_theme,
            mesh_kwargs=self._mesh_kwargs,
            cpos=self._cpos,
        )
        self._controller = KeyboardCameraController(self._renderer)

        viewport = self.query_one('#viewport', ViewportWidget)
        viewport.start(
            self._renderer,
            interactive=self._interactive,
            theme=self._theme,
            spin=self._spin,
            bounce=self._bounce,
        )

    def _handle_key(self, event: Key) -> None:
        """Process a key event."""
        viewport = self.query_one('#viewport', ViewportWidget)

        if event.key == 's':
            viewport.toggle_spin()
            event.prevent_default()
            self.update_status(
                'spin ' + ('on' if viewport.spinning else 'off'),
            )
            return

        if event.key == 'S':
            viewport.reverse_spin()
            event.prevent_default()
            self.update_status('spin reversed')
            return

        if event.key == 'm':
            if self._renderer is not None:
                self.update_status(self._renderer.mesh_info())
            event.prevent_default()
            return

        if event.key == 'd':
            viewport.show_depth = not viewport.show_depth
            event.prevent_default()
            self.update_status(
                'depth ' + ('on' if viewport.show_depth else 'off'),
            )
            return

        if event.key in THEME_HOTKEYS:
            theme = THEME_HOTKEYS[event.key]
            viewport.set_theme(theme)
            event.prevent_default()
            self.update_status(theme)
            return

        if self._controller is not None and self._controller.handle_key(
            event.key,
        ):
            event.prevent_default()
            self.update_status(event.key)
