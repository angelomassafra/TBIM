"""Visualizations of the TBIM models in Revit (Revit API; geometry from tbim.scene).

- Topologic models and graphs are DirectShapes (Generic Models) colored with
  'TBIM #RRGGBB' materials, so they keep their colors in every view;
- Revit elements are colored with view overrides in dedicated 3D views;
- legends are drafting views 'TBIM Legend - <title>' (filled regions + labels);
- 2D maps are floor plans 'TBIM - <title> - <level>' with the spaces filled by color, labels and a legend.
Every visualization replaces the previous one with the same tag.
"""
import math
import re

import clr

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import (  # noqa: E402
    XYZ,
    Arc,
    BuiltInCategory,
    BuiltInParameter,
    Color,
    CurveLoop,
    DirectShape,
    DisplayStyle,
    ElementId,
    FilledRegion,
    FilledRegionType,
    FillPatternElement,
    FilteredElementCollector,
    Frame,
    GeometryCreationUtilities,
    GeometryObject,
    Line,
    Material,
    OverrideGraphicSettings,
    Plane,
    SolidOptions,
    SpatialElementBoundaryOptions,
    TessellatedFace,
    TessellatedShapeBuilder,
    TessellatedShapeBuilderFallback,
    TessellatedShapeBuilderTarget,
    TextNote,
    TextNoteType,
    View3D,
    ViewDetailLevel,
    ViewDrafting,
    ViewFamily,
    ViewFamilyType,
    ViewOrientation3D,
    ViewPlan,
)
from System.Collections.Generic import List  # noqa: E402

from tbim import colors, revit, scene, topo, ui  # noqa: E402
from tbim.units import cm_to_ft  # noqa: E402

APPLICATION_ID = "TBIM"
VIEW_PREFIX = "TBIM - "
LEGEND_PREFIX = "TBIM Legend - "
NODE_RADIUS_CM, EXTERIOR_RADIUS_CM, EDGE_RADIUS_CM = 30, 20, 8
HOST_CATEGORIES = [BuiltInCategory.OST_Walls, BuiltInCategory.OST_Floors, BuiltInCategory.OST_Roofs,
                   BuiltInCategory.OST_Windows, BuiltInCategory.OST_Doors]


def _xyz(p):
    return XYZ(cm_to_ft(p[0]), cm_to_ft(p[1]), cm_to_ft(p[2]))


def _color(rgb):
    return Color(int(rgb[0]), int(rgb[1]), int(rgb[2]))


# --------------------------------------------------------------------------------------
# Materials, patterns, types
def material(doc, rgb, transparency=0):
    name = "TBIM %s%s" % (colors.to_hex(rgb), " T%d" % transparency if transparency else "")
    for m in FilteredElementCollector(doc).OfClass(Material):
        if m.Name == name:
            return m.Id
    m = doc.GetElement(Material.Create(doc, name))
    m.Color = _color(rgb)
    m.Transparency = transparency
    return m.Id


def solid_fill_id(doc):
    for p in FilteredElementCollector(doc).OfClass(FillPatternElement):
        if p.GetFillPattern().IsSolidFill:
            return p.Id
    return ElementId.InvalidElementId


def filled_region_type(doc, rgb):
    name = "TBIM %s" % colors.to_hex(rgb)
    types = list(FilteredElementCollector(doc).OfClass(FilledRegionType))
    for t in types:
        if revit.type_name(t) == name:
            return t.Id
    t = types[0].Duplicate(name)
    t.ForegroundPatternId = solid_fill_id(doc)
    t.ForegroundPatternColor = _color(rgb)
    return t.Id


# --------------------------------------------------------------------------------------
# DirectShapes
def clear(doc, tag=None):
    """Delete the TBIM DirectShapes (of ``tag`` only, if given). Return the number deleted."""
    ids = [e.Id for e in FilteredElementCollector(doc).OfClass(DirectShape)
           if e.ApplicationId == APPLICATION_ID and (tag is None or e.ApplicationDataId == tag)]
    for element_id in ids:
        doc.Delete(element_id)
    return len(ids)


def polygons(loops_cm, material_id, closed=False):
    """Geometry of planar polygons (a closed shell becomes a solid when possible)."""
    builder = TessellatedShapeBuilder()
    builder.OpenConnectedFaceSet(closed)
    for loop in loops_cm:
        points = List[XYZ]()
        for p in loop:
            xyz = _xyz(p)
            if points.Count == 0 or not xyz.IsAlmostEqualTo(points[points.Count - 1]):
                points.Add(xyz)
        if points.Count > 2 and points[0].IsAlmostEqualTo(points[points.Count - 1]):
            points.RemoveAt(points.Count - 1)
        if points.Count > 2:
            builder.AddFace(TessellatedFace(points, material_id))
    builder.CloseConnectedFaceSet()
    builder.Target = TessellatedShapeBuilderTarget.AnyGeometry
    builder.Fallback = TessellatedShapeBuilderFallback.Mesh
    builder.Build()
    return list(builder.GetBuildResult().GetGeometricalObjects())


