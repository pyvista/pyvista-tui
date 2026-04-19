"""Tests for terminal inline-image detection and graceful fallbacks."""

from __future__ import annotations

import builtins
from io import StringIO
import sys
from unittest.mock import patch

import numpy as np
from PIL import Image
from rich.console import Console
from textual_image.renderable.halfcell import Image as HalfcellImage
from textual_image.renderable.sixel import Image as SixelImage
from textual_image.renderable.tgp import Image as TGPImage

from pyvista_tui.display import display_frame
from pyvista_tui.terminal import _detect, _iterm2
from pyvista_tui.terminal._detect import (
    _safe_cell_size,
    get_terminal_render_size,
    load_textual_image_class,
    select_textual_image_protocol,
)
from pyvista_tui.terminal._iterm2 import supports_inline_image_protocol, try_iterm2_inline


def _frame() -> Image.Image:
    return Image.fromarray(np.full((32, 64, 3), 200, dtype=np.uint8))


def test_supports_inline_iterm2(monkeypatch):
    monkeypatch.setenv('TERM_PROGRAM', 'iTerm2')
    monkeypatch.delenv('LC_TERMINAL', raising=False)
    monkeypatch.setenv('TERM', 'xterm-256color')
    assert supports_inline_image_protocol() is True


def test_supports_inline_wezterm(monkeypatch):
    monkeypatch.setenv('TERM_PROGRAM', 'WezTerm')
    monkeypatch.delenv('LC_TERMINAL', raising=False)
    monkeypatch.setenv('TERM', 'xterm-256color')
    assert supports_inline_image_protocol() is True


def test_supports_inline_vscode(monkeypatch):
    monkeypatch.setenv('TERM_PROGRAM', 'vscode')
    monkeypatch.delenv('LC_TERMINAL', raising=False)
    monkeypatch.setenv('TERM', 'xterm-256color')
    assert supports_inline_image_protocol() is True


def test_supports_inline_lc_terminal_over_ssh(monkeypatch):
    monkeypatch.delenv('TERM_PROGRAM', raising=False)
    monkeypatch.setenv('LC_TERMINAL', 'WezTerm')
    monkeypatch.setenv('TERM', 'xterm-256color')
    assert supports_inline_image_protocol() is True


def test_supports_inline_rejects_dumb_terminal(monkeypatch):
    monkeypatch.setenv('TERM_PROGRAM', 'WezTerm')
    monkeypatch.setenv('TERM', 'dumb')
    assert supports_inline_image_protocol() is False


def test_supports_inline_rejects_unknown_terminal(monkeypatch):
    monkeypatch.delenv('TERM_PROGRAM', raising=False)
    monkeypatch.delenv('LC_TERMINAL', raising=False)
    monkeypatch.setenv('TERM', 'xterm-256color')
    assert supports_inline_image_protocol() is False


def test_try_iterm2_inline_writes_osc1337_for_wezterm(monkeypatch):
    monkeypatch.setenv('TERM_PROGRAM', 'WezTerm')
    monkeypatch.delenv('LC_TERMINAL', raising=False)
    monkeypatch.setenv('TERM', 'xterm-256color')

    fake = StringIO()
    # ``StringIO`` ships an ``isatty`` method that always returns
    # False; patch it on the instance so ``try_iterm2_inline`` treats
    # the fake stdout as a TTY for the duration of this test.
    fake.isatty = lambda: True  # type: ignore[method-assign]
    monkeypatch.setattr(sys, '__stdout__', fake)

    assert try_iterm2_inline(_frame(), 'mesh.png', 40) is True
    assert '\x1b]1337;File=' in fake.getvalue()


def test_try_iterm2_inline_returns_false_for_plain_xterm(monkeypatch):
    monkeypatch.delenv('TERM_PROGRAM', raising=False)
    monkeypatch.delenv('LC_TERMINAL', raising=False)
    monkeypatch.setenv('TERM', 'xterm-256color')
    assert try_iterm2_inline(_frame(), 'mesh.png', 40) is False


