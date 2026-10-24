"""The steps of the TBIM workflow in Revit, as functions (CPython only).

Every step reads and writes the data files of the active project, takes its options as arguments (no
dialog) and returns the lines of its report; the ribbon commands call one step, Project > Run calls
them all (``run``). The steps:

    controllers      Collectors > CellComplex > Create
    assign_from_table / export_assignments   Loads > Assignment (table of rooms, or the Revit spaces)
    loads            Loads > CellComplex > Update / Clusterize
    styles           Styles > CellComplex > Update (Informational Rule Sets and layered Revit types)
    topological_bim  TopologicalBIM > ByRules (windows and doors)
    move_apertures, by_occupancy_type, by_table_of_spaces, by_model, update_revit   InstanceBIM
    export           Export > IFC and Topologic
"""
import os
import shutil
import time

from Autodesk.Revit.DB import BuiltInParameter
from topologicpy.CellComplex import CellComplex

from tbim import (
    apertures,
    collectors,
    ibim,
    ifc,
    ild,
    instancebim,
    irs,
    paths,
    projects,
    revit,
    revit_types,
    rooms,
    scene,
    tbimjson,
    topo,
)
from tbim import (
    export as tbim_export,
)
from tbim import (
    loads as tbim_loads,
)
from tbim import (
    styles as tbim_styles,
)
from tbim.jsonio import read_json, write_json
from tbim.units import ft2_to_m2, ft3_to_m3, ft_to_cm


class StepError(Exception):
    """A step cannot run (missing input): the message says what to do."""


def command(title, step):
    """Run one step for a ribbon command: report (or what is missing) in the TBIM alert."""
    try:
        lines = step()
    except StepError as e:
        lines = [str(e)]
    revit.alert(title, "\n".join(lines))


def _require(name, hint):
    path = paths.data_file(name)
    if not os.path.isfile(path):
        raise StepError("%s is missing: %s" % (name, hint))
    return path


# --------------------------------------------------------------------------------------
# Collectors and Loads
def controllers(ctx):
    """Create the Informational Controllers from the BReps of the 3D model."""
    brep_paths = [projects.resolve(p) for p in read_json(paths.data_file(paths.BREP_FILEPATHS), default=[])]
    if not brep_paths:
        raise StepError("No BRep selected: use 3D Model > Import first.")
    cc, report = collectors.run(ctx, brep_paths)
    path = topo.save_cellcomplex(cc, paths.data_file(paths.CC_CONTROLLERS))
    if ctx.link_active_project():
        report.append("Revit model linked to the project %s" % projects.active_project())
    return report + ["Exported to: %s" % path]


def has_controllers(doc):
    """True if the model already has the spaces of the Informational Controllers."""
    return any(revit.uid(s) for s in revit.spaces(doc))


def assign_from_table(ctx, rooms_path=None):
    """Occupancy types and space names of the cells from the table of rooms (tbim_Rooms.json)."""
    rooms_path = rooms_path or paths.existing_data_file(paths.ROOMS)
    if not rooms_path:
        raise StepError("No table of rooms (%s) in the project." % paths.ROOMS)
    cc = topo.load_cellcomplex(_require(paths.CC_CONTROLLERS, "run Collectors > CellComplex > Create first."))
    matches, shared = rooms.match(cc, read_json(rooms_path))
    occupancy, names = rooms.assignments(matches), rooms.space_ids(matches)
    ild.save_assignments(occupancy)
    count = 0
    with revit.transaction(ctx.doc, "Assignment from the table of rooms"):
        for space in revit.spaces(ctx.doc):
            uid = revit.uid(space)
            if uid not in matches:
                continue
            revit.set_by_name(space, ild.OCCUPANCY_KEY, occupancy[uid])
            revit.set_builtin(space, BuiltInParameter.ROOM_NAME, names[uid])
            revit.set_builtin(space, BuiltInParameter.ROOM_NUMBER, names[uid])
            count += 1
    report = ["%d cells matched with %d rooms of %s; %d spaces updated" % (
        len(matches), len(read_json(rooms_path)), os.path.basename(rooms_path), count)]
    if shared:
        report.append("WARNING - cells sharing a room (check the room points): %s" % ", ".join(shared))
    return report


