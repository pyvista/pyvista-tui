from __future__ import annotations

import pyvista as pv

from pyvista_tui.theme import TerminalTheme


def test_terminal_theme_instantiation():
    theme = TerminalTheme()
    assert theme.name == 'terminal'
    assert theme.background is not None
    assert theme.show_edges is True
    assert theme.smooth_shading is False
    assert theme.show_scalar_bar is False


def test_terminal_theme_is_dark_theme():
    assert isinstance(TerminalTheme(), pv.themes.DarkTheme)
