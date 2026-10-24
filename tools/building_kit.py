"""Write the inputs of a TBIM project from a list of rooms (the make_model.py of the example projects).

A building is a list of building blocks, each a list of rooms. A room is a box (or any Cell) with an
occupancy type, a space id and a name: it becomes one cell of the CellComplex. The kit writes

    3d/<block>.brep                               one CellComplex per block (centimetres)
    json/tbim_BRepFilePaths.json, tbim_ProjectNorthAngle.json
    json/tbim_Rooms.json                          room point, occupancy, space id, name (Assignment > From Table)
    json/tbim_ILDs.json, tbim_InstanceBIM_*.json, tbim_IRS_*.json
    json/tbim_TopologicalBIM_Rules.json           windows and doors by occupancy type (TopologicalBIM > By Rules)
    project.json
"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
sys.path.insert(0, os.path.join(ROOT, "pyRevit", "pyRevit_extensions", "TBIM.extension", "lib"))

from topologicpy.Cell import Cell  # noqa: E402
from topologicpy.CellComplex import CellComplex  # noqa: E402
from topologicpy.Face import Face  # noqa: E402
from topologicpy.Topology import Topology  # noqa: E402
from topologicpy.Vertex import Vertex  # noqa: E402

import tbim  # noqa: E402,F401  (adds the TBIM site-packages)
from tbim import materials, paths, topo  # noqa: E402

FLOOR, ROOF, WALL = "stFC_FloorTypeName", "stFC_RoofTypeName", "stFC_WallTypeName"
IRS_FILES = ["botHor", "topHor", "intHor", "intVer", "extVer"]


class Room(object):
    """A box-shaped room: x0..x1, y0..y1, z0..z1 in centimetres."""

    def __init__(self, x0, x1, y0, y1, z0, z1, occupancy, space, name, block="Block"):
        self.box = (x0, x1, y0, y1, z0, z1)
        self.occupancy, self.space, self.name, self.block = occupancy, space, name, block
        self.cell = None  # set for non-box rooms

    @property
    def center(self):
        if self.cell is not None:
            return Vertex.Coordinates(topo.interior_point(self.cell))
        x0, x1, y0, y1, z0, z1 = self.box
        return [(x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0]

    def topology(self):
        if self.cell is not None:
            return self.cell
        x0, x1, y0, y1, z0, z1 = self.box
        return Cell.Prism(origin=Vertex.ByCoordinates((x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0),
                          width=x1 - x0, length=y1 - y0, height=z1 - z0)


def box_cell(x0, x1, y0, y1, z0, z1):
    return Room(x0, x1, y0, y1, z0, z1, "", "", "").topology()


def hipped_attic(x0, x1, y0, y1, z, rise, cuts=()):
    """Attic under a hipped roof (hips at 45 degrees in plan, ridge along x) minus the ``cuts`` boxes."""
    v = Vertex.ByCoordinates
    half = (y1 - y0) / 2.0
    a, b, c, d = v(x0, y0, z), v(x1, y0, z), v(x1, y1, z), v(x0, y1, z)
    r1, r2 = v(x0 + half, y0 + half, z + rise), v(x1 - half, y0 + half, z + rise)
    faces = [Face.ByVertices([a, d, c, b]), Face.ByVertices([a, b, r2, r1]), Face.ByVertices([c, d, r1, r2]),
             Face.ByVertices([d, a, r1]), Face.ByVertices([b, c, r2])]
    attic = Cell.ByFaces(faces)
    for cut in cuts:
        result = Topology.Difference(attic, box_cell(*cut))
        attic = max(Topology.Cells(result), key=Cell.Volume) if not Topology.IsInstance(result, "Cell") else result
    return attic


def gable_attic(x0, x1, y0, y1, z, rise):
    """Attic under a gable roof with the ridge along x."""
    v = Vertex.ByCoordinates
    ym = (y0 + y1) / 2.0
    a, b, c, d = v(x0, y0, z), v(x1, y0, z), v(x1, y1, z), v(x0, y1, z)
    r1, r2 = v(x0, ym, z + rise), v(x1, ym, z + rise)
    faces = [Face.ByVertices([a, d, c, b]), Face.ByVertices([a, b, r2, r1]), Face.ByVertices([c, d, r1, r2]),
             Face.ByVertices([d, a, r1]), Face.ByVertices([b, c, r2])]
    return Cell.ByFaces(faces)


# --------------------------------------------------------------------------------------
# Data
def ild(occupancy, circulation, occupied, heated, cooled, natural, mechanical, area_per_occupant):
    return {"pr_OccupancyType": occupancy, "pr_CirculationType": circulation, "pr_IsOccupied": occupied,
            "pr_IsHeated": heated, "pr_IsCooled": cooled, "pr_IsNaturallyVentilated": natural,
            "pr_IsMechanicallyVentilated": mechanical, "pr_AreaPerOccupantPeak": area_per_occupant}


def occupancy_data(occupancy, density, ventilation_person, natural_rate, winter, summer):
    return {"pr_OccupancyType": occupancy, "pr_OccupancyDensityOperation": density,
            "pr_OccupancyDensitySafety": density, "pr_MechanicalVentilationRatePerPerson": ventilation_person,
            "pr_MechanicalVentilationRatePerVolume": 0, "pr_NaturalVentilationRate": natural_rate,
            "pr_SpaceTemperatureWinterMin": winter, "pr_SpaceTemperatureSummerMax": summer}


def rule(face_type, conditions, name, layers, year, key=WALL, u_value=None):
    """Informational Rule Set entry with a layered construction (see tbim.materials).

    layers: [(material, mm)] from the outside (top) to the inside (bottom); the style is ``name`` plus the
    total thickness in mm (e.g. TBIM_Brick_Cavity_Wall_275). The U-value is computed from the layers unless
    given (glazed constructions).
    """
    r = {"cnFC_equalTo_pr_TopologicalType": face_type}
    r.update(conditions)
    r.update({key: "%s_%d" % (name, round(materials.thickness(layers))),
              "stFC_ThermalTransmittance": u_value if u_value is not None else materials.u_value(layers, face_type),
              "stFC_Layers": materials.text(layers), "stFC_ConstructionYear": year})
    return r


def _write(folder, name, data):
    path = os.path.join(folder, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    return path


def write_project(here, name, description, rooms, north, ilds, by_occupancy, irs, apertures, table=None):
    """Write all the inputs of the project in the folder ``here``.

    rooms: [Room]; irs: {face type: [rules]}; apertures: TopologicalBIM rules (see tbim.apertures);
    table: optional function Room -> extra columns of the table of spaces.
    """
    for sub in ("3d", "json"):
        os.makedirs(os.path.join(here, sub), exist_ok=True)
    blocks = []
    for room in rooms:
        if room.block not in blocks:
            blocks.append(room.block)
    for block in blocks:
        cells = [r.topology() for r in rooms if r.block == block]
        cc = CellComplex.ByCells(cells, silent=True) if len(cells) > 1 else cells[0]
        path = os.path.join(here, "3d", block + ".brep")
        Topology.ExportToBREP(cc, path, overwrite=True)
        print("%-14s %3d cells -> %s" % (block, len(Topology.Cells(cc)), os.path.relpath(path, here)))
    data = os.path.join(here, "json")
    _write(data, "tbim_BRepFilePaths.json", ["3d/%s.brep" % b for b in blocks])
    _write(data, "tbim_ProjectNorthAngle.json", float(north))
    _write(data, paths.ROOMS, [{"center": r.center, "pr_OccupancyType": r.occupancy, "space": r.space,
                                 "name": r.name} for r in rooms])
    _write(data, "tbim_InstanceBIM_byTableOfSpaces.json", [
        dict({"UID": r.space, "pr_SpaceName": "%s (%s)" % (r.name, r.space), "pr_NetArea": "ByModel"},
             **(table(r) if table else {})) for r in rooms])
    _write(data, "tbim_ILDs.json", ilds)
    _write(data, "tbim_InstanceBIM_byOccupancyType.json", by_occupancy)
    for face_type in IRS_FILES:
        _write(data, "tbim_IRS_%sFaces.json" % face_type, irs.get(face_type, []))
    _write(data, paths.APERTURE_RULES, apertures)
    project = os.path.join(here, "project.json")
    info = json.load(open(project, encoding="utf-8")) if os.path.isfile(project) else {"created": "2026-10-24"}
    info.update({"name": name, "description": description})
    _write(here, "project.json", info)
    occupancies = set(r.occupancy for r in rooms)
    missing = occupancies - set(i["pr_OccupancyType"] for i in ilds)
    if missing:
        raise ValueError("Occupancy types without ILD: %s" % sorted(missing))
    print("%s: %d rooms, %d blocks, %d occupancy types" % (name, len(rooms), len(blocks), len(occupancies)))
