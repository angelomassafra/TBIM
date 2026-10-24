"""ILDs, InstanceBIM data and Informational Rule Sets of the 1960s residential case study (Italian housing).

Envelope (typical of northern-Italian 1960s condominiums, cf. TABULA/EPISCOPE IT archetypes):
- reinforced-concrete frame; cavity walls: facing brick 12 cm + air gap 6 cm + hollow brick 8 cm + plaster
- clay-concrete (laterocemento) slabs 20+4 cm, hipped roof in clay tiles (coppi) on laterocemento
- anodized aluminium windows with single glazing
U-values in W/(m2 K).

    python make_rules.py
"""
import json
import os

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "json")


def ild(occupancy, circulation, occupied, heated, area_per_occupant):
    return {"pr_OccupancyType": occupancy, "pr_CirculationType": circulation, "pr_IsOccupied": occupied,
            "pr_IsHeated": heated, "pr_IsCooled": False, "pr_IsNaturallyVentilated": True,
            "pr_IsMechanicallyVentilated": False, "pr_AreaPerOccupantPeak": area_per_occupant}


ILDS = [
    ild("Default", "NoCirculation", False, False, 0),
    ild("Residential:LivingRoom", "NoCirculation", True, True, 8.0),
    ild("Residential:Bedroom", "NoCirculation", True, True, 7.0),
    ild("Residential:Kitchen", "NoCirculation", True, True, 8.0),
    ild("Support:Bathroom", "NoCirculation", True, True, 0),
    ild("Circulation:PrivateHallway", "PrivateCirculation", False, True, 0),
    ild("Circulation:Stair", "PublicCirculation", False, False, 0),
    ild("Circulation:EntranceHall", "PublicCirculation", False, False, 0),
    ild("Parking:Garage", "NoCirculation", False, False, 0),
    ild("Technical:BoilerRoom", "NoCirculation", False, False, 0),
    ild("Unconditioned:Attic", "NoCirculation", False, False, 0),
]


def occupancy_data(occupancy, density, ventilation, winter):
    return {"pr_OccupancyType": occupancy, "pr_OccupancyDensityOperation": density,
            "pr_OccupancyDensitySafety": density, "pr_MechanicalVentilationRatePerPerson": 0,
            "pr_MechanicalVentilationRatePerVolume": 0, "pr_NaturalVentilationRate": ventilation,
            "pr_SpaceTemperatureWinterMin": winter, "pr_SpaceTemperatureSummerMax": "NaN"}


BY_OCCUPANCY = [
    occupancy_data("Residential:LivingRoom", 0.04, 0.5, 20),
    occupancy_data("Residential:Bedroom", 0.04, 0.5, 20),
    occupancy_data("Residential:Kitchen", 0.04, 1.0, 20),
    occupancy_data("Support:Bathroom", 0, 1.0, 20),
    occupancy_data("Circulation:PrivateHallway", 0, 0.5, 18),
    occupancy_data("Circulation:Stair", 0, 0.5, "NaN"),
    occupancy_data("Circulation:EntranceHall", 0, 0.5, "NaN"),
    occupancy_data("Parking:Garage", 0, 2.0, "NaN"),
    occupancy_data("Technical:BoilerRoom", 0, 2.0, "NaN"),
    occupancy_data("Unconditioned:Attic", 0, 1.0, "NaN"),
]


def rule(face_type, conditions, style, u_value, layers, key="stFC_WallTypeName"):
    r = {"cnFC_equalTo_pr_TopologicalType": face_type}
    r.update(conditions)
    r.update({key: style, "stFC_ThermalTransmittance": u_value, "stFC_Layers": layers, "stFC_ConstructionYear": 1966})
    return r


FLOOR, ROOF = "stFC_FloorTypeName", "stFC_RoofTypeName"
IRS = {
    "tbim_IRS_botHorFaces.json": [
        rule("botHor", {}, "TBIM_Platea_CA_su_Vespaio_400", 1.80,
             "Pavimento in gres 2 / massetto 6 / platea c.a. 30 / magrone / vespaio in ghiaia", FLOOR),
    ],
    "tbim_IRS_topHorFaces.json": [
        rule("topHor", {}, "TBIM_Copertura_Piana_Torrino_280", 1.70,
             "Guaina bituminosa / massetto 4 / solaio laterocemento 20+4 / intonaco 1,5", ROOF),
        rule("extInc", {}, "TBIM_Tetto_Coppi_Laterocemento_260", 1.80,
             "Coppi in laterizio / listelli / solaio inclinato laterocemento 16+4 / intonaco 1,5", ROOF),
    ],
    "tbim_IRS_intHorFaces.json": [
        rule("intHor", {}, "TBIM_Solaio_Laterocemento_300", 1.60,
             "Graniglia 2 / massetto 4 / solaio laterocemento 20+4 / intonaco 1,5", FLOOR),
        rule("intHor", {"cnFC_contains_pr_OccupancyType": "Parking"}, "TBIM_Solaio_su_Autorimessa_300", 1.60,
             "Graniglia 2 / massetto 4 / solaio laterocemento 20+4 / intonaco 1,5 (verso locali non riscaldati)",
             FLOOR),
        rule("intHor", {"cnFC_contains_pr_OccupancyType": "Attic"}, "TBIM_Solaio_Sottotetto_260", 1.70,
             "Massetto 2 / solaio laterocemento 20+4 / intonaco 1,5 (sottotetto non riscaldato)", FLOOR),
    ],
    "tbim_IRS_intVerFaces.json": [
        rule("intVer", {}, "TBIM_Tramezzo_Forato_100", 2.30, "Intonaco 1 / laterizio forato 8 / intonaco 1"),
        rule("intVer", {"cnFC_contains_pr_OccupancyType": "Stair"}, "TBIM_Muro_Vano_Scala_250", 1.50,
             "Intonaco 1,5 / mattoni pieni 22 / intonaco 1,5"),
        rule("intVer", {"cnFC_contains_rl_HasLocation_tpBS": "BuildingStorey_0cm"}, "TBIM_Muro_Seminterrato_CA_250",
             2.80, "Calcestruzzo armato 25"),
    ],
    "tbim_IRS_extVerFaces.json": [
        rule("extVer", {}, "TBIM_Muro_CassaVuota_Cortina_300", 1.10,
             "Mattoni faccia vista 12 / intercapedine d'aria 6 / laterizio forato 8 / intonaco 1,5 "
             "(telaio in c.a. a vista)"),
        rule("extVer", {"cnFC_contains_rl_HasLocation_tpBS": "BuildingStorey_0cm"}, "TBIM_Muro_Controterra_CA_300",
             2.20, "Calcestruzzo armato 30 / impermeabilizzazione (seminterrato)"),
        rule("extVer", {"cnFC_contains_rl_HasLocation_tpBS": "BuildingStorey_1780cm"}, "TBIM_Muro_Torrino_Forato_250",
             1.40, "Intonaco 1,5 / laterizio forato 22 / intonaco 1,5 (torrino scala)"),
    ],
}

OUTPUTS = [("tbim_ILDs.json", ILDS), ("tbim_InstanceBIM_byOccupancyType.json", BY_OCCUPANCY)] + list(IRS.items())
for name, data in OUTPUTS:
    with open(os.path.join(HERE, name), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print("written", name, len(data))
