"""Emulate Loads > Assignment for the example projects: match the cells with json/rooms.json.

After Collectors > CellComplex > Create, each cell takes the occupancy type and the space id of the
room whose centre it contains (or of the nearest room centre). Writes
tbim_CellComplex_Loads-OccupancyTypes.json and json/space_names.txt
(``<cell UID>|<space id>|<room name>``, the names of the Revit spaces for InstanceBIM > ByTableOfSpaces).

    python tools/assign_rooms.py <project folder>
"""
import os
import sys

FOLDER = os.path.abspath(sys.argv[1])
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
sys.path.insert(0, os.path.join(ROOT, "pyRevit", "pyRevit_extensions", "TBIM.extension", "lib"))

from topologicpy.CellComplex import CellComplex  # noqa: E402
from topologicpy.Topology import Topology  # noqa: E402
from topologicpy.Vertex import Vertex  # noqa: E402

from tbim import ild, topo  # noqa: E402
from tbim.jsonio import read_json  # noqa: E402

DATA = os.path.join(FOLDER, "json")


def contains(cell, point):
    """True if ``point`` is inside ``cell`` (bounding box first, then the exact test)."""
    pts = [Vertex.Coordinates(v) for v in Topology.Vertices(cell)]
    if any(not min(p[i] for p in pts) < point[i] < max(p[i] for p in pts) for i in range(3)):
        return False
    return Vertex.IsInternal(Vertex.ByCoordinates(*point), cell)


def main():
    rooms = read_json(os.path.join(DATA, "rooms.json"))
    cc = topo.load_cellcomplex(os.path.join(DATA, "tbim_CellComplex_Controllers.json"))
    assignments, lines, used = {}, [], set()
    for cell in CellComplex.Cells(cc):
        c = Vertex.Coordinates(topo.interior_point(cell))
        inside = [r for r in rooms if contains(cell, r["center"])]
        room = min(inside or rooms, key=lambda r: sum((a - b) ** 2 for a, b in zip(c, r["center"])))
        uid = topo.cell_uid(cell)
        assignments[uid] = room["pr_OccupancyType"]
        lines.append("%s|%s|%s" % (uid, room["space"], room["name"]))
        used.add(room["space"])
    ild.save_assignments(assignments, os.path.join(DATA, "tbim_CellComplex_Loads-OccupancyTypes.json"))
    with open(os.path.join(DATA, "space_names.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("cells %d, rooms %d, rooms matched %d" % (len(assignments), len(rooms), len(used)))
    if len(used) != len(assignments):
        raise SystemExit("some cells share the same room: check rooms.json")


if __name__ == "__main__":
    main()