def test_select_protocol_kitty(monkeypatch):
    monkeypatch.setenv('TERM', 'xterm-kitty')
    monkeypatch.delenv('KONSOLE_VERSION', raising=False)
    monkeypatch.delenv('KITTY_WINDOW_ID', raising=False)
    monkeypatch.delenv('TERM_PROGRAM', raising=False)

    assert select_textual_image_protocol() is TGPImage


def test_select_protocol_konsole(monkeypatch):
    monkeypatch.setenv('TERM', 'xterm-256color')
    monkeypatch.setenv('KONSOLE_VERSION', '22.04')
    monkeypatch.delenv('KITTY_WINDOW_ID', raising=False)
    monkeypatch.delenv('TERM_PROGRAM', raising=False)

    assert select_textual_image_protocol() is SixelImage


def test_select_protocol_vscode(monkeypatch):
    monkeypatch.setenv('TERM_PROGRAM', 'vscode')
    monkeypatch.setenv('TERM', 'xterm-256color')
    monkeypatch.delenv('KONSOLE_VERSION', raising=False)
    monkeypatch.delenv('KITTY_WINDOW_ID', raising=False)

    assert select_textual_image_protocol() is HalfcellImage


def test_select_protocol_unknown_returns_none(monkeypatch):
    monkeypatch.delenv('TERM_PROGRAM', raising=False)
    monkeypatch.delenv('KONSOLE_VERSION', raising=False)
    monkeypatch.delenv('KITTY_WINDOW_ID', raising=False)
    monkeypatch.setenv('TERM', 'xterm-256color')

    assert select_textual_image_protocol() is None


def test_safe_cell_size_falls_back_on_timeout():
    with patch(
        'textual_image._terminal.get_cell_size',
        side_effect=TimeoutError('boom'),
    ):
        width, height = _safe_cell_size()
    assert width == _detect._DEFAULT_CELL_WIDTH_PX
    assert height == _detect._DEFAULT_CELL_HEIGHT_PX


def test_get_terminal_render_size_does_not_crash_on_timeout():
    with patch(
        'textual_image._terminal.get_cell_size',
        side_effect=TimeoutError('boom'),
    ):
        width_px, height_px = get_terminal_render_size()
    assert width_px > 0
    assert height_px > 0


def test_load_textual_image_class_returns_none_when_import_fails(monkeypatch):
    monkeypatch.delenv('TERM_PROGRAM', raising=False)
    monkeypatch.delenv('KONSOLE_VERSION', raising=False)
    monkeypatch.delenv('KITTY_WINDOW_ID', raising=False)
    monkeypatch.setenv('TERM', 'xterm-256color')

    real_import = builtins.__import__

    def failing_import(name, *args, **kwargs):
        if name == 'textual_image.renderable':
            msg = 'forced import failure'
            raise ImportError(msg)
        return real_import(name, *args, **kwargs)

    with patch('builtins.__import__', side_effect=failing_import):
        assert load_textual_image_class() is None


def test_display_frame_falls_back_to_ascii_when_termimage_fails(monkeypatch):
    monkeypatch.delenv('TERM_PROGRAM', raising=False)
    monkeypatch.delenv('LC_TERMINAL', raising=False)
    monkeypatch.setenv('TERM', 'xterm-256color')

    class BoomImage:
        def __init__(self, *args, **kwargs):
            msg = 'textual_image probe failed'
            raise TimeoutError(msg)

    monkeypatch.setattr(
        'pyvista_tui.display.load_textual_image_class',
        lambda: BoomImage,
    )

    console = Console(file=StringIO(), force_terminal=True, width=80)
    display_frame(_frame(), console, theme='default')
    output = console.file.getvalue()
    assert output, 'fallback must still produce visible output'
    # ASCII fallback must not accidentally emit the iTerm2 OSC 1337 or
    # the Kitty TGP start sequence that we are trying to bypass.
    assert '\x1b]1337' not in output
    assert '\x1b_G' not in output
    # The ASCII fallback draws printable characters; confirm we got
    # at least one printable non-space glyph instead of a stray ANSI
    # reset only.
    assert any(ch.isprintable() and not ch.isspace() for ch in output)


def test_iterm2_module_still_exports_helpers():
    assert hasattr(_iterm2, 'try_iterm2_inline')
    assert hasattr(_iterm2, 'supports_inline_image_protocol')
