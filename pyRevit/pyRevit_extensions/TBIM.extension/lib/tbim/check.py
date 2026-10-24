"""Project > Check Model: what is missing, unmatched or not styled in a TBIM project and its Revit model.

``project()`` checks the data files (CPython: reads the CellComplex models), ``model(doc)`` the Revit
elements. Both return findings ``(level, message)`` with level ERROR (the workflow cannot go on or gives
wrong data), WARNING (to check) or INFO.
"""
import os

from tbim import irs, materials, paths, projects
from tbim.jsonio import read_json

ERROR, WARNING, INFO = "ERROR", "WARNING", "INFO"
LEVELS = (ERROR, WARNING, INFO)
STYLE_KEYS = ("stFC_WallTypeName", "stFC_FloorTypeName", "stFC_RoofTypeName")
MAX_LISTED = 8


def _listed(items):
    items = sorted(str(i) for i in items)
    more = " and %d more" % (len(items) - MAX_LISTED) if len(items) > MAX_LISTED else ""
    return ", ".join(items[:MAX_LISTED]) + more


# --------------------------------------------------------------------------------------
# Data files
def rules(rulesets):
    """Styles without layers (generic Revit types) and layers of unknown materials."""
    findings = []
    plain = set()
    for rule in rulesets:
        style = next((rule[k] for k in STYLE_KEYS if k in rule), None)
        if not style:
            continue
        if not rule.get("stFC_Layers"):
            plain.add(style)
            continue
        try:
            materials.parse(rule["stFC_Layers"])
        except ValueError as e:
            findings.append((ERROR, "Style %s: %s" % (style, e)))
    if plain:
        findings.append((INFO, "%d styles without stFC_Layers (single-layer Revit types): %s" % (
            len(plain), _listed(plain))))
    return findings


def cellcomplex(cc):
    """Faces with holes, cells without occupancy type, faces without UID."""
    from topologicpy.CellComplex import CellComplex
    from topologicpy.Face import Face

    from tbim import topo
    findings = []
    holed = [topo.get(f, "UID", "face") for f in CellComplex.Faces(cc) if Face.InternalBoundaries(f)]
    if holed:
        findings.append((INFO, "%d faces with holes (floors and roofs get openings): %s" % (
            len(holed), _listed(holed))))
    cells = CellComplex.Cells(cc)
    default = [topo.cell_uid(c) for c in cells if topo.get(c, "pr_OccupancyType", "Default") == "Default"]
    if default:
        findings.append((WARNING, "%d of %d cells without occupancy type (Default ILD): %s" % (
            len(default), len(cells), _listed(default))))
    no_uid = [f for f in CellComplex.Faces(cc) if not topo.get(f, "UID")]
    if no_uid:
        findings.append((ERROR, "%d faces without UID" % len(no_uid)))
    return findings


def project():
    """Findings on the files of the active project."""
    findings = []
    folder = projects.active_project()
    if not folder:
        return [(ERROR, "No active project: the data folder %s is not in a project (Project > New or Open)."
                 % paths.data_dir())]
    findings.append((INFO, "Project: %s" % folder))
    breps = read_json(paths.data_file(paths.BREP_FILEPATHS), default=[])
    missing = [p for p in breps if not os.path.isfile(projects.resolve(p))]
    if not breps:
        findings.append((ERROR, "No BRep selected (3D Model > Import)."))
    elif missing:
        findings.append((ERROR, "BReps not found: %s" % _listed(missing)))
    done = [step for step, _, exists in projects.status(folder) if exists]
    todo = [step for step, _, exists in projects.status(folder) if not exists]
    findings.append((INFO, "Workflow outputs: %d of %d (%s)" % (
        len(done), len(done) + len(todo), "missing: " + ", ".join(todo) if todo else "complete")))
    for name, use in ((paths.ROOMS, "Loads > Assignment > From Table"),
                      (paths.APERTURE_RULES, "TopologicalBIM > By Rules")):
        found = paths.existing_data_file(name)
        if found and os.path.basename(found) != name:
            findings.append((WARNING, "%s has an old name: rename it %s" % (os.path.basename(found), name)))
        elif not found:
            findings.append((INFO, "No %s (%s not available)" % (name, use)))
    findings += rules(irs.load())
    for name in (paths.CC_STYLES, paths.CC_LOADS, paths.CC_CONTROLLERS):
        if os.path.isfile(paths.data_file(name)):
            from tbim import topo
            findings += cellcomplex(topo.load_cellcomplex(paths.data_file(name)))
            break
    return findings


