"""Terminal capability detection and display utilities."""

from __future__ import annotations

from pyvista_tui.terminal._detect import get_terminal_render_size, query_background_color
from pyvista_tui.terminal._iterm2 import try_iterm2_inline

__all__ = ['get_terminal_render_size', 'query_background_color', 'try_iterm2_inline']
