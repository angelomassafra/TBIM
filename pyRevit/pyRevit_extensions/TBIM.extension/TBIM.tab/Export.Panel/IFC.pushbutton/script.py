#! python3
"""Export the Revit model to IFC, with the TBIM parameters as property sets."""
import os

from tbim import export, revit, ui

ctx = revit.Context(__revit__)  # noqa: F821
versions = revit.ifc_versions()
label = ui.select("export_ifc_version", "IFC version", [v[0] for v in versions])
if label:
    name = os.path.splitext(ctx.doc.Title)[0] or "tbim"
    path = revit.export_ifc(ctx.doc, export.export_dir(), name, dict(versions)[label])
    revit.alert("Export IFC", "%s exported:\n%s" % (label, path))
