"""Masseria - a fortified farmhouse of southern Italy (invented example).

30 x 30 m courtyard plan in tuff masonry: vaulted ground-floor wings (stables, oil mill, chapel, wine
cellar, stores, granary, the farmer's house), the owner's house on the north wing and a defensive tower
with a dovecote on the south-east corner. Flat roof terraces (lastrici solari).

    python make_model.py     # writes 3d/*.brep and the json inputs of the project
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, os.pardir, os.pardir, "tools"))

from building_kit import FLOOR, ROOF, Room, ild, occupancy_data, rule, write_project  # noqa: E402

YEAR = 1760
G = 500  # vaulted ground floor
UPPER = 900
GROUND = [  # x0, x1, y0, y1, occupancy, space, name
    (0, 800, 0, 800, "Agricultural:Storage", "deposito", "Deposito"),
    (800, 1500, 0, 800, "Circulation:Passage", "androne", "Androne"),
    (1500, 2200, 0, 800, "Agricultural:Stable", "stalla", "Stalla"),
    (2200, 3000, 0, 800, "Agricultural:Stable", "torre_stalla", "Stalla della torre"),
    (0, 1500, 2200, 3000, "Agricultural:OilMill", "frantoio", "Frantoio"),
    (1500, 2200, 2200, 3000, "Religious:Chapel", "cappella", "Cappella"),
    (2200, 3000, 2200, 3000, "Agricultural:WineCellar", "cantina", "Cantina"),
    (0, 800, 800, 1500, "Agricultural:Storage", "magazzino", "Magazzino"),
    (0, 800, 1500, 2200, "Agricultural:Granary", "granaio", "Granaio"),
    (2200, 3000, 800, 1500, "Agricultural:Stable", "ovile", "Ovile"),
    (2200, 3000, 1500, 2200, "Residential:Dwelling", "casa_massaro", "Casa del massaro"),
]
OWNER = [  # owner's house on the north wing
    (0, 750, "Residential:Bedroom", "camera_ovest", "Camera ovest"),
    (750, 1500, "Residential:LivingRoom", "salone", "Salone"),
    (1500, 2250, "Residential:Kitchen", "cucina", "Cucina"),
    (2250, 3000, "Residential:Bedroom", "camera_est", "Camera est"),
]


def rooms():
    out = [Room(x0, x1, y0, y1, 0, G, occ, "PT." + space, name, "Corpo_Basso")
           for x0, x1, y0, y1, occ, space, name in GROUND]
    out += [Room(x0, x1, 2200, 3000, G, UPPER, occ, "P1." + space, name, "Casa_Padronale")
            for x0, x1, occ, space, name in OWNER]
    out.append(Room(2200, 3000, 0, 800, G, UPPER, "Defensive:Tower", "T.torre", "Torre", "Torre"))
    out.append(Room(2350, 2850, 150, 650, UPPER, 1250, "Agricultural:Dovecote", "T.colombaia", "Colombaia",
                    "Torre"))
    return out


ILDS = [
    ild("Default", "NoCirculation", False, False, False, False, False, 0),
    ild("Residential:Bedroom", "NoCirculation", True, True, False, True, False, 15.0),
    ild("Residential:LivingRoom", "NoCirculation", True, True, False, True, False, 15.0),
    ild("Residential:Kitchen", "NoCirculation", True, True, False, True, False, 15.0),
    ild("Residential:Dwelling", "NoCirculation", True, True, False, True, False, 15.0),
    ild("Circulation:Passage", "PublicCirculation", False, False, False, True, False, 0),
    ild("Religious:Chapel", "NoCirculation", True, False, False, True, False, 1.5),
    ild("Agricultural:Stable", "NoCirculation", False, False, False, True, False, 0),
    ild("Agricultural:Storage", "NoCirculation", False, False, False, True, False, 0),
    ild("Agricultural:Granary", "NoCirculation", False, False, False, True, False, 0),
    ild("Agricultural:OilMill", "NoCirculation", True, False, False, True, False, 20.0),
    ild("Agricultural:WineCellar", "NoCirculation", False, False, False, True, False, 0),
    ild("Defensive:Tower", "NoCirculation", False, False, False, True, False, 0),
    ild("Agricultural:Dovecote", "NoCirculation", False, False, False, True, False, 0),
]
BY_OCCUPANCY = [occupancy_data(i["pr_OccupancyType"], 0.05 if i["pr_IsOccupied"] else 0, 0, 0.5,
                               18 if i["pr_IsHeated"] else "NaN", "NaN") for i in ILDS[1:]]
IRS = {
    "botHor": [rule("botHor", {}, "TBIM_Battuto_Chianche_300", 2.00,
                    "Limestone slabs (chianche) / lime mortar / compacted earth", YEAR, FLOOR)],
    "topHor": [rule("topHor", {}, "TBIM_Lastrico_Solare_Volta_600", 1.30,
                    "Lime-tuff screed (lastrico) / fill / tuff vault 30", YEAR, ROOF)],
    "intHor": [rule("intHor", {}, "TBIM_Volta_a_Stella_Tufo_600", 1.20, "Pavement / fill / tuff star vault 30",
                    YEAR, FLOOR)],
    "intVer": [rule("intVer", {}, "TBIM_Muratura_Tufo_500", 1.40, "Lime plaster / tuff ashlar 45 / lime plaster",
                    YEAR)],
    "extVer": [
        rule("extVer", {}, "TBIM_Muratura_Tufo_Scarpata_900", 0.95,
             "Lime plaster / tuff ashlar 85 with battered base / whitewash", YEAR),
        rule("extVer", {"cnFC_contains_pr_OccupancyType": "Dovecote"}, "TBIM_Muratura_Tufo_400", 1.60,
             "Tuff ashlar 40 with nesting holes", YEAR),
    ],
}
APERTURES = {
    "windows": [["Residential", "TBIM_Finestra_Legno_Scuri_90x140", 90, 140, 90],
                ["Chapel", "TBIM_Finestra_Cappella_80x200", 80, 200, 200],
                ["Tower", "TBIM_Feritoia_30x100", 30, 100, 150],
                ["Dovecote", "TBIM_Feritoia_30x100", 30, 100, 150],
                ["Agricultural", "TBIM_Finestrella_Areazione_60x60", 60, 60, 300]],
    "external_doors": [["Passage", "TBIM_Portale_Ligneo_300x400", 300, 400],
                       ["Chapel", "TBIM_Portale_Cappella_150x280", 150, 280],
                       ["Agricultural", "TBIM_Portone_Rustico_220x300", 220, 300],
                       ["Residential", "TBIM_Porta_Legno_100x230", 100, 230]],
    "doors": [["Residential", "Residential", "TBIM_Porta_Interna_Legno_90x220", 90, 220],
              ["Agricultural", "Agricultural", "TBIM_Arco_Passaggio_200x300", 200, 300],
              ["Tower", "Residential", "TBIM_Porta_Interna_Legno_90x220", 90, 220]],
    "window_data": {"pr_FrameMaterial": "Wood with shutters", "pr_Glazing": "Single glazing",
                    "pr_ThermalTransmittance": 5.0, "pr_SolarFactor": 0.85, "pr_ConstructionYear": YEAR},
    "door_data": {"pr_Material": "Wood", "pr_ConstructionYear": YEAR},
}

if __name__ == "__main__":
    write_project(HERE, "Masseria", "Invented fortified farmhouse of southern Italy (18th century): tuff "
                  "masonry, vaulted ground floor, courtyard, tower with dovecote.", rooms(), 15.0, ILDS,
                  BY_OCCUPANCY, IRS, APERTURES,
                  table=lambda r: {"pr_FinishFloor": "Chianche (limestone slabs)", "pr_ConstructionYear": YEAR})
