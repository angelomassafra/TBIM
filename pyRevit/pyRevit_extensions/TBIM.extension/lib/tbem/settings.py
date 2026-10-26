"""Settings of the BIM-to-BEM conversion and of the simulation (pure Python).

``tbem_Settings.json`` holds only the values that differ from ``DEFAULTS``; ``load`` merges them, section by
section. Face and cell UIDs are those of the TBIM (e.g. 'extVerFace8', 'Cell3'); flow rates and areas in SI.
"""
import copy
import os

from tbem import files
from tbim.jsonio import read_json, write_json

# Infiltration flow per exterior surface area (m3/s per m2) by building airtightness, as in the Honeybee
# "Set EnergyPlus Zone Loads" component and digitman_bim2bem
INFILTRATION_FLOW_RATES = {
    "PassiveHouse": 0.000071,
    "TightBuilding": 0.000100,
    "AverageBuilding": 0.000300,
    "LeakyBuilding": 0.000600,
}

# Fixed horizontal aluminium blinds of digitman_bim2bem (BEM tuning of the Lecco campus models), with the slats
# overlapping (separation below the width: digitman's 0.50 m let the direct sun through at 0 degrees)
BLIND = {"slat_width": 0.30, "slat_separation": 0.25, "slat_thickness": 0.001, "slat_angle": 90,
         "slat_conductivity": 160, "solar_reflectance": 0.6, "visible_reflectance": 0.5, "emissivity": 0.9,
         "distance_to_glass": 0.30, "opening_multiplier": 0.5}

OUTPUT_VARIABLES = [
    "Zone Ideal Loads Supply Air Total Heating Energy",
    "Zone Ideal Loads Supply Air Total Cooling Energy",
    "Zone Ideal Loads Zone Total Heating Energy",
    "Zone Ideal Loads Zone Total Cooling Energy",
    "Zone Lights Electricity Energy",
    "Zone Electric Equipment Electricity Energy",
    "Zone People Occupant Count",
    "Zone Mean Air Temperature",
    "Zone Operative Temperature",
]

DEFAULTS = {
    "zoning": {
        # K-Means of the free cells (tbim.zoning); the other rules are those of Loads > Clusterize
        "n_clusters": 10,
        "kmeans_property_names": ["pr_AreaPerOccupantPeak", "pr_IsHeated", "pr_IsCooled"],
        # cells forming a zone on their own, and cells left out of the energy model
        "single_zone_occupancy_types": [],
        "excluded_occupancy_types": ["Void"],
        "excluded_cell_uids": [],
    },
    "boundary_conditions": {
        "ground_face_types": ["botHor"],
        "adiabatic_face_uids": [],      # e.g. walls shared with adjacent buildings
        "ground_face_uids": [],
        "outdoors_face_uids": [],
        "excluded_neighbour": "Adiabatic",  # faces towards cells left out of the model
    },
    "apertures": {
        "skylights": True,
        "external_doors": True,
        "glazed_wall_ratio": 0.8,       # walls whose layers are glazing (curtain walls): window-to-wall ratio
    },
    "glazing": {
        # simple glazing systems: U (W/m2K), solar heat gain coefficient, visible transmittance
        "default": {"u": 2.8, "shgc": 0.6, "vt": 0.7},
        "by_construction_year": [  # [last year, glazing]: windows with pr_ConstructionYear
            [1975, {"u": 5.7, "shgc": 0.8, "vt": 0.85}],
            [2005, {"u": 2.8, "shgc": 0.65, "vt": 0.75}],
            [9999, {"u": 1.4, "shgc": 0.45, "vt": 0.7}],
        ],
        "by_type_name": {},             # {stAP_TypeName: glazing}
    },
    "blinds": dict(BLIND, enabled=True),   # on the windows of faces styled with stFC_ShadingDevice
    "shades": [],                       # BRep files of context shading (relative to the bem folder)
    "infiltration": {"building_airtightness": "AverageBuilding"},
    "hvac": {"economizer_type": "NoEconomizer", "demand_controlled_ventilation": False,
             "sensible_heat_recovery": 0.0, "latent_heat_recovery": 0.0},
    "simulation": {
        "epw": None,                    # relative to the bem folder (Energy Simulation > Weather)
        "ddy": None,                    # design days: with them the ideal loads are sized
        "run_period": {"start": [1, 1], "end": [12, 31], "start_day_of_week": None},  # None: from the calendar
        "timestep": 6,
        "reporting_frequency": "Hourly",
        "solar_distribution": "FullExterior",
        "terrain": "City",
        "output_variables": OUTPUT_VARIABLES,
        "energyplus_folder": None,      # default: C:/EnergyPlusV24-2-0 (the version written by Honeybee)
    },
}


def merged(defaults, custom):
    """``custom`` over ``defaults``: dictionaries are merged key by key, other values replaced."""
    out = copy.deepcopy(defaults)
    for key, value in (custom or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = merged(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def load(path=None):
    path = path or files.bem_file(files.SETTINGS)
    return merged(DEFAULTS, read_json(path, default={}))


def save(settings, path=None):
    return write_json(path or files.bem_file(files.SETTINGS), settings)


def update(section, values, path=None):
    """Set ``values`` ({key: value}) in a section of the settings file. Return the settings."""
    path = path or files.bem_file(files.SETTINGS)
    custom = read_json(path, default={})
    custom.setdefault(section, {}).update(values)
    write_json(path, custom)
    return merged(DEFAULTS, custom)


def update_value(key, value, path=None):
    """Set a top-level value (e.g. 'shades') of the settings file. Return the settings."""
    path = path or files.bem_file(files.SETTINGS)
    custom = read_json(path, default={})
    custom[key] = value
    write_json(path, custom)
    return merged(DEFAULTS, custom)


def ensure_file(path=None):
    """Write the settings file with all the values (to be edited by hand). Return its path."""
    path = path or files.bem_file(files.SETTINGS)
    return save(load(path), path)


def energyplus_folder(settings):
    """EnergyPlus installation folder, or None if not found."""
    candidates = [settings["simulation"].get("energyplus_folder"), os.environ.get("ENERGYPLUS_DIR"),
                  r"C:\EnergyPlusV24-2-0"]
    for folder in candidates:
        if folder and os.path.isfile(os.path.join(folder, "energyplus.exe")):
            return folder
    return None
