"""Fortified Farmhouse - a fortified farmhouse (masseria) of southern Italy (invented example).

30 x 30 m courtyard plan in tuff masonry: vaulted ground-floor wings (stables, oil mill, chapel, wine
cellar, stores, granary, the farmer's house), the owner's house on the north wing and a defensive tower
on the south-east corner, crowned by a dovecote turret. Flat roof terraces on the vaults.

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
    (0, 800, 0, 800, "Agricultural:Storage", "store_sw", "Store"),
    (800, 1500, 0, 800, "Circulation:Passage", "gateway", "Gateway"),
    (1500, 2200, 0, 800, "Agricultural:Stable", "stable", "Stable"),
    (2200, 3000, 0, 800, "Agricultural:Stable", "tower_stable", "Tower stable"),
    (0, 1500, 2200, 3000, "Agricultural:OilMill", "oil_mill", "Oil mill"),
    (1500, 2200, 2200, 3000, "Religious:Chapel", "chapel", "Chapel"),
    (2200, 3000, 2200, 3000, "Agricultural:WineCellar", "wine_cellar", "Wine cellar"),
    (0, 800, 800, 1500, "Agricultural:Storage", "storehouse", "Storehouse"),
    (0, 800, 1500, 2200, "Agricultural:Granary", "granary", "Granary"),
    (2200, 3000, 800, 1500, "Agricultural:Stable", "sheepfold", "Sheepfold"),
    (2200, 3000, 1500, 2200, "Residential:Dwelling", "farmer_house", "Farmer's house"),
]
OWNER = [  # owner's house on the north wing
    (0, 750, "Residential:Bedroom", "bedroom_w", "West bedroom"),
    (750, 1500, "Residential:LivingRoom", "hall", "Great hall"),
    (1500, 2250, "Residential:Kitchen", "kitchen", "Kitchen"),
    (2250, 3000, "Residential:Bedroom", "bedroom_e", "East bedroom"),
]


def rooms():
    out = [Room(x0, x1, y0, y1, 0, G, occ, "GF." + space, name, "Vaulted_Wings")
           for x0, x1, y0, y1, occ, space, name in GROUND]
    out += [Room(x0, x1, 2200, 3000, G, UPPER, occ, "FF." + space, name, "Owner_House")
            for x0, x1, occ, space, name in OWNER]
    out.append(Room(2200, 3000, 0, 800, G, UPPER, "Defensive:Tower", "T.tower", "Tower room", "Tower"))
    out.append(Room(2400, 3000, 0, 600, UPPER, 1250, "Agricultural:Dovecote", "T.dovecote", "Dovecote",
                    "Tower"))
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
    "botHor": [rule("botHor", {}, "TBIM_Limestone_Slab_Paving", [
        ("Limestone paving slabs", 60), ("Lime mortar bed", 40), ("Compacted earth", 200)], YEAR, FLOOR)],
    "topHor": [rule("topHor", {}, "TBIM_Vaulted_Roof_Terrace", [
        ("Lime-tuff roof screed", 50), ("Tuff rubble fill", 250), ("Tuff stone vault", 300)], YEAR, ROOF)],
    "intHor": [rule("intHor", {}, "TBIM_Tuff_Star_Vault", [
        ("Limestone paving slabs", 40), ("Tuff rubble fill", 260), ("Tuff stone vault", 300)], YEAR, FLOOR)],
    "intVer": [rule("intVer", {}, "TBIM_Tuff_Masonry_Wall", [
        ("Lime plaster", 20), ("Tuff ashlar", 460), ("Lime plaster", 20)], YEAR)],
    "extVer": [
        rule("extVer", {}, "TBIM_Whitewashed_Battered_Tuff_Wall", [
            ("Whitewashed lime render", 20), ("Tuff ashlar", 860), ("Lime plaster", 20)], YEAR),
        rule("extVer", {"cnFC_contains_pr_OccupancyType": "Defensive"}, "TBIM_Limestone_Tower_Wall", [
            ("Limestone ashlar", 150), ("Tuff ashlar", 630), ("Lime plaster", 20)], YEAR),
        rule("extVer", {"cnFC_contains_pr_OccupancyType": "Dovecote"}, "TBIM_Exposed_Tuff_Dovecote_Wall", [
            ("Exposed tuff ashlar", 400)], YEAR),
    ],
}
APERTURES = {
    "windows": [["Residential", "TBIM_Shuttered_Timber_Window_90x140", 90, 140, 90],
                ["Chapel", "TBIM_Chapel_Window_80x200", 80, 200, 200],
                ["Tower", "TBIM_Arrow_Slit_30x100", 30, 100, 150],
                ["Dovecote", "TBIM_Arrow_Slit_30x100", 30, 100, 150],
                ["Agricultural", "TBIM_Vent_Opening_60x60", 60, 60, 300]],
    "external_doors": [["Passage", "TBIM_Timber_Gateway_300x400", 300, 400],
                       ["Chapel", "TBIM_Chapel_Portal_150x280", 150, 280],
                       ["Agricultural", "TBIM_Barn_Door_220x300", 220, 300],
                       ["Residential", "TBIM_Timber_Door_100x230", 100, 230]],
    "doors": [["Residential", "Residential", "TBIM_Internal_Timber_Door_90x220", 90, 220],
              ["Agricultural", "Agricultural", "TBIM_Arched_Passage_200x300", 200, 300],
              ["Tower", "Residential", "TBIM_Internal_Timber_Door_90x220", 90, 220]],
    "window_data": {"pr_FrameMaterial": "Wood with shutters", "pr_Glazing": "Single glazing",
                    "pr_ThermalTransmittance": 5.0, "pr_SolarFactor": 0.85, "pr_ConstructionYear": YEAR},
    "door_data": {"pr_Material": "Wood", "pr_ConstructionYear": YEAR},
}

if __name__ == "__main__":
    write_project(HERE, "Fortified Farmhouse", "Invented fortified farmhouse (masseria) of southern Italy, 18th "
                  "century: whitewashed tuff masonry, vaulted ground floor, courtyard, limestone tower with a "
                  "dovecote.", rooms(), 15.0, ILDS, BY_OCCUPANCY, IRS, APERTURES,
                  table=lambda r: {"pr_FinishFloor": "Limestone slabs", "pr_ConstructionYear": YEAR})
