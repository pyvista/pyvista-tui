"""Off-screen PyVista rendering with turntable camera control."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import TYPE_CHECKING, Literal

import numpy as np
from PIL import Image
import pyvista as pv

from pyvista_tui.effects import THEME_REGISTRY
from pyvista_tui.theme import TerminalTheme

if TYPE_CHECKING:
    from pyvista import Camera, DataSet, MultiBlock

    from pyvista_tui.utils.loader import MeshLoader


MAX_ELEVATION = math.pi / 2 - 0.008  # ~89.5 degrees, prevents pole-crossing
ZOOM_BASE = 1.03  # Exponential dolly factor per step

ViewAxis = Literal['x', 'y', 'z', '-x', '-y', '-z']

__all__ = [
    'OffScreenRenderer',
    'PreparedMesh',
    'ViewAxis',
    'apply_rainbow',
    'build_mesh_kwargs',
    'prepare_mesh',
    'resolve_mesh',
]


def _rotate_turntable(camera: Camera, d_azimuth: float, d_elevation: float) -> None:
    """Rotate the camera about the focal point in spherical coordinates.

    Parameters
    ----------
    camera : Camera
        The PyVista camera to manipulate.

    d_azimuth : float
        Azimuth delta in radians (positive = rotate left).

    d_elevation : float
        Elevation delta in radians (positive = rotate up).

    """
    pos = camera.position
    focal = camera.focal_point
    up = camera.up

    fx, fy, fz = focal
    px = pos[0] - fx
    py = pos[1] - fy
    pz = pos[2] - fz

    # Flip sign when camera is upside-down
    udf = -1 if up[2] < 0 else 1

    horiz = math.hypot(px, py)
    elev = math.atan2(pz, horiz)

    # Near poles the azimuth is ill-defined; derive from up-vector instead
    sin_elev = math.sin(elev)
    if abs(sin_elev) < 0.8:
        azi = math.atan2(py, px)
    elif sin_elev < -0.8:
        azi = math.atan2(udf * up[1], udf * up[0])
    else:
        azi = math.atan2(-udf * up[1], -udf * up[0])

    dist = math.sqrt(px * px + py * py + pz * pz)

    azi_new = azi + d_azimuth
    elev_new = elev + udf * d_elevation
    elev_new = max(-MAX_ELEVATION, min(MAX_ELEVATION, elev_new))

    cos_elev = math.cos(elev_new)
    sin_elev_new = math.sin(elev_new)
    cos_azi = math.cos(azi_new)
    sin_azi = math.sin(azi_new)

    horiz_new = dist * cos_elev
    new_px = horiz_new * cos_azi
    new_py = horiz_new * sin_azi
    new_pz = dist * sin_elev_new

    # Analytically orthogonal up-vector from elevation
    up_z = udf * cos_elev
    up_h = udf * sin_elev_new
    camera.up = (-up_h * cos_azi, -up_h * sin_azi, up_z)
    camera.position = (fx + new_px, fy + new_py, fz + new_pz)


def _apply_dolly(camera: Camera, step: float) -> None:
    """Apply exponential dolly to the camera.

    Parameters
    ----------
    camera : Camera
        The PyVista camera to manipulate.

    step : float
        Zoom step. Positive zooms out, negative zooms in.

    """
    factor = pow(ZOOM_BASE, step)
    if camera.parallel_projection:
        camera.parallel_scale *= factor
    else:
        pos = camera.position
        focal = camera.focal_point
        camera.position = (
            focal[0] + (pos[0] - focal[0]) * factor,
            focal[1] + (pos[1] - focal[1]) * factor,
            focal[2] + (pos[2] - focal[2]) * factor,
        )


def _pan_camera(camera: Camera, dx: float, dy: float) -> None:
    """Pan the camera in the image plane.

    Parameters
    ----------
    camera : Camera
        The PyVista camera to manipulate.

    dx : float
        Horizontal pan fraction (positive = right).

    dy : float
        Vertical pan fraction (positive = up).

    """
    pos = camera.position
    focal = camera.focal_point

    # Camera-to-focal distance for scaling
    dist = math.sqrt(
        (pos[0] - focal[0]) ** 2 + (pos[1] - focal[1]) ** 2 + (pos[2] - focal[2]) ** 2
    )

    # Get camera axes via VTK (view_plane_normal not exposed by PyVista)
    vpn = camera.GetViewPlaneNormal()
    vup = camera.up

    # Right vector = up x normal
    right = (
        vup[1] * vpn[2] - vup[2] * vpn[1],
        vup[2] * vpn[0] - vup[0] * vpn[2],
        vup[0] * vpn[1] - vup[1] * vpn[0],
    )

    # Scale by camera distance for consistent pan speed
    scale = dist * 0.5
    mx = (dx * right[0] + dy * vup[0]) * scale
    my = (dx * right[1] + dy * vup[1]) * scale
    mz = (dx * right[2] + dy * vup[2]) * scale

    camera.position = (pos[0] + mx, pos[1] + my, pos[2] + mz)
    camera.focal_point = (focal[0] + mx, focal[1] + my, focal[2] + mz)


def build_mesh_kwargs(
    *,
    scalars: str | None = None,
    color: str | None = None,
    cmap: str | None = None,
    clim: list[float] | None = None,
    opacity: float | None = None,
    show_edges: bool = False,
    edge_color: str | None = None,
    smooth_shading: bool = False,
    point_size: float | None = None,
    line_width: float | None = None,
    log_scale: bool = False,
) -> dict[str, object]:
    """Build keyword arguments for :func:`pyvista.Plotter.add_mesh`.

    Only explicitly-set values are included so that PyVista defaults
    are preserved for anything the caller did not specify.

    Returns
    -------
    dict[str, object]
        Keyword arguments suitable for ``pv.Plotter.add_mesh()``.

    """
    kwargs: dict[str, object] = {
        k: v
        for k, v in {
            'scalars': scalars,
            'color': color,
            'cmap': cmap,
            'clim': clim,
            'opacity': opacity,
            'edge_color': edge_color,
            'point_size': point_size,
            'line_width': line_width,
        }.items()
        if v is not None
    }
    kwargs['show_scalar_bar'] = False
    if show_edges:
        kwargs['show_edges'] = True
    if smooth_shading:
        kwargs['smooth_shading'] = True
    if log_scale:
        kwargs['log_scale'] = True
    return kwargs


def apply_rainbow(mesh_kwargs: dict[str, object]) -> dict[str, object]:
    """Apply rainbow wireframe settings to mesh kwargs.

    Parameters
    ----------
    mesh_kwargs : dict[str, object]
        Existing mesh keyword arguments to modify in place.

    Returns
    -------
    dict[str, object]
        The modified kwargs dict (same reference).

    """
    mesh_kwargs['scalars'] = '_rainbow'
    mesh_kwargs['cmap'] = 'gist_rainbow'
    return mesh_kwargs


def resolve_mesh(
    mesh_path: str = '',
    *,
    loader: MeshLoader | None = None,
    mesh: DataSet | MultiBlock | None = None,
    center: bool = False,
    rainbow: bool = False,
) -> DataSet | MultiBlock:
    """Load and prepare a mesh for rendering.

    Resolves the mesh from one of three sources (in-memory object,
    background loader, or file path), then optionally centers it and
    adds rainbow Z-coordinate scalars.

    Parameters
    ----------
    mesh_path : str, default: ''
        Path to a mesh file readable by :func:`pyvista.read`.
        Ignored when *mesh* or *loader* is provided.

    loader : MeshLoader or None, optional
        Background mesh loader.  Ignored when *mesh* is provided.

    mesh : pyvista.DataSet or None, optional
        In-memory mesh object.  Takes highest priority.

    center : bool, default: ``False``
        Center the mesh at the origin.

    rainbow : bool, default: ``False``
        Add a ``'_rainbow'`` scalars array colored by Z-coordinate.

    Returns
    -------
    DataSet or MultiBlock
        The prepared mesh, ready for rendering.

    """
    result: DataSet | MultiBlock
    if mesh is not None:
        result = mesh
    elif loader is not None:
        result = loader.result()
    else:
        result = pv.read(mesh_path)  # type: ignore[assignment]

    # Center and rainbow require point-level access (DataSet only)
    if not isinstance(result, pv.MultiBlock):
        if center:
            result = result.copy()  # type: ignore[assignment]
            result.points -= result.center  # type: ignore[misc]

        if rainbow:
            result['_rainbow'] = result.points[:, 2]

    return result


@dataclass(slots=True)
class PreparedMesh:
    """Result of :func:`prepare_mesh` bundling the mesh with render config.

    Parameters
    ----------
    mesh : pyvista.DataSet
        The prepared mesh (centered, with rainbow scalars if requested).

    mesh_kwargs : dict[str, object]
        Keyword arguments for :func:`pyvista.Plotter.add_mesh`.

    wireframe : bool
        Whether to render in wireframe mode.

    use_terminal_theme : bool
        Whether to use the high-contrast terminal theme.

    """

    mesh: DataSet | MultiBlock
    mesh_kwargs: dict[str, object]
    wireframe: bool
    use_terminal_theme: bool


def prepare_mesh(
    mesh_or_path: DataSet | MultiBlock | str = '',
    *,
    loader: MeshLoader | None = None,
    theme: str = 'default',
    center: bool = False,
    rainbow: bool = False,
    scalars: str | None = None,
    color: str | None = None,
    cmap: str | None = None,
    clim: list[float] | None = None,
    opacity: float | None = None,
    show_edges: bool = False,
    edge_color: str | None = None,
    smooth_shading: bool = False,
    point_size: float | None = None,
    line_width: float | None = None,
    log_scale: bool = False,
) -> PreparedMesh:
    """Resolve, prepare, and bundle a mesh with its rendering config.

    This is the single entry point that replaces the duplicated
    preamble in both the CLI ``main()`` and the Python ``plot()`` API.

    Parameters
    ----------
    mesh_or_path : pyvista.DataSet or str, default: ''
        In-memory mesh or file path.

    loader : MeshLoader or None, optional
        Background mesh loader.

    theme : str, default: 'default'
        Rendering theme name (looked up in
        :data:`~pyvista_tui.effects.THEME_REGISTRY`).

    center : bool, default: ``False``
        Center the mesh at the origin.

    rainbow : bool, default: ``False``
        Rainbow wireframe colored by Z-coordinate.

    scalars : str or None, optional
        Scalars array name.

    color : str or None, optional
        Solid mesh color.

    cmap : str or None, optional
        Colormap name.

    clim : list[float] or None, optional
        Scalar range ``[min, max]``.

    opacity : float or None, optional
        Mesh opacity (0.0--1.0).

    show_edges : bool, default: ``False``
        Show mesh edges.

    edge_color : str or None, optional
        Edge color.

    smooth_shading : bool, default: ``False``
        Enable smooth shading.

    point_size : float or None, optional
        Point size for point clouds.

    line_width : float or None, optional
        Line width for wireframe/edges.

    log_scale : bool, default: ``False``
        Logarithmic scalar scaling.

    Returns
    -------
    PreparedMesh
        Bundle of the prepared mesh, kwargs, and rendering flags.

    """
    mesh_kwargs = build_mesh_kwargs(
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

    wireframe = False
    if rainbow:
        wireframe = True
        apply_rainbow(mesh_kwargs)

    info = THEME_REGISTRY[theme]

    if isinstance(mesh_or_path, str):
        mesh = resolve_mesh(
            mesh_or_path,
            loader=loader,
            center=center,
            rainbow=rainbow,
        )
    else:
        mesh = resolve_mesh(
            mesh=mesh_or_path,
            center=center,
            rainbow=rainbow,
        )

    return PreparedMesh(
        mesh=mesh,
        mesh_kwargs=mesh_kwargs,
        wireframe=wireframe,
        use_terminal_theme=info.use_terminal_theme,
    )


class OffScreenRenderer:
    """Off-screen PyVista plotter that captures frames as PIL Images.

    Wraps a :class:`pyvista.Plotter` in off-screen mode and provides
    turntable camera control, frame caching via a dirty flag, and
    context-manager support for safe resource cleanup.

    Parameters
    ----------
    mesh : pyvista.DataSet
        The mesh to render.  Use :func:`resolve_mesh` to load and
        prepare the mesh before constructing the renderer.

    window_size : tuple[int, int], default: (800, 600)
        Render resolution in pixels ``(width, height)``.

    wireframe : bool, default: ``False``
        If ``True``, start in wireframe representation.

    background : str or None, optional
        Background color name or hex string.  When ``None``, the
        background is transparent so the terminal shows through.

    use_terminal_theme : bool, default: ``False``
        If ``True``, apply :class:`~pyvista_tui.theme.TerminalTheme`.
        If ``False``, use PyVista's built-in ``'dark'`` theme.

    mesh_kwargs : dict[str, object] or None, optional
        Extra keyword arguments forwarded to
        :func:`pyvista.Plotter.add_mesh`.

    """

    def __init__(
        self,
        mesh: DataSet | MultiBlock,
        window_size: tuple[int, int] = (800, 600),
        *,
        wireframe: bool = False,
        background: str | None = None,
        use_terminal_theme: bool = False,
        mesh_kwargs: dict[str, object] | None = None,
    ) -> None:
        theme = TerminalTheme() if use_terminal_theme else pv.themes.DarkTheme()
        self._plotter = pv.Plotter(
            off_screen=True,
            window_size=list(window_size),
            theme=theme,
        )

        # Prevent a macOS dock icon from appearing for off-screen renders.
        # This will land upstream in pyvista/pyvista#8423.
        ren_win = self._plotter.render_window
        if ren_win is not None and hasattr(ren_win, 'SetConnectContextToNSView'):
            ren_win.SetConnectContextToNSView(False)

        # PyVista's ColorLike type is broader than mypy can express
        if background is not None:
            self._plotter.set_background(background)  # type: ignore[arg-type]
            self._transparent = False
        else:
            self._plotter.set_background([0, 0, 0, 0])  # type: ignore[arg-type]
            self._transparent = True

        is_multiblock = isinstance(mesh, pv.MultiBlock)

        kwargs = dict(mesh_kwargs) if mesh_kwargs else {}
        kwargs.setdefault('show_scalar_bar', False)
        kwargs.setdefault('show_edges', False)
        if is_multiblock:
            kwargs.setdefault('multi_colors', True)
        else:
            kwargs['style'] = 'wireframe' if wireframe else 'surface'

            # Validate scalars if specified (not applicable to MultiBlock)
            scalars = kwargs.get('scalars')
            if scalars is not None:
                all_names = [*mesh.point_data.keys(), *mesh.cell_data.keys()]
                if scalars not in all_names:
                    msg = (
                        f'Scalars {scalars!r} not found. '
                        f'Available: {", ".join(all_names) or "(none)"}'
                    )
                    raise ValueError(msg)

        self._actor = self._plotter.add_mesh(mesh, **kwargs)  # type: ignore[arg-type]
        self._mesh: DataSet | MultiBlock = mesh
        self._wireframe = wireframe
        self._show_edges = False

        # Build list of scalar arrays for cycling (skip multi-component).
        # MultiBlock has no point_data/cell_data, so scalars cycling is
        # not supported for composite datasets.
        self._scalars_names: list[str] = []
        if not is_multiblock:
            self._scalars_names = [
                name
                for name in [*mesh.point_data.keys(), *mesh.cell_data.keys()]
                if mesh[name].ndim == 1
            ]
        self._scalars_index: int = -1

        # Initialize the render window (creates OpenGL context)
        self._plotter.show(auto_close=False)

        self._dirty = True
        self._last_frame: Image.Image | None = None

    def __enter__(self) -> OffScreenRenderer:
        """Return self for use as a context manager."""
        return self

    def __exit__(self, *exc: object) -> None:
        """Close the plotter on context exit."""
        self.close()

    @property
    def is_dirty(self) -> bool:
        """Return whether the scene needs re-rendering.

        Returns
        -------
        bool
            ``True`` if a camera or scene change has occurred since the
            last call to :meth:`render_frame`.

        """
        return self._dirty

    @property
    def wireframe(self) -> bool:
        """Return whether wireframe mode is active.

        Returns
        -------
        bool
            ``True`` if rendering in wireframe mode.

        """
        return self._wireframe

    @property
    def show_edges(self) -> bool:
        """Return whether edge visibility is enabled.

        Returns
        -------
        bool
            ``True`` if edges are visible.

        """
        return self._show_edges

    def mark_dirty(self) -> None:
        """Mark the scene as needing re-rendering."""
        self._dirty = True

    def render_frame(self) -> Image.Image:
        """Render the current scene and return a PIL Image.

        Returns
        -------
        Image.Image
            The rendered frame.

        """
        if not self._dirty and self._last_frame is not None:
            return self._last_frame

        self._plotter.render()
        img_array = self._plotter.screenshot(
            return_img=True,
            transparent_background=self._transparent,
        )
        frame = Image.fromarray(img_array)  # type: ignore[arg-type]
        self._last_frame = frame
        self._dirty = False
        return frame

    def rotate(self, d_azimuth: float, d_elevation: float) -> None:
        """Rotate the camera using turntable spherical coordinates.

        Parameters
        ----------
        d_azimuth : float
            Azimuth change in radians (positive = rotate left).

        d_elevation : float
            Elevation change in radians (positive = rotate up).

        """
        _rotate_turntable(self._plotter.camera, d_azimuth, d_elevation)
        self._plotter.renderer.reset_camera_clipping_range()
        self._dirty = True

    def pan(self, dx: float, dy: float) -> None:
        """Pan the camera in the image plane.

        Parameters
        ----------
        dx : float
            Horizontal pan fraction.

        dy : float
            Vertical pan fraction.

        """
        _pan_camera(self._plotter.camera, dx, dy)
        self._dirty = True

    def zoom(self, step: float) -> None:
        """Zoom the camera via exponential dolly.

        Parameters
        ----------
        step : float
            Zoom step. Positive zooms out, negative zooms in.

        """
        _apply_dolly(self._plotter.camera, step)
        self._plotter.renderer.reset_camera_clipping_range()
        self._dirty = True

    def reset_camera(self) -> None:
        """Reset the camera to show all actors."""
        # PyVista's _Wrapped decorator confuses mypy's call-arg analysis
        self._plotter.reset_camera()  # type: ignore[call-arg]
        self._dirty = True

    def toggle_wireframe(self) -> None:
        """Toggle between wireframe and surface representation."""
        self._wireframe = not self._wireframe
        self._actor.prop.style = 'wireframe' if self._wireframe else 'surface'
        self._dirty = True

    def toggle_edges(self) -> None:
        """Toggle edge visibility on the actor."""
        self._show_edges = not self._show_edges
        self._actor.prop.show_edges = self._show_edges
        self._dirty = True

    def cycle_scalars(self) -> None:
        """Cycle through available data arrays for scalar coloring."""
        if not self._scalars_names:
            return
        self._scalars_index = (self._scalars_index + 1) % len(self._scalars_names)
        name = self._scalars_names[self._scalars_index]

        # Set active scalars on the mesh and update the mapper range.
        # This replaces the deprecated ``Plotter.update_scalars``.
        # _scalars_names is only populated for DataSet (not MultiBlock),
        # so self._mesh is guaranteed to be a DataSet here.
        self._mesh.set_active_scalars(name)  # type: ignore[union-attr]
        mapper = self._actor.mapper
        arr = np.asarray(self._mesh[name])
        mapper.scalar_range = (float(arr.min()), float(arr.max()))
        mapper.SetScalarModeToUsePointFieldData()
        mapper.SelectColorArray(name)
        self._dirty = True

    def set_view(self, axis: ViewAxis) -> None:
        """Set the camera to an axis-aligned view.

        Parameters
        ----------
        axis : str
            One of ``'x'``, ``'y'``, ``'z'``, ``'-x'``, ``'-y'``,
            or ``'-z'``.

        """
        camera = self._plotter.camera

        # Direction vectors for each axis-aligned view
        directions: dict[ViewAxis, tuple[float, float, float]] = {
            'x': (1, 0, 0),
            '-x': (-1, 0, 0),
            'y': (0, 1, 0),
            '-y': (0, -1, 0),
            'z': (0, 0, 1),
            '-z': (0, 0, -1),
        }
        d = directions[axis]
        center = self._mesh.center

        # Place camera along the axis, then let VTK fit the view
        camera.focal_point = center
        camera.position = (center[0] + d[0], center[1] + d[1], center[2] + d[2])
        camera.up = (0, 1, 0) if axis in ('z', '-z') else (0, 0, 1)

        # reset_camera fits the view, then zoom in slightly to reduce
        # the padding VTK leaves around the bounding box
        # PyVista's _Wrapped decorator confuses mypy's call-arg analysis
        self._plotter.reset_camera()  # type: ignore[call-arg]
        _apply_dolly(camera, -3)
        self._plotter.renderer.reset_camera_clipping_range()
        self._dirty = True

    def toggle_projection(self) -> None:
        """Toggle between perspective and parallel projection."""
        camera = self._plotter.camera
        camera.parallel_projection = not camera.parallel_projection
        self._dirty = True

    def mesh_info(self) -> str:
        """Return a summary string of the loaded mesh.

        Returns
        -------
        str
            Summary with point count, cell count, and array count.

        """
        m = self._mesh
        if isinstance(m, pv.MultiBlock):
            return f'blocks:{m.n_blocks} datasets:{len(m.keys())}'
        return f'pts:{m.n_points:,} cells:{m.n_cells:,} arrays:{m.n_arrays}'

    def render_depth(self) -> Image.Image:
        """Render the depth buffer as a grayscale PIL Image.

        Returns
        -------
        Image.Image
            Grayscale image where near surfaces are white and far
            surfaces are dark.

        """
        self._plotter.render()
        depth = np.array(self._plotter.get_image_depth(), dtype=np.float64)

        # VTK returns NaN for background pixels
        valid = ~np.isnan(depth)
        if valid.any():
            lo = float(depth[valid].min())
            hi = float(depth[valid].max())
            if hi > lo:
                depth[valid] = 1.0 - (depth[valid] - lo) / (hi - lo)
            else:
                depth[valid] = 1.0
        depth[~valid] = 0.0

        normalized = (depth * 255).astype(np.uint8)
        self._dirty = False
        return Image.fromarray(normalized)

    def save_screenshot(self, path: str = 'screenshot.png') -> None:
        """Save the current frame to a file.

        Parameters
        ----------
        path : str, default: 'screenshot.png'
            Output file path.

        """
        self._plotter.screenshot(path)

    def resize(self, width: int, height: int) -> None:
        """Resize the render window.

        Parameters
        ----------
        width : int
            New width in pixels.

        height : int
            New height in pixels.

        """
        self._plotter.window_size = (width, height)
        self._dirty = True

    def close(self) -> None:
        """Close the plotter and release resources."""
        self._plotter.close()
