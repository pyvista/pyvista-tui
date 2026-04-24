"""Image-level regression tests for OffScreenRenderer.

These use :mod:`pytest_pyvista` to compare the rendered framebuffer
against cached baseline PNGs.  They are the backstop that would have
caught the camera-reset regression in commit bf217fd: when the mesh
silently drops outside the view frustum, the pixel-level diff against
the baseline blows past the error threshold.

We deliberately avoid symmetric primitives (``pv.Sphere``, ``pv.Cube``)
because a broken camera orientation would still produce a matching
baseline from most angles.  The letter ``F`` is used instead — it has
no mirror or rotational symmetry in any axis, so any camera/theme/mode
regression is visible as a pixel diff.

Baselines live in ``tests/image_cache/`` (see ``pyproject.toml``).
Regenerate with ``pytest --reset_image_cache`` or add new baselines
with ``pytest --add_missing_images``.

Pixel-level diffs have some GPU- and driver-dependent jitter, so the
error threshold is widened to ``1000`` to stay stable across common
development environments while still catching the kind of structural
regression the bf217fd camera-reset bug introduced (which produced a
diff in the tens of thousands against a correct baseline).
"""

from __future__ import annotations

import pyvista as pv

from pyvista_tui.renderer import OffScreenRenderer


def _asymmetric_mesh(scale: float = 1.0, offset: tuple[float, float, float] = (0.0, 0.0, 0.0)):
    """Return an asymmetric test mesh (letter ``F``) — no rotational or mirror symmetry."""
    mesh = pv.Text3D('F', depth=0.5)
    if scale != 1.0:
        mesh.scale(scale, inplace=True)
    if offset != (0.0, 0.0, 0.0):
        mesh.translate(offset, inplace=True)
    return mesh


def _configure(verify_image_cache):
    """Widen thresholds so these tests flag structural breakage, not GPU jitter."""
    verify_image_cache.error_value = 1000.0
    verify_image_cache.warning_value = 500.0


def test_image_default_view(verify_image_cache):
    """Asymmetric mesh rendered with the default camera must match the baseline."""
    _configure(verify_image_cache)

    r = OffScreenRenderer(_asymmetric_mesh(), window_size=(300, 300))
    r.render_frame()
    r._plotter.close()  # Triggers pytest-pyvista's before_close_callback comparison.


def test_image_mesh_with_large_bounds(verify_image_cache):
    """Regression for the bf217fd camera-reset bug.

    Before the fix, this mesh (bounds in the thousands) rendered as a
    uniform background colour because ``show()`` consumed the plotter's
    first-time camera reset before ``add_mesh`` ran.  The cached
    baseline contains the correctly-framed letter ``F``.
    """
    _configure(verify_image_cache)

    mesh = _asymmetric_mesh(scale=1000.0, offset=(5000.0, 5000.0, 5000.0))
    r = OffScreenRenderer(mesh, window_size=(300, 300))
    r.render_frame()
    r._plotter.close()  # Triggers pytest-pyvista's before_close_callback comparison.


def test_image_wireframe(verify_image_cache):
    """Wireframe mode draws edges only — distinctive from the surface baseline."""
    _configure(verify_image_cache)

    r = OffScreenRenderer(_asymmetric_mesh(), window_size=(300, 300), wireframe=True)
    r.render_frame()
    r._plotter.close()  # Triggers pytest-pyvista's before_close_callback comparison.


def test_image_cpos_xy(verify_image_cache):
    """cpos='xy' must produce the front-on view (F legible, not mirrored).

    With an asymmetric mesh, the baseline is sensitive to camera
    orientation — a wrong-axis view is not the same image.
    """
    _configure(verify_image_cache)

    r = OffScreenRenderer(_asymmetric_mesh(), window_size=(300, 300), cpos='xy')
    r.render_frame()
    r._plotter.close()  # Triggers pytest-pyvista's before_close_callback comparison.


def test_image_cpos_yz(verify_image_cache):
    """cpos='yz' must produce a side view of the F — distinct from xy/xz."""
    _configure(verify_image_cache)

    r = OffScreenRenderer(_asymmetric_mesh(), window_size=(300, 300), cpos='yz')
    r.render_frame()
    r._plotter.close()  # Triggers pytest-pyvista's before_close_callback comparison.
