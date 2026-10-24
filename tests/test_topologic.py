"""Tests of the topologicpy based pipeline (skipped if topologicpy/topologic_core are missing)."""
import json
import os
import sys

import pytest

pytest.importorskip("topologic_core")

from topologicpy.Cell import Cell  # noqa: E402
from topologicpy.CellComplex import CellComplex  # noqa: E402
from topologicpy.Topology import Topology  # noqa: E402
from topologicpy.Vertex import Vertex  # noqa: E402

from tbim import irs, loads, scene, styles, topo  # noqa: E402

ILDS = [
    {"pr_OccupancyType": "Default", "pr_CirculationType": "NoCirculation", "pr_IsHeated": True},
    {"pr_OccupancyType": "Office", "pr_CirculationType": "NoCirculation", "pr_IsHeated": True},
    {"pr_OccupancyType": "Corridor", "pr_CirculationType": "Public", "pr_IsHeated": False},
]


def three_cells():
    """Two cells side by side on the ground storey and one above (cm)."""
    boxes = [(250, 250, 150), (750, 250, 150), (250, 250, 450)]
    cells = [Cell.Prism(origin=Vertex.ByCoordinates(x, y, z), width=500, length=500, height=300) for x, y, z in boxes]
    cc = CellComplex.ByCells(cells)
    ordered = sorted(CellComplex.Cells(cc), key=lambda c: (topo.z_range(c)[0], Vertex.X(topo.interior_point(c))))
    for index, cell in enumerate(ordered):
        zmin = topo.z_range(cell)[0]
        topo.update(cell, {"UID": "Cell%d" % index, "rl_HasLocation_tpBS": "BuildingStorey_%dcm" % round(zmin),
                           "rl_HasLocation_tpBB": "B1"})
    return cc


@pytest.fixture
def cc():
    return three_cells()


def test_loads_pipeline(cc, tmp_path):
    assignments = {"Cell0": "Office", "Cell1": "Corridor", "Cell2": "Unknown"}
    face_keys = loads.run(cc, ILDS, assignments, north_angle=0, clusterize=True)
    cells = dict((topo.cell_uid(c), topo.props(c)) for c in CellComplex.Cells(cc))
    assert cells["Cell0"]["pr_OccupancyType"] == "Office"
    assert cells["Cell2"]["pr_OccupancyType"] == "Default"
    assert cells["Cell1"]["pr_CirculationType"] == "Public"  # was dropped by Clusterize in TBIM 0.2
    assert cells["Cell0"]["pr_NumberOfExposures"] == 3
    assert cells["Cell0"]["rl_HasLocation_tpZN"] != cells["Cell1"]["rl_HasLocation_tpZN"]
    assert cells["Cell2"]["rl_HasLocation_tpZN"].endswith("_BS300")
    for key in ("UID", "pr_TopologicalType", "rl_HasLocation_tpSP", "pr_FaceExposure", "rl_HasLocation_tpZN"):
        assert key in face_keys

    internal = [f for t, faces in topo.face_groups(cc) if t == "intVer" for f in faces]
    assert topo.props(internal[0])["rl_HasLocation_tpSP"] == "Cell0-Cell1"

    # JSON round trip keeps cell and face dictionaries
    path = topo.save_cellcomplex(cc, str(tmp_path / "loads.json"))
    reloaded = topo.load_cellcomplex(path)
    uids = sorted(topo.cell_uid(c) for c in CellComplex.Cells(reloaded))
    assert uids == ["Cell0", "Cell1", "Cell2"]
    assert all(topo.get(f, "UID") for f in CellComplex.Faces(reloaded))


def test_styles(cc):
    loads.run(cc, ILDS, {}, 0)
    rulesets = [{"cnFC_equalTo_pr_TopologicalType": "extVer", "stFC_WallTypeName": "EXT"},
                {"cnFC_equalTo_pr_TopologicalType": "intHor", "stFC_FloorTypeName": "SLAB"}]
    styled = styles.run(cc, rulesets)
    faces = [topo.props(f) for f in CellComplex.Faces(cc)]
    assert styled == len([f for f in faces if f["pr_TopologicalType"] in ("extVer", "intHor")])
    assert all(f.get("stFC_WallTypeName") == "EXT" for f in faces if f["pr_TopologicalType"] == "extVer")
    assert irs.style_keys(rulesets) == ["stFC_FloorTypeName", "stFC_WallTypeName"]


def test_scene_graph_and_geometry(cc):
    topo.assign_face_types(cc)
    door_face = [topo.get(f, "UID") for t, faces in topo.face_groups(cc) if t == "intVer" for f in faces][0]
    door = ({"pr_TopologicalType": "door", "rl_HasLocation_inFC": door_face}, [])
    nodes, edges = scene.graph(cc, [door])
    assert sorted(n[0] for n in nodes) == ["Cell0", "Cell1", "Cell2"]
    assert sorted(kind for _, _, kind in edges) == ["slab", "wall"]  # Cell0-Cell1 share a wall, Cell0-Cell2 a slab
    _, passages = scene.graph(cc, [door], scene.PASSAGE)
    assert [kind for _, _, kind in passages] == ["door"]  # the slab is not a passage
    faces = scene.faces(cc)
    assert len(faces) == len(CellComplex.Faces(cc)) and all(len(loop) == 4 for _, _, _, loop in faces)
    shrunk = scene.cells(cc, shrink=0.5)
    xs = [p[0] for loop in shrunk[0][2] for p in loop]
    assert max(xs) - min(xs) == pytest.approx(250)


def test_building_kit_writes_a_project(tmp_path):
    """Two rooms side by side and a gable attic: BRep, rooms and the inputs of every step."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir, "tools"))
    import building_kit as kit

    rooms = [kit.Room(0, 400, 0, 500, 0, 300, "Office:Private", "A", "Office A"),
             kit.Room(400, 800, 0, 500, 0, 300, "Office:Private", "B", "Office B")]
    attic = kit.Room(0, 1, 0, 1, 0, 1, "Unconditioned:Attic", "R", "Attic")
    attic.cell = kit.gable_attic(0, 800, 0, 500, 300, 150)
    ilds = [kit.ild("Office:Private", "NoCirculation", True, True, False, True, False, 10),
            kit.ild("Unconditioned:Attic", "NoCirculation", False, False, False, True, False, 0)]
    kit.write_project(str(tmp_path), "Test", "", rooms + [attic], 0, ilds, [], {}, {})
    cc = Topology.ByBREPPath(str(tmp_path / "3d" / "Block.brep"))
    assert len(Topology.Cells(cc)) == 3
    data = json.load(open(str(tmp_path / "json" / "tbim_Rooms.json")))
    assert [r["space"] for r in data] == ["A", "B", "R"]
    assert 300 < data[2]["center"][2] < 450  # inside the attic
    assert (tmp_path / "json" / "tbim_IRS_extVerFaces.json").exists()
