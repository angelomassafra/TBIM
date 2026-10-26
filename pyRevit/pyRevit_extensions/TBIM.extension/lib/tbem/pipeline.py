"""The steps of the TBEM tab in Revit, as functions (CPython only).

As in tbim.pipeline, every step reads and writes the files of the active project (``files``), takes its options
as arguments and returns the lines of its report; the ribbon commands call one step through ``command``.

    Project           run_workflow, check, info, open_folder
    Spatial BEM       clusterize, reset_zones, merge_selected, exclude_selected, include_selected,
                      check_programs, edit_programs, import_schedules, check_schedules, build(SPATIAL)
    Topological BEM   set_boundary, build(TOPOLOGICAL)
    Full TBEM         check_constructions, import_shades, clear_shades, set_infiltration, build(FULL)
    Energy Simulation set_weather, edit_settings, export_idf, run, results, write_results
    Visualize         show_zones, show_boundaries, show_charts, show_map_3d, show_map_2d, clear_visualizations
"""
import io
import json
import os

from Autodesk.Revit.DB import BuiltInCategory, FilteredElementCollector, ViewPlan

from tbem import charts, constructions, files, programs, schedules, simulation
from tbem import model as tbem_model
from tbem import results as tbem_results
from tbem import settings as tbem_settings
from tbem import zones as tbem_zones
from tbim import colors, materials, paths, projects, revit, scene, tbimjson, topo, ui
from tbim import visualize as viz
from tbim.jsonio import read_json, write_json
from tbim.pipeline import StepError, command, run_steps  # noqa: F401  (command: used by the ribbon commands)

TAG = "TBEM"
NOT_MODELLED = "Not modelled"
SPACE_CATEGORIES = (BuiltInCategory.OST_MEPSpaces,)
FACE_CATEGORIES = (BuiltInCategory.OST_Walls, BuiltInCategory.OST_Floors, BuiltInCategory.OST_Roofs)
BOUNDARIES = ["Adiabatic", "Ground", "Outdoors"]
BOUNDARY_KEYS = {"Adiabatic": "adiabatic_face_uids", "Ground": "ground_face_uids", "Outdoors": "outdoors_face_uids"}
BOUNDARY_COLORS = {"Outdoors": (31, 120, 180), "Ground": (140, 81, 10), "Adiabatic": (153, 153, 153),
                   "Adjacent zone": (51, 160, 44), "Inside a zone": (230, 230, 230), NOT_MODELLED: (60, 60, 60)}
LEVEL_COLORS = {"Spatial BEM": (52, 140, 210), "Topological BEM": (120, 84, 190), "Full TBEM": (214, 120, 40)}


# --------------------------------------------------------------------------------------
# Inputs
def source():
    """(label, path) of the TBIM model converted to BEM."""
    found = files.source_model()
    if not found:
        raise StepError("No TBIM model in the project: run the TBIM workflow first (TBIM > Project > Run).")
    return found


def load_source():
    label, path = source()
    return label, path, topo.load_cellcomplex(path)


def program_list():
    return read_json(files.ensure(files.PROGRAMS), default=[])


def schedule_library():
    return read_json(files.ensure(files.SCHEDULES), default=[]) or schedules.default_library()


def saved_zones():
    return read_json(files.bem_file(files.ZONES), default={})


def north_angle():
    return float(read_json(paths.data_file(paths.NORTH_ANGLE), default=0) or 0)


def project_name():
    return os.path.basename(files.project_folder())


def selected_uids(ctx, categories):
    """TBIM UIDs of the selected Revit elements of ``categories``."""
    out = []
    for element_id in ctx.uidoc.Selection.GetElementIds():
        element = ctx.doc.GetElement(element_id)
        category = getattr(element, "Category", None)
        if category is not None and category.BuiltInCategory in categories and revit.uid(element):
            out.append(revit.uid(element))
    return out


def _require_selection(uids, what):
    if not uids:
        raise StepError("Select the Revit %s first (TBIM elements, with a UID)." % what)
    return uids


def cell_list():
    """[(UID, props)] of the cells of the source model, without the geometry."""
    _, path = source()
    return [(d.get("UID"), d) for d in tbimjson.dictionaries(path)["Cell"] if d.get("UID")]


def assignment(cells=None):
    return tbem_zones.assign(cells or cell_list(), tbem_settings.load(), saved_zones())


