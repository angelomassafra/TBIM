"""Informational Loads: enrich the CellComplex of the Informational Controllers (CPython only).

Steps (shared by the Loads > Update and Loads > Clusterize commands):

1. assign to each cell the ILD of its occupancy type (``Default`` if unknown);
2. type and identify faces (``pr_TopologicalType``, ``UID``);
3. propagate cell properties to faces: external faces take the value of their
   cell, internal faces the sorted '-' joined values of the adjacent cells
   (the cell ``UID`` becomes ``rl_HasLocation_tpSP``);
4. face area and exposure, cell main exposure;
5. optionally, thermal zoning (``rl_HasLocation_tpZN``).
"""
from topologicpy.CellComplex import CellComplex
from topologicpy.Face import Face

from tbim import analysis, ild, topo, zoning
from tbim.units import cm2_to_m2

RELATIONSHIP_KEYS = ["rl_HasLocation_tpBS", "rl_HasLocation_tpBB"]
LEGACY_KEYS = {"HasLocation_tpBB": "rl_HasLocation_tpBB"}
VERTICAL_TYPES = ("intVer", "extVer")


def _value(v):
    return "None" if v is None else v


def assign_ilds(cc, ilds, assignments):
    """Assign occupancy type and ILD properties to every cell."""
    for cell in CellComplex.Cells(cc):
        props = topo.props(cell)
        for old, new in LEGACY_KEYS.items():
            if old in props and new not in props:
                props[new] = props.pop(old)
        requested = assignments.get(props.get("UID"), props.get(ild.OCCUPANCY_KEY))
        occupancy, number, values = ild.resolve(ilds, requested)
        props.update(dict((k, v) for k, v in values.items() if k != ild.OCCUPANCY_KEY))
        props[ild.OCCUPANCY_KEY] = occupancy
        props["pr_OccupancyType_Number"] = number
        topo.replace(cell, props)


def propagate_to_faces(cc, groups, keys):
    """Copy cell properties (and relationships) to the faces."""
    for face_type, faces in groups:
        for face in faces:
            cells = topo.adjacent_cells(face, cc)
            if not cells:
                continue
            cell_props = [topo.props(c) for c in cells]
            face_props = topo.props(face)
            if any(k in face_props for k in LEGACY_KEYS):
                topo.replace(face, dict((k, v) for k, v in face_props.items() if k not in LEGACY_KEYS))
            values = {}
            for key in keys:
                target = "rl_HasLocation_tpSP" if key == "UID" else key
                values[target] = analysis.join_values(_value(p.get(key)) for p in cell_props)
            for key in RELATIONSHIP_KEYS:
                values[key] = analysis.join_unique(_value(p.get(key)) for p in cell_props)
            values["pr_Area"] = round(cm2_to_m2(Face.Area(face)), 2)  # m2, like the cells
            topo.update(face, values)


def assign_exposures(cc, groups, north_angle):
    north = analysis.rotate_z(north_angle)
    per_cell = {}
    for face_type, faces in groups:
        if face_type not in VERTICAL_TYPES:
            continue
        for face in faces:
            cells = topo.adjacent_cells(face, cc)
            if face_type == "extVer" and cells:
                normal = topo.outward_normal(face, cells[0])
            else:
                normal = Face.Normal(face)
            exposure = analysis.exposure(normal, north)
            topo.update(face, {"pr_FaceExposure": exposure})
            if face_type == "extVer" and cells:
                per_cell.setdefault(topo.cell_uid(cells[0]), []).append((exposure, Face.Area(face)))
    for cell in CellComplex.Cells(cc):
        items = per_cell.get(topo.cell_uid(cell), [])
        main = analysis.dominant([e for e, _ in items], [a for _, a in items])
        topo.update(cell, {"pr_MainExposure": main or "None",
                           "pr_NumberOfExposures": len(set(e for e, _ in items))})


def lateral_adjacency(cc, groups):
    """{cell UID: set of the UIDs of the cells sharing an internal vertical face}."""
    lateral = {}
    for face_type, faces in groups:
        if face_type != "intVer":
            continue
        for face in faces:
            uids = [topo.cell_uid(c) for c in topo.adjacent_cells(face, cc)]
            for a in uids:
                for b in uids:
                    if a != b:
                        lateral.setdefault(a, set()).add(b)
    return lateral


def assign_zones(cc, groups):
    cells = CellComplex.Cells(cc)
    lateral = lateral_adjacency(cc, groups)
    cell_props = [(topo.cell_uid(c), topo.props(c)) for c in cells]
    clusters = zoning.zones(cell_props, lateral)
    for cell in cells:
        props = topo.props(cell)
        cluster = clusters.get(props.get("UID"), "ZoneCluster")
        zone = "%s_BS%s" % (cluster.replace("ZoneCluster", "Zone"),
                            analysis.storey_suffix(props.get("rl_HasLocation_tpBS")))
        topo.update(cell, {"rl_HasLocation_tpZN": zone})
    for _, faces in groups:
        for face in faces:
            zones = [topo.get(c, "rl_HasLocation_tpZN") for c in topo.adjacent_cells(face, cc)]
            if zones:
                topo.update(face, {"rl_HasLocation_tpZN": analysis.join_values(zones)})


def run(cc, ilds, assignments, north_angle=0.0, clusterize=False):
    """Run the Informational Loads pipeline in place. Return the face property names."""
    assign_ilds(cc, ilds, assignments)
    groups = topo.assign_face_types(cc)
    keys = ["UID", ild.OCCUPANCY_KEY] + [k for k in ild.load_keys(ilds) if k != ild.OCCUPANCY_KEY]
    propagate_to_faces(cc, groups, keys)
    assign_exposures(cc, groups, north_angle)
    if clusterize:
        assign_zones(cc, groups)
    return sorted(set(k for _, faces in groups for f in faces for k in topo.props(f)))
