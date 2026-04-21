from __future__ import annotations

from pathlib import Path

from PIL import Image
import pytest
import pyvista as pv

from pyvista_tui.cli._commands import render_compare, render_gallery, render_gif, render_multi
from pyvista_tui.renderer import prepare_mesh


def _asymmetric_mesh() -> pv.PolyData:
    """Return a mesh that looks different from every axis."""
    return pv.Cone()


# --- render_gallery ---


def test_render_gallery_saves_to_disk(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    prepared = prepare_mesh(mesh_or_path=_asymmetric_mesh())
    mesh_path = str(tmp_path / 'cone.vtk')
    _asymmetric_mesh().save(mesh_path)
    render_gallery(
        prepared,
        mesh_path=mesh_path,
        width=100,
        height=80,
        save=True,
    )
    assert (tmp_path / 'cone_gallery.png').exists()


def test_render_gallery_no_crash_without_save(tmp_path):
    prepared = prepare_mesh(mesh_or_path=_asymmetric_mesh())
    mesh_path = str(tmp_path / 'cone.vtk')
    _asymmetric_mesh().save(mesh_path)
    render_gallery(
        prepared,
        mesh_path=mesh_path,
        width=100,
        height=80,
        save=False,
    )


# --- render_gif ---


def test_render_gif_creates_gif(tmp_path):
    prepared = prepare_mesh(mesh_or_path=_asymmetric_mesh())
    out = str(tmp_path / 'turntable.gif')
    render_gif(
        prepared,
        output_path=out,
        width=80,
        height=60,
    )
    assert Path(out).exists()
    with Image.open(out) as img:
        assert img.format == 'GIF'


def test_render_gif_is_animated(tmp_path):
    prepared = prepare_mesh(mesh_or_path=_asymmetric_mesh())
    out = str(tmp_path / 'turntable.gif')
    render_gif(
        prepared,
        output_path=out,
        width=80,
        height=60,
    )
    with Image.open(out) as img:
        assert img.n_frames > 1


# --- render_compare ---


def test_render_compare_no_crash(tmp_path):
    prepared = prepare_mesh(mesh_or_path=_asymmetric_mesh())
    compare_path = str(tmp_path / 'cube.vtk')
    pv.Cube().save(compare_path)
    render_compare(
        prepared,
        compare_path=compare_path,
        width=100,
        height=80,
    )


# --- render_multi ---


def test_render_multi_grid_saves_composited_png(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    prepared = [
        prepare_mesh(mesh_or_path=pv.Cone()),
        prepare_mesh(mesh_or_path=pv.Cube()),
    ]
    render_multi(
        prepared,
        labels=['cone', 'cube'],
        width=120,
        height=90,
        save=True,
    )

    out = tmp_path / 'multi_cone.png'
    assert out.exists()
    with Image.open(out) as img:
        # Two tiles in a 2-col x 1-row grid
        assert img.width == 240
        assert img.height == 90


def test_render_multi_sequential_saves_one_png_per_mesh(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    prepared = [
        prepare_mesh(mesh_or_path=pv.Cone()),
        prepare_mesh(mesh_or_path=pv.Cube()),
    ]
    render_multi(
        prepared,
        labels=['cone', 'cube'],
        width=120,
        height=90,
        sequential=True,
        save=True,
    )

    assert (tmp_path / 'cone.png').exists()
    assert (tmp_path / 'cube.png').exists()
    assert not (tmp_path / 'multi_cone.png').exists()


def test_render_multi_rejects_zero_meshes():
    with pytest.raises(ValueError, match='at least one mesh'):
        render_multi([], labels=[], width=100, height=80)


def test_render_multi_rejects_label_length_mismatch():
    prepared = [prepare_mesh(mesh_or_path=pv.Cone())]
    with pytest.raises(ValueError, match='labels length'):
        render_multi(prepared, labels=['a', 'b'], width=100, height=80)


def test_render_multi_text_theme_no_crash():
    prepared = [
        prepare_mesh(mesh_or_path=pv.Cone(), theme='braille'),
        prepare_mesh(mesh_or_path=pv.Cube(), theme='braille'),
    ]
    render_multi(
        prepared,
        labels=['cone', 'cube'],
        width=100,
        height=80,
        theme='braille',
    )
