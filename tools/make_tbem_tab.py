"""Write the bundles of the TBEM tab (TBEM.tab) of the TBIM pyRevit extension.

Every command is a few lines calling one step of tbem.pipeline; this script keeps their titles, tooltips and
scripts in one place. Icons are drawn by tools/make_icons.py.

    python tools/make_tbem_tab.py
"""
import io
import os

EXTENSION = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir,
                         "pyRevit", "pyRevit_extensions", "TBIM.extension")
TAB = os.path.join(EXTENSION, "TBEM.tab")
TBIM_TAB = os.path.join(EXTENSION, "TBIM.tab")
CONTEXT = "from tbim.revit import Context\n\nctx = Context(__revit__)  # noqa: F821\n"


def script(doc, call, files_too=False):
    imports = "from tbem import files, pipeline\n" if files_too else "from tbem import pipeline\n"
    return '#! python3\n"""%s"""\n%s%s%s\n' % (doc, imports, CONTEXT, call)


def command(title, expression):
    return 'pipeline.command("%s", %s)' % (title, expression.replace("'", '"'))


def tbim_script(path):
    """Script of a TBIM tab command: the project is the same for both tabs."""
    with io.open(os.path.join(TBIM_TAB, path, "script.py"), encoding="utf-8") as f:
        return f.read()


RUN_WORKFLOW = '''#! python3
"""Run the whole TBEM workflow on the active project: the three models and their simulations."""
from tbem import files, pipeline
from tbim import revit, ui
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
CHOICES = [("Build the three models and simulate them", files.LEVELS),
           ("Build the three models and simulate the Full TBEM", [files.FULL]),
           ("Build the three models, no simulation", [])]
answer = ui.select("tbem_run_workflow", "Run the TBEM workflow", [label for label, _ in CHOICES])
if answer:
    try:
        done, report = pipeline.run_workflow(dict(CHOICES)[answer])
    except pipeline.StepError as e:
        done, report = [], [str(e)]
    revit.alert("Run", "%d steps completed:\\n%s" % (len(done), "\\n".join(report)))
'''


def level_command(title, key, step, simulated=False):
    return 'pipeline.command("%s", lambda: pipeline.for_level(\n    "%s", "%s: model", %s%s))' % (
        title, key, title, step, ", simulated=True" if simulated else "")


