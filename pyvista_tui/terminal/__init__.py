"""Terminal capability detection and display utilities."""

from __future__ import annotations

from pyvista_tui.terminal._detect import (
    PROBE_ERRORS,
    get_terminal_render_size,
    load_textual_image_class,
    query_background_color,
    select_textual_image_protocol,
)
from pyvista_tui.terminal._iterm2 import supports_inline_image_protocol, try_iterm2_inline

__all__ = [
    'PROBE_ERRORS',
    'get_terminal_render_size',
    'load_textual_image_class',
    'query_background_color',
    'select_textual_image_protocol',
    'supports_inline_image_protocol',
    'try_iterm2_inline',
]
