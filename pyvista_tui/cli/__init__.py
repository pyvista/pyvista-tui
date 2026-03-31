"""CLI application for pyvista-tui."""

from __future__ import annotations

import atexit
import logging
from pathlib import Path
import sys
import tempfile
from typing import Annotated, Literal

from cyclopts import App, Group, Parameter
import pyvista as pv
from rich.console import Console

from pyvista_tui import __version__
from pyvista_tui.cli._commands import (
    pick_scalars as _pick_scalars,
    render_compare,
    render_gallery,
    render_gif,
    watch_file,
)
from pyvista_tui.display import launch_interactive, render_inline
from pyvista_tui.effects import THEME_REGISTRY
from pyvista_tui.renderer import prepare_mesh
from pyvista_tui.terminal import query_background_color
from pyvista_tui.tui.boot import boot_sequence
from pyvista_tui.utils.loader import MeshLoader

app = App(
    name='pyvista-tui',
    help_format='md',
    version=__version__,
    help_on_error=True,
    console=Console(),
)


@app.command(name='report', help='Print full PyVista system report and exit.')
def _report() -> None:
    extra: list[str] = [
        'textual',
        'textual_image',
        'cyclopts',
        'pyvista_tui',
    ]
    app.console.print(
        str(pv.Report(additional=extra)),  # type: ignore[arg-type]
    )


_MODE = Group('Mode', sort_key=0)
_STYLE = Group('Style', sort_key=1)
_ANIMATION = Group('Animation (implies -i)', sort_key=2)
_RENDER = Group('Rendering', sort_key=3)
_OUTPUT = Group('Output', sort_key=4)

#: Explicit Literal kept in sync with :data:`THEME_REGISTRY` by test.
#: mypy cannot handle ``Literal[tuple(THEME_REGISTRY)]`` because the
#: argument is computed at runtime.
ThemeChoice = Literal[
    'default',
    'retro',
    'matrix',
    'braille',
    'crt',
    'blueprint',
    'phosphor',
    'amber',
    'thermal',
]

_THEME_HELP = 'Rendering theme.\n\n' + '\n'.join(
    f'- **{name}** -- {info.description}' for name, info in THEME_REGISTRY.items()
)


