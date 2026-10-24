"""TopologicalBIM by rules: windows and doors on the styled CellComplex (CPython only, no Revit).

The rules (``json/tbim_TopologicalBIM_Rules.json``) give the aperture types by occupancy type::

    {"windows":        [[occupancy contains, type, width, height, sill], ...],   on external vertical faces
     "external_doors": [[occupancy contains, type, width, height], ...],         one per cell, entrance levels only
     "doors":          [[occupancy A contains, occupancy B contains, type, width, height], ...],
     "entrance_levels": [0],                                                      z (cm) of the external doors
     "window_data": {...}, "door_data": {...}}                                     extra aperture properties

The first matching rule wins; a rule whose type is null places nothing (exceptions before general rules,
e.g. ``["Circulation", null]`` then ``["", "TBIM_Window_120x150", 120, 150, 90]``). An empty occupancy
matches every cell. Internal doors connect each pair of cells once. Sizes in centimetres.
"""
import math

from topologicpy.Face import Face
from topologicpy.Topology import Topology
from topologicpy.Vertex import Vertex

from tbim import topo

KINDS = ("window", "door")
DEFAULT_MARGINS = {"window": 60, "external_door": 40, "door": 20}


def opening(face, width, height, sill, margin):
    """Rectangle centred on the bottom edge of a vertical face.

    Return (face, (x, y, z of the bottom centre of the host face), (ux, uy) along the face) or (None, None, None).
    """
    pts = [Vertex.Coordinates(v) for v in Topology.Vertices(Face.ExternalBoundary(face))]
    zmin, zmax = min(p[2] for p in pts), max(p[2] for p in pts)
    bottom = [p for p in pts if abs(p[2] - zmin) < 1e-3]
    if len(bottom) < 2 or zmax - zmin < sill + height + 20:
        return None, None, None
    a, b = min(bottom), max(bottom)
    length = math.hypot(b[0] - a[0], b[1] - a[1])
    if length < width + margin:
        return None, None, None
    u = ((b[0] - a[0]) / length, (b[1] - a[1]) / length)
    cx, cy = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
    z0, z1 = zmin + sill, zmin + sill + height
    (x0, y0), (x1, y1) = [(cx + s * u[0] * width / 2, cy + s * u[1] * width / 2) for s in (-1, 1)]
    vertices = [Vertex.ByCoordinates(x, y, z) for x, y, z in ((x0, y0, z0), (x1, y1, z0), (x1, y1, z1), (x0, y0, z1))]
    return Face.ByVertices(vertices), (cx, cy, zmin), u


def first(rules, occupancy):
    """First rule whose occupancy pattern is in ``occupancy`` (None if none, or if its type is null)."""
    rule = next((r for r in rules if r[0] in (occupancy or "")), None)
    return rule if rule is not None and rule[1] is not None else None


def door_rule(rules, occupancies):
    """First rule matching the occupancies of the two cells of an internal face, in any order."""
    if len(occupancies) != 2:
        return None
    a, b = occupancies
    rule = next((r for r in rules if (r[0] in a and r[1] in b) or (r[0] in b and r[1] in a)), None)
    return rule if rule is not None and rule[2] is not None else None


def place(cc, rules):
    """Add the apertures of ``rules`` to ``cc``. Return (CellComplex with apertures, placements).

    placements: [{"UID", "kind", "type", "width", "height", "sill", "host", "point", "direction"}], with
    ``point`` the bottom centre of the host face (cm) and ``direction`` the unit vector along it.
    """
    windows, external_doors, doors = (rules.get(k, []) for k in ("windows", "external_doors", "doors"))
    levels = rules.get("entrance_levels", [0])
    records, placements, counters = [], [], dict((k, 0) for k in KINDS)
    entrance_cells, connected = set(), set()
    for face_type, faces in topo.face_groups(cc):
        if face_type not in ("extVer", "intVer"):
            continue
        for face in faces:
            props = topo.props(face)
            cells = topo.adjacent_cells(face, cc)
            occupancies = [topo.get(c, "pr_OccupancyType", "") for c in cells]
            uids = tuple(sorted(topo.cell_uid(c) for c in cells))
            if face_type == "extVer":
                if not cells:
                    continue
                at_entrance = any(abs(topo.z_range(face)[0] - z) < 1.0 for z in levels)
                door = first(external_doors, occupancies[0]) if at_entrance else None
                if door and uids[0] not in entrance_cells:
                    _, type_name, w, h = door[:4]
                    sill, kind, margin = 0, "door", DEFAULT_MARGINS["external_door"]
                else:
                    window = first(windows, occupancies[0])
                    if window is None:
                        continue
                    _, type_name, w, h, sill = window[:5]
                    kind, margin = "window", DEFAULT_MARGINS["window"]
            else:
                door = door_rule(doors, occupancies)
                if door is None or uids in connected:
                    continue
                _, _, type_name, w, h = door[:5]
                sill, kind, margin = 0, "door", DEFAULT_MARGINS["door"]
            aperture, point, direction = opening(face, w, h, sill, margin)
            if aperture is None:
                continue
            if kind == "door":
                if face_type == "extVer":
                    entrance_cells.add(uids[0])
                else:
                    connected.add(uids)
            uid = "%s%d" % (kind, counters[kind])
            counters[kind] += 1
            data = dict(rules.get(kind + "_data", {}), UID=uid, pr_TopologicalType=kind, pr_Width=w, pr_Height=h,
                        pr_SillHeight=sill, stAP_TypeName=type_name, rl_HasLocation_inFC=props["UID"])
            topo.replace(aperture, data)
            records.append(aperture)
            placements.append({"UID": uid, "kind": kind, "type": type_name, "width": w, "height": h, "sill": sill,
                               "host": props["UID"], "point": [round(c, 1) for c in point],
                               "direction": [round(c, 6) for c in direction]})
    if records:
        cc = Topology.AddApertures(cc, records, subTopologyType="face")
    return cc, placements


def locations(placements):
    """Records of tbim_CellComplex_TBIM_AperturesLocation.json (Revit insertion points, cm)."""
    return [{"UID": p["UID"], "Location": {"Revit": dict(zip("XYZ", [int(p["point"][0]), int(p["point"][1]),
                                                                      int(p["point"][2] + p["sill"])]))}}
            for p in placements]
