"""Plain geometry of the TBIM models for the visualizations (CPython only, no Revit).

Coordinates are in centimetres, as in the Topologic models.
"""
import os

from topologicpy.CellComplex import CellComplex
from topologicpy.Face import Face
from topologicpy.Topology import Topology
from topologicpy.Vertex import Vertex

from tbim import paths, tbimjson, topo

# CellComplex models of the workflow, from the most to the least complete
MODELS = [
    ("InstanceBIM", paths.CC_IBIM),
    ("TopologicalBIM", paths.CC_TBIM),
    ("Informational Styles", paths.CC_STYLES),
    ("Thermal zones", paths.CC_LOADS_CLUSTERIZED),
    ("Informational Loads", paths.CC_LOADS),
    ("Informational Controllers", paths.CC_CONTROLLERS),
]


def available_models():
    """[(label, path)] of the CellComplex models in the data folder."""
    return [(label, paths.data_file(name)) for label, name in MODELS if os.path.isfile(paths.data_file(name))]


def _loop(face):
    return [Vertex.Coordinates(v) for v in Topology.Vertices(Face.ExternalBoundary(face))]


def faces(cc):
    """[(UID, topological type, properties, boundary)] of the faces."""
    out = []
    for face_type, group in topo.face_groups(cc):
        for face in group:
            props = topo.props(face)
            out.append((props.get("UID"), props.get("pr_TopologicalType", face_type), props, _loop(face)))
    return out


def cells(cc, shrink=1.0):
    """[(UID, properties, [face boundaries])] of the cells, scaled by ``shrink`` about their centroid."""
    out = []
    for cell in CellComplex.Cells(cc):
        c = Vertex.Coordinates(Topology.Centroid(cell))
        loops = [[[c[i] + (p[i] - c[i]) * shrink for i in range(3)] for p in _loop(f)] for f in Topology.Faces(cell)]
        out.append((topo.cell_uid(cell), topo.props(cell), loops))
    return out


def apertures(path):
    """[(properties, boundary)] of the apertures of a TBIM JSON file."""
    return tbimjson.aperture_polygons(path)


def graph(cc, aperture_props=()):
    """Dual graph of the cells. Return (nodes, edges).

    nodes: [(UID, point, properties)]; edges: [(UID a, UID b, kind)] with kind
    'door' (shared face hosting a door), 'wall' (other vertical face) or 'slab'.
    """
    door_faces = set(p.get("rl_HasLocation_inFC") for p in aperture_props if p.get("pr_TopologicalType") == "door")
    nodes = [(topo.cell_uid(c), Vertex.Coordinates(topo.interior_point(c)), topo.props(c))
             for c in CellComplex.Cells(cc)]
    edges = []
    for face_type, group in topo.face_groups(cc):
        if not face_type.startswith("int"):
            continue
        for face in group:
            uids = [topo.cell_uid(c) for c in topo.adjacent_cells(face, cc)]
            if len(uids) != 2:
                continue
            if topo.get(face, "UID") in door_faces:
                kind = "door"
            else:
                kind = "wall" if face_type == "intVer" else "slab"
            edges.append((uids[0], uids[1], kind))
    return nodes, edges