@app.default
def main(
    mesh: Annotated[
        str,
        Parameter(help='Mesh file readable by pyvista.read().'),
    ],
    *,
    # Mode
    interactive: Annotated[
        bool,
        Parameter(('-i',), help='Interactive camera control.', group=_MODE),
    ] = False,
    debug: Annotated[
        bool,
        Parameter(
            help='Enable debug logging to pyvista-tui.log.',
            group=_MODE,
        ),
    ] = False,
    # Style
    theme: Annotated[
        ThemeChoice,
        Parameter(('-t',), help=_THEME_HELP, group=_STYLE),
    ] = 'default',
    boot: Annotated[
        bool,
        Parameter(
            help='Show the retro boot sequence (always on in interactive mode).',
            group=_STYLE,
        ),
    ] = False,
    # Animation
    spin: Annotated[
        bool,
        Parameter(help='Auto-rotate turntable.', group=_ANIMATION),
    ] = False,
    bounce: Annotated[
        bool,
        Parameter(help='DVD screensaver bounce.', group=_ANIMATION),
    ] = False,
    # Rendering
    wireframe: Annotated[
        bool,
        Parameter(help='Start in wireframe mode.', group=_RENDER),
    ] = False,
    scalars: Annotated[
        str | None,
        Parameter(help='Scalars array to color by.', group=_RENDER),
    ] = None,
    pick_scalars: Annotated[
        bool,
        Parameter(
            help='Interactively choose scalars from the mesh.',
            group=_RENDER,
        ),
    ] = False,
    color: Annotated[
        str | None,
        Parameter(help='Mesh color (e.g. "red", "#33cc66").', group=_RENDER),
    ] = None,
    cmap: Annotated[
        str | None,
        Parameter(
            help='Colormap for scalars (e.g. "viridis").',
            group=_RENDER,
        ),
    ] = None,
    clim: Annotated[
        list[float] | None,
        Parameter(
            help='Scalar range [min, max].',
            consume_multiple=True,
            group=_RENDER,
        ),
    ] = None,
    opacity: Annotated[
        float | None,
        Parameter(help='Mesh opacity (0.0-1.0).', group=_RENDER),
    ] = None,
    show_edges: Annotated[
        bool,
        Parameter(help='Show mesh edges on surface.', group=_RENDER),
    ] = False,
    edge_color: Annotated[
        str | None,
        Parameter(help='Edge color (e.g. "black", "#00e5ff").', group=_RENDER),
    ] = None,
    center: Annotated[
        bool,
        Parameter(
            help='Center and normalize mesh to fill viewport.',
            group=_RENDER,
        ),
    ] = False,
    smooth_shading: Annotated[
        bool,
        Parameter(help='Enable smooth shading.', group=_RENDER),
    ] = False,
    point_size: Annotated[
        float | None,
        Parameter(help='Point size for point clouds.', group=_RENDER),
    ] = None,
    line_width: Annotated[
        float | None,
        Parameter(help='Line width for wireframe/edges.', group=_RENDER),
    ] = None,
    log_scale: Annotated[
        bool,
        Parameter(
            help='Use logarithmic scaling for scalars.',
            group=_RENDER,
        ),
    ] = False,
    watch: Annotated[
        bool,
        Parameter(
            help='Watch file for changes and auto-reload.',
            group=_MODE,
        ),
    ] = False,
    rainbow: Annotated[
        bool,
        Parameter(
            help='Rainbow wireframe (colors by Z coordinate).',
            group=_STYLE,
        ),
    ] = False,
    save: Annotated[
        bool,
        Parameter(help='Save rendered image as PNG.', group=_OUTPUT),
    ] = False,
    gallery: Annotated[
        bool,
        Parameter(
            help='Render 6 axis-aligned views as a 2x3 grid.',
            group=_OUTPUT,
        ),
    ] = False,
    rotate_gif: Annotated[
        str | None,
        Parameter(
            help='Save a 360-degree turntable as animated GIF.',
            group=_OUTPUT,
        ),
    ] = None,
    compare: Annotated[
        str | None,
        Parameter(
            help='Compare with a second mesh side-by-side.',
            group=_OUTPUT,
        ),
    ] = None,
    export_ascii: Annotated[
        str | None,
        Parameter(help='Export ASCII art to a text file.', group=_OUTPUT),
    ] = None,
    width: Annotated[
        int | None,
        Parameter(help='Render width in pixels.', group=_RENDER),
    ] = None,
    height: Annotated[
        int | None,
        Parameter(help='Render height in pixels.', group=_RENDER),
    ] = None,
    background: Annotated[
        str | None,
        Parameter(
            help='Background color (e.g. "white", "#1e1e1e").',
            group=_RENDER,
        ),
    ] = None,
) -> None:
    """Render a 3D mesh in the terminal."""
    if debug:
        logging.basicConfig(
            filename='pyvista-tui.log',
            level=logging.DEBUG,
            format='%(asctime)s %(name)s %(levelname)s %(message)s',
        )

    # Read mesh data from stdin when mesh is '-'
    if mesh == '-':
        data = sys.stdin.buffer.read()
        with tempfile.NamedTemporaryFile(suffix='.vtk', delete=False) as tmp:
            tmp.write(data)
            mesh = tmp.name
        atexit.register(Path(mesh).unlink, missing_ok=True)

    # Validate mutually exclusive output modes
    exclusive = [gallery, rotate_gif is not None, compare is not None]
    if sum(exclusive) > 1:
        msg = '--gallery, --rotate-gif, and --compare are mutually exclusive.'
        raise SystemExit(msg)

    if spin or bounce:
        interactive = True

    # Auto-detect terminal background color before Textual takes over stdin
    if background is None:
        background = query_background_color()

    # Boot sequence is always shown in interactive mode, opt-in for static
    show_boot = boot or interactive

    # Start loading the mesh in a background thread so I/O overlaps
    # with the boot sequence animation
    loader = MeshLoader(mesh)

    if show_boot and not interactive:
        boot_sequence(Console(), mesh, loader=loader)

    if pick_scalars:
        scalars = _pick_scalars(loader, app.console)

    # Prepare the mesh with all rendering options in one call
    prepared = prepare_mesh(
        mesh,
        loader=loader,
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

    render_width = width or 1024
    render_height = height or 576

    if interactive:
        launch_interactive(
            prepared,
            mesh_path=mesh,
            width=width,
            height=height,
            background=background,
            loader=loader,
            theme=theme,
            spin=spin,
            bounce=bounce,
            show_boot=show_boot,
        )
    elif gallery:
        render_gallery(
            prepared,
            mesh_path=mesh,
            width=render_width,
            height=render_height,
            background=background,
            save=save,
        )
    elif rotate_gif is not None:
        render_gif(
            prepared,
            output_path=rotate_gif,
            width=render_width,
            height=render_height,
            background=background,
        )
    elif compare is not None:
        render_compare(
            prepared,
            compare_path=compare,
            width=render_width,
            height=render_height,
            background=background,
            theme=theme,
            rainbow=rainbow,
        )
    else:
        render_inline(
            prepared,
            width=render_width,
            height=render_height,
            background=background,
            theme=theme,
            export_ascii=export_ascii,
            save=Path(mesh).stem + '.png' if save else None,
            filename=Path(mesh).stem + '.png',
        )

        if watch:
            watch_file(
                mesh,
                prepared,
                width=render_width,
                height=render_height,
                background=background,
                theme=theme,
                export_ascii=export_ascii,
                save=save,
                center=center,
            )
