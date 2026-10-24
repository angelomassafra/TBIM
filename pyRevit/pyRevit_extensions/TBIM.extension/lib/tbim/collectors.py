"""Informational Controllers: CellComplex from BReps and its Revit counterpart (CPython only).

Each BRep is a building block; the merged CellComplex is translated into
building storeys (levels), room-bounding walls, floors, roofs and spaces
(one per cell); walls, floors and roofs carry the UID of their face.
"""
import math

from Autodesk.Revit.DB import (  # noqa: E402
    UV,
    XYZ,
    AreaVolumeSettings,
    BuiltInParameter,
    Curve,
    CurveArray,
    CurveLoop,
    ElementLevelFilter,
    FilteredElementCollector,
    Floor,
    FloorType,
    Level,
    Line,
    ModelCurveArray,
    RoofType,
    View,
    Wall,
)
from System.Collections.Generic import List  # noqa: E402
from topologicpy.CellComplex import CellComplex
from topologicpy.Face import Face
from topologicpy.Topology import Topology
from topologicpy.Vertex import Vertex

from tbim import revit, topo
from tbim.controllers import build_cellcomplex, storey_elevations, storey_name
from tbim.units import cm_to_ft

SPACE_PARAMETERS = ["UID", "pr_OccupancyType", "rl_HasLocation_tpBB", "rl_HasLocation_tpBS"]
FACE_PARAMETERS = ["UID", "pr_TopologicalType", "rl_HasLocation_tpBS"]
MIN_WALL_LENGTH_CM = 20.0
WALL_TYPE_NAME = "Default"


def _xyz(vertex):
    return XYZ(cm_to_ft(Vertex.X(vertex)), cm_to_ft(Vertex.Y(vertex)), cm_to_ft(Vertex.Z(vertex)))


def _horizontal_extent(face):
    pts = [Vertex.Coordinates(v) for v in Topology.Vertices(face)]
    return max(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 for a in pts for b in pts)


# --------------------------------------------------------------------------------------
# Revit
def create_levels(doc, elevations_cm):
    existing = revit.levels(doc)
    created = []
    with revit.transaction(doc, "Create building storeys"):
        for z in elevations_cm:
            ft = cm_to_ft(z)
            same = [lv for lv in existing + created if abs(lv.Elevation - ft) < 1e-4]
            if same:
                # TBIM relies on the storey names (e.g. rules on '_0cm'): rename existing levels
                if same[0].Name != storey_name(z):
                    try:
                        same[0].Name = storey_name(z)
                    except Exception:
                        pass
                continue
            level = Level.Create(doc, ft)
            try:
                level.Name = storey_name(z)
            except Exception:
                pass  # name already used: keep Revit's name
            created.append(level)
    return created


def delete_unused_levels(doc, elevations_cm):
    """Delete the levels that are not building storeys and host no element (e.g. the template's 'Level 1')."""
    storeys = [cm_to_ft(z) for z in elevations_cm]
    deleted = []
    with revit.transaction(doc, "Delete unused levels"):
        for level in revit.levels(doc):
            if any(abs(level.Elevation - ft) < 1e-4 for ft in storeys):
                continue
            hosted = [e for e in FilteredElementCollector(doc).WherePasses(ElementLevelFilter(level.Id))
                      .WhereElementIsNotElementType() if not isinstance(e, View)]
            if not hosted:
                deleted.append(level.Name)
                doc.Delete(level.Id)
    return deleted


