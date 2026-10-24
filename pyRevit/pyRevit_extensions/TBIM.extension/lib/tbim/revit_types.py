"""Revit side of Informational Styles and TopologicalBIM: layered types and apertures (CPython only).

- Styles: every style of the Informational Rule Sets becomes a wall, floor or roof type whose compound
  structure has the layers of ``stFC_Layers`` (see tbim.materials): materials with their colour and a
  thermal asset (conductivity, density, specific heat), so Revit computes the U-value of the type too.
- TopologicalBIM: windows and doors at the locations computed by tbim.apertures, hosted by the walls of
  their faces (matched by UID), as types of the template families sized from the rules.
"""
from Autodesk.Revit.DB import (
    XYZ,
    BuiltInCategory,
    BuiltInParameter,
    Color,
    CompoundStructure,
    CompoundStructureLayer,
    EndCapCondition,
    FamilySymbol,
    FilteredElementCollector,
    FloorType,
    Material,
    MaterialAspect,
    MaterialFunctionAssignment,
    PropertySetElement,
    RoofType,
    ShellLayerType,
    ThermalAsset,
    ThermalMaterialType,
    UnitTypeId,
    UnitUtils,
    WallKind,
    WallType,
)
from Autodesk.Revit.DB.Structure import StructuralType
from System.Collections.Generic import List

from tbim import materials, revit
from tbim.units import cm_to_ft

STYLE_KEYS = (("stFC_WallTypeName", WallType), ("stFC_FloorTypeName", FloorType), ("stFC_RoofTypeName", RoofType))
FUNCTIONS = {  # tbim.materials layer functions -> Revit
    materials.STRUCTURE: MaterialFunctionAssignment.Structure,
    materials.SUBSTRATE: MaterialFunctionAssignment.Substrate,
    materials.INSULATION: MaterialFunctionAssignment.Insulation,
    materials.FINISH1: MaterialFunctionAssignment.Finish1,
    materials.FINISH2: MaterialFunctionAssignment.Finish2,
}
# template families of the default Revit project template, with fallbacks to any family of the category
WINDOW_FAMILY, DOOR_FAMILY, DOUBLE_DOOR_FAMILY = "Windows_Sgl_Plain", "Doors_IntSgl", "Doors_ExtDbl_Flush"
DOUBLE_DOOR_WIDTH_CM = 150


def _mm(value):
    return UnitUtils.ConvertToInternalUnits(float(value), UnitTypeId.Millimeters)


# --------------------------------------------------------------------------------------
# Materials and layered types
def material(doc, name):
    """The material ``name`` of tbim.materials (created, or updated if it exists). Return its id."""
    rgb, conductivity, density, specific_heat, _, transparency = materials.MATERIALS[name]
    existing = [m for m in FilteredElementCollector(doc).OfClass(Material) if m.Name == name]
    m = existing[0] if existing else doc.GetElement(Material.Create(doc, name))
    m.Color = Color(*rgb)
    m.Transparency = transparency
    m.MaterialClass = "TBIM"
    m.MaterialCategory = "TBIM"
    if m.ThermalAssetId.Value < 0:  # no thermal asset yet
        asset = ThermalAsset(name, ThermalMaterialType.Solid)
        asset.ThermalConductivity = UnitUtils.ConvertToInternalUnits(conductivity, UnitTypeId.WattsPerMeterKelvin)
        asset.Density = UnitUtils.ConvertToInternalUnits(density, UnitTypeId.KilogramsPerCubicMeter)
        asset.SpecificHeat = UnitUtils.ConvertToInternalUnits(specific_heat, UnitTypeId.JoulesPerKilogramDegreeCelsius)
        m.SetMaterialAspectByPropertySet(MaterialAspect.Thermal, PropertySetElement.Create(doc, asset).Id)
    return m.Id


