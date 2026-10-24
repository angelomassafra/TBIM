"""Stand-in for the TopologicalBIM panel (step 5): windows and doors on the styled CellComplex.

The TopologicalBIM panel is not part of this release yet. This script places the apertures with the
rules of ``json/standin_apertures.json`` (written by the make_model.py of the example projects)::

    {"windows":        [[occupancy contains, type, width, height, sill], ...],   external vertical faces
     "external_doors": [[occupancy contains, type, width, height], ...],         ground floor, one per cell
     "doors":          [[occupancy A contains, occupancy B contains, type, width, height], ...],
     "window_data": {...}, "door_data": {...}}                                     extra aperture data

and writes tbim_CellComplex_TBIM.json, tbim_CellComplex_TBIM_AperturesLocation.json and
``json/standin_placement.txt`` (apertures and wall/floor/roof styles, read by the Revit side).

    python tools/topologicalbim_standin.py <project folder>
"""
import math
import os
import sys

FOLDER = os.path.abspath(sys.argv[1])
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
os.environ["TBIM_HOME"] = ROOT
sys.path.insert(0, os.path.join(ROOT, "pyRevit", "pyRevit_extensions", "TBIM.extension", "lib"))

from topologicpy.CellComplex import CellComplex  # noqa: E402
from topologicpy.Face import Face  # noqa: E402
from topologicpy.Topology import Topology  # noqa: E402
from topologicpy.Vertex import Vertex  # noqa: E402

from tbim import topo  # noqa: E402
from tbim.jsonio import read_json, write_json  # noqa: E402

DATA = os.path.join(FOLDER, "json")
STYLE_KEYS = ("stFC_WallTypeName", "stFC_FloorTypeName", "stFC_RoofTypeName")


def opening(face, width, height, sill, margin):
    """Rectangle centred on the bottom edge of a vertical face. Return (face, bottom centre) or (None, None)."""
    pts = [Vertex.Coordinates(v) for v in Topology.Vertices(face)]
    zmin, zmax = min(p[2] for p in pts), max(p[2] for p in pts)
    bottom = [p for p in pts if abs(p[2] - zmin) < 1e-3]
    if len(bottom) < 2 or zmax - zmin < sill + height + 20:
        return None, None
    a, b = min(bottom), max(bottom)
    length = math.hypot(b[0] - a[0], b[1] - a[1])
    if length < width + margin:
        return None, None
    u = ((b[0] - a[0]) / length, (b[1] - a[1]) / length)
    cx, cy = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
    z0, z1 = zmin + sill, zmin + sill + height
    (x0, y0), (x1, y1) = [(cx + s * u[0] * width / 2, cy + s * u[1] * width / 2) for s in (-1, 1)]
    vertices = [Vertex.ByCoordinates(x, y, z) for x, y, z in ((x0, y0, z0), (x1, y1, z0), (x1, y1, z1), (x0, y0, z1))]
    return Face.ByVertices(vertices), (cx, cy, zmin)


def first(rules, occupancy):
    return next((r for r in rules if r[0] in occupancy), None)


def door_rule(rules, occupancies):
    if len(occupancies) != 2:
        return None
    a, b = occupancies
    return next((r for r in rules if (r[0] in a and r[1] in b) or (r[0] in b and r[1] in a)), None)


def main():
    rules = read_json(os.path.join(DATA, "standin_apertures.json"))
    cc = topo.load_cellcomplex(os.path.join(DATA, "tbim_CellComplex_Styles.json"))
    styles = {}
    for face in CellComplex.Faces(cc):
        p = topo.props(face)
        for key in STYLE_KEYS:
            if p.get(key):
                styles[p["UID"]] = p[key]
    records, placement, counters = [], [], {"window": 0, "door": 0}
    entrance_cells, connected = set(), set()
    for face_type, faces in topo.face_groups(cc):
        if face_type not in ("extVer", "intVer"):
            continue
        for face in faces:
            props = topo.props(face)
            cells = topo.adjacent_cells(face, cc)
            occupancies = [topo.get(c, "pr_OccupancyType", "") for c in cells]
            uids = tuple(sorted(topo.cell_uid(c) for c in cells))
            ground = topo.z_range(face)[0] < 1.0
            if face_type == "extVer":
                door = first(rules.get("external_doors", []), occupancies[0]) if ground and cells else None
                if door and uids[0] not in entrance_cells:
                    _, type_name, w, h = door
                    sill, kind, margin = 0, "door", 40
                else:
                    window = first(rules.get("windows", []), occupancies[0] if occupancies else "")
                    if window is None:
                        continue
                    _, type_name, w, h, sill = window
                    kind, margin = "window", 60
            else:
                door = door_rule(rules.get("doors", []), occupancies)
                if door is None or uids in connected:
                    continue
                _, _, type_name, w, h = door
                sill, kind, margin = 0, "door", 20
            aperture, point = opening(face, w, h, sill, margin)
            if aperture is None:
                continue
            if kind == "door":
                (entrance_cells if face_type == "extVer" else connected).add(uids[0] if face_type == "extVer" else uids)
            uid = "%s%d" % (kind, counters[kind])
            counters[kind] += 1
            data = dict(rules.get(kind + "_data", {}), UID=uid, pr_TopologicalType=kind, pr_Width=w, pr_Height=h,
                        pr_SillHeight=sill, stAP_TypeName=type_name, rl_HasLocation_inFC=props["UID"])
            topo.replace(aperture, data)
            records.append(aperture)
            placement.append((uid, kind, type_name, w, h, sill, props["UID"], point))
    cc = Topology.AddApertures(cc, records, subTopologyType="face")
    topo.save_cellcomplex(cc, os.path.join(DATA, "tbim_CellComplex_TBIM.json"))
    write_json(os.path.join(DATA, "tbim_CellComplex_TBIM_AperturesLocation.json"), [
        {"UID": uid, "Location": {"Revit": dict(zip("XYZ", [int(p[0]), int(p[1]), int(p[2] + sill)]))}}
        for uid, _, _, _, _, sill, _, p in placement])
    with open(os.path.join(DATA, "standin_placement.txt"), "w", encoding="utf-8") as f:
        for uid, kind, type_name, w, h, sill, host, p in placement:
            f.write("A|%s|%s|%s|%g|%g|%g|%s|%.1f|%.1f|%.1f\n" % ((uid, kind, type_name, w, h, sill, host) + tuple(p)))
        for face_uid, style in sorted(styles.items()):
            f.write("S|%s|%s\n" % (face_uid, style))
    print("windows %d, doors %d, styled faces %d" % (counters["window"], counters["door"], len(styles)))


if __name__ == "__main__":
    main()
