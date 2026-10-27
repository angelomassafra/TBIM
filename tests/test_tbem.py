"""TBEM: BIM-to-BEM conversion of the example projects (Honeybee) and EnergyPlus run."""
import os

import pytest

import tbim
from tbem import programs, results, zones
from tbem import settings as tbem_settings

ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
PROJECTS = os.path.join(ROOT, "projects")
# weather of Bologna shipped with the School example (TMYx 2011-2025, climate.onebuilding.org)
EPW = os.path.join(PROJECTS, "School", "bem", "weather", "ITA_ER_Bologna-Marconi.AP.161400_TMYx.2011-2025.epw")


def ibim(project):
    path = os.path.join(PROJECTS, project, "json", "tbim_CellComplex_IBIM.json")
    if not os.path.isfile(path):
        pytest.skip("no InstanceBIM in %s" % project)
    return path


# --------------------------------------------------------------------------------------
# Pure Python
def test_programs_resolve_by_type_category_and_default():
    items = [{"pr_OccupancyType": "Default", "a": 0}, {"pr_OccupancyType": "Education", "a": 1},
             {"pr_OccupancyType": "Education:Laboratory", "a": 2}]
    assert programs.resolve(items, "Education:Laboratory")["a"] == 2
    assert programs.resolve(items, "Education:Classroom")["a"] == 1
    assert programs.resolve(items, "Office:Office")["a"] == 0


def test_space_data_cell_values_win_and_ventilation_is_not_counted_twice():
    program = {"pr_LightingPowerDensity": 10, "pr_SpaceTemperatureWinterMin": 18,
               "rl_IsScheduledBy_Occupancy": "OccSch_Education"}
    cell = {"UID": "Cell0", "pr_IsOccupied": 1, "pr_IsHeated": 1, "pr_IsCooled": 0, "pr_IsMechanicallyVentilated": 1,
            "pr_OccupancyDensityOperation": 0.45, "pr_SpaceTemperatureWinterMin": 20,
            "pr_SpaceTemperatureSummerMax": "NaN", "pr_MechanicalVentilationRatePerPerson": 7.0,
            "pr_MechanicalVentilationRate": 4.06}
    data = programs.space_data(cell, program, 30.0, 90.0)
    assert data["pr_SpaceTemperatureWinterMin"] == 20 and data["pr_SpaceTemperatureSummerMax"] == 26
    assert data["pr_LightingPowerDensity"] == 10 and data["occupants"] == pytest.approx(13.5)
    assert data["pr_MechanicalVentilationRatePerPerson"] == 7.0 and data["pr_AirChangesPerHour"] == 0
    assert data["rl_IsScheduledBy_Lighting"] == "OccSch_Education"
    assert data["rl_IsScheduledBy_Cooling"] == "AlwaysOff"
    natural = programs.space_data({"pr_IsNaturallyVentilated": True, "pr_NaturalVentilationRate": 0.5,
                                   "pr_AreaPerOccupantPeak": 10, "pr_IsOccupied": True}, {}, 20.0, 60.0)
    assert natural["pr_AirChangesPerHour"] == 0.5 and natural["pr_OccupancyDensityOperation"] == pytest.approx(0.1)


def test_zone_aggregation_weights():
    a = programs.space_data({"UID": "A", "pr_IsOccupied": 1, "pr_IsHeated": 1, "pr_OccupancyDensityOperation": 0.5,
                             "pr_OccupancyType": "Education:Classroom", "pr_SpaceTemperatureWinterMin": 20},
                            {"pr_LightingPowerDensity": 10}, 30.0, 90.0)
    b = programs.space_data({"UID": "B", "pr_IsOccupied": 0, "pr_IsHeated": 1, "pr_OccupancyType": "Circulation",
                             "pr_SpaceTemperatureWinterMin": 18}, {"pr_LightingPowerDensity": 4}, 10.0, 30.0)
    zone = zones.aggregate("Z", [a, b])
    assert zone["area"] == 40 and zone["pr_OccupancyType"] == "Education:Classroom"
    assert zone["pr_LightingPowerDensity"] == pytest.approx((10 * 30 + 4 * 10) / 40.0)
    assert zone["pr_OccupancyDensityOperation"] == pytest.approx(15 / 40.0)
    assert zone["pr_SpaceTemperatureWinterMin"] == 20 and zone["cells"] == ["A", "B"]


