"""TBIM inputs of an anonymized residential building of the mid 1960s (northern Italy).

Source: archive drawings of the building permit (plans 1:100, elevations, section).
Geometry in centimetres, x along the 22.00 m front, y along the 14.30 m depth, z from the
basement floor:

- Basement (garages, boiler room)      z    0 -  280
- 5 residential storeys, 3.00 m         z  280 - 1780  (raised floor + 4 typical storeys)
- hipped clay-tile roof (30 %)          z 1780 - 1995, stair turret up to 2080

Each storey of the typical plan has two flats beside the central stair: one cell per room.

    python make_model.py     # writes 3d/*.brep and the json inputs of the project
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, os.pardir, os.pardir, "pyRevit", "pyRevit_extensions", "TBIM.extension", "lib")
sys.path.insert(0, os.path.abspath(LIB))

from topologicpy.Cell import Cell  # noqa: E402
from topologicpy.CellComplex import CellComplex  # noqa: E402
from topologicpy.Face import Face  # noqa: E402
from topologicpy.Topology import Topology  # noqa: E402
from topologicpy.Vertex import Vertex  # noqa: E402

import tbim  # noqa: E402,F401  (adds the TBIM site-packages)

W, D = 2200.0, 1430.0                  # footprint
Z_BASEMENT, Z_RAISED, H = 0.0, 280.0, 300.0
STOREYS = 5
Z_TOP = Z_RAISED + STOREYS * H         # 1780: floor of the attic
ROOF_RISE = 215.0                      # 30 % slope over half the depth (715)
Z_TURRET = Z_TOP + 300.0               # top of the stair turret
STAIR = (700, 1665, 540, 890)          # x0, x1, y0, y1 of the stair core (stair + lift)

# Plan of the typical storey: (key, x0, x1, y0, y1, occupancy, flat) - from the 1:100 plan
TYPICAL = [
    ("living", 0, 565, 0, 450, "Residential:LivingRoom", "A"),
    ("kitchen", 565, 875, 0, 540, "Residential:Kitchen", "A"),
    ("bedroom1", 0, 420, 450, 880, "Residential:Bedroom", "A"),
    ("bath1", 0, 420, 880, 1050, "Support:Bathroom", "A"),
    ("bedroom2", 0, 420, 1050, 1430, "Residential:Bedroom", "A"),
    ("hallway", 420, 565, 450, 1050, "Circulation:PrivateHallway", "A"),
    ("entry", 565, 700, 540, 890, "Circulation:PrivateHallway", "A"),
    ("bath2", 420, 565, 1050, 1430, "Support:Bathroom", "A"),
    ("bedroom3", 565, 908, 890, 1430, "Residential:Bedroom", "A"),
    ("stair", 700, 1665, 540, 890, "Circulation:Stair", "-"),
    ("living", 875, 1270, 0, 540, "Residential:LivingRoom", "B"),
    ("kitchen", 1270, 1665, 0, 390, "Residential:Kitchen", "B"),
    ("entry", 1270, 1665, 390, 540, "Circulation:PrivateHallway", "B"),
    ("bedroom1", 1665, 2200, 0, 390, "Residential:Bedroom", "B"),
    ("bath1", 1665, 2200, 390, 560, "Support:Bathroom", "B"),
    ("bedroom2", 1665, 2200, 560, 890, "Residential:Bedroom", "B"),
    ("bedroom3", 908, 1255, 890, 1430, "Residential:Bedroom", "B"),
    ("corridor", 1255, 1835, 890, 1035, "Circulation:PrivateHallway", "B"),
    ("bath2", 1255, 1430, 1035, 1430, "Support:Bathroom", "B"),
    ("bedroom4", 1430, 1835, 1035, 1430, "Residential:Bedroom", "B"),
    ("dining", 1835, 2200, 890, 1430, "Residential:LivingRoom", "B"),
]
BASEMENT = [
    ("garage", 0, 2200, 0, 540, "Parking:Garage", "-"),
    ("garage_west", 0, 700, 540, 890, "Parking:Garage", "-"),
    ("stair", 700, 1665, 540, 890, "Circulation:Stair", "-"),
    ("garage_north", 0, 1665, 890, 1430, "Parking:Garage", "-"),
    ("boiler_room", 1665, 2200, 540, 1430, "Technical:BoilerRoom", "-"),
]
FINISHES = {"Residential:LivingRoom": "Marble-chip terrazzo", "Residential:Bedroom": "Marble-chip terrazzo",
            "Residential:Kitchen": "Stoneware tiles", "Support:Bathroom": "Ceramic tiles",
            "Circulation:PrivateHallway": "Marble-chip terrazzo", "Circulation:Stair": "Marble",
            "Circulation:EntranceHall": "Marble", "Parking:Garage": "Stoneware tiles",
            "Technical:BoilerRoom": "Concrete", "Unconditioned:Attic": "Cement screed"}


def box(x0, x1, y0, y1, z0, z1):
    return Cell.Prism(origin=Vertex.ByCoordinates((x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0),
                      width=x1 - x0, length=y1 - y0, height=z1 - z0)


def hipped_roof():
    """Attic under a hipped roof (hips at 45 degrees in plan), with the stair turret cut out."""
    v = Vertex.ByCoordinates
    a, b, c, d = v(0, 0, Z_TOP), v(W, 0, Z_TOP), v(W, D, Z_TOP), v(0, D, Z_TOP)
    r1, r2 = v(D / 2, D / 2, Z_TOP + ROOF_RISE), v(W - D / 2, D / 2, Z_TOP + ROOF_RISE)
    faces = [Face.ByVertices([a, d, c, b]), Face.ByVertices([a, b, r2, r1]), Face.ByVertices([c, d, r1, r2]),
             Face.ByVertices([d, a, r1]), Face.ByVertices([b, c, r2])]
    attic = Cell.ByFaces(faces)
    turret = box(STAIR[0], STAIR[1], STAIR[2], STAIR[3], Z_TOP, Z_TURRET)
    cut = Topology.Difference(attic, turret)
    cells = Topology.Cells(cut) if not Topology.IsInstance(cut, "Cell") else [cut]
    return max(cells, key=Cell.Volume), turret


def write_brep(cells, name):
    cc = CellComplex.ByCells(cells) if len(cells) > 1 else cells[0]
    path = os.path.join(HERE, "3d", name + ".brep")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Topology.ExportToBREP(cc, path, overwrite=True)
    return path, len(Topology.Cells(cc))


def write(name, data):
    with open(os.path.join(HERE, "json", name), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def label_of(key):
    """Room name from its key (bedroom1 -> Bedroom1, boiler_room -> Boiler room)."""
    return key.replace("_", " ").capitalize()


def storey_label(i):
    return "R" if i == 0 else str(i)


def main():
    rooms = []  # (centre, occupancy, space id, name, flat)
    basement = []
    for key, x0, x1, y0, y1, occupancy, flat in BASEMENT:
        basement.append(box(x0, x1, y0, y1, Z_BASEMENT, Z_RAISED))
        rooms.append((((x0 + x1) / 2, (y0 + y1) / 2, 140), occupancy, "S." + key, label_of(key), "-"))
    residential = []
    for storey in range(STOREYS):
        z0 = Z_RAISED + storey * H
        counters = {}
        for key, x0, x1, y0, y1, occupancy, flat in TYPICAL:
            if storey == 0 and key == "living" and flat == "B":
                # entrance hall of the raised floor
                key, occupancy, flat = "entrance_hall", "Circulation:EntranceHall", "-"
            residential.append(box(x0, x1, y0, y1, z0, z0 + H))
            label = storey_label(storey)
            if flat == "-":
                space = "%s.%s" % (label, key)
            else:
                counters[flat] = counters.get(flat, 0) + 1
                space = "%s%s.%02d" % (label, flat, counters[flat])
            rooms.append((((x0 + x1) / 2, (y0 + y1) / 2, z0 + 150), occupancy, space, label_of(key),
                          "%s%s" % (label, flat) if flat != "-" else "-"))
    attic, turret = hipped_roof()
    rooms.append(((300, 300, Z_TOP + 50), "Unconditioned:Attic", "T.attic", "Attic", "-"))
    rooms.append((((STAIR[0] + STAIR[1]) / 2, (STAIR[2] + STAIR[3]) / 2, Z_TOP + 150), "Circulation:Stair",
                  "T.stair_turret", "Stair turret", "-"))

    for name, cells in (("Basement", basement), ("Storeys", residential), ("Roof", [attic, turret])):
        print("%-12s -> %s (%d cells)" % ((name,) + write_brep(cells, name)))
    write("tbim_BRepFilePaths.json", ["3d/Basement.brep", "3d/Storeys.brep", "3d/Roof.brep"])
    write("tbim_ProjectNorthAngle.json", 131.0)  # north arrow of the site plan
    write("tbim_Rooms.json", [{"center": c, "pr_OccupancyType": o, "space": s, "name": n, "flat": f}
                                   for c, o, s, n, f in rooms])
    write("tbim_InstanceBIM_byTableOfSpaces.json", [
        {"UID": s, "pr_SpaceName": "%s (%s)" % (n, s), "pr_Flat": f, "pr_NetArea": "ByModel",
         "pr_FinishFloor": FINISHES.get(o, "NaN"), "pr_FinishWall": "Painted lime-cement plaster",
         "pr_ConstructionYear": 1966} for c, o, s, n, f in rooms])
    print("rooms:", len(rooms))


if __name__ == "__main__":
    main()
