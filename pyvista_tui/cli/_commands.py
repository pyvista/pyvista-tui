"""CLI-specific output mode helpers (gallery, GIF, compare, watch, pick scalars)."""

from __future__ import annotations

import math
from pathlib import Path
import shutil
import time
from typing import TYPE_CHECKING

from PIL import Image as PILImage, ImageDraw
from rich.console import Console
from rich.prompt import Prompt

from pyvista_tui.display import display_frame, render_inline
from pyvista_tui.effects import apply_theme_effect, text_mode_for_theme
from pyvista_tui.renderer import OffScreenRenderer, ViewAxis, prepare_mesh, resolve_mesh
from pyvista_tui.terminal import PROBE_ERRORS, load_textual_image_class, try_iterm2_inline
from pyvista_tui.utils.text import image_to_ascii, image_to_braille, image_to_matrix

if TYPE_CHECKING:
    from pyvista_tui.renderer import CposString, PreparedMesh
    from pyvista_tui.utils.loader import MeshLoader


def render_gallery(
    prepared: PreparedMesh,
    *,
    mesh_path: str,
    width: int,
    height: int,
    background: str | None = None,
    theme: str = 'default',
    save: bool = False,
    export_ascii: str | None = None,
) -> None:
    """Render 6 axis-aligned views as a 2x3 grid image.

    For text-mode themes (braille, retro, matrix, etc.) each view is
    rendered at full size and printed sequentially with a label.  For
    image-mode themes the views are composited into a 2x3 grid.

    Parameters
    ----------
    prepared : PreparedMesh
        Mesh and rendering config.

    mesh_path : str
        Original file path (for output filename).

    width : int
        Render width in pixels.

    height : int
        Render height in pixels.

    background : str or None, optional
        Background color.

    theme : str, default: 'default'
        Rendering theme.

    save : bool, default: ``False``
        Save the grid image as PNG.

    export_ascii : str or None, optional
        Path to export text gallery. Only used with text-mode themes.

    """
    # Engineering-convention axis-aligned views (Z-up for sides,
    # Y-up for top/bottom). See ViewAxis vs CposString in renderer.py.
    view_labels: dict[ViewAxis, str] = {
        'x': '+X (Right)',
        '-x': '-X (Left)',
        'y': '+Y (Back)',
        '-y': '-Y (Front)',
        'z': '+Z (Top)',
        '-z': '-Z (Bottom)',
    }
    text_mode = text_mode_for_theme(theme)

    with OffScreenRenderer(
        prepared.mesh,
        window_size=(width, height),
        wireframe=prepared.wireframe,
        background=background,
        use_terminal_theme=prepared.use_terminal_theme,
        mesh_kwargs=prepared.mesh_kwargs,
    ) as renderer:
        tiles: list[PILImage.Image] = []
        for view_axis in view_labels:
            renderer.set_view(view_axis)
            tiles.append(apply_theme_effect(renderer.render_frame(), theme))

    console = Console()

    if text_mode != 'normal':
        # Text-mode themes: print each view at full size with a label
        export_lines: list[str] = []
        for view_axis, tile in zip(view_labels, tiles, strict=True):
            label = view_labels[view_axis]
            console.print(f'\n[bold cyan]── {label} ──[/bold cyan]')
            display_frame(tile, console, theme=theme)
            if export_ascii is not None:
                export_lines.append(f'── {label} ──')
                if text_mode == 'braille':
                    export_lines.append(str(image_to_braille(tile, width=80, height=40)))
                elif text_mode == 'matrix':
                    export_lines.append(str(image_to_matrix(tile, width=80, height=40)))
                else:
                    export_lines.append(str(image_to_ascii(tile, width=80, height=40)))
                export_lines.append('')

        if export_ascii is not None:
            out = Path(export_ascii)
            out.write_text('\n'.join(export_lines))
            console.print(f'[dim]Exported gallery text: {out.resolve()}[/dim]')
    else:
        # Image-mode themes: composite into a 2x3 grid
        tile_w, tile_h = tiles[0].size
        grid = PILImage.new('RGBA', (tile_w * 3, tile_h * 2))
        for idx, tile in enumerate(tiles):
            col = idx % 3
            row = idx // 3
            grid.paste(tile, (col * tile_w, row * tile_h))

        term_cols = shutil.get_terminal_size().columns
        filename = Path(mesh_path).stem + '_gallery.png'
        if not try_iterm2_inline(grid, filename, term_cols):
            term_image_cls = load_textual_image_class()
            rendered = False
            if term_image_cls is not None:
                try:
                    console.print(term_image_cls(grid, width=term_cols, height='auto'))
                    rendered = True
                except PROBE_ERRORS:
                    pass
            if not rendered:
                console.print(image_to_ascii(grid, width=term_cols, height=term_cols // 2))

        if save:
            out_path = Path(mesh_path).stem + '_gallery.png'
            grid.save(out_path, format='PNG')
            console.print(f'[dim]Saved: {Path(out_path).resolve()}[/dim]')


def render_compare(
    prepared: PreparedMesh,
    *,
    compare_path: str,
    width: int,
    height: int,
    background: str | None = None,
    theme: str = 'default',
    rainbow: bool = False,
    cpos: CposString | None = None,
) -> None:
    """Render two meshes side-by-side for comparison.

    Parameters
    ----------
    prepared : PreparedMesh
        Primary mesh and rendering config.

    compare_path : str
        Path to the second mesh file.

    width : int
        Render width in pixels per mesh.

    height : int
        Render height in pixels.

    background : str or None, optional
        Background color.

    theme : str, default: 'default'
        Rendering theme.

    rainbow : bool, default: ``False``
        Whether rainbow mode is active for the compare mesh.

    cpos : CposString or None, optional
        Initial camera position string applied to both renderers. See
        :meth:`~pyvista_tui.renderer.OffScreenRenderer.set_cpos` for
        the accepted values.

    """
    with OffScreenRenderer(
        prepared.mesh,
        window_size=(width, height),
        wireframe=prepared.wireframe,
        background=background,
        use_terminal_theme=prepared.use_terminal_theme,
        mesh_kwargs=prepared.mesh_kwargs,
        cpos=cpos,
    ) as renderer:
        frame = renderer.render_frame()

    compare_mesh = resolve_mesh(compare_path, rainbow=rainbow)
    with OffScreenRenderer(
        compare_mesh,
        window_size=(width, height),
        wireframe=prepared.wireframe,
        background=background,
        use_terminal_theme=prepared.use_terminal_theme,
        mesh_kwargs=prepared.mesh_kwargs,
        cpos=cpos,
    ) as renderer2:
        frame2 = renderer2.render_frame()

    combined = PILImage.new(
        'RGBA',
        (frame.width + frame2.width, frame.height),
    )
    combined.paste(frame, (0, 0))
    combined.paste(frame2, (frame.width, 0))
    combined = apply_theme_effect(combined, theme)

    console = Console()
    display_frame(combined, console, theme=theme, full_width=True)


def render_multi(
    prepared_meshes: list[PreparedMesh],
    labels: list[str],
    *,
    width: int,
    height: int,
    background: str | None = None,
    theme: str = 'default',
    cpos: CposString | None = None,
    sequential: bool = False,
    save: bool = False,
) -> None:
    """Render multiple meshes at a shared camera position.

    Two layouts are supported:

    - **Grid** (default for image themes): each mesh is rendered once
      and composited into a square-ish grid with the supplied label
      drawn on each tile.
    - **Sequential** (``sequential=True`` or for text-mode themes):
      each mesh is rendered full-size via
      :func:`~pyvista_tui.display.render_inline` with its label printed
      first — the same pipeline the single-mesh CLI path uses.

    Parameters
    ----------
    prepared_meshes : list[PreparedMesh]
        Meshes and per-mesh render config produced by
        :func:`~pyvista_tui.renderer.prepare_mesh`.  Must be non-empty
        and the same length as ``labels``.

    labels : list[str]
        Label drawn on each tile or printed as a header in sequential
        mode (typically the file stem).

    width : int
        Render width in pixels per tile or per frame.

    height : int
        Render height in pixels per tile or per frame.

    background : str or None, optional
        Background color shared across all meshes.

    theme : str, default: 'default'
        Rendering theme.

    cpos : CposString or None, optional
        Camera position string applied to every mesh.  See
        :meth:`~pyvista_tui.renderer.OffScreenRenderer.set_cpos` for
        accepted values.

    sequential : bool, default: ``False``
        If ``True``, render each mesh full-size one after another
        instead of tiling them into a grid.  Always ``True`` for
        text-mode themes regardless of this flag.

    save : bool, default: ``False``
        Save to PNG.  Grid mode writes a single ``multi_<first>.png``;
        sequential mode writes one ``<label>.png`` per mesh.

    """
    if not prepared_meshes:
        msg = 'render_multi requires at least one mesh.'
        raise ValueError(msg)
    if len(prepared_meshes) != len(labels):
        msg = (
            f'labels length ({len(labels)}) must match '
            f'prepared_meshes length ({len(prepared_meshes)}).'
        )
        raise ValueError(msg)

    console = Console()
    text_mode = text_mode_for_theme(theme)

    if sequential or text_mode != 'normal':
        for prepared, label in zip(prepared_meshes, labels, strict=True):
            console.print(f'\n[bold cyan]── {label} ──[/bold cyan]')
            render_inline(
                prepared,
                width=width,
                height=height,
                background=background,
                theme=theme,
                save=f'{label}.png' if save else None,
                filename=f'{label}.png',
                cpos=cpos,
            )
        return

    # Grid path: pre-render all tiles, then composite.
    tiles: list[PILImage.Image] = []
    for prepared in prepared_meshes:
        with OffScreenRenderer(
            prepared.mesh,
            window_size=(width, height),
            wireframe=prepared.wireframe,
            background=background,
            use_terminal_theme=prepared.use_terminal_theme,
            mesh_kwargs=prepared.mesh_kwargs,
            cpos=cpos,
        ) as renderer:
            tiles.append(apply_theme_effect(renderer.render_frame(), theme))

    cols = math.ceil(math.sqrt(len(tiles)))
    rows = math.ceil(len(tiles) / cols)
    tile_w, tile_h = tiles[0].size
    grid = PILImage.new('RGBA', (tile_w * cols, tile_h * rows))
    for idx, (label, tile) in enumerate(zip(labels, tiles, strict=True)):
        _draw_tile_label(tile, label)
        col = idx % cols
        row = idx // cols
        grid.paste(tile, (col * tile_w, row * tile_h))

    term_cols = shutil.get_terminal_size().columns
    filename = f'multi_{labels[0]}.png'
    if not try_iterm2_inline(grid, filename, term_cols):
        term_image_cls = load_textual_image_class()
        rendered = False
        if term_image_cls is not None:
            try:
                console.print(term_image_cls(grid, width=term_cols, height='auto'))
                rendered = True
            except PROBE_ERRORS:
                pass
        if not rendered:
            console.print(image_to_ascii(grid, width=term_cols, height=term_cols // 2))

    if save:
        grid.save(filename, format='PNG')
        console.print(f'[dim]Saved: {Path(filename).resolve()}[/dim]')


def _draw_tile_label(tile: PILImage.Image, label: str) -> None:
    """Draw a filename label onto the top-left corner of a tile.

    Mutates ``tile`` in place with a dark backdrop + white text so it
    stays legible over any background.
    """
    draw = ImageDraw.Draw(tile)
    padding = 4
    # textbbox requires a font; default font is fine for short stems
    left, top, right, bottom = draw.textbbox((padding, padding), label)
    draw.rectangle(
        (left - padding, top - padding, right + padding, bottom + padding),
        fill=(0, 0, 0, 180),
    )
    draw.text((padding, padding), label, fill=(255, 255, 255, 255))


def render_gif(
    prepared: PreparedMesh,
    *,
    output_path: str,
    width: int,
    height: int,
    background: str | None = None,
) -> None:
    """Render a 360-degree turntable and save as animated GIF.

    Parameters
    ----------
    prepared : PreparedMesh
        Mesh and rendering config.

    output_path : str
        Output GIF file path.

    width : int
        Render width in pixels.

    height : int
        Render height in pixels.

    background : str or None, optional
        Background color.

    """
    n_frames = 36
    azimuth_step = 2 * math.pi / n_frames

    with OffScreenRenderer(
        prepared.mesh,
        window_size=(width, height),
        wireframe=prepared.wireframe,
        background=background,
        use_terminal_theme=prepared.use_terminal_theme,
        mesh_kwargs=prepared.mesh_kwargs,
    ) as renderer:
        gif_frames: list[PILImage.Image] = []
        for _ in range(n_frames):
            gif_frames.append(renderer.render_frame())
            renderer.rotate(azimuth_step, 0)

    rgb_frames = [f.convert('RGB') for f in gif_frames]
    rgb_frames[0].save(
        output_path,
        save_all=True,
        append_images=rgb_frames[1:],
        duration=100,
        loop=0,
    )
    console = Console()
    console.print(f'[dim]Saved GIF: {Path(output_path).resolve()}[/dim]')


def watch_file(
    mesh_path: str,
    prepared: PreparedMesh,
    *,
    width: int,
    height: int,
    background: str | None = None,
    theme: str = 'default',
    export_ascii: str | None = None,
    save: bool = False,
    center: bool = False,
) -> None:
    """Poll a mesh file for changes and re-render on modification.

    Parameters
    ----------
    mesh_path : str
        Path to the mesh file to watch.

    prepared : PreparedMesh
        Initial rendering config (mesh will be reloaded on change).

    width : int
        Render width in pixels.

    height : int
        Render height in pixels.

    background : str or None, optional
        Background color.

    theme : str, default: 'default'
        Rendering theme.

    export_ascii : str or None, optional
        ASCII export path.

    save : bool, default: ``False``
        Save PNG on each reload.

    center : bool, default: ``False``
        Center reloaded meshes.

    """
    last_mtime = Path(mesh_path).stat().st_mtime
    try:
        while True:
            time.sleep(2)
            current_mtime = Path(mesh_path).stat().st_mtime
            if current_mtime != last_mtime:
                last_mtime = current_mtime
                reloaded = prepare_mesh(
                    mesh_path,
                    theme=theme,
                    center=center,
                )
                render_inline(
                    reloaded,
                    width=width,
                    height=height,
                    background=background,
                    theme=theme,
                    export_ascii=export_ascii,
                    save=Path(mesh_path).stem + '.png' if save else None,
                    filename=Path(mesh_path).stem + '.png',
                )
    except KeyboardInterrupt:
        pass


def pick_scalars(loader: MeshLoader, console: Console) -> str | None:
    """Prompt the user to select a scalars array from the mesh.

    Parameters
    ----------
    loader : MeshLoader
        Background mesh loader to get the mesh from.

    console : Console
        Rich console for prompts and output.

    Returns
    -------
    str or None
        Selected scalars name, or ``None`` for solid color.

    """
    mesh = loader.result()
    names = [f'{n} (point)' for n in mesh.point_data]
    names.extend(f'{n} (cell)' for n in mesh.cell_data)

    if not names:
        console.print(
            '[yellow]No scalars arrays found in mesh.[/yellow]',
        )
        return None

    console.print('[bold]Available scalars:[/bold]')
    for i, name in enumerate(names, 1):
        console.print(f'  [cyan]{i}[/cyan]. {name}')
    console.print('  [cyan]0[/cyan]. (none - solid color)')

    choice = Prompt.ask(
        'Select scalars',
        choices=[str(i) for i in range(len(names) + 1)],
        default='0',
        console=console,
    )
    idx = int(choice)
    if idx == 0:
        return None

    selected = names[idx - 1]
    return selected.rsplit(' (', 1)[0]
