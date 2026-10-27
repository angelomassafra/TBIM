"""topologicpy helpers (CPython only)."""
import os

from topologicpy.Cell import Cell
from topologicpy.CellComplex import CellComplex
from topologicpy.Dictionary import Dictionary
from topologicpy.Face import Face
from topologicpy.Topology import Topology
from topologicpy.Vertex import Vertex

from tbim.jsonio import read_json
from tbim.tbimjson import INTERNAL_KEYS, aperture_uid, clean

# (face topological type, CellComplex.Decompose key)
FACE_GROUPS = [
    ("intVer", "internalVerticalFaces"),
    ("extVer", "externalVerticalFaces"),
    ("topHor", "topHorizontalFaces"),
    ("botHor", "bottomHorizontalFaces"),
    ("intHor", "internalHorizontalFaces"),
    ("extInc", "externalInclinedFaces"),
    ("intInc", "internalInclinedFaces"),
]
EXTERNAL_TYPES = ("extVer", "topHor", "botHor", "extInc")


# --------------------------------------------------------------------------------------
# topologicpy compatibility
def _by_cells_with_face_fallback():
    """Since topologicpy 0.9.87 ``CellComplex.ByCells`` returns None when the native constructor fails, while
    0.9.86 assembled the faces of the cells instead. The topologic_core backend (8.0.4) raises on the
    CellComplexes of the TBIM projects (cells sharing walls and slabs) that ``CellComplex.ByFaces`` assembles;
    the pythonocc backend builds them. The fallback is restored for every caller, whatever the backend,
    ``Topology.ByJSONDictionary`` (load_cellcomplex) included."""
    native = CellComplex.ByCells
    if getattr(native, "tbim_fallback", False):
        return

    def by_cells(cells, transferDictionaries=False, tolerance=0.0001, silent=False):
        cc = native(cells, transferDictionaries=transferDictionaries, tolerance=tolerance, silent=True)
        if cc is None and isinstance(cells, list):
            faces = [f for c in cells if Topology.IsInstance(c, "Cell") for f in Topology.Faces(c)]
            cc = CellComplex.ByFaces(faces, transferDictionaries=transferDictionaries, tolerance=tolerance,
                                     silent=True) if faces else None
        if cc is None and not silent:
            print("CellComplex.ByCells - Error: Could not create a CellComplex from the input Cells. Returning None.")
        return cc
    by_cells.tbim_fallback = True
    CellComplex.ByCells = staticmethod(by_cells)


_by_cells_with_face_fallback()


# --------------------------------------------------------------------------------------
# Dictionaries
def props(topology):
    """Topology dictionary as a python dict (without topologicpy internal keys)."""
    d = Topology.Dictionary(topology, silent=True)
    if d is None:
        return {}
    if not isinstance(d, dict):  # the pythonocc backend already returns a python dict
        d = Dictionary.PythonDictionary(d)
    return clean(d or {})


def get(topology, key, default=None):
    value = props(topology).get(key)
    return default if value is None else value


def update(topology, values):
    """Merge ``values`` into the topology dictionary (in place)."""
    merged = props(topology)
    merged.update(values)
    Topology.SetDictionary(topology, Dictionary.ByPythonDictionary(merged), silent=True)
    return topology


def replace(topology, values):
    Topology.SetDictionary(topology, Dictionary.ByPythonDictionary(dict(values)), silent=True)
    return topology


# --------------------------------------------------------------------------------------
# JSON I/O
def _mean_key(coordinates, ndigits=1):
    n = float(len(coordinates))
    return tuple(round(sum(c[i] for c in coordinates) / n, ndigits) for i in range(3))


def _vertex_key(coordinates, ndigits=1):
    """The rounded vertices themselves: a face with a hole and the face filling it share the vertex mean."""
    return tuple(sorted(set(tuple(round(c, ndigits) for c in p) for p in coordinates)))


def _keys(coordinates):
    return _vertex_key(coordinates), _mean_key(coordinates)


def _raw_dictionaries(records):
    """{'Cell'|'Face': {key: dictionary}} from the raw JSON records, keyed by vertices and by vertex mean.

    A vertex-mean key shared by two topologies (e.g. a ring face and the face inside it) is dropped.
    """
    by_uuid = dict((r["uuid"], r) for r in records if "uuid" in r)
    children = {"Edge": "vertices", "Wire": "edges", "Face": "wires", "Shell": "faces", "Cell": "shells"}
    memo = {}

    def vertices(uuid):
        if uuid not in memo:
            record = by_uuid[uuid]
            if record["type"] == "Vertex":
                memo[uuid] = {tuple(record["coordinates"])}
            else:
                result = set()
                for child in record.get(children[record["type"]], []):
                    result |= vertices(child)
                memo[uuid] = result
        return memo[uuid]

    out = {"Cell": {}, "Face": {}}
    for record in records:
        if record.get("type") in out and record.get("dictionary"):
            exact, mean = _keys(list(vertices(record["uuid"])))
            out[record["type"]][exact] = record["dictionary"]
            table = out[record["type"]]
            table[mean] = None if mean in table else record["dictionary"]  # None: ambiguous mean
    return out


