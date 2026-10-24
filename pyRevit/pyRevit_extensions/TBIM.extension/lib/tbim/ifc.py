"""Export of the Revit model to IFC with the TBIM parameters as property sets (CPython and IronPython)."""
import os

from Autodesk.Revit.DB import FilteredElementCollector, Transaction

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
