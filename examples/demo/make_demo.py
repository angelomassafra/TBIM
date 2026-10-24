"""Generate the fictitious TBIM demo case study (inputs only).

    python examples/demo/make_demo.py

Building (cm): Block A, two storeys (0, 300 cm) with three rooms and a corridor
each; Block B, a single storey gym. Outputs:

- 3d/BlockA.brep, 3d/BlockB.brep        building blocks (clusters of cells)
- json/tbim_ILDs.json                   Informational Load Dictionaries
- json/tbim_IRS_*.json                  Informational Rule Sets
- json/tbim_ProjectNorthAngle.json      project north (15 degrees)
- json/tbim_InstanceBIM_*.json          instance data by occupancy type / table of spaces
- json/demo_layout.json                 occupancy type and space ids by room
                                        (what a user would assign in Revit)
"""
import json
import os

from topologicpy.Cell import Cell
from topologicpy.Cluster import Cluster
from topologicpy.Topology import Topology
from topologicpy.Vertex import Vertex

HERE = os.path.dirname(os.path.abspath(__file__))
STOREY_HEIGHT = 300.0

# name, block, x, y, z, width (x), length (y), height, occupancy type, table of spaces ids
ROOMS = [
    ("A0-R1", "BlockA", 0, 0, 0, 500, 600, 300, "Education:Classroom", ["A0.01"]),
    ("A0-R2", "BlockA", 500, 0, 0, 500, 600, 300, "Education:Classroom", ["A0.02"]),
    ("A0-R3", "BlockA", 1000, 0, 0, 500, 600, 300, "Office:Office", ["A0.03"]),
    ("A0-CO", "BlockA", 0, 600, 0, 1500, 200, 300, "Circulation:Corridor", ["A0.04a", "A0.04b"]),
    ("A1-R1", "BlockA", 0, 0, 300, 500, 600, 300, "Office:Office", ["A1.01"]),
    ("A1-R2", "BlockA", 500, 0, 300, 500, 600, 300, "Office:MeetingRoom", ["A1.02"]),
    ("A1-R3", "BlockA", 1000, 0, 300, 500, 600, 300, "Support:Storage", ["A1.03"]),
    ("A1-CO", "BlockA", 0, 600, 300, 1500, 200, 300, "Circulation:Corridor", ["A1.04"]),
    ("B0-GY", "BlockB", 1500, 0, 0, 800, 800, 300, "Sport:Gym", ["B0.01"]),
]

ILD_KEYS = ["pr_CirculationType", "pr_IsOccupied", "pr_IsHeated", "pr_IsCooled",
            "pr_IsNaturallyVentilated", "pr_IsMechanicallyVentilated", "pr_AreaPerOccupantPeak"]
ILDS = [
    ("Default", "NoCirculation", True, True, True, True, False, 10.0),
    ("Void", "NoCirculation", False, False, False, False, False, 0.0),
    ("Education:Classroom", "NoCirculation", True, True, False, True, True, 1.8),
    ("Office:Office", "NoCirculation", True, True, True, True, True, 10.0),
    ("Office:MeetingRoom", "NoCirculation", True, True, True, True, True, 2.5),
    ("Support:Storage", "PrivateCirculation", False, False, False, False, False, 0.0),
    ("Circulation:Corridor", "PublicCirculation", True, True, False, True, False, 0.0),
    ("Sport:Gym", "NoCirculation", True, True, False, True, True, 5.0),
]

IRS = {
    "botHor": [{"cnFC_equalTo_pr_TopologicalType": "botHor", "stFC_FloorTypeName": "TBIM_GroundFloor_400"}],
    "topHor": [{"cnFC_equalTo_pr_TopologicalType": "topHor", "stFC_RoofTypeName": "TBIM_Roof_350"}],
    "intHor": [{"cnFC_equalTo_pr_TopologicalType": "intHor", "stFC_FloorTypeName": "TBIM_Slab_300"}],
    "intVer": [
        {"cnFC_equalTo_pr_TopologicalType": "intVer", "stFC_WallTypeName": "TBIM_Partition_100"},
        {"cnFC_equalTo_pr_TopologicalType": "intVer", "cnFC_contains_pr_OccupancyType": "Circulation:Corridor",
         "stFC_WallTypeName": "TBIM_CorridorWall_150"},
        {"cnFC_equalTo_pr_TopologicalType": "intVer", "cnFC_contains_rl_HasLocation_tpBB": "BlockA-BlockB",
         "stFC_WallTypeName": "TBIM_FireWall_250"},
    ],
    "extVer": [
        {"cnFC_equalTo_pr_TopologicalType": "extVer", "stFC_WallTypeName": "TBIM_ExtWall_300"},
        {"cnFC_equalTo_pr_TopologicalType": "extVer", "cnFC_isContained_pr_FaceExposure": ["S", "SE", "SW"],
         "stFC_WallTypeName": "TBIM_ExtWall_South_350", "stFC_ShadingDevice": 1},
    ],
}