# --------------------------------------------------------------------------------------
# Spatial BEM: zones, programs, schedules
def sync_revit_zones(ctx):
    """Revit HVAC zones as the zones of the energy model (the spaces left out go to the default zone)."""
    return "Revit HVAC zones: %d" % revit.sync_hvac_zones(ctx, assignment())


def clusterize(ctx):
    """New thermal zones of the cells with the zoning settings (manual changes are dropped)."""
    label, _, cc = load_source()
    zones = tbem_model.clusters(cc, tbem_settings.load())
    write_json(files.bem_file(files.ZONES), zones)
    current = tbem_zones.members(assignment())
    return ["%d thermal zones from %d cells of the %s (K-Means with k = %d)" % (
        len(current), len(zones), label, tbem_settings.load()["zoning"]["n_clusters"]),
        "Saved to: %s" % files.bem_file(files.ZONES), sync_revit_zones(ctx)]


def reset_zones(ctx):
    """Back to the thermal zones of the TBIM (Loads > Clusterize)."""
    path = files.bem_file(files.ZONES)
    if os.path.isfile(path):
        os.remove(path)
    return ["The TBEM uses the thermal zones of the TBIM: %d zones" % len(tbem_zones.members(assignment())),
            sync_revit_zones(ctx)]


def merge_selected(ctx):
    """Put the selected spaces in one zone (the zone of the first one)."""
    uids = _require_selection(selected_uids(ctx, SPACE_CATEGORIES), "spaces to merge")
    current = assignment()
    zone = next((current[u] for u in uids if current.get(u)), "Zone_%s" % uids[0])
    saved = saved_zones()
    saved.update((u, zone) for u in uids)
    write_json(files.bem_file(files.ZONES), saved)
    _model_again(uids)
    return ["%d spaces in the zone %s: %s" % (len(uids), zone, ", ".join(uids)), sync_revit_zones(ctx)]


def exclude_selected(ctx):
    """Leave the selected spaces out of the energy model."""
    uids = _require_selection(selected_uids(ctx, SPACE_CATEGORIES), "spaces to leave out")
    excluded = tbem_settings.load()["zoning"]["excluded_cell_uids"]
    tbem_settings.update("zoning", {"excluded_cell_uids": sorted(set(excluded) | set(uids))})
    return ["%d spaces left out of the energy model: %s" % (len(uids), ", ".join(uids)), sync_revit_zones(ctx)]


def include_selected(ctx):
    """Model again the selected spaces left out."""
    uids = _require_selection(selected_uids(ctx, SPACE_CATEGORIES), "spaces to model")
    _model_again(uids)
    return ["%d spaces modelled" % len(uids), sync_revit_zones(ctx)]


def _model_again(uids):
    excluded = tbem_settings.load()["zoning"]["excluded_cell_uids"]
    tbem_settings.update("zoning", {"excluded_cell_uids": sorted(set(excluded) - set(uids))})
    saved = saved_zones()
    for uid in uids:
        if uid in saved and saved[uid] is None:
            del saved[uid]
    write_json(files.bem_file(files.ZONES), saved)


def show_cells(ctx, values, title, note=None, scale=False):
    """Cells as shapes colored by ``values`` ({UID: value}) in the 3D view 'TBIM - <title>', with a legend
    (``scale``: a sequential color scale of numbers, else categories)."""
    _, path = source()
    cells = scene.cells(topo.load_cellcomplex(path), shrink=0.94)
    cell_values = [values.get(uid) for uid, _, _ in cells]
    color_of, entries = colors.scale_for(cell_values) if scale else colors.legend_for(cell_values)
    with revit.transaction(ctx.doc, "TBEM - %s" % title):
        viz.clear(ctx.doc, TAG)
        view = viz.view_3d(ctx.doc, title)
        viz.ghost(view, viz.HOST_CATEGORIES, transparency=90)
        for uid, _, loops in cells:
            geometry = viz.polygons(loops, viz.material(ctx.doc, color_of(values.get(uid))), closed=True)
            if geometry:
                viz.directshape(ctx.doc, geometry, TAG, "%s: %s" % (uid, values.get(uid)))
        viz.show_only(ctx.doc, view, TAG)
        viz.legend(ctx.doc, title, entries, note=note)
    ctx.uidoc.ActiveView = view
    return view


