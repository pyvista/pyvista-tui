"""Inline image protocol (iTerm2 / WezTerm) support."""

from __future__ import annotations

from base64 import b64encode
import io
import os
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image

# Terminals that natively implement the iTerm2 inline image protocol
# (OSC 1337 File=...).  WezTerm ships full support; iTerm2 is the
# original.  Both set ``TERM_PROGRAM`` locally and ``LC_TERMINAL`` over
# SSH (when the user opts in).
_INLINE_TERMINALS = frozenset({'iTerm2', 'WezTerm'})


def supports_inline_image_protocol() -> bool:
    """Return ``True`` if the current terminal speaks iTerm2 inline images.

    Returns
    -------
    bool
        ``True`` when the terminal is known to implement the OSC 1337
        ``File=`` inline image protocol.

    """
    if os.environ.get('TERM') == 'dumb':
        return False
    if os.environ.get('TERM_PROGRAM') in _INLINE_TERMINALS:
        return True
    return os.environ.get('LC_TERMINAL') in _INLINE_TERMINALS


def try_iterm2_inline(
    frame: Image.Image,
    filename: str,
    width_cells: int,
) -> bool:
    """Display an image using the iTerm2 inline image protocol.

    Works for any terminal that speaks the protocol natively — iTerm2
    and WezTerm at present.  Using this path on WezTerm is important
    because ``textual_image``'s Terminal Graphics Protocol rendering
    relies on Kitty Unicode placeholders, which WezTerm does not
    support and which show up as a bright-green bar over the image.

    Parameters
    ----------
    frame : Image.Image
        The PIL image to display.

    filename : str
        Display name for the image.

    width_cells : int
        Display width in terminal cell columns.

    Returns
    -------
    bool
        ``True`` if the image was written inline, ``False`` if the
        terminal does not support the protocol.

    """
    if not supports_inline_image_protocol():
        return False
    if not sys.__stdout__ or not sys.__stdout__.isatty():
        return False

    buf = io.BytesIO()
    frame.save(buf, format='PNG')
    raw = buf.getvalue()
    data = b64encode(raw).decode('ascii')
    name = b64encode(filename.encode()).decode('ascii')

    seq = f'\x1b]1337;File=name={name};size={len(raw)};width={width_cells};inline=1:{data}\a'
    sys.__stdout__.write(seq)
    sys.__stdout__.write('\n')
    sys.__stdout__.flush()
    return True