def export_assignments(ctx):
    """Save the occupancy types set on the Revit spaces (Loads > Assignment by building/storey/cell)."""
    assignments = revit.occupancy_assignments(ctx.doc)
    path = ild.save_assignments(assignments)
    return ["Occupancy types of %d spaces exported to %s" % (len(assignments), path)]


def loads(ctx, clusterize=True):
    """Informational Loads (and thermal zones) of the cells and faces; the cell data goes to the spaces."""
    cc = topo.load_cellcomplex(_require(paths.CC_CONTROLLERS, "run Collectors > CellComplex > Create first."))
    north = float(read_json(paths.data_file(paths.NORTH_ANGLE), default=0))
    face_keys = tbim_loads.run(cc, ild.load(), ild.load_assignments(), north, clusterize=clusterize)
    write_json(paths.data_file(paths.FACE_PROPERTIES), face_keys)
    cells = dict((topo.cell_uid(c), topo.props(c)) for c in CellComplex.Cells(cc))
    revit.ensure_parameters(ctx, set(k for p in cells.values() for k in p), "Cell", revit.SPACE_CATEGORIES)
    updated = revit.apply_by_uid(ctx.doc, revit.spaces(ctx.doc), cells, "Update spaces")
    outputs = [paths.CC_LOADS] + ([paths.CC_LOADS_CLUSTERIZED] if clusterize else [])
    saved = [topo.save_cellcomplex(cc, paths.data_file(name)) for name in outputs]
    report = ["Informational Loads assigned to %d cells (%d spaces updated)" % (len(cells), updated)]
    if clusterize:
        report.insert(0, "Thermal zones: %d" % len(set(p.get("rl_HasLocation_tpZN") for p in cells.values())))
    return report + ["Exported to: %s" % ", ".join(saved)]


# --------------------------------------------------------------------------------------
# Styles and TopologicalBIM
def styles(ctx, revit_types_too=True):
    """Apply the Informational Rule Sets to the faces and give the Revit elements their layered types."""
    cc = topo.load_cellcomplex(_require(paths.CC_LOADS, "run Loads > CellComplex > Update first."))
    rulesets = irs.load()
    styled = tbim_styles.run(cc, rulesets)
    path = topo.save_cellcomplex(cc, paths.data_file(paths.CC_STYLES))
    report = ["%d rule sets applied, %d faces styled" % (len(rulesets), styled)]
    if revit_types_too:
        faces = dict((topo.get(f, "UID"), topo.props(f)) for f in CellComplex.Faces(cc) if topo.get(f, "UID"))
        counts, problems = revit_types.apply_styles(ctx.doc, faces)
        report.append("Revit types: %d walls, %d floors, %d roofs (%d types created)" % (
            counts["Walls"], counts["Floors"], counts["Roofs"], counts["Types created"]))
        report += ["WARNING - %s" % p for p in problems[:20]]
    return report + ["Exported to: %s" % path]


def topological_bim(ctx, rules_path=None):
    """Windows and doors by rules (tbim_TopologicalBIM_Rules.json) on the styled CellComplex and in Revit."""
    rules_path = rules_path or paths.existing_data_file(paths.APERTURE_RULES)
    if not rules_path:
        raise StepError("No TopologicalBIM rules (%s) in the project." % paths.APERTURE_RULES)
    cc = topo.load_cellcomplex(_require(paths.CC_STYLES, "run Styles > CellComplex > Update first."))
    cc, placements = apertures.place(cc, read_json(rules_path))
    topo.save_cellcomplex(cc, paths.data_file(paths.CC_TBIM))
    write_json(paths.data_file(paths.APERTURE_LOCATIONS), apertures.locations(placements))
    placed, problems = revit_types.place_apertures(ctx, placements)
    counts = dict((k, sum(p["kind"] == k for p in placements)) for k in apertures.KINDS)
    report = ["Apertures: %d windows, %d doors (%d placed in Revit)" % (counts["window"], counts["door"], placed)]
    return report + ["WARNING - %s" % p for p in problems[:20]] + ["Exported to: %s" % paths.data_file(paths.CC_TBIM)]


