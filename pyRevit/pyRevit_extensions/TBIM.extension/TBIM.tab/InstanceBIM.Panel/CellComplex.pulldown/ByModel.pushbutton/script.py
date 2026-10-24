#! python3
"""Compute the instance data derived from the model (areas, volumes, occupancy, ventilation)."""
from Autodesk.Revit.DB import BuiltInParameter

from tbim import instancebim, paths, revit, topo
from tbim.units import ft2_to_m2, ft3_to_m3

doc = revit.Context(__revit__).doc  # noqa: F821
net = {}
for space in revit.spaces(doc):
    if revit.uid(space):
        net[revit.uid(space)] = (ft2_to_m2(space.get_Parameter(BuiltInParameter.ROOM_AREA).AsDouble()),
                                 ft3_to_m3(space.get_Parameter(BuiltInParameter.ROOM_VOLUME).AsDouble()))

cc = topo.load_cellcomplex(paths.data_file(paths.CC_IBIM))
count = instancebim.by_model(cc, net)
path = topo.save_cellcomplex(cc, paths.data_file(paths.CC_IBIM))
revit.alert("Instance BIM", "ByModel data computed for %d cells.\n\nInstanceBIM exported to:\n%s" % (count, path))
