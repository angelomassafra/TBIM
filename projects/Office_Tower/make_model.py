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
    "botHor": [rule("botHor", {}, "TBIM_Platea_CA_Isolata_600", 0.28,
                    "Floor finish / screed 8 / XPS 12 / RC raft 40", YEAR, FLOOR)],
    "topHor": [rule("topHor", {}, "TBIM_Copertura_Rovescia_450", 0.22,
                    "Gravel / XPS 16 / waterproofing / RC slab 30", YEAR, ROOF)],
    "intHor": [rule("intHor", {}, "TBIM_Solaio_PostTeso_350", 0.80,
                    "Raised floor 10 / post-tensioned RC slab 25", YEAR, FLOOR)],
    "intVer": [
        rule("intVer", {}, "TBIM_Parete_Cartongesso_125", 0.60, "Double gypsum board / mineral wool / stud 75",
             YEAR),
        rule("intVer", {"cnFC_contains_pr_OccupancyType": "Core"}, "TBIM_Nucleo_CA_400", 2.10,
             "Reinforced concrete core 40", YEAR),
    ],
    "extVer": [
        rule("extVer", {}, "TBIM_Facciata_Continua_Cellula_200", 1.10,
             "Unitized curtain wall, triple glazing, insulated spandrel", YEAR),
        rule("extVer", {"cnFC_contains_pr_OccupancyType": "Plant"}, "TBIM_Schermo_Impianti_150", 0.35,
             "Metal louvres on insulated panel", YEAR),
    ],
}
APERTURES = {
    "windows": [["Office", "TBIM_Vetrata_Ufficio_800x280", 800, 280, 30],
                ["Lobby", "TBIM_Vetrata_Atrio_800x400", 800, 400, 40],
                ["Cafe", "TBIM_Vetrata_Atrio_800x400", 800, 400, 40],
                ["Shop", "TBIM_Vetrina_800x400", 800, 400, 40]],
    "external_doors": [["Lobby", "TBIM_Ingresso_Girevole_300x300", 300, 300]],
    "doors": [["Core", "", "TBIM_Porta_REI120_100x220", 100, 220],
              ["Lobby", "", "TBIM_Porta_Vetro_200x250", 200, 250],
              ["Office", "Office", "TBIM_Porta_Ufficio_90x220", 90, 220]],
    "window_data": {"pr_FrameMaterial": "Aluminium, thermal break", "pr_Glazing": "Triple glazing, low-e",
                    "pr_ThermalTransmittance": 1.0, "pr_SolarFactor": 0.30, "pr_ConstructionYear": YEAR},
    "door_data": {"pr_ConstructionYear": YEAR},
}

if __name__ == "__main__":
    write_project(HERE, "Office Tower", "Invented 20-storey office tower: RC core, ring of offices, unitized "
                  "curtain wall, double-height lobby.", rooms(), 20.0, ILDS, BY_OCCUPANCY, IRS, APERTURES,
                  table=lambda r: {"pr_FinishFloor": "Raised access floor" if "Office" in r.occupancy else "Stone",
                                   "pr_ConstructionYear": YEAR})
