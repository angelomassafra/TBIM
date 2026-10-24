"""Instance BIM: enrich the TBIM CellComplex with instance data (CPython only)."""
from topologicpy.Cell import Cell
from topologicpy.CellComplex import CellComplex
from topologicpy.Edge import Edge
from topologicpy.Face import Face

from tbim import ibim, topo
from tbim.units import cm2_to_m2, cm3_to_m3


def by_occupancy_type(cc, table):
    """Add the properties of ``table`` rows matching the cell occupancy type."""
    rows = dict((row["pr_OccupancyType"], row) for row in table)
    for cell in CellComplex.Cells(cc):
        props = topo.props(cell)
        row = rows.get(props.get("pr_OccupancyType"))
        if row:
            new = dict((k, v) for k, v in row.items() if k not in ("UID", "pr_OccupancyType"))
            topo.update(cell, ibim.missing_only(props, new))


def by_table_of_spaces(cc, table, space_names):
    """Add the aggregated rows of the table of spaces. space_names: {cell UID: 'id1; id2'}."""
    rows = {}
    for row in table:
        rows.setdefault(str(row["UID"]).replace(" ", ""), []).append(row)
    matched = 0
    for cell in CellComplex.Cells(cc):
        props = topo.props(cell)
        names = space_names.get(props.get("UID"))
        if not names:
            continue
        ids = [n.replace(" ", "") for n in names.split(";") if n.strip()]
        cell_rows = [r for i in ids for r in rows.get(i, [])]
        values = ibim.missing_only(props, ibim.aggregate_spaces(cell_rows))
        values["rl_HasLocation_tpSP"] = names
        topo.update(cell, values)
        matched += 1 if cell_rows else 0
    return matched


def gross_geometry(cell):
    """(gross area m2, gross volume m3, gross height m) of a cell (model in cm)."""
    decomposed = Cell.Decompose(cell)
    area = sum(Face.Area(f) for f in decomposed.get("bottomHorizontalFaces") or [])
    height = None
    for face in decomposed.get("verticalFaces") or []:
        for edge in Face.Edges(face):
            if abs(Edge.Direction(edge)[2]) > 0.999:
                height = Edge.Length(edge) / 100.0
                break
        if height is not None:
            break
    return cm2_to_m2(area), cm3_to_m3(Cell.Volume(cell)), height


def by_model(cc, revit_spaces):
    """Add the ByModel properties. revit_spaces: {cell UID: (net area m2, net volume m3)}."""
    count = 0
    for cell in CellComplex.Cells(cc):
        props = topo.props(cell)
        net = revit_spaces.get(props.get("UID"))
        if net is None:
            continue
        values = ibim.by_model(props, *(gross_geometry(cell) + tuple(net)))
        new = ibim.missing_only(props, values)
        new.update((k, values[k]) for k in ibim.MEASURED_KEYS if values[k] != ibim.UNDEFINED)
        topo.update(cell, new)
        count += 1
    return count
