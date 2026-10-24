#! python3
"""Export a Topologic model of the workflow to JSON, BREP, OBJ or as the dual and passage graphs of the cells."""
from tbim import export, revit, scene, ui

models = scene.available_models()
label = ui.select("export_model", "Topologic model to export", [m[0] for m in models]) if models else None
if not models:
    revit.alert("Export Topologic", "No Topologic model yet: run Collectors > CellComplex > Create first.")
elif label:
    formats = [f[0] for f in export.FORMATS] + [export.ALL_FORMATS]
    choice = ui.select("export_format", "Export format", formats)
    if choice:
        extensions = [ext for name, ext in export.FORMATS if choice in (name, export.ALL_FORMATS)]
        written = [export.export_model(label, dict(models)[label], ext) for ext in extensions]
        revit.alert("Export Topologic", "%s exported:\n%s" % (label, "\n".join(written)))
