"""Text-mode rasterizers for terminal rendering."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from rich.color import Color
from rich.style import Style
from rich.text import Text

if TYPE_CHECKING:
    from PIL import Image


__all__ = ['image_to_ascii', 'image_to_braille', 'image_to_matrix']

# Character ramp from dark to light, chosen for visual density gradient
ASCII_RAMP = ' .\'`^",:;Il!i><~+_-?][}{1)(|/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$'

# Braille dot offsets: each cell is 2 wide x 4 tall.
# Bit positions map to Unicode braille pattern offsets.
_BRAILLE_BASE = 0x2800
_BRAILLE_DOT_MAP = (
    (0x01, 0x08),  # row 0: dots 1, 4
    (0x02, 0x10),  # row 1: dots 2, 5
    (0x04, 0x20),  # row 2: dots 3, 6
    (0x40, 0x80),  # row 3: dots 7, 8
)

# Matrix-style characters: katakana + digits + symbols
_MATRIX_CHARS = 'ｦｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ0123456789:."=*+-<>|_/\\\''


def _get_style(r: int, g: int, b: int, cache: dict[tuple[int, int, int], Style]) -> Style:
    """Return a cached Style for an RGB triplet."""
    key = (r, g, b)
    style = cache.get(key)
    if style is None:
        style = Style(color=Color.from_rgb(r, g, b))
        cache[key] = style
    return style


def image_to_ascii(image: Image.Image, *, width: int, height: int) -> Text:
    """Convert a PIL Image to colored ASCII art.

    Parameters
    ----------
    image : Image.Image
        Source image (RGB or RGBA).

    width : int
        Output width in characters.

    height : int
        Output height in characters.

    Returns
    -------
    Text
        Rich Text object with colored ASCII characters.

    """
    resized = image.resize((width, height)).convert('RGBA')
    data: np.ndarray = np.asarray(resized)

    # Vectorize brightness and character index computation
    r = data[:, :, 0].astype(np.float32)
    g = data[:, :, 1].astype(np.float32)
    b = data[:, :, 2].astype(np.float32)
    a = data[:, :, 3]

    ramp_len = len(ASCII_RAMP)
    brightness = 0.299 * r + 0.587 * g + 0.114 * b
    indices = np.clip((brightness / 255.0 * (ramp_len - 1)).astype(int), 0, ramp_len - 1)
    transparent = a < 10

    style_cache: dict[tuple[int, int, int], Style] = {}
    text = Text()

    for y in range(height):
        for x in range(width):
            if transparent[y, x]:
                text.append(' ')
                continue
            text.append(
                ASCII_RAMP[indices[y, x]],
                style=_get_style(
                    int(data[y, x, 0]),
                    int(data[y, x, 1]),
                    int(data[y, x, 2]),
                    style_cache,
                ),
            )
        if y < height - 1:
            text.append('\n')

    return text


def image_to_matrix(image: Image.Image, *, width: int, height: int) -> Text:
    """Convert an image to Matrix-style colored katakana text.

    Parameters
    ----------
    image : Image.Image
        Source image (RGB or RGBA).

    width : int
        Output width in characters.

    height : int
        Output height in characters.

    Returns
    -------
    Text
        Rich Text with Matrix-styled characters.

    """
    resized = image.resize((width, height)).convert('RGBA')
    data = np.asarray(resized)

    # Vectorize brightness and character index
    r = data[:, :, 0].astype(np.float32)
    g = data[:, :, 1].astype(np.float32)
    b = data[:, :, 2].astype(np.float32)
    a = data[:, :, 3]

    n_chars = len(_MATRIX_CHARS)
    brightness = 0.299 * r + 0.587 * g + 0.114 * b
    char_indices = np.clip((brightness / 255.0 * (n_chars - 1)).astype(int), 0, n_chars - 1)
    green_vals = np.clip((80 + brightness * 0.69).astype(int), 0, 255)
    transparent = a < 10

    style_cache: dict[tuple[int, int, int], Style] = {}
    text = Text()

    for y in range(height):
        for x in range(width):
            if transparent[y, x]:
                text.append(' ')
                continue
            gv = int(green_vals[y, x])
            text.append(
                _MATRIX_CHARS[char_indices[y, x]],
                style=_get_style(0, gv, int(gv * 0.15), style_cache),
            )
        if y < height - 1:
            text.append('\n')

    return text


def image_to_braille(image: Image.Image, *, width: int, height: int) -> Text:
    """Convert an image to colored Unicode braille characters.

    Each braille character represents a 2x4 pixel block, giving 8x
    the resolution of plain ASCII per terminal cell.

    Parameters
    ----------
    image : Image.Image
        Source image (RGB or RGBA).

    width : int
        Output width in characters.

    height : int
        Output height in characters.

    Returns
    -------
    Text
        Rich Text with colored braille characters.

    """
    px_w = width * 2
    px_h = height * 4
    resized = image.resize((px_w, px_h)).convert('RGBA')
    data = np.asarray(resized, dtype=np.float32)

    brightness_map = 0.299 * data[:, :, 0] + 0.587 * data[:, :, 1] + 0.114 * data[:, :, 2]

    # Sobel edge magnitude for geometric detail
    edge_h = np.zeros_like(brightness_map)
    edge_h[:, 1:-1] = brightness_map[:, 2:] - brightness_map[:, :-2]
    edge_v = np.zeros_like(brightness_map)
    edge_v[1:-1, :] = brightness_map[2:, :] - brightness_map[:-2, :]
    edge_map = np.sqrt(edge_h**2 + edge_v**2)

    edge_max = edge_map.max()
    edge_norm = edge_map / edge_max if edge_max > 0 else edge_map
    detail_map = brightness_map + edge_norm * 120

    dm = detail_map[:px_h, :px_w]
    blocks = dm.reshape(height, 4, width, 2)
    block_mins = blocks.min(axis=(1, 3))
    block_maxs = blocks.max(axis=(1, 3))
    block_ranges = block_maxs - block_mins
    thresholds = np.where(
        block_ranges > 8,
        block_mins + block_ranges * 0.4,
        block_maxs * 0.5,
    )

    # Raw brightness per block (before edge enhancement) to detect
    # background regions where noise would otherwise create dots
    raw_blocks = brightness_map[:px_h, :px_w].reshape(height, 4, width, 2)
    raw_block_max = raw_blocks.max(axis=(1, 3))

    alpha_blocks = data[:px_h, :px_w, 3].reshape(height, 4, width, 2)
    rgb_blocks = data[:px_h, :px_w, :3].reshape(height, 4, width, 2, 3)

    style_cache: dict[tuple[int, int, int], Style] = {}
    text = Text()

    for cy in range(height):
        for cx in range(width):
            # Skip blocks where raw brightness is too low — these are
            # background, not mesh.  Without this check, edge detection
            # amplifies numerical noise into visible dots.
            if raw_block_max[cy, cx] < 6:
                text.append(' ')
                continue

            thresh = thresholds[cy, cx]
            d_block = blocks[cy, :, cx, :]
            c_block = rgb_blocks[cy, :, cx, :, :]
            a_block = alpha_blocks[cy, :, cx, :]

            code = _BRAILLE_BASE
            r_sum, g_sum, b_sum = 0, 0, 0
            n_lit = 0

            for row in range(4):
                for col in range(2):
                    if d_block[row, col] > thresh and a_block[row, col] > 10:
                        code |= _BRAILLE_DOT_MAP[row][col]
                        r_sum += int(c_block[row, col, 0])
                        g_sum += int(c_block[row, col, 1])
                        b_sum += int(c_block[row, col, 2])
                        n_lit += 1

            if n_lit == 0:
                text.append(' ')
            else:
                text.append(
                    chr(code),
                    style=_get_style(r_sum // n_lit, g_sum // n_lit, b_sum // n_lit, style_cache),
                )

        if cy < height - 1:
            text.append('\n')

    return text