def show_zones(ctx):
    zones = dict((uid, zone or NOT_MODELLED) for uid, zone in assignment().items())
    view = show_cells(ctx, zones, "BEM thermal zones", note="TBEM zones of %s" % source()[0])
    return ["%d cells in %d zones colored in the view '%s'" % (
        len(zones), len(set(zones.values()) - {NOT_MODELLED}), view.Name)]


def check_programs():
    """The program of each occupancy type of the project and what it leaves undefined."""
    program_items = program_list()
    occupancy_types = sorted(set(p.get(programs.OCCUPANCY_KEY) or programs.DEFAULT for _, p in cell_list()))
    lines = ["Programs (%s):" % files.ensure(files.PROGRAMS)]
    for occupancy_type in occupancy_types:
        program = programs.resolve(program_items, occupancy_type)
        lines.append("  %s -> %s: lighting %s W/m2, equipment %s W/m2, occupancy %s" % (
            occupancy_type, program.get(programs.OCCUPANCY_KEY, "none"), program.get("pr_LightingPowerDensity"),
            program.get("pr_EquipmentPowerDensity"), program.get("rl_IsScheduledBy_Occupancy")))
    for occupancy_type, keys in programs.missing(program_items, occupancy_types).items():
        lines.append("WARNING - %s: no %s" % (occupancy_type, ", ".join(keys)))
    return lines


def edit_programs():
    path = files.ensure(files.PROGRAMS)
    os.startfile(path)
    return ["Programs opened in the default editor: %s" % path]


def import_schedules():
    """Add Honeybee ScheduleRuleset JSON files (e.g. the schedules of digitman_bim2bem) to the library."""
    selected = ui.open_files("tbem_schedule_files", "Schedules (Honeybee ScheduleRuleset JSON)",
                             "JSON files (*.json)|*.json", multiple=True)
    if not selected:
        return ["No file selected."]
    library = schedule_library()
    lines = []
    for path in selected:
        use = next((u for u in schedules.PREFIXES if u.lower() in os.path.basename(path).lower()), None)
        new = schedules.import_file(path, use)
        schedules.rulesets(new)  # validation
        library = schedules.merge(library, new)
        lines.append("%s: %d schedules (%s)" % (os.path.basename(path), len(new), use or "no prefix"))
    write_json(files.ensure(files.SCHEDULES), library, indent=None)
    return lines + ["Library: %d schedules" % len(library)]


def check_schedules():
    """Schedules named by the programs and the cells that are not in the library."""
    known = set(s["identifier"] for s in schedule_library()) | {programs.ALWAYS_ON, programs.ALWAYS_OFF}
    named = {}
    for source_name, items in (("programs", program_list()), ("cells", [p for _, p in cell_list()])):
        for item in items:
            for key in programs.SCHEDULE_KEYS:
                if item.get(key):
                    named.setdefault(str(item[key]).split(";")[0].strip(), set()).add(source_name)
    missing = sorted(n for n in named if n not in known)
    lines = ["%d schedules in the library, %d named by programs and cells" % (len(known), len(named))]
    lines += ["WARNING - not in the library (AlwaysOn/AlwaysOff used): %s (%s)" % (n, ", ".join(sorted(named[n])))
              for n in missing]
    return lines


# --------------------------------------------------------------------------------------
# Models
def build(level):
    """Honeybee model of ``level`` (files.SPATIAL, TOPOLOGICAL, FULL)."""
    label, path, cc = load_source()
    settings = tbem_settings.load()
    aperture_polygons = tbimjson.aperture_polygons(path) if level != files.SPATIAL else ()
    shade_paths = [files.resolve(p) for p in settings["shades"]]
    missing = [p for p in shade_paths if not os.path.isfile(p)]
    if missing:
        raise StepError("Shading BRep files not found: %s (Full TBEM > Shading)" % ", ".join(missing))
    model, summary, report = tbem_model.build(cc, level, settings, program_list(), schedule_library(),
                                              saved_zones(), aperture_polygons, shade_paths, project_name())
    write_json(files.model_file(level), model.to_dict(), indent=None)
    write_json(files.zones_file(level), summary)
    problems = tbem_model.check(model)
    lines = ["%s from the %s" % (files.TITLES[level], label)] + report
    lines += ["Honeybee check: %s" % ("valid" if not problems else "%d problems" % len(problems))]
    lines += ["  " + p for p in problems[:10]]
    return lines + ["Saved to: %s" % files.model_file(level)]


