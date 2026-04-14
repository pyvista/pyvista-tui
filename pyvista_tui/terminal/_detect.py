"""Terminal background color detection and render size calculation."""

from __future__ import annotations

import logging
import os
import shutil
import sys
from typing import Any

logger = logging.getLogger(__name__)

# VT340 cell dimensions — the same default textual_image falls back to
# when it cannot probe the real values from the terminal.
_DEFAULT_CELL_WIDTH_PX = 10
_DEFAULT_CELL_HEIGHT_PX = 20

# Exceptions that can escape ``textual_image``'s stdin-probing code
# paths on uncooperative terminals.  Catching these keeps the CLI
# usable (falling back to ASCII) instead of bubbling a traceback.
PROBE_ERRORS: tuple[type[Exception], ...] = (
    OSError,
    TimeoutError,
    UnicodeDecodeError,
    AttributeError,
    ValueError,
)

# Same as ``PROBE_ERRORS`` plus :class:`ImportError` for sites that
# import from ``textual_image.renderable`` at call time.  The upstream
# module's import triggers stdin probes, so either kind of failure
# (missing package, uncooperative terminal) must be handled here.
_LOAD_ERRORS: tuple[type[Exception], ...] = (ImportError, *PROBE_ERRORS)


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
            # ``sys.__stdout__`` is guaranteed non-None here by the
            # ``isatty()`` check in ``query_background_color``, but
            # mypy can't follow the caller -> callee narrowing.
            sys.__stdout__.write('\x1b]11;?\x1b\\')  # type: ignore[union-attr]
            sys.__stdout__.flush()  # type: ignore[union-attr]

        return _parse_osc11_response(response.sequence, end_marker)
    except (terminal_error, TimeoutError, ValueError, IndexError, OSError):
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
        ``(width_px, height_px)`` render dimensions.  Falls back to
        VT340 cell sizes (10x20) if the terminal refuses to answer the
        cell-size probe.

    """
    term_cols, term_rows = shutil.get_terminal_size()
    cell_w, cell_h = _safe_cell_size()
    return term_cols * cell_w, term_rows * cell_h


def _safe_cell_size() -> tuple[int, int]:
    """Call ``textual_image.get_cell_size`` without letting probes crash us.

    Returns
    -------
    tuple[int, int]
        ``(width_px, height_px)`` cell dimensions, or the VT340 default
        if the probe times out, the terminal is unresponsive, or
        textual_image is missing.

    """
    try:
        from textual_image._terminal import get_cell_size  # noqa: PLC0415
    except ImportError:
        return _DEFAULT_CELL_WIDTH_PX, _DEFAULT_CELL_HEIGHT_PX

    try:
        cell = get_cell_size()
    except PROBE_ERRORS:
        logger.debug('get_cell_size() failed, using VT340 default', exc_info=True)
        return _DEFAULT_CELL_WIDTH_PX, _DEFAULT_CELL_HEIGHT_PX
    return cell.width, cell.height


def select_textual_image_protocol() -> type[Any] | None:
    """Pick a ``textual_image`` renderable class for the current terminal.

    The upstream module-level auto-detection in
    :mod:`textual_image.renderable` gets WezTerm and Konsole wrong
    (picks TGP, which only works on Kitty) and reads stdin at import
    time, which can hang or crash on terminals that don't answer
    probes.  When we can identify the terminal from environment
    variables we side-step both problems by picking the renderable
    class directly.

    Returns
    -------
    type or None
        A renderable class exported from ``textual_image.renderable``
        (e.g. :class:`textual_image.renderable.sixel.Image`) when we
        can pick confidently, otherwise ``None`` — the caller should
        then fall back to the upstream auto-detect.  Return type is
        ``type[Any]`` because the textual_image classes duck-type as
        Rich renderables without inheriting from
        :class:`rich.console.ConsoleRenderable`.

    """
    env = os.environ

    if env.get('TERM') == 'xterm-kitty' or 'KITTY_WINDOW_ID' in env:
        try:
            from textual_image.renderable.tgp import Image as TGPImage  # noqa: PLC0415
        except ImportError:
            return None
        return TGPImage

    if 'KONSOLE_VERSION' in env:
        try:
            from textual_image.renderable.sixel import (  # noqa: PLC0415
                Image as SixelImage,
            )
        except ImportError:
            return None
        return SixelImage

    if env.get('TERM_PROGRAM') == 'vscode':
        try:
            from textual_image.renderable.halfcell import (  # noqa: PLC0415
                Image as HalfcellImage,
            )
        except ImportError:
            return None
        return HalfcellImage

    return None


def load_textual_image_class() -> type[Any] | None:
    """Return a ``textual_image`` renderable class, trying env first.

    Returns
    -------
    type or None
        The best renderable class for the current terminal, or
        ``None`` if ``textual_image`` cannot be imported (or its
        module-level probing raises).

    """
    cls = select_textual_image_protocol()
    if cls is not None:
        return cls
    try:
        from textual_image.renderable import Image as TermImage  # noqa: PLC0415
    except _LOAD_ERRORS:
        logger.debug('textual_image.renderable import failed', exc_info=True)
        return None
    return TermImage
