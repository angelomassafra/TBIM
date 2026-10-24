"""Loads > Update / Clusterize command (CPython only)."""
from topologicpy.CellComplex import CellComplex

from tbim import ild, loads, paths, revit, topo
from tbim.jsonio import read_json, write_json


def run(ctx, clusterize):
    cc = topo.load_cellcomplex(paths.data_file(paths.CC_CONTROLLERS))
    north = float(read_json(paths.data_file(paths.NORTH_ANGLE), default=0))
    face_keys = loads.run(cc, ild.load(), ild.load_assignments(), north, clusterize=clusterize)
    write_json(paths.data_file(paths.FACE_PROPERTIES), face_keys)

    cells = dict((topo.cell_uid(c), topo.props(c)) for c in CellComplex.Cells(cc))
    revit.ensure_parameters(ctx, set(k for p in cells.values() for k in p), "Cell", revit.SPACE_CATEGORIES)
    updated = revit.apply_by_uid(ctx.doc, revit.spaces(ctx.doc), cells, "Update spaces")

    outputs = [paths.CC_LOADS] + ([paths.CC_LOADS_CLUSTERIZED] if clusterize else [])
    saved = [topo.save_cellcomplex(cc, paths.data_file(name)) for name in outputs]
    message = "Informational Loads assigned to %d cells (%d spaces updated).\n\nExported to:\n%s" % (
        len(cells), updated, "\n".join(saved))
    if clusterize:
        zones = sorted(set(p.get("rl_HasLocation_tpZN") for p in cells.values()))
        message = "Thermal zones: %d\n" % len(zones) + message
    revit.alert("Informational Loads", message)
