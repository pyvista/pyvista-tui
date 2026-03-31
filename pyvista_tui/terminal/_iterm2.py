"""ITerm2 inline image protocol support."""

from __future__ import annotations

from base64 import b64encode
import io
import os
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image


def try_iterm2_inline(
    frame: Image.Image,
    filename: str,
    width_cells: int,
) -> bool:
    """Display an image using iTerm2's inline image protocol.

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
        ``True`` if iTerm2 was detected and the image was displayed.

    """
    if os.environ.get('TERM_PROGRAM') != 'iTerm2':
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
