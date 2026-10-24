#! python3
"""Apply the Informational Rule Sets (IRSs) to the faces of the CellComplex."""
from tbim import irs, paths, styles, topo
from tbim.revit import alert

cc = topo.load_cellcomplex(paths.data_file(paths.CC_LOADS))
rulesets = irs.load()
styled = styles.run(cc, rulesets)
path = topo.save_cellcomplex(cc, paths.data_file(paths.CC_STYLES))
alert("Informational Styles",
      "%d rule sets applied, %d faces styled.\n\nExported to:\n%s" % (len(rulesets), styled, path))
