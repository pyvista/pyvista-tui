from __future__ import annotations

from PIL import Image
import pytest
import pyvista as pv
from textual.strip import Strip

from pyvista_tui.effects import THEME_HOTKEYS
from pyvista_tui.renderer import resolve_mesh
from pyvista_tui.tui.app import TuiApp
from pyvista_tui.tui.viewport import ViewportWidget, _SafeImageWidget


def _make_app(**kwargs) -> TuiApp:
    """Create a TuiApp with a sphere mesh for testing."""
    mesh = resolve_mesh(mesh=pv.Sphere())
    return TuiApp(
        mesh=mesh,
        interactive=True,
        window_size=(200, 150),
        show_boot=False,
        **kwargs,
    )


# --- TUI app lifecycle ---


@pytest.mark.asyncio
async def test_tui_app_starts_and_quits():
    app = _make_app()
    async with app.run_test() as pilot:
        viewport = app.query_one('#viewport', ViewportWidget)
        assert viewport is not None
        await pilot.press('q')


@pytest.mark.asyncio
async def test_tui_renderer_created():
    app = _make_app()
    async with app.run_test():
        assert app._renderer is not None
        assert app._controller is not None


@pytest.mark.asyncio
async def test_tui_controls_bar_visible():
    app = _make_app()
    async with app.run_test():
        top = app.query_one('#controls-top')
        bottom = app.query_one('#controls-bottom')
        assert top is not None
        assert bottom is not None


# --- Key handling ---


@pytest.mark.asyncio
async def test_key_wireframe_toggle():
    app = _make_app()
    async with app.run_test() as pilot:
        assert not app._renderer.wireframe
        await pilot.press('w')
        assert app._renderer.wireframe
        await pilot.press('w')
        assert not app._renderer.wireframe


@pytest.mark.asyncio
async def test_key_edge_toggle():
    app = _make_app()
    async with app.run_test() as pilot:
        assert not app._renderer.show_edges
        await pilot.press('e')
        assert app._renderer.show_edges


@pytest.mark.asyncio
async def test_key_projection_toggle():
    app = _make_app()
    async with app.run_test() as pilot:
        cam = app._renderer._plotter.camera
        assert not cam.parallel_projection
        await pilot.press('p')
        assert cam.parallel_projection


@pytest.mark.asyncio
async def test_key_spin_toggle():
    app = _make_app()
    async with app.run_test() as pilot:
        viewport = app.query_one('#viewport', ViewportWidget)
        assert not viewport.spinning
        await pilot.press('s')
        assert viewport.spinning
        await pilot.press('s')
        assert not viewport.spinning


@pytest.mark.asyncio
async def test_key_depth_toggle():
    app = _make_app()
    async with app.run_test() as pilot:
        viewport = app.query_one('#viewport', ViewportWidget)
        assert not viewport.show_depth
        await pilot.press('d')
        assert viewport.show_depth


@pytest.mark.asyncio
async def test_key_mesh_info():
    app = _make_app()
    async with app.run_test() as pilot:
        await pilot.press('m')
        bar = app.query_one('#controls-bottom')
        text = str(bar.render())
        assert 'pts:' in text


@pytest.mark.asyncio
async def test_key_camera_rotation():
    app = _make_app()
    async with app.run_test() as pilot:
        pos_before = tuple(app._renderer._plotter.camera.position)
        await pilot.press('h')
        pos_after = tuple(app._renderer._plotter.camera.position)
        assert pos_before != pos_after


@pytest.mark.asyncio
async def test_key_camera_reset_does_not_crash():
    app = _make_app()
    async with app.run_test() as pilot:
        await pilot.press('h')
        await pilot.press('h')
        await pilot.press('r')
        assert app._renderer is not None


# --- Theme switching ---


@pytest.mark.asyncio
async def test_theme_switch_to_braille():
    app = _make_app()
    async with app.run_test() as pilot:
        viewport = app.query_one('#viewport', ViewportWidget)
        assert viewport.text_mode == 'normal'
        await pilot.press('2')
        assert viewport.text_mode == 'braille'


@pytest.mark.asyncio
async def test_theme_switch_back_to_default():
    app = _make_app()
    async with app.run_test() as pilot:
        viewport = app.query_one('#viewport', ViewportWidget)
        await pilot.press('2')
        assert viewport.text_mode == 'braille'
        await pilot.press('1')
        assert viewport.text_mode == 'normal'


@pytest.mark.asyncio
async def test_theme_all_hotkeys_valid():
    app = _make_app()
    async with app.run_test() as pilot:
        for key in THEME_HOTKEYS:
            await pilot.press(key)


# --- _SafeImageWidget ---


def test_safe_image_widget_render_line_returns_blank_on_error():
    img = Image.new('RGB', (10, 10), (128, 128, 128))
    widget = _SafeImageWidget(img)
    result = widget.render_line(0)
    assert isinstance(result, Strip)


def test_safe_image_widget_get_content_height_fallback():
    img = Image.new('RGB', (10, 10))
    widget = _SafeImageWidget(img)
    result = widget.get_content_height(object(), object(), 80)
    assert result == 1


# --- Viewport properties ---


@pytest.mark.asyncio
async def test_viewport_show_depth_marks_dirty():
    app = _make_app()
    async with app.run_test():
        viewport = app.query_one('#viewport', ViewportWidget)
        app._renderer.render_frame()
        assert not app._renderer.is_dirty
        viewport.show_depth = True
        assert app._renderer.is_dirty
