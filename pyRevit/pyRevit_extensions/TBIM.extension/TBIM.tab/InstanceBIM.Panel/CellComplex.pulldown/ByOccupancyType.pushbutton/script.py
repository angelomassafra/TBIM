#! python3
"""Add the instance data defined by occupancy type to the cells."""
from tbim import instancebim, paths, topo
from tbim.jsonio import read_json
from tbim.revit import alert

cc = topo.load_cellcomplex(paths.data_file(paths.CC_IBIM))
instancebim.by_occupancy_type(cc, read_json(paths.data_file(paths.IBIM_BY_OCCUPANCY_TYPE)))
path = topo.save_cellcomplex(cc, paths.data_file(paths.CC_IBIM))
alert("Instance BIM", "InstanceBIM exported to:\n%s" % path)
