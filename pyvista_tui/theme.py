"""PyVista plotting theme optimized for terminal rendering."""

from __future__ import annotations

from pyvista.plotting.themes import DarkTheme

__all__ = ['TerminalTheme']


class TerminalTheme(DarkTheme):
    """High-contrast PyVista theme optimized for terminal rendering.

    Neon colors on black, flat shading with strong edge lines, no
    specular highlights. Designed to produce clean, recognizable output
    with bold color separation at low terminal resolutions.

    This is a **PyVista plotting theme** that configures the VTK
    renderer. It is separate from the rendering :class:`~pyvista_tui.effects.Theme`
    enum which controls post-processing effects and text display modes.
    """

    def __init__(self) -> None:
        """Initialize the terminal theme."""
        super().__init__()
        self.name = 'terminal'

        # Near-black maximizes contrast
        self.background = '#0a0a0a'
        self.color = '#33cc66'

        # Edges improve wireframe legibility at low resolution
        self.show_edges = True
        self.edge_color = '#00b8d4'
        self.edge_opacity = 0.6

        self.cmap = 'cool'

        self.outline_color = '#00b8d4'
        self.nan_color = '#333333'
        self.above_range_color = '#ff3333'
        self.below_range_color = '#0066ff'
        self.floor_color = '#111111'

        self.font.color = '#66ddaa'

        self.axes.x_color = '#ff3333'
        self.axes.y_color = '#33cc66'
        self.axes.z_color = '#00aacc'

        # Flat shading produces crisp facets that map well to characters
        self.smooth_shading = False
        self.lighting_params.interpolation = 'flat'
        self.lighting_params.ambient = 0.3
        self.lighting_params.diffuse = 0.7
        self.lighting_params.specular = 0.0

        # Thicker lines survive downscaling to character resolution
        self.line_width = 2.0
        self.point_size = 6.0

        # Scalar bars are unreadable at terminal resolution
        self.show_scalar_bar = False

        # Silhouette reinforces object edges after text conversion
        self.silhouette.color = '#00b8d4'
        self.silhouette.line_width = 2
        self.silhouette.opacity = 0.4
