"""Run the complete TBIM workflow on the demo case study without Revit.

    python examples/demo/make_demo.py     # inputs
    python examples/demo/run_offline.py   # all the TBIM models

Each step mirrors a command of the TBIM ribbon (Project > Run runs them all in Revit); the Revit-side
geometry is approximated from the cells. Occupancy types and space names come from json/tbim_Rooms.json,
windows and doors from json/tbim_TopologicalBIM_Rules.json, as in Revit.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
os.environ["TBIM_HOME"] = HERE
sys.path.insert(0, os.path.join(ROOT, "pyRevit", "pyRevit_extensions", "TBIM.extension", "lib"))

from topologicpy.CellComplex import CellComplex  # noqa: E402

from tbim import apertures, controllers, ibim, ild, instancebim, irs, loads, paths, rooms, styles, tbimjson, topo  # noqa: E402,E501
from tbim.jsonio import read_json, write_json  # noqa: E402

DEMO_MOVE_CM = 100.0  # the first door is "moved in Revit" by this amount


def step(title):
    print("\n== %s" % title)


def main():
    step("3D Model > Import")
    breps = [os.path.join(HERE, "3d", name) for name in ("BlockA.brep", "BlockB.brep")]
    write_json(paths.data_file(paths.BREP_FILEPATHS), ["3d/BlockA.brep", "3d/BlockB.brep"])  # project-relative

    step("Collectors > CellComplex > Create")
    cc = controllers.build_cellcomplex(breps)
    elevations = controllers.storey_elevations(cc)
    controllers.assign_storeys(cc, elevations)
    topo.save_cellcomplex(cc, paths.data_file(paths.CC_CONTROLLERS))
    print("cells: %d, storeys: %s" % (len(CellComplex.Cells(cc)), elevations))

    step("Loads > Assignment > From Table")
    matches, _ = rooms.match(cc, read_json(paths.data_file(paths.ROOMS)))
    ild.save_assignments(rooms.assignments(matches))
    space_names = rooms.space_ids(matches)  # the names of the Revit spaces
    for uid, room in sorted(matches.items()):
        print("  %s -> %s (%s)" % (uid, room["name"], room["pr_OccupancyType"]))

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

    step("TopologicalBIM > By Rules")
    cc = topo.load_cellcomplex(paths.data_file(paths.CC_STYLES))
    cc, placements = apertures.place(cc, read_json(paths.data_file(paths.APERTURE_RULES)))
    topo.save_cellcomplex(cc, paths.data_file(paths.CC_TBIM))
    locations = apertures.locations(placements)
    write_json(paths.data_file(paths.APERTURE_LOCATIONS), locations)
    print("apertures: %d" % len(placements))

    step("InstanceBIM > 00 MoveApertures (first door moved in Revit)")
    door = next(p for p in placements if p["kind"] == "door")
    location = next(loc["Location"] for loc in locations if loc["UID"] == door["UID"])
    rv, u = location["Revit"], door["direction"]
    revit_xyz = [rv["X"] + int(u[0] * DEMO_MOVE_CM), rv["Y"] + int(u[1] * DEMO_MOVE_CM), rv["Z"]]
    moves = {door["UID"]: ibim.aperture_movement(revit_xyz, location)}
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
