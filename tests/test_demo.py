"""Run the complete demo workflow (examples/demo) on a copy of the demo folder."""
import json
import os
import shutil
import subprocess
import sys

import pytest

import tbim

if tbim.topologic_backend() is None:
    pytest.skip("no topologicpy backend (pythonocc-core or topologic_core)", allow_module_level=True)

DEMO = os.path.join(os.path.dirname(__file__), os.pardir, "examples", "demo")


def test_demo_workflow(tmp_path):
    demo = tmp_path / "examples" / "demo"
    shutil.copytree(DEMO, str(demo), ignore=shutil.ignore_patterns("json", "3d"))
    lib = os.path.abspath(os.path.join(DEMO, os.pardir, os.pardir, "pyRevit"))
    shutil.copytree(lib, str(tmp_path / "pyRevit"), ignore=shutil.ignore_patterns("__pycache__"))
    for script in ("make_demo.py", "run_offline.py"):
        subprocess.run([sys.executable, str(demo / script)], check=True, capture_output=True)

    def load(name):
        with open(str(demo / "json" / name)) as f:
            return json.load(f)

    ibim = load("tbim_CellComplex_IBIM.json")
    cells = [r["dictionary"] for r in ibim if r["type"] == "Cell"]
    groups = [g for r in ibim for g in r.get("apertures") or []]
    apertures = {a["dictionary"]["UID"] for g in groups for a in g if a["type"] == "Face"}
    assert len(cells) == 9
    assert len(apertures) == 19
    assert all(c.get("rl_HasLocation_tpZN") and c.get("pr_NetArea") for c in cells)
    assert sorted(load("tbim_CellComplex_Loads-OccupancyTypes.json")[0]) == ["UID", "pr_OccupancyType"]


def test_load_save_cycles_do_not_duplicate_apertures(tmp_path):
    from tbim import tbimjson, topo

    path = os.path.join(DEMO, "json", "tbim_CellComplex_IBIM.json")
    if not os.path.exists(path):
        pytest.skip("run examples/demo/run_offline.py first")
    expected = len(tbimjson.dictionaries(path)["Aperture"])
    sizes = []
    for i in range(3):
        path = topo.save_cellcomplex(topo.load_cellcomplex(path), str(tmp_path / ("cycle%d.json" % i)))
        records = json.load(open(path))
        sizes.append(len([a for r in records for g in r.get("apertures") or [] for a in g if a["type"] == "Face"]))
        assert len(tbimjson.dictionaries(records)["Aperture"]) == expected
    assert sizes[1] == sizes[2]  # no growth across load/save cycles


def test_move_apertures_in_json():
    from tbim import tbimjson

    group = [{"type": "Vertex", "coordinates": [0, 0, 0]}, {"type": "Vertex", "coordinates": [1, 0, 2]},
             {"type": "Face", "dictionary": {"UID": "door0"}}]
    records = [{"type": "Face", "apertures": [group]}, {"type": "Face", "apertures": []}]
    assert tbimjson.move_apertures(records, {"door0": (100, 0, 0), "missing": (1, 1, 1)}) == ["door0"]
    assert [v["coordinates"] for v in group[:2]] == [[100, 0, 0], [101, 0, 2]]
