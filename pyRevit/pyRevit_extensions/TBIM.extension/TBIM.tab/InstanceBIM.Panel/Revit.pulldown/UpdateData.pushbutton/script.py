"""Write the InstanceBIM data to Revit spaces, walls, floors, roofs, windows and doors (matched by UID)."""
from tbim import paths, revit, tbimjson

ctx = revit.Context(__revit__)  # noqa: F821
doc = ctx.doc
data = tbimjson.dictionaries(paths.data_file(paths.CC_IBIM))

report = []
for label, items, group, categories in (("Spaces", data["Cell"], "Cell", revit.SPACE_CATEGORIES),
                                        ("Walls/Floors/Roofs", data["Face"], "Face", revit.FACE_CATEGORIES),
                                        ("Windows/Doors", data["Aperture"], "Aperture", revit.APERTURE_CATEGORIES)):
    revit.ensure_parameters(ctx, set(k for d in items for k in d), group, categories)
    elements = [e for c in categories for e in revit.instances(doc, c)]
    count = revit.apply_by_uid(doc, elements, tbimjson.by_uid(items), "Update %s" % label)
    report.append("%s updated: %d" % (label, count))

revit.alert("Instance BIM", "InstanceBIM has been updated in Revit.\n\n" + "\n".join(report))
