from __future__ import annotations

import numpy as np
from PIL import Image
from rich.text import Text

from pyvista_tui.utils.text import image_to_ascii


def _solid_image(r: int, g: int, b: int, size: int = 20) -> Image.Image:
    """Create a solid-color test image."""
    arr = np.full((size, size, 3), [r, g, b], dtype=np.uint8)
    return Image.fromarray(arr)


def test_image_to_ascii_returns_text():
    img = _solid_image(128, 128, 128)
    result = image_to_ascii(img, width=10, height=5)
    assert isinstance(result, Text)


def test_image_to_ascii_dimensions():
    img = _solid_image(200, 100, 50)
    result = image_to_ascii(img, width=15, height=8)
    lines = str(result).split('\n')
    assert len(lines) == 8
    assert all(len(line) == 15 for line in lines)


def test_image_to_ascii_black_is_spaces():
    img = _solid_image(0, 0, 0)
    result = image_to_ascii(img, width=10, height=5)
    # Black pixels should map to the darkest character (space)
    plain = str(result)
    for ch in plain:
        if ch != '\n':
            assert ch == ' '
