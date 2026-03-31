from __future__ import annotations

import numpy as np
from PIL import Image
from rich.text import Text

from pyvista_tui.utils.text import (
    image_to_ascii,
    image_to_braille,
    image_to_matrix,
)


def _solid_image(r: int, g: int, b: int, size: int = 20) -> Image.Image:
    arr = np.full((size, size, 3), [r, g, b], dtype=np.uint8)
    return Image.fromarray(arr)


def _gradient_image(size: int = 40) -> Image.Image:
    arr = np.zeros((size, size, 3), dtype=np.uint8)
    for i in range(size):
        arr[i, :, :] = int(i / (size - 1) * 255)
    return Image.fromarray(arr)


# --- image_to_ascii ---


def test_ascii_returns_text():
    result = image_to_ascii(_solid_image(128, 128, 128), width=10, height=5)
    assert isinstance(result, Text)


def test_ascii_dimensions():
    result = image_to_ascii(_solid_image(200, 100, 50), width=15, height=8)
    lines = str(result).split('\n')
    assert len(lines) == 8
    assert all(len(line) == 15 for line in lines)


def test_ascii_black_maps_to_spaces():
    result = image_to_ascii(_solid_image(0, 0, 0), width=10, height=5)
    for ch in str(result):
        if ch != '\n':
            assert ch == ' '


def test_ascii_rgba_transparency():
    arr = np.zeros((10, 10, 4), dtype=np.uint8)
    img = Image.fromarray(arr)
    result = image_to_ascii(img, width=5, height=3)
    for ch in str(result):
        if ch != '\n':
            assert ch == ' '


# --- image_to_matrix ---


def test_matrix_returns_text():
    result = image_to_matrix(_gradient_image(), width=10, height=5)
    assert isinstance(result, Text)


def test_matrix_dimensions():
    result = image_to_matrix(_gradient_image(), width=12, height=6)
    lines = str(result).split('\n')
    assert len(lines) == 6
    assert all(len(line) == 12 for line in lines)


def test_matrix_transparent_maps_to_spaces():
    arr = np.zeros((10, 10, 4), dtype=np.uint8)
    img = Image.fromarray(arr)
    result = image_to_matrix(img, width=5, height=3)
    for ch in str(result):
        if ch != '\n':
            assert ch == ' '


# --- image_to_braille ---


def test_braille_returns_text():
    result = image_to_braille(_gradient_image(), width=10, height=5)
    assert isinstance(result, Text)


def test_braille_dimensions():
    result = image_to_braille(_gradient_image(), width=10, height=5)
    lines = str(result).split('\n')
    assert len(lines) == 5
    assert all(len(line) == 10 for line in lines)