# (bundle path, title, tooltip, script text | [pulldown items])
BUNDLES = [
    # Project
    ("Project.Panel/New.pushbutton", "New",
     "Create a new TBIM project folder from the templates, make it the active project and link it to the open "
     "Revit model. The project is shared with the TBIM tab: its TBEM files go in the bem folder.",
     tbim_script("Project.Panel/New.pushbutton")),
    ("Project.Panel/Open.pushbutton", "Open",
     "Activate an existing TBIM project (or turn any folder into one) and link it to the open Revit model. The "
     "project is shared with the TBIM tab.", tbim_script("Project.Panel/Open.pushbutton")),
    ("Project.Panel/Run.pushbutton", "Run",
     "Run the whole TBEM workflow on the active project: Build the Spatial BEM, the Topological BEM and the Full "
     "TBEM, then run EnergyPlus on all of them, on the Full TBEM only or on none, waiting for the results.",
     RUN_WORKFLOW),
    ("Project.Panel/CheckModel.pushbutton", "Check Model",
     "Check the inputs of the TBEM: the TBIM model, the programs of the occupancy types, the schedules, the "
     "constructions of the styles, the shading files, the weather file and EnergyPlus.",
     script("Check the inputs of the TBEM of the project.", command("Check model", "pipeline.check"))),
    ("Project.Panel/Info.pushbutton", "Info",
     "Show the active project, the project linked to the Revit model and which TBEM models, IDFs, simulations and "
     "results already exist.",
     script("Show the active project and the TBEM progress.", command("Info", "lambda: pipeline.info(ctx)"))),
    ("Project.Panel/Folder.pushbutton", "Folder", "Open the TBEM folder of the project (bem).",
     script("Open the TBEM folder.", command("Folder", "pipeline.open_folder"))),
    # Spatial BEM
    ("Spatial BEM.Panel/Zones.pulldown", "Zones",
     "Thermal zones of the energy model: the TBIM zones (Loads > Clusterize), a new clustering or zones changed "
     "by hand.", ["Clusterize", "FromTBIM", "Merge", "Exclude", "Include"]),
    ("Spatial BEM.Panel/Zones.pulldown/Clusterize.pushbutton", "Clusterize",
     "Cluster the cells in thermal zones with the TBEM zoning settings (K-Means of the free cells, zones split by "
     "storey and adjacency, classrooms and circulation as in Loads > Clusterize). Zones changed by hand are dropped.",
     script("Cluster the cells in thermal zones with the TBEM settings.",
            command("Thermal zones", "lambda: pipeline.clusterize(ctx)"))),
    ("Spatial BEM.Panel/Zones.pulldown/FromTBIM.pushbutton", "From TBIM",
     "Use again the thermal zones of the TBIM (rl_HasLocation_tpZN, Loads > Clusterize), dropping the TBEM changes.",
     script("Back to the thermal zones of the TBIM.", command("Thermal zones", "lambda: pipeline.reset_zones(ctx)"))),
    ("Spatial BEM.Panel/Zones.pulldown/Merge.pushbutton", "Merge Selected",
     "Put the selected Revit spaces in one thermal zone (the zone of the first one).",
     script("Merge the selected spaces in one thermal zone.",
            command("Thermal zones", "lambda: pipeline.merge_selected(ctx)"))),
    ("Spatial BEM.Panel/Zones.pulldown/Exclude.pushbutton", "Exclude Selected",
     "Leave the selected Revit spaces out of the energy model (their faces towards modelled zones become adiabatic).",
     script("Leave the selected spaces out of the energy model.",
            command("Thermal zones", "lambda: pipeline.exclude_selected(ctx)"))),
    ("Spatial BEM.Panel/Zones.pulldown/Include.pushbutton", "Include Selected",
     "Model again the selected Revit spaces left out of the energy model.",
     script("Model again the selected spaces.", command("Thermal zones", "lambda: pipeline.include_selected(ctx)"))),
    ("Spatial BEM.Panel/Programs.pulldown", "Programs",
     "BEM programs by occupancy type (tbem_Programs.json): lighting and equipment power, set-points, outdoor air "
     "and schedules filling the gaps of the TBIM data.", ["Check", "Edit"]),
    ("Spatial BEM.Panel/Programs.pulldown/Check.pushbutton", "Check",
     "List the program of each occupancy type of the project and what it leaves undefined.",
     script("Check the BEM programs of the occupancy types.", command("Programs", "pipeline.check_programs"))),
    ("Spatial BEM.Panel/Programs.pulldown/Edit.pushbutton", "Edit", "Open tbem_Programs.json in the default editor.",
     script("Open the BEM programs.", command("Programs", "pipeline.edit_programs"))),
    ("Spatial BEM.Panel/Schedules.pulldown", "Schedules",
     "Library of schedules (Honeybee ScheduleRuleset JSON, tbem_Schedules.json).", ["Import", "Check"]),
    ("Spatial BEM.Panel/Schedules.pulldown/Import.pushbutton", "Import",
     "Add Honeybee ScheduleRuleset JSON files to the library, e.g. the occupancy schedules of a booking service "
     "(the schedule files of digitman_bim2bem). The use in the file name (Occupancy, Lighting, Equipment, Heating, "
     "Cooling, Ventilation) sets the identifier prefix.",
     script("Import schedules into the library.", command("Schedules", "pipeline.import_schedules"))),
    ("Spatial BEM.Panel/Schedules.pulldown/Check.pushbutton", "Check",
     "List the schedules named by programs and cells that are not in the library.",
     script("Check the schedules named by programs and cells.", command("Schedules", "pipeline.check_schedules"))),
    ("Spatial BEM.Panel/Build.pushbutton", "Build",
     "Spatial BEM: the thermal zones as closed volumes with their programs and ideal loads; face types, ground and "
     "adjacencies by Honeybee from the geometry, default constructions, no apertures.",
     script("Build the Spatial BEM.", command("Spatial BEM", "lambda: pipeline.build(files.SPATIAL)"), True)),
    # Topological BEM
    ("Topological BEM.Panel/Boundaries.pulldown", "Boundaries",
     "Boundary conditions of the faces: from the topology (outdoors, ground for botHor faces, adjacent zones) or "
     "set on the selected walls, floors and roofs.", ["Adiabatic", "Ground", "Outdoors", "Reset"]),
    ("Topological BEM.Panel/Boundaries.pulldown/Adiabatic.pushbutton", "Adiabatic",
     "Set the selected walls, floors or roofs adiabatic (e.g. walls shared with adjacent buildings).",
     script("Selected faces: adiabatic.", command("Boundaries", "lambda: pipeline.set_boundary(ctx, 'Adiabatic')"))),
    ("Topological BEM.Panel/Boundaries.pulldown/Ground.pushbutton", "Ground",
     "Set the selected walls, floors or roofs in contact with the ground.",
     script("Selected faces: ground.", command("Boundaries", "lambda: pipeline.set_boundary(ctx, 'Ground')"))),
    ("Topological BEM.Panel/Boundaries.pulldown/Outdoors.pushbutton", "Outdoors",
     "Set the selected walls, floors or roofs outdoors (e.g. floors over open passages).",
     script("Selected faces: outdoors.", command("Boundaries", "lambda: pipeline.set_boundary(ctx, 'Outdoors')"))),
    ("Topological BEM.Panel/Boundaries.pulldown/Reset.pushbutton", "Reset",
     "Give the selected faces the boundary condition of the topology again.",
     script("Selected faces: boundary of the topology.",
            command("Boundaries", "lambda: pipeline.set_boundary(ctx, None)"))),
    ("Topological BEM.Panel/Build.pushbutton", "Build",
     "Topological BEM: faces typed by the topology, boundary conditions and inter-zone adjacencies from the "
     "CellComplex, windows and external doors of the TopologicalBIM, glazed walls as windows by ratio.",
     script("Build the Topological BEM.",
            command("Topological BEM", "lambda: pipeline.build(files.TOPOLOGICAL)"), True)),
    # Full TBEM
    ("Full TBEM.Panel/Constructions.pushbutton", "Constructions",
     "List the opaque constructions from the Informational Styles (layers, U-value) and the glazing of the windows.",
     script("Check the constructions of the Full TBEM.", command("Constructions", "pipeline.check_constructions"))),
    ("Full TBEM.Panel/Shading.pulldown", "Shading",
     "Context shading of the Full TBEM: BRep faces (cm) of surrounding buildings, balconies, vegetation.",
     ["Import", "Clear"]),
    ("Full TBEM.Panel/Shading.pulldown/Import.pushbutton", "Import",
     "Add BRep files of context shading (copied to the bem/shades folder).",
     script("Import context shading.", command("Shading", "pipeline.import_shades"))),
    ("Full TBEM.Panel/Shading.pulldown/Clear.pushbutton", "Clear", "Remove the context shading from the Full TBEM.",
     script("Remove the context shading.", command("Shading", "pipeline.clear_shades"))),
    ("Full TBEM.Panel/Infiltration.pushbutton", "Infiltration",
     "Building airtightness: infiltration per facade area of every zone.",
     script("Set the building airtightness.", command("Infiltration", "pipeline.set_infiltration"))),
    ("Full TBEM.Panel/Build.pushbutton", "Build",
     "Full TBEM: the Topological BEM with the layered constructions of the styles, simple glazing, external blinds "
     "on the windows of faces with stFC_ShadingDevice and context shading.",
     script("Build the Full TBEM.", command("Full TBEM", "lambda: pipeline.build(files.FULL)"), True)),
    # Energy Simulation
    ("Energy Simulation.Panel/Weather.pushbutton", "Weather",
     "Pick the EnergyPlus weather file (EPW); a DDY file with the same name adds the design days.",
     script("Pick the weather file.", command("Weather", "pipeline.set_weather"))),
    ("Energy Simulation.Panel/Settings.pushbutton", "Settings",
     "Open the TBEM settings (tbem_Settings.json): zoning, boundary conditions, glazing, blinds, HVAC, run period, "
     "timestep, output variables, EnergyPlus folder.",
     script("Open the TBEM settings.", command("Settings", "pipeline.edit_settings"))),
    ("Energy Simulation.Panel/IDF.pushbutton", "IDF",
     "Export a TBEM model to EnergyPlus (IDF) with the simulation settings.",
     script("Export a TBEM model to EnergyPlus.", level_command("IDF", "tbem_idf_level", "pipeline.export_idf"))),
    ("Energy Simulation.Panel/Run.pushbutton", "Run",
     "Export a TBEM model to EnergyPlus and run the annual simulation in the background.",
     script("Run EnergyPlus on a TBEM model.", level_command("Run", "tbem_run_level", "pipeline.run"))),
    ("Energy Simulation.Panel/Results.pulldown", "Results", "Annual results of the simulations by zone.",
     ["Summary", "WriteToSpaces"]),
    ("Energy Simulation.Panel/Results.pulldown/Summary.pushbutton", "Summary",
     "Annual heating, cooling, lighting and equipment energy of the building and of the zones (kWh, kWh/m2).",
     script("Summarise the results of a simulation.",
            level_command("Results", "tbem_results_level", "pipeline.results", True))),
    ("Energy Simulation.Panel/Results.pulldown/WriteToSpaces.pushbutton", "Write to Spaces",
     "Write the annual results of the zones to their Revit spaces (rs_HeatingNeed, rs_CoolingNeed, ... in kWh/m2).",
     script("Write the results to the Revit spaces.",
            level_command("Results", "tbem_results_level", "lambda level: pipeline.write_results(ctx, level)",
                          True))),
    # Visualize
    ("Visualize.Panel/Zones.pulldown", "Zones",
     "Grouping of the spaces in the thermal zones of the energy model (also the Revit HVAC zones and the IfcZones "
     "of the IFC export).", ["Map3D", "Map2D"]),
    ("Visualize.Panel/Zones.pulldown/Map3D.pushbutton", "3D Map",
     "Color the cells by their thermal zone in a 3D view, with a legend.",
     script("Color the cells by thermal zone.", command("Thermal zones", "lambda: pipeline.show_zones(ctx)"))),
    ("Visualize.Panel/Zones.pulldown/Map2D.pushbutton", "2D Map",
     "Fill the spaces by their thermal zone in a floor plan per storey, with the zone names and a legend of the "
     "zones of the storey.",
     script("Fill the spaces by thermal zone in floor plans.",
            command("Thermal zones", "lambda: pipeline.show_zones_2d(ctx)"))),
    ("Visualize.Panel/Boundaries.pushbutton", "Boundaries",
     "Color the walls, floors and roofs by boundary condition in a 3D view, with a legend.",
     script("Color the faces by boundary condition.", command("Boundaries", "lambda: pipeline.show_boundaries(ctx)"))),
    ("Visualize.Panel/Charts.pushbutton", "Charts",
     "Charts of the results of a simulation in the pyRevit output: end uses by month, heating and cooling need by "
     "zone and, when more levels have been simulated, the levels of detail compared.",
     script("Chart the results of a simulation.",
            level_command("Charts", "tbem_results_level", "pipeline.show_charts", True))),
    ("Visualize.Panel/Map3D.pushbutton", "3D Map",
     "Color the cells by a result of their zone (heating need, cooling need, ...) in a 3D view, with a color scale.",
     script("Color the cells by a result of their zone.",
            level_command("3D Map", "tbem_results_level", "lambda level: pipeline.show_map_3d(ctx, level)", True))),
    ("Visualize.Panel/Map2D.pushbutton", "2D Map",
     "Fill the spaces by a result of their zone (heating need, cooling need, ...) in a floor plan per storey, with "
     "the value of each space and a color scale.",
     script("Fill the spaces by a result of their zone in floor plans.",
            level_command("2D Map", "tbem_results_level", "lambda level: pipeline.show_map_2d(ctx, level)", True))),
    ("Visualize.Panel/Clear.pushbutton", "Clear",
     "Delete the TBEM visualizations: shapes, 'TBIM - BEM ...' views and their legends.",
     script("Delete the TBEM visualizations.", command("Visualize", "lambda: pipeline.clear_visualizations(ctx)"))),
]
PANELS = {
    "Project.Panel": ["New", "Open", "Run", "CheckModel", "Info", "Folder"],
    "Spatial BEM.Panel": ["Zones", "Programs", "Schedules", "Build"],
    "Topological BEM.Panel": ["Boundaries", "Build"],
    "Full TBEM.Panel": ["Constructions", "Shading", "Infiltration", "Build"],
    "Energy Simulation.Panel": ["Weather", "Settings", "IDF", "Run", "Results"],
    "Visualize.Panel": ["Zones", "Boundaries", "Charts", "Map3D", "Map2D", "Clear"],
}
TAB_LAYOUT = ["Project", "-----", "Spatial BEM", "-----", "Topological BEM", "-----", "Full TBEM", "-----",
              "Energy Simulation", "-----", "Visualize"]


def write(path, text):
    if not os.path.isdir(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def layout(items):
    return "layout:\n" + "".join("  - %s\n" % item for item in items)


def main():
    write(os.path.join(TAB, "bundle.yaml"), layout(TAB_LAYOUT))
    for panel, items in PANELS.items():
        write(os.path.join(TAB, panel, "bundle.yaml"), layout(items))
    for path, title, tooltip, content in BUNDLES:
        head = 'title: "%s"\ntooltip: "%s"\n' % (title, tooltip.replace('"', "'"))
        if isinstance(content, list):
            write(os.path.join(TAB, path, "bundle.yaml"), head + layout(content))
        else:
            write(os.path.join(TAB, path, "bundle.yaml"), head)
            write(os.path.join(TAB, path, "script.py"), content)
    print("%d bundles in %s" % (len(BUNDLES), os.path.normpath(TAB)))


if __name__ == "__main__":
    main()
