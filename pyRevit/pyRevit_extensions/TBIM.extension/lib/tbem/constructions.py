"""Constructions of the Full TBEM from the Informational Styles (CPython only).

Opaque constructions come from the layers of the styled faces (``stFC_Layers``, materials of tbim.materials),
in place of the IfcMaterialLayerSets read by digitman_bim2bem: the TBIM already holds them. Layers are listed
from the outside (or the top) to the inside (or the bottom), so the construction is reversed for the faces whose
outside is below them (floors) and for the second side of an internal wall: EnergyPlus wants the two sides of
an inter-zone surface with mirrored layers.

Windows are simple glazing systems (U, SHGC, VT): from the window data (``pr_ThermalTransmittance``,
``pr_SolarHeatGainCoefficient``, ``pr_VisibleTransmittance``, or the digitman names), else from the settings by
type name, by construction year or the default.
"""
from honeybee.typing import clean_ep_string
from honeybee_energy.construction.opaque import OpaqueConstruction
from honeybee_energy.construction.window import WindowConstruction
from honeybee_energy.construction.windowshade import WindowConstructionShade
from honeybee_energy.material.opaque import EnergyMaterial
from honeybee_energy.material.shade import EnergyWindowMaterialBlind

from tbim import materials

STYLE_KEYS = ("stFC_WallTypeName", "stFC_FloorTypeName", "stFC_RoofTypeName")
NOT_MODELLED = ("Ventilated air cavity",)  # outside the thermal envelope, as in tbim.materials.u_value
GLAZING_KEYS = {"u": ("pr_ThermalTransmittance", "pr_ThermalTrasmittance"),
                "shgc": ("pr_SolarHeatGainCoefficient", "pr_SolarTrasmittance"),
                "vt": ("pr_VisibleTransmittance", "pr_VisibleTrasmittance")}


def style(props):
    for key in STYLE_KEYS:
        if props.get(key):
            return props[key]
    return None


def layers(props):
    """[(material, mm)] of a styled face, or [] (no layers or unknown materials)."""
    text = props.get("stFC_Layers")
    if not text:
        return []
    try:
        return materials.parse(text)
    except ValueError:
        return []


def is_glazed(props):
    """True for faces whose layers include a transparent material (curtain walls, glazed roofs)."""
    return any(materials.MATERIALS[name][5] > 0 for name, _ in layers(props))


def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def glazing_values(props, settings):
    """{'u', 'shgc', 'vt'} of a window."""
    options = settings["glazing"]
    values = dict(options["default"])
    year = _number(props.get("pr_ConstructionYear"))
    if year is not None:
        for last_year, glazing in options["by_construction_year"]:
            if year <= last_year:
                values.update(glazing)
                break
    values.update(options["by_type_name"].get(props.get("stAP_TypeName"), {}))
    for key, names in GLAZING_KEYS.items():
        for name in names:
            if _number(props.get(name)) is not None:
                values[key] = _number(props[name])
                break
    return values


class Library(object):
    """Honeybee materials and constructions, created once and shared by the faces."""

    def __init__(self, settings):
        self.settings = settings
        self.materials, self.opaque, self.windows, self.shaded = {}, {}, {}, {}
        self.unknown = set()  # styles without (valid) layers

    def material(self, name, mm):
        identifier = clean_ep_string("%s %gmm" % (name, mm))
        if identifier not in self.materials:
            _, conductivity, density, specific_heat, _, _ = materials.MATERIALS[name]
            self.materials[identifier] = EnergyMaterial(
                identifier, mm / 1000.0, conductivity, density, max(specific_heat, 100), "MediumRough",
                0.9, 0.7, 0.7)
            self.materials[identifier].display_name = "%s %g mm" % (name, mm)
        return self.materials[identifier]

    def construction(self, props, reverse=False):
        """OpaqueConstruction of a styled face (None: Honeybee default)."""
        name = style(props)
        if not name:
            return None
        key = (name, reverse)
        if key not in self.opaque:
            items = [self.material(n, mm) for n, mm in layers(props) if n not in NOT_MODELLED]
            if not items:
                self.unknown.add(name)
                self.opaque[key] = None
            else:
                identifier = clean_ep_string(name + ("_Rev" if reverse else ""))
                self.opaque[key] = OpaqueConstruction(identifier, list(reversed(items)) if reverse else items)
        return self.opaque[key]

    def window(self, props):
        values = glazing_values(props, self.settings)
        identifier = clean_ep_string("Glazing_U%g_SHGC%g_VT%g" % (values["u"], values["shgc"], values["vt"]))
        if identifier not in self.windows:
            self.windows[identifier] = WindowConstruction.from_simple_parameters(
                identifier, values["u"], values["shgc"], values["vt"])
        return self.windows[identifier]

    def with_blind(self, construction):
        """The window construction with the external blind of the settings (always on, as in digitman)."""
        if construction.identifier not in self.shaded:
            options = dict((k, v) for k, v in self.settings["blinds"].items() if k != "enabled")
            blind = EnergyWindowMaterialBlind("ExternalBlind", **options)
            self.shaded[construction.identifier] = WindowConstructionShade(
                "%s_ExternalBlind" % construction.identifier, construction, blind, "Exterior", "AlwaysOn")
        return self.shaded[construction.identifier]

    def counts(self):
        return {"materials": len(self.materials), "opaque": len([c for c in self.opaque.values() if c]),
                "glazing": len(self.windows), "with blinds": len(self.shaded)}