def without_apertures():
    """TopologicalBIM without windows and doors: the styled CellComplex as it is."""
    shutil.copyfile(_require(paths.CC_STYLES, "run Styles > CellComplex > Update first."),
                    paths.data_file(paths.CC_TBIM))
    write_json(paths.data_file(paths.APERTURE_LOCATIONS), [])
    return ["No TopologicalBIM rules: the TopologicalBIM is the styled CellComplex, without apertures"]


# --------------------------------------------------------------------------------------
# InstanceBIM
def move_apertures(ctx):
    """InstanceBIM from the TopologicalBIM, with the apertures moved like the windows and doors in Revit."""
    recorded = dict((item["UID"], item["Location"]) for item in read_json(paths.data_file(paths.APERTURE_LOCATIONS),
                                                                           default=[]))
    moves = {}
    for element in [e for c in revit.APERTURE_CATEGORIES for e in revit.instances(ctx.doc, c)]:
        element_uid = revit.uid(element)
        point = getattr(element.Location, "Point", None)
        if element_uid not in recorded or point is None:
            continue
        movement = ibim.aperture_movement([int(ft_to_cm(v)) for v in (point.X, point.Y, point.Z)],
                                          recorded[element_uid])
        if movement:
            moves[element_uid] = movement
    records = read_json(_require(paths.CC_TBIM, "run TopologicalBIM first."))
    moved = tbimjson.move_apertures(records, moves)
    path = write_json(paths.data_file(paths.CC_IBIM), records)
    return ["%d apertures moved" % len(moved)] + ["  %s: %s cm" % (uid, moves[uid]) for uid in moved] + [
        "InstanceBIM exported to: %s" % path]


def _instance_bim(function, message):
    cc = topo.load_cellcomplex(_require(paths.CC_IBIM, "run InstanceBIM > MoveApertures first."))
    result = function(cc)
    path = topo.save_cellcomplex(cc, paths.data_file(paths.CC_IBIM))
    return [message % result, "InstanceBIM exported to: %s" % path]


def by_occupancy_type(ctx):
    table = read_json(paths.data_file(paths.IBIM_BY_OCCUPANCY_TYPE), default=[])
    return _instance_bim(lambda cc: instancebim.by_occupancy_type(cc, table) or len(table),
                         "Instance data of %d occupancy types added")


def space_names(doc):
    """{cell UID: name of its Revit space} (the ids of the rows of the table of spaces, ';' separated)."""
    names = {}
    for space in revit.spaces(doc):
        name = space.get_Parameter(BuiltInParameter.ROOM_NAME)
        if revit.uid(space) and name is not None and name.AsString():
            names[revit.uid(space)] = name.AsString()
    return names


def by_table_of_spaces(ctx):
    table = read_json(paths.data_file(paths.IBIM_BY_TABLE_OF_SPACES), default=[])
    names = space_names(ctx.doc)
    return _instance_bim(lambda cc: instancebim.by_table_of_spaces(cc, table, names),
                         "%d cells matched with the table of spaces")


def by_model(ctx):
    net = {}
    for space in revit.spaces(ctx.doc):
        if revit.uid(space):
            net[revit.uid(space)] = (ft2_to_m2(space.get_Parameter(BuiltInParameter.ROOM_AREA).AsDouble()),
                                     ft3_to_m3(space.get_Parameter(BuiltInParameter.ROOM_VOLUME).AsDouble()))
    return _instance_bim(lambda cc: instancebim.by_model(cc, net), "ByModel data computed for %d cells")


def update_revit(ctx):
    """Write the InstanceBIM data to the spaces, walls, floors, roofs, windows and doors (matched by UID)."""
    data = tbimjson.dictionaries(_require(paths.CC_IBIM, "run the InstanceBIM steps first."))
    report = []
    for label, items, group, categories in (("Spaces", data["Cell"], "Cell", revit.SPACE_CATEGORIES),
                                            ("Walls/Floors/Roofs", data["Face"], "Face", revit.FACE_CATEGORIES),
                                            ("Windows/Doors", data["Aperture"], "Aperture",
                                             revit.APERTURE_CATEGORIES)):
        revit.ensure_parameters(ctx, set(k for d in items for k in d), group, categories)
        elements = [e for c in categories for e in revit.instances(ctx.doc, c)]
        count = revit.apply_by_uid(ctx.doc, elements, tbimjson.by_uid(items), "Update %s" % label)
        report.append("%s updated: %d" % (label, count))
    return report


