"""ILDs, InstanceBIM data and Informational Rule Sets of the 1960s residential case study (Italian housing).

Envelope (typical of northern-Italian 1960s condominiums, cf. TABULA/EPISCOPE IT archetypes):
- reinforced-concrete frame; cavity walls: facing brick 12 cm + air gap 6 cm + hollow brick 8 cm + plaster
- clay-concrete slabs 20+4 cm, hipped roof in clay tiles on an inclined clay-concrete slab
- anodized aluminium windows with single glazing
Layers from the outside (top) to the inside (bottom), thicknesses in mm, materials of tbim.materials;
U-values in W/(m2 K), computed from the layers.

    python make_rules.py
"""
import json
import os
import sys

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "json")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir, "pyRevit",
                                "pyRevit_extensions", "TBIM.extension", "lib"))

from tbim import materials  # noqa: E402


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


def rule(face_type, conditions, name, layers, key="stFC_WallTypeName"):
    r = {"cnFC_equalTo_pr_TopologicalType": face_type}
    r.update(conditions)
    r.update({key: "%s_%d" % (name, round(materials.thickness(layers))),
              "stFC_ThermalTransmittance": materials.u_value(layers, face_type),
              "stFC_Layers": materials.text(layers), "stFC_ConstructionYear": 1966})
    return r


FLOOR, ROOF = "stFC_FloorTypeName", "stFC_RoofTypeName"
PLASTER = ("Lime-cement plaster", 15)
SLAB = ("Clay-concrete slab", 240)
IRS = {
    "tbim_IRS_botHorFaces.json": [
        rule("botHor", {}, "TBIM_RC_Basement_Slab", [
            ("Porcelain stoneware tiles", 10), ("Cement screed", 60), ("Reinforced concrete", 300),
            ("Lean concrete", 100), ("Gravel fill", 200)], FLOOR),
    ],
    "tbim_IRS_topHorFaces.json": [
        rule("topHor", {}, "TBIM_Turret_Flat_Roof", [
            ("Bitumen membrane", 8), ("Cement screed", 40), SLAB, PLASTER], ROOF),
        rule("extInc", {}, "TBIM_Clay_Tile_Pitched_Roof", [
            ("Clay roof tiles", 20), ("Cement mortar bed", 30), ("Clay-concrete slab", 200), PLASTER], ROOF),
    ],
    "tbim_IRS_intHorFaces.json": [
        rule("intHor", {}, "TBIM_Clay_Concrete_Floor", [
            ("Marble-chip terrazzo tiles", 20), ("Cement screed", 40), SLAB, PLASTER], FLOOR),
        rule("intHor", {"cnFC_contains_pr_OccupancyType": "Parking"}, "TBIM_RC_Floor_Over_Garage", [
            ("Marble-chip terrazzo tiles", 20), ("Cement screed", 40), ("Reinforced concrete", 220), PLASTER],
             FLOOR),
        rule("intHor", {"cnFC_contains_pr_OccupancyType": "Attic"}, "TBIM_Attic_Floor", [
            ("Cement screed", 30), SLAB, PLASTER], FLOOR),
    ],
    "tbim_IRS_intVerFaces.json": [
        rule("intVer", {}, "TBIM_Hollow_Brick_Partition", [PLASTER, ("Hollow clay brick", 80), PLASTER]),
        rule("intVer", {"cnFC_contains_pr_OccupancyType": "Stair"}, "TBIM_Solid_Brick_Stairwell_Wall", [
            PLASTER, ("Solid clay brick", 250), PLASTER]),
        rule("intVer", {"cnFC_contains_rl_HasLocation_tpBS": "BuildingStorey_0cm"}, "TBIM_RC_Basement_Wall", [
            ("Reinforced concrete", 250)]),
    ],
    "tbim_IRS_extVerFaces.json": [
        rule("extVer", {}, "TBIM_Brick_Cavity_Wall", [
            ("Facing brick", 120), ("Air cavity", 60), ("Hollow clay brick", 80), PLASTER]),
        rule("extVer", {"cnFC_contains_rl_HasLocation_tpBS": "BuildingStorey_0cm"}, "TBIM_RC_Retaining_Wall", [
            ("Bitumen membrane", 5), ("Reinforced concrete", 300)]),
        rule("extVer", {"cnFC_contains_rl_HasLocation_tpBS": "BuildingStorey_1780cm"}, "TBIM_Rendered_Turret_Wall", [
            ("Cream cement render", 15), ("Hollow clay brick", 250), PLASTER]),
    ],
}

# windows and doors (TopologicalBIM > By Rules, see tbim.apertures)
APERTURES = {
    "windows": [["LivingRoom", "TBIM_Anodized_Aluminium_French_Window_140x240", 140, 240, 0],
                ["Bedroom", "TBIM_Anodized_Aluminium_Window_120x150", 120, 150, 90],
                ["Kitchen", "TBIM_Anodized_Aluminium_Window_100x150", 100, 150, 90],
                ["Bathroom", "TBIM_Anodized_Aluminium_Window_60x100", 60, 100, 120]],
    "external_doors": [["EntranceHall", "TBIM_Anodized_Aluminium_Glazed_Door_180x240", 180, 240]],
    "entrance_levels": [280],  # the entrance hall is on the raised floor
    "doors": [["Stair", "PrivateHallway", "TBIM_Solid_Timber_Flat_Door_90x210", 90, 210],
              ["Stair", "EntranceHall", "TBIM_Hall_Stair_Opening_120x210", 120, 210],
              ["PrivateHallway", "Residential", "TBIM_Hollow_Core_Timber_Door_80x210", 80, 210],
              ["PrivateHallway", "Bathroom", "TBIM_Hollow_Core_Timber_Door_80x210", 80, 210]],
    "window_data": {"pr_FrameMaterial": "Anodized aluminium", "pr_Glazing": "Single glazing 4 mm",
                    "pr_ThermalTransmittance": 5.8, "pr_SolarFactor": 0.85, "pr_ConstructionYear": 1966},
    "door_data": {"pr_ConstructionYear": 1966},
}

OUTPUTS = [("tbim_ILDs.json", ILDS), ("tbim_InstanceBIM_byOccupancyType.json", BY_OCCUPANCY),
           ("tbim_TopologicalBIM_Rules.json", APERTURES)] + list(IRS.items())
for name, data in OUTPUTS:
    with open(os.path.join(HERE, name), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print("written", name, len(data))
