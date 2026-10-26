"""The Honeybee model of a TBEM level (CPython only).

``build`` runs the BIM-to-BEM conversion of digitman_bim2bem (01_bim_to_bem) on a TBIM CellComplex:

1. thermal zones of the cells (``zones.assign``) and their energy data (``programs``, ``zones.aggregate``);
2. Honeybee rooms of the zones (``geometry.rooms``), with the faces, boundary conditions and apertures of the
   level;
3. zone loads, as a program per zone: occupants, lighting and equipment with their schedules, outdoor air
   (per person, or air changes), infiltration by airtightness; heating and cooling set-points and an ideal
   loads air system with the availability schedules of the zone (heated and/or cooled zones only);
4. Full TBEM: opaque constructions from the styles, simple glazing, external blinds, context shades.
"""
from honeybee.altnumber import autosize, no_limit
from honeybee.model import Model
from honeybee.typing import clean_ep_string
from honeybee_energy.hvac.idealair import IdealAirSystem
from honeybee_energy.load.equipment import ElectricEquipment
from honeybee_energy.load.infiltration import Infiltration
from honeybee_energy.load.lighting import Lighting
from honeybee_energy.load.people import People
from honeybee_energy.load.setpoint import Setpoint
from honeybee_energy.load.ventilation import Ventilation
from honeybee_energy.programtype import ProgramType
from topologicpy.CellComplex import CellComplex

from tbem import constructions, geometry, programs, schedules, zones
from tbem.files import FULL
from tbem.settings import INFILTRATION_FLOW_RATES
from tbim import instancebim, topo
from tbim.loads import lateral_adjacency

MIN_SETPOINT_GAP = 1.0  # C between the heating and the cooling set-points


def cells(cc):
    """[(UID, props, gross area m2, gross volume m3)] of the cells."""
    out = []
    for cell in CellComplex.Cells(cc):
        area, volume, _ = instancebim.gross_geometry(cell)
        out.append((topo.cell_uid(cell), topo.props(cell), area, volume))
    return out


def clusters(cc, settings):
    """{cell UID: zone} of a new clustering of the cells with the TBEM settings."""
    lateral = lateral_adjacency(cc, topo.face_groups(cc))
    return zones.clusters([(c[0], c[1]) for c in cells(cc)], lateral, settings)


def zone_data(cell_list, assignment, program_list):
    """{room identifier (the cleaned zone name): aggregated energy data}."""
    data = dict((uid, programs.space_data(props, programs.resolve(program_list, props.get("pr_OccupancyType")),
                                          area, volume))
                for uid, props, area, volume in cell_list)
    return dict((clean_ep_string(zone), zones.aggregate(zone, [data[uid] for uid in uids]))
                for zone, uids in zones.members(assignment).items())


class Schedules(object):
    """Schedules of the library by identifier; missing ones fall back to AlwaysOn/AlwaysOff (recorded)."""

    def __init__(self, library):
        self.rulesets = schedules.rulesets(library)
        for identifier, value in (("AlwaysOn", 1), ("AlwaysOff", 0)):
            if identifier not in self.rulesets:
                self.rulesets[identifier] = schedules.constant(identifier, value, "fraction")
        self.missing = set()
        self.constants = {}

    def get(self, identifier, fallback="AlwaysOff"):
        if identifier not in self.rulesets:
            self.missing.add(identifier)
            identifier = fallback
        return self.rulesets[identifier]

    def constant(self, identifier, value, kind):
        key = (identifier, value)
        if key not in self.constants:
            self.constants[key] = schedules.constant(clean_ep_string("%s %g" % (identifier, value)), value, kind)
        return self.constants[key]


