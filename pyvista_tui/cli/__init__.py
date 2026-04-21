"""CLI application for pyvista-tui."""

from __future__ import annotations

import atexit
import logging
from pathlib import Path
import sys
import tempfile
import threading as _threading
from typing import Annotated, Literal

from cyclopts import App, Group, Parameter
from rich.console import Console

from pyvista_tui import __version__
from pyvista_tui.display import launch_interactive, render_inline
from pyvista_tui.effects import THEME_REGISTRY
from pyvista_tui.renderer import CposString, prepare_mesh
from pyvista_tui.terminal import query_background_color
from pyvista_tui.utils.loader import MeshLoader


def _prewarm_pyvista() -> None:
    """Start pyvista + pyvista.plotting imports on a background thread.

    ``pyvista.plotting`` contributes ~300 ms of import cost that
    otherwise sits on the main thread's critical path inside
    :meth:`OffScreenRenderer.__init__`.  Running it concurrently with
    cold-start cli imports + cyclopts parsing hides most of it behind
    work the main thread has to do anyway.  Best-effort -- if pyvista
    is missing, we let the main-thread path raise as usual.
    """
    try:
        import pyvista  # noqa: F401, PLC0415
        from pyvista.plotting.themes import DarkTheme  # noqa: F401, PLC0415
    except ImportError:  # pragma: no cover
        pass


def _should_prewarm(argv: list[str]) -> bool:
    """Return whether this invocation is likely to hit the render pipeline.

    We only fire the pre-warm thread when we are going to render: the
    VTK shared libraries it loads cannot be interrupted mid-import, and
    a daemon thread stuck in ``libvtk`` forces the interpreter to wait
    at shutdown -- which adds ~300 ms to ``pvtui --help``.
    """
    if len(argv) <= 1:
        return False
    rest = argv[1:]
    if any(a in {'-h', '--help', '--version'} for a in rest):
        return False
    # ``report`` is the one subcommand that needs pyvista, but it is
    # invoked rarely so hitting cold on it is acceptable.
    return rest[0] != 'report'


# Kick off the pre-warm thread at cli-module load time when we think we
# will need pyvista.  ``daemon=True`` lets the interpreter exit even if
# the thread is still running.
if _should_prewarm(sys.argv):
    _threading.Thread(target=_prewarm_pyvista, daemon=True).start()

# NOTE: every PLC0415-suppressed import in this module is an intentional
# startup-latency deferral.  ``pyvista``, ``rich.prompt.Confirm``,
# ``pyvista_tui.tui.boot`` and the ``_commands`` helpers are only used
# by specific CLI branches; importing them at module top forces
# ~440 ms of eager loading on every invocation -- including
# ``pvtui --help`` and ``--version``.  See ``profiling/STARTUP_PROFILE.md``.

MULTI_MESH_PROMPT_THRESHOLD = 6

app = App(
    name='pyvista-tui',
    help_format='md',
    version=__version__,
    help_on_error=True,
    console=Console(),
)