def test_zone_assignment_rules():
    settings = tbem_settings.merged(tbem_settings.DEFAULTS, {"zoning": {
        "single_zone_occupancy_types": ["Lab"], "excluded_cell_uids": ["C3"]}})
    cells = [("C1", {"rl_HasLocation_tpZN": "Z1"}), ("C2", {"rl_HasLocation_tpZN": "Z1", "pr_OccupancyType": "Lab"}),
             ("C3", {"rl_HasLocation_tpZN": "Z1"}), ("C4", {"pr_OccupancyType": "Void"}),
             ("C5", {"rl_HasLocation_tpZN": "Z2"})]
    assignment = zones.assign(cells, settings, saved={"C5": "Z1"})
    assert assignment == {"C1": "Z1", "C2": "C2", "C3": None, "C4": None, "C5": "Z1"}


def test_results_of_a_readvars_csv(tmp_path):
    path = tmp_path / "tbem.csv"
    header = ["Date/Time", "ZONE1 IDEAL LOADS AIR SYSTEM:Zone Ideal Loads Supply Air Total Heating Energy [J](Hourly)",
              "ZONE10:Zone Lights Electricity Energy [J](Hourly)", "ZONE1:Zone Mean Air Temperature [C](Hourly) "]
    rows = [" 01/01  01:00:00,3600000,7200000,20", " 02/01  02:00:00,3600000,0,22"]
    path.write_text(",".join(header) + "\n" + "\n".join(rows) + "\n")
    summary = {"Zone1": {"floor_area": 2.0, "cells": ["A"]}, "Zone10": {"floor_area": 1.0, "cells": ["B", "C"]}}
    data = results.read(str(path), summary)
    assert data["zones"]["Zone1"]["heating"] == 2.0 and data["zones"]["Zone1"]["heating_per_m2"] == 1.0
    assert data["zones"]["Zone10"]["lighting"] == 2.0 and data["zones"]["Zone1"]["lighting"] == 0
    assert data["zones"]["Zone1"]["mean_air_temperature"] == 21
    assert results.by_cell(data, summary)["C"]["rs_EnergyZone"] == "Zone10"
    assert data["building"]["monthly"]["heating"][:3] == [1.0, 1.0, 0.0]
    assert data["building"]["monthly"]["lighting"][0] == 2.0
    temperature = "Zone Mean Air Temperature"
    assert data["metrics"][temperature + "|max"] == "Zone Mean Air Temperature - maximum (C)"
    assert data["zones"]["Zone1"][temperature + "|mean"] == 21 and data["zones"]["Zone1"][temperature + "|max"] == 22
    assert data["zones"]["Zone10"]["Zone Lights Electricity Energy|kWh/m2"] == 2.0
    assert data["metrics"]["heating_per_m2"] == "Heating need (kWh/m2 y)"
    zone_names, needs = results.zone_series(data)
    assert zone_names == ["Zone1", "Zone10"] and needs["heating"] == [1.0, 0.0]
    keys, by_level = results.level_series({"Full TBEM": data})
    assert keys[0] == "heating" and by_level["Full TBEM"][0] == data["building"]["heating_per_m2"]


def test_svg_charts_and_report():
    from tbem import charts
    assert charts.nice_ticks(203.1) == [0, 50, 100, 150, 200, 250] and charts.nice_ticks(0) == [0, 1]
    svg = charts.bar_chart(results.MONTHS, [("Heating", [10.0] * 12, (215, 48, 31)), ("Cooling", [0.0] * 12,
                                                                                      (31, 120, 180))],
                           "kWh", stacked=True)
    assert svg.startswith("<svg") and svg.count("<rect") == 12 + 1  # bars + legend
    assert "zero all year: Cooling" in svg
    page = charts.report("School - Full TBEM", [("Monthly", svg), ("Table", charts.table(["a"], [["<b>"]]))])
    assert page.startswith("<!DOCTYPE html>") and "&lt;b&gt;" in page


def test_color_scale_of_the_maps():
    from tbim import colors
    color_of, entries = colors.scale_for([0, 10, 60, None, "5"])
    assert len(entries) == 10 + 1 and entries[-1] == ("No data", colors.NO_DATA_COLOR)
    assert len(set(rgb for _, rgb in entries)) == 11  # 10 distinct bands
    assert color_of(0) == colors.SCALE[0] and color_of(60) == colors.SCALE[-1]
    assert color_of(None) == colors.NO_DATA_COLOR
    assert colors.scale_for([3, 3])[1] == [("3", colors.SCALE[0])]


