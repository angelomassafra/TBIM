"""Tests of the pure Python modules (no topologicpy, no Revit)."""
import json
import os

import pytest

from tbim import analysis, ibim, ild, irs, paths, tbimjson, zoning


def test_tbim_root_is_the_tbim_folder(monkeypatch):
    monkeypatch.delenv("TBIM_HOME", raising=False)
    root = paths.tbim_root()
    assert os.path.basename(root).lower() == "tbim"
    assert os.path.isdir(os.path.join(root, "pyRevit"))  # not the 'tbim' package folder
    assert paths.data_file(paths.ILDS) == os.path.join(paths.data_dir(), "tbim_ILDs.json")


def test_tbim_home_override(monkeypatch, tmp_path):
    monkeypatch.setenv("TBIM_HOME", str(tmp_path))
    assert paths.data_dir() == os.path.join(str(tmp_path), "json")


# ILD ---------------------------------------------------------------------------------
ILDS = [
    {"pr_OccupancyType": "Default", "pr_IsHeated": True, "pr_CirculationType": "NoCirculation"},
    {"pr_OccupancyType": "Office", "pr_IsHeated": False, "pr_CirculationType": "NoCirculation"},
]


def test_ild_resolve_falls_back_to_default():
    assert ild.resolve(ILDS, "Office")[:2] == ("Office", 1)
    assert ild.resolve(ILDS, "Unknown")[:2] == ("Default", 0)
    assert ild.resolve(ILDS, None)[:2] == ("Default", 0)


def test_ild_load_keys_and_types():
    assert ild.load_keys(ILDS) == ["pr_CirculationType", "pr_IsHeated"]
    assert ild.occupancy_types(ILDS) == ["Default", "Office"]


@pytest.mark.parametrize("text,template,expected", [
    ("true", False, True), ("0", True, False), ("3", 1, 3), ("2.5", 1.0, 2.5), ("abc", "x", "abc")])
def test_ild_coerce_like(text, template, expected):
    assert ild.coerce_like(text, template) == expected


def test_ild_coerce_like_rejects_invalid_boolean():
    with pytest.raises(ValueError):
        ild.coerce_like("maybe", True)


# IRS ---------------------------------------------------------------------------------
def test_irs_parse_condition_is_case_insensitive():
    assert irs.parse_condition("cnFC_IsContained_pr_OccupancyType") == ("isContained", "pr_OccupancyType")
    with pytest.raises(ValueError):
        irs.parse_condition("cnFC_bigger_pr_Area")


def test_irs_apply_in_order_and_missing_property_does_not_match():
    rulesets = [
        {"cnFC_equalTo_pr_TopologicalType": "intVer", "stFC_WallTypeName": "Base"},
        {"cnFC_equalTo_pr_TopologicalType": "intVer", "cnFC_contains_rl_HasLocation_tpBS": "_0cm",
         "stFC_WallTypeName": "GroundFloor"},
        {"cnFC_equalTo_pr_TopologicalType": "intVer", "cnFC_majorOf_pr_Area": 100, "stFC_Big": 1},
    ]
    face = {"pr_TopologicalType": "intVer", "rl_HasLocation_tpBS": "BuildingStorey_0cm"}
    styled = irs.apply(rulesets, face)
    assert styled["stFC_WallTypeName"] == "GroundFloor"
    assert "stFC_Big" not in styled  # pr_Area is missing
    assert irs.apply(rulesets, dict(face, pr_Area=150))["stFC_Big"] == 1


@pytest.mark.parametrize("rule,expected,actual,result", [
    ("equalTo", 1, "1", True), ("notEqualTo", "a", "b", True), ("minorOf", 10, 5, True),
    ("majorOf", 10, 5, False), ("contains", "_0cm", "BS_0cm", True), ("isContained", "abc", "b", True),
    ("isContained", ["x", "y"], "y", True), ("minorOf", 10, "n/a", False)])
def test_irs_check(rule, expected, actual, result):
    assert irs.check(rule, expected, actual) is result


def test_repository_irs_files_are_valid():
    for _, path in paths.irs_files():
        if os.path.exists(path):
            for ruleset in json.load(open(path)):
                for key, _ in irs.split(ruleset)[0]:
                    irs.parse_condition(key)


# Analysis ----------------------------------------------------------------------------
@pytest.mark.parametrize("normal,expected", [
    ((0, 1, 0), "N"), ((-1, 0, 0), "W"), ((0, -1, 0), "S"), ((1, 0, 0), "E"), ((-1, 1, 0), "NW")])
def test_exposure_with_default_north(normal, expected):
    assert analysis.exposure(normal, analysis.rotate_z(0)) == expected


def test_exposure_with_rotated_north():
    north = analysis.rotate_z(90)  # project north points to -X
    assert analysis.exposure((-1, 0, 0), north) == "N"