def compound_structure(doc, layers, is_wall):
    """CompoundStructure of [(material, mm)] from the outside (top) to the inside (bottom)."""
    functions, first, last = materials.shell_functions(materials.MATERIALS[name][4] for name, _ in layers)
    items = List[CompoundStructureLayer]()
    for (name, mm), function in zip(layers, functions):
        items.Add(CompoundStructureLayer(_mm(mm), FUNCTIONS[function], material(doc, name)))
    structure = CompoundStructure.CreateSimpleCompoundStructure(items)
    structure.SetNumberOfShellLayers(ShellLayerType.Exterior, first)
    structure.SetNumberOfShellLayers(ShellLayerType.Interior, len(layers) - 1 - last)
    if not is_wall:
        structure.EndCap = EndCapCondition.NoEndCap
    valid = structure.IsValid(doc, None, None)
    if not (valid[0] if isinstance(valid, tuple) else valid):  # pythonnet returns the out arguments too
        core = List[CompoundStructureLayer]()
        for item in items:
            core.Add(CompoundStructureLayer(item.Width, MaterialFunctionAssignment.Structure, item.MaterialId))
        structure = CompoundStructure.CreateSimpleCompoundStructure(core)
        if not is_wall:
            structure.EndCap = EndCapCondition.NoEndCap
    return structure


def _base_type(doc, cls):
    """A layered type of ``cls`` to duplicate (basic walls, non-foundation floors)."""
    for t in FilteredElementCollector(doc).OfClass(cls):
        structure = t.GetCompoundStructure()
        if structure is None:
            continue
        if isinstance(t, WallType) and t.Kind != WallKind.Basic:
            continue
        if isinstance(t, FloorType) and t.IsFoundationSlab:
            continue
        return t
    raise RuntimeError("No layered %s in the model to duplicate" % cls.__name__)


def layered_type(doc, cls, name, layers_text=None):
    """The type ``name`` of ``cls``, created with the layers of ``layers_text`` (stFC_Layers) if missing.

    Without layers the type gets one structure layer as thick as the number ending its name (TBIM_X_300),
    in the material of the duplicated type.
    """
    existing = [t for t in FilteredElementCollector(doc).OfClass(cls) if revit.type_name(t) == name]
    if existing:
        return existing[0], False
    new_type = _base_type(doc, cls).Duplicate(name)
    is_wall = cls is WallType
    if layers_text:
        new_type.SetCompoundStructure(compound_structure(doc, materials.parse(layers_text), is_wall))
    else:
        suffix = name.rsplit("_", 1)[-1]
        if suffix.isdigit():
            base = new_type.GetCompoundStructure()
            material_id = base.GetMaterialId(base.GetFirstCoreLayerIndex())
            structure = CompoundStructure.CreateSingleLayerCompoundStructure(
                MaterialFunctionAssignment.Structure, _mm(suffix), material_id)
            if not is_wall:
                structure.EndCap = EndCapCondition.NoEndCap
            new_type.SetCompoundStructure(structure)
    return new_type, True


def apply_styles(doc, faces):
    """Give walls, floors and roofs the layered type of their style. faces: {face UID: face properties}.

    Return ({'Walls'|'Floors'|'Roofs': n, 'Types created': n}, problems).
    """
    counts = {"Walls": 0, "Floors": 0, "Roofs": 0, "Types created": 0}
    problems = []
    labels = {WallType: "Walls", FloorType: "Floors", RoofType: "Roofs"}
    with revit.transaction(doc, "Informational Styles - element types"):
        for element in [e for c in revit.FACE_CATEGORIES for e in revit.instances(doc, c)]:
            props = faces.get(revit.uid(element))
            if not props:
                continue
            category = element.Category.BuiltInCategory
            cls = WallType if category == BuiltInCategory.OST_Walls else (
                FloorType if category == BuiltInCategory.OST_Floors else RoofType)
            key = next(k for k, c in STYLE_KEYS if c is cls)
            name = props.get(key)
            if not name:
                continue
            try:
                element_type, created = layered_type(doc, cls, name, props.get("stFC_Layers"))
                counts["Types created"] += int(created)
                if element.GetTypeId().Value != element_type.Id.Value:
                    element.ChangeTypeId(element_type.Id)
                counts[labels[cls]] += 1
            except Exception as e:
                problems.append("%s (%s): %s" % (revit.uid(element), name, e))
    return counts, problems


