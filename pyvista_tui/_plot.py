"""Plot PyVista meshes inline in the terminal."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pyvista_tui.display import launch_interactive, render_inline
from pyvista_tui.renderer import prepare_mesh

if TYPE_CHECKING:
    from pyvista import DataSet, MultiBlock


def plot(
    mesh: DataSet | MultiBlock,
    *,
    interactive: bool = False,
    window_size: tuple[int, int] | None = None,
    background: str | None = None,
    theme: str = 'default',
    scalars: str | None = None,
    cmap: str | None = None,
    clim: list[float] | None = None,
    color: str | None = None,
    opacity: float | None = None,
    wireframe: bool = False,
    show_edges: bool = False,
    edge_color: str | None = None,
    smooth_shading: bool = False,
    point_size: float | None = None,
    line_width: float | None = None,
    log_scale: bool = False,
    rainbow: bool = False,
    center: bool = False,
) -> None:
    """Plot a PyVista mesh inline in the terminal.

    Parameters
    ----------
    mesh : pyvista.DataSet or pyvista.MultiBlock
        The mesh to render.

    interactive : bool, default: ``False``
        If ``True``, launch the interactive TUI with keyboard controls.

    window_size : tuple[int, int] or None, optional
        Render resolution ``(width, height)`` in pixels.

    background : str or None, optional
        Background color (e.g. ``"white"``, ``"#1e1e1e"``).

    theme : str, default: 'default'
        Rendering theme.  One of ``'default'``, ``'retro'``,
        ``'matrix'``, ``'braille'``, ``'crt'``, ``'blueprint'``,
        ``'phosphor'``, ``'amber'``, ``'thermal'``.

    scalars : str or None, optional
        Name of a scalars array to color by.

    cmap : str or None, optional
        Colormap name for scalar coloring.

    clim : list[float] or None, optional
        Scalar range ``[min, max]``.

    color : str or None, optional
        Solid mesh color.

    opacity : float or None, optional
        Mesh opacity (0.0--1.0).

    wireframe : bool, default: ``False``
        Render in wireframe mode.

    show_edges : bool, default: ``False``
        Show mesh edges.

    edge_color : str or None, optional
        Color for mesh edges.

    smooth_shading : bool, default: ``False``
        Enable smooth (Phong) shading.

    point_size : float or None, optional
        Point size for point clouds.

    line_width : float or None, optional
        Line width for wireframe and edges.

    log_scale : bool, default: ``False``
        Logarithmic scalar scaling.

    rainbow : bool, default: ``False``
        Rainbow wireframe colored by Z coordinate.

    center : bool, default: ``False``
        Center and normalize the mesh to fill the viewport.

    """
    prepared = prepare_mesh(
        mesh,
        theme=theme,
        center=center,
        rainbow=rainbow,
        scalars=scalars,
        color=color,
        cmap=cmap,
        clim=clim,
        opacity=opacity,
        show_edges=show_edges,
        edge_color=edge_color,
        smooth_shading=smooth_shading,
        point_size=point_size,
        line_width=line_width,
        log_scale=log_scale,
    )

    # Caller may have set wireframe independently of rainbow
    if wireframe:
        prepared.wireframe = True

    if interactive:
        launch_interactive(
            prepared,
            width=window_size[0] if window_size else None,
            height=window_size[1] if window_size else None,
            background=background,
            theme=theme,
        )
    else:
        render_inline(
            prepared,
            width=window_size[0] if window_size else 1024,
            height=window_size[1] if window_size else 576,
            background=background,
            theme=theme,
        )
