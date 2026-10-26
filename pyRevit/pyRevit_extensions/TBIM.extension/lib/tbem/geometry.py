"""Honeybee rooms of the thermal zones from the TBIM CellComplex (CPython only).

Every face of the CellComplex is classified by the zones of its cells:

    EXTERNAL     one cell, in a zone: a face of the zone envelope;
    INTERZONE    two cells in two zones: one face per zone, the two adjacent to each other;
    EXCLUDED     two cells, one left out of the model: a face of the zone towards an unmodelled space;
    (two cells of the same zone: inside the zone, not modelled.)

A Honeybee face per zone side, oriented outwards of its cell (topology, not vertex order), in metres. The
level of detail sets how faces become Honeybee faces:

    Spatial BEM      face types by Honeybee (from the normals), boundary conditions by geometry: outdoors, ground
                     for the lowest floors, adjacencies solved by matching the room faces; no apertures;
    Topological BEM  face types and boundary conditions by the topology (pr_TopologicalType, settings),
                     adjacencies from the shared faces; windows and external doors of the TopologicalBIM,
                     glazed walls (layers with glazing) as windows by ratio;
    Full TBEM        as the Topological BEM (constructions are added by ``model``).
"""
from honeybee.aperture import Aperture
from honeybee.boundarycondition import Outdoors
from honeybee.boundarycondition import boundary_conditions as bcs
from honeybee.door import Door
from honeybee.face import Face
from honeybee.facetype import face_types
from honeybee.room import Room
from honeybee.shade import Shade
from honeybee.typing import clean_ep_string
from ladybug_geometry.geometry3d import Face3D, Point3D, Vector3D
from topologicpy.CellComplex import CellComplex
from topologicpy.Face import Face as TopologicFace
from topologicpy.Topology import Topology
from topologicpy.Vertex import Vertex

from tbem import constructions
from tbem.files import FULL, SPATIAL, TOPOLOGICAL
from tbim import topo

CM = 0.01  # TBIM models are in centimetres
TOLERANCE, ANGLE_TOLERANCE = 0.01, 1.0
SUBFACE_SHRINK = 0.98  # apertures touching the boundary of their face (doors at floor level)
EXTERNAL, INTERZONE, EXCLUDED = "external", "interzone", "excluded"
FACE_TYPES = {"extVer": face_types.wall, "intVer": face_types.wall, "botHor": face_types.floor,
              "topHor": face_types.roof_ceiling, "extInc": face_types.roof_ceiling}
WINDOW_HOSTS = ("extVer", "extInc")
SKYLIGHT_HOSTS = ("topHor",)


def _points(coordinates):
    return [Point3D(*(c * CM for c in xyz)) for xyz in coordinates]


def _loop(wire):
    return _points([Vertex.Coordinates(v) for v in Topology.Vertices(wire)])


def face3d(face):
    """Face3D (m) of a Topologic face, with its holes; colinear vertices (left by the adjacent faces) removed."""
    holes = [_loop(w) for w in (TopologicFace.InternalBoundaries(face) or [])]
    geometry = Face3D(_loop(TopologicFace.ExternalBoundary(face)), holes=holes or None)
    try:
        return geometry.remove_colinear_vertices(TOLERANCE)
    except AssertionError:
        return geometry


def oriented(geometry, normal):
    """``geometry`` flipped if needed to face the ``normal`` direction."""
    return geometry.flip() if geometry.normal.dot(Vector3D(*normal)) < 0 else geometry


def sides(cc, zone_of):
    """[side] of the zone envelopes. A side: {'face', 'props', 'cell' (its cell), 'zone', 'other' (the other zone),
    'kind', 'index' (0 or 1: which of the two cells), 'below' (the face is under the cell)}."""
    out = []
    for face in CellComplex.Faces(cc):
        cells = topo.adjacent_cells(face, cc)
        zones = [zone_of.get(topo.cell_uid(c)) for c in cells]
        props = topo.props(face)
        if len(cells) == 1:
            candidates = [(0, EXTERNAL, None)] if zones[0] else []
        elif len(cells) == 2 and zones[0] != zones[1]:
            kind = INTERZONE if zones[0] and zones[1] else EXCLUDED
            candidates = [(i, kind, zones[1 - i]) for i in (0, 1) if zones[i]]
        else:
            candidates = []
        face_z = Vertex.Z(Topology.Centroid(face))
        for index, kind, other in candidates:
            out.append({"face": face, "props": props, "cell": cells[index], "zone": zones[index], "other": other,
                        "kind": kind, "index": index,
                        "below": face_z < Vertex.Z(topo.interior_point(cells[index])) - 1})
    return out


def face_id(side):
    return clean_ep_string("%s-%s" % (side["props"].get("UID") or "Face", side["zone"]))


def reversed_layers(side):
    """True if the layers of the face (outside/top first) run from the inside of this side's zone."""
    face_type = side["props"].get("pr_TopologicalType")
    if face_type in ("botHor", "intHor"):
        return side["below"]  # the face is the floor of the zone
    if face_type in ("intVer", "intInc"):
        return side["index"] == 1
    return False


def boundary(side, settings, lowest_z):
    """Boundary condition of a side (None: adjacent to another zone, set afterwards)."""
    options = settings["boundary_conditions"]
    uid, face_type = side["props"].get("UID"), side["props"].get("pr_TopologicalType")
    if side["kind"] == INTERZONE:
        return None
    if side["kind"] == EXCLUDED:
        return bcs.adiabatic if options["excluded_neighbour"] == "Adiabatic" else bcs.outdoors
    if uid in options["adiabatic_face_uids"]:
        return bcs.adiabatic
    if uid in options["ground_face_uids"]:
        return bcs.ground
    if uid in options["outdoors_face_uids"]:
        return bcs.outdoors
    if lowest_z is not None:  # Spatial BEM: ground if the face is a lowest floor
        zs = [Vertex.Z(v) for v in Topology.Vertices(side["face"])]
        return bcs.ground if side["below"] and max(zs) <= lowest_z + 1 else bcs.outdoors
    return bcs.ground if face_type in options["ground_face_types"] else bcs.outdoors


