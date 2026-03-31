"""Boot sequence for both static and interactive modes."""

from __future__ import annotations

import logging
from pathlib import Path
import platform
import sys
import time
from typing import TYPE_CHECKING

import pyvista as pv
from rich.text import Text
from textual.screen import Screen
from textual.widgets import Static

from pyvista_tui import __version__

if TYPE_CHECKING:
    from rich.console import Console
    from textual.app import ComposeResult

    from pyvista_tui.utils.loader import MeshLoader

logger = logging.getLogger(__name__)


def _get_gpu_strings() -> tuple[str, str, str]:
    """Query GPU info without spawning a macOS dock icon.

    Creates a minimal off-screen render window with
    ``SetConnectContextToNSView(False)`` to prevent the dock bounce.
    This workaround is needed until pyvista/pyvista#8423 lands.
    """
    from pyvista.plotting import _vtk  # noqa: PLC0415

    ren_win = _vtk.vtkRenderWindow()
    ren_win.SetOffScreenRendering(True)
    if hasattr(ren_win, 'SetConnectContextToNSView'):
        ren_win.SetConnectContextToNSView(False)

    ren = _vtk.vtkRenderer()
    ren_win.AddRenderer(ren)
    ren_win.Render()

    if hasattr(ren_win, 'ReportCapabilities'):
        gl_vendor = ren_win.ReportCapabilities().split('\n')
    else:
        gl_vendor = []
    vendor = renderer_str = api = 'UNKNOWN'
    for line in gl_vendor:
        if 'vendor' in line.lower():
            vendor = line.split(':', 1)[-1].strip().upper()
        elif 'renderer' in line.lower():
            renderer_str = line.split(':', 1)[-1].strip().upper()
        elif 'version' in line.lower():
            api = line.split(':', 1)[-1].strip().upper()

    ren_win.Finalize()
    del ren_win
    return vendor, renderer_str, api


def _build_system_info(mesh_path: str) -> dict[str, str]:
    """Gather system info for the boot display."""
    # GPUInfo requires an active GPU context which may not exist on
    # headless servers or over SSH.  Fall back gracefully.
    try:
        gpu_vendor, gpu_renderer, gpu_api = _get_gpu_strings()
    except Exception:
        logger.debug('GPUInfo unavailable', exc_info=True)
        gpu_vendor = 'UNAVAILABLE'
        gpu_renderer = 'UNAVAILABLE'
        gpu_api = 'UNAVAILABLE'

    return {
        'banner': (
            '░█▀█░█░█░█░█░▀█▀░█▀▀░▀█▀░█▀█░░░░░▀█▀░█░█░▀█▀\n'
            '░█▀▀░░█░░▀▄▀░░█░░▀▀█░░█░░█▀█░▄▄▄░░█░░█░█░░█░\n'
            '░▀░░░░▀░░░▀░░▀▀▀░▀▀▀░░▀░░▀░▀░░░░░░▀░░▀▀▀░▀▀▀'
        ),
        'version': __version__,
        'os': f'{platform.system()} {platform.machine()}',
        'python': (f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}'),
        'pyvista': pv.__version__,
        'gpu_vendor': gpu_vendor,
        'gpu_renderer': gpu_renderer,
        'gpu_api': gpu_api,
        'filename': Path(mesh_path).name.upper(),
        'filesize': f'{Path(mesh_path).stat().st_size:,}',
    }


_BAR_WIDTH = 30


def _advance_progress(progress: float, *, loader_done: bool) -> float:
    """Advance the progress bar, pacing based on loader state."""
    if loader_done:
        return min(1.0, progress + 0.15)
    if progress < 0.7:
        return progress + 0.06
    if progress < 0.9:
        return progress + 0.015
    return min(0.95, progress + 0.003)


def boot_sequence(
    console: Console,
    mesh_path: str,
    *,
    loader: MeshLoader | None = None,
) -> None:
    """Display a blocking retro POST sequence with real system info.

    Parameters
    ----------
    console : Console
        Rich console to print to.

    mesh_path : str
        Path to the mesh file being loaded.

    loader : MeshLoader or None, optional
        Background mesh loader to pace the progress bar.

    """
    info = _build_system_info(mesh_path)

    console.print()
    for line in info['banner'].strip().split('\n'):
        _flash_line(console, line, delay=0.002)
    _flash_line(console, f'v{info["version"]}  (C) 2026 The PyVista Developers')
    console.print()

    _type_line(console, f'OS ............. {info["os"]}', delay=0.002)
    _type_line(console, f'PYTHON ......... {info["python"]}', delay=0.002)
    _type_line(console, f'PYVISTA ........ {info["pyvista"]}', delay=0.002)
    _type_line(console, f'GPU VENDOR ..... {info["gpu_vendor"]}', delay=0.002)
    _type_line(console, f'GPU RENDERER ... {info["gpu_renderer"]}', delay=0.002)
    _type_line(console, f'GPU API ........ {info["gpu_api"]}', delay=0.002)

    console.print()
    _type_line(console, f'LOADING {info["filename"]}', delay=0.003)
    _type_line(console, f'  SIZE: {info["filesize"]} BYTES', delay=0.002)

    progress = 0.0
    while progress < 1.0:
        loader_done = loader is None or not loader.is_loading
        progress = _advance_progress(progress, loader_done=loader_done)

        filled = int(progress * _BAR_WIDTH)
        empty = _BAR_WIDTH - filled
        pct = int(progress * 100)
        console.print(
            f'  [green]MESH [{"█" * filled}{"░" * empty}] {pct:3d}%[/green]',
            end='\r',
            highlight=False,
        )
        time.sleep(0.04)
    console.print(highlight=False)

    if loader is not None:
        mesh = loader.result()
        _type_line(console, f'  POINTS: {mesh.n_points:,}', delay=0.002)
        _type_line(console, f'  CELLS:  {mesh.n_cells:,}', delay=0.002)
        _type_line(console, f'  ARRAYS: {mesh.n_arrays}', delay=0.002)

    console.print()
    _type_line(console, 'INITIALIZING RENDER PIPELINE ...', delay=0.003)
    _type_line(console, 'READY.', delay=0.02)
    console.print()


