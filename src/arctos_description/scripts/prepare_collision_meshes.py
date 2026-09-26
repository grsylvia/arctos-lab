#!/usr/bin/env python3
"""Simplify local collision STLs while retaining the full-detail visual meshes."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy


def read_mesh(path):
    reader = vtk.vtkSTLReader()
    reader.SetFileName(str(path))
    reader.Update()
    mesh = reader.GetOutput()
    if not mesh.GetNumberOfCells():
        raise ValueError(f'Empty or unreadable mesh: {path}')
    return mesh


def topology(mesh):
    regions = vtk.vtkPolyDataConnectivityFilter()
    regions.SetInputData(mesh)
    regions.SetExtractionModeToAllRegions()
    regions.Update()
    edges = vtk.vtkFeatureEdges()
    edges.SetInputData(mesh)
    edges.FeatureEdgesOff()
    edges.ManifoldEdgesOff()
    edges.BoundaryEdgesOn()
    edges.NonManifoldEdgesOff()
    edges.Update()
    return regions.GetNumberOfExtractedRegions(), edges.GetOutput().GetNumberOfCells()


def deviation(original, simplified):
    # Check both directions at every vertex and triangle centre; this is a sampled bound.
    distance = vtk.vtkDistancePolyDataFilter()
    distance.SetInputData(0, original)
    distance.SetInputData(1, simplified)
    distance.SignedDistanceOff()
    distance.ComputeSecondDistanceOn()
    distance.ComputeCellCenterDistanceOn()
    distance.Update()
    return max(float(np.abs(vtk_to_numpy(data.GetArray('Distance'))).max())
               for index in (0, 1)
               for data in (distance.GetOutput(index).GetPointData(),
                            distance.GetOutput(index).GetCellData()))


def simplify(source, max_deviation):
    original = read_mesh(source)
    original_topology = topology(original)
    for error in (0.1, 0.03, 0.01, 0.003, 0.001):
        decimator = vtk.vtkDecimatePro()
        decimator.SetInputData(original)
        decimator.SetTargetReduction(0.98)
        decimator.PreserveTopologyOn()
        decimator.SplittingOff()
        decimator.BoundaryVertexDeletionOff()
        decimator.AccumulateErrorOn()
        decimator.SetErrorIsAbsolute(1)
        decimator.SetAbsoluteError(error)
        decimator.Update()
        candidate = decimator.GetOutput()
        measured = deviation(original, candidate)
        if measured <= max_deviation and topology(candidate) == original_topology:
            result = vtk.vtkPolyData()
            result.DeepCopy(candidate)
            return original, result, measured, error
    raise ValueError(f'Could not simplify {source.name} within {max_deviation} mm')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cad-root', type=Path, required=True)
    parser.add_argument('--max-deviation-mm', type=float, default=0.5)
    args = parser.parse_args()
    root = args.cad_root.resolve()
    if 'cad' not in root.parts or args.max_deviation_mm <= 0:
        parser.error('Use a local cad/ directory and a positive deviation limit')
    sources = sorted((root / 'urdf_meshes').glob('*_link.stl'))
    if len(sources) != 7:
        parser.error('Expected seven prepared structural link meshes')
    output = root / 'collision_meshes'
    output.mkdir(exist_ok=True)
    report = {'vtk_version': vtk.vtkVersion.GetVTKVersion(),
              'max_sampled_deviation_mm': args.max_deviation_mm, 'links': {}}
    prepared = []
    for source in sources:
        original, simplified, measured, error = simplify(source, args.max_deviation_mm)
        prepared.append((source, simplified))
        entry = {'original_triangles': original.GetNumberOfCells(),
                 'collision_triangles': simplified.GetNumberOfCells(),
                 'sampled_deviation_mm': measured, 'decimator_error': error,
                 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
        report['links'][source.stem] = entry
        print(f'{source.stem}: {entry["original_triangles"]} -> '
              f'{entry["collision_triangles"]} triangles; sampled deviation {measured:.3f} mm', flush=True)
    # Write derived assets only after all seven links have passed validation.
    for source, mesh in prepared:
        writer = vtk.vtkSTLWriter()
        writer.SetFileName(str(output / source.name))
        writer.SetFileTypeToBinary()
        writer.SetInputData(mesh)
        if writer.Write() != 1:
            raise RuntimeError(f'Failed to write {source.name}')
    (output / 'simplification_report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'Private collision meshes: {output}')


if __name__ == '__main__':
    main()
