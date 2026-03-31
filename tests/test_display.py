from __future__ import annotations

from io import StringIO

import numpy as np
from PIL import Image
from rich.console import Console

from pyvista_tui.display import display_frame


def _test_frame(w: int = 100, h: int = 80) -> Image.Image:
    arr = np.full((h, w, 3), 128, dtype=np.uint8)
    return Image.fromarray(arr)


def test_display_frame_ascii_theme():
    console = Console(file=StringIO(), force_terminal=True)
    display_frame(_test_frame(), console, theme='retro')
    output = console.file.getvalue()
    assert len(output) > 0


def test_display_frame_matrix_theme():
    console = Console(file=StringIO(), force_terminal=True)
    display_frame(_test_frame(), console, theme='matrix')
    output = console.file.getvalue()
    assert len(output) > 0


def test_display_frame_braille_theme():
    console = Console(file=StringIO(), force_terminal=True)
    display_frame(_test_frame(), console, theme='braille')
    output = console.file.getvalue()
    assert len(output) > 0


def test_display_frame_default_theme_no_crash():
    console = Console(file=StringIO(), force_terminal=True)
    display_frame(_test_frame(), console, theme='default')