def create_walls(doc, faces, level_list, wall_type_id, cc=None):
    """Room-bounding walls following the profile of vertical faces. Return (created, failed).

    With ``cc``, the exterior side of the walls on external faces faces away from the building
    (Wall.Create picks it from the direction of the profile), so layered types are not inside out.
    """
    created, failed, to_orient = 0, [], []
    tolerance = doc.Application.ShortCurveTolerance
    with revit.transaction(doc, "Create walls"):
        for face in faces:
            if _horizontal_extent(face) < MIN_WALL_LENGTH_CM:
                continue
            profile = List[Curve]()
            for edge in Topology.Edges(Face.ExternalBoundary(face)):
                start, end = [_xyz(v) for v in Topology.Vertices(edge)]
                if start.DistanceTo(end) > tolerance:
                    profile.Add(Line.CreateBound(start, end))
            zmin, _ = topo.z_range(face)
            base = revit.nearest_level(level_list, cm_to_ft(zmin))
            wall = None
            try:
                wall = Wall.Create(doc, profile, wall_type_id, base.Id, False)
                # the face UID lets Loads, Styles and InstanceBIM update the wall
                props = topo.props(face)
                revit.set_by_name(wall, "UID", props["UID"])
                revit.set_by_name(wall, "pr_TopologicalType", props["pr_TopologicalType"])
                revit.set_by_name(wall, "rl_HasLocation_tpBS", base.Name)
                external = cc is not None and props.get("pr_TopologicalType") == "extVer"
                cells = topo.adjacent_cells(face, cc) if external else []
                if cells:
                    to_orient.append((wall, topo.outward_normal(face, cells[0])))
                created += 1
            except Exception as e:
                failed.append("%s: %s" % (topo.get(face, "UID", "face"), e))
                if wall is not None and wall.IsValidObject:
                    doc.Delete(wall.Id)
        # Wall.Orientation needs the wall geometry: regenerate once, then flip
        doc.Regenerate()
        for wall, outward in to_orient:
            try:
                if wall.Orientation.DotProduct(XYZ(outward[0], outward[1], outward[2])) < 0:
                    wall.Flip()
            except Exception as e:
                failed.append("%s (orientation): %s" % (revit.uid(wall), e))
    return created, failed


def _boundary_loop(face, tolerance):
    points = [_xyz(v) for v in Topology.Vertices(Face.ExternalBoundary(face))]
    loop = CurveLoop()
    for start, end in zip(points, points[1:] + points[:1]):
        if start.DistanceTo(end) > tolerance:
            loop.Append(Line.CreateBound(start, end))
    return loop


def _footprint_roof(doc, footprint, level, roof_type):
    result = doc.Create.NewFootPrintRoof(footprint, level, roof_type, ModelCurveArray())
    # pythonnet returns the out argument too: (roof, model curves)
    return result if isinstance(result, tuple) else (result, None)


def _pitched_roof(doc, face, level, roof_type, tolerance):
    """Roof pitch of an inclined face: footprint roof whose eave edges only define the slope.

    The plane through the eave with the slope of the face contains the whole face, so
    one roof per face reproduces hipped and gabled roofs face by face (one UID each).
    """
    points = [Vertex.Coordinates(v) for v in Topology.Vertices(Face.ExternalBoundary(face))]
    zmin = min(p[2] for p in points)
    footprint, eaves = CurveArray(), []
    for p, q in zip(points, points[1:] + points[:1]):
        start = XYZ(cm_to_ft(p[0]), cm_to_ft(p[1]), level.Elevation)
        end = XYZ(cm_to_ft(q[0]), cm_to_ft(q[1]), level.Elevation)
        if start.DistanceTo(end) > tolerance:
            footprint.Append(Line.CreateBound(start, end))
            eaves.append(abs(p[2] - zmin) < 0.5 and abs(q[2] - zmin) < 0.5)
    roof, curves = _footprint_roof(doc, footprint, level, roof_type)
    normal = Face.Normal(face)
    slope = math.hypot(normal[0], normal[1]) / abs(normal[2])  # rise / run
    for curve, eave in zip(curves, eaves):
        roof.set_DefinesSlope(curve, eave)
        if eave:
            roof.set_SlopeAngle(curve, slope)
    revit.set_builtin(roof, BuiltInParameter.ROOF_LEVEL_OFFSET_PARAM, cm_to_ft(zmin) - level.Elevation)
    return roof


