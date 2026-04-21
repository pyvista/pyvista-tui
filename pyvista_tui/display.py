"""Terminal display utilities for rendered frames."""

from __future__ import annotations

from pathlib import Path
import shutil
from typing import TYPE_CHECKING

from rich.console import Console

from pyvista_tui.effects import apply_theme_effect, text_mode_for_theme
from pyvista_tui.renderer import OffScreenRenderer
from pyvista_tui.terminal import (
    PROBE_ERRORS,
    get_terminal_render_size,
    load_textual_image_class,
    try_iterm2_inline,
)
from pyvista_tui.utils.text import image_to_ascii, image_to_braille, image_to_matrix

__all__ = ['display_frame', 'launch_interactive', 'render_inline']

if TYPE_CHECKING:
    from PIL import Image as PILImage
    from pyvista import DataSet, MultiBlock

    from pyvista_tui.renderer import CposString, PreparedMesh
    from pyvista_tui.utils.loader import MeshLoader


def display_frame(
    frame: PILImage.Image,
    console: Console,
    *,
    theme: str = 'default',
    full_width: bool = False,
    filename: str = 'mesh.png',
) -> None:
    """Display a rendered frame inline in the terminal.

    Parameters
    ----------
    frame : PIL.Image.Image
        The rendered frame to display.

    console : Console
        Rich console for output.

    theme : str, default: 'default'
        Theme name controlling the display method.

    full_width : bool, default: ``False``
        If ``True``, use full terminal width for display.

    filename : str, default: 'mesh.png'
        Display name for iTerm2 inline images.

    """
    img_w, img_h = frame.size
    char_w = 80
    char_h = max(1, int(char_w * img_h / img_w / 2))
    text_mode = text_mode_for_theme(theme)

    if text_mode == 'matrix':
        console.print(image_to_matrix(frame, width=char_w, height=char_h))
    elif text_mode == 'braille':
        console.print(image_to_braille(frame, width=char_w, height=char_h))
    elif text_mode == 'ascii':
        console.print(image_to_ascii(frame, width=char_w, height=char_h))
    else:
        display_width = shutil.get_terminal_size().columns if full_width else char_w
        if not try_iterm2_inline(frame, filename, display_width):
            _print_termimage_or_ascii(frame, console, display_width, char_h)


def _print_termimage_or_ascii(
    frame: PILImage.Image,
    console: Console,
    display_width: int,
    ascii_height: int,
) -> None:
    """Print an image via ``textual_image`` with ASCII fallback.

    If ``textual_image`` cannot be imported (e.g. its module-level
    terminal probes crash on an unresponsive TTY) or the renderable
    raises while rendering, fall back to ASCII so the CLI still
    produces visible output instead of a traceback.
    """
    term_image_cls = load_textual_image_class()
    if term_image_cls is not None:
        try:
            console.print(term_image_cls(frame, width=display_width, height='auto'))
            return
        except PROBE_ERRORS:
            pass
    console.print(image_to_ascii(frame, width=display_width, height=ascii_height))


