"""Tests for the ``.tui`` component registered on :class:`pyvista.Plotter`."""

from __future__ import annotations

from unittest.mock import patch

import pytest
import pyvista as pv

WINDOW_SIZE = (96, 72)


def _make_plotter() -> pv.Plotter:
    plotter = pv.Plotter()
    plotter.add_mesh(pv.Sphere(theta_resolution=12, phi_resolution=12), color='tomato')
    return plotter


def test_plotter_component_attached():
    plotter = _make_plotter()
    try:
        assert hasattr(plotter, 'tui')
    finally:
        plotter.close()


def test_plotter_component_cached_per_instance():
    plotter = _make_plotter()
    try:
        assert plotter.tui is plotter.tui
    finally:
        plotter.close()


def test_plotter_component_registered_record_reports_pyvista_tui_as_source():
    records = [r for r in pv.registered_plotter_components() if r.name == 'tui']
    assert len(records) == 1
    record = records[0]
    assert record.target.__name__ == 'BasePlotter'
    assert record.source.startswith('pyvista_tui._plotter')


def test_plotter_tui_show_renders_off_screen_plotter_before_plotter_show():
    plotter = _make_plotter()
    try:
        frame = plotter.tui.show(display=False, window_size=WINDOW_SIZE)
        assert frame.size == WINDOW_SIZE
    finally:
        plotter.close()


def test_plotter_tui_show_displays_themed_frame():
    plotter = _make_plotter()
    try:
        with patch('pyvista_tui._plotter.display_frame') as mock_display:
            frame = plotter.tui.show(
                theme='thermal',
                filename='scene.png',
                window_size=WINDOW_SIZE,
            )
        assert frame.size == WINDOW_SIZE
        mock_display.assert_called_once()
        assert mock_display.call_args.args[0] is frame
        assert mock_display.call_args.kwargs['theme'] == 'thermal'
        assert mock_display.call_args.kwargs['filename'] == 'scene.png'
    finally:
        plotter.close()


def test_plotter_tui_show_after_plotter_show_auto_close_false():
    plotter = _make_plotter()
    try:
        plotter.show(auto_close=False, interactive=False)
        frame = plotter.tui.show(display=False, window_size=WINDOW_SIZE)
        assert frame.size == WINDOW_SIZE
        assert not plotter._closed
    finally:
        plotter.close()


def test_plotter_show_after_plotter_tui_show_auto_close_false():
    plotter = _make_plotter()
    try:
        frame = plotter.tui.show(display=False, window_size=WINDOW_SIZE)
        plotter.show(auto_close=False, interactive=False)
        assert frame.size == WINDOW_SIZE
        assert not plotter._closed
    finally:
        plotter.close()


def test_plotter_tui_show_rejects_closed_plotter():
    plotter = _make_plotter()
    component = plotter.tui
    plotter.close()

    with pytest.raises(RuntimeError, match='closed Plotter'):
        component.show(display=False)


def test_plotter_tui_show_rejects_on_screen_plotter_before_first_render():
    plotter = _make_plotter()
    plotter.off_screen = False
    try:
        with pytest.raises(RuntimeError, match='requires off-screen rendering'):
            plotter.tui.show(display=False)
    finally:
        plotter.close()


def test_plotter_tui_show_treats_missing_first_time_as_first_render(monkeypatch):
    plotter = _make_plotter()
    plotter.off_screen = False
    monkeypatch.delattr(plotter, '_first_time')
    try:
        with pytest.raises(RuntimeError, match='requires off-screen rendering'):
            plotter.tui.show(display=False)
    finally:
        plotter.close()


def test_plotter_tui_show_can_force_off_screen_before_first_render():
    plotter = _make_plotter()
    plotter.off_screen = False
    try:
        with pytest.warns(UserWarning, match='force_off_screen=True'):
            frame = plotter.tui.show(
                display=False,
                force_off_screen=True,
                window_size=WINDOW_SIZE,
            )
        assert frame.size == WINDOW_SIZE
        assert plotter.off_screen
    finally:
        plotter.close()


def test_plotter_tui_show_exports_outputs(tmp_path):
    png_path = tmp_path / 'plotter.png'
    text_path = tmp_path / 'plotter.txt'
    plotter = _make_plotter()
    try:
        frame = plotter.tui.show(
            display=False,
            save=png_path,
            export_ascii=text_path,
            theme='braille',
            window_size=WINDOW_SIZE,
        )
    finally:
        plotter.close()

    assert frame.size == WINDOW_SIZE
    assert png_path.is_file()
    text = text_path.read_text(encoding='utf-8')
    assert any('\u2800' <= char <= '\u28ff' for char in text)


def test_plotter_tui_show_raises_on_none_screenshot():
    plotter = _make_plotter()
    try:
        with (
            patch.object(plotter, 'screenshot', return_value=None),
            pytest.raises(RuntimeError, match='returned None'),
        ):
            plotter.tui.show(display=False)
    finally:
        plotter.close()
