"""Informational Controllers: the CellComplex built from the BReps (no Revit, CPython only).

Each BRep is a building block (a cluster of cells); the BReps are merged in a
CellComplex whose cells get a UID ('Cell<i>') and their building block.
"""
import os

from topologicpy.CellComplex import CellComplex
from topologicpy.Topology import Topology
from topologicpy.Vertex import Vertex

from tbim import topo


def block_name(path):
    return os.path.splitext(os.path.basename(path))[0]


def _centroid_key(cell):
    return tuple(round(c, 1) for c in Vertex.Coordinates(Topology.Centroid(cell)))


def build_cellcomplex(brep_paths):
    """Merge the BReps in a CellComplex; cells get UID 'Cell<i>' and their building block."""
    faces, blocks = [], []
    for path in brep_paths:
        topology = Topology.ByBREPPath(path)
        if topology is None:
            raise ValueError("Cannot read BRep %s (is topologic_core installed?)" % path)
        faces.extend(Topology.Faces(topology))
        blocks.append((block_name(path), Topology.Cells(topology)))
    # merging the cells is orders of magnitude faster than merging all their faces
    # (112 cells: 0.5 s instead of 5 min); faces are the fallback for open blocks
    cells = [c for _, block_cells in blocks for c in block_cells]
    cc = CellComplex.ByCells(cells, silent=True) if cells else None
    if cc is None or len(CellComplex.Cells(cc)) < len(cells):
        cc = CellComplex.ByFaces(faces)
    if cc is None:
        raise ValueError("The BReps do not form a CellComplex")
    # merged cells keep their geometry: match their centroid first (point-in-cell tests are slow)
    by_centroid = dict((_centroid_key(c), name) for name, block_cells in blocks for c in block_cells)
    for index, cell in enumerate(CellComplex.Cells(cc)):
        block = by_centroid.get(_centroid_key(cell))
        if block is None:
            point = topo.interior_point(cell)
            block = next((name for name, cells in blocks if any(Vertex.IsInternal(point, c) for c in cells)), "None")
        topo.update(cell, {"UID": "Cell%d" % index, "rl_HasLocation_tpBB": block})
    return cc


def storey_elevations(cc, ndigits=1):
    """Distinct elevations (cm) of the horizontal faces: floors, slabs and flat roofs.

    The vertices of inclined faces (e.g. ridges and hips of pitched roofs) do not make storeys.
    Without horizontal faces, the distinct vertex elevations are returned.
    """
    elevations = set()
    for face in CellComplex.Faces(cc):
        zmin, zmax = topo.z_range(face)
        if zmax - zmin < 0.1:
            elevations.add(round(zmin, ndigits))
    return sorted(elevations or set(round(Vertex.Z(v), ndigits) for v in CellComplex.Vertices(cc)))



def storey_name(elevation_cm):
    return "BuildingStorey_%dcm" % int(round(elevation_cm))


def assign_storeys(cc, elevations_cm):
    """Set rl_HasLocation_tpBS of each cell to the storey nearest to its base (as Collectors > Create)."""
    for cell in CellComplex.Cells(cc):
        zmin = topo.z_range(cell)[0]
        topo.update(cell, {"rl_HasLocation_tpBS": storey_name(min(elevations_cm, key=lambda z: abs(z - zmin)))})
