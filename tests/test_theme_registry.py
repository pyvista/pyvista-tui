from __future__ import annotations

from typing import get_args

from PIL import Image

from pyvista_tui.cli import ThemeChoice
from pyvista_tui.effects import (
    THEME_HOTKEYS,
    THEME_NAMES,
    THEME_REGISTRY,
    Theme,
    ThemeInfo,
    apply_theme_effect,
    text_mode_for_theme,
)

# --- Registry integrity ---


def test_registry_all_entries_are_theme_info():
    for name, info in THEME_REGISTRY.items():
        assert isinstance(info, ThemeInfo), f'{name} is not ThemeInfo'


def test_registry_hotkeys_are_unique():
    hotkeys = [info.hotkey for info in THEME_REGISTRY.values()]
    assert len(hotkeys) == len(set(hotkeys)), 'Duplicate hotkeys in registry'


def test_registry_hotkeys_are_single_digits():
    for name, info in THEME_REGISTRY.items():
        assert len(info.hotkey) == 1, f'{name} hotkey not single char'
        assert info.hotkey.isdigit(), f'{name} hotkey not a digit'


def test_registry_text_modes_are_valid():
    valid = {'normal', 'ascii', 'matrix', 'braille'}
    for name, info in THEME_REGISTRY.items():
        assert info.text_mode in valid, f'{name} has invalid text_mode'


def test_registry_cli_literal_matches_registry():
    literal_names = set(get_args(ThemeChoice))
    registry_names = set(THEME_REGISTRY.keys())
    assert literal_names == registry_names, (
        f'ThemeChoice Literal is out of sync with THEME_REGISTRY. '
        f'Missing from Literal: {registry_names - literal_names}. '
        f'Extra in Literal: {literal_names - registry_names}.'
    )


# --- Derived lookups ---


def test_theme_names_matches_registry():
    assert set(THEME_NAMES) == set(THEME_REGISTRY.keys())


def test_theme_names_is_tuple():
    assert isinstance(THEME_NAMES, tuple)


def test_hotkey_map_covers_all_themes():
    assert set(THEME_HOTKEYS.values()) == set(THEME_REGISTRY.keys())


def test_hotkey_map_reverse_lookup():
    for name, info in THEME_REGISTRY.items():
        assert THEME_HOTKEYS[info.hotkey] == name


# --- Theme enum ---


def test_theme_enum_members_match_registry():
    enum_names = {member.value for member in Theme}
    assert enum_names == set(THEME_REGISTRY.keys())


def test_theme_enum_values_are_strings():
    for member in Theme:
        assert isinstance(member.value, str)


def test_theme_enum_is_str_subclass():
    for member in Theme:
        assert isinstance(member, str)


# --- text_mode_for_theme ---


def test_text_mode_for_unknown_theme_returns_normal():
    assert text_mode_for_theme('nonexistent_theme') == 'normal'


def test_text_mode_for_theme_enum_value_works():
    result = text_mode_for_theme(Theme.MATRIX)
    assert result == 'matrix'


# --- apply_theme_effect ---


def test_apply_theme_effect_unknown_theme_returns_original():
    img = Image.new('RGB', (10, 10))
    result = apply_theme_effect(img, 'nonexistent')
    assert result is img


def test_apply_theme_effect_no_effect_themes_return_original():
    img = Image.new('RGB', (10, 10))
    for name, info in THEME_REGISTRY.items():
        if info.effect is None:
            result = apply_theme_effect(img, name)
            assert result is img, f'{name} modified image despite no effect'