def render_inline(
    prepared: PreparedMesh,
    *,
    width: int = 1024,
    height: int = 576,
    background: str | None = None,
    theme: str = 'default',
    export_ascii: str | Path | None = None,
    save: str | Path | None = None,
    filename: str = 'mesh.png',
    cpos: CposString | None = None,
) -> None:
    """Render a mesh to the terminal in a single shot.

    This is the shared static rendering pipeline used by both the CLI
    and the Python API.

    Parameters
    ----------
    prepared : PreparedMesh
        Mesh and rendering config from
        :func:`~pyvista_tui.renderer.prepare_mesh`.

    width : int, default: 1024
        Render width in pixels.

    height : int, default: 576
        Render height in pixels.

    background : str or None, optional
        Background color.

    theme : str, default: 'default'
        Theme name for post-processing.

    export_ascii : str, Path, or None, optional
        Path to export ASCII art text file.

    save : str, Path, or None, optional
        Path to save the rendered PNG.

    filename : str, default: 'mesh.png'
        Display name for iTerm2 inline images.

    cpos : CposString or None, optional
        Initial camera position string. See
        :meth:`~pyvista_tui.renderer.OffScreenRenderer.set_cpos` for
        the accepted values.

    """
    with OffScreenRenderer(
        prepared.mesh,
        window_size=(width, height),
        wireframe=prepared.wireframe,
        background=background,
        use_terminal_theme=prepared.use_terminal_theme,
        mesh_kwargs=prepared.mesh_kwargs,
        cpos=cpos,
    ) as renderer:
        frame = renderer.render_frame()

    frame = apply_theme_effect(frame, theme)

    console = Console()
    display_frame(frame, console, theme=theme, filename=filename)

    if export_ascii is not None:
        text_mode = text_mode_for_theme(theme)
        if text_mode == 'braille':
            export_text = image_to_braille(frame, width=80, height=40)
        elif text_mode == 'matrix':
            export_text = image_to_matrix(frame, width=80, height=40)
        else:
            export_text = image_to_ascii(frame, width=80, height=40)
        out = Path(export_ascii)
        out.write_text(str(export_text))
        console.print(f'[dim]Exported ASCII art: {out.resolve()}[/dim]')

    if save is not None:
        out = Path(save)
        frame.save(str(out), format='PNG')
        console.print(f'[dim]Saved: {out.resolve()}[/dim]')


def launch_interactive(
    prepared: PreparedMesh,
    *,
    mesh_path: str = '',
    width: int | None = None,
    height: int | None = None,
    background: str | None = None,
    loader: MeshLoader | None = None,
    theme: str = 'default',
    spin: bool = False,
    bounce: bool = False,
    show_boot: bool = False,
    cpos: CposString | None = None,
) -> None:
    """Launch the interactive TUI with a prepared mesh.

    This is the shared interactive entry point used by both the CLI
    and the Python API.

    Parameters
    ----------
    prepared : PreparedMesh
        Mesh and rendering config from
        :func:`~pyvista_tui.renderer.prepare_mesh`.

    mesh_path : str, default: ''
        Original file path (used for boot screen display).

    width : int or None, optional
        Render width in pixels.  Detected from terminal if ``None``.

    height : int or None, optional
        Render height in pixels.  Detected from terminal if ``None``.

    background : str or None, optional
        Background color.

    loader : MeshLoader or None, optional
        Background loader (used to pace boot screen progress bar).

    theme : str, default: 'default'
        Rendering theme name.

    spin : bool, default: ``False``
        Start with auto-rotation.

    bounce : bool, default: ``False``
        Start with DVD-style bounce.

    show_boot : bool, default: ``False``
        Show the boot sequence screen.

    cpos : CposString or None, optional
        Initial camera position string. See
        :meth:`~pyvista_tui.renderer.OffScreenRenderer.set_cpos` for
        the accepted values.

    """
    from pyvista_tui.renderer import _DeferredMesh  # noqa: PLC0415
    from pyvista_tui.tui import TuiApp  # noqa: PLC0415
    from pyvista_tui.utils.loader import MeshLoader  # noqa: PLC0415

    if width is None or height is None:
        term_w, term_h = get_terminal_render_size()
        width = width or term_w
        height = height or term_h

    # In interactive mode the boot-screen animation already provides
    # the pv.read / GL-setup overlap window, so resolve the mesh here
    # rather than threading a loader through the Textual screen stack.
    resolved_mesh: DataSet | MultiBlock | None
    if isinstance(prepared.mesh, MeshLoader | _DeferredMesh):
        resolved_mesh = prepared.mesh.result()
    else:
        resolved_mesh = prepared.mesh

    tui = TuiApp(
        mesh_path,
        mesh=resolved_mesh,
        interactive=True,
        window_size=(width, height),
        wireframe=prepared.wireframe,
        background=background,
        use_terminal_theme=prepared.use_terminal_theme,
        mesh_kwargs=prepared.mesh_kwargs,
        loader=loader,
        theme=theme,
        spin=spin,
        bounce=bounce,
        show_boot=show_boot,
        cpos=cpos,
    )
    tui.run()