# --------------------------------------------------------------------------------------
# Revit model
def model(doc):
    """Findings on the Revit model (needs the Revit API)."""
    from Autodesk.Revit.DB import BuiltInParameter

    from tbim import revit
    findings = []
    linked = revit.project_folder(doc)
    active = projects.active_project()
    if not linked:
        findings.append((WARNING, "The Revit model is not linked to a TBIM project (Project > Open)."))
    elif active and os.path.normcase(os.path.abspath(linked)) != os.path.normcase(active):
        findings.append((ERROR, "The Revit model is linked to %s, the active project is %s." % (linked, active)))

    hosts = [e for c in revit.FACE_CATEGORIES for e in revit.instances(doc, c)]
    spaces = revit.spaces(doc)
    openings = [e for c in revit.APERTURE_CATEGORIES for e in revit.instances(doc, c)]
    for label, elements in (("walls/floors/roofs", hosts), ("spaces", spaces), ("windows/doors", openings)):
        uids = [revit.uid(e) for e in elements]
        without = sum(1 for u in uids if not u)
        if without:
            findings.append((WARNING, "%d of %d %s without UID (not part of the TBIM)" % (
                without, len(elements), label)))
        seen, repeated = set(), set()
        for u in uids:
            if u:
                (repeated if u in seen else seen).add(u)
        if repeated:
            findings.append((ERROR, "Duplicated UIDs on %s: %s" % (label, _listed(repeated))))
    findings.append((INFO, "Revit: %d walls/floors/roofs, %d spaces, %d windows/doors with UID" % (
        sum(1 for e in hosts if revit.uid(e)), sum(1 for e in spaces if revit.uid(e)),
        sum(1 for e in openings if revit.uid(e)))))

    not_enclosed = [revit.uid(s) or s.Id for s in spaces
                    if s.get_Parameter(BuiltInParameter.ROOM_AREA).AsDouble() <= 0]
    if not_enclosed:
        findings.append((ERROR, "%d spaces not placed or not enclosed (area 0): %s" % (
            len(not_enclosed), _listed(not_enclosed))))
    if os.path.isfile(paths.data_file(paths.CC_CONTROLLERS)):
        from tbim import tbimjson
        cells = set(d.get("UID") for d in tbimjson.dictionaries(paths.data_file(paths.CC_CONTROLLERS))["Cell"])
        with_space = set(revit.uid(s) for s in spaces)
        if cells - with_space:
            findings.append((ERROR, "Cells without Revit space: %s" % _listed(cells - with_space)))
        if with_space - cells - {None}:
            findings.append((WARNING, "Spaces of cells that are not in the CellComplex: %s" % _listed(
                with_space - cells - {None})))

    styles = {}
    if os.path.isfile(paths.data_file(paths.CC_STYLES)):
        from tbim import tbimjson
        for d in tbimjson.dictionaries(paths.data_file(paths.CC_STYLES))["Face"]:
            style = next((d[k] for k in STYLE_KEYS if d.get(k)), None)
            if style:
                styles[d.get("UID")] = style
    wrong = []
    for element in hosts:
        style = styles.get(revit.uid(element))
        element_type = doc.GetElement(element.GetTypeId())
        if style and element_type is not None and revit.type_name(element_type) != style:
            wrong.append(revit.uid(element))
    if wrong:
        findings.append((WARNING, "%d elements without the type of their style (run Styles > Update): %s" % (
            len(wrong), _listed(wrong))))
    elif styles:
        findings.append((INFO, "All the styled elements have the type of their style"))

    recorded = [item["UID"] for item in read_json(paths.data_file(paths.APERTURE_LOCATIONS), default=[])]
    missing = sorted(set(recorded) - set(revit.uid(o) for o in openings))
    if missing:
        findings.append((ERROR, "%d windows/doors of the TopologicalBIM are not in the Revit model (do they fit "
                                "their wall?): %s" % (len(missing), _listed(missing))))
    hosts_by_id = dict((e.Id.Value, revit.uid(e)) for e in hosts)
    orphan = [revit.uid(o) for o in openings if revit.uid(o) and (
        o.Host is None or not hosts_by_id.get(o.Host.Id.Value))]
    if orphan:
        findings.append((WARNING, "Windows/doors not hosted by a TBIM wall: %s" % _listed(orphan)))
    return findings


def report(findings):
    counts = dict((level, sum(1 for f in findings if f[0] == level)) for level in LEVELS)
    lines = ["%d errors, %d warnings" % (counts[ERROR], counts[WARNING]), ""]
    for level in LEVELS:
        lines += ["%s - %s" % (level, message) for lv, message in findings if lv == level]
    return "\n".join(lines)