def test_dominant_and_joins():
    assert analysis.dominant(["N", "E", "N"], [1, 5, 3]) == "E"
    assert analysis.dominant([], []) is None
    assert analysis.join_values(["b", "a"]) == "a-b"
    assert analysis.join_unique(["x", "x"]) == "x"
    assert analysis.storey_suffix("BuildingStorey_335cm") == "335"


# Zoning ------------------------------------------------------------------------------
def test_connected_components_and_merge():
    adjacency = {"a": {"b"}, "b": {"a"}, "c": set()}
    assert zoning.connected_components(["a", "b", "c"], adjacency) == [["a", "b"], ["c"]]
    assert zoning.merge_overlapping([["a", "s"], ["b", "s"], ["c"]]) == [["a", "s", "b"], ["c"]]


def test_kmeans_is_deterministic():
    points = [[0, 0], [0, 1], [10, 10], [10, 11]]
    labels = zoning.kmeans(points, 2)
    assert labels == zoning.kmeans(points, 2)
    assert labels[0] == labels[1] != labels[2] == labels[3]


def test_zones():
    cells = [
        ("c1", {"pr_OccupancyType": "Office", "pr_CirculationType": "NoCirculation", "pr_IsHeated": 1}),
        ("c2", {"pr_OccupancyType": "Office", "pr_CirculationType": "NoCirculation", "pr_IsHeated": 1}),
        ("s1", {"pr_OccupancyType": "Support:Storage", "pr_CirculationType": "NoCirculation"}),
        ("p1", {"pr_OccupancyType": "Hall", "pr_CirculationType": "Public"}),
        ("k1", {"pr_OccupancyType": "Classroom", "pr_CirculationType": "NoCirculation"}),
    ]
    lateral = {"c1": {"c2", "s1"}, "c2": {"c1"}, "s1": {"c1"}}
    result = zoning.zones(cells, lateral)
    assert result["c1"] == result["c2"] == result["s1"]
    assert len({result["c1"], result["p1"], result["k1"]}) == 3


def test_zones_do_not_span_storeys():
    # s1 lies above c1 (no lateral adjacency) and next to c2 on the upper storey
    cells = [
        ("c1", {"pr_OccupancyType": "Office", "pr_IsHeated": 1}),
        ("c2", {"pr_OccupancyType": "Office", "pr_IsHeated": 1}),
        ("s1", {"pr_OccupancyType": "Support:Storage"}),
    ]
    result = zoning.zones(cells, {"c2": {"s1"}, "s1": {"c2"}})
    assert result["c2"] == result["s1"] != result["c1"]


# Instance BIM ------------------------------------------------------------------------
def test_aperture_movement():
    recorded = {"Revit": {"X": 0, "Y": 0, "Z": 0}}
    assert ibim.aperture_movement([5, 5, 0], recorded) is None
    assert ibim.aperture_movement([-50, 30, 0], recorded) == (-50, 0, 0)


def test_aggregate_spaces():
    rows = [{"UID": "a", "pr_NetArea": 10, "pr_IsHeated": 0, "pr_Name": "ByModel"},
            {"UID": "b", "pr_NetArea": 5.5, "pr_IsHeated": 1, "pr_Name": "Room"}]
    assert ibim.aggregate_spaces(rows) == {"pr_NetArea": 15.5, "pr_IsHeated": 1, "pr_Name": "Room"}
    rows.append({"UID": "c", "pr_Name": "Hall"})
    assert ibim.aggregate_spaces(rows)["pr_Name"] == "Room; Hall"


def test_by_model_measured_area_wins():
    values = ibim.by_model({"pr_NetArea": 27.6}, 30.0, 90.0, 3.0, 28.18, 84.52)
    assert values["pr_NetArea"] == 28.18 and values["pr_NominalHeight"] == 3.0


def test_by_model():
    props = {"pr_OccupancyDensityOperation": 0.1, "pr_OccupancyDensitySafety": 0.5,
             "pr_MechanicalVentilationRatePerPerson": 10}
    values = ibim.by_model(props, 110.0, 330.0, 3.0, 100.0, 300.0)
    assert values["pr_OccupancyNumber"] == 10
    assert values["pr_OccupancyNumberPeak"] == 50  # was never computed in TBIM 0.2
    assert values["pr_NominalHeight"] == 3.0
    assert values["pr_MechanicalVentilationRate"] == round(10 * 3.6 * 10 / 300.0, 5)
    assert values["pr_NaturalVentilationRate"] == ibim.UNDEFINED


# topologicpy JSON reader -------------------------------------------------------------
def test_tbimjson_dictionaries():
    records = [
        {"type": "Cell", "uuid": "1", "dictionary": {"UID": "Cell0", "uuid": "1", "toplevel": 0}},
        {"type": "Face", "uuid": "2", "dictionary": {"UID": "extVerFace0"},
         "apertures": [[{"type": "Face", "dictionary": {"UID": "door0"}}]]},
    ]
    data = tbimjson.dictionaries(records)
    assert data["Cell"] == [{"UID": "Cell0"}]
    assert tbimjson.by_uid(data["Aperture"]) == {"door0": {"UID": "door0"}}