def sphere(center_cm, radius_cm, material_id):
    c, r = _xyz(center_cm), cm_to_ft(radius_cm)
    profile = CurveLoop()
    profile.Append(Arc.Create(c + XYZ.BasisZ * r, c - XYZ.BasisZ * r, c + XYZ.BasisX * r))
    profile.Append(Line.CreateBound(c - XYZ.BasisZ * r, c + XYZ.BasisZ * r))
    loops = List[CurveLoop]()
    loops.Add(profile)
    frame = Frame(c, XYZ.BasisX, XYZ.BasisY, XYZ.BasisZ)
    return [GeometryCreationUtilities.CreateRevolvedGeometry(frame, loops, 0, 2 * math.pi,
                                                             SolidOptions(material_id, ElementId.InvalidElementId))]


def cylinder(a_cm, b_cm, radius_cm, material_id):
    a, b = _xyz(a_cm), _xyz(b_cm)
    direction = (b - a).Normalize()
    plane = Plane.CreateByNormalAndOrigin(direction, a)
    circle = CurveLoop()
    circle.Append(Arc.Create(plane, cm_to_ft(radius_cm), 0, math.pi))
    circle.Append(Arc.Create(plane, cm_to_ft(radius_cm), math.pi, 2 * math.pi))
    loops = List[CurveLoop]()
    loops.Add(circle)
    return [GeometryCreationUtilities.CreateExtrusionGeometry(loops, direction, a.DistanceTo(b),
                                                              SolidOptions(material_id, ElementId.InvalidElementId))]


def directshape(doc, geometry, tag, name):
    shape = DirectShape.CreateElement(doc, ElementId(BuiltInCategory.OST_GenericModel))
    shape.ApplicationId = APPLICATION_ID
    shape.ApplicationDataId = tag
    shapes = List[GeometryObject]()  # pythonnet does not convert python lists here
    for item in geometry:
        shapes.Add(item)
    shape.SetShape(shapes)
    shape.Name = re.sub(r"[\\:{}\[\]|;<>?`~]", "-", name)  # characters not allowed in Revit names
    revit.set_builtin(shape, BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS, name)
    return shape


def normal(loop_cm):
    """Unit normal of a planar polygon (Newell's method)."""
    n = [0.0, 0.0, 0.0]
    for p, q in zip(loop_cm, loop_cm[1:] + loop_cm[:1]):
        n[0] += (p[1] - q[1]) * (p[2] + q[2])
        n[1] += (p[2] - q[2]) * (p[0] + q[0])
        n[2] += (p[0] - q[0]) * (p[1] + q[1])
    length = math.sqrt(sum(c * c for c in n)) or 1.0
    return [c / length for c in n]


def offset(loop_cm, distance_cm):
    n = normal(loop_cm)
    return [[p[i] + n[i] * distance_cm for i in range(3)] for p in loop_cm]


# --------------------------------------------------------------------------------------
# Views and overrides
def view_family_type(doc, family):
    return [t for t in FilteredElementCollector(doc).OfClass(ViewFamilyType) if t.ViewFamily == family][0]


def view_3d(doc, name):
    """3D view 'TBIM - <name>' (created as a south-west isometric view)."""
    full = VIEW_PREFIX + name
    for v in FilteredElementCollector(doc).OfClass(View3D):
        if not v.IsTemplate and v.Name == full:
            return v
    vft = view_family_type(doc, ViewFamily.ThreeDimensional)
    view = View3D.CreateIsometric(doc, vft.Id)
    view.Name = full
    forward = XYZ(1, 2, -1.2).Normalize()
    up = forward.CrossProduct(XYZ.BasisZ).CrossProduct(forward).Normalize()
    view.SetOrientation(ViewOrientation3D(XYZ(-30, -60, 50), up, forward))
    view.DisplayStyle = DisplayStyle.ShadingWithEdges
    view.DetailLevel = ViewDetailLevel.Fine
    set_hidden(view, [BuiltInCategory.OST_Levels, BuiltInCategory.OST_Grids], True)
    return view