@app.command(name='report', help='Print full PyVista system report and exit.')
def _report() -> None:
    import pyvista as pv  # noqa: PLC0415

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
        list[str],
        Parameter(help='Mesh file(s) readable by pyvista.read().'),
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
    yes: Annotated[
        bool,
        Parameter(
            ('-y', '--yes'),
            help='Skip the confirmation prompt when many meshes are passed.',
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
        bool | None,
        Parameter(
            help=(
                'Composite into a grid. With one mesh: 6 axis-aligned views '
                'as a 2x3 grid (default off). With multiple meshes: tile all '
                'meshes into a grid at a shared camera position (default on; '
                'pass --no-gallery to render each full-size in sequence).'
            ),
            group=_OUTPUT,
        ),
    ] = None,
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
    cpos: Annotated[
        CposString | None,
        Parameter(
            help=(
                'Initial camera position. Any string supported by '
                "PyVista's `Plotter.camera_position`."
            ),
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

    # Read mesh data from stdin when a single '-' was passed
    if len(mesh) == 1 and mesh[0] == '-':
        data = sys.stdin.buffer.read()
        with tempfile.NamedTemporaryFile(suffix='.vtk', delete=False) as tmp:
            tmp.write(data)
            mesh[0] = tmp.name
        atexit.register(Path(mesh[0]).unlink, missing_ok=True)

    # Validate mutually exclusive output modes
    exclusive = [gallery is True, rotate_gif is not None, compare is not None]
    if sum(exclusive) > 1:
        msg = '--gallery, --rotate-gif, and --compare are mutually exclusive.'
        raise SystemExit(msg)

    render_width = width or 1024
    render_height = height or 576

    # Auto-detect terminal background color before Textual takes over stdin
    if background is None:
        background = query_background_color()

    if len(mesh) > 1:
        _reject_multi_mesh_flags(
            mesh,
            interactive=interactive,
            spin=spin,
            bounce=bounce,
            watch=watch,
            rotate_gif=rotate_gif,
            compare=compare,
            pick_scalars=pick_scalars,
            export_ascii=export_ascii,
        )
        if len(mesh) >= MULTI_MESH_PROMPT_THRESHOLD and not yes:
            from rich.prompt import Confirm  # noqa: PLC0415

            if not Confirm.ask(
                f'About to render {len(mesh)} meshes. Continue?',
                console=app.console,
                default=False,
            ):
                msg = 'Cancelled.'
                raise SystemExit(msg)

        prepared_list = [
            prepare_mesh(
                p,
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
            for p in mesh
        ]
        if wireframe:
            for prepared in prepared_list:
                prepared.wireframe = True

        # Multi-mesh default is the grid; --no-gallery opts out to sequential.
        use_gallery = True if gallery is None else gallery
        from pyvista_tui.cli._commands import render_multi  # noqa: PLC0415

        render_multi(
            prepared_list,
            labels=[Path(p).stem for p in mesh],
            width=render_width,
            height=render_height,
            background=background,
            theme=theme,
            cpos=cpos,
            sequential=not use_gallery,
            save=save,
        )
        return

    mesh_path = mesh[0]

    if spin or bounce:
        interactive = True

    # Boot sequence is always shown in interactive mode, opt-in for static
    show_boot = boot or interactive

    # Start loading the mesh in a background thread so I/O overlaps
    # with the boot sequence animation
    loader = MeshLoader(mesh_path)

    if show_boot and not interactive:
        from pyvista_tui.tui.boot import boot_sequence  # noqa: PLC0415

        boot_sequence(Console(), mesh_path, loader=loader)

    if pick_scalars:
        from pyvista_tui.cli._commands import pick_scalars as _pick_scalars  # noqa: PLC0415

        scalars = _pick_scalars(loader, app.console)

    # Prepare the mesh with all rendering options in one call
    prepared = prepare_mesh(
        mesh_path,
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

    if interactive:
        launch_interactive(
            prepared,
            mesh_path=mesh_path,
            width=width,
            height=height,
            background=background,
            loader=loader,
            theme=theme,
            spin=spin,
            bounce=bounce,
            show_boot=show_boot,
            cpos=cpos,
        )
    elif gallery:
        from pyvista_tui.cli._commands import render_gallery  # noqa: PLC0415

        render_gallery(
            prepared,
            mesh_path=mesh_path,
            width=render_width,
            height=render_height,
            background=background,
            theme=theme,
            save=save,
            export_ascii=export_ascii,
        )
    elif rotate_gif is not None:
        from pyvista_tui.cli._commands import render_gif  # noqa: PLC0415

        render_gif(
            prepared,
            output_path=rotate_gif,
            width=render_width,
            height=render_height,
            background=background,
        )
    elif compare is not None:
        from pyvista_tui.cli._commands import render_compare  # noqa: PLC0415

        render_compare(
            prepared,
            compare_path=compare,
            width=render_width,
            height=render_height,
            background=background,
            theme=theme,
            rainbow=rainbow,
            cpos=cpos,
        )
    else:
        render_inline(
            prepared,
            width=render_width,
            height=render_height,
            background=background,
            theme=theme,
            export_ascii=export_ascii,
            save=Path(mesh_path).stem + '.png' if save else None,
            filename=Path(mesh_path).stem + '.png',
            cpos=cpos,
        )

        if watch:
            from pyvista_tui.cli._commands import watch_file  # noqa: PLC0415

            watch_file(
                mesh_path,
                prepared,
                width=render_width,
                height=render_height,
                background=background,
                theme=theme,
                export_ascii=export_ascii,
                save=save,
                center=center,
            )


def _reject_multi_mesh_flags(
    mesh_paths: list[str],
    *,
    interactive: bool,
    spin: bool,
    bounce: bool,
    watch: bool,
    rotate_gif: str | None,
    compare: str | None,
    pick_scalars: bool,
    export_ascii: str | None,
) -> None:
    """Raise ``SystemExit`` if a flag with no multi-mesh meaning was passed."""
    unsupported: list[str] = []
    if interactive:
        unsupported.append('-i/--interactive')
    if spin:
        unsupported.append('--spin')
    if bounce:
        unsupported.append('--bounce')
    if watch:
        unsupported.append('--watch')
    if rotate_gif is not None:
        unsupported.append('--rotate-gif')
    if compare is not None:
        unsupported.append('--compare')
    if pick_scalars:
        unsupported.append('--pick-scalars')
    if export_ascii is not None:
        unsupported.append('--export-ascii')
    if '-' in mesh_paths:
        unsupported.append("stdin ('-')")
    if unsupported:
        msg = (
            f'The following options are not supported with multiple meshes: '
            f'{", ".join(unsupported)}.'
        )
        raise SystemExit(msg)
