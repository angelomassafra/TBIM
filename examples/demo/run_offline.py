"""Run the complete TBIM workflow on the demo case study without Revit.

    python examples/demo/make_demo.py     # inputs
    python examples/demo/run_offline.py   # all the TBIM models

Each step mirrors a command of the TBIM ribbon; the Revit interactions are
emulated from json/demo_layout.json (occupancy types and space names a user
would set in Revit) and the Revit-side geometry is approximated from the cells.

The "TopologicalBIM" step (apertures on the styled CellComplex) is a stand-in
for the TopologicalBIM panel, which is not part of this release yet.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
os.environ["TBIM_HOME"] = HERE
sys.path.insert(0, os.path.join(ROOT, "pyRevit", "pyRevit_extensions", "TBIM.extension", "lib"))

from topologicpy.CellComplex import CellComplex  # noqa: E402
from topologicpy.Face import Face  # noqa: E402
from topologicpy.Topology import Topology  # noqa: E402
from topologicpy.Vertex import Vertex  # noqa: E402

from tbim import controllers, ibim, ild, instancebim, irs, loads, paths, styles, tbimjson, topo  # noqa: E402
from tbim.jsonio import read_json, write_json  # noqa: E402

WINDOW = (120.0, 150.0, 90.0)  # width, height, sill (cm)
DOOR = (90.0, 210.0, 0.0)
DEMO_MOVE_CM = 100.0  # the first door is "moved in Revit" by this amount


def step(title):
    print("\n== %s" % title)


def room_of(cell, layout):
    c = Vertex.Coordinates(topo.interior_point(cell))
    return min(layout, key=lambda r: sum((a - b) ** 2 for a, b in zip(c, r["center"])))


def opening(face, width, height, sill):
    """Rectangular face centred on the bottom edge of a vertical face, ``sill`` above it."""
    pts = [Vertex.Coordinates(v) for v in Topology.Vertices(face)]
    zmin = min(p[2] for p in pts)
    bottom = [p for p in pts if abs(p[2] - zmin) < 1e-3]
    a, b = min(bottom), max(bottom)
    length = math.hypot(b[0] - a[0], b[1] - a[1])
    if length < width + 60:
        return None, None
    u = ((b[0] - a[0]) / length, (b[1] - a[1]) / length)
    cx, cy = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
    z0, z1 = zmin + sill, zmin + sill + height
    (x0, y0), (x1, y1) = [(cx + s * u[0] * width / 2, cy + s * u[1] * width / 2) for s in (-1, 1)]
    vertices = [Vertex.ByCoordinates(x, y, z) for x, y, z in ((x0, y0, z0), (x1, y1, z0), (x1, y1, z1), (x0, y0, z1))]
    return Face.ByVertices(vertices), (cx, cy, zmin + sill, u)


def topological_bim(cc):
    """Stand-in for the TopologicalBIM panel: windows on external walls, doors towards corridors."""
    apertures, locations = [], []
    counters = {"window": 0, "door": 0}
    for face_type, faces in topo.face_groups(cc):
        for face in faces:
            props = topo.props(face)
            if face_type == "extVer" and "Circulation" not in props.get("pr_OccupancyType", ""):
                kind, size = "window", WINDOW
            elif face_type == "intVer" and "Corridor" in props.get("pr_OccupancyType", "") \
                    and props["pr_OccupancyType"].count("Corridor") == 1:
                kind, size = "door", DOOR
            else:
                continue
            aperture, location = opening(face, *size)
            if aperture is None:
                continue
            uid = "%s%d" % (kind, counters[kind])
            counters[kind] += 1
            topo.replace(aperture, {"UID": uid, "pr_TopologicalType": kind, "pr_Width": size[0],
                                    "pr_Height": size[1], "rl_HasLocation_inFC": props["UID"]})
            apertures.append(aperture)
            c = Vertex.Coordinates(Topology.Centroid(aperture))
            revit_point = dict(zip("XYZ", [int(v) for v in location[:3]]))
            locations.append({"UID": uid, "Direction": location[3],
                              "Location": {"Revit": revit_point, "Topologic": dict(zip("XYZ", c))}})
    cc = Topology.AddApertures(cc, apertures, subTopologyType="face")
    return cc, locations


def main():
    layout = read_json(paths.data_file("demo_layout.json"))

    step("3D Model > Import")
    breps = [os.path.join(HERE, "3d", name) for name in ("BlockA.brep", "BlockB.brep")]
    write_json(paths.data_file(paths.BREP_FILEPATHS), ["3d/BlockA.brep", "3d/BlockB.brep"])  # project-relative

    step("Collectors > CellComplex > Create")
    cc = controllers.build_cellcomplex(breps)
    elevations = controllers.storey_elevations(cc)
    controllers.assign_storeys(cc, elevations)
    topo.save_cellcomplex(cc, paths.data_file(paths.CC_CONTROLLERS))
    print("cells: %d, storeys: %s" % (len(CellComplex.Cells(cc)), elevations))

    step("Loads > Assignment (emulated)")
    assignments, space_names = {}, {}
    for cell in CellComplex.Cells(cc):
        room = room_of(cell, layout)
        assignments[topo.cell_uid(cell)] = room["pr_OccupancyType"]
        space_names[topo.cell_uid(cell)] = "; ".join(room["spaces"])
        print("  %s -> %s (%s)" % (topo.cell_uid(cell), room["room"], room["pr_OccupancyType"]))
    ild.save_assignments(assignments)
    write_json(paths.data_file("demo_space_names.json"), space_names)

    step("Loads > CellComplex > Clusterize")
    cc = topo.load_cellcomplex(paths.data_file(paths.CC_CONTROLLERS))
    face_keys = loads.run(cc, ild.load(), ild.load_assignments(), float(read_json(paths.data_file(paths.NORTH_ANGLE))),
                          clusterize=True)
    write_json(paths.data_file(paths.FACE_PROPERTIES), face_keys)
    for name in (paths.CC_LOADS, paths.CC_LOADS_CLUSTERIZED):
        topo.save_cellcomplex(cc, paths.data_file(name))
    for cell in CellComplex.Cells(cc):
        p = topo.props(cell)
        print("  %s %-22s %-18s exposure=%s/%s" % (p["UID"], p["pr_OccupancyType"], p["rl_HasLocation_tpZN"],
                                                   p["pr_MainExposure"], p["pr_NumberOfExposures"]))

    step("Styles > CellComplex > Update")
    cc = topo.load_cellcomplex(paths.data_file(paths.CC_LOADS))
    rulesets = irs.load()
    print("faces styled: %d" % styles.run(cc, rulesets))
    topo.save_cellcomplex(cc, paths.data_file(paths.CC_STYLES))

    step("TopologicalBIM (stand-in)")
    cc = topo.load_cellcomplex(paths.data_file(paths.CC_STYLES))
    cc, locations = topological_bim(cc)
    topo.save_cellcomplex(cc, paths.data_file(paths.CC_TBIM))
    write_json(paths.data_file(paths.APERTURE_LOCATIONS), [dict((k, v) for k, v in loc.items() if k != "Direction")
                                                           for loc in locations])
    print("apertures: %d" % len(locations))

    step("InstanceBIM > 00 MoveApertures (first door moved in Revit)")
    door = next(loc for loc in locations if loc["UID"].startswith("door"))
    rv, u = door["Location"]["Revit"], door["Direction"]
    revit_xyz = [rv["X"] + int(u[0] * DEMO_MOVE_CM), rv["Y"] + int(u[1] * DEMO_MOVE_CM), rv["Z"]]
    moves = {door["UID"]: ibim.aperture_movement(revit_xyz, door["Location"])}
    records = read_json(paths.data_file(paths.CC_TBIM))
    print("moved: %s %s" % (tbimjson.move_apertures(records, moves), moves))
    write_json(paths.data_file(paths.CC_IBIM), records)

    step("InstanceBIM > 01 ByOccupancyType / 02 ByTableOfSpaces / 03 ByModel")
    cc = topo.load_cellcomplex(paths.data_file(paths.CC_IBIM))
    instancebim.by_occupancy_type(cc, read_json(paths.data_file(paths.IBIM_BY_OCCUPANCY_TYPE)))
    matched = instancebim.by_table_of_spaces(cc, read_json(paths.data_file(paths.IBIM_BY_TABLE_OF_SPACES)),
                                             space_names)
    net = {}
    for cell in CellComplex.Cells(cc):
        gross_area, gross_volume, _ = instancebim.gross_geometry(cell)
        net[topo.cell_uid(cell)] = (gross_area * 0.92, gross_volume * 0.85)
    print("table of spaces matched: %d, ByModel: %d" % (matched, instancebim.by_model(cc, net)))
    topo.save_cellcomplex(cc, paths.data_file(paths.CC_IBIM))

    step("InstanceBIM > Revit > UpdateData (data that would be written to Revit)")
    data = tbimjson.dictionaries(paths.data_file(paths.CC_IBIM))
    print(dict((k, len(v)) for k, v in data.items()))
    example = tbimjson.by_uid(data["Cell"])[sorted(tbimjson.by_uid(data["Cell"]))[0]]
    for key in sorted(example):
        print("  %s: %s" % (key, example[key]))


if __name__ == "__main__":
    main()