def program(room, z, library, settings):
    """Program and ideal loads of a room from its zone data ``z``."""
    uid = room.identifier
    occupancy = library.get(z["rl_IsScheduledBy_Occupancy"])
    people = lighting = equipment = ventilation = setpoint = None
    if z["pr_OccupancyDensityOperation"] > 0:
        people = People("People_%s" % uid, z["pr_OccupancyDensityOperation"], occupancy)
    if z["pr_LightingPowerDensity"] > 0:
        lighting = Lighting("Lighting_%s" % uid, z["pr_LightingPowerDensity"],
                            library.get(z["rl_IsScheduledBy_Lighting"]))
    if z["pr_EquipmentPowerDensity"] > 0:
        equipment = ElectricEquipment("Equipment_%s" % uid, z["pr_EquipmentPowerDensity"],
                                      library.get(z["rl_IsScheduledBy_Equipment"]))
    per_person, air_changes = z["pr_MechanicalVentilationRatePerPerson"], z["pr_AirChangesPerHour"]
    if per_person > 0 or air_changes > 0:
        ventilation = Ventilation("Ventilation_%s" % uid, flow_per_person=per_person / 1000.0,
                                  air_changes_per_hour=air_changes,
                                  schedule=library.get(z["rl_IsScheduledBy_Ventilation"]), method="Max")
    rate = INFILTRATION_FLOW_RATES[settings["infiltration"]["building_airtightness"]]
    infiltration = Infiltration("Infiltration_%s" % uid, rate, library.get("AlwaysOn"))
    conditioned = z["pr_IsHeated"] or z["pr_IsCooled"]
    if conditioned:
        heating = z["pr_SpaceTemperatureWinterMin"]
        cooling = max(z["pr_SpaceTemperatureSummerMax"], heating + MIN_SETPOINT_GAP)
        setpoint = Setpoint("Setpoint_%s" % uid, library.constant("Heating setpoint", heating, "temperature"),
                            library.constant("Cooling setpoint", cooling, "temperature"))
        if z["pr_HumidityMin"] is not None:
            setpoint.humidifying_schedule = library.constant("Humidifying setpoint", z["pr_HumidityMin"], "humidity")
        if z["pr_HumidityMax"] is not None:
            setpoint.dehumidifying_schedule = library.constant("Dehumidifying setpoint", z["pr_HumidityMax"],
                                                               "humidity")
    room.properties.energy.program_type = ProgramType(
        "Program_%s" % uid, people=people, lighting=lighting, electric_equipment=equipment,
        infiltration=infiltration, ventilation=ventilation, setpoint=setpoint)
    if conditioned:
        hvac = settings["hvac"]
        limit = autosize if settings["simulation"].get("ddy") else no_limit
        room.properties.energy.hvac = IdealAirSystem(
            "IdealAir_%s" % uid, economizer_type=hvac["economizer_type"],
            demand_controlled_ventilation=hvac["demand_controlled_ventilation"],
            sensible_heat_recovery=hvac["sensible_heat_recovery"], latent_heat_recovery=hvac["latent_heat_recovery"],
            heating_limit=limit if z["pr_IsHeated"] else no_limit,
            cooling_limit=limit if z["pr_IsCooled"] else no_limit,
            heating_availability=library.get(z["rl_IsScheduledBy_Heating"], "AlwaysOn"),
            cooling_availability=library.get(z["rl_IsScheduledBy_Cooling"], "AlwaysOn"))


def assign_constructions(room_list, faces_by_id, subfaces, settings):
    """Full TBEM: constructions of the faces and apertures. Return the construction library."""
    library = constructions.Library(settings)
    for room in room_list:
        for face in room.faces:
            side = faces_by_id[face.identifier]
            construction = library.construction(side["props"], geometry.reversed_layers(side))
            if construction is not None:
                face.properties.energy.construction = construction
            for aperture in face.apertures:
                props, host = subfaces.get(aperture.identifier, ({}, side))
                window = library.window(props)
                if settings["blinds"]["enabled"] and programs.flag(host["props"].get("stFC_ShadingDevice")):
                    window = library.with_blind(window)
                aperture.properties.energy.construction = window
    return library


def build(cc, level, settings, program_list, schedule_library, saved_zones=None, aperture_polygons=(),
          shade_paths=(), name="TBEM"):
    """Honeybee model of ``level``. Return (model, {zone: summary}, report lines)."""
    cell_list = cells(cc)
    assignment = zones.assign([(c[0], c[1]) for c in cell_list], settings, saved_zones)
    data = zone_data(cell_list, assignment, program_list)
    room_list, faces_by_id, subfaces, problems = geometry.rooms(cc, assignment, level, settings, aperture_polygons)
    library = Schedules(schedule_library)
    for room in room_list:
        program(room, data[room.identifier], library, settings)
    report = ["%d cells in %d thermal zones (%d cells left out)" % (
        len(cell_list), len(room_list), sum(1 for z in assignment.values() if z is None))]
    shades = []
    if level == FULL:
        construction_library = assign_constructions(room_list, faces_by_id, subfaces, settings)
        shades = geometry.shades(shade_paths)
        counts = construction_library.counts()
        report.append("Constructions: %(opaque)d opaque (%(materials)d materials), %(glazing)d glazing, "
                      "%(with blinds)d with external blinds" % counts)
        if construction_library.unknown:
            report.append("Styles without layers (Honeybee default construction): %s" %
                          ", ".join(sorted(construction_library.unknown)))
        report.append("Context shading: %d faces from %d BRep files" % (len(shades), len(shade_paths)))
    model = Model(clean_ep_string(name), rooms=room_list, orphaned_shades=shades, units="Meters",
                  tolerance=geometry.TOLERANCE, angle_tolerance=geometry.ANGLE_TOLERANCE)
    apertures = sum(len(f.apertures) for r in room_list for f in r.faces)
    doors = sum(len(f.doors) for r in room_list for f in r.faces)
    report.append("%d faces, %d windows, %d external doors" % (len(faces_by_id), apertures, doors))
    if library.missing:
        report.append("WARNING - schedules not in the library (AlwaysOn/AlwaysOff used): %s" %
                      ", ".join(sorted(library.missing)))
    report += ["WARNING - %s" % p for p in problems[:20]]
    summary = dict((room.identifier, {"cells": data[room.identifier]["cells"],
                                      "floor_area": round(room.floor_area, 2), "volume": round(room.volume, 2),
                                      "pr_OccupancyType": data[room.identifier]["pr_OccupancyType"],
                                      "heated": data[room.identifier]["pr_IsHeated"],
                                      "cooled": data[room.identifier]["pr_IsCooled"]})
                   for room in room_list)
    return model, summary, report


def check(model):
    """Honeybee validation of the model: report lines (empty if valid)."""
    text = model.check_all(raise_exception=False, detailed=False)
    return [line for line in text.splitlines() if line.strip()]