def choose_level(key, title, levels=None):
    """Title of a level picked among ``levels`` (default: the built ones, most detailed first)."""
    levels = levels if levels is not None else files.built_levels()
    if not levels:
        raise StepError("No TBEM model yet: Build a Spatial BEM, Topological BEM or Full TBEM first.")
    titles = [files.TITLES[level] for level in levels]
    answer = ui.select(key, title, titles, default=titles[0])
    return levels[titles.index(answer)] if answer else None


def for_level(key, title, step, simulated=False):
    """Run ``step(level)`` on a level picked by the user (``simulated``: only the levels already run)."""
    levels = files.built_levels()
    if simulated:
        levels = [lv for lv in levels if simulation.status(files.run_dir(lv))[0] != simulation.NONE]
        if not levels:
            raise StepError("No simulation yet: use Energy Simulation > Run first.")
    level = choose_level(key, title, levels)
    return step(level) if level else ["Cancelled."]


# --------------------------------------------------------------------------------------
# Topological BEM: boundary conditions
def set_boundary(ctx, kind=None):
    """Boundary condition ``kind`` (BOUNDARIES; None: from the topology) of the selected walls, floors, roofs."""
    uids = _require_selection(selected_uids(ctx, FACE_CATEGORIES), "walls, floors or roofs")
    options = tbem_settings.load()["boundary_conditions"]
    values = {}
    for name, key in BOUNDARY_KEYS.items():
        current = set(options[key]) - set(uids)
        values[key] = sorted(current | set(uids) if name == kind else current)
    tbem_settings.update("boundary_conditions", values)
    return ["%d faces set to %s: %s" % (len(uids), kind or "the boundary of the topology", ", ".join(uids))]


def boundary_labels():
    """{face UID: boundary label} of the faces of the source model (Topological BEM rules)."""
    from tbem import geometry
    _, _, cc = load_source()
    settings = tbem_settings.load()
    sides = geometry.sides(cc, assignment())
    labels = {}
    for side in sides:
        uid = side["props"].get("UID")
        if side["kind"] == geometry.INTERZONE:
            labels[uid] = "Adjacent zone"
        else:
            labels[uid] = str(geometry.boundary(side, settings, None))
    for _, faces in topo.face_groups(cc):
        for face in faces:
            labels.setdefault(topo.get(face, "UID"), "Inside a zone")
    return labels


def show_boundaries(ctx):
    labels = boundary_labels()
    elements = [e for c in FACE_CATEGORIES for e in revit.instances(ctx.doc, c) if revit.uid(e)]
    title = "BEM boundary conditions"
    with revit.transaction(ctx.doc, "TBEM - %s" % title):
        view = viz.view_3d(ctx.doc, title)
        viz.set_hidden(view, [BuiltInCategory.OST_GenericModel], True)
        viz.reset_overrides(view, elements)
        solid = viz.solid_fill_id(ctx.doc)
        for element in elements:
            label = labels.get(revit.uid(element), NOT_MODELLED)
            viz.color_element(view, element.Id, BOUNDARY_COLORS.get(label, BOUNDARY_COLORS[NOT_MODELLED]), solid)
        used = sorted(set(labels.get(revit.uid(e), NOT_MODELLED) for e in elements))
        viz.legend(ctx.doc, title, [(label, BOUNDARY_COLORS.get(label, (60, 60, 60))) for label in used])
    ctx.uidoc.ActiveView = view
    counts = dict((label, sum(1 for e in elements if labels.get(revit.uid(e), NOT_MODELLED) == label))
                  for label in used)
    return ["%d walls, floors and roofs colored in the view '%s':" % (len(elements), view.Name)] + [
        "  %s: %d" % item for item in sorted(counts.items())]


