"""Image post-processing effects and theme registry."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Literal

import numpy as np
from PIL import Image, ImageFilter

TextMode = Literal['normal', 'ascii', 'matrix', 'braille']

__all__ = [
    'THEME_HOTKEYS',
    'THEME_NAMES',
    'THEME_REGISTRY',
    'TextMode',
    'Theme',
    'ThemeInfo',
    'apply_theme_effect',
    'text_mode_for_theme',
]

if TYPE_CHECKING:
    from collections.abc import Callable

    EffectFunc = Callable[[Image.Image], Image.Image]


@dataclass(frozen=True)
class ThemeInfo:
    """Metadata for a single rendering theme.

    Parameters
    ----------
    text_mode : str
        Text rendering mode: ``'normal'``, ``'ascii'``, ``'matrix'``,
        or ``'braille'``.

    effect : callable or None
        Post-processing function ``(Image) -> Image``, or ``None``
        for themes that use the raw rendered image.

    hotkey : str
        Single-digit key (``'1'``--``'9'``) for interactive switching.

    description : str
        One-line description shown in ``--help``.

    use_terminal_theme : bool
        If ``True``, apply :class:`~pyvista_tui.theme.TerminalTheme`
        (high-contrast neon) instead of PyVista's dark theme.

    """

    text_mode: TextMode
    effect: EffectFunc | None
    hotkey: str
    description: str
    use_terminal_theme: bool = True


def crt_effect(image: Image.Image) -> Image.Image:
    """Apply CRT scanline and phosphor tint to an image.

    Parameters
    ----------
    image : Image.Image
        Source image.

    Returns
    -------
    Image.Image
        Image with CRT effect applied.

    """
    arr = np.array(image.convert('RGB'), dtype=np.float32)

    # Darken every other scanline
    arr[1::2] *= 0.55

    # Green phosphor tint
    arr[:, :, 0] *= 0.85
    arr[:, :, 1] *= 1.05
    arr[:, :, 2] *= 0.80

    base = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    bloom = base.filter(ImageFilter.GaussianBlur(radius=2))
    bloom_arr = np.array(bloom, dtype=np.float32)

    result = np.clip(arr * 0.85 + bloom_arr * 0.2, 0, 255).astype(np.uint8)
    return Image.fromarray(result)


def blueprint_effect(image: Image.Image) -> Image.Image:
    """Apply blueprint edge-detection effect.

    Parameters
    ----------
    image : Image.Image
        Source image.

    Returns
    -------
    Image.Image
        Blueprint-style image with white edges on deep blue.

    """
    gray = np.array(image.convert('L'), dtype=np.float32)

    gx = np.zeros_like(gray)
    gx[:, 1:-1] = gray[:, 2:] - gray[:, :-2]
    gy = np.zeros_like(gray)
    gy[1:-1, :] = gray[2:, :] - gray[:-2, :]

    edges = np.sqrt(gx**2 + gy**2)
    if edges.max() > 0:
        edges = np.clip(edges / edges.max() * 255, 0, 255)

    h, w = edges.shape
    result = np.zeros((h, w, 3), dtype=np.uint8)
    result[:, :, 0] = 10
    result[:, :, 1] = 15
    result[:, :, 2] = 45

    edge_norm = (edges / 255.0).astype(np.float32)
    result[:, :, 0] = np.clip(
        result[:, :, 0] + edge_norm * 220,
        0,
        255,
    ).astype(np.uint8)
    result[:, :, 1] = np.clip(
        result[:, :, 1] + edge_norm * 230,
        0,
        255,
    ).astype(np.uint8)
    result[:, :, 2] = np.clip(
        result[:, :, 2] + edge_norm * 255,
        0,
        255,
    ).astype(np.uint8)

    return Image.fromarray(result)


def phosphor_effect(
    image: Image.Image,
    *,
    color: str = 'green',
) -> Image.Image:
    """Apply monochrome phosphor monitor effect.

    Parameters
    ----------
    image : Image.Image
        Source image.

    color : str, default: 'green'
        Phosphor color: ``'green'`` (P1) or ``'amber'`` (P3).

    Returns
    -------
    Image.Image
        Monochrome phosphor-tinted image.

    """
    tints = {
        'green': (0x33, 0xFF, 0x33),
        'amber': (0xFF, 0xB0, 0x00),
    }
    tint = tints.get(color, tints['green'])

    gray = np.array(image.convert('L'), dtype=np.float32) / 255.0

    h, w = gray.shape
    result = np.zeros((h, w, 3), dtype=np.float32)
    result[:, :, 0] = gray * tint[0]
    result[:, :, 1] = gray * tint[1]
    result[:, :, 2] = gray * tint[2]

    base = Image.fromarray(np.clip(result, 0, 255).astype(np.uint8))
    bloom = base.filter(ImageFilter.GaussianBlur(radius=2))
    bloom_arr = np.array(bloom, dtype=np.float32)

    blended = np.clip(result * 0.85 + bloom_arr * 0.2, 0, 255).astype(
        np.uint8,
    )
    return Image.fromarray(blended)


# Pre-computed thermal LUT: maps 0-255 grayscale to false-color RGB.
_THERMAL_ANCHORS = np.array(
    [
        [0.0, 0, 0, 0],
        [0.2, 0, 0, 128],
        [0.4, 0, 0, 255],
        [0.6, 255, 0, 0],
        [0.8, 255, 255, 0],
        [1.0, 255, 255, 255],
    ],
    dtype=np.float32,
)
_THERMAL_POSITIONS = _THERMAL_ANCHORS[:, 0]
_THERMAL_LUT = np.zeros((256, 3), dtype=np.uint8)
for _ch in range(3):
    _THERMAL_LUT[:, _ch] = np.clip(
        np.interp(
            np.linspace(0, 1, 256),
            _THERMAL_POSITIONS,
            _THERMAL_ANCHORS[:, _ch + 1],
        ),
        0,
        255,
    ).astype(np.uint8)


def thermal_effect(image: Image.Image) -> Image.Image:
    """Apply false-color thermal camera effect.

    Parameters
    ----------
    image : Image.Image
        Source image.

    Returns
    -------
    Image.Image
        False-color thermal image.

    """
    gray = np.array(image.convert('L'), dtype=np.uint8)
    return Image.fromarray(_THERMAL_LUT[gray])


def _phosphor_green(image: Image.Image) -> Image.Image:
    return phosphor_effect(image, color='green')


def _phosphor_amber(image: Image.Image) -> Image.Image:
    return phosphor_effect(image, color='amber')


THEME_REGISTRY: dict[str, ThemeInfo] = {
    'default': ThemeInfo(
        text_mode='normal',
        effect=None,
        hotkey='1',
        description='native terminal image (Sixel/halfcell)',
        use_terminal_theme=False,
    ),
    'retro': ThemeInfo(
        text_mode='ascii',
        effect=None,
        hotkey='3',
        description='colored ASCII art with neon green theme',
    ),
    'matrix': ThemeInfo(
        text_mode='matrix',
        effect=None,
        hotkey='4',
        description='Matrix-style green katakana characters',
    ),
    'braille': ThemeInfo(
        text_mode='braille',
        effect=None,
        hotkey='2',
        description='high-res Unicode braille (8x density)',
    ),
    'crt': ThemeInfo(
        text_mode='ascii',
        effect=crt_effect,
        hotkey='5',
        description='CRT scanlines + green phosphor glow',
    ),
    'blueprint': ThemeInfo(
        text_mode='ascii',
        effect=blueprint_effect,
        hotkey='6',
        description='Sobel edge detection on blue',
    ),
    'phosphor': ThemeInfo(
        text_mode='ascii',
        effect=_phosphor_green,
        hotkey='7',
        description='green monochrome P1 phosphor',
    ),
    'amber': ThemeInfo(
        text_mode='ascii',
        effect=_phosphor_amber,
        hotkey='8',
        description='amber monochrome P3 phosphor',
    ),
    'thermal': ThemeInfo(
        text_mode='ascii',
        effect=thermal_effect,
        hotkey='9',
        description='false-color thermal camera view',
    ),
}

# Derived lookups — generated once from the registry so every consumer
# stays in sync automatically.

#: All valid theme names as a tuple (used to build CLI Literal type).
THEME_NAMES: tuple[str, ...] = tuple(THEME_REGISTRY)

#: Hotkey -> theme name mapping for interactive mode.
THEME_HOTKEYS: dict[str, str] = {info.hotkey: name for name, info in THEME_REGISTRY.items()}


#: Enum of all theme names, derived from the registry.
Theme = Enum(  # type: ignore[misc]
    'Theme',
    {name.upper(): name for name in THEME_REGISTRY},
    type=str,
)


def text_mode_for_theme(theme: Theme | str) -> TextMode:
    """Return the text rendering mode for a given theme.

    Parameters
    ----------
    theme : Theme or str
        Theme name.

    Returns
    -------
    str
        One of ``'normal'``, ``'ascii'``, ``'matrix'``, or
        ``'braille'``.

    """
    name = theme.value if isinstance(theme, Theme) else theme
    info = THEME_REGISTRY.get(name)
    if info is None:
        return 'normal'
    return info.text_mode


def apply_theme_effect(frame: Image.Image, theme: Theme | str) -> Image.Image:
    """Apply the post-processing image effect for a theme.

    Parameters
    ----------
    frame : Image.Image
        Source image.

    theme : Theme or str
        Theme name.

    Returns
    -------
    Image.Image
        Processed image (unchanged for themes without an image
        effect).

    """
    name = theme.value if isinstance(theme, Theme) else theme
    info = THEME_REGISTRY.get(name)
    if info is None or info.effect is None:
        return frame
    return info.effect(frame)
