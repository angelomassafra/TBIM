"""Town Hall - a three-storey municipal building with a clock tower (invented example).

40 x 18 m plan: offices on both sides of a central block (entrance hall on the ground floor, a double-height
council chamber above it), corridors along the back, a hipped clay-tile roof and a clock tower with a
belfry on the front.

    python make_model.py     # writes 3d/*.brep and the json inputs of the project
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, os.pardir, os.pardir, "tools"))

from building_kit import FLOOR, ROOF, Room, hipped_attic, ild, occupancy_data, rule, write_project  # noqa: E402

YEAR = 1912
W, D = 4000, 1800
LEVELS = [(0, 450), (450, 900), (900, 1300)]
TOWER = (1750, 2250, 0, 500)
ROOF_RISE = 270
FRONT = {0: [("Office:PublicDesk", "Public desk"), ("Office:Registry", "Registry office")],
         1: [("Office:Private", "Councillor office"), ("Office:Private", "Mayor office")],
         2: [("Office:Administration", "Technical office"), ("Office:Administration", "Accounts office")]}
BACK = {0: ("Archive:Records", "Archive"), 1: ("Office:Administration", "Secretariat"),
        2: ("Office:Administration", "Planning office")}


def rooms():
    out = []
    for level, (z0, z1) in enumerate(LEVELS):
        for side, xs in (("W", (0, 750, 1500)), ("E", (2500, 3250, 4000))):
            for i in range(2):
                x0, x1 = xs[i], xs[i + 1]
                occupancy, name = FRONT[level][i]
                space = "%d%s.F%d" % (level, side, i + 1)
                out.append(Room(x0, x1, 0, 800, z0, z1, occupancy, space, name, "Municipio"))
                occupancy, name = BACK[level]
                out.append(Room(x0, x1, 1000, 1800, z0, z1, occupancy, "%d%s.B%d" % (level, side, i + 1), name,
                                "Municipio"))
            out.append(Room(xs[0], xs[2], 800, 1000, z0, z1, "Circulation:Corridor", "%d%s.COR" % (level, side),
                            "Corridor", "Municipio"))
    out.append(Room(1500, 2500, 0, D, 0, 450, "Circulation:EntranceHall", "0.HALL", "Entrance hall", "Municipio"))
    out.append(Room(1500, 2500, 0, D, 450, 1300, "Assembly:CouncilChamber", "1.CHAMBER", "Council chamber",
                    "Municipio"))
    attic = Room(950, 1050, 850, 950, 1300, 1400, "Unconditioned:Attic", "R.ATTIC", "Attic", "Tetto")
    attic.cell = hipped_attic(0, W, 0, D, 1300, ROOF_RISE, cuts=[TOWER + (1300, 2700)])
    out.append(attic)
    out.append(Room(*(TOWER + (1300, 2000)), occupancy="Civic:ClockTower", space="T.CLOCK", name="Clock room",
                    block="Torre"))
    out.append(Room(*(TOWER + (2000, 2700)), occupancy="Civic:Belfry", space="T.BELFRY", name="Belfry",
                    block="Torre"))
    return out


ILDS = [
    ild("Default", "NoCirculation", False, False, False, False, False, 0),
    ild("Office:PublicDesk", "NoCirculation", True, True, True, True, False, 5.0),
    ild("Office:Registry", "NoCirculation", True, True, True, True, False, 8.0),
    ild("Office:Private", "NoCirculation", True, True, True, True, False, 15.0),
    ild("Office:Administration", "NoCirculation", True, True, True, True, False, 10.0),
    ild("Archive:Records", "NoCirculation", False, True, False, False, True, 0),
    ild("Circulation:Corridor", "PublicCirculation", False, True, False, True, False, 0),
    ild("Circulation:EntranceHall", "PublicCirculation", True, True, False, True, False, 4.0),
    ild("Assembly:CouncilChamber", "NoCirculation", True, True, True, False, True, 1.2),
    ild("Unconditioned:Attic", "NoCirculation", False, False, False, True, False, 0),
    ild("Civic:ClockTower", "NoCirculation", False, False, False, True, False, 0),
    ild("Civic:Belfry", "NoCirculation", False, False, False, True, False, 0),
]
BY_OCCUPANCY = [
    occupancy_data("Office:PublicDesk", 0.20, 40, 0.5, 20, 26),
    occupancy_data("Office:Registry", 0.12, 40, 0.5, 20, 26),
    occupancy_data("Office:Private", 0.06, 40, 0.5, 20, 26),
    occupancy_data("Office:Administration", 0.10, 40, 0.5, 20, 26),
    occupancy_data("Archive:Records", 0, 0, 0.3, 16, 24),
    occupancy_data("Circulation:Corridor", 0, 0, 0.5, 18, "NaN"),
    occupancy_data("Circulation:EntranceHall", 0.25, 0, 1.0, 18, "NaN"),
    occupancy_data("Assembly:CouncilChamber", 0.80, 40, 0, 20, 26),
    occupancy_data("Unconditioned:Attic", 0, 0, 1.0, "NaN", "NaN"),
    occupancy_data("Civic:ClockTower", 0, 0, 1.0, "NaN", "NaN"),
    occupancy_data("Civic:Belfry", 0, 0, 5.0, "NaN", "NaN"),
]
IRS = {
    "botHor": [rule("botHor", {}, "TBIM_Vespaio_Pavimento_Graniglia_450", 1.70,
                    "Terrazzo / lime screed / brick vault crawl space (vespaio)", YEAR, FLOOR)],
    "topHor": [
        rule("topHor", {}, "TBIM_Copertura_Torre_Piombo_200", 2.50, "Lead sheet / timber boarding / beams",
             YEAR, ROOF),
        rule("extInc", {}, "TBIM_Tetto_Coppi_Capriate_250", 2.20,
             "Clay tiles (coppi) / clay tiles board / timber trusses", YEAR, ROOF),
    ],
    "intHor": [
        rule("intHor", {}, "TBIM_Solaio_Putrelle_Voltine_350", 1.40,
             "Terrazzo / screed / steel I-beams with brick vaults", YEAR, FLOOR),
        rule("intHor", {"cnFC_contains_pr_OccupancyType": "Attic"}, "TBIM_Solaio_Sottotetto_Incannucciato_250", 1.60,
             "Timber floor / reed-and-plaster ceiling", YEAR, FLOOR),
    ],
    "intVer": [
        rule("intVer", {}, "TBIM_Tramezzo_Mattoni_Pieni_150", 2.10, "Lime plaster / solid brick 12 / lime plaster",
             YEAR),
        rule("intVer", {"cnFC_contains_pr_OccupancyType": "Corridor"}, "TBIM_Muro_Spina_Mattoni_450", 1.20,
             "Lime plaster / solid brick 42 / lime plaster (spine wall)", YEAR),
    ],
    "extVer": [
        rule("extVer", {}, "TBIM_Muratura_Mattoni_Bugnato_600", 0.95,
             "Rusticated render / solid brick 55 / lime plaster", YEAR),
        rule("extVer", {"cnFC_contains_pr_OccupancyType": "Civic"}, "TBIM_Muratura_Torre_Mattoni_450", 1.20,
             "Exposed solid brick 45 (tower)", YEAR),
    ],
}
APERTURES = {
    "windows": [["Office", "TBIM_Finestra_Legno_Arco_120x240", 120, 240, 90],
                ["Archive", "TBIM_Finestra_Inferriata_80x100", 80, 100, 220],
                ["Assembly", "TBIM_Finestrone_Sala_Consiliare_160x420", 160, 420, 200],
                ["EntranceHall", "TBIM_Finestra_Legno_Arco_120x240", 120, 240, 90],
                ["Corridor", "TBIM_Finestra_Corridoio_100x200", 100, 200, 100],
                ["ClockTower", "TBIM_Quadrante_Orologio_200x200", 200, 200, 300],
                ["Belfry", "TBIM_Bifora_Campanaria_200x350", 200, 350, 200]],
    "external_doors": [["EntranceHall", "TBIM_Portone_Municipio_250x380", 250, 380]],
    "doors": [["EntranceHall", "Corridor", "TBIM_Porta_Vetri_Atrio_160x280", 160, 280],
              ["CouncilChamber", "Corridor", "TBIM_Porta_Sala_Consiliare_160x300", 160, 300],
              ["Corridor", "", "TBIM_Porta_Legno_Pannelli_100x240", 100, 240]],
    "window_data": {"pr_FrameMaterial": "Wood", "pr_Glazing": "Single glazing", "pr_ThermalTransmittance": 4.9,
                    "pr_SolarFactor": 0.85, "pr_ConstructionYear": YEAR},
    "door_data": {"pr_Material": "Wood", "pr_ConstructionYear": YEAR},
}

if __name__ == "__main__":
    write_project(HERE, "Town Hall", "Invented early-20th-century town hall: brick masonry, steel-and-vault slabs, "
                  "double-height council chamber, hipped roof, clock tower.", rooms(), 0.0, ILDS, BY_OCCUPANCY,
                  IRS, APERTURES,
                  table=lambda r: {"pr_FinishFloor": "Terrazzo", "pr_ConstructionYear": YEAR})