# --------------------------------------------------------------------------------------
# Full TBEM: constructions, shading, airtightness
def check_constructions():
    """Styles of the faces with their layers and U-value, and the glazing of the windows."""
    _, path = source()
    data = tbimjson.dictionaries(path)
    settings = tbem_settings.load()
    styles = {}
    for face in data["Face"]:
        name = constructions.style(face)
        if name:
            styles.setdefault(name, [face, 0])[1] += 1
    lines = ["Opaque constructions (%d styles):" % len(styles)]
    for name, (face, count) in sorted(styles.items()):
        layers = constructions.layers(face)
        if layers:
            u = materials.u_value(layers, face.get("pr_TopologicalType"))
            lines.append("  %s: %d faces, %d layers, U %.2f W/m2K%s" % (
                name, count, len(layers), u, " (glazed: windows by ratio)" if constructions.is_glazed(face) else ""))
        else:
            lines.append("  WARNING - %s: %d faces without layers (Honeybee default construction)" % (name, count))
    glazing = {}
    for aperture in data["Aperture"]:
        if aperture.get("pr_TopologicalType") == "window":
            values = constructions.glazing_values(aperture, settings)
            key = "U %(u)g, SHGC %(shgc)g, VT %(vt)g" % values
            glazing[key] = glazing.get(key, 0) + 1
    lines.append("Glazing of %d windows:" % sum(glazing.values()))
    lines += ["  %s: %d windows" % item for item in sorted(glazing.items())]
    return lines


def import_shades():
    selected = ui.open_files("tbem_shade_files", "Context shading (BRep)", "BRep files (*.brep)|*.brep",
                             multiple=True)
    if not selected:
        return ["No file selected."]
    current = tbem_settings.load()["shades"]
    added = [files.copy_in(path, files.SHADES_FOLDER) for path in selected]
    tbem_settings.update_value("shades", sorted(set(current) | set(added)))
    return ["Shading BRep files of the Full TBEM:"] + ["  %s" % p for p in sorted(set(current) | set(added))]


def clear_shades():
    tbem_settings.update_value("shades", [])
    return ["No context shading in the Full TBEM."]


def set_infiltration():
    current = tbem_settings.load()["infiltration"]["building_airtightness"]
    options = sorted(tbem_settings.INFILTRATION_FLOW_RATES, key=tbem_settings.INFILTRATION_FLOW_RATES.get)
    labels = ["%s (%.6f m3/s per m2 of facade)" % (o, tbem_settings.INFILTRATION_FLOW_RATES[o]) for o in options]
    answer = ui.select("tbem_infiltration", "Building airtightness", labels, default=labels[options.index(current)])
    if not answer:
        return ["Airtightness unchanged: %s" % current]
    choice = options[labels.index(answer)]
    tbem_settings.update("infiltration", {"building_airtightness": choice})
    return ["Building airtightness: %s (Build the models again)" % choice]


# --------------------------------------------------------------------------------------
# Energy Simulation
def set_weather():
    selected = ui.open_files("tbem_weather_file", "Weather file (EPW)", "EnergyPlus weather (*.epw)|*.epw")
    if not selected:
        return ["No file selected."]
    epw = files.copy_in(selected[0], files.WEATHER_FOLDER)
    ddy_source = os.path.splitext(selected[0])[0] + ".ddy"
    ddy = files.copy_in(ddy_source, files.WEATHER_FOLDER) if os.path.isfile(ddy_source) else None
    tbem_settings.update("simulation", {"epw": epw, "ddy": ddy})
    return ["Weather file: %s" % epw,
            "Design days: %s" % (ddy or "none (ideal loads without capacity limits; add a .ddy next to the EPW)")]


def edit_settings():
    path = tbem_settings.ensure_file()
    os.startfile(path)
    return ["Settings opened in the default editor: %s" % path]


def _weather(settings):
    epw = settings["simulation"].get("epw")
    if not epw or not os.path.isfile(files.resolve(epw)):
        raise StepError("No weather file: use Energy Simulation > Weather first.")
    ddy = settings["simulation"].get("ddy")
    return files.resolve(epw), files.resolve(ddy) if ddy and os.path.isfile(files.resolve(ddy)) else None


def export_idf(level):
    from honeybee.model import Model
    settings = tbem_settings.load()
    epw, ddy = _weather(settings)
    with open(files.model_file(level)) as f:
        model = Model.from_dict(json.load(f))
    parameter = simulation.parameter(settings, north_angle(), ddy)
    path = simulation.write_idf(model, parameter, files.idf_file(level), epw)
    return ["%s exported to EnergyPlus (24.2): %s" % (files.TITLES[level], path)]


def _energyplus(settings):
    folder = tbem_settings.energyplus_folder(settings)
    if not folder:
        raise StepError("EnergyPlus 24.2 not found: install it in C:\\EnergyPlusV24-2-0 or set "
                        "'energyplus_folder' in the settings (Energy Simulation > Settings).")
    return folder