def _topology_keys(topology):
    return _keys([Vertex.Coordinates(v) for v in Topology.Vertices(topology)])


def restore(cc, dictionaries):
    """Re-apply cell and face dictionaries to a rebuilt CellComplex (matched by their vertices)."""
    for kind, subtopologies in (("Cell", Topology.Cells(cc)), ("Face", Topology.Faces(cc))):
        for sub in subtopologies:
            exact, mean = _topology_keys(sub)
            d = dictionaries[kind].get(exact) or dictionaries[kind].get(mean)
            if d is not None:
                replace(sub, clean(d))
    return cc


def load_cellcomplex(path):
    """Load the CellComplex of a TBIM JSON file, with cell and face dictionaries.

    ``Topology.ByJSONPath`` (topologicpy >= 0.9) rebuilds the CellComplex from its
    cells and loses the dictionaries of the sub-topologies: they are restored here
    by matching the vertices of cells and faces.
    """
    if not os.path.exists(path):
        raise IOError("TBIM file not found: %s" % path)
    records = _unique_apertures(read_json(path))
    result = Topology.ByJSONDictionary(records, silent=True)
    topologies = result if isinstance(result, list) else [result]
    complexes = [t for t in topologies if Topology.IsInstance(t, "CellComplex")]
    if not complexes:
        raise ValueError("No CellComplex in %s" % path)
    return restore(complexes[0], _raw_dictionaries(records))


def _aperture_key(group):
    uid = aperture_uid(group)
    if uid is not None:
        return uid
    return tuple(sorted(tuple(round(c, 1) for c in i["coordinates"]) for i in group if i.get("type") == "Vertex"))


def _unique_apertures(records):
    """Drop repeated apertures.

    topologicpy exports the apertures of an internal face once per adjacent cell and
    re-adds all of them on import, so every load/save cycle would double them.
    (Even unique apertures are attached once per adjacent cell after import:
    readers must de-duplicate apertures by UID, as ``tbimjson.dictionaries`` does.)
    """
    seen = set()
    for record in records:
        groups = record.get("apertures")
        if not groups:
            continue
        unique = []
        for group in groups:
            key = _aperture_key(group)
            if key not in seen:
                seen.add(key)
                unique.append(group)
        record["apertures"] = unique
    return records


def save_cellcomplex(cc, path):
    Topology.ExportToJSON([cc], path, overwrite=True, silent=True)
    return path


# --------------------------------------------------------------------------------------
# Topology queries
def face_groups(cc):
    """Ordered dict-like list of (topological type, faces)."""
    decomposed = CellComplex.Decompose(cc)
    return [(face_type, decomposed.get(key) or []) for face_type, key in FACE_GROUPS]


def adjacent_cells(face, cc):
    return Topology.AdjacentTopologies(face, cc, topologyType="cell", silent=True) or []


def cell_uid(cell):
    return get(cell, "UID")


def interior_point(cell):
    """Centroid if inside the cell, otherwise a vertex guaranteed to be inside (e.g. L-shapes)."""
    centroid = Topology.Centroid(cell)
    if Vertex.IsInternal(centroid, cell):
        return centroid
    return Cell.InternalVertex(cell)


def z_range(topology):
    zs = [Vertex.Z(v) for v in Topology.Vertices(topology)]
    return min(zs), max(zs)


def outward_normal(face, cell):
    """Normal of ``face`` pointing away from ``cell``."""
    normal = Face.Normal(face)
    c = Vertex.Coordinates(Topology.Centroid(face))
    p = Vertex.Coordinates(interior_point(cell))
    if sum(n * (a - b) for n, a, b in zip(normal, c, p)) < 0:
        normal = [-n for n in normal]
    return normal


def assign_face_types(cc):
    """Set pr_TopologicalType and UID (e.g. 'extVerFace3') on every face.

    Existing UIDs are kept: they are already written on the Revit walls by the Collectors.
    """
    groups = face_groups(cc)
    for face_type, faces in groups:
        for index, face in enumerate(faces):
            update(face, {"pr_TopologicalType": face_type, "UID": get(face, "UID") or "%sFace%d" % (face_type, index)})
    return groups


__all__ = ["INTERNAL_KEYS", "FACE_GROUPS", "EXTERNAL_TYPES", "props", "get", "update", "replace",
           "load_cellcomplex", "save_cellcomplex", "face_groups", "adjacent_cells", "cell_uid",
           "interior_point", "z_range", "outward_normal", "assign_face_types"]
