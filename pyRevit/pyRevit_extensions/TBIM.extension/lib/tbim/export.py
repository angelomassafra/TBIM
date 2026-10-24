"""Export of the TBIM Topologic models to files (CPython only, no Revit).

The files go to the ``export`` folder of the active project (next to ``json``).
Coordinates are in centimetres, as in the Topologic models.
"""
import os
import shutil

from topologicpy.Topology import Topology

from tbim import paths, scene, topo
from tbim.jsonio import write_json

EXPORT_FOLDER = "export"

# (label, file extension) of the export formats
FORMATS = [
    ("Topologic JSON (geometry, dictionaries and apertures)", ".json"),
    ("BREP (geometry)", ".brep"),
    ("OBJ (geometry)", ".obj"),
    ("Adjacency graph JSON (cells sharing walls and slabs)", "_adjacency_graph.json"),
    ("Passage graph JSON (doors, stairs and entrances between the cells)", "_passage_graph.json"),
]
ALL_FORMATS = "All the formats"


def export_dir():
    """``<project>/export``, created if missing."""
    folder = os.path.join(os.path.dirname(os.path.abspath(paths.data_dir())), EXPORT_FOLDER)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    return folder


def file_name(label, extension):
    """tbim_<model label without spaces><extension>, e.g. tbim_InstanceBIM.brep."""
    words = [w[:1].upper() + w[1:] for w in label.split()]
    return "tbim_" + "".join(ch for ch in "".join(words) if ch.isalnum()) + extension


def graph_data(cc, path, kind=scene.ADJACENCY):
    """Adjacency or passage graph of the cells of ``cc`` as JSON-ready nodes and edges."""
    nodes, edges = scene.graph(cc, scene.apertures(path), kind)
    return {
        "graph": kind,
        "units": "cm",
        "nodes": [{"id": uid, "x": p[0], "y": p[1], "z": p[2], "properties": props} for uid, p, props in nodes],
        "edges": [{"source": a, "target": b, "kind": kind} for a, b, kind in edges],
    }


def write_obj(cc, out):
    """Wavefront OBJ of the faces of ``cc``: one polygon per face, grouped by face UID (centimetres, Z up).

    Topology.ExportToOBJ is not used: it queries PyPI for the topologicpy version, which fails offline.
    """
    lines, index = ["# TBIM - faces of the CellComplex (cm)"], {}
    for uid, face_type, _, loop in scene.faces(cc):
        ids = []
        for p in loop:
            key = tuple(round(c, 3) for c in p)
            if key not in index:
                index[key] = len(index) + 1
                lines.append("v %g %g %g" % key)
            ids.append(index[key])
        lines.append("g %s_%s" % (face_type, uid or len(lines)))
        lines.append("f " + " ".join(str(i) for i in ids))
    with open(out, "w") as f:
        f.write("\n".join(lines) + "\n")
    return True


def export_model(label, path, extension, folder=None):
    """Export the CellComplex model ``path`` (labelled ``label``) in one format. Return the file written."""
    out = os.path.join(folder or export_dir(), file_name(label, extension))
    if extension == ".json":
        shutil.copyfile(path, out)  # the TBIM files already are topologicpy JSON exports
        return out
    cc = topo.load_cellcomplex(path)
    if extension == ".brep":
        ok = Topology.ExportToBREP(cc, out, overwrite=True, silent=True)
    elif extension == ".obj":
        ok = write_obj(cc, out)
    elif extension in ("_adjacency_graph.json", "_passage_graph.json"):
        kind = scene.ADJACENCY if extension.startswith("_adjacency") else scene.PASSAGE
        write_json(out, graph_data(cc, path, kind))
        ok = True
    else:
        raise ValueError("Unknown export format: %s" % extension)
    if not ok or not os.path.isfile(out):
        raise RuntimeError("topologicpy could not write %s" % out)
    return out
