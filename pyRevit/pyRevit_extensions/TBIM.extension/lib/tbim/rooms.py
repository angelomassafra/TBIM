"""Room table: occupancy types and space ids of the cells from a list of rooms (CPython only, no Revit).

``json/tbim_Rooms.json`` lists the rooms of the building with a point inside each of them (cm)::

    [{"center": [x, y, z], "pr_OccupancyType": "Education:Classroom", "space": "0.01", "name": "Classroom 1A"}]

Each cell takes the room whose point it contains (or the nearest one). This is Loads > Assignment > From
Table: the occupancy types go to the assignments and the space ids to the names of the Revit spaces, the
key of InstanceBIM > ByTableOfSpaces.
"""
from topologicpy.CellComplex import CellComplex
from topologicpy.Topology import Topology
from topologicpy.Vertex import Vertex

from tbim import topo


def contains(cell, point):
    """True if ``point`` is inside ``cell`` (bounding box first, then the exact test)."""
    pts = [Vertex.Coordinates(v) for v in Topology.Vertices(cell)]
    if any(not min(p[i] for p in pts) < point[i] < max(p[i] for p in pts) for i in range(3)):
        return False
    return Vertex.IsInternal(Vertex.ByCoordinates(*point), cell)


def match(cc, rooms):
    """{cell UID: room} for every cell of ``cc``. Return (matches, cells sharing a room with another cell)."""
    matches = {}
    for cell in CellComplex.Cells(cc):
        c = Vertex.Coordinates(topo.interior_point(cell))
        inside = [r for r in rooms if contains(cell, r["center"])]
        matches[topo.cell_uid(cell)] = min(inside or rooms,
                                           key=lambda r: sum((a - b) ** 2 for a, b in zip(c, r["center"])))
    used = {}
    for uid, room in matches.items():
        used.setdefault(room["space"], []).append(uid)
    shared = sorted(uid for uids in used.values() if len(uids) > 1 for uid in uids)
    return matches, shared


def assignments(matches):
    """{cell UID: occupancy type}."""
    return dict((uid, room["pr_OccupancyType"]) for uid, room in matches.items())


def space_ids(matches):
    """{cell UID: space id} (the name of the Revit space, read by InstanceBIM > ByTableOfSpaces)."""
    return dict((uid, room["space"]) for uid, room in matches.items())
