"""Revit API helpers shared by all TBIM commands (IronPython and CPython).

Targets Revit 2026 (.NET 8): parameter groups use ``GroupTypeId`` (the
``BuiltInParameterGroup`` enum no longer exists) and locale dependent parameter
names are replaced by ``BuiltInParameter`` values.
"""
import io
import os
import sys

import clr

clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import (  # noqa: E402
    BuiltInCategory,
    BuiltInParameter,
    Category,
    ElementTypeGroup,
    ExternalDefinitionCreationOptions,
    FailureProcessingResult,
    FailureSeverity,
    FilteredElementCollector,
    GroupTypeId,
    IFailuresPreprocessor,
    Level,
    SpecTypeId,
    StorageType,
    Transaction,
    ViewFamily,
    ViewFamilyType,
    ViewPlan,
)
from Autodesk.Revit.UI import TaskDialog  # noqa: E402

from tbim import paths  # noqa: E402

UID_PARAMETER = "UID"
NAN = "NaN"

SPACE_CATEGORIES = [BuiltInCategory.OST_MEPSpaces]
FACE_CATEGORIES = [BuiltInCategory.OST_Walls, BuiltInCategory.OST_Floors, BuiltInCategory.OST_Roofs]
APERTURE_CATEGORIES = [BuiltInCategory.OST_Windows, BuiltInCategory.OST_Doors]


class Context(object):
    """Revit handles from pyRevit's ``__revit__`` (a UIApplication)."""

    def __init__(self, revit):
        self.uiapp = revit
        self.app = revit.Application
        self.uidoc = revit.ActiveUIDocument
        if self.uidoc is None:
            raise RuntimeError("TBIM: open a Revit project first.")
        self.doc = self.uidoc.Document


def alert(title, message):
    """Task dialog, or console output when tbim_settings.json has "dialogs": false (automation)."""
    if not paths.read_settings().get("dialogs", True):
        text = u"TBIM - %s\n%s\n" % (title, message)
        print(text)
        with io.open(paths.data_file("tbim.log"), "a", encoding="utf-8") as f:
            f.write(text + u"\n")
        return
    dialog = TaskDialog("TBIM - " + title)
    dialog.MainContent = message
    dialog.Show()


def _dismiss_warnings_class():
    """The failures preprocessor, defined once per Revit session: pythonnet cannot define the same .NET type
    twice, so a module reload (Installation > Check) reuses the class kept on ``sys``."""
    cls = getattr(sys, "_tbim_dismiss_warnings", None)
    if cls is not None:
        return cls

    class DismissWarnings(IFailuresPreprocessor):
        """Delete the warnings of a transaction (e.g. 'Space is not in a properly enclosed region') and apply
        the default resolution of the errors that have one (e.g. 'Can't keep elements joined' -> unjoin), so
        that no modal dialog stops the TBIM commands. Other errors are left to Revit."""

        __namespace__ = "TBIM.Failures"  # pythonnet: .NET classes defined in Python need a namespace

        def PreprocessFailures(self, accessor):
            resolved = False
            for failure in accessor.GetFailureMessages():
                if failure.GetSeverity() == FailureSeverity.Warning:
                    accessor.DeleteWarning(failure)
                elif failure.HasResolutions():
                    accessor.ResolveFailure(failure)
                    resolved = True
            return FailureProcessingResult.ProceedWithCommit if resolved else FailureProcessingResult.Continue

    sys._tbim_dismiss_warnings = DismissWarnings
    return DismissWarnings


DismissWarnings = _dismiss_warnings_class()


class transaction(object):
    """``with transaction(doc, 'name'):`` - commit on success, roll back on errors; warnings are dismissed."""

    def __init__(self, doc, name):
        self.t = Transaction(doc, "TBIM: " + name)
        options = self.t.GetFailureHandlingOptions()
        options.SetFailuresPreprocessor(DismissWarnings())
        self.t.SetFailureHandlingOptions(options)

    def __enter__(self):
        self.t.Start()
        return self.t

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.t.Commit()
        elif self.t.HasStarted() and not self.t.HasEnded():
            self.t.RollBack()
        return False


