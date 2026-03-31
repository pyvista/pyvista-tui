"""Terminal background color detection and render size calculation."""

from __future__ import annotations

import shutil
import sys
from typing import Any

from textual_image._terminal import get_cell_size


def query_background_color() -> str | None:
    """Query the terminal's background color via OSC 11.

    Returns
    -------
    str or None
        Hex color string (e.g. ``'#1e1e1e'``) or ``None`` if detection
        fails (non-TTY, unsupported terminal, timeout).

    """
    if not sys.__stdout__ or not sys.__stdout__.isatty():
        return None

    try:
        from textual_image._terminal import (  # noqa: PLC0415
            TerminalError,
            capture_terminal_response,
        )
    except ImportError:
        return None

    result = _try_osc11_query(capture_terminal_response, TerminalError, '\x1b\\')
    if result is None:
        result = _try_osc11_query(capture_terminal_response, TerminalError, '\a')
    return result


def _try_osc11_query(
    capture_terminal_response: Any,
    terminal_error: type[Exception],
    end_marker: str,
) -> str | None:
    """Attempt one OSC 11 query with the given terminator."""
    try:
        with capture_terminal_response(
            start_marker='\x1b]11;', end_marker=end_marker, timeout=0.15
        ) as response:
            sys.__stdout__.write('\x1b]11;?\x1b\\')  # type: ignore[union-attr]
            sys.__stdout__.flush()  # type: ignore[union-attr]

        return _parse_osc11_response(response.sequence, end_marker)
    except (terminal_error, TimeoutError, ValueError, IndexError):
        return None


def _parse_osc11_response(seq: str, end_marker: str) -> str | None:
    """Parse an OSC 11 response into a hex color string.

    Parameters
    ----------
    seq : str
        Raw response sequence.

    end_marker : str
        The terminator used (ST or BEL).

    Returns
    -------
    str or None
        Hex color string or ``None`` if parsing fails.

    """
    prefix = '\x1b]11;rgb:'
    if not seq.startswith(prefix):
        return None

    rgb_part = seq[len(prefix) : -len(end_marker)]
    parts = rgb_part.split('/')
    if len(parts) != 3:
        return None

    r = int(parts[0][:2], 16)
    g = int(parts[1][:2], 16)
    b = int(parts[2][:2], 16)
    return f'#{r:02x}{g:02x}{b:02x}'


def get_terminal_render_size() -> tuple[int, int]:
    """Compute render pixel dimensions that fill the terminal.

    Returns
    -------
    tuple[int, int]
        ``(width_px, height_px)`` render dimensions.

    """
    term_cols, term_rows = shutil.get_terminal_size()
    cell = get_cell_size()
    return term_cols * cell.width, term_rows * cell.height