# --------------------------------------------------------------------------------------
# Honeybee
def test_schedule_library_and_digitman_files():
    pytest.importorskip("honeybee_energy")
    from tbem import schedules
    library = schedules.rulesets(schedules.default_library())
    heating = library["HtnSch_Season_Weekdays_7-18"].values()
    assert len(heating) == 8760 and 0 < sum(heating) < 8760 * 11 / 24.0
    entry = {"identifier": "Unoccupied", "day_schedules": [{"identifier": "d", "values": [0, 0.05, 0],
                                                            "times": [[0, 7, 21]]}],
             "default_day_schedule": "d", "schedule_rules": []}
    imported = schedules.rulesets([schedules.normalized(entry, "EqpSch_")])
    assert max(imported["EqpSch_Unoccupied"].values()) == 0.05


def build(project, level, settings=None):
    pytest.importorskip("honeybee_energy")
    if tbim.topologic_backend() is None:
        pytest.skip("no topologicpy backend (pythonocc-core or topologic_core)")
    from tbem import model, schedules
    from tbim import tbimjson, topo
    path = ibim(project)
    program_list = [{"pr_OccupancyType": "Default", "pr_LightingPowerDensity": 8, "pr_EquipmentPowerDensity": 4,
                     "rl_IsScheduledBy_Occupancy": "OccSch_Office"}]
    return model.build(topo.load_cellcomplex(path), level, settings or tbem_settings.load("missing.json"),
                       program_list, schedules.default_library(), aperture_polygons=tbimjson.aperture_polygons(path),
                       name=project)


@pytest.mark.parametrize("level", ["SpatialBEM", "TopologicalBEM", "FullTBEM"])
def test_demo_school_levels_are_valid_honeybee_models(level):
    from tbem import model as tbem_model
    hb_model, summary, report = build("Demo_School", level)
    assert len(hb_model.rooms) == len(summary) == 8
    assert tbem_model.check(hb_model) == [], report
    windows = sum(len(f.apertures) for r in hb_model.rooms for f in r.faces)
    assert (windows == 0) if level == "SpatialBEM" else (windows == 12)
    adjacent = [f for r in hb_model.rooms for f in r.faces if f.boundary_condition.name == "Surface"]
    ground = [f for r in hb_model.rooms for f in r.faces if f.boundary_condition.name == "Ground"]
    assert adjacent and ground
    heated = [r for r in hb_model.rooms if r.properties.energy.hvac is not None]
    assert heated and all(r.properties.energy.setpoint is not None for r in heated)


def test_full_tbem_constructions_from_styles():
    hb_model, _, report = build("School", "FullTBEM")
    floors = [f for r in hb_model.rooms for f in r.faces if f.type.name == "Floor"]
    constructions = set(f.properties.energy.construction.identifier for f in floors)
    assert any(c.endswith("_Rev") for c in constructions), constructions  # floors: layers listed top first
    doors = sum(len(f.doors) for r in hb_model.rooms for f in r.faces)
    assert doors == 2, report


def test_excluded_cells_give_adiabatic_faces():
    settings = tbem_settings.merged(tbem_settings.DEFAULTS, {"zoning": {"excluded_cell_uids": ["Cell0"]}})
    hb_model, summary, _ = build("Demo_School", "TopologicalBEM", settings)
    assert "Cell0" not in [c for z in summary.values() for c in z["cells"]]
    assert any(f.boundary_condition.name == "Adiabatic" for r in hb_model.rooms for f in r.faces)


# --------------------------------------------------------------------------------------
# EnergyPlus
def test_energyplus_run_of_the_demo_school(tmp_path):
    from tbem import simulation
    settings = tbem_settings.load("missing.json")
    folder = tbem_settings.energyplus_folder(settings)
    if not folder or not os.path.isfile(EPW):
        pytest.skip("EnergyPlus 24.2 or the weather file not available")
    hb_model, summary, _ = build("Demo_School", "FullTBEM", settings)
    idf = simulation.write_idf(hb_model, simulation.parameter(settings), str(tmp_path / "demo.idf"), EPW)
    run_dir = str(tmp_path / "run")
    simulation.start(idf, EPW, run_dir, folder, wait=True)
    state, message = simulation.status(run_dir)
    assert state == simulation.COMPLETED and "0 Severe Errors" in message, message
    data = results.read(simulation.csv_file(run_dir), summary)
    assert data["building"]["heating"] > 0 and data["building"]["lighting"] > 0
    assert data["building"]["cooling"] > 0  # Demo School: cooled classrooms, Bologna summer