# --------------------------------------------------------------------------------------
# Elements and parameters
def instances(doc, category):
    return list(FilteredElementCollector(doc).OfCategory(category).WhereElementIsNotElementType().ToElements())


def levels(doc):
    return sorted(FilteredElementCollector(doc).OfClass(Level).ToElements(), key=lambda lv: lv.Elevation)


def nearest_level(level_list, elevation_ft):
    return min(level_list, key=lambda lv: abs(lv.Elevation - elevation_ft))


def get_text(element, name):
    p = element.LookupParameter(name)
    return p.AsString() if p is not None else None


def uid(element):
    return get_text(element, UID_PARAMETER)


def to_text(value):
    """Revit text value of a TBIM property: undefined values become 'NaN'."""
    if value is None:
        return NAN
    text = str(value)
    if text == "" or text.startswith("Undef") or text == "None":
        return NAN
    return text


def set_value(parameter, value):
    """Set a parameter according to its storage type. Return True if set."""
    if parameter is None or parameter.IsReadOnly:
        return False
    storage = parameter.StorageType
    if storage == StorageType.String:
        return parameter.Set(to_text(value))
    if storage == StorageType.Double:
        return parameter.Set(float(value))
    if storage == StorageType.Integer:
        return parameter.Set(int(value))
    if storage == StorageType.ElementId:
        return parameter.Set(value)
    return False


def set_by_name(element, name, value):
    return set_value(element.LookupParameter(name), value)


def set_builtin(element, builtin, value):
    return set_value(element.get_Parameter(builtin), value)


def apply_by_uid(doc, elements, values_by_uid, name):
    """Write the properties {key: value} of ``values_by_uid[UID]`` to the matching elements."""
    count = 0
    with transaction(doc, name):
        for element in elements:
            values = values_by_uid.get(uid(element))
            if values is None:
                continue
            for key, value in values.items():
                if key != UID_PARAMETER:
                    set_by_name(element, key, value)
            count += 1
    return count


def type_name(element_type):
    p = element_type.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM)
    return p.AsString() if p is not None else None


def wall_type_id(doc, name="Default"):
    """Id of the wall type called ``name``, or the default wall type of the document."""
    types = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Walls).WhereElementIsElementType()
    for wall_type in types:
        if type_name(wall_type) == name:
            return wall_type.Id
    return doc.GetDefaultElementTypeId(ElementTypeGroup.WallType)


def floor_plan_type_id(doc):
    for vft in FilteredElementCollector(doc).OfClass(ViewFamilyType):
        if vft.ViewFamily == ViewFamily.FloorPlan:
            return vft.Id
    return None


def create_floor_plans(doc, level_list):
    type_id = floor_plan_type_id(doc)
    if type_id is None:
        return []
    with transaction(doc, "Create floor plans"):
        return [ViewPlan.Create(doc, type_id, lv.Id) for lv in level_list]


# --------------------------------------------------------------------------------------
# Shared parameters
def _binding_categories(binding):
    # BindingMap returns a Binding: read Categories via reflection (works with IronPython and pythonnet)
    prop = binding.GetType().GetProperty("Categories")
    return prop.GetValue(binding, None) if prop is not None else None


def _bound_definitions(doc):
    """{parameter name: (definition, binding)} of the document."""
    result = {}
    iterator = doc.ParameterBindings.ForwardIterator()
    iterator.Reset()
    while iterator.MoveNext():
        result[iterator.Key.Name] = (iterator.Key, iterator.Current)
    return result


def _tbim_shared_parameter_file(app):
    path = paths.shared_parameter_file()
    if not os.path.exists(path):
        with io.open(path, "w", encoding="utf-8") as f:
            f.write(u"")
    app.SharedParametersFilename = path
    return app.OpenSharedParameterFile()