BY_OCCUPANCY_TYPE = {
    # density operation / safety (persons/m2), ventilation per person (l/s), set points (C)
    "Education:Classroom": (0.45, 0.7, 7.0, 20, 26),
    "Office:Office": (0.08, 0.1, 10.0, 20, 26),
    "Office:MeetingRoom": (0.35, 0.6, 10.0, 20, 26),
    "Support:Storage": (0.0, 0.0, 0.0, "Undef", "Undef"),
    "Circulation:Corridor": (0.0, 0.2, 0.0, 18, 28),
    "Sport:Gym": (0.1, 0.5, 16.5, 18, 26),
    "Default": (0.1, 0.2, 10.0, 20, 26),
}


def write(name, data):
    path = os.path.join(HERE, "json", name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    return path


def make_breps():
    os.makedirs(os.path.join(HERE, "3d"), exist_ok=True)
    for block in sorted(set(r[1] for r in ROOMS)):
        cells = [Cell.Prism(origin=Vertex.ByCoordinates(x, y, z), width=w, length=d, height=h, placement="lowerleft")
                 for _, b, x, y, z, w, d, h, _, _ in ROOMS if b == block]
        path = os.path.join(HERE, "3d", block + ".brep")
        with open(path, "w") as f:
            f.write(Topology.BREPString(Cluster.ByTopologies(cells)))
        print("written", path, len(cells), "cells")


def main():
    make_breps()
    write("tbim_ILDs.json", [dict(zip(["pr_OccupancyType"] + ILD_KEYS, values)) for values in ILDS])
    for face_type, rulesets in IRS.items():
        write("tbim_IRS_%sFaces.json" % face_type, rulesets)
    write("tbim_ProjectNorthAngle.json", 15.0)
    write("tbim_InstanceBIM_byOccupancyType.json", [
        {"pr_OccupancyType": occ, "pr_OccupancyDensityOperation": op, "pr_OccupancyDensitySafety": sf,
         "pr_MechanicalVentilationRatePerPerson": vent, "pr_MechanicalVentilationRatePerVolume": 0,
         "pr_NaturalVentilationRate": 0.5, "pr_SpaceTemperatureWinterMin": tmin,
         "pr_SpaceTemperatureSummerMax": tmax}
        for occ, (op, sf, vent, tmin, tmax) in BY_OCCUPANCY_TYPE.items()])
    table = []
    for name, _, _, _, _, w, d, h, occ, ids in ROOMS:
        for space_id in ids:
            share = 1.0 / len(ids)
            table.append({"UID": space_id, "pr_SpaceName": "%s (%s)" % (occ.split(":")[1], space_id),
                          "pr_NetArea": round(w * d / 1.0e4 * 0.92 * share, 2), "pr_GrossArea": "ByModel",
                          "pr_NetVolume": "ByModel", "pr_OccupancyNumber": "ByModel",
                          "pr_IsOccupied": "ByOccupancyType", "pr_IsAboveGround": 1, "pr_IsRefugeArea": 0,
                          "pr_FinishFloor": "Linoleum" if "Classroom" in occ else "Ceramic tiles"})
    write("tbim_InstanceBIM_byTableOfSpaces.json", table)
    write("demo_layout.json", [{"room": name, "block": block, "center": [x + w / 2.0, y + d / 2.0, z + h / 2.0],
                                "pr_OccupancyType": occ, "spaces": ids}
                               for name, block, x, y, z, w, d, h, occ, ids in ROOMS])
    print("demo inputs written in", HERE)


if __name__ == "__main__":
    main()
