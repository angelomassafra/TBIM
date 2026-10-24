"""Office Tower - a 20-storey office building (invented example).

30 x 30 m square plan with a central reinforced-concrete core (stairs, lifts, services) and a ring of
eight office cells per storey; double-height lobby at the ground floor, plant room on the roof.

    python make_model.py     # writes 3d/*.brep and the json inputs of the project
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, os.pardir, os.pardir, "tools"))

from building_kit import FLOOR, ROOF, Room, ild, occupancy_data, rule, write_project  # noqa: E402

YEAR = 2022
STOREYS, LOBBY_H, H = 20, 500, 360
CORE = (1000, 2000, 1000, 2000)
RING = [  # (key, x0, x1, y0, y1)
    ("SW", 0, 1000, 0, 1000), ("S", 1000, 2000, 0, 1000), ("SE", 2000, 3000, 0, 1000),
    ("E", 2000, 3000, 1000, 2000), ("NE", 2000, 3000, 2000, 3000), ("N", 1000, 2000, 2000, 3000),
    ("NW", 0, 1000, 2000, 3000), ("W", 0, 1000, 1000, 2000),
]
GROUND = {"SW": ("Food:Cafe", "Cafe"), "SE": ("Retail:Shop", "Shop"), "NE": ("Retail:Shop", "Shop"),
          "NW": ("Office:Reception", "Reception")}
OFFICE = {"E": ("Office:MeetingRoom", "Meeting room"), "W": ("Office:Private", "Private offices")}


def rooms():
    out = []
    for storey in range(STOREYS):
        z0 = 0 if storey == 0 else LOBBY_H + (storey - 1) * H
        z1 = LOBBY_H if storey == 0 else z0 + H
        label = "%02d" % storey
        out.append(Room(*(CORE + (z0, z1)), occupancy="Circulation:Core", space="%s.CORE" % label, name="Core",
                        block="Tower"))
        for key, x0, x1, y0, y1 in RING:
            if storey == 0:
                occupancy, name = GROUND.get(key, ("Circulation:Lobby", "Lobby"))
            else:
                occupancy, name = OFFICE.get(key, ("Office:OpenPlan", "Open-plan office"))
            out.append(Room(x0, x1, y0, y1, z0, z1, occupancy, "%s.%s" % (label, key), name, "Tower"))
    top = LOBBY_H + (STOREYS - 1) * H
    out.append(Room(*(CORE + (top, top + 500)), occupancy="Technical:Plant", space="RF.PLANT",
                    name="Plant room", block="Tower"))
    return out


ILDS = [
    ild("Default", "NoCirculation", False, False, False, False, False, 0),
    ild("Office:OpenPlan", "NoCirculation", True, True, True, False, True, 10.0),
    ild("Office:Private", "NoCirculation", True, True, True, False, True, 12.0),
    ild("Office:MeetingRoom", "NoCirculation", True, True, True, False, True, 3.0),
    ild("Office:Reception", "NoCirculation", True, True, True, False, True, 8.0),
    ild("Circulation:Core", "PublicCirculation", False, True, False, False, True, 0),
    ild("Circulation:Lobby", "PublicCirculation", True, True, True, False, True, 5.0),
    ild("Food:Cafe", "NoCirculation", True, True, True, False, True, 1.5),
    ild("Retail:Shop", "NoCirculation", True, True, True, False, True, 4.0),
    ild("Technical:Plant", "NoCirculation", False, False, False, True, False, 0),
]
BY_OCCUPANCY = [
    occupancy_data("Office:OpenPlan", 0.10, 40, 0, 20, 26),
    occupancy_data("Office:Private", 0.08, 40, 0, 20, 26),
    occupancy_data("Office:MeetingRoom", 0.35, 40, 0, 20, 26),
    occupancy_data("Office:Reception", 0.12, 40, 0, 20, 26),
    occupancy_data("Circulation:Core", 0, 0, 0, 18, "NaN"),
    occupancy_data("Circulation:Lobby", 0.20, 40, 0, 18, 27),
    occupancy_data("Food:Cafe", 0.70, 40, 0, 20, 26),
    occupancy_data("Retail:Shop", 0.25, 40, 0, 20, 26),
    occupancy_data("Technical:Plant", 0, 0, 2.0, "NaN", "NaN"),
]
IRS = {
    "botHor": [rule("botHor", {}, "TBIM_Insulated_RC_Raft", [
        ("Natural stone tiles", 20), ("Cement screed", 80), ("XPS insulation", 120), ("Reinforced concrete", 400)],
        YEAR, FLOOR)],
    "topHor": [rule("topHor", {}, "TBIM_Inverted_Flat_Roof", [
        ("Gravel ballast", 60), ("XPS insulation", 160), ("Bitumen membrane", 10),
        ("Lightweight concrete screed", 60), ("Reinforced concrete", 300)], YEAR, ROOF)],
    "intHor": [rule("intHor", {}, "TBIM_PT_Slab_Raised_Floor", [
        ("Raised access floor panel", 40), ("Floor void", 110), ("Reinforced concrete", 250)], YEAR, FLOOR)],
    "intVer": [
        rule("intVer", {}, "TBIM_Gypsum_Stud_Partition", [
            ("Gypsum board", 25), ("Mineral wool", 75), ("Gypsum board", 25)], YEAR),
        rule("intVer", {"cnFC_contains_pr_OccupancyType": "Core"}, "TBIM_RC_Core_Wall", [
            ("Reinforced concrete", 400)], YEAR),
    ],
    "extVer": [
        rule("extVer", {}, "TBIM_Unitised_Curtain_Wall", [
            ("Triple glazing unit", 54), ("Insulated spandrel panel", 146)], YEAR, u_value=1.00),
        rule("extVer", {"cnFC_contains_pr_OccupancyType": "Plant"}, "TBIM_Plant_Louvre_Screen", [
            ("Aluminium louvres", 50), ("Ventilated air cavity", 50), ("Mineral wool", 100),
            ("Precast concrete", 100)], YEAR),
    ],
}
APERTURES = {
    "windows": [["Office", "TBIM_Office_Glazing_800x280", 800, 280, 30],
                ["Lobby", "TBIM_Lobby_Glazing_800x400", 800, 400, 40],
                ["Cafe", "TBIM_Lobby_Glazing_800x400", 800, 400, 40],
                ["Shop", "TBIM_Shop_Window_800x400", 800, 400, 40]],
    "external_doors": [["Lobby", "TBIM_Revolving_Door_300x300", 300, 300]],
    "doors": [["Core", "", "TBIM_Fire_Door_EI120_100x220", 100, 220],
              ["Lobby", "", "TBIM_Glass_Door_200x250", 200, 250],
              ["Office", "Office", "TBIM_Office_Door_90x220", 90, 220]],
    "window_data": {"pr_FrameMaterial": "Aluminium, thermal break", "pr_Glazing": "Triple glazing, low-e",
                    "pr_ThermalTransmittance": 1.0, "pr_SolarFactor": 0.30, "pr_ConstructionYear": YEAR},
    "door_data": {"pr_ConstructionYear": YEAR},
}

if __name__ == "__main__":
    write_project(HERE, "Office Tower", "Invented 20-storey office tower: RC core, ring of offices, unitized "
                  "curtain wall, double-height lobby.", rooms(), 20.0, ILDS, BY_OCCUPANCY, IRS, APERTURES,
                  table=lambda r: {"pr_FinishFloor": "Raised access floor" if "Office" in r.occupancy else "Stone",
                                   "pr_ConstructionYear": YEAR})
