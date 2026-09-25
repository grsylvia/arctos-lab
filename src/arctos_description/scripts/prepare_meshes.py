#!/usr/bin/env python3
"""Assemble private STL visuals in link frames; write only below the CAD directory."""

# Parse the CAD directory and geometry configuration arguments.
import argparse
# Handle source and output paths as filesystem objects.
from pathlib import Path
# Read and write the binary STL number fields.
import struct

# Load the link definitions from YAML.
import yaml


# Combine a link's source meshes in its own coordinate frame.
def build_mesh(parts, origin, source, destination):
    """Preserve STL normals and triangles, translating millimetre coordinates."""
    # Collect the translated binary triangle records.
    triangles = bytearray()
    # Track the combined triangle count for the output header.
    count = 0
    # Process every structural part assigned to this link.
    for part in parts:
        # Locate the original purchased STL.
        path = source / part['file']
        # Read the source mesh without changing it.
        data = path.read_bytes()
        # Require the 80-byte header and 4-byte triangle count.
        if len(data) < 84:
            # Identify the source file with an incomplete header.
            raise ValueError(f'Incomplete binary STL: {path}')
        # Decode the little-endian triangle count after the header.
        part_count = struct.unpack_from('<I', data, 80)[0]
        # Check that every declared triangle has a complete 50-byte record.
        if len(data) != 84 + 50 * part_count:
            # Reject ASCII or truncated data before translating vertices.
            raise ValueError(f'Expected binary STL with complete triangles: {path}')
        # Apply an assembly alignment correction only when configured.
        offset = part.get('translation', [0.0, 0.0, 0.0])
        # Copy triangle data into a buffer that can be edited.
        body = bytearray(data[84:])
        # Visit each triangle while retaining its normal and attributes.
        for start in range(0, len(body), 50):
            # Translate all three vertices of the triangle.
            for vertex in range(3):
                # Skip the normal and locate this vertex's three floats.
                position = start + 12 + vertex * 12
                # Decode the source vertex coordinates in millimetres.
                point = struct.unpack_from('<3f', body, position)
                # Replace the vertex coordinates in the copied record.
                struct.pack_into(
                    # Store three little-endian floats at the vertex offset.
                    '<3f', body, position,
                    # Align the part and subtract the link's assembly origin.
                    *(point[i] + offset[i] - origin[i] for i in range(3)),
                )
        # Append this part's translated triangles to the link mesh.
        triangles.extend(body)
        # Include this part in the output triangle count.
        count += part_count
    # Label the export as private and retain STL's 80-byte header size.
    header = b'Private Arctos visual mesh; millimetres; keep local'.ljust(80, b'\0')
    # Write the binary STL beside the local CAD assets.
    destination.write_bytes(header + struct.pack('<I', count) + triangles)
    # Report the generated mesh name and triangle count.
    print(f'{destination.name}: {count} triangles')


# Prepare one local STL export for each configured robot link.
def main():
    # Use the module description as the command's help text.
    parser = argparse.ArgumentParser(description=__doc__)
    # Require the purchased CAD version directory.
    parser.add_argument('--cad-root', type=Path, required=True,
                        # Explain which directory the user must supply.
                        help='Local version directory containing the 2.9.7 STL folder')
    # Require the configuration that assigns source meshes to links.
    parser.add_argument('--geometry', type=Path, required=True,
                        # Show the expected configuration file in command help.
                        help='Path to arctos_description/config/geometry.yaml')
    # Parse the supplied paths before accessing files.
    args = parser.parse_args()
    # Load plain YAML data without constructing Python objects.
    geometry = yaml.safe_load(args.geometry.read_text())
    # Resolve the CAD root to an absolute local path.
    cad_root = args.cad_root.resolve()
    # Select the STL subdirectory in the purchased v2.9.7 layout.
    source = cad_root / '2.9.7'
    # Keep generated meshes inside the private CAD directory.
    output = cad_root / 'urdf_meshes'
    # Create the export directory or reuse it on subsequent runs.
    output.mkdir(exist_ok=True)
    # Generate meshes in the configuration's link order.
    for name, link in geometry.items():
        # Translate and combine this link's configured parts.
        build_mesh(link['meshes'], link['origin'], source, output / f'{name}.stl')
    # Print the directory to pass to the Xacro model.
    print(f'Local mesh directory: {output}')


# Run the command only when this file is executed directly.
if __name__ == '__main__':
    # Start mesh preparation with the command-line arguments.
    main()
