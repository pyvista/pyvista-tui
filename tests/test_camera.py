from __future__ import annotations

from unittest.mock import MagicMock

from pyvista_tui.tui.camera import ROTATION_STEP, KeyboardCameraController


def _make_controller():
    renderer = MagicMock()
    controller = KeyboardCameraController(renderer)
    return controller, renderer


def test_h_rotates_left():
    ctrl, r = _make_controller()
    assert ctrl.handle_key('h')
    r.rotate.assert_called_once_with(-ROTATION_STEP, 0)


def test_l_rotates_right():
    ctrl, r = _make_controller()
    assert ctrl.handle_key('l')
    r.rotate.assert_called_once_with(ROTATION_STEP, 0)


def test_k_rotates_up():
    ctrl, r = _make_controller()
    assert ctrl.handle_key('k')
    r.rotate.assert_called_once_with(0, ROTATION_STEP)


def test_j_rotates_down():
    ctrl, r = _make_controller()
    assert ctrl.handle_key('j')
    r.rotate.assert_called_once_with(0, -ROTATION_STEP)


def test_shift_h_pans_left():
    ctrl, r = _make_controller()
    assert ctrl.handle_key('H')
    r.pan.assert_called_once()
    args = r.pan.call_args[0]
    assert args[0] > 0  # Left (positive dx = camera moves right, scene pans left)
    assert args[1] == 0


def test_shift_l_pans_right():
    ctrl, r = _make_controller()
    assert ctrl.handle_key('L')
    r.pan.assert_called_once()
    args = r.pan.call_args[0]
    assert args[0] < 0  # Right (negative dx = camera moves left, scene pans right)
    assert args[1] == 0


def test_shift_k_pans_up():
    ctrl, r = _make_controller()
    assert ctrl.handle_key('K')
    r.pan.assert_called_once()
    args = r.pan.call_args[0]
    assert args[0] == 0
    assert args[1] > 0  # Up


def test_shift_j_pans_down():
    ctrl, r = _make_controller()
    assert ctrl.handle_key('J')
    r.pan.assert_called_once()
    args = r.pan.call_args[0]
    assert args[0] == 0
    assert args[1] < 0  # Down


def test_plus_zooms_in():
    ctrl, r = _make_controller()
    assert ctrl.handle_key('plus')
    r.zoom.assert_called_once()
    assert r.zoom.call_args[0][0] < 0  # Negative = zoom in


def test_equal_zooms_in():
    ctrl, r = _make_controller()
    assert ctrl.handle_key('equal')
    r.zoom.assert_called_once()


def test_minus_zooms_out():
    ctrl, r = _make_controller()
    assert ctrl.handle_key('minus')
    r.zoom.assert_called_once()
    assert r.zoom.call_args[0][0] > 0  # Positive = zoom out


def test_r_resets_camera():
    ctrl, r = _make_controller()
    assert ctrl.handle_key('r')
    r.reset_camera.assert_called_once()


def test_w_toggles_wireframe():
    ctrl, r = _make_controller()
    assert ctrl.handle_key('w')
    r.toggle_wireframe.assert_called_once()


def test_p_toggles_projection():
    ctrl, r = _make_controller()
    assert ctrl.handle_key('p')
    r.toggle_projection.assert_called_once()


def test_unknown_key_returns_false():
    ctrl, r = _make_controller()
    assert not ctrl.handle_key('Q')
    r.rotate.assert_not_called()
    r.pan.assert_not_called()
    r.zoom.assert_not_called()
