#!/usr/bin/env python3
"""Assemble private STL visuals in link frames; write only below the CAD directory."""
import argparse
from pathlib import Path
import struct

import yaml


def build_mesh(parts, origin, source, destination):
    """Combine a link's parts, translating millimetre vertices; normals and triangles are preserved."""
    triangles = bytearray()
    count = 0
    for part in parts:
        path = source / part['file']
        data = path.read_bytes()
        # Binary STL: 80-byte header, uint32 triangle count, then 50-byte triangle records.
        if len(data) < 84:
            raise ValueError(f'Incomplete binary STL: {path}')
        part_count = struct.unpack_from('<I', data, 80)[0]
        if len(data) != 84 + 50 * part_count:
            raise ValueError(f'Expected binary STL with complete triangles: {path}')
        offset = part.get('translation', [0.0, 0.0, 0.0])
        body = bytearray(data[84:])
        for start in range(0, len(body), 50):
            for vertex in range(3):
                # Each record starts with a 12-byte normal, then three 12-byte vertices.
                position = start + 12 + vertex * 12
                point = struct.unpack_from('<3f', body, position)
                struct.pack_into(
                    '<3f', body, position,
                    *(point[i] + offset[i] - origin[i] for i in range(3)),
                )
        triangles.extend(body)
        count += part_count
    header = b'Private Arctos visual mesh; millimetres; keep local'.ljust(80, b'\0')
    destination.write_bytes(header + struct.pack('<I', count) + triangles)
    print(f'{destination.name}: {count} triangles')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cad-root', type=Path, required=True,
                        help='Local version directory containing the 2.9.7 STL folder')
    parser.add_argument('--geometry', type=Path, required=True,
                        help='Path to arctos_description/config/geometry.yaml')
    args = parser.parse_args()
    geometry = yaml.safe_load(args.geometry.read_text())
    cad_root = args.cad_root.resolve()
    source = cad_root / '2.9.7'
    output = cad_root / 'urdf_meshes'
    output.mkdir(exist_ok=True)
    for name, link in geometry.items():
        build_mesh(link['meshes'], link['origin'], source, output / f'{name}.stl')
    print(f'Local mesh directory: {output}')


if __name__ == '__main__':
    main()
