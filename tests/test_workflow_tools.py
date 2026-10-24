"""Tests of the TopologicalBIM rules, the table of rooms, the graphs, the JSON round trip and the checks."""
import pytest

pytest.importorskip("topologic_core")

from topologicpy.Cell import Cell  # noqa: E402
from topologicpy.CellComplex import CellComplex  # noqa: E402
from topologicpy.Face import Face  # noqa: E402
from topologicpy.Vertex import Vertex  # noqa: E402

from tbim import apertures, check, materials, rooms, scene, topo  # noqa: E402


def box(x0, x1, y0, y1, z0, z1):
    return Cell.Prism(origin=Vertex.ByCoordinates((x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0),
                      width=x1 - x0, length=y1 - y0, height=z1 - z0)


def building(occupancies):
    """Two stacked rows of rooms 500 x 600 x 300 cm along x, with the given occupancy types (bottom row first)."""
    cells = [box(i * 500, (i + 1) * 500, 0, 600, z * 300, (z + 1) * 300)
             for z, row in enumerate(occupancies) for i in range(len(row))]
    cc = CellComplex.ByCells(cells, silent=True)
    topo.assign_face_types(cc)
    flat = [o for row in occupancies for o in row]
    for index, cell in enumerate(CellComplex.Cells(cc)):
        c = Vertex.Coordinates(topo.interior_point(cell))
        i, z = int(c[0] // 500), int(c[2] // 300)
        topo.update(cell, {"UID": "Cell%d" % index, "pr_OccupancyType": occupancies[z][i]})
    assert len(CellComplex.Cells(cc)) == len(flat)
    return cc


def test_faces_with_holes_keep_their_data(tmp_path):
    """A ring face and the face inside it share the vertex mean: both keep their dictionaries."""
    cc = CellComplex.ByCells([box(0, 800, 0, 800, 0, 400), box(200, 600, 200, 600, 400, 800)], silent=True)
    topo.assign_face_types(cc)
    ring = [topo.get(f, "UID") for f in CellComplex.Faces(cc) if Face.InternalBoundaries(f)]
    assert len(ring) == 1
    reloaded = topo.load_cellcomplex(topo.save_cellcomplex(cc, str(tmp_path / "cc.json")))
    uids = [topo.get(f, "UID") for f in CellComplex.Faces(reloaded)]
    assert len(uids) == len(set(uids)) == len(CellComplex.Faces(cc))
    assert [topo.get(f, "UID") for f in CellComplex.Faces(reloaded) if Face.InternalBoundaries(f)] == ring


def test_aperture_rules():
    cc = building([["Circulation:EntranceHall", "Office:Private", "Circulation:Stair"],
                   ["Office:Private", "Office:Private", "Circulation:Stair"]])
    rules = {"windows": [["Circulation", None], ["", "W", 120, 150, 90]],
             "external_doors": [["EntranceHall", "D_EXT", 200, 240]],
             "doors": [["Office", "Office", None], ["", "", "D", 90, 210]]}
    cc, placements = apertures.place(cc, rules)
    kinds = [(p["kind"], p["type"]) for p in placements]
    assert ("door", "D_EXT") in kinds  # entrance hall on the ground
    assert all(t != "W" or k == "window" for k, t in kinds)
    hosts = dict((p["UID"], p["host"]) for p in placements)
    assert all(h.startswith("extVer") for u, h in hosts.items() if u.startswith("window"))
    # no window in the circulation cells: the null rule comes first
    windowed = set(topo.get(c, "pr_OccupancyType") for f in CellComplex.Faces(cc) for c in topo.adjacent_cells(f, cc)
                   if topo.get(f, "UID") in [p["host"] for p in placements if p["kind"] == "window"])
    assert windowed == {"Office:Private"}
    # internal doors: office-office is excluded, every other pair of neighbours gets one door
    internal = [p for p in placements if p["kind"] == "door" and p["host"].startswith("intVer")]
    assert len(internal) == 3  # hall-office, office-stair (ground), office-stair (first floor)
    assert apertures.locations(placements)[0]["Location"]["Revit"]["Z"] >= 0


def test_entrance_levels():
    cc = building([["Parking:Garage", "Parking:Garage"], ["Circulation:EntranceHall", "Residential:Flat"]])
    rules = {"external_doors": [["EntranceHall", "D", 180, 240]], "entrance_levels": [300]}
    _, placements = apertures.place(cc, rules)
    assert [p["type"] for p in placements] == ["D"] and placements[0]["point"][2] == 300


def test_rooms_match_by_containment():
    cc = building([["A", "B"]])
    table = [{"center": [250, 300, 150], "pr_OccupancyType": "A", "space": "1", "name": "a"},
             {"center": [750, 300, 150], "pr_OccupancyType": "B", "space": "2; 3", "name": "b"}]
    matches, shared = rooms.match(cc, table)
    assert not shared
    by_occupancy = dict((topo.get(c, "pr_OccupancyType"), topo.cell_uid(c)) for c in CellComplex.Cells(cc))
    assert rooms.assignments(matches)[by_occupancy["B"]] == "B"
    assert rooms.space_ids(matches)[by_occupancy["B"]] == "2; 3"
    _, shared = rooms.match(cc, table[:1])  # one room for two cells
    assert len(shared) == 2


def test_passage_graph_with_stairs_and_entrances(tmp_path):
    cc = building([["Circulation:EntranceHall", "Circulation:Stair"], ["Office:Private", "Circulation:Stair"]])
    rules = {"external_doors": [["EntranceHall", "D_EXT", 200, 240]], "doors": [["", "", "D", 90, 210]]}
    cc, _ = apertures.place(cc, rules)
    path = topo.save_cellcomplex(cc, str(tmp_path / "tbim.json"))
    cc, records = topo.load_cellcomplex(path), scene.apertures(path)  # as Visualize > Dual/Passage Graph read it
    nodes, edges = scene.graph(cc, records, scene.PASSAGE)
    kinds = sorted(kind for _, _, kind in edges)
    assert kinds.count("stair") == 1 and kinds.count("entrance") == 1 and "door" in kinds
    exterior = [n for n in nodes if n[0].startswith(scene.EXTERIOR)]
    x, y, _ = exterior[0][1]
    assert len(exterior) == 1 and not (0 < x < 1000 and 0 < y < 600)  # just outside the building
    _, adjacency = scene.graph(cc, records, scene.ADJACENCY)
    assert set(kind for _, _, kind in adjacency) == {"wall", "slab"}


def test_shell_functions_are_valid_for_revit():
    names = [materials.MATERIALS[n][4] for n in
             ("Clay roof tiles", "Timber battens", "Timber boarding", "Mineral wool", "Timber rafters")]
    functions, first, last = materials.shell_functions(names)
    assert (first, last) == (4, 4)
    outside = [materials.FUNCTIONS.index(f) for f in functions[:first]]
    assert outside == sorted(outside, reverse=True)  # priority does not decrease from the core outwards
    assert materials.shell_functions([materials.INSULATION])[1:] == (0, 0)


def test_checks():
    findings = check.rules([{"stFC_WallTypeName": "A", "stFC_Layers": "Facing brick 120 mm"},
                            {"stFC_WallTypeName": "B"},
                            {"stFC_WallTypeName": "C", "stFC_Layers": "Unobtainium 10 mm"}])
    assert [level for level, _ in findings] == [check.ERROR, check.INFO]
    cc = building([["Default", "Office"]])
    levels = [level for level, _ in check.cellcomplex(cc)]
    assert levels == [check.WARNING]  # one cell without occupancy type
    assert check.report([(check.ERROR, "x"), (check.INFO, "y")]).startswith("1 errors, 0 warnings")