# --------------------------------------------------------------------------------------
# Apertures
def _symbol(doc, category, family, name, width_cm, height_cm):
    symbols = [s for s in FilteredElementCollector(doc).OfClass(FamilySymbol).OfCategory(category)]
    named = [s for s in symbols if revit.type_name(s) == name]
    if named:
        symbol = named[0]
    else:
        base = [s for s in symbols if s.FamilyName == family] or symbols
        if not base:
            raise RuntimeError("No %s family loaded in the model" % category)
        symbol = base[0].Duplicate(name)
        for builtin, value in ((BuiltInParameter.FAMILY_WIDTH_PARAM, width_cm),
                               (BuiltInParameter.FAMILY_HEIGHT_PARAM, height_cm)):
            revit.set_builtin(symbol, builtin, cm_to_ft(value))
    if not symbol.IsActive:
        symbol.Activate()
    return symbol


def delete_apertures(doc):
    """Delete the windows and doors placed by TopologicalBIM (UID 'window<i>' or 'door<i>'). Return the count."""
    ids = [e.Id for c in revit.APERTURE_CATEGORIES for e in revit.instances(doc, c)
           if (revit.uid(e) or "").startswith(("window", "door"))]
    for element_id in ids:
        doc.Delete(element_id)
    return len(ids)


def place_apertures(ctx, placements):
    """Windows and doors of tbim.apertures.place in the walls of their host faces.

    Earlier TopologicalBIM apertures are replaced. Return (placed, problems).
    """
    doc = ctx.doc
    revit.ensure_parameters(ctx, ["UID"], "Aperture", revit.APERTURE_CATEGORIES)
    walls = {}
    for wall in revit.instances(doc, BuiltInCategory.OST_Walls):
        walls.setdefault(revit.uid(wall), wall)
    placed, problems = 0, []
    with revit.transaction(doc, "TopologicalBIM - windows and doors"):
        delete_apertures(doc)
        for p in placements:
            wall = walls.get(p["host"])
            if wall is None:
                problems.append("%s: no wall for face %s" % (p["UID"], p["host"]))
                continue
            try:
                if p["kind"] == "window":
                    category, family = BuiltInCategory.OST_Windows, WINDOW_FAMILY
                else:
                    category = BuiltInCategory.OST_Doors
                    family = DOUBLE_DOOR_FAMILY if p["width"] >= DOUBLE_DOOR_WIDTH_CM else DOOR_FAMILY
                symbol = _symbol(doc, category, family, p["type"], p["width"], p["height"])
                level = doc.GetElement(wall.LevelId)
                x, y, z = p["point"]
                instance = doc.Create.NewFamilyInstance(XYZ(cm_to_ft(x), cm_to_ft(y), level.Elevation), symbol, wall,
                                                        level, StructuralType.NonStructural)
                sill = instance.get_Parameter(BuiltInParameter.INSTANCE_SILL_HEIGHT_PARAM)
                if sill is not None and not sill.IsReadOnly:
                    sill.Set(cm_to_ft(z + p["sill"]) - level.Elevation)
                revit.set_by_name(instance, "UID", p["UID"])
                placed += 1
            except Exception as e:
                problems.append("%s: %s" % (p["UID"], e))
    # Revit deletes the instances that do not fit their wall (e.g. a door wider than the free length)
    present = set(revit.uid(e) for c in revit.APERTURE_CATEGORIES for e in revit.instances(doc, c))
    deleted = [p["UID"] for p in placements if p["UID"] not in present and p["host"] in walls]
    if deleted:
        problems.append("deleted by Revit (they do not fit their wall): %s" % ", ".join(deleted))
    return placed - len(deleted), problems
