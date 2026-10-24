"""School - a two-storey school with a gym (invented example).

L-shaped plan: a classroom wing (42 x 9.5 m, classrooms facing south along a north corridor, stair and
toilets behind it) and a single-storey gym with changing rooms under a gable roof.

    python make_model.py     # writes 3d/*.brep and the json inputs of the project
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, os.pardir, os.pardir, "tools"))

from building_kit import FLOOR, ROOF, Room, gable_attic, ild, occupancy_data, rule, write_project  # noqa: E402

YEAR = 1978
H = 350
GROUND = [("Circulation:EntranceHall", "Entrance hall"), ("Office:Administration", "Administration"),
          ("Education:Classroom", "Classroom 1A"), ("Education:Classroom", "Classroom 1B"),
          ("Education:Classroom", "Classroom 2A"), ("Education:Classroom", "Classroom 2B")]
FIRST = [("Education:Library", "Library"), ("Education:Laboratory", "Science lab"),
         ("Education:Classroom", "Classroom 3A"), ("Education:Classroom", "Classroom 3B"),
         ("Education:Classroom", "Classroom 4A"), ("Education:Classroom", "Classroom 4B")]


def rooms():
    out = []
    for storey, plan in enumerate((GROUND, FIRST)):
        z0, z1 = storey * H, (storey + 1) * H
        for i, (occupancy, name) in enumerate(plan):
            out.append(Room(i * 700, (i + 1) * 700, 0, 650, z0, z1, occupancy, "%d.%02d" % (storey, i + 1), name,
                            "Classrooms"))
        out.append(Room(0, 4200, 650, 950, z0, z1, "Circulation:Corridor", "%d.COR" % storey, "Corridor",
                        "Classrooms"))
        out.append(Room(0, 350, 950, 1550, z0, z1, "Circulation:Stair", "%d.STAIR" % storey, "Stair", "Classrooms"))
        out.append(Room(350, 700, 950, 1550, z0, z1, "Support:Restroom", "%d.WC" % storey, "Toilets",
                        "Classrooms"))
    out.append(Room(4200, 6000, 0, 1200, 0, 750, "Sports:Gym", "G.GYM", "Gym", "Gym"))
    for i, (occupancy, name) in enumerate((("Support:ChangingRoom", "Changing room A"),
                                           ("Support:ChangingRoom", "Changing room B"),
                                           ("Storage:Equipment", "Equipment store"))):
        out.append(Room(4200 + i * 600, 4800 + i * 600, 1200, 1800, 0, H, occupancy, "G.%02d" % (i + 1), name,
                        "Gym"))
    attic = Room(5050, 5150, 550, 650, 750, 790, "Unconditioned:Attic", "G.ATTIC", "Gym roof void", "Gym")
    attic.cell = gable_attic(4200, 6000, 0, 1200, 750, 180)
    out.append(attic)
    return out


ILDS = [
    ild("Default", "NoCirculation", False, False, False, False, False, 0),
    ild("Education:Classroom", "NoCirculation", True, True, False, True, False, 1.8),
    ild("Education:Library", "NoCirculation", True, True, False, True, False, 4.0),
    ild("Education:Laboratory", "NoCirculation", True, True, False, True, True, 2.5),
    ild("Office:Administration", "NoCirculation", True, True, False, True, False, 10.0),
    ild("Circulation:EntranceHall", "PublicCirculation", False, True, False, True, False, 0),
    ild("Circulation:Corridor", "PublicCirculation", False, True, False, True, False, 0),
    ild("Circulation:Stair", "PublicCirculation", False, True, False, True, False, 0),
    ild("Support:Restroom", "NoCirculation", False, True, False, False, True, 0),
    ild("Sports:Gym", "NoCirculation", True, True, False, True, True, 6.0),
    ild("Support:ChangingRoom", "NoCirculation", True, True, False, False, True, 3.0),
    ild("Storage:Equipment", "NoCirculation", False, False, False, True, False, 0),
    ild("Unconditioned:Attic", "NoCirculation", False, False, False, True, False, 0),
]
BY_OCCUPANCY = [
    occupancy_data("Education:Classroom", 0.45, 25, 3.0, 20, "NaN"),
    occupancy_data("Education:Library", 0.20, 25, 2.0, 20, "NaN"),
    occupancy_data("Education:Laboratory", 0.35, 25, 3.0, 20, "NaN"),
    occupancy_data("Office:Administration", 0.10, 25, 1.5, 20, "NaN"),
    occupancy_data("Circulation:EntranceHall", 0, 0, 1.0, 18, "NaN"),
    occupancy_data("Circulation:Corridor", 0, 0, 1.0, 18, "NaN"),
    occupancy_data("Circulation:Stair", 0, 0, 1.0, 18, "NaN"),
    occupancy_data("Support:Restroom", 0, 0, 4.0, 20, "NaN"),
    occupancy_data("Sports:Gym", 0.15, 40, 2.0, 18, "NaN"),
    occupancy_data("Support:ChangingRoom", 0.30, 40, 4.0, 22, "NaN"),
    occupancy_data("Storage:Equipment", 0, 0, 0.5, "NaN", "NaN"),
    occupancy_data("Unconditioned:Attic", 0, 0, 1.0, "NaN", "NaN"),
]
IRS = {
    "botHor": [rule("botHor", {}, "TBIM_Solaio_Controterra_400", 1.10,
                    "Linoleum / screed 6 / RC slab 20 / crawl space", YEAR, FLOOR)],
    "topHor": [
        rule("topHor", {}, "TBIM_Copertura_Piana_Guaina_350", 0.95,
             "Bitumen membrane / screed / cork 3 / clay-concrete slab 20+4", YEAR, ROOF),
        rule("extInc", {}, "TBIM_Copertura_Lamiera_Grecata_200", 0.90,
             "Corrugated steel sheet / mineral wool 4 / steel trusses", YEAR, ROOF),
    ],
    "intHor": [
        rule("intHor", {}, "TBIM_Solaio_Laterocemento_300", 1.40, "Linoleum / screed / clay-concrete 20+4",
             YEAR, FLOOR),
        rule("intHor", {"cnFC_contains_pr_OccupancyType": "Attic"}, "TBIM_Controsoffitto_Palestra_150", 0.80,
             "Suspended ceiling / mineral wool 6", YEAR, FLOOR),
    ],
    "intVer": [
        rule("intVer", {}, "TBIM_Tramezzo_Forato_120", 2.10, "Plaster / hollow brick 10 / plaster", YEAR),
        rule("intVer", {"cnFC_contains_pr_OccupancyType": "Corridor"}, "TBIM_Muro_Corridoio_250", 1.30,
             "Plaster / perforated brick 22 / plaster", YEAR),
        rule("intVer", {"cnFC_contains_pr_OccupancyType": "Gym"}, "TBIM_Muro_Palestra_CA_300", 2.00,
             "Reinforced concrete 30", YEAR),
    ],
    "extVer": [
        rule("extVer", {}, "TBIM_Muro_Laterizio_Isolato_350", 0.95,
             "Plaster / perforated brick 25 / polystyrene 3 / facing brick 6", YEAR),
        rule("extVer", {"cnFC_contains_pr_OccupancyType": "Gym"}, "TBIM_Pannello_Prefabbricato_CA_300", 1.20,
             "Precast sandwich panel: RC 8 / polystyrene 4 / RC 12", YEAR),
    ],
}
APERTURES = {
    "windows": [["Classroom", "TBIM_Finestra_Aula_300x180", 300, 180, 100],
                ["Library", "TBIM_Finestra_Aula_300x180", 300, 180, 100],
                ["Laboratory", "TBIM_Finestra_Aula_300x180", 300, 180, 100],
                ["Administration", "TBIM_Finestra_Ufficio_150x150", 150, 150, 100],
                ["Corridor", "TBIM_Finestra_Corridoio_150x150", 150, 150, 100],
                ["Stair", "TBIM_Finestra_Scala_100x200", 100, 200, 90],
                ["Restroom", "TBIM_Finestra_Bagno_80x60", 80, 60, 200],
                ["Gym", "TBIM_Finestra_Nastro_Palestra_600x120", 600, 120, 450],
                ["ChangingRoom", "TBIM_Finestra_Bagno_80x60", 80, 60, 200]],
    "external_doors": [["EntranceHall", "TBIM_Portone_Ingresso_200x250", 200, 250],
                       ["Gym", "TBIM_Porta_Antipanico_150x240", 150, 240]],
    "doors": [["Corridor", "", "TBIM_Porta_Aula_100x220", 100, 220],
              ["Gym", "", "TBIM_Porta_Palestra_120x220", 120, 220]],
    "window_data": {"pr_FrameMaterial": "Aluminium, no thermal break", "pr_Glazing": "Double glazing 4-6-4",
                    "pr_ThermalTransmittance": 3.3, "pr_SolarFactor": 0.75, "pr_ConstructionYear": YEAR},
    "door_data": {"pr_ConstructionYear": YEAR},
}

if __name__ == "__main__":
    write_project(HERE, "School", "Invented two-storey school of the late 1970s: classroom wing along a corridor, "
                  "gym under a steel gable roof.", rooms(), 10.0, ILDS, BY_OCCUPANCY, IRS, APERTURES,
                  table=lambda r: {"pr_FinishFloor": "Linoleum" if "Gym" not in r.occupancy else "Sports flooring",
                                   "pr_ConstructionYear": YEAR})
