from __future__ import annotations

import numpy as np
from PIL import Image
from rich.text import Text

from pyvista_tui.effects import (
    apply_theme_effect,
    blueprint_effect,
    crt_effect,
    phosphor_effect,
    text_mode_for_theme,
    thermal_effect,
)
from pyvista_tui.utils.text import image_to_braille, image_to_matrix


def _gradient_image(size: int = 20) -> Image.Image:
    """Create a small gradient test image."""
    arr = np.zeros((size, size, 3), dtype=np.uint8)
    for i in range(size):
        arr[i, :, :] = int(i / (size - 1) * 255)
    return Image.fromarray(arr)


def test_crt_effect_preserves_size():
    img = _gradient_image()
    result = crt_effect(img)
    assert result.size == img.size
    assert result.mode == 'RGB'


def test_blueprint_effect_preserves_size():
    img = _gradient_image()
    result = blueprint_effect(img)
    assert result.size == img.size
    assert result.mode == 'RGB'


def test_phosphor_effect_green():
    img = _gradient_image()
    result = phosphor_effect(img, color='green')
    assert result.size == img.size
    arr = np.array(result)
    # Green channel should dominate for bright pixels
    bright_row = arr[-1, 0]
    assert bright_row[1] >= bright_row[0]


def test_phosphor_effect_amber():
    img = _gradient_image()
    result = phosphor_effect(img, color='amber')
    assert result.size == img.size
    arr = np.array(result)
    # Blue channel should be near zero for amber
    assert arr[:, :, 2].max() < 30


def test_thermal_effect_colormap():
    img = _gradient_image()
    result = thermal_effect(img)
    assert result.size == img.size
    arr = np.array(result)
    # Dark pixels should be near black
    assert arr[0, 0].sum() < 30
    # Bright pixels should be near white
    assert arr[-1, 0].sum() > 600


def test_image_to_matrix_returns_text():
    img = _gradient_image()
    result = image_to_matrix(img, width=10, height=5)
    assert isinstance(result, Text)
    lines = str(result).split('\n')
    assert len(lines) == 5
    assert all(len(line) == 10 for line in lines)


def test_image_to_braille_returns_text():
    img = _gradient_image()
    result = image_to_braille(img, width=10, height=5)
    assert isinstance(result, Text)
    lines = str(result).split('\n')
    assert len(lines) == 5
    assert all(len(line) == 10 for line in lines)


def test_text_mode_for_theme():
    assert text_mode_for_theme('default') == 'normal'
    assert text_mode_for_theme('matrix') == 'matrix'
    assert text_mode_for_theme('braille') == 'braille'
    assert text_mode_for_theme('crt') == 'ascii'
    assert text_mode_for_theme('phosphor') == 'ascii'


def test_apply_theme_effect_dispatches():
    img = _gradient_image()
    # Known themes should return modified images
    for theme in ('crt', 'blueprint', 'phosphor', 'amber', 'thermal'):
        result = apply_theme_effect(img, theme)
        assert isinstance(result, Image.Image)
        assert result.size == img.size

    # Default theme returns the image unchanged
    result = apply_theme_effect(img, 'default')
    assert result is img
