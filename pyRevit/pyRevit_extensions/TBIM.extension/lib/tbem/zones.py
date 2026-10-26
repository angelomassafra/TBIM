"""Thermal zones of the TBEM (pure Python).

``assign`` gives each cell its zone: the TBIM zone (``rl_HasLocation_tpZN``, from Loads > Clusterize) or a new
clustering with the TBEM settings, then the zones changed by hand (``tbem_Zones.json``), the occupancy types
forming a zone on their own and the cells left out of the model (zone None).

``aggregate`` transfers the energy data of the cells to their zone, as the BIM-to-BEM conversion of
digitman_bim2bem (``TopologicZoneInheritSpaceData``): densities weighted by area, air changes by volume,
outdoor air per person by occupants; the zone is heated, cooled or ventilated if any of its cells is; heating
set-point the highest, cooling set-point the lowest; occupancy type and schedules of the most occupied cell.
"""
from tbim import analysis, zoning

ZONE_KEY = "rl_HasLocation_tpZN"


def clusters(cells, lateral, settings):
    """{cell UID: zone} by tbim.zoning with the TBEM settings (zones named as Loads > Clusterize)."""
    options = settings["zoning"]
    result = zoning.zones(cells, lateral, kmeans_keys=options["kmeans_property_names"], k=options["n_clusters"])
    props = dict(cells)
    return dict((uid, "%s_BS%s" % (result.get(uid, "ZoneCluster").replace("ZoneCluster", "Zone"),
                                   analysis.storey_suffix(props[uid].get("rl_HasLocation_tpBS"))))
                for uid, _ in cells)


def assign(cells, settings, saved=None, base=None):
    """{cell UID: zone or None}. cells: [(UID, props)]; base: zones to start from (default: the TBIM zones);
    saved: zones set in the TBEM tab ({UID: zone or None})."""
    options = settings["zoning"]
    single = set(options["single_zone_occupancy_types"])
    excluded_types = set(options["excluded_occupancy_types"])
    excluded = set(options["excluded_cell_uids"])
    out = {}
    for uid, props in cells:
        zone = (base or {}).get(uid) or props.get(ZONE_KEY) or uid
        if props.get("pr_OccupancyType") in single:
            zone = uid
        if saved and uid in saved:
            zone = saved[uid]
        if uid in excluded or props.get("pr_OccupancyType") in excluded_types:
            zone = None
        out[uid] = zone
    return out


def members(assignment):
    """{zone: [cell UIDs]} in the order of the cells."""
    out = {}
    for uid, zone in assignment.items():
        if zone is not None:
            out.setdefault(zone, []).append(uid)
    return out


def _weighted(items, key, weight):
    total = sum(d[weight] for d in items)
    return sum(d[key] * d[weight] for d in items) / total if total else 0.0


def _prevailing(items):
    """The most occupied cell (the largest one if none is occupied)."""
    return max(items, key=lambda d: (d["occupants"], d["area"]))


def aggregate(zone, items):
    """Energy data of a zone from the ``programs.space_data`` of its cells."""
    heated = [d for d in items if d["pr_IsHeated"]]
    cooled = [d for d in items if d["pr_IsCooled"]]
    main = _prevailing(items)
    humidity_min = [d["pr_HumidityMin"] for d in items if d["pr_HumidityMin"] is not None]
    humidity_max = [d["pr_HumidityMax"] for d in items if d["pr_HumidityMax"] is not None]
    occupants = sum(d["occupants"] for d in items)
    data = {
        "UID": zone,
        "cells": [d["UID"] for d in items],
        "area": sum(d["area"] for d in items),
        "volume": sum(d["volume"] for d in items),
        "occupants": occupants,
        "pr_OccupancyType": main["pr_OccupancyType"],
        "pr_IsOccupied": any(d["pr_IsOccupied"] for d in items),
        "pr_IsHeated": bool(heated),
        "pr_IsCooled": bool(cooled),
        "pr_IsMechanicallyVentilated": any(d["pr_IsMechanicallyVentilated"] for d in items),
        "pr_OccupancyDensityOperation": _weighted(items, "pr_OccupancyDensityOperation", "area"),
        "pr_LightingPowerDensity": _weighted(items, "pr_LightingPowerDensity", "area"),
        "pr_EquipmentPowerDensity": _weighted(items, "pr_EquipmentPowerDensity", "area"),
        "pr_AirChangesPerHour": _weighted(items, "pr_AirChangesPerHour", "volume"),
        "pr_MechanicalVentilationRatePerPerson": _weighted(items, "pr_MechanicalVentilationRatePerPerson",
                                                           "occupants") if occupants else 0.0,
        "pr_SpaceTemperatureWinterMin": max(d["pr_SpaceTemperatureWinterMin"] for d in (heated or items)),
        "pr_SpaceTemperatureSummerMax": min(d["pr_SpaceTemperatureSummerMax"] for d in (cooled or items)),
        "pr_HumidityMin": max(humidity_min) if humidity_min else None,
        "pr_HumidityMax": min(humidity_max) if humidity_max else None,
    }
    for use in ("Occupancy", "Lighting", "Equipment", "Ventilation"):
        key = "rl_IsScheduledBy_%s" % use
        data[key] = main[key]
    data["rl_IsScheduledBy_Heating"] = _prevailing(heated)["rl_IsScheduledBy_Heating"] if heated else "AlwaysOff"
    data["rl_IsScheduledBy_Cooling"] = _prevailing(cooled)["rl_IsScheduledBy_Cooling"] if cooled else "AlwaysOff"
    return data