def honeybee_face(side, settings, level, lowest_z):
    geometry = oriented(face3d(side["face"]), topo.outward_normal(side["face"], side["cell"]))
    face_type = None
    if level != SPATIAL:
        face_type = FACE_TYPES.get(side["props"].get("pr_TopologicalType"))
        if side["props"].get("pr_TopologicalType") == "intHor":
            face_type = face_types.floor if side["below"] else face_types.roof_ceiling
    face = Face(face_id(side), geometry, face_type)
    bc = boundary(side, settings, lowest_z if level == SPATIAL else None)
    if bc is not None:
        face.boundary_condition = bc
    return face


def add_openings(face, side, openings, settings, problems):
    """Windows, external doors and glazed walls of an outdoor face. Return [(sub-face, aperture props)]."""
    face_type = side["props"].get("pr_TopologicalType")
    options = settings["apertures"]
    hosts = WINDOW_HOSTS + (SKYLIGHT_HOSTS if options["skylights"] else ())
    if not isinstance(face.boundary_condition, Outdoors) or face_type not in hosts:
        return []
    if constructions.is_glazed(side["props"]):
        face.apertures_by_ratio(options["glazed_wall_ratio"], TOLERANCE)
        for aperture in face.apertures:
            aperture.identifier = clean_ep_string("Glazing-%s" % face.identifier)
        year = side["props"].get("stFC_ConstructionYear")
        return [(a, {"pr_ConstructionYear": year}) for a in face.apertures]
    added = []
    for props, coordinates in openings.get(side["props"].get("UID"), []):
        kind = props.get("pr_TopologicalType")
        if kind == "door" and not options["external_doors"] or kind not in ("window", "door"):
            continue
        geometry = oriented(Face3D(_points(coordinates)), face.normal)
        if not face.geometry.is_sub_face(geometry, TOLERANCE, ANGLE_TOLERANCE):
            geometry = geometry.scale(SUBFACE_SHRINK, geometry.center)  # e.g. doors on the edge of the wall
        if not face.geometry.is_sub_face(geometry, TOLERANCE, ANGLE_TOLERANCE):
            problems.append("%s %s is not inside its face %s: skipped" % (kind, props.get("UID"), face.identifier))
            continue
        identifier = clean_ep_string(props.get("UID") or "Aperture")
        if kind == "window":
            sub = Aperture(identifier, geometry)
            face.add_aperture(sub)
        else:
            sub = Door(identifier, geometry)
            face.add_door(sub)
        added.append((sub, props))
    return added


def rooms(cc, zone_of, level, settings, aperture_polygons=()):
    """Honeybee rooms of the zones. Return (rooms, {face id: side}, {sub-face id: (aperture props, side)}, problems)."""
    openings = {}
    if level != SPATIAL:
        for props, coordinates in aperture_polygons:
            openings.setdefault(props.get("rl_HasLocation_inFC"), []).append((props, coordinates))
    lowest_z = min(Vertex.Z(v) for v in Topology.Vertices(cc))
    by_zone, faces_by_id, subfaces, problems = {}, {}, {}, []
    for side in sides(cc, zone_of):
        face = honeybee_face(side, settings, level, lowest_z)
        if face.identifier in faces_by_id:
            problems.append("Two faces named %s: the second is skipped" % face.identifier)
            continue
        faces_by_id[face.identifier] = side
        for sub, props in (add_openings(face, side, openings, settings, problems) if level != SPATIAL else []):
            subfaces[sub.identifier] = (props, side)
        by_zone.setdefault(side["zone"], []).append(face)
    result = []
    for zone in sorted(by_zone):
        room = Room(clean_ep_string(zone), by_zone[zone], TOLERANCE, ANGLE_TOLERANCE)
        room.story = topo.get(next(s["cell"] for s in faces_by_id.values() if s["zone"] == zone),
                              "rl_HasLocation_tpBS")
        if room.check_solid(TOLERANCE, ANGLE_TOLERANCE, False):
            problems.append("Zone %s is not a closed volume" % zone)
        result.append(room)
    if level == SPATIAL:
        Room.solve_adjacency(result, TOLERANCE)
    else:
        _pair_adjacent_faces(result, faces_by_id)
    return result, faces_by_id, subfaces, problems


def _pair_adjacent_faces(room_list, faces_by_id):
    """Set the inter-zone boundary conditions from the faces shared in the CellComplex."""
    hb_faces = dict((f.identifier, f) for r in room_list for f in r.faces)
    for identifier, side in faces_by_id.items():
        if side["kind"] != INTERZONE:
            continue
        other = clean_ep_string("%s-%s" % (side["props"].get("UID") or "Face", side["other"]))
        if identifier < other and other in hb_faces:
            hb_faces[identifier].set_adjacency(hb_faces[other])


def shades(brep_paths):
    """Detached Honeybee shades of the faces of BRep files (cm)."""
    out = []
    for i, path in enumerate(brep_paths):
        topology = Topology.ByBREPPath(path)
        for j, face in enumerate(Topology.Faces(topology) or []):
            out.append(Shade(clean_ep_string("Shade%d-%d" % (i, j)), face3d(face), is_detached=True))
    return out


__all__ = ["SPATIAL", "TOPOLOGICAL", "FULL", "rooms", "shades", "sides", "reversed_layers"]
