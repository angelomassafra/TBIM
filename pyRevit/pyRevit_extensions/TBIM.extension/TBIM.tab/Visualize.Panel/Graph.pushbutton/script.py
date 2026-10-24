#! python3
"""Show the dual graph of the cells: nodes colored by thermal zone, edges by connection type."""
from tbim import colors, revit, scene, topo, ui
from tbim import visualize as viz

TAG = "Graph"
NODE_RADIUS_CM, EDGE_RADIUS_CM = 30, 8
ctx = revit.Context(__revit__)  # noqa: F821
models = scene.available_models()
label = ui.select("visualize_graph_model", "Graph of the model", [m[0] for m in models]) if models else None
if not models:
    revit.alert("Visualize", "No Topologic model yet: run Collectors > CellComplex > Create first.")
elif label:
    path = dict(models)[label]
    cc = topo.load_cellcomplex(path)
    nodes, edges = scene.graph(cc, [p for p, _ in scene.apertures(path)])
    key = next((k for k in ("rl_HasLocation_tpZN", "pr_OccupancyType") if any(k in n[2] for n in nodes)), "UID")
    color_of, node_entries = colors.legend_for([n[2].get(key) for n in nodes])
    points = dict((uid, point) for uid, point, _ in nodes)
    with revit.transaction(ctx.doc, "TBIM - Visualize graph"):
        viz.clear(ctx.doc, TAG)
        view = viz.view_3d(ctx.doc, "Graph")
        viz.ghost(view, viz.HOST_CATEGORIES, transparency=85)
        for uid, point, props in nodes:
            viz.directshape(ctx.doc, viz.sphere(point, NODE_RADIUS_CM, viz.material(ctx.doc, color_of(props.get(key)))),
                            TAG, "%s (%s)" % (uid, props.get(key)))
        for a, b, kind in edges:
            viz.directshape(ctx.doc, viz.cylinder(points[a], points[b], EDGE_RADIUS_CM,
                                                  viz.material(ctx.doc, colors.GRAPH_EDGE_COLORS[kind])),
                            TAG, "%s-%s (%s)" % (a, b, kind))
        viz.show_only(ctx.doc, view, TAG)
        kinds = [k for k in colors.GRAPH_EDGE_COLORS if any(e[2] == k for e in edges)]
        entries = [("Node: %s" % v, rgb) for v, rgb in node_entries]
        entries += [("Edge: %s" % k, colors.GRAPH_EDGE_COLORS[k]) for k in kinds]
        viz.legend(ctx.doc, "Graph", entries, note="%s - nodes by %s" % (label, key))
    ctx.uidoc.ActiveView = view
    counts = ", ".join("%s %d" % (k, sum(e[2] == k for e in edges)) for k in kinds)
    revit.alert("Visualize", "Graph of %s: %d nodes, %d edges (%s).\nView: '%s'." % (
        label, len(nodes), len(edges), counts, view.Name))
