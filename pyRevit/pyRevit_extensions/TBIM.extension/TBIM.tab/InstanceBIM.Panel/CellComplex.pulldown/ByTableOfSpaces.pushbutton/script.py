#! python3
"""Add the instance data of the table of spaces to the cells.

The Name of each Revit space lists the ids of the table rows it contains, separated by ';'.
"""
from Autodesk.Revit.DB import BuiltInParameter

from tbim import instancebim, paths, revit, topo
from tbim.jsonio import read_json

doc = revit.Context(__revit__).doc  # noqa: F821
space_names = {}
for space in revit.spaces(doc):
    name = space.get_Parameter(BuiltInParameter.ROOM_NAME)
    if revit.uid(space) and name is not None and name.AsString():
        space_names[revit.uid(space)] = name.AsString()

cc = topo.load_cellcomplex(paths.data_file(paths.CC_IBIM))
matched = instancebim.by_table_of_spaces(cc, read_json(paths.data_file(paths.IBIM_BY_TABLE_OF_SPACES)), space_names)
path = topo.save_cellcomplex(cc, paths.data_file(paths.CC_IBIM))
revit.alert("Instance BIM",
            "%d cells matched with the table of spaces.\n\nInstanceBIM exported to:\n%s" % (matched, path))
