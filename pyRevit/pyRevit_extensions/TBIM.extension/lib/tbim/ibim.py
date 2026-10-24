"""Instance BIM: pure data rules (no topologicpy, no Revit)."""

PLACEHOLDERS = ("ByModel", "ByOccupancyType", "Inserire valore manualmente")
UNDEFINED = "Undefined"
MOVE_THRESHOLD_CM = 20

BOOLEAN_KEYS = ["pr_IsOccupied", "pr_IsRefugeArea", "pr_IsAboveGround", "pr_IsSafeSpace",
                "pr_IsTemporarySafeSpace", "pr_IsFireGapSpace", "pr_IsFilterSpace", "pr_IsFireStaircase",
                "pr_IsSmokeProof", "pr_IsProtected", "pr_IsCooled", "pr_IsHeated", "pr_IsMechanicalVentilated"]
SUM_KEYS = ["pr_NetArea", "pr_OccupancyNumber", "pr_OccupancyNumberPeak", "pr_GrossArea",
            "pr_NetVolume", "pr_GrossVolume"]
# ByModel keys measured on the model: they overwrite the values of the table of spaces
MEASURED_KEYS = ["pr_GrossArea", "pr_NetArea", "pr_GrossVolume", "pr_NetVolume", "pr_GrossHeight"]


def number(value):
    """float(value) or None for missing/placeholder/non numeric values."""
    if value is None or isinstance(value, bool):
        return None if value is None else float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def is_defined(value):
    return value is not None and value not in PLACEHOLDERS and str(value) != ""


def missing_only(current, new):
    """Values of ``new`` whose key is not already in ``current``."""
    return dict((k, v) for k, v in new.items() if k not in current)


# --------------------------------------------------------------------------------------
def aperture_movement(revit_xyz, recorded):
    """Movement (cm) of an aperture moved in Revit, or None if below the threshold.

    revit_xyz: current Revit location (cm); recorded: {'Revit': {'X','Y','Z'}, ...}
    location when the TBIM was generated. Only the main horizontal component is kept.
    """
    old = recorded["Revit"]
    dx, dy, dz = revit_xyz[0] - old["X"], revit_xyz[1] - old["Y"], revit_xyz[2] - old["Z"]
    if max(abs(dx), abs(dy), abs(dz)) <= MOVE_THRESHOLD_CM:
        return None
    if abs(dx) > abs(dy):
        dy = 0
    else:
        dx = 0
    return dx, dy, dz


def aggregate_spaces(rows):
    """Aggregate the rows of the table of spaces belonging to one cell.

    Boolean keys: 1 if any space is 1; sum keys: sum; text keys: distinct values joined
    with '; '; other keys: first defined value.
    """
    result = {}
    for row in rows:
        for key, value in row.items():
            if key == "UID" or not is_defined(value):
                continue
            if key in BOOLEAN_KEYS:
                result[key] = 1 if (number(value) or 0) > 0 or result.get(key) == 1 else 0
            elif key in SUM_KEYS and number(value) is not None:
                result[key] = (result.get(key) or 0) + number(value)
            elif key in result and number(value) is None and isinstance(result[key], str):
                if value not in result[key].split("; "):
                    result[key] += "; " + value
            elif key not in result:
                result[key] = value
    return result


def by_model(props, gross_area, gross_volume, gross_height, revit_net_area, revit_net_volume):
    """ByModel properties of a cell (areas m2, volumes m3, heights m)."""
    # measured Revit values win over the table of spaces (see MEASURED_KEYS)
    net_area = revit_net_area if revit_net_area else number(props.get("pr_NetArea"))
    net_volume = revit_net_volume

    density_op = number(props.get("pr_OccupancyDensityOperation"))
    occupants = number(props.get("pr_OccupancyNumber"))
    if occupants is None:
        if density_op is not None and net_area:
            occupants = int(density_op * net_area)
    elif net_area:
        density_op = occupants / net_area

    density_safety = number(props.get("pr_OccupancyDensitySafety"))
    occupants_peak = number(props.get("pr_OccupancyNumberPeak"))
    if occupants_peak is None:
        if density_safety is not None and net_area:
            occupants_peak = int(density_safety * net_area)
    elif net_area:
        density_safety = occupants_peak / net_area

    nominal_height = round(net_volume / net_area, 2) if net_area and net_volume else None

    per_person = number(props.get("pr_MechanicalVentilationRatePerPerson"))
    per_volume = number(props.get("pr_MechanicalVentilationRatePerVolume"))
    ventilation = None
    if per_person and occupants and net_volume:
        ventilation = round(per_person * 3600.0 / 1000.0 * occupants / net_volume, 5)
    elif per_volume:
        ventilation = per_volume

    values = {
        "pr_GrossArea": round(gross_area, 2),
        "pr_NetArea": round(net_area, 2) if net_area is not None else None,
        "pr_GrossVolume": round(gross_volume, 2),
        "pr_NetVolume": round(net_volume, 2) if net_volume is not None else None,
        "pr_GrossHeight": round(gross_height, 2) if gross_height is not None else None,
        "pr_OccupancyNumber": occupants,
        "pr_OccupancyNumberPeak": occupants_peak,
        "pr_OccupancyDensityOperation": density_op,
        "pr_OccupancyDensitySafety": density_safety,
        "pr_NominalHeight": nominal_height,
        "pr_MechanicalVentilationRate": ventilation,
        "pr_NaturalVentilationRate": props.get("pr_NaturalVentilationRate"),
    }
    return dict((k, UNDEFINED if v is None else v) for k, v in values.items())
