#! python3
"""Color walls, floors, roofs, windows and doors by their Revit type, with a legend."""
from Autodesk.Revit.DB import BuiltInCategory

from tbim import colors, revit
from tbim import visualize as viz

ctx = revit.Context(__revit__)  # noqa: F821
doc = ctx.doc
elements = [e for c in viz.HOST_CATEGORIES for e in revit.instances(doc, c)]


def type_key(element):
    element_type = doc.GetElement(element.GetTypeId())
    return "%s: %s" % (element.Category.Name, revit.type_name(element_type) if element_type else "-")


keys = [type_key(e) for e in elements]
color_of, entries = colors.legend_for(keys, numeric_threshold=10 ** 6)
with revit.transaction(doc, "TBIM - Visualize element types"):
    view = viz.view_3d(doc, "Element types")
    viz.set_hidden(view, [BuiltInCategory.OST_GenericModel], True)
    viz.reset_overrides(view, elements)
    solid = viz.solid_fill_id(doc)
    for element, key in zip(elements, keys):
        viz.color_element(view, element.Id, color_of(key), solid)
    viz.legend(doc, "Element types", entries)
ctx.uidoc.ActiveView = view
revit.alert("Visualize", "%d elements of %d types colored in the view '%s'." % (len(elements), len(entries), view.Name))
