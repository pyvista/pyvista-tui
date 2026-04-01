---
name: "pyvista-tui"
description: "Render a 3D mesh in the terminal using pyvista-tui and describe the visualization. Use when the user wants to visualize or inspect a mesh file (STL, VTK, PLY, OBJ, GLTF, etc.) directly in the terminal."
argument-hint: "[mesh-file] [optional instructions]"
---

# pyvista-tui: Terminal 3D Mesh Visualization

Render a 3D mesh file in the terminal as Unicode braille art so you can see and describe its contents.

## Steps

1. Identify the mesh file from the user's arguments. The file path may be provided as an `@`-reference or inline path. Supported formats: STL, VTK, VTP, VTU, PLY, OBJ, GLTF, GLB, and anything PyVista can read.

2. Render the mesh to a temporary text file using the Bash tool:

```
uv run pyvista-tui <mesh-file> -t braille --no-boot --width 800 --height 600 --export-ascii /tmp/pyvista-tui-render.txt
```

IMPORTANT: You must use `--export-ascii` to write the braille output to a file. Without it, the output may render as a terminal image protocol (Sixel/iTerm2) that you cannot read.

3. Read the exported text file using the Read tool:

```
Read /tmp/pyvista-tui-render.txt
```

The file contains Unicode braille characters that form a visual representation of the 3D mesh. Examine the shapes, contours, and structure visible in the braille pattern.

4. Describe what you see: the shape, geometry, features, symmetry, and any recognizable structures. If the user asked a specific question about the mesh (e.g., "does this look correct?", "what is this?"), answer it based on what you observe.

## Additional rendering options

You can add these flags for different views:

- `--scalars <name> --cmap <colormap>`: Color the mesh by a data array (e.g., stress, temperature)
- `--wireframe`: Render as wireframe to see the mesh topology
- `--show-edges`: Overlay edges on the surface
- `--center`: Center and normalize the mesh to fill the viewport

## Tips

- If the mesh appears too small or off-center, add `--center` to normalize it.
- If the mesh has scalar data arrays and you want to explore them, pass `--scalars <array-name>` directly.
- For complex geometry, render multiple times from different angles to build a complete picture.