def _type_line(console: Console, line: str, *, delay: float = 0.003) -> None:
    """Print a line character by character with typewriter effect."""
    text = Text()
    for char in line:
        text.append(char, style='green')
        console.print(text, end='\r', highlight=False)
        time.sleep(delay)
    console.print(highlight=False)


def _flash_line(console: Console, line: str, *, delay: float = 0.01) -> None:
    """Print a line instantly with a brief pause."""
    console.print(f'[green]{line}[/green]', highlight=False)
    time.sleep(delay)


def _build_boot_lines(info: dict[str, str]) -> list[str]:
    """Build Rich-markup lines for the interactive boot display."""
    header = [f'[green]{line}[/green]' for line in info['banner'].strip().split('\n')]
    return [
        '',
        *header,
        f'[dim green]v{info["version"]}  (C) 2026 The PyVista Developers[/dim green]',
        '',
        f'[green]OS ............. {info["os"]}[/green]',
        f'[green]PYTHON ......... {info["python"]}[/green]',
        f'[green]PYVISTA ........ {info["pyvista"]}[/green]',
        f'[green]GPU VENDOR ..... {info["gpu_vendor"]}[/green]',
        f'[green]GPU RENDERER ... {info["gpu_renderer"]}[/green]',
        f'[green]GPU API ........ {info["gpu_api"]}[/green]',
        '',
        f'[green]LOADING {info["filename"]}[/green]',
        f'[green]  SIZE: {info["filesize"]} BYTES[/green]',
    ]


class BootScreen(Screen):
    """Full-screen retro boot sequence that transitions to the main view.

    Parameters
    ----------
    mesh_path : str
        Path to the mesh file being loaded.

    loader : MeshLoader or None, optional
        Background mesh loader to pace the progress bar.

    """

    DEFAULT_CSS = """
    BootScreen {
        background: black;
    }
    #boot-text {
        padding: 1 2;
    }
    """

    def __init__(self, mesh_path: str, *, loader: MeshLoader | None = None) -> None:
        super().__init__()
        self._loader = loader
        self._lines = _build_boot_lines(_build_system_info(mesh_path))
        self._current_line = 0
        self._boot_widget: Static | None = None
        self._phase: str = 'text'
        self._progress = 0.0

    def compose(self) -> ComposeResult:
        """Compose the boot screen."""
        self._boot_widget = Static('', id='boot-text', markup=True)
        yield self._boot_widget

    def on_mount(self) -> None:
        """Start the typewriter animation."""
        self._timer = self.set_interval(0.04, self._tick)

    def _tick(self) -> None:
        """Drive the boot sequence animation."""
        if self._phase == 'text':
            self._tick_text()
        elif self._phase == 'progress':
            self._tick_progress()

    def _tick_text(self) -> None:
        """Animate the text lines one at a time."""
        if self._current_line >= len(self._lines):
            self._phase = 'progress'
            return
        if self._boot_widget is not None:
            displayed = '\n'.join(self._lines[: self._current_line + 1])
            self._boot_widget.update(displayed)
        self._current_line += 1

    def _tick_progress(self) -> None:
        """Animate the progress bar, paced by the mesh loader."""
        loader_done = self._loader is None or not self._loader.is_loading

        if loader_done and self._progress >= 1.0:
            self._finish()
            return

        self._progress = _advance_progress(
            self._progress,
            loader_done=loader_done,
        )
        self._render_progress()

    def _render_progress(self) -> None:
        """Update the display with the current progress bar state."""
        if self._boot_widget is None:
            return
        filled = int(self._progress * _BAR_WIDTH)
        empty = _BAR_WIDTH - filled
        pct = int(self._progress * 100)
        bar_line = f'[green]  MESH [{"█" * filled}{"░" * empty}] {pct:3d}%[/green]'
        displayed = '\n'.join([*self._lines, bar_line])
        self._boot_widget.update(displayed)

    def _finish(self) -> None:
        """Show mesh stats, READY, and dismiss."""
        self._phase = 'done'
        self._timer.stop()

        if self._boot_widget is None:
            self.app.call_later(self.dismiss, True)
            return

        bar_line = f'[green]  MESH [{"█" * _BAR_WIDTH}] 100%[/green]'
        stats: list[str] = []
        if self._loader is not None:
            mesh = self._loader.result()
            stats = [
                f'[green]  POINTS: {mesh.n_points:,}[/green]',
                f'[green]  CELLS:  {mesh.n_cells:,}[/green]',
                f'[green]  ARRAYS: {mesh.n_arrays}[/green]',
            ]

        lines = [*self._lines, bar_line, *stats, '', '[green]READY.[/green]']
        self._boot_widget.update('\n'.join(lines))
        self.set_timer(0.4, self._do_dismiss)

    def _do_dismiss(self) -> None:
        """Dismiss via call_later to avoid Textual ScreenError."""
        self.app.call_later(self.dismiss, True)
