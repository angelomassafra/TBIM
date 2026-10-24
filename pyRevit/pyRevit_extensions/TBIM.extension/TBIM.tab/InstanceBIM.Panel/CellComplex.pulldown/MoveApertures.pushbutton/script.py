"""Create the InstanceBIM: move the TBIM apertures like the doors and windows moved in Revit."""
from tbim import ibim, paths, revit, tbimjson
from tbim.jsonio import read_json, write_json
from tbim.units import ft_to_cm

doc = revit.Context(__revit__).doc  # noqa: F821
recorded = dict((item["UID"], item["Location"]) for item in read_json(paths.data_file(paths.APERTURE_LOCATIONS)))
moves = {}
for element in [e for c in revit.APERTURE_CATEGORIES for e in revit.instances(doc, c)]:
    element_uid = revit.uid(element)
    point = getattr(element.Location, "Point", None)
    if element_uid not in recorded or point is None:
        continue
    movement = ibim.aperture_movement([int(ft_to_cm(v)) for v in (point.X, point.Y, point.Z)], recorded[element_uid])
    if movement:
        moves[element_uid] = movement
        print("Moved %s: dx=%s dy=%s dz=%s cm" % ((element_uid,) + tuple(movement)))

records = read_json(paths.data_file(paths.CC_TBIM))
moved = tbimjson.move_apertures(records, moves)
path = write_json(paths.data_file(paths.CC_IBIM), records)
revit.alert("Instance BIM", "%d apertures moved.\n\nInstanceBIM exported to:\n%s" % (len(moved), path))
