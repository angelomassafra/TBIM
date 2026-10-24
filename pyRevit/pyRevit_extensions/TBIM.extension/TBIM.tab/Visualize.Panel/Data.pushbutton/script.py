#! python3
"""Color cells (as shapes) or Revit faces/apertures by a TBIM property, with a legend."""
from Autodesk.Revit.DB import BuiltInCategory

from tbim import colors, revit, scene, topo, ui
from tbim import visualize as viz

TAG = "Data"
CELLS, FACES, APERTURES = "Cells (spaces)", "Faces (walls, floors, roofs)", "Apertures (windows, doors)"
SKIP = ("UID", "uuid", "toplevel")
DEFAULT_PROPERTY = "rl_HasLocation_tpZN"


def color_cells(ctx):
    models = scene.available_models()
    if not models:
        return "No Topologic model yet: run Collectors > CellComplex > Create first."
    cells = scene.cells(topo.load_cellcomplex(models[0][1]), shrink=0.94)
    keys = sorted(set(k for _, props, _ in cells for k in props if k not in SKIP))
    prop = ui.select("visualize_data_property", "Cell property", keys, default=DEFAULT_PROPERTY)
    if not prop:
        return None
    color_of, entries = colors.legend_for([props.get(prop) for _, props, _ in cells])
    with revit.transaction(ctx.doc, "TBIM - Visualize cell data"):
        viz.clear(ctx.doc, TAG)
        view = viz.view_3d(ctx.doc, "Cells by data")
        viz.ghost(view, viz.HOST_CATEGORIES, transparency=90)
        for uid, props, loops in cells:
            geometry = viz.polygons(loops, viz.material(ctx.doc, color_of(props.get(prop))), closed=True)
            if geometry:
                viz.directshape(ctx.doc, geometry, TAG, "%s: %s" % (uid, props.get(prop)))
        viz.show_only(ctx.doc, view, TAG)
        viz.legend(ctx.doc, "Cells by data", entries, note="%s (%s)" % (prop, models[0][0]))
    ctx.uidoc.ActiveView = view
    return "%d cells colored by %s in the view '%s'." % (len(cells), prop, view.Name)


def color_elements(ctx, target):
    categories = viz.HOST_CATEGORIES[:3] if target == FACES else viz.HOST_CATEGORIES[3:]
    elements = [e for c in categories for e in revit.instances(ctx.doc, c) if revit.uid(e)]
    keys = sorted(set(p.Definition.Name for e in elements for p in e.Parameters
                      if p.IsShared and p.Definition.Name not in SKIP))
    if not keys:
        return "No TBIM data on these elements: run InstanceBIM > Revit > Update Data first."
    prop = ui.select("visualize_data_property", "Property", keys, default=DEFAULT_PROPERTY)
    if not prop:
        return None
    values = [revit.get_text(e, prop) for e in elements]
    color_of, entries = colors.legend_for(values)
    name = "Faces by data" if target == FACES else "Apertures by data"
    with revit.transaction(ctx.doc, "TBIM - Visualize element data"):
        view = viz.view_3d(ctx.doc, name)
        viz.set_hidden(view, [BuiltInCategory.OST_GenericModel], True)
        viz.reset_overrides(view, elements)
        solid = viz.solid_fill_id(ctx.doc)
        for element, value in zip(elements, values):
            viz.color_element(view, element.Id, color_of(value), solid)
        viz.legend(ctx.doc, name, entries, note=prop)
    ctx.uidoc.ActiveView = view
    return "%d elements colored by %s in the view '%s'." % (len(elements), prop, view.Name)


context = revit.Context(__revit__)  # noqa: F821
target = ui.select("visualize_data_target", "Color by data: elements", [CELLS, FACES, APERTURES])
message = None
if target == CELLS:
    message = color_cells(context)
elif target:
    message = color_elements(context, target)
if message:
    revit.alert("Visualize", message)