def show_only(doc, view, tag):
    """Show the DirectShapes of ``tag`` only in ``view`` among the 'TBIM - ' 3D views."""
    shapes = [e for e in FilteredElementCollector(doc).OfClass(DirectShape) if e.ApplicationId == APPLICATION_ID]
    for v in FilteredElementCollector(doc).OfClass(View3D):
        if v.IsTemplate or not v.Name.startswith(VIEW_PREFIX):
            continue
        hide, show = List[ElementId](), List[ElementId]()
        for e in shapes:
            if e.ApplicationDataId == tag and v.Id == view.Id:
                show.Add(e.Id)
            elif (e.ApplicationDataId == tag) != (v.Id == view.Id) and e.CanBeHidden(v):
                hide.Add(e.Id)  # other tags in this view, this tag in the other views
        if hide.Count:
            v.HideElements(hide)
        if show.Count:
            v.UnhideElements(show)


def set_hidden(view, categories, hidden):
    for bic in categories:
        category_id = ElementId(bic)
        if view.CanCategoryBeHidden(category_id):
            view.SetCategoryHidden(category_id, hidden)


def ghost(view, categories, transparency=80):
    settings = OverrideGraphicSettings()
    settings.SetSurfaceTransparency(transparency)
    settings.SetHalftone(True)
    for bic in categories:
        view.SetCategoryOverrides(ElementId(bic), settings)


def color_element(view, element_id, rgb, solid_id):
    settings = OverrideGraphicSettings()
    settings.SetSurfaceForegroundPatternId(solid_id)
    settings.SetSurfaceForegroundPatternColor(_color(rgb))
    settings.SetCutForegroundPatternId(solid_id)
    settings.SetCutForegroundPatternColor(_color(rgb))
    view.SetElementOverrides(element_id, settings)


def reset_overrides(view, elements):
    blank = OverrideGraphicSettings()
    for e in elements:
        view.SetElementOverrides(e.Id, blank)
    for bic in HOST_CATEGORIES:
        view.SetCategoryOverrides(ElementId(bic), blank)


# --------------------------------------------------------------------------------------
# Legends
def legend(doc, title, entries, note=None):
    """Drafting view 'TBIM Legend - <title>' with a colored box and a label per (label, rgb)."""
    name = LEGEND_PREFIX + title
    for view_id in [v.Id for v in FilteredElementCollector(doc).OfClass(ViewDrafting) if v.Name == name]:
        doc.Delete(view_id)  # (not while iterating the collector)
    vft = view_family_type(doc, ViewFamily.Drafting)
    view = ViewDrafting.Create(doc, vft.Id)
    view.Name = name
    view.Scale = 50
    draw_legend(doc, view, XYZ(0, 0, 0), title, entries, note)
    return view


def draw_legend(doc, view, origin, title, entries, note=None):
    """Title, note and a colored box with a label per (label, rgb) in ``view``, from ``origin`` (top left)."""
    text_type = FilteredElementCollector(doc).OfClass(TextNoteType).FirstElementId()
    m = view.Scale / 50.0 / 0.3048  # feet per metre at 1:50, scaled with the view
    TextNote.Create(doc, view.Id, origin + XYZ(0, 0.9 * m, 0), title, text_type)
    if note:
        TextNote.Create(doc, view.Id, origin + XYZ(0, 0.45 * m, 0), note, text_type)
    for i, (label, rgb) in enumerate(entries):
        y = -i * 0.6 * m
        corners = [origin + XYZ(x, y + dy, 0) for x, dy in ((0, 0), (0.8 * m, 0), (0.8 * m, -0.4 * m), (0, -0.4 * m))]
        box = CurveLoop()
        for p, q in zip(corners, corners[1:] + corners[:1]):
            box.Append(Line.CreateBound(p, q))
        loops = List[CurveLoop]()
        loops.Add(box)
        FilledRegion.Create(doc, filled_region_type(doc, rgb), view.Id, loops)
        TextNote.Create(doc, view.Id, origin + XYZ(1.0 * m, y - 0.05 * m, 0), str(label), text_type)


# --------------------------------------------------------------------------------------
# 2D maps
def view_plan(doc, name, level):
    """Floor plan 'TBIM - <name>' of ``level``, emptied of its filled regions and text notes."""
    full = VIEW_PREFIX + name
    view = next((v for v in FilteredElementCollector(doc).OfClass(ViewPlan) if not v.IsTemplate and v.Name == full),
                None)
    if view is None:
        view = ViewPlan.Create(doc, revit.floor_plan_type_id(doc), level.Id)
        view.Name = full
        view.DetailLevel = ViewDetailLevel.Fine
    owned = [e.Id for cls in (FilledRegion, TextNote) for e in FilteredElementCollector(doc, view.Id).OfClass(cls)
             if e.OwnerViewId == view.Id]
    for element_id in owned:
        doc.Delete(element_id)
    return view