def run(level, wait=False):
    """Export the IDF of ``level`` and start EnergyPlus (in the background unless ``wait``)."""
    settings = tbem_settings.load()
    folder = _energyplus(settings)
    state, message = simulation.status(files.run_dir(level))
    if state == simulation.RUNNING:
        raise StepError(message)
    lines = export_idf(level)
    epw, _ = _weather(settings)
    simulation.start(files.idf_file(level), epw, files.run_dir(level), folder, wait=wait)
    if wait:
        return lines + results(level)
    return lines + ["EnergyPlus started in the background (%s)." % files.run_dir(level),
                    "Use Results > Summary when it is over (seconds to minutes, by model size)."]


def results(level):
    """Collect the outputs of the run of ``level`` and summarise the annual results."""
    run_folder = files.run_dir(level)
    state, message = simulation.status(run_folder)
    if state != simulation.COMPLETED:
        err = os.path.join(run_folder, "%s.err" % simulation.PREFIX)
        raise StepError(message + ("\nErrors: %s" % err if os.path.isfile(err) else ""))
    simulation.collect(run_folder, files.simulation_dir(level))
    summary = read_json(files.zones_file(level))
    data = tbem_results.read(simulation.csv_file(run_folder), summary)
    data["level"], data["energyplus"] = level, message
    write_json(files.results_file(level), data)
    return tbem_results.summary_lines(data, files.TITLES[level]) + [message,
                                                                "Saved to: %s" % files.results_file(level)]


def _results(level):
    path = files.results_file(level)
    data = read_json(path) if os.path.isfile(path) else {}
    if "metrics" not in data:  # not collected yet, or collected before the monthly totals and the metrics
        results(level)
        data = read_json(path)
    return data


def write_results(ctx, level):
    """Annual results of the zones on their Revit spaces (rs_ parameters)."""
    values = tbem_results.by_cell(_results(level), read_json(files.zones_file(level)))
    revit.ensure_parameters(ctx, [p for p, _ in tbem_results.CELL_KEYS], "TBEM", revit.SPACE_CATEGORIES)
    count = revit.apply_by_uid(ctx.doc, revit.spaces(ctx.doc), values, "TBEM results")
    return ["Results of the %s written to %d spaces: %s" % (files.TITLES[level], count,
                                                          ", ".join(p for p, _ in tbem_results.CELL_KEYS))]


# --------------------------------------------------------------------------------------
# Project
def run_workflow(simulated=(), log=print):
    """Build the three levels, then run EnergyPlus on the ``simulated`` ones and wait for the results.

    Return (completed steps, report lines), as tbim.pipeline.run.
    """
    source()
    if simulated:
        settings = tbem_settings.load()
        _weather(settings)
        _energyplus(settings)
    steps = [("%s > Build" % files.TITLES[level], lambda level=level: build(level)) for level in files.LEVELS]
    steps += [("Energy Simulation > Run: %s" % files.TITLES[level], lambda level=level: run(level, wait=True))
              for level in simulated]
    return run_steps(steps, log)


def check():
    """What the TBEM of the project is missing: TBIM model, programs, schedules, constructions, weather, EnergyPlus."""
    found = files.source_model()
    if found:
        lines = ["TBIM model: %s (%s)" % found]
        for step in (check_programs, check_schedules, check_constructions):
            lines += step()
    else:
        lines = ["WARNING - no TBIM model in the project: run the TBIM workflow first (TBIM > Project > Run)."]
    settings = tbem_settings.load()
    missing = [p for p in settings["shades"] if not os.path.isfile(files.resolve(p))]
    lines += ["WARNING - shading BRep file not found: %s (Full TBEM > Shading)" % p for p in missing]
    try:
        epw, ddy = _weather(settings)
        lines.append("Weather: %s%s" % (epw, "" if ddy else " (no design days: ideal loads without capacity limits)"))
    except StepError as e:
        lines.append("WARNING - %s" % e)
    try:
        lines.append("EnergyPlus: %s" % _energyplus(settings))
    except StepError as e:
        lines.append("WARNING - %s" % e)
    return lines