def create_floors_and_roofs(doc, groups, level_list):
    """Floors on botHor/intHor faces, roofs on topHor and inclined faces, tagged with the face UID.

    Return ({'Floors': n, 'Roofs': n}, failed).
    """
    # layered types only: e.g. 'Sloped Glazing' roofs have no structure and are transparent
    floor_type = next(t for t in FilteredElementCollector(doc).OfClass(FloorType)
                      if not t.IsFoundationSlab and t.GetCompoundStructure() is not None)
    roof_type = next(t for t in FilteredElementCollector(doc).OfClass(RoofType) if t.GetCompoundStructure() is not None)
    tolerance = doc.Application.ShortCurveTolerance
    counts, failed = {"Floors": 0, "Roofs": 0}, []
    with revit.transaction(doc, "Create floors and roofs"):
        for face_type in ("botHor", "intHor", "topHor", "extInc"):
            for face in groups.get(face_type, []):
                zmin, _ = topo.z_range(face)
                level = revit.nearest_level(level_list, cm_to_ft(zmin))
                loop = _boundary_loop(face, tolerance)
                try:
                    if face_type == "extInc":
                        element = _pitched_roof(doc, face, level, roof_type, tolerance)
                        counts["Roofs"] += 1
                    elif face_type == "topHor":
                        footprint = CurveArray()
                        for curve in loop:
                            footprint.Append(curve)
                        element = _footprint_roof(doc, footprint, level, roof_type)[0]
                        counts["Roofs"] += 1
                    else:
                        loops = List[CurveLoop]()
                        loops.Add(loop)
                        element = Floor.Create(doc, loops, floor_type.Id, level.Id)
                        counts["Floors"] += 1
                except Exception as e:
                    failed.append("%s: %s" % (topo.get(face, "UID", "face"), e))
                    continue
                props = topo.props(face)
                revit.set_by_name(element, "UID", props["UID"])
                revit.set_by_name(element, "pr_TopologicalType", props["pr_TopologicalType"])
                revit.set_by_name(element, "rl_HasLocation_tpBS", level.Name)
    return counts, failed


def create_spaces(doc, cc, level_list):
    """One space per cell, bounded by the storeys containing the cell."""
    count = 0
    with revit.transaction(doc, "Create spaces"):
        AreaVolumeSettings.GetAreaVolumeSettings(doc).ComputeVolumes = True  # needed by InstanceBIM > ByModel
        doc.Regenerate()
        for cell in CellComplex.Cells(cc):
            zmin, zmax = [cm_to_ft(z) for z in topo.z_range(cell)]
            base = revit.nearest_level(level_list, zmin)
            above = [lv for lv in level_list if lv.Elevation > base.Elevation + 1e-4]
            upper = revit.nearest_level(above, zmax) if above else base
            point = topo.interior_point(cell)
            space = doc.Create.NewSpace(base, UV(cm_to_ft(Vertex.X(point)), cm_to_ft(Vertex.Y(point))))
            revit.set_builtin(space, BuiltInParameter.ROOM_UPPER_LEVEL, upper.Id)
            revit.set_builtin(space, BuiltInParameter.ROOM_UPPER_OFFSET, zmax - upper.Elevation)
            topo.update(cell, {"rl_HasLocation_tpBS": base.Name})
            props = topo.props(cell)
            revit.set_by_name(space, "UID", props["UID"])
            revit.set_by_name(space, "pr_OccupancyType", "Default")
            revit.set_by_name(space, "rl_HasLocation_tpBS", base.Name)
            revit.set_by_name(space, "rl_HasLocation_tpBB", props.get("rl_HasLocation_tpBB"))
            count += 1
    return count


def run(ctx, brep_paths):
    """Create the Informational Controllers. Return (CellComplex, report lines)."""
    doc = ctx.doc
    cc = build_cellcomplex(brep_paths)
    revit.ensure_parameters(ctx, SPACE_PARAMETERS, "Cell", revit.SPACE_CATEGORIES)
    revit.ensure_parameters(ctx, FACE_PARAMETERS, "Face", revit.FACE_CATEGORIES)
    elevations = storey_elevations(cc)
    new_levels = create_levels(doc, elevations)
    deleted_levels = delete_unused_levels(doc, elevations)
    level_list = revit.levels(doc)
    groups = dict(topo.assign_face_types(cc))
    wall_type_id = revit.wall_type_id(doc, WALL_TYPE_NAME)
    walls, failed = create_walls(doc, groups["extVer"] + groups["intVer"], level_list, wall_type_id, cc)
    horizontals, failed_horizontals = create_floors_and_roofs(doc, groups, level_list)
    failed += failed_horizontals
    n_spaces = create_spaces(doc, cc, level_list)
    revit.create_floor_plans(doc, new_levels)
    report = ["Cells: %d" % len(CellComplex.Cells(cc)), "New building storeys: %d" % len(new_levels),
              "Walls: %d" % walls, "Floors: %d" % horizontals["Floors"], "Roofs: %d" % horizontals["Roofs"],
              "Spaces: %d" % n_spaces]
    if deleted_levels:
        report.append("Unused levels deleted: %s" % ", ".join(deleted_levels))
    if failed:
        report.append("Elements not created: %d (see output)" % len(failed))
        for line in failed:
            print(line)
    return cc, report

