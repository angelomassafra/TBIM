"""Shopping Centre - a two-level mall (invented example).

80 m long double-height gallery with two levels of shops on both sides, a food court on the upper
level, a two-level anchor store at the east end, an entrance hall at the west end and plant rooms on
the roof.

    python make_model.py     # writes 3d/*.brep and the json inputs of the project
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, os.pardir, os.pardir, "tools"))

from building_kit import FLOOR, ROOF, Room, ild, occupancy_data, rule, write_project  # noqa: E402

YEAR = 2008
H, BAYS, BAY = 500, 8, 1000
SOUTH, GALLERY, NORTH = (0, 1600), (1600, 2400), (2400, 4000)


def rooms():
    out = []
    for level in range(2):
        z0, z1 = level * H, (level + 1) * H
        for side, (y0, y1) in (("S", SOUTH), ("N", NORTH)):
            for i in range(BAYS):
                if level == 1 and side == "N" and i < 3:
                    continue  # food court
                space = "%d%s.%02d" % (level, side, i + 1)
                out.append(Room(i * BAY, (i + 1) * BAY, y0, y1, z0, z1, "Retail:Shop", space,
                                "Shop %d%s%02d" % (level, side, i + 1), "Mall"))
        out.append(Room(8000, 11000, 0, 4000, z0, z1, "Retail:DepartmentStore", "%d.ANCHOR" % level,
                        "Department store", "Mall"))
    out.append(Room(0, 3000, NORTH[0], NORTH[1], H, 2 * H, "Food:FoodCourt", "1.FOOD", "Food court", "Mall"))
    out.append(Room(0, 4000, GALLERY[0], GALLERY[1], 0, 2 * H, "Circulation:Gallery", "G.W", "Gallery west", "Mall"))
    out.append(Room(4000, 8000, GALLERY[0], GALLERY[1], 0, 2 * H, "Circulation:Gallery", "G.E", "Gallery east",
                    "Mall"))
    out.append(Room(-800, 0, GALLERY[0] - 200, GALLERY[1] + 200, 0, 2 * H, "Circulation:EntranceHall", "G.ENTRY",
                    "Entrance hall", "Mall"))
    out.append(Room(1000, 3000, 400, 1400, 2 * H, 2 * H + 400, "Technical:Plant", "R.P1", "Plant room 1", "Mall"))
    out.append(Room(9500, 11000, 2500, 3500, 2 * H, 2 * H + 400, "Technical:Plant", "R.P2", "Plant room 2", "Mall"))
    return out


ILDS = [
    ild("Default", "NoCirculation", False, False, False, False, False, 0),
    ild("Retail:Shop", "NoCirculation", True, True, True, False, True, 4.0),
    ild("Retail:DepartmentStore", "NoCirculation", True, True, True, False, True, 5.0),
    ild("Food:FoodCourt", "NoCirculation", True, True, True, False, True, 1.5),
    ild("Circulation:Gallery", "PublicCirculation", True, True, True, False, True, 3.0),
    ild("Circulation:EntranceHall", "PublicCirculation", True, True, True, False, True, 3.0),
    ild("Technical:Plant", "NoCirculation", False, False, False, True, False, 0),
]
BY_OCCUPANCY = [
    occupancy_data("Retail:Shop", 0.25, 40, 0, 20, 26),
    occupancy_data("Retail:DepartmentStore", 0.20, 40, 0, 20, 26),
    occupancy_data("Food:FoodCourt", 0.70, 40, 0, 20, 26),
    occupancy_data("Circulation:Gallery", 0.30, 40, 0, 18, 27),
    occupancy_data("Circulation:EntranceHall", 0.30, 40, 0, 18, 27),
    occupancy_data("Technical:Plant", 0, 0, 2.0, "NaN", "NaN"),
]
IRS = {
    "botHor": [rule("botHor", {}, "TBIM_Insulated_Ground_Slab", [
        ("Porcelain stoneware tiles", 12), ("Cement screed", 60), ("EPS insulation", 100),
        ("Reinforced concrete", 300), ("Lean concrete", 100)], YEAR, FLOOR)],
    "topHor": [
        rule("topHor", {}, "TBIM_Standing_Seam_Roof", [
            ("Standing-seam aluminium sheet", 2), ("Mineral wool", 160), ("Precast hollow-core slab", 200)],
            YEAR, ROOF),
        rule("topHor", {"cnFC_contains_pr_OccupancyType": "Gallery"}, "TBIM_Gallery_Skylight", [
            ("Laminated double glazing", 44)], YEAR, ROOF, u_value=1.40),
    ],
    "intHor": [rule("intHor", {}, "TBIM_Hollow_Core_Floor", [
        ("Porcelain stoneware tiles", 12), ("Cement screed", 60), ("Precast hollow-core slab", 300)], YEAR, FLOOR)],
    "intVer": [
        rule("intVer", {}, "TBIM_Fire_Rated_Partition_EI60", [
            ("Fire-rated gypsum board", 25), ("Mineral wool", 100), ("Fire-rated gypsum board", 25)], YEAR),
        rule("intVer", {"cnFC_contains_pr_OccupancyType": "Gallery"}, "TBIM_Glazed_Shop_Front", [
            ("Laminated safety glass", 24)], YEAR, u_value=2.80),
    ],
    "extVer": [
        rule("extVer", {}, "TBIM_Ventilated_Metal_Facade", [
            ("Aluminium composite panel", 4), ("Ventilated air cavity", 40), ("Mineral wool", 100),
            ("Precast concrete", 150)], YEAR),
        rule("extVer", {"cnFC_contains_pr_OccupancyType": "DepartmentStore"}, "TBIM_Terracotta_Rainscreen_Facade", [
            ("Terracotta rainscreen tiles", 30), ("Ventilated air cavity", 40), ("Mineral wool", 120),
            ("Precast concrete", 150)], YEAR),
    ],
}
APERTURES = {
    "windows": [["Shop", "TBIM_Shop_Window_400x300", 400, 300, 40],
                ["DepartmentStore", "TBIM_Store_Window_600x300", 600, 300, 50],
                ["FoodCourt", "TBIM_Food_Court_Glazing_800x300", 800, 300, 100],
                ["EntranceHall", "TBIM_Entrance_Glazing_500x700", 500, 700, 50]],
    "external_doors": [["EntranceHall", "TBIM_Sliding_Door_400x300", 400, 300],
                       ["DepartmentStore", "TBIM_Sliding_Door_300x300", 300, 300]],
    "doors": [["EntranceHall", "Gallery", "TBIM_Gallery_Opening_500x400", 500, 400],
              ["Gallery", "DepartmentStore", "TBIM_Store_Opening_600x350", 600, 350],
              ["Gallery", "FoodCourt", "TBIM_Store_Opening_600x350", 600, 350],
              ["Gallery", "Shop", "TBIM_Shop_Entrance_300x300", 300, 300]],
    "window_data": {"pr_FrameMaterial": "Aluminium, thermal break", "pr_Glazing": "Double glazing, low-e",
                    "pr_ThermalTransmittance": 1.8, "pr_SolarFactor": 0.40, "pr_ConstructionYear": YEAR},
    "door_data": {"pr_ConstructionYear": YEAR},
}

if __name__ == "__main__":
    write_project(HERE, "Shopping Centre", "Invented two-level shopping centre: glazed double-height gallery, "
                  "shops, food court, anchor store, precast structure.", rooms(), 0.0, ILDS, BY_OCCUPANCY, IRS,
                  APERTURES, table=lambda r: {"pr_FinishFloor": "Porcelain tiles", "pr_ConstructionYear": YEAR})