def info(ctx):
    """The active project, its link with the Revit model and which TBEM models, IDFs and results exist."""
    folder = projects.active_project()
    lines = ["Project: %s" % ("%s (%s)" % (projects.info(folder)["name"], folder) if folder else
                              "none: the data folder %s is not in a project (use Project > New or Open)"
                              % paths.data_dir()),
             "Revit model linked to: %s" % (revit.project_folder(ctx.doc) or "none"),
             "TBEM folder: %s" % files.bem_dir()]
    found = files.source_model()
    lines.append("TBIM model: %s" % (found[0] if found else "none (TBIM > Project > Run)"))
    epw = tbem_settings.load()["simulation"].get("epw")
    lines.append("Weather: %s" % (os.path.basename(epw) if epw else "none (Energy Simulation > Weather)"))
    lines.append("Models:")
    for level in files.LEVELS:
        state = simulation.status(files.run_dir(level))[0]
        done = [name for name, path in (("model", files.model_file(level)), ("IDF", files.idf_file(level)),
                                        ("results", files.results_file(level))) if os.path.isfile(path)]
        lines.append("  %s: %s; simulation %s" % (files.TITLES[level], ", ".join(done) or "not built", state))
    return lines


def open_folder():
    if not os.path.isdir(files.bem_dir()):
        os.makedirs(files.bem_dir())
    os.startfile(files.bem_dir())
    return ["TBEM folder: %s" % files.bem_dir()]


# --------------------------------------------------------------------------------------
# Visualize (show_zones and show_boundaries are with the zones and the boundaries)
def choose_result(level):
    """(result key, label) of a KPI or output variable of the run of ``level`` picked by the user, or
    (None, None)."""
    metrics = _results(level)["metrics"]
    labels = list(metrics.values())
    answer = ui.select("tbem_result", "KPI or output variable to map", labels, default=labels[0])
    key = next((k for k, label in metrics.items() if label == answer), None)
    return key, answer if key else None


def result_values(level, key):
    """{cell UID: result of its zone} (None for the cells left out of the model)."""
    data = _results(level)
    return dict((uid, data["zones"].get(zone, {}).get(key) if zone else None) for uid, zone in assignment().items())


def chart_sections(level):
    """(title, [(heading, html)]) of the charts of the results of ``level``."""
    data = _results(level)
    keys = [key for key, _ in tbem_results.END_USES]
    b = data["building"]
    title = "%s - %s" % (project_name(), files.TITLES[level])
    sections = [("Annual results (%.0f m2)" % b["floor_area"], charts.table(
        ["End use", "kWh", "kWh/m2"], [[key.capitalize(), "%.0f" % b[key], "%.1f" % b[key + "_per_m2"]]
                                       for key in keys]))]
    sections.append(("End uses by month (kWh)", charts.bar_chart(
        tbem_results.MONTHS, [(key.capitalize(), b["monthly"][key], tbem_results.END_USE_COLORS[key])
                              for key in keys], "kWh", stacked=True)))
    zones, needs = tbem_results.zone_series(data)
    sections.append(("Heating and cooling need by zone (kWh/m2 y)", charts.bar_chart(
        zones, [(key.capitalize() + " need", needs[key], tbem_results.END_USE_COLORS[key]) for key in needs],
        "kWh/m2 y")))
    compared = dict((files.TITLES[lv], read_json(files.results_file(lv))) for lv in files.LEVELS
                    if os.path.isfile(files.results_file(lv)))
    if len(compared) > 1:
        _, by_title = tbem_results.level_series(compared)
        sections.append(("Levels of detail compared (kWh/m2 y)", charts.bar_chart(
            [k.capitalize() for k in keys], [(t, by_title[t], LEVEL_COLORS[t]) for t in by_title], "kWh/m2 y")))
    return title, sections


def show_charts(level):
    """Charts of the results in the pyRevit output, saved as an HTML report: end uses by month, needs by zone,
    the simulated levels compared."""
    from pyrevit import script
    title, sections = chart_sections(level)
    path = files.bem_file("tbem_%s_Charts.html" % level)
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(charts.report(title, sections))
    output = script.get_output()
    output.print_md("## %s" % title)
    for heading, html in sections:
        output.print_md("### %s" % heading)
        output.print_html(html)
    return ["Charts of the %s in the pyRevit output (%d sections)." % (files.TITLES[level], len(sections)),
            "Report: %s" % path]


def show_map_3d(ctx, level):
    """Cells colored by a result of their zone in a 3D view, with a color scale."""
    key, label = choose_result(level)
    if not key:
        return ["Nothing shown."]
    view = show_cells(ctx, result_values(level, key), "BEM %s" % label,
                      note="%s - %s" % (files.TITLES[level], label), scale=True)
    return ["%s by zone in the view '%s'" % (label, view.Name)]


