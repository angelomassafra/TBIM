#! python3
"""Show a Topologic model of the workflow: faces colored by topological type, windows and doors."""
from tbim import colors, revit, scene, topo, ui
from tbim import visualize as viz

TAG = "Model"
EXTERNAL_TRANSPARENCY = 60
ctx = revit.Context(__revit__)  # noqa: F821
models = scene.available_models()
label = ui.select("visualize_model", "Topologic model to show", [m[0] for m in models]) if models else None
if not models:
    revit.alert("Visualize", "No Topologic model yet: run Collectors > CellComplex > Create first.")
elif label:
    path = dict(models)[label]
    cc = topo.load_cellcomplex(path)
    used = set()
    with revit.transaction(ctx.doc, "TBIM - Visualize Topologic model"):
        viz.clear(ctx.doc, TAG)
        view = viz.view_3d(ctx.doc, "Topologic model")
        viz.set_hidden(view, viz.HOST_CATEGORIES, True)
        for uid, face_type, props, loop in scene.faces(cc):
            rgb = colors.TOPOLOGY_COLORS.get(face_type, colors.PALETTE[8])
            # external faces are see-through, so that the internal faces stay visible
            transparency = EXTERNAL_TRANSPARENCY if face_type in topo.EXTERNAL_TYPES else 0
            geometry = viz.polygons([loop], viz.material(ctx.doc, rgb, transparency))
            if geometry:
                viz.directshape(ctx.doc, geometry, TAG, uid or face_type)
                used.add(face_type)
        for props, loop in scene.apertures(path):
            kind = props.get("pr_TopologicalType", "window")
            # drawn on both sides of the host face, slightly offset to stay visible
            geometry = viz.polygons([viz.offset(loop, 2), viz.offset(loop, -2)],
                                    viz.material(ctx.doc, colors.TOPOLOGY_COLORS.get(kind, colors.PALETTE[8])))
            if geometry:
                viz.directshape(ctx.doc, geometry, TAG, props.get("UID", kind))
                used.add(kind)
        entries = [(t, rgb) for t, rgb in colors.TOPOLOGY_COLORS.items() if t in used]
        viz.show_only(ctx.doc, view, TAG)
        viz.legend(ctx.doc, "Topologic model", entries, note=label)
    ctx.uidoc.ActiveView = view
    revit.alert("Visualize", "%s shown in the 3D view '%s' (legend: '%sTopologic model')."
                % (label, view.Name, viz.LEGEND_PREFIX))
