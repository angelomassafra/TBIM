"""BEM programs: the energy data of the spaces (pure Python).

A program is a dictionary of space properties keyed by ``pr_OccupancyType``, like an ILD: the occupancy type
itself (e.g. 'Education:Classroom'), its category (e.g. 'Education') or 'Default'. ``tbem_Programs.json`` is a
list of programs. The data of a cell win over its program, so the values of the TBIM (InstanceBIM tables, ILDs)
are kept and the programs only fill the gaps:

    pr_OccupancyDensityOperation            occupants per m2 (else 1 / pr_AreaPerOccupantPeak)
    pr_LightingPowerDensity                 W/m2
    pr_EquipmentPowerDensity                W/m2
    pr_SpaceTemperatureWinterMin            heating set-point (C)
    pr_SpaceTemperatureSummerMax            cooling set-point (C)
    pr_HumidityMin, pr_HumidityMax          humidifying and dehumidifying set-points (%), optional
    pr_MechanicalVentilationRatePerPerson   outdoor air of mechanically ventilated spaces (L/s per person)
    pr_MechanicalVentilationRate            same, as air changes per hour (when no rate per person)
    pr_NaturalVentilationRate               outdoor air of naturally ventilated spaces (air changes per hour)
    rl_IsScheduledBy_<use>                  identifier of a schedule of the library, for the uses
                                            Occupancy, Lighting, Equipment, Heating, Cooling, Ventilation
"""
import math

OCCUPANCY_KEY = "pr_OccupancyType"
DEFAULT = "Default"
USES = ["Occupancy", "Lighting", "Equipment", "Heating", "Cooling", "Ventilation"]
SCHEDULE_KEYS = ["rl_IsScheduledBy_%s" % use for use in USES]
ALWAYS_ON, ALWAYS_OFF = "AlwaysOn", "AlwaysOff"

DEFAULT_SETPOINTS = {"pr_SpaceTemperatureWinterMin": 20.0, "pr_SpaceTemperatureSummerMax": 26.0}


def number(value):
    """float(value), or None for missing, 'NaN', 'Undefined' and non numeric values."""
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(value) else value


def flag(value):
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "1.0")
    return bool(number(value))


def category(occupancy_type):
    return (occupancy_type or "").split(":")[0]


def resolve(programs, occupancy_type):
    """Program of an occupancy type: exact match, else its category, else 'Default' (else {})."""
    by_key = dict((p.get(OCCUPANCY_KEY), p) for p in programs)
    for key in (occupancy_type, category(occupancy_type), DEFAULT):
        if key in by_key:
            return by_key[key]
    return {}


def value(props, program, key):
    """Number of the cell, else of its program, else None."""
    cell_value = number(props.get(key))
    return cell_value if cell_value is not None else number(program.get(key))


def schedule(props, program, use, fallback):
    key = "rl_IsScheduledBy_%s" % use
    for source in (props, program):
        text = source.get(key)
        if text and str(text) not in ("NaN", "None", "Undefined"):
            return str(text).split(";")[0].strip()  # several schedules: the first one, as in digitman
    return fallback


def space_data(props, program, area, volume):
    """Energy data of a cell (``props``) from its properties and its program. ``area`` (m2) and ``volume`` (m3)
    are the gross ones of the cell geometry, used to weight the zone values."""
    occupied, heated, cooled = flag(props.get("pr_IsOccupied")), flag(props.get("pr_IsHeated")), \
        flag(props.get("pr_IsCooled"))
    mechanical = flag(props.get("pr_IsMechanicallyVentilated") or props.get("pr_IsMechanicalVentilated"))
    natural = flag(props.get("pr_IsNaturallyVentilated"))

    density = value(props, program, "pr_OccupancyDensityOperation")
    if density is None:
        area_per_occupant = number(props.get("pr_AreaPerOccupantPeak")) or number(program.get("pr_AreaPerOccupantPeak"))
        density = 1.0 / area_per_occupant if area_per_occupant else 0.0
    density = density if occupied else 0.0

    per_person = value(props, program, "pr_MechanicalVentilationRatePerPerson") if mechanical else None
    if per_person:
        air_changes = 0.0  # pr_MechanicalVentilationRate is derived from the rate per person (InstanceBIM)
    elif mechanical:
        air_changes = value(props, program, "pr_MechanicalVentilationRate") or 0.0
    else:
        air_changes = (value(props, program, "pr_NaturalVentilationRate") or 0.0) if natural else 0.0

    occupancy_schedule = schedule(props, program, "Occupancy", ALWAYS_OFF)
    data = {
        "UID": props.get("UID"),
        OCCUPANCY_KEY: props.get(OCCUPANCY_KEY) or DEFAULT,
        "area": area,
        "volume": volume,
        "occupants": density * area,
        "pr_IsOccupied": occupied,
        "pr_IsHeated": heated,
        "pr_IsCooled": cooled,
        "pr_IsMechanicallyVentilated": mechanical,
        "pr_OccupancyDensityOperation": density,
        "pr_LightingPowerDensity": value(props, program, "pr_LightingPowerDensity") or 0.0,
        "pr_EquipmentPowerDensity": value(props, program, "pr_EquipmentPowerDensity") or 0.0,
        "pr_MechanicalVentilationRatePerPerson": per_person or 0.0,
        "pr_AirChangesPerHour": air_changes,
        "pr_HumidityMin": value(props, program, "pr_HumidityMin"),
        "pr_HumidityMax": value(props, program, "pr_HumidityMax"),
        "rl_IsScheduledBy_Occupancy": occupancy_schedule,
        "rl_IsScheduledBy_Lighting": schedule(props, program, "Lighting", occupancy_schedule),
        "rl_IsScheduledBy_Equipment": schedule(props, program, "Equipment", occupancy_schedule),
        "rl_IsScheduledBy_Heating": schedule(props, program, "Heating", ALWAYS_ON) if heated else ALWAYS_OFF,
        "rl_IsScheduledBy_Cooling": schedule(props, program, "Cooling", ALWAYS_ON) if cooled else ALWAYS_OFF,
        "rl_IsScheduledBy_Ventilation": schedule(props, program, "Ventilation", occupancy_schedule),
    }
    for key, default in DEFAULT_SETPOINTS.items():
        setpoint = value(props, program, key)
        data[key] = default if setpoint is None else setpoint
    return data


def missing(programs, occupancy_types):
    """{occupancy type: keys taken from no program} - what the programs do not define for these types."""
    keys = ["pr_LightingPowerDensity", "pr_EquipmentPowerDensity"] + SCHEDULE_KEYS[:1]
    out = {}
    for occupancy_type in sorted(set(occupancy_types)):
        program = resolve(programs, occupancy_type)
        absent = [k for k in keys if program.get(k) is None]
        if absent:
            out[occupancy_type] = absent
    return out