def plan_maps(ctx, values, title, legend_title, note, color_of, entries, text_of):
    """Floor plans 'TBIM - <title> - <level>' with the spaces filled by ``color_of(value)`` of ``values``
    ({space UID: value}), ``text_of(value)`` in each space and the legend ``entries`` of the values of the storey.
    Return the report lines."""
    spaces = [s for s in revit.spaces(ctx.doc) if revit.uid(s) in values and s.Area > 0]
    if not spaces:
        raise StepError("No Revit space of the model has a cell UID: run TBIM > Collectors first.")
    storeys = {}
    for space in spaces:
        storeys.setdefault(space.LevelId, []).append(space)
    boxes = [s.get_BoundingBox(None) for s in spaces]  # legend right of the whole building, on every plan
    corner = viz.XYZ(max(b.Max.X for b in boxes) + 10, max(b.Max.Y for b in boxes), 0)
    views, lines = [], []
    with revit.transaction(ctx.doc, "TBEM - %s (2D)" % title):
        for level_id in sorted(storeys, key=lambda i: ctx.doc.GetElement(i).Elevation):
            storey = ctx.doc.GetElement(level_id)
            view = viz.view_plan(ctx.doc, "%s - %s" % (title, storey.Name), storey)
            failed = 0
            for space in storeys[level_id]:
                value = values[revit.uid(space)]
                failed += not viz.fill_space(ctx.doc, view, space, color_of(value))
                viz.note_at(ctx.doc, view, space.Location.Point, text_of(value))
            shown = set(str(values[revit.uid(s)]) for s in storeys[level_id])
            viz.draw_legend(ctx.doc, view, corner, legend_title, entries(shown), note="%s - %s" % (note, storey.Name))
            views.append(view)
            lines.append("  %s: %d spaces%s" % (view.Name, len(storeys[level_id]),
                                                " (%d without a closed boundary)" % failed if failed else ""))
    ctx.uidoc.ActiveView = views[0]
    return ["%d floor plans:" % len(views)] + lines


def show_map_2d(ctx, level):
    """Spaces filled by a result of their zone in a floor plan per storey, with values and a color scale."""
    key, label = choose_result(level)
    if not key:
        return ["Nothing shown."]
    values = result_values(level, key)
    color_of, entries = colors.scale_for([values[revit.uid(s)] for s in revit.spaces(ctx.doc)
                                          if revit.uid(s) in values and s.Area > 0])

    def text_of(value):
        number = colors.number(value)
        return "%.1f" % number if number is not None else "-"
    return ["%s by zone in" % label] + plan_maps(ctx, values, "BEM %s" % label, label, files.TITLES[level],
                                                 color_of, lambda shown: entries, text_of)


def show_zones_2d(ctx):
    """Spaces filled by their thermal zone (the zones of the energy model) in a floor plan per storey, with the
    zone names and a legend of the zones of each storey."""
    zones = dict((uid, zone or NOT_MODELLED) for uid, zone in assignment().items())
    color_of, entries = colors.legend_for(list(zones.values()), numeric_threshold=len(zones))
    lines = plan_maps(ctx, zones, "BEM thermal zones", "Thermal zones", "TBEM zones of %s" % source()[0],
                      color_of, lambda shown: [(z, rgb) for z, rgb in entries if z in shown], str)
    return ["%d cells in %d thermal zones in" % (len(zones), len(set(zones.values()) - {NOT_MODELLED}))] + lines


def clear_visualizations(ctx):
    """Delete the TBEM shapes, the 'TBIM - BEM ...' views and their legends."""
    title = "BEM "
    if ctx.uidoc.ActiveView.Name.startswith((viz.VIEW_PREFIX + title, viz.LEGEND_PREFIX + title)):
        plans = [v for v in FilteredElementCollector(ctx.doc).OfClass(ViewPlan)
                 if not v.IsTemplate and not v.Name.startswith(viz.VIEW_PREFIX)]
        ctx.uidoc.ActiveView = plans[0]  # the active view cannot be deleted
    with revit.transaction(ctx.doc, "TBEM - Clear visualizations"):
        shapes, views = viz.delete_all(ctx.doc, TAG, title)
    return ["Deleted %d shapes and %d views/legends." % (shapes, views)]
