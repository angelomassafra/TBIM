"""Projects, colors and visualization geometry (Revit-free parts)."""
import json
import os

import pytest

from tbim import colors, paths, projects, tbimjson

DEMO_JSON = os.path.join(os.path.dirname(__file__), os.pardir, "examples", "demo", "json")


@pytest.fixture
def tbim_home(tmp_path, monkeypatch):
    """Empty TBIM installation with templates."""
    templates = tmp_path / "templates" / "json"
    templates.mkdir(parents=True)
    (templates / "tbim_ILDs.json").write_text("[]")
    monkeypatch.setenv(paths.ENV_VAR, str(tmp_path))
    return tmp_path


# Projects ----------------------------------------------------------------------------
def test_create_and_activate_project(tbim_home):
    folder = projects.create_project("My School / 2026", "test")
    assert os.path.basename(folder) == "My_School_2026"
    assert os.path.isfile(os.path.join(folder, "json", "tbim_ILDs.json"))
    assert os.path.isdir(os.path.join(folder, "3d"))
    assert projects.list_projects() == [("My School / 2026", folder)]
    with pytest.raises(ValueError):
        projects.create_project("My School / 2026")

    projects.activate(folder)
    assert paths.read_settings()["data_dir"] == "projects/My_School_2026/json"
    assert os.path.normcase(projects.active_project()) == os.path.normcase(folder)
    assert [s for s, _, done in projects.status() if done] == []


def test_project_relative_paths(tbim_home, tmp_path):
    folder = projects.activate(projects.create_project("P"))
    brep = os.path.join(folder, "3d", "A.brep")
    assert projects.relative(brep) == "3d/A.brep"
    assert os.path.normcase(projects.resolve("3d/A.brep")) == os.path.normcase(brep)
    outside = str(tmp_path.parent / "elsewhere.brep")
    assert projects.relative(outside) == os.path.abspath(outside)


def test_model_link_is_relative_inside_tbim(tbim_home, tmp_path):
    folder = projects.create_project("P")
    assert projects.model_link(folder) == "projects/P"
    assert os.path.normcase(projects.resolve_link("projects/P")) == os.path.normcase(folder)
    outside = str(tmp_path.parent / "elsewhere")
    assert projects.model_link(outside) == os.path.abspath(outside)
    assert projects.resolve_link(outside) == os.path.normpath(outside) and projects.resolve_link("") is None


def test_any_folder_becomes_a_project(tbim_home, tmp_path):
    folder = str(tmp_path / "external")
    projects.activate(folder)
    assert projects.is_project(folder) and projects.info(folder)["name"] == "external"


# Colors ------------------------------------------------------------------------------
def test_legend_categorical_and_numeric():
    color_of, entries = colors.legend_for(["Zone1", "Zone0", None, "Zone1"])
    assert [label for label, _ in entries] == ["NaN", "Zone0", "Zone1"]
    assert color_of("Zone1") == dict(entries)["Zone1"] != color_of("Zone0")

    color_of, entries = colors.legend_for([float(i) for i in range(20)])
    assert len(entries) == len(colors.SEQUENTIAL)
    assert color_of(0.0) == colors.SEQUENTIAL[0] and color_of(19.0) == colors.SEQUENTIAL[-1]
    assert colors.to_hex((0, 114, 178)) == "#0072B2"


# Apertures from the JSON -------------------------------------------------------------
def test_aperture_polygons_from_demo():
    path = os.path.join(DEMO_JSON, paths.CC_TBIM)
    if not os.path.isfile(path):
        pytest.skip("run examples/demo/run_offline.py first")
    polygons = tbimjson.aperture_polygons(path)
    uids = [d["UID"] for d, _ in polygons]
    assert len(uids) == len(set(uids)) > 0
    assert all(len(loop) == 4 and d.get("rl_HasLocation_inFC") for d, loop in polygons)
    with open(path) as f:
        assert len(tbimjson.aperture_polygons(json.load(f))) == len(polygons)


# Export ------------------------------------------------------------------------------
def test_export_topologic_formats(tmp_path):
    from tbim import export
    path = os.path.join(os.path.dirname(__file__), os.pardir, "projects", "Demo_School", "json",
                        "tbim_CellComplex_IBIM.json")
    assert export.file_name("Informational Controllers", ".brep") == "tbim_InformationalControllers.brep"
    for _, extension in export.FORMATS:
        out = export.export_model("InstanceBIM", path, extension, str(tmp_path))
        assert os.path.getsize(out) > 0
    adjacency = json.load(open(str(tmp_path / "tbim_InstanceBIM_adjacency_graph.json")))
    assert adjacency["graph"] == "Adjacency graph" and len(adjacency["nodes"]) == 9 and adjacency["edges"]
    passage = json.load(open(str(tmp_path / "tbim_InstanceBIM_passage_graph.json")))
    kinds = set(e["kind"] for e in passage["edges"])
    assert kinds <= {"door", "stair", "entrance"} and "door" in kinds
