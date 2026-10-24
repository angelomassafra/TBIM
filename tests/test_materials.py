"""Tests of the layered constructions (tbim.materials)."""
import pytest

from tbim import materials

CAVITY_WALL = [("Facing brick", 120), ("Air cavity", 60), ("Hollow clay brick", 80), ("Lime-cement plaster", 15)]


def test_text_and_parse_round_trip():
    text = materials.text(CAVITY_WALL)
    assert text == "Facing brick 120 mm / Air cavity 60 mm / Hollow clay brick 80 mm / Lime-cement plaster 15 mm"
    assert materials.parse(text) == [(name, float(mm)) for name, mm in CAVITY_WALL]
    assert materials.thickness(CAVITY_WALL) == 275


def test_u_value_from_the_layers():
    # 1 / (0.13 + 0.04 + 0.12/0.9 + 0.06/0.33 + 0.08/0.36 + 0.015/0.9)
    assert materials.u_value(CAVITY_WALL, "extVer") == pytest.approx(1.38, abs=0.01)
    insulated = CAVITY_WALL[:1] + [("EPS insulation", 100)] + CAVITY_WALL[1:]
    assert materials.u_value(insulated, "extVer") < 0.3


def test_unknown_material_is_rejected():
    with pytest.raises(KeyError):
        materials.text([("Unobtainium", 10)])
    with pytest.raises(ValueError):
        materials.parse("Facing brick twelve")


def test_revit_spec_carries_function_colour_and_thermal_data():
    name, mm, function, rgb, transparency, k, rho, c = materials.revit_spec([("Facing brick", 120)]).split(":")
    assert (name, mm, function, transparency) == ("Facing brick", "120", "Finish1", "0")
    assert len(rgb.split(",")) == 3 and float(k) > 0 and float(rho) > 0 and float(c) > 0


def test_material_names_fit_the_revit_spec():
    for name, (rgb, k, rho, c, function, transparency) in materials.MATERIALS.items():
        assert not set(name) & set(":;|"), name
        assert function in ("Structure", "Substrate", "Insulation", "Finish1", "Finish2")
        assert all(0 <= v <= 255 for v in rgb) and 0 <= transparency <= 100 and k > 0