# --------------------------------------------------------------------------------------
# Export
def export(ctx, ifc_version="IFC4 Reference View", model="InstanceBIM", formats=None):
    """IFC of the Revit model and the Topologic model in all the formats (or ``formats``: extensions)."""
    report = []
    if ifc_version:
        versions = dict(ifc.ifc_versions())
        if ifc_version not in versions:
            raise StepError("IFC version '%s' not available in this Revit" % ifc_version)
        name = os.path.splitext(ctx.doc.Title)[0] or "tbim"
        report.append("IFC: %s" % ifc.export_ifc(ctx.doc, tbim_export.export_dir(), name, versions[ifc_version]))
    models = dict(scene.available_models())
    if model in models:
        for _, extension in tbim_export.FORMATS:
            if formats is None or extension in formats:
                report.append("Topologic: %s" % tbim_export.export_model(model, models[model], extension))
    return report


# --------------------------------------------------------------------------------------
# The whole workflow
def run(ctx, log=print, export_too=True):
    """Run every step whose inputs are in the project. Return (completed steps, report lines).

    - Collectors: only if the model has no TBIM spaces yet (otherwise its CellComplex is reused);
    - Assignment: from the table of rooms if the project has one, else the occupancy types of the spaces;
    - TopologicalBIM: by rules if the project has them, else the styled CellComplex without apertures.
    """
    steps = []
    if not has_controllers(ctx.doc):
        steps.append(("Collectors > CellComplex > Create", lambda: controllers(ctx)))
    elif os.path.isfile(paths.data_file(paths.CC_CONTROLLERS)):
        steps.append(("Collectors (already in the model: kept)", lambda: []))
    else:
        raise StepError("The model has TBIM spaces but the project has no %s: link the model to its project "
                        "(Project > Open) or delete them (Collectors > CellComplex > Delete)." % paths.CC_CONTROLLERS)
    if paths.existing_data_file(paths.ROOMS):
        steps.append(("Loads > Assignment > From Table", lambda: assign_from_table(ctx)))
    else:
        steps.append(("Loads > Assignment (occupancy types of the spaces)", lambda: export_assignments(ctx)))
    steps += [("Loads > CellComplex > Clusterize", lambda: loads(ctx, clusterize=True)),
              ("Styles > CellComplex > Update", lambda: styles(ctx))]
    if paths.existing_data_file(paths.APERTURE_RULES):
        steps.append(("TopologicalBIM > ByRules", lambda: topological_bim(ctx)))
    else:
        steps.append(("TopologicalBIM (no rules)", without_apertures))
    steps += [("InstanceBIM > MoveApertures", lambda: move_apertures(ctx)),
              ("InstanceBIM > ByOccupancyType", lambda: by_occupancy_type(ctx)),
              ("InstanceBIM > ByTableOfSpaces", lambda: by_table_of_spaces(ctx)),
              ("InstanceBIM > ByModel", lambda: by_model(ctx)),
              ("InstanceBIM > Revit > UpdateData", lambda: update_revit(ctx))]
    if export_too:
        steps.append(("Export > IFC and Topologic", lambda: export(ctx)))
    done, report = [], []
    for title, step in steps:
        start = time.time()
        log("== %s" % title)
        try:
            lines = step()
        except StepError as e:
            report += ["%s: STOPPED - %s" % (title, e)]
            log("   STOPPED: %s" % e)
            break
        except Exception as e:
            import traceback
            log(traceback.format_exc())
            report += ["%s: FAILED - %s" % (title, e)]
            break
        for line in lines:
            log("   " + line)
        done.append(title)
        report.append("%s (%.0f s)" % (title, time.time() - start))
        report += ["   " + line for line in lines if not line.startswith(("Exported to", "InstanceBIM exported"))]
    return done, report