def fill_space(doc, view, space, rgb):
    """Fill the boundary of ``space`` with ``rgb`` in ``view``. Return False if its boundary is not a region."""
    loops = List[CurveLoop]()
    for segments in space.GetBoundarySegments(SpatialElementBoundaryOptions()) or []:
        loop = CurveLoop()
        for segment in segments:
            loop.Append(segment.GetCurve())
        loops.Add(loop)
    if not loops.Count:
        return False
    try:
        FilledRegion.Create(doc, filled_region_type(doc, rgb), view.Id, loops)
    except Exception:  # open or self-intersecting boundary
        return False
    return True


def note_at(doc, view, point, text):
    TextNote.Create(doc, view.Id, XYZ(point.X, point.Y, 0), text,
                    FilteredElementCollector(doc).OfClass(TextNoteType).FirstElementId())


# --------------------------------------------------------------------------------------
# Graphs
def show_graph(ctx, kind, title):
    """Visualize > Dual Graph / Passage Graph: the ``kind`` graph (scene.GRAPHS) of a Topologic model in the
    3D view 'TBIM - <title>': nodes colored by thermal zone (or occupancy type), edges by kind, with a legend."""
    models = scene.available_models()
    if not models:
        revit.alert("Visualize", "No Topologic model yet: run Collectors > CellComplex > Create first.")
        return
    label = ui.select("visualize_graph_model", "%s of the model" % title, [m[0] for m in models])
    if not label:
        return
    path = dict(models)[label]
    nodes, edges = scene.graph(topo.load_cellcomplex(path), scene.apertures(path), kind)
    cells = [n for n in nodes if not n[0].startswith(scene.EXTERIOR)]
    key = next((k for k in ("rl_HasLocation_tpZN", "pr_OccupancyType") if any(k in n[2] for n in cells)), "UID")
    color_of, node_entries = colors.legend_for([n[2].get(key) for n in cells])
    points = dict((uid, point) for uid, point, _ in nodes)
    doc = ctx.doc
    with revit.transaction(doc, "TBIM - Visualize %s" % title.lower()):
        clear(doc, title)  # the DirectShapes of each graph are tagged with its title
        view = view_3d(doc, title)
        ghost(view, HOST_CATEGORIES, transparency=85)
        for uid, point, props in nodes:
            if uid.startswith(scene.EXTERIOR):
                directshape(doc, sphere(point, EXTERIOR_RADIUS_CM, material(doc, colors.EXTERIOR_COLOR)),
                            title, uid)
            else:
                directshape(doc, sphere(point, NODE_RADIUS_CM, material(doc, color_of(props.get(key)))),
                            title, "%s (%s)" % (uid, props.get(key)))
        for a, b, edge_kind in edges:
            directshape(doc, cylinder(points[a], points[b], EDGE_RADIUS_CM,
                                      material(doc, colors.GRAPH_EDGE_COLORS[edge_kind])),
                        title, "%s-%s (%s)" % (a, b, edge_kind))
        show_only(doc, view, title)
        kinds = [k for k in colors.GRAPH_EDGE_COLORS if any(e[2] == k for e in edges)]
        entries = [("Node: %s" % v, rgb) for v, rgb in node_entries]
        if len(cells) < len(nodes):
            entries.append(("Node: %s" % scene.EXTERIOR, colors.EXTERIOR_COLOR))
        entries += [("Edge: %s" % k, colors.GRAPH_EDGE_COLORS[k]) for k in kinds]
        legend(doc, title, entries, note="%s of %s - nodes by %s" % (title, label, key))
    ctx.uidoc.ActiveView = view
    counts = ", ".join("%s %d" % (k, sum(e[2] == k for e in edges)) for k in kinds) or "none"
    note = "" if edges or kind != scene.PASSAGE else "\nNo doors yet: run TopologicalBIM > By Rules first."
    revit.alert("Visualize", "%s of %s: %d nodes, %d edges (%s).\nView: '%s'.%s" % (
        title, label, len(nodes), len(edges), counts, view.Name, note))


def delete_all(doc, tag=None, title=""):
    """Delete the TBIM visualizations: DirectShapes (of ``tag`` only, if given), 'TBIM - ' views and legends
    (whose title starts with ``title``)."""
    count = clear(doc, tag)
    views = [v.Id for cls in (View3D, ViewPlan) for v in FilteredElementCollector(doc).OfClass(cls)
             if not v.IsTemplate and v.Name.startswith(VIEW_PREFIX + title)]
    views += [v.Id for v in FilteredElementCollector(doc).OfClass(ViewDrafting)
              if v.Name.startswith(LEGEND_PREFIX + title)]
    for view_id in views:
        doc.Delete(view_id)
    return count, len(views)