def ensure_parameters(ctx, names, group_name, categories):
    """Create/bind text instance parameters ``names`` to ``categories`` (one transaction).

    Definitions are stored in <tbim>/tbim_SharedParameters.txt; the user's shared
    parameter file setting is restored afterwards.
    """
    doc, app = ctx.doc, ctx.app
    names = [n for n in sorted(set(names)) if n]
    cats = [Category.GetCategory(doc, c) for c in categories]
    bound = _bound_definitions(doc)
    original = app.SharedParametersFilename
    try:
        sp_file = None
        with transaction(doc, "Bind parameters (%s)" % group_name):
            for name in names:
                category_set = app.Create.NewCategorySet()
                for cat in cats:
                    category_set.Insert(cat)
                if name in bound:
                    definition, binding = bound[name]
                    existing = _binding_categories(binding)
                    missing = [c for c in cats if existing is None or not existing.Contains(c)]
                    if not missing:
                        continue
                    if existing is not None:
                        for cat in existing:
                            category_set.Insert(cat)
                    doc.ParameterBindings.ReInsert(definition, app.Create.NewInstanceBinding(category_set),
                                                   GroupTypeId.Data)
                    continue
                if sp_file is None:
                    sp_file = _tbim_shared_parameter_file(app)
                group = sp_file.Groups.get_Item(group_name) or sp_file.Groups.Create(group_name)
                definition = group.Definitions.get_Item(name)
                if definition is None:
                    options = ExternalDefinitionCreationOptions(name, SpecTypeId.String.Text)
                    definition = group.Definitions.Create(options)
                doc.ParameterBindings.Insert(definition, app.Create.NewInstanceBinding(category_set), GroupTypeId.Data)
    finally:
        if original is not None and app.SharedParametersFilename != original:
            app.SharedParametersFilename = original


# --------------------------------------------------------------------------------------
# Spaces
def spaces(doc):
    return instances(doc, BuiltInCategory.OST_MEPSpaces)


def occupancy_assignments(doc):
    """{space UID: pr_OccupancyType} of all the spaces with a UID."""
    result = {}
    for space in spaces(doc):
        space_uid = uid(space)
        if space_uid:
            result[space_uid] = get_text(space, "pr_OccupancyType") or "Default"
    return result


# --------------------------------------------------------------------------------------
# Projects
def project_folder(doc):
    """TBIM project folder stored in the Project Information of ``doc`` (or None)."""
    from tbim.projects import REVIT_PARAMETER
    value = get_text(doc.ProjectInformation, REVIT_PARAMETER)
    return value if value and value != NAN else None


def link_project(ctx, folder):
    """Store the TBIM project folder in the Project Information of the model."""
    from tbim.projects import REVIT_PARAMETER
    ensure_parameters(ctx, [REVIT_PARAMETER], "Project", [BuiltInCategory.OST_ProjectInformation])
    with transaction(ctx.doc, "Link TBIM project"):
        set_by_name(ctx.doc.ProjectInformation, REVIT_PARAMETER, folder)


def delete_controllers(doc):
    """Delete zones, spaces, walls, floors, roofs and levels. Return {category: count}."""
    counts = {}
    with transaction(doc, "Delete Informational Controllers"):
        zone_ids = set()
        for space in spaces(doc):
            if space.Zone is not None and not space.Zone.IsDefaultZone:
                zone_ids.add(space.Zone.Id)
        targets = [("Zones", list(zone_ids))]
        for label, category in (("Spaces", BuiltInCategory.OST_MEPSpaces), ("Walls", BuiltInCategory.OST_Walls),
                                ("Floors", BuiltInCategory.OST_Floors), ("Roofs", BuiltInCategory.OST_Roofs),
                                ("Levels", BuiltInCategory.OST_Levels)):
            targets.append((label, [e.Id for e in instances(doc, category)]))
        for label, ids in targets:
            counts[label] = 0
            for element_id in ids:
                try:
                    if doc.GetElement(element_id) is not None:
                        doc.Delete(element_id)
                        counts[label] += 1
                except Exception:
                    pass  # e.g. the last level of the model cannot be deleted
    return counts


