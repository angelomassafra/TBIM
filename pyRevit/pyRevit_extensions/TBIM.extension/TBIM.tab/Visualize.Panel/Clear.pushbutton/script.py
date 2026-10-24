#! python3
"""Delete all the TBIM visualizations: shapes, 'TBIM - ' views and legends."""
from Autodesk.Revit.DB import FilteredElementCollector, ViewPlan

from tbim import revit
from tbim import visualize as viz

ctx = revit.Context(__revit__)  # noqa: F821
if ctx.uidoc.ActiveView.Name.startswith((viz.VIEW_PREFIX, viz.LEGEND_PREFIX)):
    plans = [v for v in FilteredElementCollector(ctx.doc).OfClass(ViewPlan) if not v.IsTemplate]
    ctx.uidoc.ActiveView = plans[0]  # the active view cannot be deleted
with revit.transaction(ctx.doc, "TBIM - Clear visualizations"):
    shapes, views = viz.delete_all(ctx.doc)
revit.alert("Visualize", "Deleted %d shapes and %d views/legends." % (shapes, views))
