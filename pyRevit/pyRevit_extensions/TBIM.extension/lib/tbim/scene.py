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


ADJACENCY, PASSAGE = "Adjacency graph", "Passage graph"
GRAPHS = [ADJACENCY, PASSAGE]
# occupancy types whose stacked cells are connected through the slab (stairs, lifts, cores)
VERTICAL_CIRCULATION = ("Stair", "Core", "Lift", "Elevator", "Ramp")
EXTERIOR = "Exterior"
EXTERIOR_OFFSET_CM = 150


def _vertical(occupancy):
    return any(word in (occupancy or "") for word in VERTICAL_CIRCULATION)


def _centroid(loop):
    return [sum(p[i] for p in loop) / float(len(loop)) for i in range(3)]


def graph(cc, aperture_records=(), kind=ADJACENCY):
    """Graph of the cells. Return (nodes, edges).

    nodes: [(UID, point, properties)]; edges: [(UID a, UID b, kind)].

    - Adjacency graph: cells sharing a face, edge kind 'wall' (vertical face) or 'slab'.
    - Passage graph: where people can go from a cell to another: 'door' (internal face hosting a door),
      'stair' (slab between two stacked vertical-circulation cells, see VERTICAL_CIRCULATION) and
      'entrance' (external door), which links the cell to an exterior node 'Exterior-<door UID>' placed
      just outside the door.

    aperture_records: [(properties, boundary)] of the apertures (``apertures(path)``).
    """
    doors = dict((p.get("rl_HasLocation_inFC"), (p, loop)) for p, loop in aperture_records
                 if p.get("pr_TopologicalType") == "door")
    nodes = [(topo.cell_uid(c), Vertex.Coordinates(topo.interior_point(c)), topo.props(c))
             for c in CellComplex.Cells(cc)]
    edges = []
    for face_type, group in topo.face_groups(cc):
        for face in group:
            cells = topo.adjacent_cells(face, cc)
            uids = [topo.cell_uid(c) for c in cells]
            if kind == ADJACENCY:
                if face_type.startswith("int") and len(uids) == 2:
                    edges.append((uids[0], uids[1], "wall" if face_type == "intVer" else "slab"))
                continue
            door = doors.get(topo.get(face, "UID"))
            if face_type == "intVer" and len(uids) == 2 and door:
                edges.append((uids[0], uids[1], "door"))
            elif face_type == "intHor" and len(uids) == 2 and all(
                    _vertical(topo.get(c, "pr_OccupancyType")) for c in cells):
                edges.append((uids[0], uids[1], "stair"))
            elif face_type == "extVer" and len(uids) == 1 and door:
                props, loop = door
                normal = topo.outward_normal(face, cells[0])
                centre = _centroid(loop)
                point = [centre[i] + normal[i] * EXTERIOR_OFFSET_CM for i in range(3)]
                name = "%s-%s" % (EXTERIOR, props.get("UID"))
                nodes.append((name, point, {"UID": name, "pr_OccupancyType": EXTERIOR}))
                edges.append((uids[0], name, "entrance"))
    return nodes, edges