# --------------------------------------------------------------------------------------
# Export
# (label, IFCVersion member) - members missing in older Revit versions are skipped
IFC_VERSIONS = [
    ("IFC4 Reference View", "IFC4RV"),
    ("IFC4 Design Transfer View", "IFC4DTV"),
    ("IFC2x3 Coordination View 2.0", "IFC2x3CV2"),
    ("IFC4x3", "IFC4x3"),
]


def ifc_versions():
    from Autodesk.Revit.DB import IFCVersion
    return [(label, getattr(IFCVersion, name)) for label, name in IFC_VERSIONS if hasattr(IFCVersion, name)]


IFC_SETTINGS = [  # IFCExportConfiguration properties
    ("ExportInternalRevitPropertySets", True),  # Revit and shared parameters: UID, pr_*, rl_*, st*
    ("ExportIFCCommonPropertySets", True),
    ("ExportBaseQuantities", True),
    ("SpaceBoundaries", 1),
    ("SplitWallsAndColumns", False),
]


def _ifc_options(doc, version):
    """IFCExportOptions from the configuration of the Revit IFC exporter, with the TBIM property sets.

    Revit 2026 ignores the named options of IFCExportOptions for the property sets: they come from an IFC
    parameter template that IFCExportConfiguration.UpdateOptions creates for the exporter's current document.
    """
    from Autodesk.Revit.DB import ElementId, IFCExportOptions
    from System import AppDomain, Array, Int32, Object
    options = IFCExportOptions()
    options.FileVersion = version
    config_type = None
    for assembly in AppDomain.CurrentDomain.GetAssemblies():
        config_type = assembly.GetType("BIM.IFC.Export.UI.IFCExportConfiguration")
        if config_type is not None:
            app_type = assembly.GetType("BIM.IFC.Export.UI.IFCCommandOverrideApplication")
            break
    if config_type is None:  # IFC exporter add-in not loaded: geometry and base quantities only
        options.ExportBaseQuantities = True
        return options
    config = config_type.GetMethod("CreateDefaultConfiguration").Invoke(None, None)
    config_type.GetProperty("IFCVersion").SetValue(config, version)
    for name, value in IFC_SETTINGS:
        # PropertyInfo.SetValue takes an Object: Python ints must be boxed explicitly
        value = value if isinstance(value, bool) else Int32(value)
        config_type.GetProperty(name).SetValue(config, value)
    current = app_type.GetProperty("TheDocument")
    previous = current.GetValue(None)
    current.SetValue(None, doc)
    try:
        config_type.GetMethod("UpdateOptions").Invoke(config, Array[Object]([options, ElementId.InvalidElementId]))
    finally:
        current.SetValue(None, previous)
    return options


def export_ifc(doc, folder, name, version):
    """Export ``doc`` to ``<folder>/<name>.ifc`` with the TBIM parameters as property sets. Return the path.

    The IFC exporter needs an open transaction; it is rolled back so the model is left unchanged, and the
    TBIM visualizations (DirectShapes) are deleted in it so they are not exported as proxies.
    """
    from Autodesk.Revit.DB import DirectShape
    options = _ifc_options(doc, version)
    t = Transaction(doc, "TBIM: Export IFC")
    t.Start()
    try:
        shapes = [e.Id for e in FilteredElementCollector(doc).OfClass(DirectShape).ToElements()
                  if e.ApplicationId == "TBIM"]
        for shape_id in shapes:
            doc.Delete(shape_id)
        ok = doc.Export(folder, name, options)
    finally:
        t.RollBack()
    path = os.path.join(folder, name + ".ifc")
    if not ok or not os.path.isfile(path):
        raise RuntimeError("Revit could not export %s" % path)
    return path
